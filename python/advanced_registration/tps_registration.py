"""
Thin-Plate Spline (TPS) Registration
Feature-based non-rigid registration using radial basis functions
"""

import numpy as np
import cv2
from typing import Tuple, List, Optional
from scipy.spatial.distance import cdist
import logging

logger = logging.getLogger(__name__)


def compute_tps_matrices(
    source_points: np.ndarray,
    target_points: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute TPS transformation matrices from control point correspondences
    
    Args:
        source_points: Control points in source image (N, 2)
        target_points: Corresponding points in target image (N, 2)
    
    Returns:
        weights: TPS weights (N, 2)
        affine: Affine transformation parameters (3, 2)
    
    References:
        Bookstein, F. L. (1989). Principal warps: thin-plate splines and 
        the decomposition of deformations. IEEE TPAMI.
    """
    n_points = source_points.shape[0]
    
    # Compute pairwise distances
    K = _compute_tps_kernel(source_points, source_points)
    
    # Build linear system: [K P] [w] = [target]
    #                      [P^T 0] [a]   [  0  ]
    P = np.hstack([np.ones((n_points, 1)), source_points])
    
    # Upper block
    L_upper = np.hstack([K, P])
    
    # Lower block
    L_lower = np.hstack([P.T, np.zeros((3, 3))])
    
    # Full matrix
    L = np.vstack([L_upper, L_lower])
    
    # Right-hand side
    Y = np.vstack([target_points, np.zeros((3, 2))])
    
    # Solve for parameters
    try:
        params = np.linalg.solve(L, Y)
    except np.linalg.LinAlgError:
        logger.warning("TPS matrix singular, using least-squares solution")
        params = np.linalg.lstsq(L, Y, rcond=None)[0]
    
    # Extract weights and affine parameters
    weights = params[:n_points, :]
    affine = params[n_points:, :]
    
    return weights, affine


def _compute_tps_kernel(points1: np.ndarray, points2: np.ndarray) -> np.ndarray:
    """
    Compute TPS radial basis function kernel: r^2 log(r)
    
    Args:
        points1: First point set (N, 2)
        points2: Second point set (M, 2)
    
    Returns:
        K: Kernel matrix (N, M)
    """
    # Compute pairwise distances
    r = cdist(points1, points2, metric='euclidean')
    
    # TPS kernel: r^2 log(r)
    # Handle r=0 case: lim r->0 of r^2 log(r) = 0
    with np.errstate(divide='ignore', invalid='ignore'):
        K = np.where(r > 0, r**2 * np.log(r), 0)
    
    return K


def apply_tps_transform(
    image: np.ndarray,
    source_points: np.ndarray,
    weights: np.ndarray,
    affine: np.ndarray,
    output_shape: Optional[Tuple[int, int]] = None
) -> np.ndarray:
    """
    Warp image using TPS transformation
    
    Args:
        image: Input image to warp
        source_points: Control points from source image (N, 2)
        weights: TPS weights (N, 2)
        affine: Affine parameters (3, 2)
        output_shape: Output image shape (H, W), defaults to input shape
    
    Returns:
        warped: Warped image
    """
    if output_shape is None:
        output_shape = image.shape[:2]
    
    h, w = output_shape
    
    # Create coordinate grid for output image
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
    coords = np.stack([x_coords.ravel(), y_coords.ravel()], axis=1)
    
    # Compute transformation for each output pixel
    transformed_coords = _tps_interpolate(coords, source_points, weights, affine)
    
    # Reshape to grid
    map_x = transformed_coords[:, 0].reshape(h, w)
    map_y = transformed_coords[:, 1].reshape(h, w)
    
    # Remap image
    warped = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)
    
    return warped


def _tps_interpolate(
    points: np.ndarray,
    control_points: np.ndarray,
    weights: np.ndarray,
    affine: np.ndarray
) -> np.ndarray:
    """
    Interpolate point positions using TPS transformation
    
    Args:
        points: Points to transform (M, 2)
        control_points: TPS control points (N, 2)
        weights: TPS weights (N, 2)
        affine: Affine parameters (3, 2)
    
    Returns:
        transformed: Transformed points (M, 2)
    """
    n_points = points.shape[0]
    
    # Compute kernel between query points and control points
    K = _compute_tps_kernel(points, control_points)
    
    # Affine part
    P = np.hstack([np.ones((n_points, 1)), points])
    affine_part = P @ affine
    
    # Non-rigid part
    nonrigid_part = K @ weights
    
    # Total transformation
    transformed = affine_part + nonrigid_part
    
    return transformed


def register_with_tps(
    fixed: np.ndarray,
    moving: np.ndarray,
    fixed_points: np.ndarray,
    moving_points: np.ndarray,
    return_deformation: bool = True
) -> Tuple[np.ndarray, Optional[np.ndarray], dict]:
    """
    Register images using Thin-Plate Spline transformation
    
    Args:
        fixed: Fixed image (target)
        moving: Moving image (source)
        fixed_points: Control points in fixed image (N, 2)
        moving_points: Corresponding points in moving image (N, 2)
        return_deformation: Whether to compute full deformation field
    
    Returns:
        warped: Warped moving image
        deformation: Deformation field (H, W, 2) or None
        metadata: Registration info
    """
    import time
    start = time.perf_counter()
    
    # Compute TPS parameters
    weights, affine = compute_tps_matrices(moving_points, fixed_points)
    
    # Warp image
    warped = apply_tps_transform(moving, moving_points, weights, affine, fixed.shape[:2])
    
    # Optionally compute deformation field
    deformation = None
    if return_deformation:
        h, w = fixed.shape[:2]
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        coords = np.stack([x_coords.ravel(), y_coords.ravel()], axis=1)
        transformed = _tps_interpolate(coords, moving_points, weights, affine)
        deformation = transformed.reshape(h, w, 2)
    
    runtime = time.perf_counter() - start
    
    # Compute displacement statistics
    displacements = fixed_points - moving_points
    mean_disp = np.linalg.norm(displacements, axis=1).mean()
    max_disp = np.linalg.norm(displacements, axis=1).max()
    
    metadata = {
        'method': 'tps',
        'runtime_seconds': runtime,
        'n_control_points': len(fixed_points),
        'mean_displacement': float(mean_disp),
        'max_displacement': float(max_disp)
    }
    
    logger.info(f"TPS registration: {runtime:.3f}s, {len(fixed_points)} control points, "
                f"mean disp={mean_disp:.2f}px")
    
    return warped, deformation, metadata


def extract_control_points_from_matches(
    keypoints1: List[cv2.KeyPoint],
    keypoints2: List[cv2.KeyPoint],
    matches: List[cv2.DMatch],
    max_points: int = 50,
    ransac_threshold: float = 5.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract reliable control points from feature matches using RANSAC
    
    Args:
        keypoints1: Keypoints from first image
        keypoints2: Keypoints from second image
        matches: Feature matches
        max_points: Maximum control points to use
        ransac_threshold: RANSAC inlier threshold
    
    Returns:
        points1: Control points in first image (N, 2)
        points2: Control points in second image (N, 2)
        inlier_mask: Boolean mask of inliers
    """
    if len(matches) < 4:
        logger.warning("Too few matches for RANSAC")
        return np.array([]), np.array([]), np.array([])
    
    # Extract matched points
    src_pts = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    
    # RANSAC to filter outliers
    _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, ransac_threshold)
    
    if mask is None:
        logger.warning("RANSAC failed")
        return np.array([]), np.array([]), np.array([])
    
    # Extract inliers
    mask = mask.ravel().astype(bool)
    points1 = src_pts[mask].reshape(-1, 2)
    points2 = dst_pts[mask].reshape(-1, 2)
    
    # Limit number of control points
    if len(points1) > max_points:
        indices = np.linspace(0, len(points1) - 1, max_points, dtype=int)
        points1 = points1[indices]
        points2 = points2[indices]
    
    logger.info(f"Extracted {len(points1)} control points ({mask.sum()} inliers from {len(matches)} matches)")
    
    return points1, points2, mask


