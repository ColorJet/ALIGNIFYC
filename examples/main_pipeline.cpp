/**
 * @file main_pipeline.cpp
 * @brief Complete pipeline example demonstrating all modules
 */

#include "alinify/common/types.h"
#include "alinify/common/logger.h"
#include "alinify/camera/gidel_camera.h"
#include "alinify/stitching/strip_stitcher.h"
#include "alinify/preprocessing/image_processor.h"
#include "alinify/registration/elastix_wrapper.h"
#include "alinify/gpu_warp/cuda_warper.h"
#include "alinify/printer/printer_interface.h"

#include <iostream>
#include <thread>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>

using namespace alinify;

// Global state for pipeline
std::atomic<bool> g_running{false};
std::queue<ScanStrip> g_strip_queue;
std::mutex g_queue_mutex;
std::condition_variable g_queue_cv;

// Statistics
struct PipelineStats {
    uint64_t strips_acquired = 0;
    uint64_t strips_processed = 0;
    double total_acquisition_time_ms = 0;
    double total_stitching_time_ms = 0;
    double total_registration_time_ms = 0;
    double total_warping_time_ms = 0;
};

PipelineStats g_stats;

// Camera callback
void onCameraStrip(const ScanStrip& strip) {
    std::lock_guard<std::mutex> lock(g_queue_mutex);
    g_strip_queue.push(strip);
    g_stats.strips_acquired++;
    g_queue_cv.notify_one();
}

// Processing thread
void processingThread(
    stitching::StripStitcher* stitcher,
    preprocessing::ImageProcessor* preprocessor,
    registration::ElastixWrapper* registrator,
    gpu_warp::CudaWarper* warper,
    printer::PrinterInterface* printer,
    const Image<byte_t>& design_image)
{
    LOG_INFO("Processing thread started");
    
    while (g_running) {
        ScanStrip strip;
        
        // Get strip from queue
        {
            std::unique_lock<std::mutex> lock(g_queue_mutex);
            g_queue_cv.wait(lock, [] { 
                return !g_strip_queue.empty() || !g_running; 
            });
            
            if (!g_running && g_strip_queue.empty()) {
                break;
            }
            
            if (!g_strip_queue.empty()) {
                strip = g_strip_queue.front();
                g_strip_queue.pop();
            }
        }
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // 1. Stitch strip
        auto stitch_start = std::chrono::high_resolution_clock::now();
        StatusCode status = stitcher->addStrip(strip);
        auto stitch_end = std::chrono::high_resolution_clock::now();
        
        if (status != StatusCode::SUCCESS) {
            LOG_ERROR("Stitching failed for strip ", strip.strip_id);
            continue;
        }
        
        double stitch_time = std::chrono::duration_cast<std::chrono::microseconds>(
            stitch_end - stitch_start).count() / 1000.0;
        g_stats.total_stitching_time_ms += stitch_time;
        
        // Every N strips, perform registration
        const int REGISTRATION_INTERVAL = 10;
        if (strip.strip_id % REGISTRATION_INTERVAL == 0 && strip.strip_id > 0) {
            
            LOG_INFO("Performing registration at strip ", strip.strip_id);
            
            // 2. Get stitched image
            Image<byte_t> stitched = stitcher->getStitchedImage();
            
            // 3. Preprocess
            Image<byte_t> preprocessed;
            preprocessing::ImageProcessor::PreprocessingConfig prep_config;
            prep_config.enable_gaussian = true;
            prep_config.gaussian_sigma = 1.0;
            prep_config.enable_normalize = true;
            
            preprocessor->applyPipeline(stitched, preprocessed, prep_config);
            
            // 4. Register to design image
            auto reg_start = std::chrono::high_resolution_clock::now();
            RegistrationResult reg_result;
            status = registrator->registerImages(design_image, preprocessed, reg_result);
            auto reg_end = std::chrono::high_resolution_clock::now();
            
            if (status != StatusCode::SUCCESS || !reg_result.success) {
                LOG_ERROR("Registration failed");
                continue;
            }
            
            double reg_time = std::chrono::duration_cast<std::chrono::milliseconds>(
                reg_end - reg_start).count();
            g_stats.total_registration_time_ms += reg_time;
            
            LOG_INFO("Registration completed: metric=", reg_result.metric_value, 
                    " time=", reg_time, "ms");
            
            // 5. Warp full resolution design image
            if (warper) {
                auto warp_start = std::chrono::high_resolution_clock::now();
                Image<byte_t> warped;
                status = warper->warpImage(design_image, reg_result.deformation, warped);
                auto warp_end = std::chrono::high_resolution_clock::now();
                
                if (status == StatusCode::SUCCESS) {
                    double warp_time = std::chrono::duration_cast<std::chrono::milliseconds>(
                        warp_end - warp_start).count();
                    g_stats.total_warping_time_ms += warp_time;
                    
                    LOG_INFO("Warping completed: time=", warp_time, "ms");
                    
                    // 6. Send to printer
                    if (printer && printer->isReady()) {
                        status = printer->sendImage(warped);
                        if (status == StatusCode::SUCCESS) {
                            LOG_INFO("Image sent to printer");
                        } else {
                            LOG_ERROR("Failed to send image to printer");
                        }
                    }
                }
            }
        }
        
        g_stats.strips_processed++;
        
        auto end_time = std::chrono::high_resolution_clock::now();
        double total_time = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time).count();
        
        LOG_DEBUG("Strip ", strip.strip_id, " processed in ", total_time, "ms");
    }
    
    LOG_INFO("Processing thread stopped");
}

