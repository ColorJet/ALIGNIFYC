"""
VoxelMorph Backend for Fabric Registration (TensorFlow)
Wraps VoxelMorph 2D registration for deformable fabric alignment

References:
- Paper: https://arxiv.org/abs/1809.05231
- Code: https://github.com/voxelmorph/voxelmorph

Note: VoxelMorph uses TensorFlow backend, not PyTorch
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class VoxelMorphRegistration:
    """
    VoxelMorph-based deformable registration for fabric images
    
    Features:
    - GPU-accelerated inference (<1s per 512x512 image with TensorFlow+CUDA)
    - Unsupervised learning (no ground truth needed for training)
    - Smooth, diffeomorphic deformations
    - CPU fallback when GPU unavailable
    
    Note: Uses TensorFlow backend
    """
    
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True, inshape: Tuple[int, int] = (512, 512)):
        """
        Initialize VoxelMorph registration backend
        
        Args:
            model_path: Path to pre-trained model (.h5 file). If None, creates default U-Net.
            use_gpu: Use GPU if available (requires TensorFlow with CUDA)
            inshape: Input image shape (H, W) - default 512x512
        """
        self.model = None
        self.model_path = model_path
        self.inshape = inshape
        
        # Check if VoxelMorph and TensorFlow are installed
        try:
            import voxelmorph as vxm
            import tensorflow as tf
            self.vxm = vxm
            self.tf = tf
            self.available = True
            
            # Configure GPU
            if use_gpu:
                gpus = tf.config.list_physical_devices('GPU')
                if gpus:
                    try:
                        # Enable memory growth to avoid OOM
                        for gpu in gpus:
                            tf.config.experimental.set_memory_growth(gpu, True)
                        self.device = 'cuda'
                        logger.info(f"✓ VoxelMorph available (device: GPU, {len(gpus)} GPU(s) found)")
                    except RuntimeError as e:
                        logger.warning(f"GPU configuration failed: {e}, falling back to CPU")
                        self.device = 'cpu'
                else:
                    self.device = 'cpu'
                    logger.info("✓ VoxelMorph available (device: CPU - no GPU found)")
            else:
                self.device = 'cpu'
                logger.info("✓ VoxelMorph available (device: CPU - GPU disabled)")
                
        except ImportError as e:
            self.vxm = None
            self.tf = None
            self.available = False
            self.device = 'cpu'
            logger.warning(f"✗ VoxelMorph not installed. Run: pip install voxelmorph tensorflow")
    
    def load_model(self, model_path: Optional[str] = None):
        """
        Load VoxelMorph model
        
        Args:
            model_path: Path to pre-trained .h5 model. If None, creates default U-Net.
        """
        if not self.available:
            raise RuntimeError("VoxelMorph not available. Install: pip install voxelmorph tensorflow")
        
        model_path = model_path or self.model_path
        
        if model_path and Path(model_path).exists():
            # Load pre-trained model
            logger.info(f"Loading VoxelMorph model from: {model_path}")
            self.model = self.tf.keras.models.load_model(
                model_path,
                custom_objects={'SpatialTransformer': self.vxm.layers.SpatialTransformer}
            )
        else:
            # Create default VoxelMorph U-Net
            logger.info(f"Creating default VoxelMorph U-Net (inshape={self.inshape})")
            
            # VoxelMorph 2D model: (fixed, moving) -> (warped, flow)
            ndims = 2
            unet_input_features = 2  # Fixed and moving images concatenated
            
            # Build U-Net encoder-decoder
            nb_features = [
                [32, 32, 32, 32],         # Encoder features per layer
                [32, 32, 32, 32, 32, 16]  # Decoder features per layer
            ]
            
            # Create VoxelMorph model
            self.model = self.vxm.networks.VxmDense(
                inshape=self.inshape,
                nb_unet_features=nb_features,
                int_steps=7,  # Integration steps for diffeomorphic flow
                int_downsize=2
            )
            
        logger.info(f"VoxelMorph model loaded (device: {self.device})")
    
    def register(
        self, 
        fixed: np.ndarray, 
        moving: np.ndarray,
        return_warped: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Register moving image to fixed image using VoxelMorph
        
        Args:
            fixed: Fixed image (H, W) or (H, W, 1) grayscale
            moving: Moving image (same shape as fixed)
            return_warped: Return warped image (always True for now)
        
        Returns:
            warped: Warped moving image aligned to fixed
            deformation_field: Dense deformation field (H, W, 2) with (dx, dy)
            metadata: Registration statistics (runtime, device, etc.)
        """
        import time
        
        if not self.available:
            raise RuntimeError("VoxelMorph not available")
        
        if self.model is None:
            self.load_model()
        
        start = time.perf_counter()
        
        # Preprocess images
        fixed_preprocessed = self._preprocess(fixed)
        moving_preprocessed = self._preprocess(moving)
        
        # Run registration (TensorFlow inference)
        moved, flow = self.model.predict([moving_preprocessed, fixed_preprocessed], verbose=0)
        
        # Post-process outputs
        warped_image = self._denormalize(moved[0, ..., 0], moving)
        deformation_field = flow[0, ...]  # (H, W, 2)
        
        runtime = time.perf_counter() - start
        
        # Compute statistics
        flow_magnitude = np.sqrt(np.sum(deformation_field ** 2, axis=-1))
        
        metadata = {
            'method': 'voxelmorph',
            'device': self.device,
            'runtime_seconds': runtime,
            'mean_displacement': float(flow_magnitude.mean()),
            'max_displacement': float(flow_magnitude.max()),
            'flow_shape': deformation_field.shape,
            'model_inshape': self.inshape
        }
        
        logger.info(f"VoxelMorph registration: {runtime:.3f}s, mean disp={flow_magnitude.mean():.2f}px (device: {self.device})")
        
        return warped_image, deformation_field, metadata
    
    def warp_image(
        self,
        image: np.ndarray,
        deformation_field: np.ndarray
    ) -> np.ndarray:
        """
        Apply pre-computed deformation field to an image
        
        Args:
            image: Image to warp (H, W) or (H, W, C)
            deformation_field: Deformation field (H, W, 2) from register()
        
        Returns:
            warped: Warped image same shape as input
        """
        if not self.available:
            raise RuntimeError("VoxelMorph not available")
        
        # Preprocess image
        image_preprocessed = self._preprocess(image)
        
        # Expand deformation field to batch dimension
        flow_batch = np.expand_dims(deformation_field, axis=0)
        
        # Apply spatial transformation
        spatial_transformer = self.vxm.layers.SpatialTransformer()
        warped = spatial_transformer([image_preprocessed, flow_batch])
        
        # Denormalize
        warped_image = self._denormalize(warped[0, ..., 0], image)
        
        return warped_image
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for VoxelMorph (TensorFlow format)
        
        Args:
            image: Input image (H, W) or (H, W, C)
        
        Returns:
            preprocessed: Image tensor (1, H, W, 1) normalized to [0, 1]
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            image = np.mean(image, axis=2)
        
        # Normalize to [0, 1]
        if image.dtype == np.uint8:
            normalized = image.astype(np.float32) / 255.0
        else:
            normalized = (image - image.min()) / (image.max() - image.min() + 1e-8)
        
        # Resize to model input shape if needed
        if normalized.shape[:2] != self.inshape:
            import cv2
            normalized = cv2.resize(normalized, (self.inshape[1], self.inshape[0]))
        
        # Add batch and channel dimensions: (H, W) -> (1, H, W, 1)
        preprocessed = normalized[np.newaxis, ..., np.newaxis]
        
        return preprocessed.astype(np.float32)
    
    def _denormalize(self, tensor: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """
        Denormalize output tensor back to original image format
        
        Args:
            tensor: Normalized tensor from model
            reference: Original image for dtype/range reference
        
        Returns:
            image: Denormalized image matching reference dtype
        """
        # Clip to [0, 1]
        tensor = np.clip(tensor, 0, 1)
        
        # Resize back to reference shape if needed
        if tensor.shape[:2] != reference.shape[:2]:
            import cv2
            tensor = cv2.resize(tensor, (reference.shape[1], reference.shape[0]))
        
        # Convert back to original dtype
        if reference.dtype == np.uint8:
            return (tensor * 255).astype(np.uint8)
        else:
            # Match reference range
            ref_min, ref_max = reference.min(), reference.max()
            return (tensor * (ref_max - ref_min) + ref_min).astype(reference.dtype)


def register_voxelmorph(
    fixed: np.ndarray,
    moving: np.ndarray,
    model_path: Optional[str] = None,
    use_gpu: bool = True,
    inshape: Tuple[int, int] = (512, 512)
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Convenience function for VoxelMorph registration
    
    Args:
        fixed: Fixed image
        moving: Moving image
        model_path: Optional path to pre-trained model
        use_gpu: Use GPU if available
        inshape: Model input shape
    
    Returns:
        warped, deformation_field, metadata
    
    Example:
        >>> warped, flow, meta = register_voxelmorph(fixed_img, moving_img, use_gpu=True)
        >>> print(f"Registration took {meta['runtime_seconds']:.3f}s on {meta['device']}")
    """
    backend = VoxelMorphRegistration(model_path=model_path, use_gpu=use_gpu, inshape=inshape)
    backend.load_model()
    return backend.register(fixed, moving)
