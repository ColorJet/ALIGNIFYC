"""
VoxelMorph PyTorch Backend with Training Support
Learn deformable registration from Elastix examples

Key Features:
- Pure PyTorch implementation (uses existing Alinify GPU setup)
- Train on Elastix registration pairs (unsupervised learning)
- Manual training by operator through GUI
- Fast inference (<1s on GPU)
- Compatible with existing PyTorch 2.9.1+cu130
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Optional, List
import logging
import json
import time

logger = logging.getLogger(__name__)


class SpatialTransformer(nn.Module):
    """
    N-D Spatial Transformer
    Applies deformation field to images
    """
    def __init__(self, size, mode='bilinear'):
        super().__init__()
        self.mode = mode
        
        # Create sampling grid
        vectors = [torch.arange(0, s) for s in size]
        grids = torch.meshgrid(vectors, indexing='ij')
        grid = torch.stack(grids)
        grid = torch.unsqueeze(grid, 0)
        grid = grid.type(torch.FloatTensor)
        
        # Registering as buffer for proper device handling
        self.register_buffer('grid', grid)
    
    def forward(self, src, flow):
        """
        Apply deformation to source image
        
        Args:
            src: [B, C, H, W] source image
            flow: [B, 2, H, W] displacement field (dx, dy)
        
        Returns:
            Warped image [B, C, H, W]
        """
        new_locs = self.grid + flow
        shape = flow.shape[2:]
        
        # Normalize to [-1, 1] for grid_sample
        for i in range(len(shape)):
            new_locs[:, i, ...] = 2 * (new_locs[:, i, ...] / (shape[i] - 1) - 0.5)
        
        # Permute to [B, H, W, 2] for grid_sample
        new_locs = new_locs.permute(0, 2, 3, 1)
        new_locs = new_locs[..., [1, 0]]  # Swap to (y, x) order for grid_sample
        
        return F.grid_sample(src, new_locs, align_corners=True, mode=self.mode)


class UNet(nn.Module):
    """
    U-Net architecture for VoxelMorph
    Encoder-decoder with skip connections
    """
    def __init__(self, in_channels=2, enc_features=[32, 32, 32, 32], dec_features=[32, 32, 32, 32, 32, 16]):
        super().__init__()
        
        # Encoder
        self.enc_blocks = nn.ModuleList()
        features = in_channels
        for f in enc_features:
            self.enc_blocks.append(nn.Sequential(
                nn.Conv2d(features, f, 3, stride=2, padding=1),
                nn.LeakyReLU(0.2)
            ))
            features = f
        
        # Decoder
        self.dec_blocks = nn.ModuleList()
        for i, f in enumerate(dec_features):
            # Skip connection channels from encoder
            skip_channels = enc_features[-(i+1)] if i < len(enc_features) else 0
            in_f = features + skip_channels
            self.dec_blocks.append(nn.Sequential(
                nn.Conv2d(in_f, f, 3, padding=1),
                nn.LeakyReLU(0.2),
                nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            ))
            features = f
        
        # Flow output layer
        self.flow = nn.Conv2d(features, 2, 3, padding=1)
        self.flow.weight = nn.Parameter(torch.zeros(self.flow.weight.shape))
        self.flow.bias = nn.Parameter(torch.zeros(self.flow.bias.shape))
    
    def forward(self, x):
        """
        Forward pass through U-Net
        
        Args:
            x: [B, C, H, W] concatenated fixed and moving images
        
        Returns:
            Flow field [B, 2, H, W]
        """
        # Encoder with skip connections
        enc_features = []
        for enc_block in self.enc_blocks:
            x = enc_block(x)
            enc_features.append(x)
        
        # Decoder with skip connections
        for i, dec_block in enumerate(self.dec_blocks):
            if i < len(enc_features):
                skip = enc_features[-(i+1)]
                x = torch.cat([x, skip], dim=1)
            x = dec_block(x)
        
        # Flow prediction
        flow = self.flow(x)
        return flow


class VoxelMorphPyTorch(nn.Module):
    """
    VoxelMorph registration network (PyTorch)
    """
    def __init__(self, inshape=(512, 512)):
        super().__init__()
        self.inshape = inshape
        
        # U-Net for flow prediction
        self.unet = UNet(in_channels=2)
        
        # Spatial transformer
        self.spatial_transformer = SpatialTransformer(inshape)
    
    def forward(self, fixed, moving):
        """
        Register moving to fixed image
        
        Args:
            fixed: [B, 1, H, W]
            moving: [B, 1, H, W]
        
        Returns:
            moved: Warped moving image [B, 1, H, W]
            flow: Displacement field [B, 2, H, W]
        """
        # Concatenate fixed and moving
        x = torch.cat([fixed, moving], dim=1)
        
        # Predict flow
        flow = self.unet(x)
        
        # Warp moving image
        moved = self.spatial_transformer(moving, flow)
        
        return moved, flow


class VoxelMorphRegistrationPyTorch:
    """
    VoxelMorph registration with PyTorch
    Supports training from Elastix examples
    """
    
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = True, inshape: Tuple[int, int] = (512, 512)):
        """
        Initialize VoxelMorph PyTorch backend
        
        Args:
            model_path: Path to trained .pth model
            use_gpu: Use GPU if available
            inshape: Input shape (H, W)
        """
        self.inshape = inshape
        self.model_path = model_path
        
        # Check PyTorch availability
        self.available = True
        try:
            if use_gpu and torch.cuda.is_available():
                self.device = torch.device('cuda')
                logger.info(f"✓ VoxelMorph PyTorch (device: GPU - {torch.cuda.get_device_name(0)})")
            else:
                self.device = torch.device('cpu')
                logger.info("✓ VoxelMorph PyTorch (device: CPU)")
        except Exception as e:
            logger.error(f"✗ PyTorch initialization failed: {e}")
            self.available = False
            self.device = torch.device('cpu')
        
        self.model = None
    
    def load_model(self, model_path: Optional[str] = None):
        """Load trained model or create new one"""
        model_path = model_path or self.model_path
        
        # Create model
        self.model = VoxelMorphPyTorch(inshape=self.inshape).to(self.device)
        
        if model_path and Path(model_path).exists():
            logger.info(f"Loading trained model: {model_path}")
            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            logger.info("✓ Model loaded")
        else:
            logger.info("Created new VoxelMorph U-Net (untrained)")
        
        self.model.eval()
    
    def register(
        self,
        fixed: np.ndarray,
        moving: np.ndarray,
        return_warped: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Register moving to fixed image
        
        Args:
            fixed: Fixed image (H, W) or (H, W, C)
            moving: Moving image (same shape)
            return_warped: Return warped image
        
        Returns:
            warped: Warped moving image
            deformation: Displacement field (H, W, 2)
            metadata: Registration info
        """
        if self.model is None:
            self.load_model()
        
        start = time.perf_counter()
        
        # Preprocess
        fixed_tensor = self._preprocess(fixed)
        moving_tensor = self._preprocess(moving)
        
        # Register
        with torch.no_grad():
            moved, flow = self.model(fixed_tensor, moving_tensor)
        
        # Post-process
        warped_image = self._denormalize(moved[0, 0].cpu().numpy(), moving)
        deformation_field = flow[0].permute(1, 2, 0).cpu().numpy()  # [H, W, 2]
        
        runtime = time.perf_counter() - start
        
        # Stats
        flow_magnitude = np.sqrt(np.sum(deformation_field ** 2, axis=-1))
        
        metadata = {
            'method': 'voxelmorph_pytorch',
            'device': str(self.device),
            'runtime_seconds': runtime,
            'mean_displacement': float(flow_magnitude.mean()),
            'max_displacement': float(flow_magnitude.max()),
            'flow_shape': deformation_field.shape,
            'model_inshape': self.inshape
        }
        
        logger.info(f"VoxelMorph PyTorch: {runtime:.3f}s, disp={flow_magnitude.mean():.2f}px ({self.device})")
        
        return warped_image, deformation_field, metadata
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image to tensor"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            image = np.mean(image, axis=2)
        
        # Normalize
        if image.dtype == np.uint8:
            normalized = image.astype(np.float32) / 255.0
        else:
            normalized = (image - image.min()) / (image.max() - image.min() + 1e-8)
        
        # Resize if needed
        if normalized.shape != self.inshape:
            import cv2
            normalized = cv2.resize(normalized, (self.inshape[1], self.inshape[0]))
        
        # To tensor [1, 1, H, W]
        tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0).float()
        return tensor.to(self.device)
    
    def _denormalize(self, tensor: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """Denormalize output"""
        tensor = np.clip(tensor, 0, 1)
        
        # Resize to reference
        if tensor.shape != reference.shape[:2]:
            import cv2
            tensor = cv2.resize(tensor, (reference.shape[1], reference.shape[0]))
        
        # Convert to reference dtype
        if reference.dtype == np.uint8:
            return (tensor * 255).astype(np.uint8)
        else:
            ref_min, ref_max = reference.min(), reference.max()
            return (tensor * (ref_max - ref_min) + ref_min).astype(reference.dtype)


class VoxelMorphTrainer:
    """
    Train VoxelMorph from Elastix registration pairs
    Operator can collect training data and train model
    """
    
    def __init__(self, model_path: str = "models/voxelmorph_fabric.pth", inshape: Tuple[int, int] = (512, 512)):
        """
        Initialize trainer
        
        Args:
            model_path: Where to save trained model
            inshape: Training image size
        """
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.inshape = inshape
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Create model
        self.model = VoxelMorphPyTorch(inshape=inshape).to(self.device)
        
        # Training data storage
        self.training_data_dir = Path("data/voxelmorph_training")
        self.training_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"VoxelMorph Trainer initialized (device: {self.device})")
    
    def add_training_pair(
        self,
        fixed: np.ndarray,
        moving: np.ndarray,
        deformation: Optional[np.ndarray] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add Elastix registration pair to training dataset
        
        Args:
            fixed: Fixed image
            moving: Moving image
            deformation: Elastix deformation field (optional - for supervised learning)
            metadata: Registration metadata
        
        Returns:
            sample_id: Unique ID for this training sample
        """
        import cv2
        
        # Generate unique ID
        sample_id = f"sample_{int(time.time() * 1000)}"
        sample_dir = self.training_data_dir / sample_id
        sample_dir.mkdir(exist_ok=True)
        
        # Save images
        cv2.imwrite(str(sample_dir / "fixed.png"), fixed)
        cv2.imwrite(str(sample_dir / "moving.png"), moving)
        
        # Save deformation if provided
        if deformation is not None:
            np.save(sample_dir / "deformation.npy", deformation)
        
        # Save metadata
        if metadata:
            with open(sample_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
        
        logger.info(f"✓ Training pair added: {sample_id}")
        return sample_id
    
    def load_training_data(self) -> List[Dict]:
        """Load all training pairs"""
        training_pairs = []
        
        for sample_dir in self.training_data_dir.iterdir():
            if not sample_dir.is_dir():
                continue
            
            fixed_path = sample_dir / "fixed.png"
            moving_path = sample_dir / "moving.png"
            
            if not (fixed_path.exists() and moving_path.exists()):
                continue
            
            import cv2
            fixed = cv2.imread(str(fixed_path), cv2.IMREAD_GRAYSCALE)
            moving = cv2.imread(str(moving_path), cv2.IMREAD_GRAYSCALE)
            
            # Load deformation if available
            deform_path = sample_dir / "deformation.npy"
            deformation = np.load(deform_path) if deform_path.exists() else None
            
            training_pairs.append({
                'fixed': fixed,
                'moving': moving,
                'deformation': deformation,
                'sample_id': sample_dir.name
            })
        
        logger.info(f"Loaded {len(training_pairs)} training pairs")
        return training_pairs
    
    def train(
        self,
        epochs: int = 100,
        batch_size: int = 4,
        learning_rate: float = 1e-4,
        smoothness_weight: float = 0.01,
        progress_callback = None
    ) -> Dict:
        """
        Train VoxelMorph model on collected data
        
        Args:
            epochs: Number of training epochs
            batch_size: Batch size (keep small for limited data)
            learning_rate: Adam learning rate
            smoothness_weight: Weight for flow smoothness regularization
            progress_callback: Optional callback(epoch, loss) for GUI updates
        
        Returns:
            Training history
        """
        # Load training data
        training_pairs = self.load_training_data()
        
        if len(training_pairs) == 0:
            raise ValueError("No training data found! Add pairs with add_training_pair()")
        
        logger.info(f"Training with {len(training_pairs)} pairs for {epochs} epochs")
        
        # Setup training
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # Losses
        mse_loss = nn.MSELoss()
        
        history = {'epoch': [], 'loss': [], 'similarity_loss': [], 'smoothness_loss': []}
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_sim_loss = 0.0
            epoch_smooth_loss = 0.0
            
            # Mini-batch training
            for i in range(0, len(training_pairs), batch_size):
                batch = training_pairs[i:i+batch_size]
                
                # Prepare batch
                fixed_batch = []
                moving_batch = []
                
                for pair in batch:
                    fixed_tensor = self._preprocess_train(pair['fixed'])
                    moving_tensor = self._preprocess_train(pair['moving'])
                    fixed_batch.append(fixed_tensor)
                    moving_batch.append(moving_tensor)
                
                fixed_batch = torch.cat(fixed_batch, dim=0)
                moving_batch = torch.cat(moving_batch, dim=0)
                
                # Forward pass
                moved, flow = self.model(fixed_batch, moving_batch)
                
                # Similarity loss (MSE between warped and fixed)
                sim_loss = mse_loss(moved, fixed_batch)
                
                # Smoothness regularization (penalize large gradients in flow)
                smooth_loss = self._smoothness_loss(flow)
                
                # Total loss
                total_loss = sim_loss + smoothness_weight * smooth_loss
                
                # Backward pass
                optimizer.zero_grad()
                total_loss.backward()
                optimizer.step()
                
                epoch_loss += total_loss.item()
                epoch_sim_loss += sim_loss.item()
                epoch_smooth_loss += smooth_loss.item()
            
            # Average losses
            n_batches = (len(training_pairs) + batch_size - 1) // batch_size
            epoch_loss /= n_batches
            epoch_sim_loss /= n_batches
            epoch_smooth_loss /= n_batches
            
            # Record history
            history['epoch'].append(epoch + 1)
            history['loss'].append(epoch_loss)
            history['similarity_loss'].append(epoch_sim_loss)
            history['smoothness_loss'].append(epoch_smooth_loss)
            
            # Progress callback
            if progress_callback:
                progress_callback(epoch + 1, epoch_loss)
            
            # Log progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(f"Epoch {epoch+1}/{epochs}: loss={epoch_loss:.4f}, "
                          f"sim={epoch_sim_loss:.4f}, smooth={epoch_smooth_loss:.4f}")
        
        # Save model
        self.save_model()
        
        logger.info(f"✓ Training complete! Model saved to {self.model_path}")
        return history
    
    def _preprocess_train(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess for training"""
        # Normalize
        if image.dtype == np.uint8:
            normalized = image.astype(np.float32) / 255.0
        else:
            normalized = (image - image.min()) / (image.max() - image.min() + 1e-8)
        
        # Resize
        if normalized.shape != self.inshape:
            import cv2
            normalized = cv2.resize(normalized, (self.inshape[1], self.inshape[0]))
        
        # To tensor
        tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0).float()
        return tensor.to(self.device)
    
    def _smoothness_loss(self, flow: torch.Tensor) -> torch.Tensor:
        """
        Compute flow smoothness penalty
        Penalizes large gradients in the flow field
        """
        # Gradient in x direction
        dx = torch.abs(flow[:, :, :, :-1] - flow[:, :, :, 1:])
        # Gradient in y direction
        dy = torch.abs(flow[:, :, :-1, :] - flow[:, :, 1:, :])
        
        return dx.mean() + dy.mean()
    
    def save_model(self, path: Optional[str] = None):
        """Save trained model"""
        save_path = Path(path) if path else self.model_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        torch.save(self.model.state_dict(), save_path)
        logger.info(f"✓ Model saved: {save_path}")
    
    def get_training_stats(self) -> Dict:
        """Get statistics about training data"""
        n_samples = len(list(self.training_data_dir.iterdir()))
        
        return {
            'n_samples': n_samples,
            'training_data_dir': str(self.training_data_dir),
            'model_path': str(self.model_path),
            'inshape': self.inshape
        }


# Convenience functions
def register_voxelmorph_pytorch(
    fixed: np.ndarray,
    moving: np.ndarray,
    model_path: Optional[str] = None,
    use_gpu: bool = True,
    inshape: Tuple[int, int] = (512, 512)
) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Convenience function for VoxelMorph PyTorch registration
    """
    backend = VoxelMorphRegistrationPyTorch(model_path=model_path, use_gpu=use_gpu, inshape=inshape)
    backend.load_model()
    return backend.register(fixed, moving)
