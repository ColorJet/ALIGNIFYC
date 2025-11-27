"""
Registration backend for Alinify GUI
Wraps Elastix registration for real-time use
"""

import numpy as np
from pathlib import Path
import time
from typing import Optional, Tuple, Dict
import cv2
import sys
import io
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from datetime import datetime


class _StreamTee(io.TextIOBase):
    """Duplicate writes to original stream and log file."""

    def __init__(self, primary, secondary):
        super().__init__()
        self.primary = primary
        self.secondary = secondary

    def write(self, message):
        if self.primary is not None:
            self.primary.write(message)
        if self.secondary is not None:
            self.secondary.write(message)
        return len(message)

    def flush(self):
        if self.primary is not None:
            try:
                self.primary.flush()
            except (ValueError, OSError):
                pass  # File already closed
        if self.secondary is not None:
            try:
                self.secondary.flush()
            except (ValueError, OSError):
                pass  # File already closed

try:
    from .elastix_registration import ElastixFabricRegistration
    from .elastix_config import ElastixConfig
    ELASTIX_AVAILABLE = True
except ImportError:
    try:
        from elastix_registration import ElastixFabricRegistration
        from elastix_config import ElastixConfig
        ELASTIX_AVAILABLE = True
    except ImportError:
        ELASTIX_AVAILABLE = False
        print("WARNING: Elastix registration not available")


