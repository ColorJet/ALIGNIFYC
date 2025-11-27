#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <iostream>

#include "alinify/common/types.h"
#include "alinify/camera/gidel_camera.h"
#include "alinify/stitching/strip_stitcher.h"
#include "alinify/preprocessing/image_processor.h"
// #include "alinify/registration/elastix_wrapper.h"  // Disabled until ITK is available
// #include "alinify/gpu_warp/cuda_warper.h"  // Disabled until CUDA is available
#include "alinify/printer/printer_interface.h"

namespace py = pybind11;

using namespace alinify;

// Helper to convert numpy array to Image
template<typename T>
Image<T> numpy_to_image(py::array_t<T> arr) {
    auto buf = arr.request();
    
    if (buf.ndim < 2 || buf.ndim > 3) {
        throw std::runtime_error("Image must be 2D or 3D array");
    }
    
    int height = buf.shape[0];
    int width = buf.shape[1];
    int channels = (buf.ndim == 3) ? buf.shape[2] : 1;
    
    Image<T> img(width, height, channels, sizeof(T) * 8);
    std::memcpy(img.ptr(), buf.ptr, img.size() * sizeof(T));
    
    return img;
}

// Helper to convert Image to numpy array
template<typename T>
py::array_t<T> image_to_numpy(const Image<T>& img) {
    if (img.channels == 1) {
        return py::array_t<T>({img.height, img.width}, img.ptr());
    } else {
        return py::array_t<T>({img.height, img.width, img.channels}, img.ptr());
    }
}

