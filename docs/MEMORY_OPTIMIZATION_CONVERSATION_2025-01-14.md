# Memory Optimization Conversation Summary
## Date: January 14, 2025

## System Specifications
- **CPU RAM**: 32GB
- **GPU**: 16GB dedicated VRAM
- **Image Size**: 283MP fabric scans (18960×14960 pixels)

---

## Problem 1: Import Error
**Error**: `No module named 'python'`

**Fix**: Changed 5 import statements in `gui/main_gui.py`:
```python
# Before
from python.advanced_registration import ...

# After  
from advanced_registration import ...
```

---

## Problem 2: Attribute Name Mismatch
**Error**: `AttributeError: 'AlinifyMainWindow' object has no attribute 'camera_img'`

**Fix**: Lines 2511-2512 in `gui/main_gui.py`:
```python
# Before
self.camera_img
self.design_img

# After
self.camera_image
self.design_image
```

---

## Problem 3: ITK Memory Allocation Failure (Registration)
**Error**: `RuntimeError: Failed to allocate memory for image` (283MP images)

**Root Cause**: Downsampling logic in `registration_backend.py` was being SKIPPED when GUI passed parameters without explicit `target_size` key.

**The Bug** (lines 204-205):
```python
# BROKEN - skips auto-downsampling when parameters exists but has no target_size
if parameters and 'target_size' in parameters:
    target_size = parameters['target_size']
else:
    # Auto-scale logic (never reached!)
```

**The Fix**:
```python
# FIXED - always check image dimensions for safety
if parameters and 'target_size' in parameters and parameters['target_size'] is not None:
    target_size = parameters['target_size']
else:
    # ALWAYS auto-scale large images
    max_dim = max(fixed_gray.shape)
    if max_dim > 1024:
        scale = 1024 / max_dim
        target_h = int(fixed_gray.shape[0] * scale)
        target_w = int(fixed_gray.shape[1] * scale)
        target_size = (target_h, target_w)
    else:
        target_size = None
```

---

## Problem 4: PyTorch CPU Memory Allocation Failure (Warping)
**Error**: `RuntimeError: [enforce fail at alloc_cpu.cpp:121] not enough memory: you tried to allocate 3402135072 bytes`

**Root Cause**: After successful registration on downsampled images, the code tried to warp the FULL 283MP RGB image, requiring 3.4GB CPU allocation before GPU transfer.

**Calculation**:
- 18960 × 14960 × 3 channels × 4 bytes (float32) = 3,402,135,040 bytes = **3.4GB**

---

## The Real Issue: Unnecessary Downsampling

**User's Valid Point**: With 32GB RAM and 16GB GPU, forcing downsampling to 1024px is NOT smart. The system should:

1. **Use available memory intelligently**
2. **Only downsample when actually needed**
3. **Process at highest resolution possible**

---

## Proposed Smart Solution

### 1. Dynamic Memory-Based Sizing

Instead of hardcoded 1024px limit, calculate based on available memory:

```python
def get_smart_target_size(image_shape, available_ram_gb=32, available_vram_gb=16):
    """Calculate optimal processing size based on available memory"""
    height, width = image_shape[:2]
    total_pixels = height * width
    
    # Memory requirements per pixel:
    # - Registration (grayscale float32): 4 bytes
    # - Warping (RGB float32): 12 bytes
    # - Deformation field (2 channels float32): 8 bytes
    # - Safety factor: 2x for intermediate buffers
    bytes_per_pixel = 24 * 2  # 48 bytes with safety
    
    # Use 50% of available VRAM for processing
    max_bytes = int(available_vram_gb * 1024**3 * 0.5)
    max_pixels = max_bytes // bytes_per_pixel
    
    if total_pixels <= max_pixels:
        return None  # No downsampling needed!
    
    # Calculate scale to fit in memory
    scale = (max_pixels / total_pixels) ** 0.5
    target_h = int(height * scale)
    target_w = int(width * scale)
    
    return (target_h, target_w)
```

### 2. For 16GB GPU with 32GB RAM

With your hardware:
- Max VRAM usage (50%): 8GB
- Max pixels: 8GB / 48 bytes = ~170 million pixels
- Your images: 283 million pixels
- Required downscale: ~78% → **~14700 × 11700** (not 1024!)

This means you could process at **~170MP** instead of being forced to 1MP!

### 3. Tiled Warping for Large Images

For warping, use tiles to avoid loading entire image at once:

```python
def warp_rgb_tiled(self, rgb_path, deformation_field, output_path, tile_size=4096):
    """Warp large RGB images using tiles to avoid memory issues"""
    rgb = cv2.imread(str(rgb_path))
    h, w = rgb.shape[:2]
    result = np.zeros_like(rgb)
    
    # Process in tiles
    for y in range(0, h, tile_size):
        for x in range(0, w, tile_size):
            # Extract tile
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            
            tile = rgb[y:y_end, x:x_end]
            deform_tile = deformation_field[y:y_end, x:x_end]
            
            # Warp tile on GPU
            warped_tile = self._warp_tile_gpu(tile, deform_tile)
            result[y:y_end, x:x_end] = warped_tile
            
            # Clear GPU cache
            torch.cuda.empty_cache()
    
    cv2.imwrite(str(output_path), result)
    return result
```

---

## Files to Modify

### 1. `python/registration_backend.py`
- Replace hardcoded 1024px with smart memory calculation
- Add tiled warping support

### 2. `python/elastix_registration.py`  
- Remove redundant size calculations (already simplified)
- Add tiled warp method

### 3. `config/system_config.yaml` (optional)
```yaml
memory:
  max_registration_pixels: auto  # or specific number
  max_warp_pixels: auto
  tile_size: 4096
  use_tiled_warping: true
```

---

## Quick Fix vs Smart Fix

### Quick Fix (Conservative)
Change 1024 limit to 4096 or 8192:
```python
if max_dim > 4096:  # Instead of 1024
    scale = 4096 / max_dim
```
This would give you ~16MP processing instead of 1MP.

### Smart Fix (Recommended)
Implement memory-based dynamic sizing as described above.

---

## Commands to Apply Fixes

The edits I made during our conversation were undone. To re-apply:

1. **Fix the downsampling condition** (prevents skip):
   - File: `python/registration_backend.py`
   - Line ~204-225
   - Add `and parameters['target_size'] is not None` check

2. **Increase processing limit** (quick fix):
   - File: `python/registration_backend.py`
   - Change `if max_dim > 1024` to `if max_dim > 4096`

3. **Add tiled warping** (best fix):
   - File: `python/elastix_registration.py`
   - Add `warp_rgb_tiled()` method

---

## Testing

After applying fixes, test with:
```python
python test_downsampling_logic.py  # Verify logic
python gui/main_gui.py             # Test full pipeline
```

---

## Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| Import error | Wrong package path | `python.X` → `X` |
| Attribute error | Naming mismatch | `camera_img` → `camera_image` |
| ITK memory crash | Downsampling skipped | Fix conditional logic |
| PyTorch memory crash | Full 283MP warp | Use tiled warping |
| Over-conservative limits | Hardcoded 1024px | Smart memory calculation |

---

## Conversation Context

This document summarizes debugging session for Alinify fabric registration software:
- ITK-Elastix based registration
- PyTorch GPU acceleration  
- VoxelMorph deep learning integration
- Support for 283MP industrial fabric scans

The core issue was that 1024px downsampling was being applied unnecessarily, reducing image quality when the system has plenty of memory to handle larger sizes.
