#ifndef ALINIFY_REGISTRATION_ELASTIX_WRAPPER_H
#define ALINIFY_REGISTRATION_ELASTIX_WRAPPER_H

#include "alinify/common/types.h"
#include <string>
#include <map>

namespace alinify {
namespace registration {

/**
 * @brief Wrapper for Elastix/ITK registration
 * 
 * Provides:
 * - Multi-resolution pyramid registration
 * - B-spline transformation
 * - Multiple optimizers and metrics
 * - Parameter map generation
 */
class ElastixWrapper {
public:
    ElastixWrapper();
    ~ElastixWrapper();
    
    /**
     * @brief Initialize with registration parameters
     */
    StatusCode initialize(const RegistrationParams& params);
    
    /**
     * @brief Register moving image to fixed image
     * @param fixed Fixed (reference) image
     * @param moving Moving (scan) image
     * @param result Output registration result with deformation field
     * @return StatusCode indicating success or failure
     */
    StatusCode registerImages(const Image<byte_t>& fixed,
                             const Image<byte_t>& moving,
                             RegistrationResult& result);
    
    /**
     * @brief Load transform parameters from file
     */
    StatusCode loadTransformParameters(const std::string& filename);
    
    /**
     * @brief Save transform parameters to file
     */
    StatusCode saveTransformParameters(const std::string& filename) const;
    
    /**
     * @brief Apply saved transformation to new image
     */
    StatusCode applyTransform(const Image<byte_t>& input,
                             Image<byte_t>& output);
    
    /**
     * @brief Set custom parameter
     */
    void setParameter(const std::string& key, const std::string& value);
    
    /**
     * @brief Get current parameter map
     */
    std::map<std::string, std::string> getParameterMap() const;
    
private:
    // Generate Elastix parameter map
    void generateParameterMaps();
    
    // Convert between our types and ITK types
    template<typename TPixel>
    void convertToITKImage(const Image<byte_t>& input, void* itk_image);
    
    template<typename TPixel>
    void convertFromITKImage(void* itk_image, Image<byte_t>& output);
    
    RegistrationParams params_;
    std::map<std::string, std::string> parameter_map_;
    bool initialized_;
    
    // Opaque pointers to avoid ITK headers in interface
    void* elastix_object_;
    void* transform_parameters_;
};

} // namespace registration
} // namespace alinify

#endif // ALINIFY_REGISTRATION_ELASTIX_WRAPPER_H
