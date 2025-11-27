# Advanced Registration Architecture

## Module Hierarchy

```
Alinify GUI
│
├── Main GUI (gui/main_gui.py)
│   └── Registration Tab
│       ├── Preprocessing Selector (11 methods)
│       │   ├── Gabor Filter ✅
│       │   ├── Frangi Vesselness ✅
│       │   ├── Structure Tensor ✅
│       │   └── ... (existing methods)
│       │
│       └── Fine Registration Selector (to be added)
│           ├── B-spline (Elastix) - Current Default
│           ├── VoxelMorph (GPU DL) - NEW
│           ├── Optical Flow (Fast) - NEW
│           └── Thin-Plate Spline - NEW
│
├── Registration Backend (python/registration_backend.py)
│   ├── Elastix B-spline wrapper
│   ├── Preprocessing methods (11 total)
│   └── Backend dispatcher (to be extended)
│
└── Advanced Registration (python/advanced_registration/)
    ├── VoxelMorph Backend ✅
    │   ├── GPU auto-detection
    │   ├── Model loading (pre-trained or default U-Net)
    │   └── register() method (~0.5-1s)
    │
    ├── Feature Detectors ✅
    │   ├── SIFT (scale-invariant, 128-dim)
    │   ├── AKAZE (fast binary descriptors)
    │   ├── ORB (current default)
    │   └── SuperPoint (DL, future)
    │
    ├── Optical Flow ✅
    │   ├── Farneback (pyramidal, 0.2-0.5s)
    │   ├── DIS (large displacements)
    │   └── RAFT (DL, future)
    │
    └── TPS Registration ✅
        ├── Feature-based pipeline
        ├── RANSAC outlier filtering
        └── Deformation field computation
```

## Registration Pipeline Flow

### Current Workflow (B-spline)
```
Input Images
    ↓
Preprocessing (optional)
    ↓
Phase Correlation (coarse alignment)
    ↓
Elastix B-spline (5-10s)
    ↓
Warped Image + Deformation Field
```

### New Workflows Available

#### 1. VoxelMorph (GPU-Accelerated DL)
```
Input Images
    ↓
Preprocessing (optional)
    ↓
VoxelMorph Backend
    ├── Convert to PyTorch tensors
    ├── Normalize to [0, 1]
    ├── GPU inference (~0.5-1s)
    └── Deformation field extraction
    ↓
Warped Image + Dense Flow Field
```

#### 2. Optical Flow (Fastest)
```
Input Images
    ↓
Preprocessing (optional)
    ↓
Farneback/DIS Optical Flow
    ├── Pyramidal computation
    ├── Dense flow field (0.2-0.5s)
    └── Image warping
    ↓
Warped Image + Flow Vectors
```

#### 3. Thin-Plate Spline (Feature-Based)
```
Input Images
    ↓
Feature Detection (SIFT/AKAZE/ORB)
    ↓
Feature Matching + RANSAC
    ↓
Control Point Extraction (~50 points)
    ↓
TPS Matrix Computation
    ↓
Non-rigid Warping (1-3s)
    ↓
Warped Image + Deformation Field
```

## Data Flow

### Image Preprocessing Stage
```python
# User selects from GUI dropdown
preprocessing_method = "gabor"  # or "frangi", "structure_tensor", etc.

# Backend applies preprocessing
fixed_img = registration_backend.preprocess_image(fixed_img, method=preprocessing_method)
moving_img = registration_backend.preprocess_image(moving_img, method=preprocessing_method)
```

