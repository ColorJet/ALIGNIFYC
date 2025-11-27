"""
Feature Detection Alternatives to ORB
Provides SIFT, AKAZE, and optional SuperPoint for robust feature matching
"""

import numpy as np
import cv2
from typing import Tuple, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeatureDetector(Enum):
    """Available feature detection algorithms"""
    ORB = "orb"           # Fast, patent-free (current default)
    SIFT = "sift"         # Robust, scale-invariant (patent expired 2020)
    AKAZE = "akaze"       # Good balance, binary descriptors
    SUPERPOINT = "superpoint"  # Deep learning, requires PyTorch


def detect_features_sift(
    image: np.ndarray,
    nfeatures: int = 2000,
    nOctaveLayers: int = 3,
    contrastThreshold: float = 0.04,
    edgeThreshold: float = 10,
    sigma: float = 1.6
) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
    """
    Detect SIFT features (Scale-Invariant Feature Transform)
    
    Best for:
    - Low-texture fabrics
    - Scale variations
    - Rotation invariance
    
    Args:
        image: Grayscale image
        nfeatures: Maximum number of features to retain
        nOctaveLayers: Layers per octave in Gaussian pyramid
        contrastThreshold: Contrast threshold (lower = more features)
        edgeThreshold: Edge threshold (higher = more edge features)
        sigma: Gaussian sigma for initial image smoothing
    
    Returns:
        keypoints: List of cv2.KeyPoint objects
        descriptors: Feature descriptors (N, 128)
    """
    try:
        sift = cv2.SIFT_create(
            nfeatures=nfeatures,
            nOctaveLayers=nOctaveLayers,
            contrastThreshold=contrastThreshold,
            edgeThreshold=edgeThreshold,
            sigma=sigma
        )
        keypoints, descriptors = sift.detectAndCompute(image, None)
        
        if descriptors is None:
            logger.warning("SIFT detected 0 features")
            return [], np.array([])
        
        logger.info(f"SIFT detected {len(keypoints)} features")
        return keypoints, descriptors
        
    except Exception as e:
        logger.error(f"SIFT detection failed: {e}")
        logger.info("Hint: Install OpenCV with contrib modules: pip install opencv-contrib-python")
        raise


def detect_features_akaze(
    image: np.ndarray,
    descriptor_type: int = cv2.AKAZE_DESCRIPTOR_MLDB,
    descriptor_size: int = 0,
    descriptor_channels: int = 3,
    threshold: float = 0.001,
    nOctaves: int = 4,
    nOctaveLayers: int = 4
) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
    """
    Detect AKAZE features (Accelerated-KAZE)
    
    Best for:
    - Real-time applications
    - Binary descriptors (fast matching)
    - Good quality/speed tradeoff
    
    Args:
        image: Grayscale image
        descriptor_type: AKAZE descriptor type
        descriptor_size: Descriptor size (0=auto)
        descriptor_channels: Descriptor channels
        threshold: Detection threshold (lower = more features)
        nOctaves: Number of octaves
        nOctaveLayers: Layers per octave
    
    Returns:
        keypoints: List of cv2.KeyPoint objects
        descriptors: Binary descriptors (N, descriptor_size)
    """
    try:
        akaze = cv2.AKAZE_create(
            descriptor_type=descriptor_type,
            descriptor_size=descriptor_size,
            descriptor_channels=descriptor_channels,
            threshold=threshold,
            nOctaves=nOctaves,
            nOctaveLayers=nOctaveLayers
        )
        keypoints, descriptors = akaze.detectAndCompute(image, None)
        
        if descriptors is None:
            logger.warning("AKAZE detected 0 features")
            return [], np.array([])
        
        logger.info(f"AKAZE detected {len(keypoints)} features")
        return keypoints, descriptors
        
    except Exception as e:
        logger.error(f"AKAZE detection failed: {e}")
        raise


def detect_features_orb(
    image: np.ndarray,
    nfeatures: int = 2000,
    scaleFactor: float = 1.2,
    nlevels: int = 8,
    edgeThreshold: int = 31,
    firstLevel: int = 0,
    WTA_K: int = 2,
    patchSize: int = 31
) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
    """
    Detect ORB features (Oriented FAST and Rotated BRIEF)
    
    This is the current default method in Alinify.
    
    Best for:
    - Real-time processing
    - Patent-free alternative
    - Good rotation invariance
    
    Args:
        image: Grayscale image
        nfeatures: Maximum number of features
        scaleFactor: Pyramid decimation ratio
        nlevels: Pyramid levels
        edgeThreshold: Border size to ignore
        firstLevel: Level of pyramid to start
        WTA_K: Points to produce BRIEF descriptor
        patchSize: Patch size for oriented BRIEF
    
    Returns:
        keypoints: List of cv2.KeyPoint objects
        descriptors: Binary descriptors (N, 32)
    """
    orb = cv2.ORB_create(
        nfeatures=nfeatures,
        scaleFactor=scaleFactor,
        nlevels=nlevels,
        edgeThreshold=edgeThreshold,
        firstLevel=firstLevel,
        WTA_K=WTA_K,
        patchSize=patchSize
    )
    keypoints, descriptors = orb.detectAndCompute(image, None)
    
    if descriptors is None:
        logger.warning("ORB detected 0 features")
        return [], np.array([])
    
    logger.info(f"ORB detected {len(keypoints)} features")
    return keypoints, descriptors


