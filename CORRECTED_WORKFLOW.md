# CORRECTED WORKFLOW: Pattern Tiling → Registration → High-Res Warping

## 📋 **Terminology (FIXED)**

| Old Name | New Name | Purpose |
|----------|----------|---------|
| "Design Image" | "Pattern/Tile Image" | Single repeat of pattern |
| N/A | "Tiled Pattern" | Full-size pattern (tiled across fabric) |
| "Camera Image" | "Camera/Fabric Image" | Reference fabric photo |
| "Registered" | "Warped Result" | Final aligned output |

---

## 🔄 **Complete Processing Pipeline**

### **INPUTS**
```
1. Camera Image (fabric):   2000×1500 pixels (example)
   → Reference image with pattern repeats
   → May have wrinkles, distortions

2. Pattern Image (tile):    200×200 pixels (example)
   → Single repeat of the design
   → Will be tiled across fabric
```

---

### **STAGE 1: Pattern Tiling (5-10%)**
**Purpose:** Create full-size pattern matching fabric dimensions

```python
# In background worker thread
tiled_pattern = backend.align_and_tile_pattern(
    pattern_image,      # 200×200
    camera_image,       # 2000×1500
    use_smart_alignment=True
)
# Result: 2000×1500 tiled pattern
```

**What happens:**
- Feature matching detects rotation/scale/position
- Pattern repeated across full fabric size
- Saved: `output/tiled_pattern_fullres.png` (2000×1500)
- Layer added: "Tiled Pattern (before warp)"

**Key:** This is FULL RESOLUTION but not yet warped

---

### **STAGE 2: Downsampled Registration (10-90%)**
**Purpose:** Find deformation field at manageable resolution

```python
# Backend automatically downsamples if needed
max_dim = max(camera_image.shape)
if max_dim > 1024:
    # Downsample to ≤1024 for registration
    scale_factor = 1024 / max_dim
    camera_small = resize(camera_image, scale_factor)
    tiled_small = resize(tiled_pattern, scale_factor)
    
# Run Elastix B-spline registration
registered_small, deformation_field, metadata = elastix.register(
    fixed=camera_small,    # e.g., 1024×768
    moving=tiled_small     # e.g., 1024×768
)
# Result: deformation_field [1024, 768, 2]
```

**What happens:**
- Images downsampled to ≤1024px for speed
- B-spline registration finds deformation
- Deformation field at LOW resolution
- Time: ~30-60 seconds

**Key:** Registration is FAST because images are small

---

### **STAGE 3: Deformation Field Scaling**
**Purpose:** Scale deformation field to full resolution

```python
# Scale deformation field from registration resolution to full resolution
scale_x = full_width / reg_width     # e.g., 2000 / 1024 = 1.953
scale_y = full_height / reg_height   # e.g., 1500 / 768  = 1.953

# Resize deformation field
deformation_full = cv2.resize(
    deformation_field,               # [1024, 768, 2]
    (full_width, full_height),       # → [2000, 1500, 2]
    interpolation=cv2.INTER_LINEAR
)

# Scale displacement magnitudes
deformation_full[:, :, 0] *= scale_x  # X displacements
deformation_full[:, :, 1] *= scale_y  # Y displacements
```

**Key:** Deformation field properly scaled for high-res

---

### **STAGE 4: High-Resolution Warping (90-100%)**
**Purpose:** Apply deformation to full-resolution tiled pattern

```python
# Warp the FULL RESOLUTION tiled pattern
warped_result = warp_image(
    tiled_pattern_fullres,  # 2000×1500 (from Stage 1)
    deformation_full        # [2000, 1500, 2] (from Stage 3)
)
# Result: 2000×1500 warped pattern matching fabric
```

**What happens:**
- Uses full-resolution tiled pattern
- Applies scaled deformation field
- Result matches fabric distortions
- Time: ~10-30 seconds

**Key:** Final output is FULL RESOLUTION and WARPED

---

## 📁 **Files Created**

| Stage | File | Size | Purpose |
|-------|------|------|---------|
| 1 | `output/tiled_pattern_fullres.png` | 2000×1500 | Tiled pattern (FLAT) |
| 2 | (in memory) | 1024×768 | Downsampled for registration |
| 2 | `deformation_field.nii` | 1024×768×2 | Low-res deformation |
| 4 | `output/registered_result.png` | 2000×1500 | Final warped output |

