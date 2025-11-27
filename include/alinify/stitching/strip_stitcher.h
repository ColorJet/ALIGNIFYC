#ifndef ALINIFY_STITCHING_STRIP_STITCHER_H
#define ALINIFY_STITCHING_STRIP_STITCHER_H

#include "alinify/common/types.h"
#include <vector>
#include <memory>

namespace alinify {
namespace stitching {

/**
 * @brief Stitches multiple scan strips into a single image
 * 
 * Handles:
 * - Bidirectional scanning (left-to-right and right-to-left)
 * - Sub-pixel alignment using phase correlation
 * - Mechanical error compensation
 * - Overlap blending
 */
class StripStitcher {
public:
    StripStitcher();
    ~StripStitcher();
    
    /**
     * @brief Initialize stitcher with scanning parameters
     */
    StatusCode initialize(const ScanningParams& params);
    
    /**
     * @brief Add a new strip to the stitched image
     * @param strip The scan strip to add
     * @return StatusCode indicating success or failure
     */
    StatusCode addStrip(const ScanStrip& strip);
    
    /**
     * @brief Get the current stitched image
     * @return The accumulated stitched image
     */
    Image<byte_t> getStitchedImage() const;
    
    /**
     * @brief Clear all strips and reset
     */
    void reset();
    
    /**
     * @brief Get alignment statistics for last strip
     */
    struct AlignmentStats {
        double offset_x;
        double offset_y;
        double correlation;
        bool success;
    };
    
    AlignmentStats getLastAlignmentStats() const;
    
    /**
     * @brief Set minimum correlation threshold
     */
    void setCorrelationThreshold(double threshold) {
        min_correlation_ = threshold;
    }
    
    /**
     * @brief Enable/disable blending
     */
    void setBlendingEnabled(bool enabled) {
        blending_enabled_ = enabled;
    }
    
private:
    // Alignment methods
    AlignmentStats alignStrips(const Image<byte_t>& prev, const Image<byte_t>& current);
    AlignmentStats phaseCorrelation(const Image<byte_t>& img1, const Image<byte_t>& img2);
    AlignmentStats templateMatching(const Image<byte_t>& img1, const Image<byte_t>& img2);
    
    // Blending
    void blendOverlapRegion(Image<byte_t>& target, const Image<byte_t>& source,
                           int offset_x, int offset_y);
    void linearBlend(byte_t* target_ptr, const byte_t* source_ptr, 
                    int width, int height, float alpha);
    
    // Configuration
    ScanningParams params_;
    double min_correlation_;
    bool blending_enabled_;
    
    // State
    std::vector<ScanStrip> strips_;
    Image<byte_t> stitched_image_;
    AlignmentStats last_alignment_;
    
    int current_height_;  // Current height of stitched image
    bool initialized_;
};

} // namespace stitching
} // namespace alinify

#endif // ALINIFY_STITCHING_STRIP_STITCHER_H
