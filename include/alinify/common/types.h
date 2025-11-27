#ifndef ALINIFY_COMMON_TYPES_H
#define ALINIFY_COMMON_TYPES_H

#include <cstdint>
#include <vector>
#include <memory>
#include <string>
#include <chrono>

namespace alinify {

// Type aliases
using timestamp_t = std::chrono::time_point<std::chrono::high_resolution_clock>;
using byte_t = uint8_t;
using pixel_t = uint16_t;  // Support up to 16-bit images

// Image data structure
template<typename T = byte_t>
struct Image {
    std::vector<T> data;
    int width;
    int height;
    int channels;
    int bit_depth;
    timestamp_t timestamp;
    
    Image() : width(0), height(0), channels(1), bit_depth(8) {}
    
    Image(int w, int h, int c = 1, int bits = 8) 
        : width(w), height(h), channels(c), bit_depth(bits) {
        data.resize(w * h * c);
        timestamp = std::chrono::high_resolution_clock::now();
    }
    
    size_t size() const { return data.size(); }
    T* ptr() { return data.data(); }
    const T* ptr() const { return data.data(); }
    
    // Get pixel value at (x, y, channel)
    T& at(int x, int y, int c = 0) {
        return data[(y * width + x) * channels + c];
    }
    
    const T& at(int x, int y, int c = 0) const {
        return data[(y * width + x) * channels + c];
    }
};

// Line scan strip (single scan line or accumulated lines)
struct ScanStrip {
    Image<byte_t> image;
    int strip_id;
    double physical_position;  // mm from start
    bool is_left_to_right;
    
    ScanStrip() : strip_id(0), physical_position(0.0), is_left_to_right(true) {}
};

// Deformation field
struct DeformationField {
    std::vector<float> dx;  // X displacement
    std::vector<float> dy;  // Y displacement
    int width;
    int height;
    
    DeformationField() : width(0), height(0) {}
    
    DeformationField(int w, int h) : width(w), height(h) {
        dx.resize(w * h, 0.0f);
        dy.resize(w * h, 0.0f);
    }
    
    void getDisplacement(int x, int y, float& out_dx, float& out_dy) const {
        int idx = y * width + x;
        out_dx = dx[idx];
        out_dy = dy[idx];
    }
    
    void setDisplacement(int x, int y, float in_dx, float in_dy) {
        int idx = y * width + x;
        dx[idx] = in_dx;
        dy[idx] = in_dy;
    }
};

// Registration result
struct RegistrationResult {
    DeformationField deformation;
    double metric_value;
    int iterations;
    double elapsed_time_ms;
    bool success;
    std::string error_message;
    
    RegistrationResult() 
        : metric_value(0.0), iterations(0), elapsed_time_ms(0.0), success(false) {}
};

// Camera configuration
struct CameraConfig {
    int width;
    int height;
    int frequency_hz;
    int bit_depth;
    double pixel_size_mm;
    double fov_width_mm;
    
    CameraConfig() 
        : width(4096), height(1), frequency_hz(10000), 
          bit_depth(8), pixel_size_mm(0.010256), fov_width_mm(42.0) {}
};

// Scanning parameters
struct ScanningParams {
    double max_length_mm;
    double strip_width_mm;
    int overlap_pixels;
    bool bidirectional;
    
    ScanningParams() 
        : max_length_mm(1800.0), strip_width_mm(42.0), 
          overlap_pixels(100), bidirectional(true) {}
};

// Registration parameters
struct RegistrationParams {
    int pyramid_levels;
    std::vector<int> pyramid_schedule;
    int bspline_grid_spacing;
    int max_iterations;
    std::string optimizer_type;
    std::string metric_type;
    double sampling_percentage;
    
    RegistrationParams() 
        : pyramid_levels(5), pyramid_schedule({8, 4, 2, 1, 1}),
          bspline_grid_spacing(50), max_iterations(500),
          optimizer_type("LBFGS"), metric_type("MutualInformation"),
          sampling_percentage(0.25) {}
};

// GPU configuration
struct GPUConfig {
    int device_id;
    size_t max_vram_bytes;
    int tile_width;
    int tile_height;
    int tile_overlap;
    int batch_size;
    
    GPUConfig() 
        : device_id(0), max_vram_bytes(15ULL * 1024 * 1024 * 1024),
          tile_width(4096), tile_height(4096), tile_overlap(128),
          batch_size(4) {}
};

// Status codes
enum class StatusCode {
    SUCCESS = 0,
    ERROR_CAMERA_INIT,
    ERROR_CAMERA_START,
    ERROR_BUFFER_OVERFLOW,
    ERROR_STITCHING_FAILED,
    ERROR_REGISTRATION_FAILED,
    ERROR_GPU_OUT_OF_MEMORY,
    ERROR_PRINTER_COMMUNICATION,
    ERROR_INVALID_CONFIG,
    ERROR_FILE_IO,
    ERROR_UNKNOWN
};

// Logging levels
enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARNING = 2,
    ERROR = 3,
    CRITICAL = 4
};

} // namespace alinify

#endif // ALINIFY_COMMON_TYPES_H
