#ifndef NOMINMAX
#define NOMINMAX
#endif
#include "alinify/camera/gidel_camera.h"
#include "alinify/common/logger.h"
#include <procext.h>
#include <global_regs.h>
#include <algorithm>

namespace alinify {
namespace camera {

// Static callback bridge
static GidelCamera* g_camera_instance = nullptr;

GidelCamera::GidelCamera() 
    : fg_api_(nullptr)
    , board_id_(0)
    , is_acquiring_(false)
    , should_stop_(false)
    , current_strip_id_(0)
    , current_position_mm_(0.0)
    , is_left_to_right_(true) {
    
    g_camera_instance = this;
    stats_ = {};
}

GidelCamera::~GidelCamera() {
    stopAcquisition();
    
    if (fg_api_) {
        delete fg_api_;
        fg_api_ = nullptr;
    }
    
    g_camera_instance = nullptr;
}

StatusCode GidelCamera::initialize(const CameraConfig& config) {
    LOG_INFO("Initializing Gidel camera...");
    
    config_ = config;
    
    try {
        // Create ProcFg API instance
        fg_api_ = new fg::CProcFgApi();
        
        fg::CAMERA_INFO cameras;
        if (!fg_api_->Init(cameras)) {
            char error_desc[1024];
            fg_api_->GetLastError(error_desc);
            LOG_ERROR("Failed to initialize Gidel API: ", error_desc);
            return StatusCode::ERROR_CAMERA_INIT;
        }
        
        // Load configuration file
        if (!config_file_.empty()) {
            if (!fg_api_->LoadConfig(config_file_.c_str())) {
                char error_desc[1024];
                fg_api_->GetLastError(error_desc);
                LOG_ERROR("Failed to load config file: ", error_desc);
                return StatusCode::ERROR_CAMERA_INIT;
            }
        }
        
        // Create buffers
        // Use the same buffer size as FgExample (72 MB) for 4096x18432 images
        // This is large enough for the full scan strip
        const size_t buffer_size = 0x4E50000;  // 72 MB (from FgExample.cpp)
        const int buffer_count = 30;  // From Gidel example
        
        LOG_INFO("Allocating ", buffer_count, " buffers of ", buffer_size / (1024 * 1024), " MB each");
        
        for (int i = 0; i < buffer_count; i++) {
            fg::BUFFER_HANDLE handle = fg_api_->AnnounceBuffer(buffer_size, nullptr, this);
            if (handle == nullptr) {
                LOG_ERROR("Failed to announce buffer ", i);
                return StatusCode::ERROR_CAMERA_INIT;
            }
            
            if (!fg_api_->QueueBuffer(handle)) {
                LOG_ERROR("Failed to queue buffer ", i);
                return StatusCode::ERROR_CAMERA_INIT;
            }
            
            buffer_handles_.push_back(handle);
        }
        
        // Set callbacks
        if (!fg_api_->SetImageCallBack(grabberCallback)) {
            LOG_ERROR("Failed to set image callback");
            return StatusCode::ERROR_CAMERA_INIT;
        }
        
        if (!fg_api_->SetFgStateCallBack(statusCallback, 100)) {
            LOG_ERROR("Failed to set status callback");
            return StatusCode::ERROR_CAMERA_INIT;
        }
        
        LOG_INFO("Gidel camera initialized successfully");
        return StatusCode::SUCCESS;
        
    } catch (const std::exception& e) {
        LOG_ERROR("Exception during camera initialization: ", e.what());
        return StatusCode::ERROR_CAMERA_INIT;
    }
}

StatusCode GidelCamera::startAcquisition() {
    if (is_acquiring_) {
        LOG_WARNING("Camera is already acquiring");
        return StatusCode::SUCCESS;
    }
    
    if (!fg_api_) {
        LOG_ERROR("Camera not initialized");
        return StatusCode::ERROR_CAMERA_START;
    }
    
    LOG_INFO("Starting acquisition...");
    
    // Reset statistics
    {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_ = {};
        last_frame_time_ = std::chrono::high_resolution_clock::now();
    }
    
    // Start processing thread
    should_stop_ = false;
    processing_thread_ = std::thread(&GidelCamera::processingThread, this);
    
    // Start grabbing
    if (!fg_api_->Grab()) {
        char error_desc[1024];
        fg_api_->GetLastError(error_desc);
        LOG_ERROR("Failed to start grabbing: ", error_desc);
        return StatusCode::ERROR_CAMERA_START;
    }
    
    is_acquiring_ = true;
    LOG_INFO("Acquisition started");
    return StatusCode::SUCCESS;
}

StatusCode GidelCamera::stopAcquisition() {
    if (!is_acquiring_) {
        return StatusCode::SUCCESS;
    }
    
    LOG_INFO("Stopping acquisition...");
    
    if (fg_api_) {
        fg_api_->StopAcquisition();
    }
    
    // Stop processing thread
    should_stop_ = true;
    queue_cv_.notify_all();
    
    if (processing_thread_.joinable()) {
        processing_thread_.join();
    }
    
    is_acquiring_ = false;
    LOG_INFO("Acquisition stopped");
    return StatusCode::SUCCESS;
}

bool GidelCamera::isAcquiring() const {
    return is_acquiring_;
}

StatusCode GidelCamera::setTriggerMode(const std::string& mode, int frequency) {
    LOG_INFO("Setting trigger mode: ", mode, " @ ", frequency, " Hz");
    
    // This requires access to Proc and global_regs
    // Implementation would use the trigger example logic
    // For now, we'll log and return success
    
    // TODO: Implement using Proc and global_regs similar to TriggerExample.cpp
    
    return StatusCode::SUCCESS;
}

StatusCode GidelCamera::setEncoderTrigger(double step) {
    LOG_INFO("Setting encoder trigger with step: ", step, " mm");
    
    // TODO: Implement encoder trigger using encoder IP
    
    return StatusCode::SUCCESS;
}

void GidelCamera::setImageCallback(ImageCallback callback) {
    image_callback_ = callback;
}

void GidelCamera::setErrorCallback(ErrorCallback callback) {
    error_callback_ = callback;
}

GidelCamera::Statistics GidelCamera::getStatistics() const {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    return stats_;
}

StatusCode GidelCamera::saveConfiguration(const std::string& filename) {
    // TODO: Implement configuration save
    return StatusCode::SUCCESS;
}

StatusCode GidelCamera::loadConfiguration(const std::string& filename) {
    config_file_ = filename;
    return StatusCode::SUCCESS;
}

std::string GidelCamera::getDeviceInfo() const {
    return "Gidel CameraLink Frame Grabber";
}

StatusCode GidelCamera::setConfigFile(const std::string& config_file) {
    config_file_ = config_file;
    return StatusCode::SUCCESS;
}

// Static callbacks
void GidelCamera::grabberCallback(fg::BUFFER_DATA buffer_info) {
    if (g_camera_instance) {
        g_camera_instance->processBuffer(buffer_info);
    }
}

void GidelCamera::statusCallback(fg::CURRENT_STATE state) {
    if (!g_camera_instance) return;
    
    std::lock_guard<std::mutex> lock(g_camera_instance->stats_mutex_);
    g_camera_instance->stats_.frames_received = state.Received;
    g_camera_instance->stats_.fps = state.Fps;
    
    if (state.State == fg::STATE_ERROR && g_camera_instance->error_callback_) {
        g_camera_instance->error_callback_(state.ErrorMessage);
    }
}

void GidelCamera::processBuffer(fg::BUFFER_DATA buffer_info) {
    // Update statistics
    {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.frames_received++;
        
        auto now = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - last_frame_time_).count();
        
        if (duration > 0) {
            stats_.fps = 1000.0 / duration;
        }
        last_frame_time_ = now;
    }
    
