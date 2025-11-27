#include "alinify/preprocessing/image_processor.h"
#include "alinify/common/logger.h"
#include <opencv2/opencv.hpp>

namespace alinify {
namespace preprocessing {

ImageProcessor::ImageProcessor() = default;
ImageProcessor::~ImageProcessor() = default;

StatusCode ImageProcessor::gaussianBlur(const Image<byte_t>& input,
                                        Image<byte_t>& output,
                                        double sigma) {
    try {
        cv::Mat input_mat(input.height, input.width, CV_8UC1, 
                         const_cast<byte_t*>(input.ptr()));
        cv::Mat output_mat;
        
        int kernel_size = static_cast<int>(6 * sigma + 1);
        if (kernel_size % 2 == 0) kernel_size++;
        
        cv::GaussianBlur(input_mat, output_mat, cv::Size(kernel_size, kernel_size), sigma);
        
        output = Image<byte_t>(output_mat.cols, output_mat.rows, 1, 8);
        std::memcpy(output.ptr(), output_mat.data, output.size());
        
        return StatusCode::SUCCESS;
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in gaussianBlur: ", e.what());
        return StatusCode::ERROR_UNKNOWN;
    }
}

StatusCode ImageProcessor::bilateralFilter(const Image<byte_t>& input,
                                           Image<byte_t>& output,
                                           double spatial_sigma,
                                           double intensity_sigma) {
    try {
        cv::Mat input_mat(input.height, input.width, CV_8UC1,
                         const_cast<byte_t*>(input.ptr()));
        cv::Mat output_mat;
        
        int d = static_cast<int>(2 * spatial_sigma + 1);
        cv::bilateralFilter(input_mat, output_mat, d, intensity_sigma, spatial_sigma);
        
        output = Image<byte_t>(output_mat.cols, output_mat.rows, 1, 8);
        std::memcpy(output.ptr(), output_mat.data, output.size());
        
        return StatusCode::SUCCESS;
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in bilateralFilter: ", e.what());
        return StatusCode::ERROR_UNKNOWN;
    }
}

StatusCode ImageProcessor::medianFilter(const Image<byte_t>& input,
                                        Image<byte_t>& output,
                                        int kernel_size) {
    try {
        cv::Mat input_mat(input.height, input.width, CV_8UC1,
                         const_cast<byte_t*>(input.ptr()));
        cv::Mat output_mat;
        
        if (kernel_size % 2 == 0) kernel_size++;
        cv::medianBlur(input_mat, output_mat, kernel_size);
        
        output = Image<byte_t>(output_mat.cols, output_mat.rows, 1, 8);
        std::memcpy(output.ptr(), output_mat.data, output.size());
        
        return StatusCode::SUCCESS;
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in medianFilter: ", e.what());
        return StatusCode::ERROR_UNKNOWN;
    }
}

StatusCode ImageProcessor::histogramEqualization(const Image<byte_t>& input,
                                                 Image<byte_t>& output) {
    try {
        cv::Mat input_mat(input.height, input.width, CV_8UC1,
                         const_cast<byte_t*>(input.ptr()));
        cv::Mat output_mat;
        
        cv::equalizeHist(input_mat, output_mat);
        
        output = Image<byte_t>(output_mat.cols, output_mat.rows, 1, 8);
        std::memcpy(output.ptr(), output_mat.data, output.size());
        
        return StatusCode::SUCCESS;
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in histogramEqualization: ", e.what());
        return StatusCode::ERROR_UNKNOWN;
    }
}

StatusCode ImageProcessor::histogramMatching(const Image<byte_t>& input,
                                             const Image<byte_t>& reference,
                                             Image<byte_t>& output) {
    // TODO: Implement using ITK
    LOG_WARNING("histogramMatching not yet implemented");
    output = input;
    return StatusCode::SUCCESS;
}

StatusCode ImageProcessor::normalize(const Image<byte_t>& input,
                                     Image<byte_t>& output) {
    try {
        cv::Mat input_mat(input.height, input.width, CV_8UC1,
                         const_cast<byte_t*>(input.ptr()));
        cv::Mat output_mat;
        
        cv::normalize(input_mat, output_mat, 0, 255, cv::NORM_MINMAX);
        
        output = Image<byte_t>(output_mat.cols, output_mat.rows, 1, 8);
        std::memcpy(output.ptr(), output_mat.data, output.size());
        
        return StatusCode::SUCCESS;
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in normalize: ", e.what());
        return StatusCode::ERROR_UNKNOWN;
    }
}

StatusCode ImageProcessor::unsharpMask(const Image<byte_t>& input,
                                       Image<byte_t>& output,
                                       double sigma,
                                       double amount) {
    try {
        cv::Mat input_mat(input.height, input.width, CV_8UC1,
                         const_cast<byte_t*>(input.ptr()));
        cv::Mat blurred, mask, output_mat;
        
        int kernel_size = static_cast<int>(6 * sigma + 1);
        if (kernel_size % 2 == 0) kernel_size++;
        
        cv::GaussianBlur(input_mat, blurred, cv::Size(kernel_size, kernel_size), sigma);
        cv::subtract(input_mat, blurred, mask);
        cv::addWeighted(input_mat, 1.0, mask, amount, 0, output_mat);
        
        output = Image<byte_t>(output_mat.cols, output_mat.rows, 1, 8);
        std::memcpy(output.ptr(), output_mat.data, output.size());
        
        return StatusCode::SUCCESS;
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in unsharpMask: ", e.what());
        return StatusCode::ERROR_UNKNOWN;
    }
}

StatusCode ImageProcessor::applyPipeline(const Image<byte_t>& input,
                                         Image<byte_t>& output,
                                         const PreprocessingConfig& config) {
    Image<byte_t> temp = input;
    
    if (config.enable_gaussian) {
        if (gaussianBlur(temp, temp, config.gaussian_sigma) != StatusCode::SUCCESS) {
            return StatusCode::ERROR_UNKNOWN;
        }
    }
    
    if (config.enable_bilateral) {
        if (bilateralFilter(temp, temp, config.bilateral_spatial_sigma,
                           config.bilateral_intensity_sigma) != StatusCode::SUCCESS) {
            return StatusCode::ERROR_UNKNOWN;
        }
    }
    
    if (config.enable_histogram_eq) {
        if (histogramEqualization(temp, temp) != StatusCode::SUCCESS) {
            return StatusCode::ERROR_UNKNOWN;
        }
    }
    
    if (config.enable_normalize) {
        if (normalize(temp, temp) != StatusCode::SUCCESS) {
            return StatusCode::ERROR_UNKNOWN;
        }
    }
    
    output = temp;
    return StatusCode::SUCCESS;
}

} // namespace preprocessing
} // namespace alinify
