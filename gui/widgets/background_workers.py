"""
Background worker threads for long-running operations
Prevents GUI freezing during registration and warping
"""

import numpy as np
from PySide6.QtCore import QThread, Signal, QObject
import traceback


def _normalize_preproc_method(name: str) -> str:
    """Map UI labels to backend preprocessing method identifiers."""
    if not name:
        return ''
    normalized = name.lower().replace(" ", "_")
    mapping = {
        "clahe": "clahe",
        "histogram_equalization": "histogram_eq",
        "edge_enhance": "edge_enhance",
        "normalize": "normalize",
        "bilateral_filter": "bilateral",
        "combo": "combo",
        "emboss_gradient": "emboss_gradient",
        "texture_enhance": "texture_enhance",
        "gabor_filter": "gabor",
        "frangi_vesselness": "frangi",
        "structure_tensor": "structure_tensor"
    }
    return mapping.get(normalized, normalized)


class RegistrationWorker(QThread):
    """
    Background thread for image registration
    Prevents GUI from freezing during computation
    """
    
    # Signals
    progress = Signal(int, str)  # progress_percent, status_message
    finished = Signal(object, object, dict)  # registered_image, deformation_field, metadata
    error = Signal(str)  # error_message
    tiled_pattern_ready = Signal(object)  # tiled_pattern_image (before registration)
    
    def __init__(self, backend, fixed_image, moving_image, parameters, preview_only=False,
                 apply_pattern_tiling=False, smart_tiling=True, tile_width=None, tile_height=None,
                 fixed_preproc=None, moving_preproc=None):
        super().__init__()
        self.backend = backend
        self.fixed_image = fixed_image
        self.moving_image = moving_image
        self.parameters = parameters
        self.preview_only = preview_only
        self.apply_pattern_tiling = apply_pattern_tiling
        self.smart_tiling = smart_tiling
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.fixed_preproc = fixed_preproc
        self.moving_preproc = moving_preproc
        self._is_cancelled = False
        
    def run(self):
        """Run registration in background"""
        try:
            self.progress.emit(0, "Starting registration...")
            
            fixed_img = self.fixed_image
            moving_img = self.moving_image
            
            # Apply pattern tiling if requested
            if self.apply_pattern_tiling:
                if self.smart_tiling:
                    # EXPERIMENTAL: ORB feature-based alignment
                    self.progress.emit(5, f"🔲 Creating pattern with ORB alignment (experimental)...")
                    try:
                        moving_img = self.backend.align_and_tile_pattern(
                            moving_img,
                            fixed_img,
                            auto_detect_repeat=True,
                            use_smart_alignment=True
                        )
                        self.progress.emit(8, f"✓ ORB-aligned pattern ready: {moving_img.shape[1]}×{moving_img.shape[0]}")
                        self.tiled_pattern_ready.emit(moving_img.copy())
                        self.progress.emit(9, "→ Now B-spline will warp this pattern to match fabric deformations")
                    except Exception as e:
                        self.progress.emit(8, f"⚠ ORB pattern tiling failed: {e}")
                else:
                    # DEFAULT: Simple XY tiling with user-specified repeat size
                    width = self.tile_width or 200
                    height = self.tile_height or 200
                    self.progress.emit(5, f"🔲 Creating tiled pattern ({width}×{height} repeat)...")
                    try:
                        moving_img = self.backend.tile_pattern(
                            moving_img,
                            fixed_img.shape[:2],
                            tile_width=width,
                            tile_height=height
                        )
                        self.progress.emit(8, f"✓ Tiled pattern ready: {moving_img.shape[1]}×{moving_img.shape[0]}")
                        self.tiled_pattern_ready.emit(moving_img.copy())
                        self.progress.emit(9, "→ Now B-spline will warp this pattern to match fabric deformations")
                    except Exception as e:
                        self.progress.emit(8, f"⚠ Pattern tiling failed: {e}")
            
            # Apply preprocessing to fixed image
            if self.fixed_preproc and self.fixed_preproc != "None":
                self.progress.emit(10, f"🔧 Preprocessing fixed image ({self.fixed_preproc})...")
                try:
                    fixed_img = self.backend.preprocess_image(
                        fixed_img,
                        _normalize_preproc_method(self.fixed_preproc)
                    )
                    self.progress.emit(15, "✓ Fixed preprocessing complete")
                except Exception as e:
                    self.progress.emit(15, f"⚠ Fixed preprocessing failed: {e}")
            
            # Apply preprocessing to moving image
            if self.moving_preproc and self.moving_preproc != "None":
                self.progress.emit(20, f"🔧 Preprocessing moving image ({self.moving_preproc})...")
                try:
                    moving_img = self.backend.preprocess_image(
                        moving_img,
                        _normalize_preproc_method(self.moving_preproc)
                    )
                    self.progress.emit(25, "✓ Moving preprocessing complete")
                except Exception as e:
                    self.progress.emit(25, f"⚠ Moving preprocessing failed: {e}")
            
            if self._is_cancelled:
                self.error.emit("Registration cancelled by user")
                return
            
            # Perform registration
            self.progress.emit(30, "Running registration algorithm...")
            
            registered, deformation, metadata = self.backend.register(
                fixed_img,
                moving_img,
                self.parameters,
                preview_only=self.preview_only
            )
            
            if self._is_cancelled:
                self.error.emit("Registration cancelled by user")
                return
            
            self.progress.emit(100, "Registration complete!")
            self.finished.emit(registered, deformation, metadata)
            
        except Exception as e:
            error_msg = f"Registration failed: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
    
    def cancel(self):
        """Cancel the registration"""
        self._is_cancelled = True


