#ifndef ALINIFY_GPU_WARP_CUDA_WARPER_H
#define ALINIFY_GPU_WARP_CUDA_WARPER_H

#include "alinify/common/types.h"
#include <torch/torch.h>

namespace alinify {
namespace gpu_warp {

/**
 * @brief GPU-accelerated image warping using LibTorch/CUDA
 * 
 * Applies deformation fields to large RGB images efficiently
 * using GPU with memory-efficient tiling for 1000+ megapixel images
 */
class CudaWarper {
public:
    CudaWarper();
    ~CudaWarper();
    
    /**
     * @brief Initialize CUDA warper with GPU configuration
     */
    StatusCode initialize(const GPUConfig& config);
    
    /**
     * @brief Warp RGB image using deformation field
     * @param input Input RGB image (large, e.g., 1000MP)
     * @param deformation Deformation field from registration
     * @param output Warped output image
     * @return StatusCode indicating success or failure
     */
    StatusCode warpImage(const Image<byte_t>& input,
                        const DeformationField& deformation,
                        Image<byte_t>& output);
    
    /**
     * @brief Warp with tiling for very large images
     */
    StatusCode warpImageTiled(const Image<byte_t>& input,
                             const DeformationField& deformation,
                             Image<byte_t>& output);
    
    /**
     * @brief Check if GPU is available
     */
    static bool isGPUAvailable();
    
    /**
     * @brief Get GPU memory usage
     */
    struct GPUMemoryInfo {
        size_t total_bytes;
        size_t used_bytes;
        size_t free_bytes;
    };
    
    GPUMemoryInfo getMemoryInfo() const;
    
    /**
     * @brief Set interpolation mode
     */
    void setInterpolationMode(const std::string& mode);
    
private:
    // Tile processing
    struct Tile {
        int x, y, width, height;
        int overlap;
    };
    
    std::vector<Tile> generateTiles(int width, int height) const;
    
    StatusCode warpTile(const torch::Tensor& input_tensor,
                       const torch::Tensor& deformation_tensor,
                       torch::Tensor& output_tensor,
                       const Tile& tile);
    
    // Type conversions
    torch::Tensor imageToTensor(const Image<byte_t>& image);
    void tensorToImage(const torch::Tensor& tensor, Image<byte_t>& image);
    torch::Tensor deformationToTensor(const DeformationField& field);
    
    // CUDA operations
    torch::Tensor createSamplingGrid(int height, int width,
                                     const torch::Tensor& deformation);
    
    GPUConfig config_;
    torch::Device device_;
    bool initialized_;
    std::string interpolation_mode_;
};

} // namespace gpu_warp
} // namespace alinify

#endif // ALINIFY_GPU_WARP_CUDA_WARPER_H
