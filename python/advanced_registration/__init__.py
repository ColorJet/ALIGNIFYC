"""
Advanced Registration Module
Provides learning-based and conventional registration alternatives to Elastix
"""

# VoxelMorph deep learning backend
from .voxelmorph_backend import VoxelMorphRegistration, register_voxelmorph

# Feature detection alternatives
from .feature_detectors import (
    FeatureDetector,
    detect_features_sift,
    detect_features_akaze,
    detect_features_orb,
    detect_and_match,
    match_features,
    compute_transform_from_matches
)

# Optical flow methods
from .optical_flow import (
    OpticalFlowMethod,
    compute_dense_flow_farneback,
    compute_dense_flow_dis,
    warp_image_with_flow,
    flow_to_deformation_field,
    register_with_optical_flow,
    visualize_flow,
    flow_to_hsv
)

# Thin-plate spline registration
from .tps_registration import (
    compute_tps_matrices,
    apply_tps_transform,
    register_with_tps,
    register_with_tps_from_features,
    extract_control_points_from_matches,
    visualize_tps_control_points,
    visualize_tps_grid
)

__all__ = [
    # VoxelMorph
    'VoxelMorphRegistration',
    'register_voxelmorph',
    
    # Feature detection
    'FeatureDetector',
    'detect_features_sift',
    'detect_features_akaze',
    'detect_features_orb',
    'detect_and_match',
    'match_features',
    'compute_transform_from_matches',
    
    # Optical flow
    'OpticalFlowMethod',
    'compute_dense_flow_farneback',
    'compute_dense_flow_dis',
    'warp_image_with_flow',
    'flow_to_deformation_field',
    'register_with_optical_flow',
    'visualize_flow',
    'flow_to_hsv',
    
    # Thin-plate spline
    'compute_tps_matrices',
    'apply_tps_transform',
    'register_with_tps',
    'register_with_tps_from_features',
    'extract_control_points_from_matches',
    'visualize_tps_control_points',
    'visualize_tps_grid',
]
