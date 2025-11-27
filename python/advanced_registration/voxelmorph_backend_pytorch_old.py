"""
VoxelMorph Backend for Fabric Registration
Wraps VoxelMorph 2D registration for deformable fabric alignment

References:
- Paper: https://arxiv.org/abs/1809.05231
- Code: https://github.com/voxelmorph/voxelmorph
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
    - GPU-accelerated inference (<1s per 1024x1024 image with TensorFlow+CUDA)
    - Unsupervised learning (no ground truth needed for training)
    - Smooth, diffeomorphic deformations
    - CPU fallback when GPU unavailable
    
    Note: VoxelMorph uses TensorFlow backend, not PyTorch
    """
    
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True):
        """
        Initialize VoxelMorph registration backend
        
        Args:
            model_path: Path to pre-trained model (.h5 file). If None, use default.
            use_gpu: Use GPU if available (requires TensorFlow with CUDA)
        """
        self.model = None
        self.model_path = model_path
        
        # Check if VoxelMorph and TensorFlow are installed
        try:
            import voxelmorph as vxm
            import tensorflow as tf
            self.vxm = vxm
            self.tf = tf
            self.available = True
            
            # Set device (TensorFlow auto-handles GPU)
            gpus = tf.config.list_physical_devices('GPU')
            if use_gpu and gpus:
                self.device = 'cuda'  # For compatibility with our API
                logger.info(f"✓ VoxelMorph available (device: GPU, {len(gpus)} GPU(s) found)")
            else:
                self.device = 'cpu'
                logger.info(f"✓ VoxelMorph available (device: CPU)")
                
        except ImportError as e:
            self.vxm = None
            self.tf = None
            self.available = False
            self.device = 'cpu'
            logger.warning("✗ VoxelMorph not installed. Run: pip install voxelmorph")
    
    def _setup_device(self, use_gpu: bool) -> torch.device:
        """Detect and configure computation device"""
        if use_gpu and torch.cuda.is_available():
            device = torch.device('cuda:0')
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            device = torch.device('cpu')
            if use_gpu:
                logger.warning("GPU requested but not available, using CPU")
            else:
                logger.info("Using CPU (set use_gpu=True for speedup)")
        return device
    
    def load_model(self, model_path: Optional[str] = None):
        """
        Load pre-trained VoxelMorph model
        
        Args:
            model_path: Path to .pt checkpoint. If None, use default or create new model.
        """
        if not self.available:
            raise RuntimeError("VoxelMorph not installed")
        
        if model_path is None:
            model_path = self.model_path
        
        # Check if model exists
        if model_path and Path(model_path).exists():
            logger.info(f"Loading pre-trained model: {model_path}")
            self.model = torch.load(model_path, map_location=self.device)
            self.model.eval()
        else:
            # Create default 2D U-Net architecture
            logger.info("Creating default VoxelMorph U-Net model")
            inshape = (512, 512)  # Will be resized dynamically
            nb_features = [[16, 32, 32, 32], [32, 32, 32, 32, 32, 16, 16]]
            
            self.model = self.vxm.networks.VxmDense(
                inshape=inshape,
                nb_unet_features=nb_features,
                int_steps=7  # Integration steps for diffeomorphic warp
            ).to(self.device)
            
            logger.warning("Using untrained model - consider fine-tuning on fabric data")
    
    def register(
        self,
        fixed: np.ndarray,
        moving: np.ndarray,
        return_warped: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Register moving image to fixed image using VoxelMorph
        
        Args:
            fixed: Fixed/reference image (H, W) or (H, W, C)
            moving: Moving image to align (H, W) or (H, W, C)
            return_warped: If True, return warped moving image
        
        Returns:
            warped_image: Registered moving image (if return_warped=True, else None)
            deformation_field: Dense displacement field (H, W, 2)
            metadata: Dictionary with registration info
        """
        if not self.available:
            raise RuntimeError("VoxelMorph not installed")
        
        if self.model is None:
            self.load_model()
        
        import time
        start_time = time.time()
        
        # Preprocess images
        fixed_tensor = self._preprocess(fixed)
        moving_tensor = self._preprocess(moving)
        
        # Run inference
        with torch.no_grad():
            # VoxelMorph expects (batch, channel, height, width)
            moved, flow = self.model(moving_tensor, fixed_tensor, registration=True)
        
        # Convert flow to numpy deformation field
        # VoxelMorph outputs flow in (batch, 2, H, W) format
        flow_np = flow.squeeze().cpu().numpy()  # (2, H, W)
        deformation_field = np.transpose(flow_np, (1, 2, 0))  # (H, W, 2)
        
        # Warp image if requested
        if return_warped:
            warped = moved.squeeze().cpu().numpy()
            if warped.ndim == 2:
                warped_image = warped
            else:
                # Handle multi-channel
                warped_image = np.transpose(warped, (1, 2, 0))
            
            # Denormalize
            warped_image = self._denormalize(warped_image, moving)
        else:
            warped_image = None
        
        elapsed = time.time() - start_time
        
        # Compute quality metrics
        metadata = {
            'method': 'VoxelMorph',
            'device': str(self.device),
            'elapsed_time': elapsed,
            'deformation_magnitude': np.linalg.norm(deformation_field, axis=2).mean(),
            'max_displacement': np.linalg.norm(deformation_field, axis=2).max(),
            'model_path': self.model_path
        }
        
        logger.info(f"VoxelMorph registration completed in {elapsed:.3f}s")
        
        return warped_image, deformation_field, metadata
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Convert numpy image to torch tensor with normalization
        
        Args:
            image: Input image (H, W) or (H, W, C)
        
        Returns:
            Normalized tensor (1, 1, H, W) for grayscale or (1, C, H, W)
        """
        # Convert to grayscale if RGB
        if image.ndim == 3:
            import cv2
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Normalize to [0, 1]
        normalized = gray.astype(np.float32) / 255.0
        
        # Add batch and channel dims: (H, W) -> (1, 1, H, W)
        tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0)
        
        return tensor.to(self.device)
    
    def _denormalize(self, warped: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """Denormalize warped image to original intensity range"""
        warped = np.clip(warped * 255.0, 0, 255).astype(np.uint8)
        
        # Match shape of reference
        if reference.ndim == 3 and warped.ndim == 2:
            # Convert grayscale to RGB if needed
            warped = np.stack([warped] * 3, axis=-1)
        
        return warped
    
    def warp_image(
        self,
        image: np.ndarray,
        deformation_field: np.ndarray
    ) -> np.ndarray:
        """
        Apply pre-computed deformation field to warp an image
        
        Args:
            image: Image to warp (H, W) or (H, W, C)
            deformation_field: Displacement field (H, W, 2)
        
        Returns:
            Warped image
        """
        # Convert to torch tensors
        if image.ndim == 2:
            image_tensor = torch.from_numpy(image).unsqueeze(0).unsqueeze(0).float()
        else:
            # (H, W, C) -> (1, C, H, W)
            image_tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0).float()
        
        image_tensor = image_tensor.to(self.device)
        
        # Deformation field: (H, W, 2) -> (1, H, W, 2)
        flow_tensor = torch.from_numpy(deformation_field).unsqueeze(0).float().to(self.device)
        
        # Apply spatial transformation
        with torch.no_grad():
            warped = self._apply_flow(image_tensor, flow_tensor)
        
        # Convert back to numpy
        warped_np = warped.squeeze().cpu().numpy()
        
        if image.ndim == 3:
            warped_np = np.transpose(warped_np, (1, 2, 0))
        
        return warped_np.astype(image.dtype)
    
    def _apply_flow(self, image: torch.Tensor, flow: torch.Tensor) -> torch.Tensor:
        """Apply optical flow to warp image using grid_sample"""
        batch, channels, height, width = image.shape
        
        # Create sampling grid
        grid_y, grid_x = torch.meshgrid(
            torch.arange(height, device=self.device),
            torch.arange(width, device=self.device),
            indexing='ij'
        )
        grid = torch.stack([grid_x, grid_y], dim=-1).float()  # (H, W, 2)
        
        # Add flow to grid
        new_grid = grid + flow.squeeze(0)  # (H, W, 2)
        
        # Normalize grid to [-1, 1] for grid_sample
        new_grid[..., 0] = 2.0 * new_grid[..., 0] / (width - 1) - 1.0
        new_grid[..., 1] = 2.0 * new_grid[..., 1] / (height - 1) - 1.0
        
        # Add batch dim and sample
        new_grid = new_grid.unsqueeze(0)  # (1, H, W, 2)
        warped = F.grid_sample(
            image, new_grid,
            mode='bilinear',
            padding_mode='border',
            align_corners=True
        )
        
        return warped


# Convenience function for quick registration
def register_voxelmorph(
    fixed: np.ndarray,
    moving: np.ndarray,
    model_path: Optional[str] = None,
    use_gpu: bool = True
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Quick VoxelMorph registration without explicit backend initialization
    
    Args:
        fixed: Fixed image
        moving: Moving image
        model_path: Optional pre-trained model path
        use_gpu: Use GPU acceleration
    
    Returns:
        warped_image, deformation_field, metadata
    """
    backend = VoxelMorphRegistration(model_path=model_path, use_gpu=use_gpu)
    return backend.register(fixed, moving, return_warped=True)
