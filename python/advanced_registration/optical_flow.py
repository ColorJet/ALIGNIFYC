"""
Optical Flow Registration Methods
Dense deformation field estimation for fabric alignment
"""

import numpy as np
import cv2
from typing import Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OpticalFlowMethod(Enum):
    """Available optical flow algorithms"""
    FARNEBACK = "farneback"      # Dense pyramidal optical flow
    DIS = "dis"                  # Dense Inverse Search (fast)
    RAFT = "raft"                # RAFT (deep learning, future)


def compute_dense_flow_farneback(
    image1: np.ndarray,
    image2: np.ndarray,
    pyr_scale: float = 0.5,
    levels: int = 3,
    winsize: int = 15,
    iterations: int = 3,
    poly_n: int = 5,
    poly_sigma: float = 1.2,
    flags: int = 0
) -> np.ndarray:
    """
    Compute dense optical flow using Farneback's algorithm
    
    Best for:
    - Fast registration (~0.2-0.5s)
    - Small to moderate deformations
    - Real-time applications
    
    Args:
        image1: First image (grayscale)
        image2: Second image (grayscale)
        pyr_scale: Pyramid scale (<1)
        levels: Number of pyramid levels
        winsize: Averaging window size
        iterations: Iterations at each pyramid level
        poly_n: Pixel neighborhood size
        poly_sigma: Gaussian sigma for polynomial expansion
        flags: Operation flags
    
    Returns:
        flow: Dense flow field (H, W, 2) with (dx, dy) at each pixel
    
    References:
        Farnebäck, G. (2003). Two-frame motion estimation based on 
        polynomial expansion. SCIA 2003.
    """
    # Ensure grayscale
    if len(image1.shape) == 3:
        image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    if len(image2.shape) == 3:
        image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
    
    # Compute flow
    flow = cv2.calcOpticalFlowFarneback(
        image1, image2,
        None,
        pyr_scale, levels, winsize,
        iterations, poly_n, poly_sigma,
        flags
    )
    
    # Log statistics
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    logger.info(f"Farneback flow: mean={magnitude.mean():.2f}, max={magnitude.max():.2f} pixels")
    
    return flow


def compute_dense_flow_dis(
    image1: np.ndarray,
    image2: np.ndarray,
    preset: int = cv2.DISOpticalFlow_PRESET_MEDIUM
) -> np.ndarray:
    """
    Compute dense optical flow using DIS (Dense Inverse Search)
    
    Best for:
    - Very fast registration
    - Large displacements
    - Good quality/speed tradeoff
    
    Args:
        image1: First image (grayscale)
        image2: Second image (grayscale)
        preset: DIS preset (FAST/MEDIUM/ULTRAFAST)
    
    Returns:
        flow: Dense flow field (H, W, 2)
    
    References:
        Kroeger et al. (2016). Fast optical flow using dense inverse search.
        ECCV 2016.
    """
    # Ensure grayscale
    if len(image1.shape) == 3:
        image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    if len(image2.shape) == 3:
        image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
    
    # Create DIS instance
    dis = cv2.DISOpticalFlow_create(preset)
    
    # Compute flow
    flow = dis.calc(image1, image2, None)
    
    # Log statistics
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    logger.info(f"DIS flow: mean={magnitude.mean():.2f}, max={magnitude.max():.2f} pixels")
    
    return flow


def warp_image_with_flow(
    image: np.ndarray,
    flow: np.ndarray
) -> np.ndarray:
    """
    Warp image using dense optical flow field
    
    Args:
        image: Image to warp (H, W) or (H, W, C)
        flow: Flow field (H, W, 2) with (dx, dy) at each pixel
    
    Returns:
        warped: Warped image same shape as input
    """
    h, w = flow.shape[:2]
    
    # Create coordinate grid
    flow_map = np.zeros((h, w, 2), dtype=np.float32)
    for y in range(h):
        flow_map[y, :, 0] = np.arange(w)  # x coordinates
    for x in range(w):
        flow_map[:, x, 1] = np.arange(h)  # y coordinates
    
    # Add flow to get new coordinates
    flow_map += flow
    
    # Remap image
    warped = cv2.remap(image, flow_map, None, cv2.INTER_LINEAR)
    
    return warped


def flow_to_deformation_field(flow: np.ndarray) -> np.ndarray:
    """
    Convert optical flow to deformation field format
    
    Optical flow: displacement vectors (dx, dy) at each pixel
    Deformation field: target coordinates (x', y') at each pixel
    
    Args:
        flow: Optical flow (H, W, 2)
    
    Returns:
        deformation: Deformation field (H, W, 2) with absolute coordinates
    """
    h, w = flow.shape[:2]
    
    # Create coordinate grid
    x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
    
    # Deformation = original coords + flow
    deformation = np.stack([
        x_coords + flow[..., 0],
        y_coords + flow[..., 1]
    ], axis=-1)
    
    return deformation.astype(np.float32)


