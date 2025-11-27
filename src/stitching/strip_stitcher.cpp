#include "alinify/stitching/strip_stitcher.h"
#include "alinify/common/logger.h"
#include <opencv2/opencv.hpp>
#include <cmath>
#include <algorithm>

namespace alinify {
namespace stitching {

StripStitcher::StripStitcher()
    : min_correlation_(0.7)
    , blending_enabled_(true)
    , current_height_(0)
    , initialized_(false) {
}

StripStitcher::~StripStitcher() = default;

StatusCode StripStitcher::initialize(const ScanningParams& params) {
    LOG_INFO("Initializing strip stitcher...");
    
    params_ = params;
    initialized_ = true;
    
    LOG_INFO("Strip stitcher initialized: max_length=", params_.max_length_mm,
             "mm, overlap=", params_.overlap_pixels, "px");
    
    return StatusCode::SUCCESS;
}

StatusCode StripStitcher::addStrip(const ScanStrip& strip) {
    if (!initialized_) {
        LOG_ERROR("Stitcher not initialized");
        return StatusCode::ERROR_INVALID_CONFIG;
    }
    
    LOG_DEBUG("Adding strip ", strip.strip_id, " at position ", 
              strip.physical_position, "mm, direction: ",
              strip.is_left_to_right ? "L->R" : "R->L");
    
    // First strip - initialize stitched image
    if (strips_.empty()) {
        stitched_image_ = strip.image;
        current_height_ = strip.image.height;
        strips_.push_back(strip);
        return StatusCode::SUCCESS;
    }
    
    // Get previous strip for alignment
    const auto& prev_strip = strips_.back();
    
    // Align current strip with previous
    AlignmentStats align_stats = alignStrips(prev_strip.image, strip.image);
    last_alignment_ = align_stats;
    
    if (!align_stats.success) {
        LOG_WARNING("Strip alignment failed for strip ", strip.strip_id,
                   " correlation: ", align_stats.correlation);
        return StatusCode::ERROR_STITCHING_FAILED;
    }
    
    LOG_DEBUG("Strip aligned: offset=(", align_stats.offset_x, ", ",
              align_stats.offset_y, "), correlation=", align_stats.correlation);
    
    // Expand stitched image if needed
    int new_height = current_height_ + strip.image.height - params_.overlap_pixels;
    
    if (new_height > stitched_image_.height) {
        Image<byte_t> expanded(stitched_image_.width, new_height, 
                               stitched_image_.channels, stitched_image_.bit_depth);
        
        // Copy existing data
        std::memcpy(expanded.ptr(), stitched_image_.ptr(), 
                   stitched_image_.size());
        
        stitched_image_ = std::move(expanded);
    }
    
    // Blend/copy new strip
    int insert_y = current_height_ - params_.overlap_pixels;
    
    if (blending_enabled_ && params_.overlap_pixels > 0) {
        blendOverlapRegion(stitched_image_, strip.image, 
                          static_cast<int>(align_stats.offset_x), insert_y);
    } else {
        // Simple copy
        const int copy_width = strip.image.width;
        const int copy_height = strip.image.height;
        
        for (int y = 0; y < copy_height; ++y) {
            int dst_y = insert_y + y;
            if (dst_y >= 0 && dst_y < stitched_image_.height) {
                std::memcpy(&stitched_image_.at(0, dst_y),
                           &strip.image.at(0, y),
                           copy_width * sizeof(byte_t));
            }
        }
    }
    
    current_height_ = new_height;
    strips_.push_back(strip);
    
    return StatusCode::SUCCESS;
}

Image<byte_t> StripStitcher::getStitchedImage() const {
    return stitched_image_;
}

void StripStitcher::reset() {
    strips_.clear();
    stitched_image_ = Image<byte_t>();
    current_height_ = 0;
    last_alignment_ = AlignmentStats{};
}

StripStitcher::AlignmentStats StripStitcher::getLastAlignmentStats() const {
    return last_alignment_;
}

StripStitcher::AlignmentStats StripStitcher::alignStrips(
    const Image<byte_t>& prev, const Image<byte_t>& current) {
    
    // Use phase correlation for sub-pixel accuracy
    return phaseCorrelation(prev, current);
}

StripStitcher::AlignmentStats StripStitcher::phaseCorrelation(
    const Image<byte_t>& img1, const Image<byte_t>& img2) {
    
    AlignmentStats stats;
    stats.success = false;
    
    try {
        // Convert to OpenCV Mat for processing
        cv::Mat mat1(img1.height, img1.width, CV_8UC1, 
                     const_cast<byte_t*>(img1.ptr()));
        cv::Mat mat2(img2.height, img2.width, CV_8UC1, 
                     const_cast<byte_t*>(img2.ptr()));
        
        // Extract overlap regions
        int overlap_height = std::min(params_.overlap_pixels, 
                                     std::min(img1.height, img2.height));
        
        cv::Mat overlap1 = mat1(cv::Rect(0, img1.height - overlap_height, 
                                        img1.width, overlap_height));
        cv::Mat overlap2 = mat2(cv::Rect(0, 0, img2.width, overlap_height));
        
        // Compute phase correlation
        cv::Point2d shift = cv::phaseCorrelate(overlap1, overlap2);
        
        // Compute correlation coefficient for validation
        cv::Mat result;
        cv::matchTemplate(overlap1, overlap2, result, cv::TM_CCORR_NORMED);
        
        double min_val, max_val;
        cv::minMaxLoc(result, &min_val, &max_val);
        
        stats.offset_x = shift.x;
        stats.offset_y = shift.y;
        stats.correlation = max_val;
        stats.success = (max_val >= min_correlation_);
        
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in phase correlation: ", e.what());
        stats.success = false;
    }
    
    return stats;
}

StripStitcher::AlignmentStats StripStitcher::templateMatching(
    const Image<byte_t>& img1, const Image<byte_t>& img2) {
    
    AlignmentStats stats;
    stats.success = false;
    
    try {
        cv::Mat mat1(img1.height, img1.width, CV_8UC1, 
                     const_cast<byte_t*>(img1.ptr()));
        cv::Mat mat2(img2.height, img2.width, CV_8UC1, 
                     const_cast<byte_t*>(img2.ptr()));
        
        // Extract overlap regions
        int overlap_height = std::min(params_.overlap_pixels, 
                                     std::min(img1.height, img2.height));
        
        cv::Mat templ = mat1(cv::Rect(0, img1.height - overlap_height, 
                                     img1.width, overlap_height));
        cv::Mat search = mat2;
        
        // Template matching
        cv::Mat result;
        cv::matchTemplate(search, templ, result, cv::TM_CCORR_NORMED);
        
        double min_val, max_val;
        cv::Point min_loc, max_loc;
        cv::minMaxLoc(result, &min_val, &max_val, &min_loc, &max_loc);
        
        stats.offset_x = max_loc.x;
        stats.offset_y = max_loc.y;
        stats.correlation = max_val;
        stats.success = (max_val >= min_correlation_);
        
    } catch (const cv::Exception& e) {
        LOG_ERROR("OpenCV exception in template matching: ", e.what());
        stats.success = false;
    }
    
    return stats;
}

void StripStitcher::blendOverlapRegion(Image<byte_t>& target, 
                                       const Image<byte_t>& source,
                                       int offset_x, int offset_y) {
    
    const int blend_height = params_.overlap_pixels;
    
    for (int y = 0; y < source.height; ++y) {
        int target_y = offset_y + y;
        
        if (target_y < 0 || target_y >= target.height) continue;
        
        // Calculate blend weight (0.0 to 1.0)
        float alpha = 1.0f;
        
        if (y < blend_height) {
            // In overlap region - blend
            alpha = static_cast<float>(y) / blend_height;
        }
        
        for (int x = 0; x < source.width; ++x) {
            int target_x = x + offset_x;
            
            if (target_x < 0 || target_x >= target.width) continue;
            
            byte_t source_val = source.at(x, y);
            byte_t target_val = target.at(target_x, target_y);
            
            // Linear blend
            byte_t blended = static_cast<byte_t>(
                alpha * source_val + (1.0f - alpha) * target_val
            );
            
            target.at(target_x, target_y) = blended;
        }
    }
}

void StripStitcher::linearBlend(byte_t* target_ptr, const byte_t* source_ptr,
                               int width, int height, float alpha) {
    for (int i = 0; i < width * height; ++i) {
        target_ptr[i] = static_cast<byte_t>(
            alpha * source_ptr[i] + (1.0f - alpha) * target_ptr[i]
        );
    }
}

} // namespace stitching
} // namespace alinify