int main(int argc, char* argv[]) {
    
    // Initialize logger
    Logger::getInstance().setLogLevel(LogLevel::INFO);
    Logger::getInstance().setLogFile("logs/alinify.log");
    
    LOG_INFO("=== Alinify Pipeline Starting ===");
    
    // Configuration
    CameraConfig cam_config;
    cam_config.width = 4096;
    cam_config.height = 1;
    cam_config.frequency_hz = 10000;
    cam_config.fov_width_mm = 42.0;
    
    ScanningParams scan_params;
    scan_params.max_length_mm = 1800.0;
    scan_params.strip_width_mm = 42.0;
    scan_params.overlap_pixels = 100;
    scan_params.bidirectional = true;
    
    RegistrationParams reg_params;
    reg_params.pyramid_levels = 5;
    reg_params.bspline_grid_spacing = 50;
    reg_params.max_iterations = 500;
    
    GPUConfig gpu_config;
    gpu_config.device_id = 0;
    gpu_config.tile_width = 4096;
    gpu_config.tile_height = 4096;
    
    // Initialize modules
    LOG_INFO("Initializing camera...");
    camera::GidelCamera camera;
    camera.setConfigFile("config/camera/FGConfig.gxfg");
    camera.setBoardId(0);
    
    if (camera.initialize(cam_config) != StatusCode::SUCCESS) {
        LOG_ERROR("Failed to initialize camera");
        return 1;
    }
    
    LOG_INFO("Initializing stitcher...");
    stitching::StripStitcher stitcher;
    if (stitcher.initialize(scan_params) != StatusCode::SUCCESS) {
        LOG_ERROR("Failed to initialize stitcher");
        return 1;
    }
    
    LOG_INFO("Initializing preprocessor...");
    preprocessing::ImageProcessor preprocessor;
    
    LOG_INFO("Initializing registration...");
    registration::ElastixWrapper registrator;
    if (registrator.initialize(reg_params) != StatusCode::SUCCESS) {
        LOG_ERROR("Failed to initialize registration");
        return 1;
    }
    
    LOG_INFO("Initializing GPU warper...");
    gpu_warp::CudaWarper warper;
    if (gpu_warp::CudaWarper::isGPUAvailable()) {
        if (warper.initialize(gpu_config) != StatusCode::SUCCESS) {
            LOG_WARNING("Failed to initialize GPU warper, continuing without GPU acceleration");
        }
    } else {
        LOG_WARNING("GPU not available");
    }
    
    LOG_INFO("Initializing printer...");
    printer::PrinterInterface printer;
    // printer.initialize("lib/printer_interface.dll");
    
    // Load design image (placeholder)
    LOG_INFO("Loading design image...");
    Image<byte_t> design_image(4096, 10000, 3, 8);  // Placeholder
    
    // Set camera callback
    camera.setImageCallback(onCameraStrip);
    
    // Start processing thread
    g_running = true;
    std::thread proc_thread(processingThread, &stitcher, &preprocessor, 
                           &registrator, &warper, &printer, std::ref(design_image));
    
    // Start camera
    LOG_INFO("Starting camera acquisition...");
    if (camera.startAcquisition() != StatusCode::SUCCESS) {
        LOG_ERROR("Failed to start camera");
        g_running = false;
        proc_thread.join();
        return 1;
    }
    
    LOG_INFO("Pipeline running. Press Enter to stop...");
    std::cin.get();
    
    // Stop pipeline
    LOG_INFO("Stopping pipeline...");
    camera.stopAcquisition();
    
    g_running = false;
    g_queue_cv.notify_all();
    proc_thread.join();
    
    // Print statistics
    LOG_INFO("=== Pipeline Statistics ===");
    LOG_INFO("Strips acquired: ", g_stats.strips_acquired);
    LOG_INFO("Strips processed: ", g_stats.strips_processed);
    LOG_INFO("Average stitching time: ", 
            g_stats.total_stitching_time_ms / g_stats.strips_processed, "ms");
    
    if (g_stats.total_registration_time_ms > 0) {
        LOG_INFO("Total registration time: ", g_stats.total_registration_time_ms, "ms");
        LOG_INFO("Total warping time: ", g_stats.total_warping_time_ms, "ms");
    }
    
    LOG_INFO("=== Pipeline Stopped ===");
    
    return 0;
}