### Registration Stage (Multi-Backend)
```python
# User selects registration method
fine_registration_method = "voxelmorph"  # or "optical_flow", "tps", "bspline"

if fine_registration_method == "voxelmorph":
    from python.advanced_registration import VoxelMorphRegistration
    backend = VoxelMorphRegistration(use_gpu=True)
    backend.load_model()
    warped, deformation, metadata = backend.register(fixed_img, moving_img)
    
elif fine_registration_method == "optical_flow":
    from python.advanced_registration import register_with_optical_flow, OpticalFlowMethod
    warped, deformation, metadata = register_with_optical_flow(
        fixed_img, moving_img,
        method=OpticalFlowMethod.FARNEBACK
    )
    
elif fine_registration_method == "tps":
    from python.advanced_registration import register_with_tps_from_features
    warped, deformation, metadata = register_with_tps_from_features(
        fixed_img, moving_img,
        detector_type='sift'
    )
    
else:  # "bspline" (current default)
    warped, deformation = registration_backend.register_bspline(fixed_img, moving_img)
```

## Performance Characteristics

### Method Comparison Matrix

|  | Speed | Accuracy | GPU? | Memory | Best For |
|--|-------|----------|------|--------|----------|
| **B-spline** | 5-10s | ⭐⭐⭐⭐ | No | 500MB | General-purpose |
| **VoxelMorph** | 0.5-1s | ⭐⭐⭐⭐⭐ | Yes | 2GB VRAM | Tone-on-tone, production |
| **Optical Flow** | 0.2-0.5s | ⭐⭐⭐ | Optional | 100MB | Real-time preview |
| **TPS** | 1-3s | ⭐⭐⭐⭐ | No | 200MB | Feature-rich patterns |

### Deformation Capacity

```
Optical Flow    [====    ] Small-medium deformations
B-spline        [======  ] Medium-large deformations
TPS             [======= ] Medium-large (control point limited)
VoxelMorph      [========] Large deformations, learned priors
```

## Dependency Graph

### Core Dependencies (Already Installed)
```
OpenCV >= 4.8.0
    ├── ORB feature detection ✅
    ├── AKAZE feature detection ✅
    ├── Farneback optical flow ✅
    └── DIS optical flow ✅
    
NumPy >= 1.24.0
    └── Array operations ✅
    
SciPy >= 1.10.0
    ├── cdist (TPS kernel) ✅
    └── Linear system solving ✅
    
scikit-image >= 0.21.0
    ├── Gabor filters ✅
    ├── Frangi vesselness ✅
    └── Structure tensor ✅
```

### Optional Dependencies (GPU/ML)
```
opencv-contrib-python (optional)
    └── SIFT feature detection ⚠️ (installed, working)
    
PyTorch >= 2.0 + CUDA 12.1 (optional)
    └── GPU acceleration ⏳ (not installed)
        ├── VoxelMorph backend
        └── Future: RAFT, SuperPoint
        
voxelmorph (optional)
    └── Deep learning registration ⏳ (not installed)
```

## File Structure (Detailed)