def register_with_optical_flow(
    fixed: np.ndarray,
    moving: np.ndarray,
    method: OpticalFlowMethod = OpticalFlowMethod.FARNEBACK,
    **kwargs
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """
    Complete optical flow registration pipeline
    
    Args:
        fixed: Fixed image (target)
        moving: Moving image (source)
        method: Optical flow algorithm
        **kwargs: Algorithm-specific parameters
    
    Returns:
        warped: Warped moving image aligned to fixed
        deformation: Deformation field (H, W, 2)
        metadata: Registration info (runtime, flow magnitude, etc.)
    """
    import time
    start = time.perf_counter()
    
    # Compute flow
    if method == OpticalFlowMethod.FARNEBACK:
        flow = compute_dense_flow_farneback(fixed, moving, **kwargs)
    elif method == OpticalFlowMethod.DIS:
        flow = compute_dense_flow_dis(fixed, moving, **kwargs)
    else:
        raise ValueError(f"Unknown optical flow method: {method}")
    
    # Warp image
    warped = warp_image_with_flow(moving, flow)
    
    # Convert to deformation field
    deformation = flow_to_deformation_field(flow)
    
    # Compute metrics
    runtime = time.perf_counter() - start
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    
    metadata = {
        'method': method.value,
        'runtime_seconds': runtime,
        'mean_displacement': float(magnitude.mean()),
        'max_displacement': float(magnitude.max()),
        'flow_shape': flow.shape
    }
    
    logger.info(f"Optical flow registration: {runtime:.3f}s, mean disp={magnitude.mean():.2f}px")
    
    return warped, deformation, metadata


def visualize_flow(
    flow: np.ndarray,
    scale: float = 1.0,
    step: int = 16
) -> np.ndarray:
    """
    Create visualization of optical flow field
    
    Args:
        flow: Flow field (H, W, 2)
        scale: Arrow length scale
        step: Sampling step for vectors
    
    Returns:
        vis: RGB visualization image
    """
    h, w = flow.shape[:2]
    
    # Create blank canvas
    vis = np.ones((h, w, 3), dtype=np.uint8) * 255
    
    # Sample flow vectors
    y_coords, x_coords = np.mgrid[step//2:h:step, step//2:w:step]
    
    # Draw arrows
    for i in range(len(y_coords.flat)):
        y = y_coords.flat[i]
        x = x_coords.flat[i]
        fx = flow[y, x, 0] * scale
        fy = flow[y, x, 1] * scale
        
        cv2.arrowedLine(
            vis,
            (x, y),
            (int(x + fx), int(y + fy)),
            (0, 0, 255),
            1,
            tipLength=0.3
        )
    
    return vis


def flow_to_hsv(flow: np.ndarray) -> np.ndarray:
    """
    Convert flow to HSV color visualization
    
    Hue = direction, Saturation = magnitude
    
    Args:
        flow: Flow field (H, W, 2)
    
    Returns:
        vis: RGB visualization image
    """
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    
    # Create HSV image
    hsv = np.zeros((flow.shape[0], flow.shape[1], 3), dtype=np.uint8)
    hsv[..., 0] = angle * 180 / np.pi / 2  # Hue: direction
    hsv[..., 1] = 255                       # Saturation: full
    hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)  # Value: magnitude
    
    # Convert to RGB
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    return rgb


# Placeholder for RAFT (Week 3)
def compute_dense_flow_raft(
    image1: np.ndarray,
    image2: np.ndarray,
    model_path: Optional[str] = None,
    device: str = 'cuda'
) -> np.ndarray:
    """
    Compute optical flow using RAFT (Recurrent All-Pairs Field Transforms)
    
    Best for:
    - State-of-the-art accuracy
    - GPU-accelerated (~0.3-0.5s)
    - Challenging scenarios
    
    Note: Requires PyTorch and pre-trained weights
    
    Args:
        image1: First image
        image2: Second image
        model_path: Path to RAFT checkpoint
        device: 'cuda' or 'cpu'
    
    Returns:
        flow: Dense flow field (H, W, 2)
    
    References:
        Teed & Deng (2020). RAFT: Recurrent All-Pairs Field Transforms 
        for Optical Flow. ECCV 2020.
    """
    raise NotImplementedError("RAFT integration coming in Week 3")
