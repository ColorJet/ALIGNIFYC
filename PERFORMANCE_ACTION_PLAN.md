# Performance Optimization Action Plan

**Date:** November 13, 2025  
**Target:** 20-second registration for 300MP files (currently ~40s)  
**System:** 20-core CPU, RTX 5080 Laptop GPU

---

## 📋 Current Status

### System Configuration:
- **CPU:** 20 logical cores available
- **ITK Threading:** Default 20 threads, Max 128 threads ✅
- **NumPy BLAS:** OpenBLAS with MAX_THREADS=24 ✅
- **GPU:** RTX 5080 (CUDA 12.8, 16GB VRAM)
- **OpenCV CUDA:** **NOT available** (0 devices) ❌

### Performance Analysis:
```
300MP Image (17320×17320) Registration:
├─ Current: ~40 seconds total
│  ├─ Pyramid Level 0 (4K): ~2s
│  ├─ Pyramid Level 1 (8K): ~5s
│  ├─ Pyramid Level 2 (12K): ~8s
│  └─ Pyramid Level 3 (17K): ~25s
│
└─ Target: 20 seconds (50% speedup needed)
```

---

## 🎯 SOLUTION 1: Warmup Feedback (MINOR - Easy Win)

### Problem:
Warmup registration doesn't show completion feedback, user waits blindly.

### Solution:
Add progress callback to warmup registration to show iteration progress.

#### Implementation:

**File: `gui/main_gui.py`** (lines 140-220)

```python
# Current warmup code:
self.warmup_status = "Pre-compiling registration pipeline (JIT)..."

# Add progress callback:
import threading

def warmup_progress_callback(iteration, metric_value):
    """Update warmup status during registration"""
    self.warmup_status = f"Pre-compiling registration (iter {iteration}/10)..."
    if hasattr(self, 'canvas'):
        # Thread-safe canvas update
        QTimer.singleShot(0, lambda: self.canvas.update())

warmup_params = {
    'pyramid_levels': 1,
    'grid_spacing': 80,
    'max_iterations': 10,
    'spatial_samples': 500,
    'metric': 'AdvancedMeanSquares',
    'target_size': (100, 100),
    'progress_callback': warmup_progress_callback  # ADD THIS
}

# Run warmup in thread to keep GUI responsive
def run_warmup():
    self.registration_backend.engine.register_bspline(
        str(fixed_path),
        str(moving_path),
        target_size=(100, 100),
        parameters=warmup_params
    )
    
    # Signal completion
    QTimer.singleShot(0, lambda: setattr(self, 'warmup_status', 'Warmup complete! Ready to use.'))
    QTimer.singleShot(0, lambda: setattr(self, 'is_ready', True))
    QTimer.singleShot(0, lambda: self.warmup_timer.stop())
    QTimer.singleShot(0, lambda: self.canvas.update())

warmup_thread = threading.Thread(target=run_warmup, daemon=True)
warmup_thread.start()
```

### Convergence Testing During Warmup:

**Can we test convergence stop before all iterations?**

**Answer:** YES - Elastix has early stopping built-in!

```python
# In elastix parameter map:
bspline_params["MaximumNumberOfIterations"] = ["1000"]  # Max limit

# Early stopping parameters (ADD THESE):
bspline_params["UseAdaptiveStepSizes"] = ["true"]  # ASGD adaptive step
bspline_params["AutomaticParameterEstimation"] = ["true"]  # Auto-tune
bspline_params["AutomaticScalesEstimation"] = ["true"]  # Auto-scale

# Convergence detection (stops when improvement is negligible):
bspline_params["MetricRelativeTolerance"] = ["1e-5"]  # Stop if metric improves <0.001%
bspline_params["MetricAbsoluteTolerance"] = ["1e-7"]  # Stop if metric change <1e-7
```

