#ifndef ALINIFY_CAMERA_GIDEL_CAMERA_H
#define ALINIFY_CAMERA_GIDEL_CAMERA_H

#include "camera_interface.h"
#include <ProcFgApi.h>
#include <g_InfiniVision.h>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>

namespace alinify {
namespace camera {

/**
 * @brief Gidel CameraLink frame grabber implementation
 * 
 * Supports:
 * - CameraLink interface via ProcFgApi
 * - InfiniVision multi-camera system
 * - GenTL producer
 * - Hardware triggering (auto, external, encoder)
 */
class GidelCamera : public ICameraInterface {
public:
    GidelCamera();
    ~GidelCamera() override;
    
    // ICameraInterface implementation
    StatusCode initialize(const CameraConfig& config) override;
    StatusCode startAcquisition() override;
    StatusCode stopAcquisition() override;
    bool isAcquiring() const override;
    StatusCode setTriggerMode(const std::string& mode, int frequency) override;
    StatusCode setEncoderTrigger(double step) override;
    void setImageCallback(ImageCallback callback) override;
    void setErrorCallback(ErrorCallback callback) override;
    Statistics getStatistics() const override;
    StatusCode saveConfiguration(const std::string& filename) override;
    StatusCode loadConfiguration(const std::string& filename) override;
    std::string getDeviceInfo() const override;
    
    /**
     * @brief Set specific Gidel configuration file
     */
    StatusCode setConfigFile(const std::string& config_file);
    
    /**
     * @brief Set board ID
     */
    void setBoardId(int board_id) { board_id_ = board_id; }
    
private:
    // Gidel API callbacks (static)
    static void grabberCallback(fg::BUFFER_DATA buffer_info);
    static void statusCallback(fg::CURRENT_STATE state);
    
    // Internal processing
    void processBuffer(fg::BUFFER_DATA buffer_info);
    void processingThread();
    
    // Configuration
    CameraConfig config_;
    std::string config_file_;
    int board_id_;
    
    // Gidel objects
    fg::CProcFgApi* fg_api_;
    std::vector<fg::BUFFER_HANDLE> buffer_handles_;
    
    // State
    std::atomic<bool> is_acquiring_;
    std::atomic<bool> should_stop_;
    
    // Callbacks
    ImageCallback image_callback_;
    ErrorCallback error_callback_;
    
    // Buffer queue for processing
    std::queue<ScanStrip> strip_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;
    std::thread processing_thread_;
    
    // Statistics
    mutable std::mutex stats_mutex_;
    Statistics stats_;
    timestamp_t last_frame_time_;
    
    // Scanning state
    int current_strip_id_;
    double current_position_mm_;
    bool is_left_to_right_;
};

} // namespace camera
} // namespace alinify

#endif // ALINIFY_CAMERA_GIDEL_CAMERA_H
