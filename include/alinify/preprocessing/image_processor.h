#ifndef ALINIFY_PREPROCESSING_IMAGE_PROCESSOR_H
#define ALINIFY_PREPROCESSING_IMAGE_PROCESSOR_H

#include "alinify/common/types.h"
#include <vector>
#include <string>

namespace alinify {
namespace preprocessing {

/**
 * @brief Image preprocessing pipeline
 * 
 * Provides filtering, normalization, and enhancement operations
 * to prepare images for registration
 */
class ImageProcessor {
public:
    ImageProcessor();
    ~ImageProcessor();
    
    /**
     * @brief Apply Gaussian blur
     */
    static StatusCode gaussianBlur(const Image<byte_t>& input,
                                   Image<byte_t>& output,
                                   double sigma);
    
    /**
     * @brief Apply bilateral filter
     */
    static StatusCode bilateralFilter(const Image<byte_t>& input,
                                      Image<byte_t>& output,
                                      double spatial_sigma,
                                      double intensity_sigma);
    
    /**
     * @brief Apply median filter
     */
    static StatusCode medianFilter(const Image<byte_t>& input,
                                   Image<byte_t>& output,
                                   int kernel_size);
    
    /**
     * @brief Histogram equalization
     */
    static StatusCode histogramEqualization(const Image<byte_t>& input,
                                           Image<byte_t>& output);
    
    /**
     * @brief Histogram matching
     */
    static StatusCode histogramMatching(const Image<byte_t>& input,
                                       const Image<byte_t>& reference,
                                       Image<byte_t>& output);
    
    /**
     * @brief Normalize to [0, 255] range
     */
    static StatusCode normalize(const Image<byte_t>& input,
                               Image<byte_t>& output);
    
    /**
     * @brief Unsharp masking for edge enhancement
     */
    static StatusCode unsharpMask(const Image<byte_t>& input,
                                 Image<byte_t>& output,
                                 double sigma,
                                 double amount);
    
    /**
     * @brief Apply full preprocessing pipeline
     */
    struct PreprocessingConfig {
        bool enable_gaussian;
        double gaussian_sigma;
        bool enable_bilateral;
        double bilateral_spatial_sigma;
        double bilateral_intensity_sigma;
        bool enable_histogram_eq;
        bool enable_normalize;
    };
    
    static StatusCode applyPipeline(const Image<byte_t>& input,
                                   Image<byte_t>& output,
                                   const PreprocessingConfig& config);
};

} // namespace preprocessing
} // namespace alinify

#endif // ALINIFY_PREPROCESSING_IMAGE_PROCESSOR_H