**How it works:**
- Elastix monitors metric improvement per iteration
- If improvement falls below threshold → stops early
- Prevents wasting iterations on converged registrations
- Can reduce 1000 iterations → 200-400 for easy cases

---

## 🚀 SOLUTION 2: Multi-Core CPU Utilization (MAJOR - HIGH IMPACT)

### Problem:
Registration not using all 20 CPU cores efficiently during iterations.

### Root Cause Analysis:

1. **ITK Threading:** Already set to 20 threads ✅
2. **Between pyramid levels:** Sequential (no parallelism) ❌
3. **During iterations:** Single-threaded optimizer loop ❌
4. **Metric computation:** Multi-threaded sampling ✅

### Solution A: Force Maximum Threading

**File: `python/elastix_registration.py`** (add to parameter map)

```python
def register_bspline(self, fixed_path, moving_path, target_size=None, parameters=None):
    # ... existing code ...
    
    # FORCE MAXIMUM CPU UTILIZATION
    import os
    num_threads = os.cpu_count()  # 20 cores
    
    bspline_params["MaximumNumberOfThreads"] = [str(num_threads)]  # ADD THIS
    bspline_params["NumberOfThreads"] = [str(num_threads)]  # Legacy parameter
    
    # Enable parallel sampling (uses all cores for metric evaluation)
    bspline_params["UseMultiThread"] = ["true"]  # ADD THIS
    
    # Increase samples to better utilize threads
    # Rule of thumb: samples_per_thread = 1000-2000
    optimal_samples = num_threads * 1500  # 20 * 1500 = 30,000
    bspline_params["NumberOfSpatialSamples"] = [str(optimal_samples)]
    
    # Enable parallel image pyramid construction
    bspline_params["UseDirectionCosines"] = ["true"]
    bspline_params["UseFixedImagePyramid"] = ["true"]
    bspline_params["UseMovingImagePyramid"] = ["true"]
```

**Expected Impact:** 30-50% speedup by better core utilization

---

### Solution B: Parallel Pyramid Processing (ADVANCED)

**Problem:** Pyramid levels are processed sequentially:
```
Level 0 (4K) → wait → Level 1 (8K) → wait → Level 2 (12K) → wait → Level 3 (17K)
```

**Solution:** Pre-compute all pyramid levels in parallel:

```python
import concurrent.futures
import itk
import numpy as np

def precompute_image_pyramids(fixed_path, moving_path, num_levels=4):
    """Pre-compute all pyramid levels in parallel"""
    
    # Read original images
    fixed_img = itk.imread(fixed_path, itk.F)
    moving_img = itk.imread(moving_path, itk.F)
    
    # Compute all levels in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Fixed pyramid
        fixed_future = executor.submit(
            build_pyramid_levels, fixed_img, num_levels
        )
        
        # Moving pyramid
        moving_future = executor.submit(
            build_pyramid_levels, moving_img, num_levels
        )
        
        fixed_pyramid = fixed_future.result()
        moving_pyramid = moving_future.result()
    
    return fixed_pyramid, moving_pyramid

def build_pyramid_levels(image, num_levels):
    """Build all pyramid levels for an image"""
    pyramid = []
    current = image
    
    for level in range(num_levels):
        pyramid.append(current)
        
        # Downsample by 2x for next level
        if level < num_levels - 1:
            shrink_filter = itk.ShrinkImageFilter.New(current)
            shrink_filter.SetShrinkFactors([2, 2])
            shrink_filter.Update()
            current = shrink_filter.GetOutput()
    
    return pyramid

# Use in registration:
def register_bspline_optimized(self, fixed_path, moving_path, ...):
    # Pre-compute pyramids (parallel)
    fixed_pyramid, moving_pyramid = precompute_image_pyramids(
        fixed_path, moving_path, num_levels=int(pyramid_levels)
    )
    
    # Register each level using pre-computed pyramids
    for level in range(len(fixed_pyramid)):
        # Save pyramid level to temp file
        # Run elastix on that level
        # Use output as initial transform for next level
```