def match_features(
    descriptors1: np.ndarray,
    descriptors2: np.ndarray,
    method: FeatureDetector = FeatureDetector.SIFT,
    ratio_threshold: float = 0.7,
    cross_check: bool = True
) -> List[cv2.DMatch]:
    """
    Match feature descriptors using appropriate matcher
    
    Args:
        descriptors1: Descriptors from first image
        descriptors2: Descriptors from second image
        method: Feature detector type (determines matcher)
        ratio_threshold: Lowe's ratio test threshold
        cross_check: Enable cross-checking for robustness
    
    Returns:
        matches: List of DMatch objects
    """
    if descriptors1 is None or descriptors2 is None or len(descriptors1) == 0 or len(descriptors2) == 0:
        logger.warning("Cannot match: one or both descriptor sets empty")
        return []
    
    # Choose matcher based on descriptor type
    if method in [FeatureDetector.SIFT]:
        # FLANN matcher for float descriptors
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        matcher = cv2.FlannBasedMatcher(index_params, search_params)
        
        # Lowe's ratio test
        matches = matcher.knnMatch(descriptors1, descriptors2, k=2)
        good_matches = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)
        
    else:
        # Hamming distance for binary descriptors (ORB, AKAZE)
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=cross_check)
        good_matches = matcher.match(descriptors1, descriptors2)
        
        # Sort by distance
        good_matches = sorted(good_matches, key=lambda x: x.distance)
    
    logger.info(f"Matched {len(good_matches)} features")
    return good_matches


def compute_transform_from_matches(
    keypoints1: List[cv2.KeyPoint],
    keypoints2: List[cv2.KeyPoint],
    matches: List[cv2.DMatch],
    method: int = cv2.RANSAC,
    ransac_threshold: float = 5.0
) -> Tuple[Optional[np.ndarray], np.ndarray]:
    """
    Compute geometric transform from feature matches using RANSAC
    
    Args:
        keypoints1: Keypoints from first image
        keypoints2: Keypoints from second image
        matches: Feature matches
        method: Robust estimation method (RANSAC/LMEDS)
        ransac_threshold: RANSAC reprojection threshold
    
    Returns:
        transform: Homography matrix (3x3) or None if failed
        inlier_mask: Boolean mask of inlier matches
    """
    if len(matches) < 4:
        logger.warning(f"Too few matches ({len(matches)}) to compute transform")
        return None, np.array([])
    
    # Extract matched point coordinates
    src_pts = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    
    # Compute homography with RANSAC
    H, mask = cv2.findHomography(src_pts, dst_pts, method, ransac_threshold)
    
    if H is None:
        logger.warning("Homography estimation failed")
        return None, np.array([])
    
    inlier_count = int(mask.sum())
    logger.info(f"Transform computed with {inlier_count}/{len(matches)} inliers")
    
    return H, mask


def detect_and_match(
    image1: np.ndarray,
    image2: np.ndarray,
    detector: FeatureDetector = FeatureDetector.SIFT,
    nfeatures: int = 2000,
    ratio_threshold: float = 0.7
) -> Tuple[List[cv2.KeyPoint], List[cv2.KeyPoint], List[cv2.DMatch]]:
    """
    Complete feature detection and matching pipeline
    
    Args:
        image1: First image (grayscale)
        image2: Second image (grayscale)
        detector: Feature detector to use
        nfeatures: Maximum features to detect
        ratio_threshold: Match ratio threshold
    
    Returns:
        keypoints1, keypoints2, matches
    """
    # Detect features
    if detector == FeatureDetector.SIFT:
        kp1, desc1 = detect_features_sift(image1, nfeatures=nfeatures)
        kp2, desc2 = detect_features_sift(image2, nfeatures=nfeatures)
    elif detector == FeatureDetector.AKAZE:
        kp1, desc1 = detect_features_akaze(image1, threshold=0.001)
        kp2, desc2 = detect_features_akaze(image2, threshold=0.001)
    elif detector == FeatureDetector.ORB:
        kp1, desc1 = detect_features_orb(image1, nfeatures=nfeatures)
        kp2, desc2 = detect_features_orb(image2, nfeatures=nfeatures)
    else:
        raise ValueError(f"Unknown detector: {detector}")
    
    # Match features
    matches = match_features(desc1, desc2, method=detector, ratio_threshold=ratio_threshold)
    
    return kp1, kp2, matches


# Optional: SuperPoint integration (requires PyTorch and pre-trained weights)
def detect_features_superpoint(
    image: np.ndarray,
    model_path: Optional[str] = None,
    nms_dist: int = 4,
    conf_thresh: float = 0.015,
    device: str = 'cuda'
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Detect features using SuperPoint (learning-based)
    
    Best for:
    - Tone-on-tone fabrics
    - Low-texture scenarios
    - GPU-accelerated processing
    
    Note: Requires PyTorch and pre-trained weights
    
    Args:
        image: Grayscale image
        model_path: Path to SuperPoint weights
        nms_dist: Non-maximum suppression distance
        conf_thresh: Confidence threshold
        device: 'cuda' or 'cpu'
    
    Returns:
        keypoints: (N, 2) array of keypoint coordinates
        descriptors: (N, 256) feature descriptors
    """
    try:
        import torch
        # TODO: Load SuperPoint model from official repo or pre-trained weights
        # Placeholder for future implementation
        raise NotImplementedError("SuperPoint integration coming in Week 3")
        
    except ImportError:
        logger.error("PyTorch not installed. Required for SuperPoint.")
        raise