class WarpingWorker(QThread):
    """
    Background thread for high-resolution image warping
    """
    
    # Signals
    progress = Signal(int, str)
    finished = Signal(object)  # warped_image
    error = Signal(str)
    
    def __init__(self, backend, image, deformation_field, manual_corrections=None):
        super().__init__()
        self.backend = backend
        self.image = image
        self.deformation_field = deformation_field
        self.manual_corrections = manual_corrections or []
        self._is_cancelled = False
        
    def run(self):
        """Run warping in background"""
        try:
            self.progress.emit(0, "Preparing to warp image...")
            
            # Apply manual corrections if any
            if self.manual_corrections:
                self.progress.emit(20, f"Applying {len(self.manual_corrections)} manual corrections...")
                corrected_field = self.backend.apply_manual_corrections(
                    self.deformation_field, 
                    self.manual_corrections
                )
            else:
                corrected_field = self.deformation_field
            
            if self._is_cancelled:
                self.error.emit("Warping cancelled by user")
                return
            
            self.progress.emit(40, "Warping high-resolution image...")
            
            # Warp the image
            warped = self.backend.warp_image(self.image, corrected_field)
            
            if self._is_cancelled:
                self.error.emit("Warping cancelled by user")
                return
            
            self.progress.emit(100, "Warping complete!")
            self.finished.emit(warped)
            
        except Exception as e:
            error_msg = f"Warping failed: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
    
    def cancel(self):
        """Cancel the warping"""
        self._is_cancelled = True


class PreviewWarpWorker(QThread):
    """
    Quick preview warping for manual editing
    Works on downsampled image for speed
    """
    
    # Signals
    finished = Signal(object, object)  # preview_image, deformation_field
    error = Signal(str)
    
    def __init__(self, backend, fixed_image, moving_image, deformation_field, target_size=(800, 600)):
        super().__init__()
        self.backend = backend
        self.fixed_image = fixed_image
        self.moving_image = moving_image
        self.deformation_field = deformation_field
        self.target_size = target_size
        
    def run(self):
        """Create preview warp"""
        try:
            import cv2
            
            # Downsample for preview
            h, w = self.moving_image.shape[:2]
            scale_h = self.target_size[1] / h
            scale_w = self.target_size[0] / w
            scale = min(scale_h, scale_w, 1.0)  # Don't upscale
            
            new_h = int(h * scale)
            new_w = int(w * scale)
            
            # Resize image
            preview_img = cv2.resize(self.moving_image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # Scale deformation field
            deform_h, deform_w = self.deformation_field.shape[:2]
            preview_deform = cv2.resize(
                self.deformation_field, 
                (new_w, new_h), 
                interpolation=cv2.INTER_LINEAR
            )
            
            # Scale displacement magnitudes
            preview_deform[:, :, 0] *= (new_w / deform_w)
            preview_deform[:, :, 1] *= (new_h / deform_h)
            
            # Warp preview
            preview_warped = self.backend.warp_image(preview_img, preview_deform)
            
            self.finished.emit(preview_warped, preview_deform)
            
        except Exception as e:
            error_msg = f"Preview creation failed: {str(e)}"
            self.error.emit(error_msg)
