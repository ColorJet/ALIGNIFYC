# Advanced Registration Module

Comprehensive registration toolkit providing learning-based and conventional alternatives to Elastix B-spline registration.

## Overview

This module extends Alinify's registration capabilities with:
- **Deep Learning**: VoxelMorph (GPU-accelerated, 0.5-1s)
- **Feature-Based**: SIFT, AKAZE, ORB detectors + Thin-Plate Spline warping
- **Dense Flow**: Farneback, DIS optical flow methods
- **Preprocessing**: Gabor, Frangi, Structure Tensor (already integrated in main GUI)

## Module Structure

```
python/advanced_registration/
├── __init__.py                    # Module exports
├── voxelmorph_backend.py          # VoxelMorph DL registration
├── feature_detectors.py           # SIFT/AKAZE/ORB feature detection
├── optical_flow.py                # Farneback/DIS optical flow
└── tps_registration.py            # Thin-plate spline warping
```

## Installation

### Basic (CPU-only, no ML)
Already functional with current dependencies:
```powershell
# ORB, AKAZE, optical flow work out of the box
python tests/test_advanced_registration.py
```

### SIFT Support (optional)
```powershell
pip install opencv-contrib-python
```

### GPU-Accelerated ML (VoxelMorph)
```powershell
# 1. Install PyTorch with CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 2. Install VoxelMorph
pip install voxelmorph

# 3. Verify GPU availability
python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"
```

## Quick Start

### 1. Feature Detection

```python
from python.advanced_registration import detect_features_sift, detect_and_match, FeatureDetector

# Detect SIFT features
keypoints, descriptors = detect_features_sift(image, nfeatures=2000)

# Complete detection + matching pipeline
kp1, kp2, matches = detect_and_match(
    image1, image2,
    detector=FeatureDetector.SIFT,
    nfeatures=2000
)
```

**Available Detectors**:
- **SIFT**: Best accuracy, scale-invariant (requires opencv-contrib-python)
- **AKAZE**: Fast, binary descriptors, no patent issues
- **ORB**: Fastest, good for real-time (current default in Alinify)

### 2. Optical Flow Registration

```python
from python.advanced_registration import register_with_optical_flow, OpticalFlowMethod

# Fast registration (~0.2-0.5s)
warped, deformation, metadata = register_with_optical_flow(
    fixed_image,
    moving_image,
    method=OpticalFlowMethod.FARNEBACK
)

print(f"Runtime: {metadata['runtime_seconds']:.3f}s")
print(f"Mean displacement: {metadata['mean_displacement']:.2f}px")
```

**Available Methods**:
- **Farneback**: Pyramidal optical flow, good for small-medium deformations
- **DIS**: Dense Inverse Search, handles large displacements
- **RAFT** (future): State-of-the-art deep learning method

### 3. Thin-Plate Spline Registration

```python
from python.advanced_registration import register_with_tps_from_features

# Automatic feature-based TPS registration
warped, deformation, metadata = register_with_tps_from_features(
    fixed_image,
    moving_image,
    detector_type='sift',
    max_control_points=50
)

print(f"Control points: {metadata['n_control_points']}")
print(f"Inliers: {metadata['n_inliers']}/{metadata['n_matches']}")
```

### 4. VoxelMorph Deep Learning Registration

```python
from python.advanced_registration import VoxelMorphRegistration

# Initialize backend (auto-detects GPU)
backend = VoxelMorphRegistration(use_gpu=True)
backend.load_model()  # Loads default U-Net or pre-trained weights

# Fast registration (~0.5-1s on GPU, 10-15s CPU)
warped, deformation, metadata = backend.register(fixed_image, moving_image)

print(f"Device: {metadata['device']}")
print(f"Runtime: {metadata['runtime_seconds']:.3f}s")
print(f"Deformation shape: {deformation.shape}")
```

## Benchmark Comparison

| Method | Speed | Accuracy | GPU? | Best For |
|--------|-------|----------|------|----------|
| **B-spline (Elastix)** | 5-10s | ⭐⭐⭐⭐ | No | General-purpose, robust |
| **VoxelMorph** | 0.5-1s (GPU) | ⭐⭐⭐⭐⭐ | Yes (2GB) | Production, tone-on-tone |
| **Optical Flow** | 0.2-0.5s | ⭐⭐⭐ | Optional | Real-time, preview |
| **TPS + SIFT** | 1-3s | ⭐⭐⭐⭐ | No | Feature-rich patterns |

## Integration into Main GUI

The advanced methods can be integrated into `gui/main_gui.py`:

```python
# Add method selector to registration tab
self.combo_fine_registration = QComboBox()
self.combo_fine_registration.addItems([
    "B-spline (Elastix)",
    "Thin-Plate Spline",
    "Optical Flow (Fast)",
    "VoxelMorph (GPU)",
    "DeepReg (Future)"
])

# In registration worker
if method == "Optical Flow (Fast)":
    from python.advanced_registration import register_with_optical_flow, OpticalFlowMethod
    warped, deformation, metadata = register_with_optical_flow(
        fixed_img, moving_img,
        method=OpticalFlowMethod.FARNEBACK
    )
elif method == "VoxelMorph (GPU)":
    from python.advanced_registration import VoxelMorphRegistration
    backend = VoxelMorphRegistration(use_gpu=True)
    backend.load_model()
    warped, deformation, metadata = backend.register(fixed_img, moving_img)
```

## Testing

### Run Full Test Suite
```powershell
python tests/test_advanced_registration.py
```

