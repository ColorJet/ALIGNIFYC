"""
Elastix Parameter Reference Guide
Explains all warning parameters and how to optimize them for fabric registration
"""

ELASTIX_PARAMETER_GUIDE = {
    # =================================================================
    # IMAGE PYRAMIDS - Multi-resolution processing
    # =================================================================
    "FixedImagePyramid": {
        "default": "FixedSmoothingImagePyramid",
        "options": ["FixedSmoothingImagePyramid", "FixedRecursiveImagePyramid", "FixedShrinkingImagePyramid"],
        "description": "How to downsample fixed image for multi-resolution",
        "recommendation": "FixedSmoothingImagePyramid - Best quality, applies Gaussian smoothing before downsampling",
        "when_to_change": "Use FixedShrinkingImagePyramid for faster processing at cost of quality"
    },
    
    "MovingImagePyramid": {
        "default": "MovingSmoothingImagePyramid",
        "options": ["MovingSmoothingImagePyramid", "MovingRecursiveImagePyramid", "MovingShrinkingImagePyramid"],
        "description": "How to downsample moving image for multi-resolution",
        "recommendation": "MovingSmoothingImagePyramid - Best quality",
        "when_to_change": "Match with FixedImagePyramid setting"
    },
    
    # =================================================================
    # B-SPLINE TRANSFORM - Deformation model
    # =================================================================
    "BSplineTransformSplineOrder": {
        "default": "3",
        "options": ["1", "2", "3"],
        "description": "Polynomial order for B-spline basis functions",
        "recommendation": "3 (cubic) - Smoothest deformations for fabric",
        "when_to_change": "Use 1 (linear) for faster computation, less smooth",
        "impact": "Higher = smoother deformations, better for fabric without sharp folds"
    },
    
    "UseCyclicTransform": {
        "default": "false",
        "options": ["true", "false"],
        "description": "Whether deformation wraps around image edges",
        "recommendation": "false - Fabric doesn't wrap around",
        "when_to_change": "Set to true only for cylindrical/toroidal images",
        "impact": "Fabric registration should never use this"
    },
    
    "FinalBSplineInterpolationOrder": {
        "default": "3",
        "options": ["0", "1", "2", "3"],
        "description": "Interpolation order for final warping",
        "recommendation": "3 (cubic) - Highest quality for fabric texture",
        "when_to_change": "Use 1 for speed, 0 for nearest-neighbor (pixel art)",
        "impact": "Higher = better visual quality of warped fabric"
    },
    
    # =================================================================
    # HISTOGRAM-BASED METRICS - Mutual Information settings
    # =================================================================
    "NumberOfHistogramBins": {
        "default": "32",
        "options": ["16", "32", "64", "128", "256"],
        "description": "Histogram bins for mutual information metric",
        "recommendation": "64 for fabric - Better intensity discrimination",
        "when_to_change": "32 for speed, 128+ for high dynamic range images",
        "impact": "More bins = better metric accuracy but slower computation"
    },
    
    "NumberOfFixedHistogramBins": {
        "default": "32",
        "options": ["16", "32", "64", "128"],
        "description": "Histogram bins specifically for fixed image",
        "recommendation": "64 - Match with NumberOfHistogramBins",
        "when_to_change": "Increase if fixed image has wide intensity range"
    },
    
    "NumberOfMovingHistogramBins": {
        "default": "32",
        "options": ["16", "32", "64", "128"],
        "description": "Histogram bins specifically for moving image",
        "recommendation": "64 - Match with NumberOfHistogramBins",
        "when_to_change": "Increase if moving image has different range than fixed"
    },
    
    "FixedLimitRangeRatio": {
        "default": "0.01",
        "options": ["0.0", "0.01", "0.05"],
        "description": "Fraction of extreme values to ignore in fixed image",
        "recommendation": "0.01 - Ignore 1% of outliers",
        "when_to_change": "0.0 for clean images, 0.05 for noisy fabric scans",
        "impact": "Helps ignore dust/artifacts in fabric scans"
    },
    
    "MovingLimitRangeRatio": {
        "default": "0.01",
        "options": ["0.0", "0.01", "0.05"],
        "description": "Fraction of extreme values to ignore in moving image",
        "recommendation": "0.01 - Ignore 1% of outliers",
        "when_to_change": "Match with FixedLimitRangeRatio"
    },
    
    # =================================================================
    # KERNEL-BASED DENSITY ESTIMATION
    # =================================================================
    "FixedKernelBSplineOrder": {
        "default": "0",
        "options": ["0", "1", "2", "3"],
        "description": "B-spline order for Parzen window in fixed image histogram",
        "recommendation": "3 - Smoother density estimation",
        "when_to_change": "0 for box kernel (faster), 3 for Gaussian-like (better)",
        "impact": "Higher = smoother metric, more stable optimization"
    },
    
    "MovingKernelBSplineOrder": {
        "default": "3",
        "options": ["0", "1", "2", "3"],
        "description": "B-spline order for Parzen window in moving image histogram",
        "recommendation": "3 - Match with FixedKernelBSplineOrder",
        "when_to_change": "Keep at 3 for best results"
    },
    
    # =================================================================
    # PERFORMANCE OPTIMIZATION
    # =================================================================
    "UseFastAndLowMemoryVersion": {
        "default": "true",
        "options": ["true", "false"],
        "description": "Use optimized implementation trading memory for speed",
        "recommendation": "true - Faster, lower memory for large fabric images",
        "when_to_change": "false only if you have memory issues",
        "impact": "true = 2-3x faster for large images"
    },
    
    "UseJacobianPreconditioning": {
        "default": "false",
        "options": ["true", "false"],
        "description": "Scale gradient by local deformation Jacobian",
        "recommendation": "true - Better convergence for large deformations",
        "when_to_change": "Enable for fabric with significant stretch/compression",
        "impact": "Can improve registration of highly deformed fabric"
    },
    
    "FiniteDifferenceDerivative": {
        "default": "false",
        "options": ["true", "false"],
        "description": "Use finite differences vs analytical derivatives",
        "recommendation": "false - Analytical is faster and more accurate",
        "when_to_change": "true only for debugging or unsupported metrics",
        "impact": "false = 2x faster gradient computation"
    },
}