    // Create scan strip
    ScanStrip strip;
    strip.strip_id = current_strip_id_++;
    strip.physical_position = current_position_mm_;
    strip.is_left_to_right = is_left_to_right_;
    
    // Copy image data - use actual buffer dimensions from frame grabber
    const byte_t* buffer_ptr = static_cast<const byte_t*>(buffer_info.pBuffer);
    const size_t data_size = buffer_info.BufferSizeBytes;
    
    // Use BufferInfoHeight from the frame grabber, not config_.height
    // The frame grabber accumulates scan lines into strips (e.g., 4096x18432)
    const int frame_height = buffer_info.BufferInfoHeight;
    const int frame_width = buffer_info.BufferInfoWidth;
    
    strip.image = Image<byte_t>(frame_width, frame_height, 1, config_.bit_depth);
    std::memcpy(strip.image.ptr(), buffer_ptr + buffer_info.Offset, 
                (std::min)(data_size, strip.image.size()));
    
    // Queue for processing
    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        strip_queue_.push(strip);
    }
    queue_cv_.notify_one();
    
    // Queue the previous buffer back to the grabber
    static fg::BUFFER_HANDLE prev_handle = nullptr;
    static bool has_prev = false;
    
    if (has_prev && prev_handle) {
        fg_api_->QueueBuffer(prev_handle);
    }
    
    prev_handle = buffer_info.hBuffer;
    has_prev = true;
    
    // Update position (simplified - actual position comes from encoder or time)
    current_position_mm_ += config_.fov_width_mm;
}

void GidelCamera::processingThread() {
    LOG_DEBUG("Processing thread started");
    
    while (!should_stop_) {
        ScanStrip strip;
        
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            queue_cv_.wait(lock, [this] { 
                return !strip_queue_.empty() || should_stop_; 
            });
            
            if (should_stop_ && strip_queue_.empty()) {
                break;
            }
            
            if (!strip_queue_.empty()) {
                strip = strip_queue_.front();
                strip_queue_.pop();
            }
        }
        
        // Call user callback
        if (image_callback_) {
            try {
                image_callback_(strip);
            } catch (const std::exception& e) {
                LOG_ERROR("Exception in image callback: ", e.what());
                if (error_callback_) {
                    error_callback_(e.what());
                }
            }
        }
    }
    
    LOG_DEBUG("Processing thread stopped");
}

} // namespace camera
} // namespace alinify
