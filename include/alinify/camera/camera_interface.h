#ifndef ALINIFY_CAMERA_INTERFACE_H
#define ALINIFY_CAMERA_INTERFACE_H

#include "alinify/common/types.h"
#include <functional>
#include <atomic>

namespace alinify {
namespace camera {

// Camera callback function type
using ImageCallback = std::function<void(const ScanStrip&)>;
using ErrorCallback = std::function<void(const std::string&)>;

/**
 * @brief Abstract interface for camera acquisition
 * 
 * This interface abstracts the camera hardware layer, allowing
 * different camera implementations (Gidel, GenICam, etc.)
 */
class ICameraInterface {
public:
    virtual ~ICameraInterface() = default;
    
    /**
     * @brief Initialize camera with configuration
     */
    virtual StatusCode initialize(const CameraConfig& config) = 0;
    
    /**
     * @brief Start continuous acquisition
     */
    virtual StatusCode startAcquisition() = 0;
    
    /**
     * @brief Stop acquisition
     */
    virtual StatusCode stopAcquisition() = 0;
    
    /**
     * @brief Check if camera is acquiring
     */
    virtual bool isAcquiring() const = 0;
    
    /**
     * @brief Set trigger mode
     * @param mode "auto", "external", "encoder"
     * @param frequency Trigger frequency in Hz (for auto mode)
     */
    virtual StatusCode setTriggerMode(const std::string& mode, int frequency = 10000) = 0;
    
    /**
     * @brief Set encoder trigger parameters
     * @param step Step size in mm between triggers
     */
    virtual StatusCode setEncoderTrigger(double step) = 0;
    
    /**
     * @brief Register callback for acquired images
     */
    virtual void setImageCallback(ImageCallback callback) = 0;
    
    /**
     * @brief Register callback for errors
     */
    virtual void setErrorCallback(ErrorCallback callback) = 0;
    
    /**
     * @brief Get current camera statistics
     */
    struct Statistics {
        uint64_t frames_received;
        uint64_t frames_dropped;
        double fps;
        double temperature;
    };
    
    virtual Statistics getStatistics() const = 0;
    
    /**
     * @brief Save current configuration
     */
    virtual StatusCode saveConfiguration(const std::string& filename) = 0;
    
    /**
     * @brief Load configuration
     */
    virtual StatusCode loadConfiguration(const std::string& filename) = 0;
    
    /**
     * @brief Get camera information
     */
    virtual std::string getDeviceInfo() const = 0;
};

} // namespace camera
} // namespace alinify

#endif // ALINIFY_CAMERA_INTERFACE_H