class RegistrationBackend:
    """
    Unified registration backend for Alinify GUI
    Supports both Python-Elastix and future C++ bindings
    """
    
    def __init__(self, mode='elastix', config_path='config/elastix_config.yaml'):
        """
        Initialize registration backend
        
        Args:
            mode: 'elastix' (Python-ITK) or 'cpp' (C++ bindings - future)
            config_path: Path to elastix config YAML file
        """
        self.mode = mode
        self.config = ElastixConfig(config_path)
        
        if mode == 'elastix':
            if not ELASTIX_AVAILABLE:
                raise RuntimeError("Elastix registration not available. Please install ITK-Elastix.")
            
            # Initialize with debug/log settings from config
            self.engine = ElastixFabricRegistration(
                use_clean_parameters=True,
                debug_mode=self.config.get('debug_mode', False),
                log_to_file=self.config.get('log_to_file', None)
            )
            # print("[OK] Using Python-Elastix registration engine with clean parameters")
        elif mode == 'cpp':
            # TODO: Load C++ bindings when available
            raise NotImplementedError("C++ bindings not yet implemented")
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        # Registration results cache
        self.last_deformation = None
        self.last_metadata = None
        self.last_preview_warp = None  # Preview warped image at low resolution
        
        # GPU acceleration settings
        self.warp_acceleration_mode = 'warp'  # Default to Warp if available
        
        # Manual correction points: list of [(x, y, dx, dy), ...]
        
        # Store paths for high-res warp (persistent across calls)
        self.moving_rgb_path = None
        self.fixed_path = None
        self.moving_path = None
        self.temp_dir = None
        self.manual_corrections = []

        # Logging
        self.log_path = Path("logs") / "elastix_engine.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _log(self, message: str):
        """Log message with timestamp to stdout (and file when captured)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # print(f"[Registration Backend] {timestamp} - {message}")

    @contextmanager
    def _capture_logs(self):
        """Capture stdout/stderr from Elastix into log file while preserving console output."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        with self.log_path.open("a", encoding="utf-8") as log_file:
            header = "\n===== Elastix Session {} =====\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log_file.write(header)
            log_file.flush()
            tee_out = _StreamTee(original_stdout, log_file)
            tee_err = _StreamTee(original_stderr, log_file)
            with redirect_stdout(tee_out), redirect_stderr(tee_err):
                yield

    def register(self, 
                 fixed_image: np.ndarray,
                 moving_image: np.ndarray,
                 parameters: Optional[Dict] = None,
                 preview_only: bool = False) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Register two images
        
        Args:
            fixed_image: Camera/reference image (grayscale or RGB)
            moving_image: Design/moving image (grayscale or RGB)
            parameters: Registration parameters dict
            preview_only: If True, only warp downsampled preview (for manual correction)
        
        Returns:
            registered_image: Warped moving image (RGB) - preview or full-res
            deformation_field: [H, W, 2] displacement field
            metadata: Registration quality metrics
        """
        if self.mode == 'elastix':
            return self._register_elastix(fixed_image, moving_image, parameters, preview_only)
        else:
            raise NotImplementedError(f"Mode {self.mode} not implemented")
    
    def _register_elastix(self, 
                          fixed_image: np.ndarray,
                          moving_image: np.ndarray,
                          parameters: Optional[Dict] = None,
                          preview_only: bool = False) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Register using Elastix backend
        
        Args:
            preview_only: If True, only warp downsampled preview for manual correction
        """
        with self._capture_logs():
            print("\n" + "="*70)
            print("⏱️ ELASTIX BACKEND - Detailed Timing Debug")
            print("="*70)
            start_time = time.time()
            
            self._log("Starting Elastix registration...")
            if preview_only:
                self._log("Preview mode - will stop before high-res warp")

            # Save temporary images for Elastix
            import tempfile
            print(f"[+{time.time()-start_time:.3f}s] Imports complete")

            # Create or reuse temp directory (persistent for high-res warp)
            if self.temp_dir is None:
                self.temp_dir = tempfile.mkdtemp()
            print(f"[+{time.time()-start_time:.3f}s] Temp dir ready: {self.temp_dir}")

            tmpdir = Path(self.temp_dir)

            # Convert to grayscale if needed for registration
            print(f"[+{time.time()-start_time:.3f}s] Converting to grayscale...")
            if len(fixed_image.shape) == 3:
                fixed_gray = cv2.cvtColor(fixed_image, cv2.COLOR_RGB2GRAY)
            else:
                fixed_gray = fixed_image

            if len(moving_image.shape) == 3:
                moving_gray = cv2.cvtColor(moving_image, cv2.COLOR_RGB2GRAY)
            else:
                moving_gray = moving_image
            print(f"[+{time.time()-start_time:.3f}s] Grayscale conversion done")

            # Determine target size BEFORE saving images - SMART sizing based on available memory
            print(f"[+{time.time()-start_time:.3f}s] Determining target size...")
            
            # Check if GUI explicitly provided target_size
            if parameters and 'target_size' in parameters and parameters['target_size'] is not None:
                target_size = parameters['target_size']
                print(f"[+{time.time()-start_time:.3f}s] Using GUI target size: {target_size}")
            else:
                # Smart auto-scaling based on image size and available memory
                max_dim = max(fixed_gray.shape)
                total_pixels = fixed_gray.shape[0] * fixed_gray.shape[1]
                print(f"[+{time.time()-start_time:.3f}s] Image: {fixed_gray.shape[1]}×{fixed_gray.shape[0]} = {total_pixels:,} pixels ({total_pixels/1e6:.1f}MP)")
                
                # SMART LIMITS based on your hardware (32GB RAM + 16GB GPU)
                # ITK can handle up to ~100MP with 32GB RAM
                # PyTorch GPU can handle up to ~50MP with 16GB VRAM
                # Conservative limit: 20MP for safety margin with other processes
                MAX_PIXELS = 20_000_000  # 20 megapixels (e.g., 5000×4000)
                
                if total_pixels > MAX_PIXELS:
                    # Downsample to fit within memory budget
                    scale = (MAX_PIXELS / total_pixels) ** 0.5
                    target_h = int(fixed_gray.shape[0] * scale)
                    target_w = int(fixed_gray.shape[1] * scale)
                    target_size = (target_h, target_w)
                    target_mp = (target_h * target_w) / 1e6
                    print(f"[+{time.time()-start_time:.3f}s] ⚠️ Very large image - downsampling for stability")
                    print(f"[+{time.time()-start_time:.3f}s]    {total_pixels/1e6:.1f}MP → {target_mp:.1f}MP ({target_w}×{target_h})")
                else:
                    target_size = None
                    print(f"[+{time.time()-start_time:.3f}s] ✅ Image size OK - using full resolution (no downsampling)")
            
            print(f"[+{time.time()-start_time:.3f}s] Final target size for registration: {target_size}")

            # Downsample grayscale images for registration if needed
            if target_size is not None:
                print(f"[+{time.time()-start_time:.3f}s] Downsampling images for registration...")
                fixed_gray_reg = cv2.resize(fixed_gray, (target_size[1], target_size[0]), interpolation=cv2.INTER_LINEAR)
                moving_gray_reg = cv2.resize(moving_gray, (target_size[1], target_size[0]), interpolation=cv2.INTER_LINEAR)
                print(f"[+{time.time()-start_time:.3f}s] Downsampled: {fixed_gray.shape} -> {fixed_gray_reg.shape}")
            else:
                fixed_gray_reg = fixed_gray
                moving_gray_reg = moving_gray

            # OPTIMIZATION: Write compressed PNG in memory buffer, then save (faster)
            print(f"[+{time.time()-start_time:.3f}s] Writing images (optimized)...")
            fixed_path = tmpdir / "fixed.png"
            moving_path = tmpdir / "moving.png"
            moving_rgb_path = tmpdir / "moving_rgb.png"

            # Use faster compression for temp files (compression=0 = no compression)
            # Save DOWNSAMPLED images for registration (prevents ITK memory errors)
            cv2.imwrite(str(fixed_path), fixed_gray_reg, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            cv2.imwrite(str(moving_path), moving_gray_reg, [cv2.IMWRITE_PNG_COMPRESSION, 0])

            # Save RGB version for warping (keep full resolution!)
            if len(moving_image.shape) == 3:
                cv2.imwrite(str(moving_rgb_path), cv2.cvtColor(moving_image, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 0])
            else:
                # Convert grayscale to RGB
                moving_rgb = cv2.cvtColor(moving_gray, cv2.COLOR_GRAY2BGR)
                cv2.imwrite(str(moving_rgb_path), moving_rgb, [cv2.IMWRITE_PNG_COMPRESSION, 0])
            print(f"[+{time.time()-start_time:.3f}s] Images written (uncompressed)")

            # Store paths for later high-res warp
            self.fixed_path = str(fixed_path)
            self.moving_path = str(moving_path)
            self.moving_rgb_path = str(moving_rgb_path)

            self._log(f"Saved images to: {tmpdir}")
            self._log(f"  Fixed (registration): {fixed_path} ({fixed_gray_reg.shape if target_size else fixed_gray.shape})")
            self._log(f"  Moving (registration): {moving_path} ({moving_gray_reg.shape if target_size else moving_gray.shape})")
            self._log(f"  Moving RGB (full-res): {moving_rgb_path} ({moving_image.shape})")

            # Target size already calculated above (no need to recalculate)
            print(f"[+{time.time()-start_time:.3f}s] Using target size: {target_size}")

            # Run registration using selected method
            registration_method = self.config.get('registration_method', 'bspline')
            print(f"[+{time.time()-start_time:.3f}s] Registration method: {registration_method}")
            
            if registration_method == 'voxelmorph':
                # VoxelMorph PyTorch registration
                self._log(f"Using VoxelMorph PyTorch registration (deep learning GPU)")
                print(f"[+{time.time()-start_time:.3f}s] Loading VoxelMorph model...")
                
                from advanced_registration.voxelmorph_pytorch import VoxelMorphRegistrationPyTorch
                
                voxelmorph = VoxelMorphRegistrationPyTorch(
                    model_path="models/voxelmorph_fabric.pth",
                    use_gpu=True,
                    inshape=(512, 512)
                )
                voxelmorph.load_model()
                
                print(f"[+{time.time()-start_time:.3f}s] Running VoxelMorph registration...")
                warped_gray, deformation, metadata = voxelmorph.register(
                    fixed_gray,
                    moving_gray,
                    return_warped=True
                )
                
                # Convert to expected format
                fixed_np = fixed_gray
                moving_np = moving_gray
                
                # Convert warped grayscale to RGB
                if len(moving_image.shape) == 3:
                    # Apply warp to RGB image using deformation field
                    # For now, just convert grayscale result to RGB
                    warped_rgb = cv2.cvtColor(warped_gray, cv2.COLOR_GRAY2RGB)
                else:
                    warped_rgb = cv2.cvtColor(warped_gray, cv2.COLOR_GRAY2RGB)
                
                print(f"[+{time.time()-start_time:.3f}s] VoxelMorph registration complete!")
                
                # Skip the normal warp step - already have result
                self.last_deformation = deformation
                self.last_metadata = metadata
                
                reg_time = time.time() - start_time
                print(f"[+{time.time()-start_time:.3f}s] ✅ TOTAL BACKEND TIME: {reg_time:.2f}s")
                print("="*70 + "\n")
                
                self._log(f"Complete in {reg_time:.2f}s")
                self._log(f"  Quality: {metadata.get('quality', 'unknown')}")
                self._log(f"  Deformation range: [{deformation.min():.2f}, {deformation.max():.2f}]")
                
                return warped_rgb, deformation, metadata
                
            elif registration_method == 'demons':
                self._log(f"Using Demons registration (fast, large deformations)")
                print(f"[+{time.time()-start_time:.3f}s] Calling engine.register_demons()...")
                deformation, fixed_np, moving_np, metadata = self.engine.register_demons(
                    fixed_path,
                    moving_path,
                    target_size=target_size,
                    parameters=parameters
                )
            elif registration_method == 'hybrid':
                self._log(f"Using Hybrid registration (Demons→B-spline for best quality)")
                print(f"[+{time.time()-start_time:.3f}s] Calling engine.register_hybrid()...")
                deformation, fixed_np, moving_np, metadata = self.engine.register_hybrid(
                    fixed_path,
                    moving_path,
                    target_size=target_size,
                    parameters=parameters
                )
            else:  # Default to bspline
                self._log(f"Using B-spline registration (standard)")
                print(f"[+{time.time()-start_time:.3f}s] Calling engine.register_bspline()...")
                deformation, fixed_np, moving_np, metadata = self.engine.register_bspline(
                    fixed_path,
                    moving_path,
                    target_size=target_size,
                    parameters=parameters
                )
            
            print(f"[+{time.time()-start_time:.3f}s] Registration algorithm complete!")

            # Cache deformation and metadata first
            self.last_deformation = deformation
            self.last_metadata = metadata

            # Warp RGB image - use preview or full-res based on mode
            print(f"[+{time.time()-start_time:.3f}s] Starting RGB image warp...")
            if preview_only:
                # Only warp the downsampled preview image
                self._log("Warping preview image only (for manual correction)")
                output_path = tmpdir / "warped_preview.png"
                warped_rgb = self.engine.warp_rgb_image(
                    moving_path,  # Use downsampled image, not full RGB
                    deformation,
                    output_path
                )
            else:
                # Warp full-resolution RGB image
                self._log("Warping full-resolution RGB image")
                output_path = tmpdir / "warped.png"
                warped_rgb = self.engine.warp_rgb_image(
                    moving_rgb_path,  # Full-res RGB
                    deformation,
                    output_path
                )
            
            print(f"[+{time.time()-start_time:.3f}s] RGB warp complete!")

            reg_time = time.time() - start_time
            print(f"[+{time.time()-start_time:.3f}s] ✅ TOTAL BACKEND TIME: {reg_time:.2f}s")
            print("="*70 + "\n")
            
            self._log(f"Complete in {reg_time:.2f}s")
            self._log(f"  Quality: {metadata.get('quality', 'unknown')}")
            self._log(f"  Deformation range: [{deformation.min():.2f}, {deformation.max():.2f}]")

            return warped_rgb, deformation, metadata
    
    def warp_image(self, 
                   image: np.ndarray, 
                   deformation_field: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply deformation to an image
        
        Args:
            image: Image to warp
            deformation_field: Optional deformation field (uses last if None)
        
        Returns:
            Warped image
        """
        if deformation_field is None:
            if self.last_deformation is None:
                raise ValueError("No deformation field available")
            deformation_field = self.last_deformation
        
        if self.mode == 'elastix':
            # Use Elastix warping
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                
                # Save image
                img_path = tmpdir / "input.png"
                if len(image.shape) == 3:
                    cv2.imwrite(str(img_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
                else:
                    cv2.imwrite(str(img_path), image)
                
                # Warp
                output_path = tmpdir / "warped.png"
                warped = self.engine.warp_rgb_image(
                    img_path,
                    deformation_field,
                    output_path
                )
                
                return warped
        else:
            raise NotImplementedError()
    
    def get_quality_metrics(self, metadata: Dict) -> str:
        """Format quality metrics for display"""
        lines = []
        lines.append(f"Quality: {metadata.get('quality', 'unknown').upper()}")
        
        if 'final_metric' in metadata and metadata['final_metric'] is not None:
            lines.append(f"Metric Value: {metadata['final_metric']:.2f}")
        
        if 'registration_time' in metadata:
            lines.append(f"Time: {metadata['registration_time']:.2f}s")
        
        return "\n".join(lines)
    
    def set_acceleration_mode(self, mode: str):
        """Set GPU acceleration mode for warping operations"""
        self.warp_acceleration_mode = mode
        
        if self.mode == 'elastix' and hasattr(self.engine, 'use_warp_acceleration'):
            if mode == 'warp':
                self.engine.use_warp_acceleration = True
                print("[Registration Backend] 🚀 NVIDIA Warp acceleration enabled")
            else:
                self.engine.use_warp_acceleration = False
                print("[Registration Backend] 🐍 PyTorch fallback mode enabled")
        
    def get_acceleration_mode(self) -> str:
        """Get current GPU acceleration mode"""
        return self.warp_acceleration_mode
    
    def is_warp_available(self) -> bool:
        """Check if NVIDIA Warp acceleration is available"""
        if self.mode == 'elastix' and hasattr(self.engine, 'use_warp_acceleration'):
            return hasattr(self.engine, 'warp_accelerator') and self.engine.warp_accelerator is not None
        return False
    
    def get_acceleration_status(self) -> str:
        """Get detailed acceleration status"""
        if not self.is_warp_available():
            return "NVIDIA Warp not available - using PyTorch only"
        
        if self.warp_acceleration_mode == 'warp':
            return "🚀 NVIDIA Warp enabled (Real-time acceleration)"
        else:
            return "🐍 PyTorch fallback mode (Standard performance)"
    
    def get_warp_performance_stats(self) -> Dict:
        """Get Warp acceleration performance statistics"""
        if hasattr(self.engine, 'warp_accelerator') and self.engine.warp_accelerator:
            return self.engine.warp_accelerator.get_performance_stats()
        return {}
    
    def apply_manual_corrections(self, deformation_field: np.ndarray, 
                                 corrections: list) -> np.ndarray:
        """
        Apply manual corrections to deformation field
        
        Args:
            deformation_field: [H, W, 2] original deformation
            corrections: list of (x, y, dx, dy) tuples
        
        Returns:
            corrected_deformation: [H, W, 2] with manual corrections applied
        """
        if not corrections:
            return deformation_field
        
        # print(f"\n[Registration Backend] Applying {len(corrections)} manual corrections...")
        
        # Create a copy
        corrected = deformation_field.copy()
        h, w = corrected.shape[:2]
        
        # Apply Gaussian-weighted influence for each correction point
        for i, (x, y, dx, dy) in enumerate(corrections, 1):
            # Convert to pixel coordinates if needed
            x_px = int(x)
            y_px = int(y)
            
            # print(f"  Correction {i}: pos=({x_px}, {y_px}), offset=({dx:.2f}, {dy:.2f})")
            
            # Skip out-of-bounds
            if x_px < 0 or x_px >= w or y_px < 0 or y_px >= h:
                # print(f"    WARNING: Out of bounds, skipping")
                continue
            
            # Create influence radius (50 pixels for more visible effect)
            radius = 250
            sigma = radius / 2.5
            
            # Create meshgrid for influence calculation
            y_range = np.arange(max(0, y_px - radius), min(h, y_px + radius + 1))
            x_range = np.arange(max(0, x_px - radius), min(w, x_px + radius + 1))
            yy, xx = np.meshgrid(y_range, x_range, indexing='ij')
            
            # Calculate Gaussian weights
            dist_sq = (xx - x_px)**2 + (yy - y_px)**2
            weights = np.exp(-dist_sq / (2 * sigma**2))
            
            # Apply correction with Gaussian falloff (ADDITIVE to existing deformation)
            corrected[yy.min():yy.max()+1, xx.min():xx.max()+1, 0] += weights * dx
            corrected[yy.min():yy.max()+1, xx.min():xx.max()+1, 1] += weights * dy
            
            # print(f"    Applied with radius={radius}, max_weight={weights.max():.3f}")
        
        # print(f"  ✓ Manual corrections applied")
        # print(f"  Original deformation range: [{deformation_field.min():.2f}, {deformation_field.max():.2f}]")
        # print(f"  Corrected deformation range: [{corrected.min():.2f}, {corrected.max():.2f}]")
        
        return corrected
    
    def set_manual_corrections(self, corrections: list):
        """Store manual corrections for later use"""
        self.manual_corrections = corrections
        # print(f"[Registration Backend] Stored {len(corrections)} manual corrections")
    
    def warp_full_resolution(self, deformation_field: Optional[np.ndarray] = None) -> str:
        """
        Warp the full-resolution RGB image using stored paths
        
        Args:
            deformation_field: Deformation to apply (uses last if None)
        
        Returns:
            Path to warped image file
        """
        if deformation_field is None:
            deformation_field = self.last_deformation
        
        if deformation_field is None:
            raise ValueError("No deformation field available. Run registration first.")
        
        if self.moving_rgb_path is None or not Path(self.moving_rgb_path).exists():
            raise FileNotFoundError(
                "Full-resolution fabric image not found. "
                "It may have been deleted from temporary storage."
            )
        
        # print(f"\n[Registration Backend] Warping full-resolution image...")
        # print(f"  Input: {self.moving_rgb_path}")
        
        # Apply manual corrections if available
        if self.manual_corrections:
            # print(f"  Applying {len(self.manual_corrections)} manual corrections...")
            deformation_field = self.apply_manual_corrections(deformation_field, self.manual_corrections)
        
        # Warp using the engine
        output_path = Path(self.temp_dir) / "warped_fullres.png"
        warped_rgb = self.engine.warp_rgb_image(
            self.moving_rgb_path,
            deformation_field,
            str(output_path)
        )
        
        # print(f"  ✓ Full-resolution warp complete")
        # print(f"  Output: {output_path}")
        
        return str(output_path)
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
                # print(f"[Registration Backend] Cleaned up temp directory: {self.temp_dir}")
                self.temp_dir = None
                self.moving_rgb_path = None
                self.fixed_path = None
                self.moving_path = None
            except Exception as e:
                # print(f"[Registration Backend] Warning: Could not clean temp files: {e}")
                pass
    
    def __del__(self):
        """Cleanup on destruction"""
        self.cleanup_temp_files()
    
    def preprocess_image(self, image: np.ndarray, method: str = 'clahe') -> np.ndarray:
        """
        Apply preprocessing to improve registration
        
        Args:
            image: Input image (grayscale or RGB)
            method: Preprocessing method - 'clahe', 'histogram_eq', 'edge_enhance', 
                   'normalize', 'bilateral', 'combo', 'emboss_gradient', or 'texture_enhance'
        
        Returns:
            Preprocessed image
        """
        import cv2
        
        # Convert to grayscale if RGB
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        if method == 'clahe':
            # CLAHE - Contrast Limited Adaptive Histogram Equalization
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray)
        
        elif method == 'histogram_eq':
            # Global histogram equalization
            return cv2.equalizeHist(gray)
        
        elif method == 'edge_enhance':
            # Edge enhancement using Laplacian
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            laplacian = np.uint8(np.absolute(laplacian))
            enhanced = cv2.addWeighted(gray, 1.5, laplacian, -0.5, 0)
            return np.clip(enhanced, 0, 255).astype(np.uint8)
        
        elif method == 'normalize':
            # Intensity normalization with percentile clipping
            lower = np.percentile(gray, 2)
            upper = np.percentile(gray, 98)
            clipped = np.clip(gray, lower, upper)
            normalized = ((clipped - lower) / (upper - lower + 1e-10) * 255).astype(np.uint8)
            return normalized
        
        elif method == 'bilateral':
            # Bilateral filter - denoise while preserving edges
            return cv2.bilateralFilter(gray, 9, 75, 75)
        
        elif method == 'combo':
            # Combination: bilateral + CLAHE + edge enhance
            bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(bilateral)
            laplacian = cv2.Laplacian(enhanced, cv2.CV_64F)
            laplacian = np.uint8(np.absolute(laplacian))
            result = cv2.addWeighted(enhanced, 1.3, laplacian, -0.3, 0)
            return np.clip(result, 0, 255).astype(np.uint8)
        
        elif method == 'emboss_gradient':
            # For embossed/textured fabrics - extract gradient magnitude
            # This emphasizes structure regardless of lighting
            bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Compute gradients in X and Y
            sobelx = cv2.Sobel(bilateral, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(bilateral, cv2.CV_64F, 0, 1, ksize=3)
            
            # Gradient magnitude
            gradient_mag = np.sqrt(sobelx**2 + sobely**2)
            gradient_mag = np.uint8(np.clip(gradient_mag, 0, 255))
            
            # Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gradient_mag)
            
            return enhanced
        
        elif method == 'texture_enhance':
            # For white-on-white patterns with 3D texture
            # Combines bilateral smoothing, CLAHE, and directional gradients
            bilateral = cv2.bilateralFilter(gray, 13, 100, 100)
            
            # CLAHE with higher clip limit for subtle texture
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(bilateral)
            
            # Extract texture via high-pass filter
            blurred = cv2.GaussianBlur(enhanced, (0, 0), 3)
            texture = cv2.addWeighted(enhanced, 2.0, blurred, -1.0, 0)
            texture = np.clip(texture, 0, 255).astype(np.uint8)
            
            return texture

        elif method == 'gabor':
            # Multi-orientation Gabor filters to highlight tone-on-tone patterns
            from skimage.filters import gabor
            gray_norm = gray.astype(np.float32) / 255.0
            response = np.zeros_like(gray_norm, dtype=np.float32)
            orientations = [0.0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
            for theta in orientations:
                real, imag = gabor(gray_norm, frequency=0.2, theta=theta)
                magnitude = np.sqrt(real**2 + imag**2)
                response = np.maximum(response, magnitude)
            response = response / (response.max() + 1e-6)
            return (response * 255).astype(np.uint8)

        elif method == 'frangi':
            # Multi-scale Frangi vesselness to enhance fine linear threads
            from skimage.filters import frangi
            gray_norm = gray.astype(np.float32) / 255.0
            vesselness = frangi(gray_norm, sigmas=tuple(np.linspace(1, 6, num=6)))
            vesselness = np.clip(vesselness, 0, 1)
            return (vesselness * 255).astype(np.uint8)

        elif method == 'structure_tensor':
            # Structure tensor coherence to emphasize weave orientation
            from skimage.feature import structure_tensor, structure_tensor_eigenvalues
            gray_norm = gray.astype(np.float32) / 255.0
            Axx, Axy, Ayy = structure_tensor(gray_norm, sigma=1.5)
            l1, l2 = structure_tensor_eigenvalues((Axx, Axy, Ayy))
            coherence = (l1 - l2) / (l1 + l2 + 1e-6)
            coherence = np.clip(coherence, 0, 1)
            return (coherence * 255).astype(np.uint8)
        
        else:
            return gray
    
    def create_mask(self, image: np.ndarray, mask_type: str = 'foreground') -> np.ndarray:
        """
        Create mask for registration
        
        Args:
            image: Input image
            mask_type: 'foreground', 'content', or 'lighting'
        
        Returns:
            Binary mask (255=use, 0=ignore)
        """
        import cv2
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        if mask_type == 'foreground':
            # Mask white background
            _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            
        elif mask_type == 'content':
            # Mask based on edges
            edges = cv2.Canny(gray, 50, 150)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            mask = cv2.dilate(edges, kernel, iterations=2)
            
        elif mask_type == 'lighting':
            # Exclude extreme brightness/darkness (lighting issues)
            _, dark_mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
            _, bright_mask = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY_INV)
            mask = cv2.bitwise_and(dark_mask, bright_mask)
            
        else:
            # No mask
            return np.ones_like(gray) * 255
        
        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    
    def detect_pattern_repeat(self, image: np.ndarray, method: str = 'autocorr') -> Tuple[int, int]:
        """
        Detect repeating pattern size in design image
        
        Args:
            image: Design image (should contain repeating pattern)
            method: Detection method - 'autocorr' or 'fft'
        
        Returns:
            (repeat_width, repeat_height) in pixels
        """
        import cv2
        from scipy import signal
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        if method == 'autocorr':
            # Use autocorrelation to find repeat
            # Normalize image
            gray_norm = (gray - gray.mean()) / (gray.std() + 1e-10)
            
            # Compute autocorrelation
            autocorr = signal.correlate2d(gray_norm, gray_norm, mode='same')
            
            # Find peaks in autocorrelation (excluding center)
            h, w = autocorr.shape
            center_y, center_x = h // 2, w // 2
            
            # Look for peaks in horizontal and vertical directions
            horizontal_line = autocorr[center_y, :]
            vertical_line = autocorr[:, center_x]
            
            # Find first significant peak (excluding center)
            def find_first_peak(line, center_idx):
                # Look for peaks after center
                right_half = line[center_idx + 10:]  # Skip near-center
                if len(right_half) > 0:
                    from scipy.signal import find_peaks
                    peaks, _ = find_peaks(right_half, prominence=right_half.std() * 0.5)
                    if len(peaks) > 0:
                        return peaks[0] + 10  # Add back offset
                return len(line) // 4  # Default fallback
            
            repeat_w = find_first_peak(horizontal_line, center_x)
            repeat_h = find_first_peak(vertical_line, center_y)
            
            self._log(f"Detected pattern repeat: {repeat_w}×{repeat_h} pixels (autocorrelation)")
            return repeat_w, repeat_h
            
        elif method == 'fft':
            # Use FFT to find periodicity
            from numpy.fft import fft2, fftshift
            
            # FFT
            f_transform = fft2(gray)
            f_shift = fftshift(f_transform)
            magnitude = np.abs(f_shift)
            
            # Find peaks in frequency domain
            h, w = magnitude.shape
            center_y, center_x = h // 2, w // 2
            
            # Look at horizontal and vertical frequency components
            # Convert frequency peaks back to spatial period
            # This is simplified - full implementation would need peak detection
            
            # For now, use a simple heuristic based on image size
            repeat_w = min(w // 4, 512)  # Estimate
            repeat_h = min(h // 4, 512)
            
            self._log(f"Estimated pattern repeat: {repeat_w}×{repeat_h} pixels (FFT)")
            return repeat_w, repeat_h
        
        else:
            # Default: assume pattern is whole image or 1/4 of it
            h, w = gray.shape
            return min(w // 2, 512), min(h // 2, 512)
    
    def tile_pattern(self, pattern: np.ndarray, target_size: Tuple[int, int], 
                     tile_width: int = None, tile_height: int = None,
                     blend_edges: bool = True) -> np.ndarray:
        """
        Tile a pattern to fill target canvas size
        
        Args:
            pattern: Pattern image to tile
            target_size: (height, width) of output canvas
            tile_width: Width of single tile repeat (None = use pattern width)
            tile_height: Height of single tile repeat (None = use pattern height)
            blend_edges: If True, blend edges for seamless tiling
        
        Returns:
            Tiled pattern image
        """
        import cv2
        
        target_h, target_w = target_size
        pattern_h, pattern_w = pattern.shape[:2]
        
        # Use custom tile size if specified
        if tile_width is not None and tile_height is not None:
            # Resize pattern to specified tile size
            tile = cv2.resize(pattern, (tile_width, tile_height), interpolation=cv2.INTER_LINEAR)
            self._log(f"Resized pattern {pattern_w}×{pattern_h} → {tile_width}×{tile_height} for tiling")
        else:
            # Use pattern as-is
            tile = pattern
            tile_width = pattern_w
            tile_height = pattern_h
        
        # Calculate number of tiles needed
        tiles_x = int(np.ceil(target_w / tile_width)) + 1  # Extra for safety
        tiles_y = int(np.ceil(target_h / tile_height)) + 1
        
        # Create tiled image
        if len(tile.shape) == 3:
            tiled = np.tile(tile, (tiles_y, tiles_x, 1))
        else:
            tiled = np.tile(tile, (tiles_y, tiles_x))
        
        # Crop to exact target size
        tiled = tiled[:target_h, :target_w]
        
        if blend_edges and len(pattern.shape) == 3:
            # Optional: blend tile boundaries for seamless look
            # This is complex - simplified version here
            blend_width = min(20, pattern_w // 10)
            
            # Create blend mask for edges
            # (Full implementation would use alpha blending at tile boundaries)
            pass
        
        self._log(f"Tiled pattern {pattern_w}×{pattern_h} to {target_w}×{target_h} ({tiles_x}×{tiles_y} tiles)")
        return tiled
    
    def detect_pattern_instances_in_target(self, pattern_unit: np.ndarray, target: np.ndarray,
                                           threshold: float = 0.7) -> list:
        """
        Detect all instances of pattern_unit in target image using template matching
        
        Args:
            pattern_unit: Single repeating unit of the pattern
            target: Fabric/camera image containing multiple pattern instances
            threshold: Matching confidence threshold (0-1)
        
        Returns:
            List of dicts with 'position': (x, y), 'confidence': float, 'size': (w, h)
        """
        import cv2
        
        # Convert to grayscale for matching
        if len(pattern_unit.shape) == 3:
            pattern_gray = cv2.cvtColor(pattern_unit, cv2.COLOR_RGB2GRAY)
        else:
            pattern_gray = pattern_unit
            
        if len(target.shape) == 3:
            target_gray = cv2.cvtColor(target, cv2.COLOR_RGB2GRAY)
        else:
            target_gray = target
        
        pattern_h, pattern_w = pattern_gray.shape
        target_h, target_w = target_gray.shape
        
        # Multi-scale template matching
        instances = []
        scales = [1.0, 0.9, 1.1, 0.8, 1.2]  # Try different scales
        
        best_scale = 1.0
        best_matches = []
        
        for scale in scales:
            if scale != 1.0:
                scaled_w = int(pattern_w * scale)
                scaled_h = int(pattern_h * scale)
                scaled_pattern = cv2.resize(pattern_gray, (scaled_w, scaled_h))
            else:
                scaled_pattern = pattern_gray
                scaled_w, scaled_h = pattern_w, pattern_h
            
            # Skip if scaled pattern is larger than target
            if scaled_h > target_h or scaled_w > target_w:
                continue
            
            # Template matching
            result = cv2.matchTemplate(target_gray, scaled_pattern, cv2.TM_CCOEFF_NORMED)
            
            # Find all matches above threshold
            locations = np.where(result >= threshold)
            
            scale_matches = []
            for pt in zip(*locations[::-1]):  # (x, y) format
                confidence = result[pt[1], pt[0]]
                scale_matches.append({
                    'position': pt,
                    'confidence': float(confidence),
                    'size': (scaled_w, scaled_h),
                    'scale': scale
                })
            
            if len(scale_matches) > len(best_matches):
                best_matches = scale_matches
                best_scale = scale
        
        # Non-maximum suppression to avoid overlapping detections
        if best_matches:
            instances = self._nms_pattern_instances(best_matches, overlap_threshold=0.3)
            self._log(f"Detected {len(instances)} pattern instances at scale {best_scale:.2f}")
        else:
            self._log("No pattern instances detected above threshold")
        
        return instances
    
    def _nms_pattern_instances(self, instances: list, overlap_threshold: float = 0.3) -> list:
        """Non-maximum suppression for overlapping pattern detections"""
        if not instances:
            return []
        
        # Sort by confidence
        instances = sorted(instances, key=lambda x: x['confidence'], reverse=True)
        
        kept = []
        while instances:
            best = instances.pop(0)
            kept.append(best)
            
            # Remove overlapping instances
            instances = [inst for inst in instances 
                        if not self._boxes_overlap(best, inst, overlap_threshold)]
        
        return kept
    
    def _boxes_overlap(self, inst1: dict, inst2: dict, threshold: float) -> bool:
        """Check if two pattern instances overlap significantly"""
        x1, y1 = inst1['position']
        w1, h1 = inst1['size']
        x2, y2 = inst2['position']
        w2, h2 = inst2['size']
        
        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return False
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        iou = intersection / union if union > 0 else 0
        return iou > threshold
    
    def create_pattern_grid_from_instances(self, pattern_unit: np.ndarray, 
                                          instances: list, target_shape: tuple) -> np.ndarray:
        """
        Create a tiled pattern image based on detected instance positions
        Places pattern_unit at each detected location
        
        Args:
            pattern_unit: Single pattern repeat
            instances: List of detected instances with positions
            target_shape: (height, width, channels) of output
        
        Returns:
            Pattern image with units placed at detected positions
        """
        import cv2
        
        target_h, target_w = target_shape[:2]
        
        if len(pattern_unit.shape) == 3:
            output = np.zeros((target_h, target_w, pattern_unit.shape[2]), dtype=np.uint8)
        else:
            output = np.zeros((target_h, target_w), dtype=np.uint8)
        
        self._log(f"Placing {len(instances)} pattern units at detected positions")
        
        for inst in instances:
            x, y = inst['position']
            w, h = inst['size']
            
            # Scale pattern to detected size
            if (w, h) != (pattern_unit.shape[1], pattern_unit.shape[0]):
                scaled_pattern = cv2.resize(pattern_unit, (w, h))
            else:
                scaled_pattern = pattern_unit
            
            # Place pattern at detected position
            y2 = min(y + h, target_h)
            x2 = min(x + w, target_w)
            h_actual = y2 - y
            w_actual = x2 - x
            
            output[y:y2, x:x2] = scaled_pattern[:h_actual, :w_actual]
        
        return output
    
    def detect_pattern_transform(self, pattern: np.ndarray, target: np.ndarray) -> dict:
        """
        Detect geometric transform (rotation, scale, translation) of pattern in target
        Uses feature matching (ORB + RANSAC) for robustness
        
        Returns:
            dict with 'transform', 'rotation', 'scale', 'translation', 'matches'
        """
        import cv2
        from scipy.spatial import distance
        
        # Convert to grayscale
        if len(pattern.shape) == 3:
            pattern_gray = cv2.cvtColor(pattern, cv2.COLOR_RGB2GRAY)
        else:
            pattern_gray = pattern
            
        if len(target.shape) == 3:
            target_gray = cv2.cvtColor(target, cv2.COLOR_RGB2GRAY)
        else:
            target_gray = target
        
        # Downsample for speed
        scale_factor = 0.5
        pattern_small = cv2.resize(pattern_gray, None, fx=scale_factor, fy=scale_factor)
        target_small = cv2.resize(target_gray, None, fx=scale_factor, fy=scale_factor)
        
        # Feature detection with ORB (faster than SIFT, still robust)
        orb = cv2.ORB_create(nfeatures=2000)
        
        kp1, des1 = orb.detectAndCompute(pattern_small, None)
        kp2, des2 = orb.detectAndCompute(target_small, None)
        
        if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
            self._log("⚠ Insufficient features detected")
            return None
        
        # Match features with BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(des1, des2, k=2)
        
        # Apply Lowe's ratio test
        good_matches = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)
        
        if len(good_matches) < 10:
            self._log(f"⚠ Only {len(good_matches)} good matches found (need 10+)")
            return None
        
        # Extract matched keypoints
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        # Find homography with RANSAC
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        
        if M is None:
            self._log("⚠ Could not compute homography")
            return None
        
        # Scale back to original resolution
        scale_mat = np.array([[1/scale_factor, 0, 0], [0, 1/scale_factor, 0], [0, 0, 1]])
        M_full = scale_mat @ M @ np.linalg.inv(scale_mat)
        
        # Decompose transform to get rotation, scale
        inliers = mask.ravel().tolist().count(1)
        self._log(f"✓ Found transform: {inliers}/{len(good_matches)} inliers")
        
        return {
            'transform': M_full,
            'inliers': inliers,
            'total_matches': len(good_matches),
            'success': True
        }
    
    def create_transformed_tile(self, pattern: np.ndarray, target_size: tuple, 
                               transform: np.ndarray = None) -> np.ndarray:
        """
        Create tiled pattern with optional global transform applied
        
        Args:
            pattern: Pattern unit
            target_size: (height, width) of output
            transform: Optional 3×3 homography matrix
        
        Returns:
            Tiled and transformed pattern
        """
        import cv2
        
        target_h, target_w = target_size
        
        if transform is not None:
            # Warp pattern with transform first
            pattern_transformed = cv2.warpPerspective(
                pattern, transform, (target_w, target_h),
                borderMode=cv2.BORDER_WRAP
            )
            return pattern_transformed
        else:
            # Simple tiling
            return self.tile_pattern(pattern, target_size)
    
    def align_and_tile_pattern(self, pattern: np.ndarray, target: np.ndarray,
                               auto_detect_repeat: bool = True,
                               use_smart_alignment: bool = True) -> np.ndarray:
        """
        3-STAGE PIPELINE for robust pattern alignment:
        
        Stage 1: Feature-based transform detection (LOW-RES)
                 → Finds rotation, scale, translation robustly
        Stage 2: Apply transform and tile pattern (COARSE)
                 → Creates full pattern with correct global alignment  
        Stage 3: B-spline registration will handle fine deformations (in main workflow)
        
        Args:
            pattern: Design pattern image
            target: Fabric/camera image to match
            auto_detect_repeat: If True, auto-detect pattern repeat size
            use_smart_alignment: If True, use feature matching (recommended)
        
        Returns:
            Tiled and globally-aligned pattern ready for fine B-spline registration
        """
        import cv2
        
        target_h, target_w = target.shape[:2]
        
        # Step 1: Detect pattern repeat unit (or use full pattern)
        if auto_detect_repeat and min(pattern.shape[:2]) < min(target.shape[:2]) / 2:
            try:
                repeat_w, repeat_h = self.detect_pattern_repeat(pattern)
                
                # Extract repeat unit (centered crop)
                pattern_h, pattern_w = pattern.shape[:2]
                start_y = max(0, (pattern_h - repeat_h) // 2)
                start_x = max(0, (pattern_w - repeat_w) // 2)
                pattern_unit = pattern[start_y:start_y+repeat_h, start_x:start_x+repeat_w]
                
                self._log(f"Using detected pattern unit: {repeat_w}×{repeat_h}")
            except Exception as e:
                self._log(f"Pattern detection failed, using full image: {e}")
                pattern_unit = pattern
        else:
            pattern_unit = pattern
        
        # Step 2: Smart alignment using feature matching
        if use_smart_alignment:
            self._log("🧠 Stage 1: Detecting pattern transform (rotation/scale/position)...")
            
            transform_result = self.detect_pattern_transform(pattern_unit, target)
            
            if transform_result and transform_result['success']:
                self._log(f"✓ Found transform: {transform_result['inliers']} inliers")
                
                # Create tiled pattern with detected transform
                self._log("📐 Stage 2: Creating globally-aligned tiled pattern...")
                tiled_pattern = self.create_transformed_tile(
                    pattern_unit, (target_h, target_w), transform_result['transform']
                )
                
                self._log(f"✓ Pattern tiled with global alignment: {tiled_pattern.shape[1]}×{tiled_pattern.shape[0]}")
                self._log("→ Stage 3 (B-spline) will handle local deformations")
                
                return tiled_pattern
            else:
                self._log("⚠ Feature matching failed, falling back to simple tiling")
        
        # Step 3: Fallback to simple tiling
        self._log("📐 Using simple tiling (wallpaper mode)")
        tiled_pattern = self.tile_pattern(pattern_unit, (target_h, target_w))
        
        # Step 4: Coarse alignment using phase correlation (optional)
        try:
            # Convert both to grayscale for alignment
            if len(tiled_pattern.shape) == 3:
                pattern_gray = cv2.cvtColor(tiled_pattern, cv2.COLOR_RGB2GRAY)
            else:
                pattern_gray = tiled_pattern
                
            if len(target.shape) == 3:
                target_gray = cv2.cvtColor(target, cv2.COLOR_RGB2GRAY)
            else:
                target_gray = target
            
            # Resize for faster phase correlation
            scale = 0.25
            pattern_small = cv2.resize(pattern_gray, None, fx=scale, fy=scale)
            target_small = cv2.resize(target_gray, None, fx=scale, fy=scale)
            
            # Phase correlation to find translation
            shift, _ = cv2.phaseCorrelate(
                np.float32(pattern_small), 
                np.float32(target_small)
            )
            
            # Scale shift back to full resolution
            shift_x = int(shift[0] / scale)
            shift_y = int(shift[1] / scale)
            
            if abs(shift_x) > 10 or abs(shift_y) > 10:  # Only apply significant shifts
                # Apply translation
                M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
                tiled_pattern = cv2.warpAffine(
                    tiled_pattern, M, (target_w, target_h),
                    borderMode=cv2.BORDER_WRAP  # Wrap pattern at edges
                )
                self._log(f"Applied coarse alignment: shift=({shift_x}, {shift_y})")
            else:
                self._log("No significant coarse shift needed")
                
        except Exception as e:
            self._log(f"Coarse alignment skipped: {e}")
        
        return tiled_pattern
    
    def compare_registration_methods(self, fixed_image: np.ndarray, moving_image: np.ndarray,
                                     methods: list = None, parameters: dict = None) -> dict:
        """
        Test multiple registration methods and return comparison results
        
        Args:
            fixed_image: Reference image
            moving_image: Image to register
            methods: List of method configs to test
            parameters: Base parameters to use
        
        Returns:
            Dictionary with results for each method
        """
        if methods is None:
            methods = [
                {'name': 'B-spline Standard', 'type': 'bspline', 'grid_spacing': 64},
                {'name': 'B-spline Fine', 'type': 'bspline', 'grid_spacing': 32},
                {'name': 'Demons Fast', 'type': 'demons', 'iterations': 200},
                {'name': 'Hybrid Best', 'type': 'hybrid', 'grid_spacing': 48},
            ]
        
        results = {}
        
        for method_config in methods:
            method_name = method_config['name']
            self._log(f"\n{'='*60}")
            self._log(f"Testing: {method_name}")
            self._log(f"{'='*60}")
            
            try:
                # Merge method config with base parameters
                test_params = {**(parameters or {}), **method_config}
                
                # Set registration method
                old_method = self.config.get('registration_method', 'bspline')
                self.config.config['registration_method'] = method_config.get('type', 'bspline')
                
                # Run registration
                start_time = time.time()
                registered, deformation, metadata = self.register(
                    fixed_image, moving_image, test_params, preview_only=False
                )
                elapsed = time.time() - start_time
                
                # Restore old method
                self.config.config['registration_method'] = old_method
                
                # Store results
                results[method_name] = {
                    'registered': registered,
                    'deformation': deformation,
                    'metadata': metadata,
                    'time': elapsed,
                    'config': method_config
                }
                
                self._log(f"✓ {method_name} completed in {elapsed:.2f}s")
                self._log(f"  Quality: {metadata.get('quality', 'unknown')}")
                
            except Exception as e:
                self._log(f"✗ {method_name} failed: {e}")
                results[method_name] = {
                    'error': str(e),
                    'config': method_config
                }
        
        return results


def test_backend():
    """Test the registration backend"""
    import cv2
    
    # Load test images
    fixed = cv2.imread("camera_capture.png")
    moving = cv2.imread("master_design.png")
    
    if fixed is None or moving is None:
        print("ERROR: Test images not found")
        return
    
    # Convert BGR to RGB
    fixed = cv2.cvtColor(fixed, cv2.COLOR_BGR2RGB)
    moving = cv2.cvtColor(moving, cv2.COLOR_BGR2RGB)
    
    # Create backend
    backend = RegistrationBackend(mode='elastix')
    
    # Register
    registered, deformation, metadata = backend.register(fixed, moving)
    
    print("\nBackend Test Results:")
    print(backend.get_quality_metrics(metadata))
    # print(f"Deformation shape: {deformation.shape}")
    # print(f"Registered shape: {registered.shape}")
    
    # Save result
    cv2.imwrite("test_backend_result.png", cv2.cvtColor(registered, cv2.COLOR_RGB2BGR))
    print("\nSaved result to: test_backend_result.png")


if __name__ == "__main__":
    test_backend()