PYBIND11_MODULE(alinify_bindings, m) {
    m.doc() = "Alinify C++ bindings for Python";
    
    // Enums
    py::enum_<StatusCode>(m, "StatusCode")
        .value("SUCCESS", StatusCode::SUCCESS)
        .value("ERROR_CAMERA_INIT", StatusCode::ERROR_CAMERA_INIT)
        .value("ERROR_CAMERA_START", StatusCode::ERROR_CAMERA_START)
        .value("ERROR_STITCHING_FAILED", StatusCode::ERROR_STITCHING_FAILED)
        .value("ERROR_REGISTRATION_FAILED", StatusCode::ERROR_REGISTRATION_FAILED)
        .value("ERROR_GPU_OUT_OF_MEMORY", StatusCode::ERROR_GPU_OUT_OF_MEMORY)
        .value("ERROR_PRINTER_COMMUNICATION", StatusCode::ERROR_PRINTER_COMMUNICATION)
        .export_values();
    
    // Configuration structures
    py::class_<CameraConfig>(m, "CameraConfig")
        .def(py::init<>())
        .def_readwrite("width", &CameraConfig::width)
        .def_readwrite("height", &CameraConfig::height)
        .def_readwrite("frequency_hz", &CameraConfig::frequency_hz)
        .def_readwrite("bit_depth", &CameraConfig::bit_depth)
        .def_readwrite("pixel_size_mm", &CameraConfig::pixel_size_mm)
        .def_readwrite("fov_width_mm", &CameraConfig::fov_width_mm);
    
    py::class_<ScanningParams>(m, "ScanningParams")
        .def(py::init<>())
        .def_readwrite("max_length_mm", &ScanningParams::max_length_mm)
        .def_readwrite("strip_width_mm", &ScanningParams::strip_width_mm)
        .def_readwrite("overlap_pixels", &ScanningParams::overlap_pixels)
        .def_readwrite("bidirectional", &ScanningParams::bidirectional);
    
    py::class_<RegistrationParams>(m, "RegistrationParams")
        .def(py::init<>())
        .def_readwrite("pyramid_levels", &RegistrationParams::pyramid_levels)
        .def_readwrite("bspline_grid_spacing", &RegistrationParams::bspline_grid_spacing)
        .def_readwrite("max_iterations", &RegistrationParams::max_iterations);
    
    py::class_<GPUConfig>(m, "GPUConfig")
        .def(py::init<>())
        .def_readwrite("device_id", &GPUConfig::device_id)
        .def_readwrite("tile_width", &GPUConfig::tile_width)
        .def_readwrite("tile_height", &GPUConfig::tile_height);
    
    // Camera statistics
    py::class_<camera::ICameraInterface::Statistics>(m, "CameraStatistics")
        .def(py::init<>())
        .def_readonly("frames_received", &camera::ICameraInterface::Statistics::frames_received)
        .def_readonly("frames_dropped", &camera::ICameraInterface::Statistics::frames_dropped)
        .def_readonly("fps", &camera::ICameraInterface::Statistics::fps)
        .def_readonly("temperature", &camera::ICameraInterface::Statistics::temperature);
    
    // Camera interface
    py::class_<camera::GidelCamera>(m, "GidelCamera")
        .def(py::init<>())
        .def("initialize", &camera::GidelCamera::initialize)
        .def("start_acquisition", &camera::GidelCamera::startAcquisition)
        .def("stop_acquisition", &camera::GidelCamera::stopAcquisition)
        .def("is_acquiring", &camera::GidelCamera::isAcquiring)
        .def("set_trigger_mode", &camera::GidelCamera::setTriggerMode)
        .def("set_config_file", &camera::GidelCamera::setConfigFile)
        .def("get_device_info", &camera::GidelCamera::getDeviceInfo)
        .def("set_image_callback", [](camera::GidelCamera& cam, py::function callback) {
            // Wrapper to convert C++ callback to Python
            cam.setImageCallback([callback](const ScanStrip& strip) {
                try {
                    py::gil_scoped_acquire acquire;  // Acquire GIL for Python call
                    
                    // Convert image data to numpy array
                    py::array_t<byte_t> np_array;
                    if (strip.image.channels == 1) {
                        np_array = py::array_t<byte_t>(
                            {strip.image.height, strip.image.width},
                            {strip.image.width * sizeof(byte_t), sizeof(byte_t)},
                            strip.image.ptr()
                        );
                    } else {
                        np_array = py::array_t<byte_t>(
                            {strip.image.height, strip.image.width, strip.image.channels},
                            {strip.image.width * strip.image.channels * sizeof(byte_t), 
                             strip.image.channels * sizeof(byte_t), 
                             sizeof(byte_t)},
                            strip.image.ptr()
                        );
                    }
                    
                    // Make a copy so Python owns the data
                    py::array_t<byte_t> np_copy = py::array_t<byte_t>(np_array.request());
                    
                    // Call Python callback with numpy array, strip_id, and position
                    callback(np_copy, strip.strip_id, strip.physical_position);
                    
                } catch (const py::error_already_set& e) {
                    // Python exception in callback
                    std::cerr << "Python callback error: " << e.what() << std::endl;
                } catch (const std::exception& e) {
                    std::cerr << "Callback error: " << e.what() << std::endl;
                }
            });
        }, py::arg("callback"),
        "Set callback function that receives (image_array, strip_id, position_mm)")
        .def("get_statistics", &camera::GidelCamera::getStatistics,
        "Get acquisition statistics (frames captured, FPS, etc.)");
    
    // Stitcher
    py::class_<stitching::StripStitcher>(m, "StripStitcher")
        .def(py::init<>())
        .def("initialize", &stitching::StripStitcher::initialize)
        .def("reset", &stitching::StripStitcher::reset)
        .def("set_correlation_threshold", &stitching::StripStitcher::setCorrelationThreshold)
        .def("set_blending_enabled", &stitching::StripStitcher::setBlendingEnabled);
    
    // Image processor
    py::class_<preprocessing::ImageProcessor>(m, "ImageProcessor")
        .def(py::init<>())
        .def_static("gaussian_blur", [](py::array_t<byte_t> input, double sigma) {
            auto img_in = numpy_to_image(input);
            Image<byte_t> img_out;
            preprocessing::ImageProcessor::gaussianBlur(img_in, img_out, sigma);
            return image_to_numpy(img_out);
        })
        .def_static("normalize", [](py::array_t<byte_t> input) {
            auto img_in = numpy_to_image(input);
            Image<byte_t> img_out;
            preprocessing::ImageProcessor::normalize(img_in, img_out);
            return image_to_numpy(img_out);
        });
    
    // Registration - Disabled until ITK/Elastix is available
    /*
    py::class_<registration::ElastixWrapper>(m, "ElastixWrapper")
        .def(py::init<>())
        .def("initialize", &registration::ElastixWrapper::initialize)
        .def("load_transform_parameters", &registration::ElastixWrapper::loadTransformParameters)
        .def("save_transform_parameters", &registration::ElastixWrapper::saveTransformParameters);
    */
    
    // GPU Warper - Disabled until CUDA is available
    /*
    py::class_<gpu_warp::CudaWarper>(m, "CudaWarper")
        .def(py::init<>())
        .def("initialize", &gpu_warp::CudaWarper::initialize)
        .def_static("is_gpu_available", &gpu_warp::CudaWarper::isGPUAvailable)
        .def("set_interpolation_mode", &gpu_warp::CudaWarper::setInterpolationMode);
    */
    
    // Printer interface
    py::class_<printer::PrinterInterface>(m, "PrinterInterface")
        .def(py::init<>())
        .def("initialize", &printer::PrinterInterface::initialize)
        .def("is_ready", &printer::PrinterInterface::isReady)
        .def("close", &printer::PrinterInterface::close);
}