def register_with_tps_from_features(
    fixed: np.ndarray,
    moving: np.ndarray,
    detector_type: str = 'sift',
    nfeatures: int = 2000,
    max_control_points: int = 50,
    ransac_threshold: float = 5.0
) -> Tuple[np.ndarray, Optional[np.ndarray], dict]:
    """
    Complete TPS registration pipeline with automatic feature detection
    
    Args:
        fixed: Fixed image
        moving: Moving image
        detector_type: Feature detector ('sift', 'akaze', 'orb')
        nfeatures: Number of features to detect
        max_control_points: Maximum control points for TPS
        ransac_threshold: RANSAC threshold
    
    Returns:
        warped: Warped moving image
        deformation: Deformation field (H, W, 2)
        metadata: Registration info including feature detection stats
    """
    from .feature_detectors import detect_and_match, compute_transform_from_matches, FeatureDetector
    
    # Map string to enum
    detector_map = {
        'sift': FeatureDetector.SIFT,
        'akaze': FeatureDetector.AKAZE,
        'orb': FeatureDetector.ORB
    }
    detector = detector_map.get(detector_type.lower(), FeatureDetector.SIFT)
    
    # Detect and match features
    kp1, kp2, matches = detect_and_match(fixed, moving, detector=detector, nfeatures=nfeatures)
    
    if len(matches) < 4:
        logger.error("Insufficient matches for TPS registration")
        return moving, None, {'error': 'insufficient_matches', 'n_matches': len(matches)}
    
    # Extract control points
    fixed_pts, moving_pts, mask = extract_control_points_from_matches(
        kp1, kp2, matches, max_points=max_control_points, ransac_threshold=ransac_threshold
    )
    
    if len(fixed_pts) < 3:
        logger.error("Too few control points after RANSAC")
        return moving, None, {'error': 'insufficient_control_points', 'n_points': len(fixed_pts)}
    
    # Perform TPS registration
    warped, deformation, tps_metadata = register_with_tps(fixed, moving, fixed_pts, moving_pts)
    
    # Merge metadata
    tps_metadata.update({
        'detector': detector_type,
        'n_features': len(kp1),
        'n_matches': len(matches),
        'n_inliers': int(mask.sum()),
        'n_control_points': len(fixed_pts)
    })
    
    return warped, deformation, tps_metadata