---

## 🎨 **Layer Management**

### Layers in GUI (from bottom to top):
```
1. Camera (fabric)              - 2000×1500 preview - VISIBLE
2. Pattern (single repeat)      - 200×200 preview   - HIDDEN after tiling
3. Tiled Pattern (before warp)  - 2000×1500 preview - VISIBLE (Stage 1)
4. Registered (warped result)   - 2000×1500 preview - VISIBLE (Stage 4)
```

### Preview vs Full-Res:
- **Layers show PREVIEWS** (≤12MP for canvas responsiveness)
- **Registration uses DOWNSAMPLED** (≤1024px for speed)
- **Final warp uses FULL-RES** (original resolution for quality)

---

## ⚙️ **Resolution Strategy**

```
Pattern Image:        200×200       (original)
Camera Image:        2000×1500      (original)

↓ STAGE 1: TILING
Tiled Pattern:       2000×1500      (full-res, saved to disk)

↓ STAGE 2: REGISTRATION
Camera (downsampled): 1024×768      (in memory, for registration)
Tiled (downsampled):  1024×768      (in memory, for registration)
Deformation Field:    1024×768×2    (output)

↓ STAGE 3: SCALING
Deformation (scaled): 2000×1500×2   (in memory)

↓ STAGE 4: WARPING
Tiled Pattern:       2000×1500      (loaded from disk)
Warped Result:       2000×1500      (final output)
```

---

## 🔍 **Why This Architecture?**

### **Memory Efficiency**
- Registration on small images (1024px) = FAST
- Warping on full-res (2000px) = HIGH QUALITY
- Don't need full-res in memory during registration

### **Speed**
- Registration: ~30s on 1024px vs ~5min on 2000px
- Warping: ~15s (unavoidable, but worth it)

### **Quality**
- Deformation field captures coarse structure
- Full-res warping preserves fine details
- Best of both worlds

---

## ✅ **Verification Checklist**

After running registration:

- [ ] `output/tiled_pattern_fullres.png` exists (Stage 1)
- [ ] Size matches camera image
- [ ] Layer "Tiled Pattern" visible in GUI
- [ ] Log shows "→ B-spline registration on downsampled"
- [ ] Log shows "→ Deformation field scaled for high-res"
- [ ] `output/registered_result.png` exists (Stage 4)
- [ ] Result shows warped pattern matching fabric

---

## 🐛 **Common Issues**

### Issue: "Tiled pattern not created"
**Check:**
- Pattern tiling checkbox enabled?
- Log shows "Creating full pattern-filled image"?
- `output/tiled_pattern_fullres.png` file exists?

### Issue: "Result is low resolution"
**Check:**
- Are you looking at layer preview (normal) or exported file?
- Check file size of `output/registered_result.png`
- Should match camera image dimensions

### Issue: "Pattern not aligned"
**Check:**
- Smart alignment enabled?
- Log shows "Found transform: X inliers"?
- Try different preprocessing options

---

## 🎯 **What You Should See in GUI**

### Progress Log:
```
[0%]  Starting registration...
[5%]  🔲 Creating full pattern-filled image (smart alignment)...
[8%]  ✓ Pattern-filled image ready: 2000×1500
[8%]  📐 TILED PATTERN created (full-size, BEFORE B-spline warping)
[8%]  ✓ Saved full-res tiled pattern: output/tiled_pattern_fullres.png
[9%]  → Next: B-spline registration on downsampled version
[9%]  → Then: Deformation field will be scaled for high-res warping
[30%] Running registration algorithm...
[90%] Warping high-resolution image...
[100%] Registration complete!
```

### File Output:
```
output/
  ├── tiled_pattern_fullres.png       (Stage 1: 2000×1500)
  ├── deformationField.mhd/.raw       (Stage 2: 1024×768×2)
  └── registered_result.png           (Stage 4: 2000×1500)
```

---

## 📖 **Summary**

**OLD (Broken):**
- Registration on full-res = SLOW
- Pattern not tiled properly
- Confusing layer names

**NEW (Fixed):**
1. ✅ Tile pattern at FULL resolution
2. ✅ Register on DOWNSAMPLED version (fast)
3. ✅ Scale deformation field
4. ✅ Warp at FULL resolution (quality)
5. ✅ Clear naming: Pattern → Tiled → Warped

**Result:** Fast + High Quality + Clear workflow!
