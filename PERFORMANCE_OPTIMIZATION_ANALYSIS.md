# Performance Optimization Analysis & Recommendations

**Date:** November 13, 2025  
**Issue:** Layer composition causing 40s GUI freeze, JIT compilation causing 15-20s startup delay

---

## 🔍 Current Performance Bottlenecks

### 1. **Layer Composition (40s freeze)** - CRITICAL
- **Location:** `gui/widgets/layer_manager.py` → `LayerCompositor.compose_layers()`
- **Root Cause:** CPU-bound pixel-by-pixel operations on full-resolution images
- **Problem Code:**
  ```python
  # Pixel-by-pixel blend operations at full resolution
  result = cv2.addWeighted(result, 1.0 - opacity, blended, opacity, 0)
  
  # Multiple blend modes using NumPy (CPU-bound)
  base = base.astype(np.float32) / 255.0  # Full image conversion
  overlay = overlay.astype(np.float32) / 255.0
  result = np.where(mask, 2.0 * base * overlay, ...)  # Element-wise operations
  ```

### 2. **JIT Compilation (15-20s startup)** - MEDIUM
- **Location:** `python/elastix_registration.py` → First call to `itk.elastix_registration_method()`
- **Root Cause:** ITK-Python uses JIT compilation for C++ templates on first use
- **Current Solution:** Pre-warming with dummy 100×100 registration during startup ✅

---

## 💡 Optimization Strategies

### A. **Layer Composition Optimization** (Most Impactful)

#### ⭐ Option 1: GPU Acceleration with CUDA/OpenGL ⭐
**Best approach for real-time performance**

```python
# Use OpenCV with CUDA backend (if available)
import cv2

# Enable CUDA acceleration
cv2.cuda.setDevice(0)

class GPULayerCompositor:
    def __init__(self):
        self.use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
    
    def compose_layers(self, layers_data, canvas_size):
        if self.use_cuda:
            # Upload to GPU memory once
            gpu_result = cv2.cuda_GpuMat()
            gpu_result.upload(base_image)
            
            for layer in layers_data:
                gpu_layer = cv2.cuda_GpuMat()
                gpu_layer.upload(layer['image'])
                
                # GPU-accelerated blend (milliseconds instead of seconds)
                cv2.cuda.addWeighted(gpu_result, 1-opacity, gpu_layer, opacity, 0, gpu_result)
            
            # Download result only once
            return gpu_result.download()
```

**Pros:**
- 100-1000x speedup (40s → 0.04-0.4s)
- Real-time layer composition
- Uses existing GPU (RTX 5080 Laptop)

**Cons:**
- Requires OpenCV with CUDA support (rebuild or binary)
- Additional dependency

---

#### Option 2: Multi-threaded CPU with Numba JIT
**Moderate speedup without GPU**

```python
from numba import jit, prange
import numpy as np

@jit(nopython=True, parallel=True, fastmath=True)
def blend_layers_fast(base, overlay, opacity):
    result = np.empty_like(base)
    for i in prange(base.shape[0]):  # Parallel loop
        for j in range(base.shape[1]):
            for c in range(3):
                result[i, j, c] = base[i, j, c] * (1 - opacity) + overlay[i, j, c] * opacity
    return result

class OptimizedLayerCompositor:
    def compose_layers(self, layers_data, canvas_size):
        result = base_image
        for layer in layers_data:
            result = blend_layers_fast(result, layer['image'], layer['opacity'])
        return result
```

**Pros:**
- 5-10x speedup (40s → 4-8s)
- No additional dependencies (Numba already available)
- Cross-platform

**Cons:**
- Still slower than GPU
- First-time JIT compilation delay

---

#### Option 3: Downsample for Preview (Quick Win)
**Immediate fix with minimal code changes**

```python
def compose_layers(layers_data, canvas_size, preview_mode=True):
    """Compose layers with optional downsampling for preview"""
    
    # Downsample for preview (4x faster)
    if preview_mode and max(canvas_size) > 1024:
        scale = 1024 / max(canvas_size)
        preview_size = (int(canvas_size[1] * scale), int(canvas_size[0] * scale))
        
        # Resize all layers once
        layers_downsampled = []
        for layer in layers_data:
            img = cv2.resize(layer['image'], preview_size, interpolation=cv2.INTER_LINEAR)
            layers_downsampled.append({**layer, 'image': img})
        
        # Compose at lower resolution
        result = compose_layers_internal(layers_downsampled, preview_size)
        
        # Upscale result for display (fast)
        return cv2.resize(result, (canvas_size[1], canvas_size[0]), interpolation=cv2.INTER_LINEAR)
    
    return compose_layers_internal(layers_data, canvas_size)
```

**Pros:**
- 4-16x speedup (40s → 2.5-10s) depending on downscale factor
- Minimal code changes
- No new dependencies

**Cons:**
- Reduced preview quality
- Still needs full-res for export

---

### B. **Elastix Registration Optimization**

#### Option 1: Use elastix.exe/transformix.exe CLI (Subprocess)
**NOT RECOMMENDED** - Actually slower than ITK-Python

```python
import subprocess
import tempfile

def register_with_cli(fixed_path, moving_path, params):
    """Use elastix.exe instead of ITK-Python"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write parameter file
        param_file = Path(tmpdir) / "params.txt"
        write_elastix_params(param_file, params)
        
        # Run elastix.exe
        subprocess.run([
            "elastix.exe",
            "-f", fixed_path,
            "-m", moving_path,
            "-p", param_file,
            "-out", tmpdir
        ])
        
        # Read result
        result_path = Path(tmpdir) / "result.0.mhd"
        return itk.imread(str(result_path))
```