def generate_optimized_parameters():
    """
    Generate optimized parameter additions to eliminate warnings
    and utilize max Elastix features for fabric registration
    """
    return {
        # ===== Image Pyramids (eliminates pyramid warnings) =====
        "FixedImagePyramid": ["FixedSmoothingImagePyramid"],
        "MovingImagePyramid": ["MovingSmoothingImagePyramid"],
        
        # ===== B-Spline Transform (eliminates transform warnings) =====
        "BSplineTransformSplineOrder": ["3"],  # Cubic for smooth fabric deformation
        "UseCyclicTransform": ["false"],
        "FinalBSplineInterpolationOrder": ["3"],  # High-quality warping
        
        # ===== Histogram Settings for Mutual Information =====
        "NumberOfHistogramBins": ["64"],  # Better than default 32 for fabric
        "NumberOfFixedHistogramBins": ["64"],
        "NumberOfMovingHistogramBins": ["64"],
        "FixedLimitRangeRatio": ["0.01"],  # Ignore 1% outliers (dust/artifacts)
        "MovingLimitRangeRatio": ["0.01"],
        
        # ===== Parzen Window Kernel Settings =====
        "FixedKernelBSplineOrder": ["3"],  # Smoother density estimation
        "MovingKernelBSplineOrder": ["3"],
        
        # ===== Performance Optimization =====
        "UseFastAndLowMemoryVersion": ["true"],  # Optimized for large images
        "UseJacobianPreconditioning": ["true"],  # Better for fabric deformation
        "FiniteDifferenceDerivative": ["false"],  # Analytical derivatives
    }


def get_high_quality_parameters():
    """High-quality settings for final production runs"""
    return {
        "NumberOfHistogramBins": ["128"],  # Maximum discrimination
        "FixedKernelBSplineOrder": ["3"],
        "MovingKernelBSplineOrder": ["3"],
        "FinalBSplineInterpolationOrder": ["3"],
        "BSplineTransformSplineOrder": ["3"],
        "UseJacobianPreconditioning": ["true"],
    }


def get_fast_preview_parameters():
    """Fast settings for preview/testing"""
    return {
        "NumberOfHistogramBins": ["32"],  # Faster
        "FixedKernelBSplineOrder": ["0"],  # Box kernel
        "MovingKernelBSplineOrder": ["0"],
        "FinalBSplineInterpolationOrder": ["1"],  # Linear interpolation
        "UseFastAndLowMemoryVersion": ["true"],
    }


# Print parameter guide
if __name__ == "__main__":
    print("="*70)
    print("ELASTIX PARAMETER OPTIMIZATION GUIDE")
    print("="*70)
    print("\nAll parameters that trigger warnings and how to optimize them:\n")
    
    for param, info in ELASTIX_PARAMETER_GUIDE.items():
        print(f"📌 {param}")
        print(f"   Default: {info['default']}")
        print(f"   Options: {', '.join(info['options'])}")
        print(f"   ℹ️  {info['description']}")
        print(f"   ✅ {info['recommendation']}")
        if 'impact' in info:
            print(f"   ⚡ {info['impact']}")
        print()
    
    print("="*70)
    print("RECOMMENDED SETTINGS FOR FABRIC REGISTRATION")
    print("="*70)
    
    print("\n🎯 OPTIMIZED (balanced quality/speed):")
    for k, v in generate_optimized_parameters().items():
        print(f"   {k}: {v[0]}")
    
    print("\n🏆 HIGH QUALITY (production):")
    for k, v in get_high_quality_parameters().items():
        print(f"   {k}: {v[0]}")
    
    print("\n⚡ FAST PREVIEW (testing):")
    for k, v in get_fast_preview_parameters().items():
        print(f"   {k}: {v[0]}")
    
    print("\n" + "="*70)