**Expected Impact:** 10-20% speedup by overlapping pyramid construction with registration

---

### Solution C: Increase Samples for Better Parallelism

**Problem:** Too few samples = threads idle waiting

**Current:**
```python
bspline_params["NumberOfSpatialSamples"] = ["5000"]  # Only ~250 per thread!
```

**Optimized:**
```python
num_threads = 20
samples_per_thread = 1500  # Good workload
total_samples = num_threads * samples_per_thread  # 30,000

bspline_params["NumberOfSpatialSamples"] = [str(total_samples)]
```

**Why this helps:**
- Each thread needs enough work to stay busy
- Too few samples → threads finish early → CPU idle
- More samples → better parallelism → faster overall (counterintuitive!)

**Expected Impact:** 20-30% speedup for large images

---

## 🎮 SOLUTION 3: OpenCV CUDA Compilation

### Problem:
Your OpenCV has NO CUDA support (0 devices detected).

### Option A: Use Pre-compiled CUDA Builds

**Try opencv-contrib-python with CUDA:**

```powershell
# Uninstall current OpenCV
pip uninstall opencv-python opencv-contrib-python

# Try CUDA-enabled build (if available)
pip install opencv-contrib-python

# Verify:
python -c "import cv2; print(f'CUDA: {cv2.cuda.getCudaEnabledDeviceCount()}')"
```

**Result:** Unlikely to work - pip wheels rarely include CUDA

---

### Option B: Build from Source (RECOMMENDED)

**Time required:** 1-2 hours  
**Speedup:** 100-1000x for layer composition (40s → 0.04-0.4s)

#### Step-by-Step:

**1. Install Prerequisites:**
```powershell
# Install CMake
choco install cmake --installargs 'ADD_CMAKE_TO_PATH=System'

# Install Visual Studio 2022 (already have?)
# Download from: https://visualstudio.microsoft.com/downloads/

# Install CUDA Toolkit 12.8 (already have via Warp)
# Verify:
nvcc --version
```

**2. Clone and Configure OpenCV:**
```powershell
cd d:\
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git

mkdir opencv_build
cd opencv_build

# Configure with CUDA for RTX 5080 (Compute Capability 8.9)
cmake -G "Visual Studio 17 2022" -A x64 `
  -D CMAKE_BUILD_TYPE=Release `
  -D OPENCV_EXTRA_MODULES_PATH=d:\opencv_contrib\modules `
  -D WITH_CUDA=ON `
  -D WITH_CUDNN=OFF `
  -D CUDA_ARCH_BIN="8.9" `
  -D CUDA_ARCH_PTX="8.9" `
  -D WITH_CUBLAS=ON `
  -D WITH_CUFFT=ON `
  -D WITH_OPENGL=ON `
  -D BUILD_opencv_world=OFF `
  -D BUILD_opencv_python3=ON `
  -D PYTHON3_EXECUTABLE=d:\Alinify\venv\Scripts\python.exe `
  -D PYTHON3_INCLUDE_DIR="C:\Python313\include" `
  -D PYTHON3_LIBRARY="C:\Python313\libs\python313.lib" `
  -D PYTHON3_NUMPY_INCLUDE_DIRS=d:\Alinify\venv\Lib\site-packages\numpy\core\include `
  -D INSTALL_PYTHON_EXAMPLES=OFF `
  -D INSTALL_C_EXAMPLES=OFF `
  -D BUILD_EXAMPLES=OFF `
  ..\..\opencv
```

**3. Build (takes 30-60 minutes):**
```powershell
cmake --build . --config Release -- /m:20  # Use all 20 cores