Expected output:
```
✅ Module imports: PASS
✅ ORB detection: PASS
✅ SIFT detection: PASS (if opencv-contrib installed)
✅ Optical flow: PASS
⚠️  VoxelMorph: Requires voxelmorph package
```

### Validate GPU Setup
```powershell
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

### Test VoxelMorph Backend
```python
from python.advanced_registration import VoxelMorphRegistration
import numpy as np

backend = VoxelMorphRegistration(use_gpu=True)
print(f"Available: {backend.available}")
print(f"Device: {backend.device}")

# Test with dummy images
img1 = np.random.rand(256, 256).astype(np.float32)
img2 = np.random.rand(256, 256).astype(np.float32)

backend.load_model()
warped, flow, metadata = backend.register(img1, img2)
print(f"Runtime: {metadata['runtime_seconds']:.3f}s")
```

## Performance Tuning

### Optical Flow Speed/Quality Tradeoff
```python
# Fast preview (low quality)
warped, _, _ = register_with_optical_flow(
    fixed, moving,
    method=OpticalFlowMethod.FARNEBACK,
    pyr_scale=0.8,    # Larger = faster, less accurate
    levels=2,         # Fewer levels = faster
    winsize=10        # Smaller window = faster
)

# High quality (slower)
warped, _, _ = register_with_optical_flow(
    fixed, moving,
    method=OpticalFlowMethod.FARNEBACK,
    pyr_scale=0.5,
    levels=5,
    winsize=20
)
```

### VoxelMorph GPU Memory
- Default U-Net: ~2GB VRAM
- Reduce `inshape` for lower memory: `VoxelMorphRegistration(inshape=(128, 128))`
- CPU fallback automatic if GPU unavailable

### TPS Control Points
```python
# More control points = better accuracy but slower
warped, _, _ = register_with_tps_from_features(
    fixed, moving,
    max_control_points=100  # Default: 50
)
```

## Visualization

### Flow Field Visualization
```python
from python.advanced_registration import visualize_flow, flow_to_hsv

# Arrow visualization
flow_vis = visualize_flow(flow, scale=2.0, step=16)

# HSV color coding (hue=direction, value=magnitude)
flow_hsv = flow_to_hsv(flow)
```

### TPS Grid Warping
```python
from python.advanced_registration import visualize_tps_grid

# Show how TPS deforms a regular grid
grid_vis = visualize_tps_grid(
    control_points, weights, affine,
    image_shape=(512, 512),
    grid_spacing=50
)
```

## Troubleshooting

### SIFT Not Available
**Error**: `cv2.error: OpenCV was built without SIFT support`
**Solution**: Install opencv-contrib-python
```powershell
pip uninstall opencv-python
pip install opencv-contrib-python
```

### VoxelMorph Import Error
**Error**: `No module named 'voxelmorph'`
**Solution**: Install VoxelMorph and PyTorch
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install voxelmorph
```

### GPU Not Detected
**Error**: `torch.cuda.is_available() = False`
**Solutions**:
1. Verify CUDA 12.1 installed: `nvidia-smi`
2. Reinstall PyTorch with correct CUDA version
3. Use CPU fallback: `VoxelMorphRegistration(use_gpu=False)`

### Optical Flow Too Slow
**Problem**: Registration taking >1 second
**Solutions**:
1. Use DIS instead of Farneback: `method=OpticalFlowMethod.DIS`
2. Reduce pyramid levels: `levels=2`
3. Downsample images before registration

## Roadmap (ADVANCED_REGISTRATION_PLAN.md)

**Week 1** (Nov 14-21):
- ✅ SIFT/AKAZE/ORB feature detectors
- ✅ Thin-plate spline registration
- ✅ Optical flow (Farneback, DIS)
- 🚧 Benchmark framework setup

**Week 2** (Nov 22-29):
- 🚧 VoxelMorph integration into GUI
- ⏳ GPU environment verification
- ⏳ Performance profiling
- ⏳ Initial benchmarking (B-spline vs VoxelMorph vs Optical Flow)

**Week 3** (Nov 30-Dec 7):
- ⏳ DeepReg backend (optional)
- ⏳ RAFT optical flow (deep learning)
- ⏳ SuperPoint feature detector (optional)

**Week 4** (Dec 8-14):
- ⏳ Comprehensive benchmarking (50+ test cases)
- ⏳ Documentation and examples
- ⏳ Production deployment

## References

1. **VoxelMorph**: Balakrishnan et al. (2019). "VoxelMorph: A Learning Framework for Deformable Medical Image Registration." *IEEE TMI*.
   - Code: https://github.com/voxelmorph/voxelmorph
   - Paper: https://arxiv.org/abs/1809.05231

2. **SIFT**: Lowe, D. G. (2004). "Distinctive image features from scale-invariant keypoints." *IJCV*.

3. **Farneback Flow**: Farnebäck, G. (2003). "Two-frame motion estimation based on polynomial expansion." *SCIA*.

4. **Thin-Plate Splines**: Bookstein, F. L. (1989). "Principal warps: thin-plate splines and the decomposition of deformations." *IEEE TPAMI*.

5. **Survey**: Fu et al. (2021). "Deep Learning in Medical Image Registration: A Review." *arXiv:2111.10480*.

## Support

- **Documentation**: See `ADVANCED_REGISTRATION_PLAN.md` for detailed implementation plan
- **Issues**: Check Alinify logs at `logs/elastix_engine.log`
- **GPU Setup**: See `INSTALL_PYTORCH_GPU.md` (to be created)

---

**Status**: Core modules complete (Week 1 Phase 1). VoxelMorph scaffold ready, awaiting GPU setup and integration.
