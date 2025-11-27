# Manual Deformation Correction Guide

## Overview
The enhanced manual deformation editor provides powerful visualization and editing tools to precisely correct fabric registration misalignments.

---

## 🎨 Key Features

### 1. **Bypass Option**
- **Checkbox**: "⏭️ Bypass Manual Correction (skip this step)"
- **Purpose**: Quickly skip manual editing when registration is already good
- **Behavior**: 
  - When checked, all controls are disabled
  - Clicking "Done" returns empty corrections list
  - Registration proceeds directly to high-res warping

---

### 2. **Overlay Visualization Modes**
Shows where corrections are needed by comparing fixed and warped images:

#### **Blend (Overlay)** - Default
- Overlays fixed and warped images with adjustable transparency
- **Use when**: You want to see both images simultaneously
- **Blend slider**: Adjusts mix ratio (0% = all warped, 100% = all fixed)

#### **Difference (Shows Errors)** ⭐ RECOMMENDED
- Displays absolute difference between images
- **Bright areas = misalignment** that needs correction
- **Dark areas = good alignment**
- **Use when**: Finding exact locations needing control points
- Enhanced contrast automatically applied for visibility

#### **Checkerboard**
- Alternates between fixed and warped in 64px tiles
- **Use when**: Checking alignment at boundaries
- Makes edge discontinuities very visible

#### **Warped Only**
- Shows only the registered (warped) image
- **Use when**: Inspecting warped image quality

#### **Fixed Only**
- Shows only the original camera/fixed image
- **Use when**: Reference comparison

---

### 3. **Image Adjustments for Precise Marking**

#### **Invert Checkbox**
- Inverts image colors (black ↔ white)
- **Use when**: 
  - Dark fabric on dark background makes control points hard to see
  - Need to highlight specific features that are subtle in normal view

#### **Contrast Slider** (0.5x - 3.0x)
- Increases or decreases contrast
- **High contrast (2.0x - 3.0x)**:
  - Makes small misalignments more visible
  - Useful for finding subtle weave pattern shifts
- **Low contrast (0.5x)**:
  - Reduces noise for cleaner view

#### **Brightness Slider** (-100 to +100)
- Adjusts overall brightness
- **Increase brightness**: See details in dark fabric regions
- **Decrease brightness**: Reduce glare in bright areas

#### **Reset Button**
- Instantly returns all adjustments to defaults
- Invert: OFF, Contrast: 1.0x, Brightness: 0

---

## 🎯 Workflow for Manual Correction

### Step 1: Check if Correction is Needed
1. Open manual editor after registration
2. **Switch to "Difference" mode** - this clearly shows errors
3. Look for bright areas (misalignment)
4. If entire image is dark → registration is good → **Check "Bypass"** → Click "Done"

### Step 2: Adjust View for Precision
1. If bright areas exist, adjust image for better visibility:
   - Increase **Contrast** to 2.0x-2.5x
   - Adjust **Brightness** if needed
   - Try **Invert** if control points blend with background
2. Switch between modes:
   - **Difference**: Find error locations
   - **Blend**: See how fixed and warped align
   - **Checkerboard**: Verify edges

### Step 3: Mark Control Points
#### Option A: Manual Placement
1. **Click** on misaligned areas to add control points
2. Points appear as **red circles with white outline**
3. **Drag** points to correct alignment:
   - Original position = where you clicked
   - Current position = where you drag to
   - Correction vector = displacement applied to deformation field

#### Option B: Auto Grid
1. Set **Spacing** (20-200 px) - distance between points
2. Click **"🔲 Auto Grid"**
3. Points placed automatically across entire image
4. **Drag individual points** to fine-tune

### Step 4: Refine Corrections
- **Undo**: Remove last added point
- **Clear All**: Start over
- **Preview**: See effect of corrections (if implemented)
- Point counter shows total number of corrections

### Step 5: Apply or Cancel
- **✅ Done**: Apply corrections and proceed to high-res warping
- **❌ Cancel**: Discard corrections and return to GUI

---

## 💡 Pro Tips

### Finding Problem Areas
1. **Start with Difference mode** - bright = problems
2. **Increase contrast to 2.5x** - makes subtle errors obvious
3. Look for patterns:
   - Bright horizontal/vertical lines = systematic shift
   - Bright patches = local distortion
   - Edge brightness = boundary misalignment

### Marking Control Points Efficiently
1. **Few strategic points > many random points**
   - 5-10 well-placed points often better than 50 random ones
2. **Place points at misaligned features**:
   - Thread intersections in fabric weave
   - Pattern boundaries
   - Color transitions
3. **Avoid edges** - registration usually good at boundaries
4. **For large errors**: Place points in a small grid around the problem area