def visualize_tps_control_points(
    image: np.ndarray,
    control_points: np.ndarray,
    radius: int = 5,
    color: Tuple[int, int, int] = (0, 255, 0)
) -> np.ndarray:
    """
    Draw control points on image for visualization
    
    Args:
        image: Input image
        control_points: Control points (N, 2)
        radius: Circle radius
        color: Circle color (B, G, R)
    
    Returns:
        vis: Image with control points drawn
    """
    vis = image.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
    
    for pt in control_points:
        cv2.circle(vis, tuple(pt.astype(int)), radius, color, -1)
        cv2.circle(vis, tuple(pt.astype(int)), radius + 2, (255, 255, 255), 1)
    
    return vis


def visualize_tps_grid(
    source_points: np.ndarray,
    weights: np.ndarray,
    affine: np.ndarray,
    image_shape: Tuple[int, int],
    grid_spacing: int = 50
) -> np.ndarray:
    """
    Visualize TPS deformation with a warped grid
    
    Args:
        source_points: TPS control points
        weights: TPS weights
        affine: Affine parameters
        image_shape: Output image shape (H, W)
        grid_spacing: Spacing between grid lines
    
    Returns:
        vis: Warped grid visualization
    """
    h, w = image_shape
    vis = np.zeros((h, w, 3), dtype=np.uint8)
    
    # Draw vertical grid lines
    for x in range(0, w, grid_spacing):
        points = np.array([[x, y] for y in range(h)], dtype=np.float32)
        transformed = _tps_interpolate(points, source_points, weights, affine)
        pts = transformed.astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(vis, [pts], False, (0, 255, 0), 1)
    
    # Draw horizontal grid lines
    for y in range(0, h, grid_spacing):
        points = np.array([[x, y] for x in range(w)], dtype=np.float32)
        transformed = _tps_interpolate(points, source_points, weights, affine)
        pts = transformed.astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(vis, [pts], False, (0, 255, 0), 1)
    
    return vis