**Why NOT to use this:**
- ❌ Subprocess overhead (process creation, file I/O)
- ❌ Disk I/O bottleneck (write inputs, read outputs)
- ❌ No Python integration (harder to control/debug)
- ❌ Similar or slower than ITK-Python (both use same C++ core)
- ❌ JIT compilation happens anyway when loading results

**Current ITK-Python approach is BETTER:**
- ✅ Direct memory access (no file I/O)
- ✅ Better error handling
- ✅ Python integration (callbacks, progress tracking)
- ✅ JIT already optimized with pre-warming

---

#### Option 2: C++ Rewrite (Overkill)
**NOT RECOMMENDED** - Minimal benefit

**Reasons:**
- Registration itself is already fast (2s for 4K image)
- JIT compilation only happens once (pre-warming solves this)
- C++ would require Qt for GUI (similar performance)
- Development cost >> performance gain
- ITK/Elastix core is already C++ (we're just calling it)

---

## 🎯 Recommended Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
1. **Implement downsampled preview mode for layer composition**
   - Add `preview_scale` parameter to `LayerCompositor.compose_layers()`
   - Downsample to 1024px max dimension for canvas display
   - Keep full-res for final export
   - **Expected result:** 40s → 5-10s

2. **Cache composed result until layers change**
   ```python
   class LayerCanvas:
       def __init__(self):
           self._cache_key = None
           self._cached_composition = None
       
       def updateComposition(self):
           current_key = self.getLayersHash()
           if current_key == self._cache_key:
               return  # Use cached result
           
           self._cached_composition = LayerCompositor.compose_layers(...)
           self._cache_key = current_key
   ```
   - **Expected result:** Eliminate redundant recompositions

### Phase 2: GPU Acceleration (4-8 hours)
1. **Check if OpenCV has CUDA support**
   ```python
   print(cv2.getBuildInformation())  # Look for CUDA: YES
   print(cv2.cuda.getCudaEnabledDeviceCount())
   ```

2. **If CUDA available:** Implement `GPULayerCompositor`
   - Upload layers to GPU once
   - Perform all blending on GPU
   - Download final result
   - **Expected result:** 40s → 0.1-0.5s (100x faster)

3. **If CUDA not available:** Install OpenCV with CUDA
   ```bash
   pip uninstall opencv-python opencv-contrib-python
   pip install opencv-contrib-python  # Check for CUDA builds
   # Or build from source with -D WITH_CUDA=ON
   ```

### Phase 3: Fallback Optimization (2-4 hours)
1. **If GPU not viable:** Implement Numba JIT version
   - Use `@jit(nopython=True, parallel=True)` for blend operations
   - **Expected result:** 40s → 5-8s

---

## 📊 Performance Comparison

| Method | Layer Composition Time | Registration Time | Startup Time |
|--------|------------------------|-------------------|--------------|
| **Current** | 40s ❌ | 2s ✅ | 15-20s ⚠️ |
| **+ Downsampled Preview** | 5-10s ⚠️ | 2s ✅ | 15-20s ⚠️ |
| **+ GPU Acceleration** | 0.1-0.5s ✅ | 2s ✅ | 15-20s ⚠️ |
| **+ Numba JIT** | 5-8s ⚠️ | 2s ✅ | 20-25s ⚠️ |
| **CLI elastix.exe** | 40s ❌ | 3-5s ❌ | 0s ✅ (but slower overall) |
| **Full C++ Rewrite** | ??? | 2s ✅ | 0s ✅ (huge dev cost) |

---

## 🚀 Quick Implementation: Downsampled Preview

Here's the immediate fix you can apply right now:

```python
# In gui/widgets/layer_manager.py

class LayerCompositor:
    @staticmethod
    def compose_layers(layers_data, global_settings, canvas_size=None, max_preview_size=1024):
        """Compose layers with optional preview downsampling"""
        
        if not layers_data:
            return None
        
        # Determine canvas size
        if canvas_size is None:
            max_h, max_w = 0, 0
            for layer in layers_data:
                img = layer['image']
                if img is not None:
                    h, w = img.shape[:2]
                    max_h = max(max_h, h)
                    max_w = max(max_w, w)
            canvas_size = (max_h, max_w)
        
        # Downsample for preview if too large
        original_size = canvas_size
        scale_factor = 1.0
        
        if max_preview_size and max(canvas_size) > max_preview_size:
            scale_factor = max_preview_size / max(canvas_size)
            canvas_size = (
                int(canvas_size[0] * scale_factor),
                int(canvas_size[1] * scale_factor)
            )
            print(f"🔄 Preview mode: Downsampling {original_size} → {canvas_size} ({scale_factor:.2f}x)")
        
        # ... rest of composition code works on downsampled images ...
        
        return result.astype(np.uint8)
```

---

## 🎬 Conclusion

### DO THIS:
1. ✅ **Keep ITK-Python for registration** (already fast with pre-warming)
2. ✅ **Implement downsampled preview mode** (quick win)
3. ✅ **Add layer composition caching** (avoid redundant work)
4. ✅ **Try GPU acceleration with OpenCV CUDA** (massive speedup)

### DON'T DO THIS:
1. ❌ **Don't switch to elastix.exe CLI** (slower, more complex)
2. ❌ **Don't rewrite in C++** (huge cost, minimal gain)
3. ❌ **Don't over-optimize registration** (already fast enough)

### Focus Area:
**Layer composition is the bottleneck, not registration!** 🎯

The 40s freeze is pure NumPy/OpenCV CPU operations. GPU acceleration or downsampling will solve this. Registration itself (2s) is already excellent and doesn't need optimization.