```
python/advanced_registration/
│
├── __init__.py (80 lines)
│   └── Exports: VoxelMorphRegistration, detect_features_sift,
│                compute_dense_flow_farneback, register_with_tps, etc.
│
├── voxelmorph_backend.py (324 lines)
│   ├── class VoxelMorphRegistration
│   │   ├── __init__(model_path, use_gpu)
│   │   ├── _setup_device()           # GPU auto-detection
│   │   ├── load_model()               # Pre-trained or default U-Net
│   │   ├── register(fixed, moving)    # Main registration method
│   │   ├── warp_image(image, flow)    # Apply deformation
│   │   ├── _preprocess()              # Normalize to [0,1], tensor conversion
│   │   ├── _denormalize()             # Back to uint8
│   │   └── _apply_flow()              # grid_sample spatial transformer
│   └── register_voxelmorph()          # Convenience function
│
├── feature_detectors.py (285 lines)
│   ├── enum FeatureDetector          # SIFT, AKAZE, ORB, SUPERPOINT
│   ├── detect_features_sift()        # SIFT detector (128-dim descriptors)
│   ├── detect_features_akaze()       # AKAZE detector (binary)
│   ├── detect_features_orb()         # ORB detector (32-dim binary)
│   ├── match_features()              # FLANN (SIFT) or BFMatcher (binary)
│   ├── compute_transform_from_matches() # Homography with RANSAC
│   ├── detect_and_match()            # Complete pipeline
│   └── detect_features_superpoint()  # Placeholder (Week 3)
│
├── optical_flow.py (270 lines)
│   ├── enum OpticalFlowMethod        # FARNEBACK, DIS, RAFT
│   ├── compute_dense_flow_farneback() # Pyramidal flow (0.2-0.5s)
│   ├── compute_dense_flow_dis()      # Dense Inverse Search
│   ├── warp_image_with_flow()        # Apply flow to image
│   ├── flow_to_deformation_field()   # Convert flow to coordinates
│   ├── register_with_optical_flow()  # Complete pipeline
│   ├── visualize_flow()              # Arrow visualization
│   ├── flow_to_hsv()                 # HSV color coding
│   └── compute_dense_flow_raft()     # Placeholder (Week 3)
│
├── tps_registration.py (360 lines)
│   ├── compute_tps_matrices()        # Solve linear system for TPS weights
│   ├── _compute_tps_kernel()         # r² log(r) radial basis
│   ├── apply_tps_transform()         # Warp image with TPS
│   ├── _tps_interpolate()            # Affine + non-rigid parts
│   ├── register_with_tps()           # TPS from given control points
│   ├── extract_control_points_from_matches() # RANSAC filtering
│   ├── register_with_tps_from_features() # Complete pipeline
│   ├── visualize_tps_control_points() # Draw control points
│   └── visualize_tps_grid()          # Warped grid visualization
│
└── README.md (550 lines)
    ├── Installation instructions
    ├── Quick start examples
    ├── API reference
    ├── Benchmark comparison
    ├── GUI integration guide
    ├── Performance tuning
    └── Troubleshooting
```

## Integration Points

### 1. GUI Integration (gui/main_gui.py)

**Add to Registration Tab**:
```python
# Fine registration method selector
self.label_fine_method = QLabel("Fine Registration Method:")
self.combo_fine_method = QComboBox()
self.combo_fine_method.addItems([
    "B-spline (Elastix) - Robust",
    "VoxelMorph (GPU) - Fast & Accurate",
    "Optical Flow - Fastest Preview",
    "Thin-Plate Spline - Feature-Rich"
])
self.combo_fine_method.setToolTip(
    "B-spline: General-purpose, 5-10s\n"
    "VoxelMorph: GPU-accelerated, 0.5-1s (requires PyTorch)\n"
    "Optical Flow: Real-time preview, 0.2-0.5s\n"
    "TPS: Feature-based, 1-3s"
)

# GPU status indicator
self.label_gpu_status = QLabel()
self._update_gpu_status()

def _update_gpu_status(self):
    try:
        import torch
        if torch.cuda.is_available():
            self.label_gpu_status.setText("🟢 GPU Available")
            self.label_gpu_status.setStyleSheet("color: green;")
        else:
            self.label_gpu_status.setText("🟡 CPU Only")
            self.label_gpu_status.setStyleSheet("color: orange;")
    except ImportError:
        self.label_gpu_status.setText("🔴 PyTorch Not Installed")
        self.label_gpu_status.setStyleSheet("color: red;")
```

### 2. Backend Integration (python/registration_backend.py)

**Add Method Dispatcher**:
```python
def register(self, fixed_img, moving_img, method='bspline', **kwargs):
    """
    Unified registration interface
    
    Args:
        fixed_img: Fixed image
        moving_img: Moving image
        method: 'bspline', 'voxelmorph', 'optical_flow', 'tps'
        **kwargs: Method-specific parameters
    """
    if method == 'voxelmorph':
        from python.advanced_registration import VoxelMorphRegistration
        backend = VoxelMorphRegistration(use_gpu=kwargs.get('use_gpu', True))
        backend.load_model(kwargs.get('model_path'))
        return backend.register(fixed_img, moving_img)
    
    elif method == 'optical_flow':
        from python.advanced_registration import register_with_optical_flow, OpticalFlowMethod
        flow_method = kwargs.get('flow_method', OpticalFlowMethod.FARNEBACK)
        return register_with_optical_flow(fixed_img, moving_img, method=flow_method)
    
    elif method == 'tps':
        from python.advanced_registration import register_with_tps_from_features
        return register_with_tps_from_features(
            fixed_img, moving_img,
            detector_type=kwargs.get('detector', 'sift'),
            max_control_points=kwargs.get('max_control_points', 50)
        )
    
    else:  # 'bspline'
        return self.register_bspline(fixed_img, moving_img, **kwargs)
```