### Using Different Modes Together
1. **Difference** → Find where to add points
2. **Blend (50%)** → See both images while dragging points
3. **Checkerboard** → Verify alignment after corrections
4. **Switch back to Difference** → Confirm bright areas are reduced

### Adjustment Strategy
- **High-contrast fabric**: Contrast 1.5x-2.0x, minimal brightness
- **Low-contrast fabric**: Contrast 2.5x-3.0x, adjust brightness ±30
- **Dark fabric**: Invert ON, Contrast 2.0x, Brightness +50
- **Bright fabric**: Contrast 1.5x, Brightness -30

---

## 🔧 Technical Details

### How Corrections are Applied
1. Control point corrections stored as `[(x, y, dx, dy), ...]`
   - `(x, y)` = original position where you clicked
   - `(dx, dy)` = how far you dragged the point
2. During high-res warping:
   - Gaussian weighting applied (σ = 3× control point size)
   - Corrections blend smoothly with deformation field
   - Closer to control point = stronger correction
   - Far from control point = original deformation

### Overlay Processing
- **Blend**: `cv2.addWeighted(fixed, alpha, warped, 1-alpha, 0)`
- **Difference**: `cv2.absdiff(fixed, warped)` + normalization
- **Checkerboard**: 64px tiles alternating between images
- **Adjustments**: Applied after overlay generation
  - Contrast: `image * contrast_factor`
  - Brightness: `image + brightness_offset`
  - Invert: `255 - image`

### Performance
- Preview images downsampled to ~2000px max dimension
- Real-time adjustment updates (<50ms)
- Control point dragging updates instantly
- Full corrections applied only during high-res warp

---

## ⚡ Keyboard Shortcuts (Future)
- `Space`: Toggle between Blend and Difference
- `I`: Toggle Invert
- `Ctrl+Z`: Undo last point
- `Del`: Remove selected point
- `Escape`: Cancel dialog
- `Enter`: Apply corrections

---

## 🐛 Troubleshooting

### "Image appears too dark/bright"
→ Adjust **Brightness slider** or try **Invert**

### "Can't see misalignment clearly"
→ Switch to **Difference mode** and increase **Contrast to 2.5x**

### "Control points not visible"
→ Points are red circles with white outline - they may blend with fabric color. Try **Invert** or adjust **Contrast**

### "Dragged point, but no effect"
→ Corrections applied during high-res warp, not in preview. Check point counter shows your corrections.

### "Registration already good"
→ Check **"Bypass Manual Correction"** and click **Done** to skip

---

## 📊 Example Workflows

### Workflow 1: Quick Check (No Corrections Needed)
1. Open editor → Difference mode
2. Image mostly dark (good alignment)
3. Check "Bypass Manual Correction"
4. Click "Done"
⏱️ **Time**: 5 seconds

### Workflow 2: Minor Local Correction
1. Open editor → Difference mode
2. See small bright patch at position (X, Y)
3. Increase contrast to 2.0x
4. Click on bright patch center to add control point
5. Drag point ~10-20 pixels to align
6. Switch to Blend mode → verify alignment looks better
7. Click "Done"
⏱️ **Time**: 30 seconds, 1 control point

### Workflow 3: Systematic Shift Correction
1. Open editor → Difference mode
2. See horizontal bright line across image (systematic Y-shift)
3. Contrast 2.5x
4. Set spacing to 100px
5. Click "Auto Grid"
6. Drag points along bright line upward/downward to fix shift
7. Preview → Checkerboard → verify
8. Click "Done"
⏱️ **Time**: 2 minutes, 20-30 control points

### Workflow 4: Complex Local Distortion
1. Open editor → Difference mode
2. Large bright irregular region
3. Contrast 3.0x, Brightness +20
4. Manually place 5-7 points around distorted region boundary
5. Drag each point to align local fabric features
6. Switch to Blend 30% (more warped visible) while dragging
7. Return to Difference → confirm brightness reduced
8. Click "Done"
⏱️ **Time**: 3-5 minutes, 5-7 control points

---

## 🎓 Best Practices Summary

✅ **DO**:
- Start with Difference mode to find problems
- Use high contrast (2.0x-3.0x) for precision
- Place strategic points at misaligned features
- Test different overlay modes during editing
- Use Bypass when registration is already good

❌ **DON'T**:
- Don't add points randomly hoping for improvement
- Don't place control points too close together (<20px)
- Don't use low contrast when marking points
- Don't forget to check Difference mode after corrections
- Don't spend time correcting if Difference shows mostly dark (good alignment)

---

## 🚀 Future Enhancements
- [ ] Keyboard shortcuts
- [ ] Zoom controls for pixel-level precision
- [ ] Multi-layer undo/redo stack
- [ ] Save/load correction presets
- [ ] Automated error detection (auto-suggest control point locations)
- [ ] Side-by-side before/after comparison
- [ ] Export correction report (positions, magnitudes)