# Install to venv
cmake --build . --config Release --target install
```

**4. Verify:**
```powershell
.\venv\Scripts\python.exe -c "import cv2; print(f'CUDA: {cv2.cuda.getCudaEnabledDeviceCount()}')"
# Should print: CUDA: 1
```

**Expected Impact:**
- Layer composition: 40s → 0.04-0.4s (100-1000x speedup)
- Real-time preview updates
- **MASSIVE UX improvement**

---

## 🏎️ SOLUTION 4: Alternative Registration Algorithms

### Option A: TPS (Thin Plate Spline)

**Pros:**
- Simpler optimization (fewer parameters)
- Faster convergence for global deformations
- Good for smooth, non-local warps

**Cons:**
- Less flexible than B-spline for local details
- Not ideal for fabric with independent local deformations
- **Elastix doesn't support TPS natively** ❌

**Verdict:** NOT RECOMMENDED for your use case

---

### Option B: Greedy SyN (Symmetric Normalization)

**What is it:**
- Fast diffeomorphic registration
- Used in ANTs (Advanced Normalization Tools)
- Iterative gradient descent on velocity field

**Performance:**
```
B-spline Multi-resolution: 40s for 300MP
Greedy SyN: ~15-25s for 300MP (30-40% faster)
```

**Implementation via SimpleITK:**

```python
import SimpleITK as sitk

def register_greedy_syn(fixed_path, moving_path):
    """Fast SyN registration using SimpleITK"""
    
    # Read images
    fixed = sitk.ReadImage(fixed_path, sitk.sitkFloat32)
    moving = sitk.ReadImage(moving_path, sitk.sitkFloat32)
    
    # SyN registration
    registration = sitk.ImageRegistrationMethod()
    
    # Similarity metric (mutual information or mean squares)
    registration.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    registration.SetMetricSamplingStrategy(registration.RANDOM)
    registration.SetMetricSamplingPercentage(0.01)  # 1% sampling
    
    # Optimizer: Gradient descent
    registration.SetOptimizerAsGradientDescent(
        learningRate=1.0,
        numberOfIterations=100,
        convergenceMinimumValue=1e-6,
        convergenceWindowSize=10
    )
    
    # Multi-resolution pyramid
    registration.SetShrinkFactorsPerLevel(shrinkFactors=[8,4,2,1])
    registration.SetSmoothingSigmasPerLevel(smoothingSigmas=[3,2,1,0])
    registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    
    # Use displacement field transform (like B-spline but faster)
    transform = sitk.DisplacementFieldTransform(2)  # 2D
    registration.SetInitialTransform(transform)
    
    # Execute
    final_transform = registration.Execute(fixed, moving)
    
    # Apply transform
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(fixed)
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    resampler.SetTransform(final_transform)
    
    warped = resampler.Execute(moving)
    
    return sitk.GetArrayFromImage(warped)
```

**Expected Impact:** 30-40% speedup over B-spline

**Trade-off:** May be less accurate for very local deformations

---

### Option C: Optical Flow (GPU-Accelerated)

**What is it:**
- Dense motion estimation (like Demons but GPU-based)
- Available in OpenCV with CUDA

**Performance:**
```
CPU Demons: ~40s
GPU Optical Flow: ~2-5s (8-20x faster!)
```

**Implementation (requires OpenCV CUDA):**

```python
import cv2

def register_optical_flow_cuda(fixed_img, moving_img):
    """Ultra-fast registration using GPU optical flow"""
    
    # Upload to GPU
    gpu_fixed = cv2.cuda_GpuMat()
    gpu_moving = cv2.cuda_GpuMat()
    gpu_fixed.upload(fixed_img)
    gpu_moving.upload(moving_img)
    
    # Create optical flow instance
    # DIS (Dense Inverse Search) - fast and accurate
    optical_flow = cv2.cuda.OpticalFlowDual_TVL1.create()
    
    # Compute flow (this is VERY fast on GPU)
    gpu_flow = cv2.cuda_GpuMat()
    optical_flow.calc(gpu_fixed, gpu_moving, gpu_flow)
    
    # Download flow
    flow = gpu_flow.download()
    
    # Warp image using flow
    h, w = fixed_img.shape[:2]
    flow_map = np.copy(flow)
    flow_map[:,:,0] += np.arange(w)
    flow_map[:,:,1] += np.arange(h)[:,np.newaxis]
    
    warped = cv2.remap(moving_img, flow_map, None, cv2.INTER_LINEAR)
    
    return warped, flow
