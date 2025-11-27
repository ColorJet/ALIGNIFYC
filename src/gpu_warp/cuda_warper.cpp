#include "alinify/gpu_warp/cuda_warper.h"
#include "alinify/common/logger.h"
#include <torch/torch.h>

namespace alinify {
namespace gpu_warp {

CudaWarper::CudaWarper()
    : device_(torch::kCPU)
    , initialized_(false)
    , interpolation_mode_("bilinear") {
}

CudaWarper::~CudaWarper() = default;

StatusCode CudaWarper::initialize(const GPUConfig& config) {
    LOG_INFO("Initializing CUDA warper...");
    
    config_ = config;
    
    if (!torch::cuda::is_available()) {
        LOG_ERROR("CUDA is not available");
        return StatusCode::ERROR_INVALID_CONFIG;
    }
    
    if (config_.device_id >= torch::cuda::device_count()) {
        LOG_ERROR("Invalid GPU device ID: ", config_.device_id);
        return StatusCode::ERROR_INVALID_CONFIG;
    }
    
    device_ = torch::Device(torch::kCUDA, config_.device_id);
    torch::cuda::set_device(config_.device_id);
    
    LOG_INFO("CUDA warper initialized on GPU ", config_.device_id);
    LOG_INFO("GPU: ", torch::cuda::get_device_name(config_.device_id));
    
    auto mem_info = getMemoryInfo();
    LOG_INFO("GPU Memory: ", mem_info.total_bytes / (1024*1024*1024), " GB");
    
    initialized_ = true;
    return StatusCode::SUCCESS;
}

StatusCode CudaWarper::warpImage(const Image<byte_t>& input,
                                 const DeformationField& deformation,
                                 Image<byte_t>& output) {
    
    if (!initialized_) {
        LOG_ERROR("CUDA warper not initialized");
        return StatusCode::ERROR_INVALID_CONFIG;
    }
    
    // Check if image is too large for direct processing
    size_t image_size_bytes = static_cast<size_t>(input.width) * input.height * 
                              input.channels * sizeof(float);
    
    auto mem_info = getMemoryInfo();
    
    if (image_size_bytes * 3 > mem_info.free_bytes) {  // Need 3x for input, output, grid
        LOG_INFO("Image too large for direct processing, using tiled approach");
        return warpImageTiled(input, deformation, output);
    }
    
    try {
        LOG_DEBUG("Warping image: ", input.width, "x", input.height, 
                 " channels=", input.channels);
        
        // Convert image to tensor [C, H, W]
        torch::Tensor input_tensor = imageToTensor(input).to(device_);
        
        // Convert deformation field to tensor
        torch::Tensor deformation_tensor = deformationToTensor(deformation).to(device_);
        
        // Create sampling grid
        torch::Tensor grid = createSamplingGrid(input.height, input.width, 
                                               deformation_tensor);
        
        // Apply grid sampling (warping)
        torch::Tensor output_tensor;
        
        if (interpolation_mode_ == "nearest") {
            output_tensor = torch::grid_sampler(
                input_tensor.unsqueeze(0),  // Add batch dimension
                grid.unsqueeze(0),
                0,  // Nearest interpolation
                0,  // Zeros padding
                false);
        } else {  // bilinear
            output_tensor = torch::grid_sampler(
                input_tensor.unsqueeze(0),
                grid.unsqueeze(0),
                1,  // Bilinear interpolation
                0,  // Zeros padding
                true);
        }
        
        output_tensor = output_tensor.squeeze(0);  // Remove batch dimension
        
        // Convert back to image
        tensorToImage(output_tensor, output);
        
        LOG_DEBUG("Warping completed successfully");
        return StatusCode::SUCCESS;
        
    } catch (const c10::Error& e) {
        LOG_ERROR("LibTorch error during warping: ", e.what());
        return StatusCode::ERROR_GPU_OUT_OF_MEMORY;
    }
}

StatusCode CudaWarper::warpImageTiled(const Image<byte_t>& input,
                                      const DeformationField& deformation,
                                      Image<byte_t>& output) {
    
    LOG_INFO("Starting tiled warping for large image");
    
    // Generate tiles
    auto tiles = generateTiles(input.width, input.height);
    LOG_INFO("Processing ", tiles.size(), " tiles");
    
    // Initialize output image
    output = Image<byte_t>(input.width, input.height, input.channels, input.bit_depth);
    
    try {
        torch::Tensor input_tensor = imageToTensor(input).to(device_);
        torch::Tensor deformation_tensor = deformationToTensor(deformation).to(device_);
        
        for (size_t i = 0; i < tiles.size(); ++i) {
            const auto& tile = tiles[i];
            
            LOG_DEBUG("Processing tile ", i+1, "/", tiles.size(), 
                     " at (", tile.x, ",", tile.y, ")");
            
            // Extract tile region
            torch::Tensor tile_input = input_tensor.index({
                torch::indexing::Slice(),
                torch::indexing::Slice(tile.y, tile.y + tile.height),
                torch::indexing::Slice(tile.x, tile.x + tile.width)
            });
            
            // Extract deformation for tile
            torch::Tensor tile_deform = deformation_tensor.index({
                torch::indexing::Slice(tile.y, tile.y + tile.height),
                torch::indexing::Slice(tile.x, tile.x + tile.width),
                torch::indexing::Slice()
            });
            
            // Create grid for tile
            torch::Tensor tile_grid = createSamplingGrid(tile.height, tile.width, 
                                                         tile_deform);
            
            // Warp tile
            torch::Tensor tile_output = torch::grid_sampler(
                tile_input.unsqueeze(0),
                tile_grid.unsqueeze(0),
                1, 0, true).squeeze(0);
            
            // Copy tile to output (handle overlap blending)
            // For simplicity, direct copy here
            tile_output = tile_output.to(torch::kCPU);
            
            auto tile_accessor = tile_output.accessor<float, 3>();
            
            for (int c = 0; c < input.channels; ++c) {
                for (int y = 0; y < tile.height; ++y) {
                    for (int x = 0; x < tile.width; ++x) {
                        int out_x = tile.x + x;
                        int out_y = tile.y + y;
                        
                        if (out_x < output.width && out_y < output.height) {
                            float val = tile_accessor[c][y][x];
                            output.at(out_x, out_y, c) = 
                                static_cast<byte_t>(std::clamp(val * 255.0f, 0.0f, 255.0f));
                        }
                    }
                }
            }
        }
        
        LOG_INFO("Tiled warping completed successfully");
        return StatusCode::SUCCESS;
        
    } catch (const c10::Error& e) {
        LOG_ERROR("LibTorch error during tiled warping: ", e.what());
        return StatusCode::ERROR_GPU_OUT_OF_MEMORY;
    }
}

bool CudaWarper::isGPUAvailable() {
    return torch::cuda::is_available();
}

CudaWarper::GPUMemoryInfo CudaWarper::getMemoryInfo() const {
    GPUMemoryInfo info;
    
    if (device_.is_cuda()) {
        c10::cuda::CUDACachingAllocator::DeviceStats stats = 
            c10::cuda::CUDACachingAllocator::getDeviceStats(device_.index());
        
        info.used_bytes = stats.allocated_bytes[0].current;
        
        // Get total memory
        size_t free_mem, total_mem;
        cudaMemGetInfo(&free_mem, &total_mem);
        
        info.total_bytes = total_mem;
        info.free_bytes = free_mem;
    }
    
    return info;
}

void CudaWarper::setInterpolationMode(const std::string& mode) {
    interpolation_mode_ = mode;
}

std::vector<CudaWarper::Tile> CudaWarper::generateTiles(int width, int height) const {
    std::vector<Tile> tiles;
    
    const int tile_w = config_.tile_width;
    const int tile_h = config_.tile_height;
    const int overlap = config_.tile_overlap;
    
    for (int y = 0; y < height; y += (tile_h - overlap)) {
        for (int x = 0; x < width; x += (tile_w - overlap)) {
            Tile tile;
            tile.x = x;
            tile.y = y;
            tile.width = std::min(tile_w, width - x);
            tile.height = std::min(tile_h, height - y);
            tile.overlap = overlap;
            
            tiles.push_back(tile);
        }
    }
    
    return tiles;
}

torch::Tensor CudaWarper::imageToTensor(const Image<byte_t>& image) {
    // Convert [H, W, C] byte image to [C, H, W] float tensor [0, 1]
    auto options = torch::TensorOptions().dtype(torch::kFloat32);
    torch::Tensor tensor = torch::zeros({image.channels, image.height, image.width}, options);
    
    auto accessor = tensor.accessor<float, 3>();
    
    for (int c = 0; c < image.channels; ++c) {
        for (int y = 0; y < image.height; ++y) {
            for (int x = 0; x < image.width; ++x) {
                accessor[c][y][x] = image.at(x, y, c) / 255.0f;
            }
        }
    }
    
    return tensor;
}

void CudaWarper::tensorToImage(const torch::Tensor& tensor, Image<byte_t>& image) {
    // Convert [C, H, W] float tensor to [H, W, C] byte image
    tensor = tensor.to(torch::kCPU);
    
    auto accessor = tensor.accessor<float, 3>();
    int C = accessor.size(0);
    int H = accessor.size(1);
    int W = accessor.size(2);
    
    image = Image<byte_t>(W, H, C, 8);
    
    for (int c = 0; c < C; ++c) {
        for (int y = 0; y < H; ++y) {
            for (int x = 0; x < W; ++x) {
                float val = accessor[c][y][x] * 255.0f;
                image.at(x, y, c) = static_cast<byte_t>(std::clamp(val, 0.0f, 255.0f));
            }
        }
    }
}

torch::Tensor CudaWarper::deformationToTensor(const DeformationField& field) {
    // Convert to [H, W, 2] tensor
    auto options = torch::TensorOptions().dtype(torch::kFloat32);
    torch::Tensor tensor = torch::zeros({field.height, field.width, 2}, options);
    
    auto accessor = tensor.accessor<float, 3>();
    
    for (int y = 0; y < field.height; ++y) {
        for (int x = 0; x < field.width; ++x) {
            float dx, dy;
            field.getDisplacement(x, y, dx, dy);
            accessor[y][x][0] = dx;
            accessor[y][x][1] = dy;
        }
    }
    
    return tensor;
}

torch::Tensor CudaWarper::createSamplingGrid(int height, int width,
                                             const torch::Tensor& deformation) {
    // Create normalized grid [-1, 1]
    auto options = torch::TensorOptions().dtype(torch::kFloat32).device(device_);
    
    // Base grid
    torch::Tensor y_coords = torch::linspace(-1, 1, height, options);
    torch::Tensor x_coords = torch::linspace(-1, 1, width, options);
    
    auto meshgrid = torch::meshgrid({y_coords, x_coords}, "ij");
    torch::Tensor grid_y = meshgrid[0];
    torch::Tensor grid_x = meshgrid[1];
    
    // Add deformation (normalize to [-1, 1] range)
    torch::Tensor deform_normalized = deformation.clone();
    deform_normalized.index_put_({torch::indexing::Slice(), torch::indexing::Slice(), 0},
                                  deformation.index({torch::indexing::Slice(), torch::indexing::Slice(), 0}) / (width / 2.0));
    deform_normalized.index_put_({torch::indexing::Slice(), torch::indexing::Slice(), 1},
                                  deformation.index({torch::indexing::Slice(), torch::indexing::Slice(), 1}) / (height / 2.0));
    
    // Combine: [H, W, 2] where last dim is [x, y]
    torch::Tensor grid = torch::stack({
        grid_x + deform_normalized.index({torch::indexing::Slice(), torch::indexing::Slice(), 0}),
        grid_y + deform_normalized.index({torch::indexing::Slice(), torch::indexing::Slice(), 1})
    }, -1);
    
    return grid;
}

} // namespace gpu_warp
} // namespace alinify