### 3. Worker Thread (gui/widgets/background_workers.py)

**Update RegistrationWorker**:
```python
class RegistrationWorker(QThread):
    def __init__(self, ..., fine_method='bspline', fine_method_kwargs=None):
        # ... existing code ...
        self.fine_method = fine_method
        self.fine_method_kwargs = fine_method_kwargs or {}
    
    def run(self):
        # ... preprocessing code ...
        
        # Registration with method selection
        warped, deformation, metadata = self.backend.register(
            fixed_img,
            moving_img,
            method=self.fine_method,
            **self.fine_method_kwargs
        )
        
        # ... emit results ...
```

## Testing Strategy

### Unit Tests
```python
# tests/test_advanced_registration.py
def test_feature_detection():
    for detector in [FeatureDetector.SIFT, FeatureDetector.AKAZE, FeatureDetector.ORB]:
        kp, desc = detect_and_match(img1, img2, detector=detector)
        assert len(kp) > 0

def test_optical_flow():
    for method in [OpticalFlowMethod.FARNEBACK, OpticalFlowMethod.DIS]:
        warped, flow, metadata = register_with_optical_flow(img1, img2, method=method)
        assert warped.shape == img1.shape
        assert metadata['runtime_seconds'] < 1.0

def test_tps():
    warped, deformation, metadata = register_with_tps_from_features(img1, img2)
    assert metadata['n_control_points'] > 3

def test_voxelmorph():
    backend = VoxelMorphRegistration(use_gpu=torch.cuda.is_available())
    backend.load_model()
    warped, flow, metadata = backend.register(img1, img2)
    assert flow.shape[-1] == 2  # (H, W, 2)
```

### Integration Tests
```python
# tests/test_registration_pipeline.py
def test_end_to_end_voxelmorph():
    # Load real fabric images
    fixed = cv2.imread("test_fabric_1.jpg", 0)
    moving = cv2.imread("test_fabric_2.jpg", 0)
    
    # Preprocess
    fixed = preprocess_image(fixed, method='gabor')
    moving = preprocess_image(moving, method='gabor')
    
    # Register with VoxelMorph
    backend = VoxelMorphRegistration(use_gpu=True)
    backend.load_model()
    warped, flow, metadata = backend.register(fixed, moving)
    
    # Validate
    assert warped.shape == fixed.shape
    assert metadata['runtime_seconds'] < 2.0
    
    # Compare quality
    mse_before = np.mean((fixed - moving) ** 2)
    mse_after = np.mean((fixed - warped) ** 2)
    assert mse_after < mse_before
```

### Benchmark Tests
```python
# tests/benchmark/benchmark_registration.py
methods = ['bspline', 'voxelmorph', 'optical_flow', 'tps']
results = {method: {'runtimes': [], 'mse': [], 'mi': []} for method in methods}

for test_pair in test_image_pairs:
    fixed, moving = test_pair
    for method in methods:
        start = time.time()
        warped, _, _ = register(fixed, moving, method=method)
        runtime = time.time() - start
        
        results[method]['runtimes'].append(runtime)
        results[method]['mse'].append(np.mean((fixed - warped) ** 2))
        results[method]['mi'].append(mutual_information(fixed, warped))

# Generate report
plot_boxplot(results)
print_summary_table(results)
```

---

**Last Updated**: 2025-01-13
**Status**: Architecture complete, ready for GPU setup and integration