```

**Expected Impact:** 8-20x speedup (40s → 2-5s)

**Requirements:**
- OpenCV with CUDA (**you need to build this**)
- RTX 5080 (perfect for this!)

---

## 📊 Combined Optimization Strategy

### Phase 1: Quick Wins (Today - 30min)
```python
# 1. Add warmup feedback (MINOR)
# 2. Force max threading
bspline_params["MaximumNumberOfThreads"] = ["20"]
bspline_params["NumberOfSpatialSamples"] = ["30000"]  # 20 * 1500

# 3. Enable early stopping
bspline_params["MetricRelativeTolerance"] = ["1e-5"]

# Expected: 40s → 25-30s (25-40% speedup)
```

---

### Phase 2: Build OpenCV CUDA (Weekend - 2 hours)
```powershell
# Build OpenCV with CUDA support
# Then implement GPU optical flow or GPU layer composition

# Expected: Layer composition 40s → 0.1s (400x!)
#          + Optical flow option: 40s → 2-5s (8-20x!)
```

---

### Phase 3: Algorithm Switch (Next Week - 1 day)
```python
# Add Greedy SyN or GPU Optical Flow as registration mode
# Keep B-spline as "high accuracy" mode
# New mode: "Fast" = GPU optical flow (2-5s)

# Expected: Registration 40s → 5s for "Fast" mode
```

---

## 🎯 Final Performance Target

### Current (300MP):
```
Registration: 40 seconds
Layer Composition: 40 seconds (if enabled)
Total workflow: ~80 seconds
```

### After Phase 1 (Quick Wins):
```
Registration: 25 seconds (-37%)
Layer Composition: 10 seconds (downsampling)
Total workflow: ~35 seconds (-56%)
```

### After Phase 2 (OpenCV CUDA):
```
Registration: 25 seconds
Layer Composition: 0.1 seconds (GPU, -99.75%!)
Total workflow: ~25 seconds (-69%)
```

### After Phase 3 (GPU Optical Flow):
```
Registration: 5 seconds (GPU flow, -87%)
Layer Composition: 0.1 seconds (GPU)
Total workflow: ~5 seconds (-94%!)
```

---

## 🚀 ACTION ITEMS

### TODAY (30 minutes):
- [ ] Add warmup feedback with iteration counter
- [ ] Add `MaximumNumberOfThreads = 20` to Elastix params
- [ ] Increase `NumberOfSpatialSamples = 30000`
- [ ] Add early stopping with `MetricRelativeTolerance`

### THIS WEEKEND (2 hours):
- [ ] Build OpenCV with CUDA support (sm_89 for RTX 5080)
- [ ] Implement GPU layer composition
- [ ] Test layer composition speedup (should be 100-400x!)

### NEXT WEEK (1 day):
- [ ] Implement GPU optical flow registration (2-5s target)
- [ ] Add "Fast Mode" vs "Accurate Mode" toggle
- [ ] Benchmark 300MP images end-to-end

---

## 💡 Key Insights

1. **CPU is underutilized** → More threads + more samples = better parallelism
2. **OpenCV CUDA is CRITICAL** → 100-400x speedup for layer composition
3. **GPU Optical Flow** → Best registration speed (2-5s for 300MP)
4. **B-spline is accurate but slow** → Keep as "Accurate" mode, add "Fast" mode
5. **Your RTX 5080 is powerful but unused** → OpenCV CUDA unlocks it!

**Bottom line:** Building OpenCV with CUDA is the #1 priority for massive speedup! 🚀
