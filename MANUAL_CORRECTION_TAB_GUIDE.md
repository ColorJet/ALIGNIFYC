# Manual Correction Tab - Integrated Workflow

## Overview
The Manual Correction feature is now **fully integrated into the main GUI** as a dedicated tab, not a separate dialog. This allows operators to review registration results and make precise corrections before applying the deformation field to the full-resolution image.

---

## 🎨 Visual Design

### Tab Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ 🔵 Blue points = Camera layer │ 🔴 Red points = Registered layer│
│ Click on image to add │ Drag any point to adjust correction      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│               BLENDED OVERLAY VISUALIZATION                      │
│         (50% Camera + 50% Registered Preview)                    │
│                                                                  │
│     🔵 Blue Point        🔴 Red Point                           │
│        (Camera)          (Registered)                            │
│           ●─────────────────●                                   │
│            \               /                                     │
│             Offset = dx, dy                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Control Points Table:
┌─────┬─────┬──────────┬──────────┐
│  X  │  Y  │ Offset X │ Offset Y │
├─────┼─────┼──────────┼──────────┤
│ 100 │ 150 │   25.0   │   -10.5  │  ← Camera (100,150), Registered (125,139.5)
│ 200 │ 250 │   -15.3  │    5.2   │
│ 300 │ 350 │    8.1   │   12.7   │
└─────┴─────┴──────────┴──────────┘

[Add Control Point] [Remove Selected] [Clear All]     Points: 3

                    [Apply Manual Correction]
```

---

## 🔧 How It Works

### 1. **Registration Checkbox**
In the **Registration tab → Advanced Options**:
```
☑ Stop before high-res warp for manual correction
```

**When CHECKED:**
- Registration runs on downsampled preview (~2000px)
- Results shown in Manual Correction tab
- Operator can add/adjust control points
- Click "Apply" → scales deformation field → warps full-resolution image

**When UNCHECKED:**
- Registration proceeds directly to full-resolution warp (old behavior)
- No manual correction step

---

### 2. **Manual Correction Tab Components**

#### **Overlay Visualization**
- Shows **50/50 blend** of camera (fixed) and registered (warped) images
- Both layers visible simultaneously
- Click anywhere to add control point pair

#### **Control Point Markers**
- **Blue Point (🔵)**: Position in camera/fixed layer
- **Red Point (🔴)**: Position in registered/warped layer
- **Both created together** when you click on image
- **Drag either point** to adjust correction

#### **Corrections Table**
- **X, Y**: Camera layer position (where you clicked)
- **Offset X, Offset Y**: Correction to apply = (Red pos - Blue pos)

Example:
```
Camera Blue Point at (100, 150)
Registered Red Point at (125, 140)
→ Offset X = 25, Offset Y = -10
→ Means: "At position (100,150), shift by (+25, -10) to align"
```

---

## 🎯 Operator Workflow

### Step-by-Step

1. **Configure Registration**
   ```
   Registration tab:
   - Set parameters (grid spacing, iterations, etc.)
   - ☑ Check "Stop before high-res warp for manual correction"
   - Click "Register"
   ```

2. **Registration Runs**
   ```
   Background registration on preview image...
   Progress: 25%... 50%... 75%... 100%
   ✓ Registration complete
   ```

3. **Manual Correction Tab Opens Automatically**
   ```
   Dialog appears:
   "Registration preview is ready!
    
    ➡️ Switch to the 'Manual Correction' tab to:
      • View camera (blue) and registered (red) layers
      • Add control points by clicking on the image
      • Drag points to adjust alignment
      • Click 'Apply Manual Correction' when done"
   ```

4. **Review Overlay**
   - Check blended visualization
   - Look for misalignment areas
   - Decide if corrections needed

5. **Add Control Points** (if needed)
   - Click "Add Control Point" button (or just click on image)
   - **Click on misaligned area**
   - Two markers appear: Blue (camera) + Red (registered)
   - Both start at same position (no offset initially)

6. **Adjust Corrections**
   - **Drag Blue point** → adjusts camera reference position
   - **Drag Red point** → adjusts registered position
   - **Table updates in real-time** showing X, Y, Offset X, Offset Y
   - Add multiple points for different misalignment areas

7. **Apply Corrections**
   - Click "Apply Manual Correction"
   - Corrections sent to backend
   - Deformation field scaled to full resolution
   - High-res warp applied with corrections

---

## 📊 Example Scenario

### Scenario: Fabric has local distortion at position (500, 300)

1. **Registration completes**, shows in Manual Correction tab
2. **Operator sees misalignment** in blended view around (500, 300)
3. **Click at (500, 300)**
   - Blue point appears at (500, 300) on camera layer
   - Red point appears at (500, 300) on registered layer
   - Table shows: `500 | 300 | 0.0 | 0.0`

4. **Operator drags RED point** to (485, 310) to align fabric pattern
   - Blue stays at (500, 300)
   - Red moves to (485, 310)
   - Table updates: `500 | 300 | -15.0 | 10.0`

5. **Offset interpretation:**
   ```
   At camera position (500, 300):
   Registered layer is shifted by (-15, +10)
   Correction needed: shift by (-15, +10) to align
   ```

6. **Click "Apply Manual Correction"**
   - Backend receives: `[(500, 300, -15.0, 10.0)]`
   - Gaussian-weighted correction blended into deformation field
   - Deformation field scaled to full-resolution
   - Final warp applied

---

## 🔢 Mathematical Details

### Correction Calculation
```python
# User clicks at (x, y)
camera_x, camera_y = click_position

# Creates markers
blue_marker.pos = (camera_x, camera_y)
red_marker.pos = (camera_x, camera_y)  # Initially same

# User drags red marker to (new_x, new_y)
registered_x, registered_y = drag_position

# Calculate offset
offset_x = registered_x - camera_x
offset_y = registered_y - camera_y

# Table shows
table.add_row(camera_x, camera_y, offset_x, offset_y)

# Correction tuple
correction = (camera_x, camera_y, offset_x, offset_y)
```

### Application to Deformation Field
```python
# Backend applies Gaussian-weighted correction
for (x, y, dx, dy) in corrections:
    # Gaussian weight (σ = 3 × control point radius)
    weight = exp(-distance² / (2 × σ²))
    
    # Blend with existing deformation
    deformation[y, x, 0] += weight × dx
    deformation[y, x, 1] += weight × dy
```

### Scaling to Full Resolution
```python
# Preview image: 2000 × 1500
# Full-res image: 16000 × 12000
# Scale factor: 8.0

# Scale control point positions
full_res_x = camera_x × 8.0
full_res_y = camera_y × 8.0

# Offsets scale proportionally
full_res_dx = offset_x × 8.0
full_res_dy = offset_y × 8.0

# Apply to full-res deformation field
full_res_correction = (full_res_x, full_res_y, full_res_dx, full_res_dy)
```

---

## 🎛️ Controls Reference

### Buttons

| Button | Action |
|--------|--------|
| **Add Control Point** | Enables click-to-add mode (cursor becomes crosshair) |
| **Remove Selected** | Deletes selected row from table + markers from view |
| **Clear All** | Removes all control points (asks for confirmation) |
| **Apply Manual Correction** | Commits corrections and proceeds to high-res warp |

### Interactions

| Action | Result |
|--------|--------|
| **Click on image** | Adds blue + red marker pair at click position |
| **Drag blue marker** | Updates camera reference position, recalculates offset |
| **Drag red marker** | Updates registered position, recalculates offset |
| **Select table row** | Highlights corresponding markers (future) |
| **Double-click table** | Zooms to control point (future) |

---

## 📝 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     REGISTRATION                             │
│  1. Load camera + design images                              │
│  2. Downsample to preview size (~2000px)                     │
│  3. Run Elastix registration → deformation field             │
│  4. Warp preview image                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
    ☑ Stop before high-res warp? ────No────> Proceed to full-res warp
                           │
                           Yes
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              MANUAL CORRECTION TAB                           │
│  1. Display camera + registered preview (blended)            │
│  2. Operator adds control points                             │
│  3. Operator drags points to adjust                          │
│  4. Table shows X, Y, Offset X, Offset Y                     │
│  5. Click "Apply Manual Correction"                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          APPLY CORRECTIONS TO DEFORMATION FIELD              │
│  1. Gaussian-weighted blending of corrections                │
│  2. Scale deformation field to full resolution               │
│  3. Apply to original large image                            │
│  4. Send to printer                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Advantages of Integrated Tab

### vs. Separate Dialog

| Aspect | Dialog | Integrated Tab |
|--------|--------|----------------|
| **Workflow** | Interrupts flow | Smooth transition |
| **Context** | Loses main GUI | Keeps all info visible |
| **Flexibility** | Must complete | Can switch tabs, return later |
| **Multi-tasking** | Blocks GUI | Non-blocking |
| **UI Space** | Limited | Full tab area |

### Key Benefits

✅ **No blocking**: Operator can check log, adjust parameters, etc.  
✅ **Persistent**: Tab stays available, can return to it  
✅ **Integrated**: Part of main workflow, not separate step  
✅ **Visible**: Always see if corrections pending  
✅ **Flexible**: Enable/disable with simple checkbox  

---

## 🧪 Testing

### Test Script
```bash
D:\Alinify\venv\Scripts\python.exe python\test_manual_correction_tab.py
```

**Tests:**
1. ✅ Tab initialization
2. ✅ Image display (blended overlay)
3. ✅ Control point creation
4. ✅ Table synchronization
5. ✅ Movement tracking
6. ✅ Clear functionality

---

## 📂 Files Modified/Created

### Created
- `gui/widgets/manual_correction_tab.py` (420 lines)
  - ManualCorrectionTab widget
  - ControlPointMarker class
  - Table management
  - Signal: correctionsApplied

### Modified
- `gui/main_gui.py`
  - Import ManualCorrectionTab
  - Add checkbox: "Stop before high-res warp"
  - Replace createManualControls() with tab instance
  - Update onRegistrationFinished() to populate tab
  - Add onManualCorrectionsApplied() callback

---

## 🎓 Training Notes

### For Operators

**Quick Start:**
1. Check "Stop before high-res warp" box
2. Run registration
3. When tab opens, review overlay
4. Click where misalignment exists
5. Drag red point to align
6. Click "Apply"

**Tips:**
- Blue = where correction applies (camera position)
- Red = what correction does (shift amount)
- 5-10 strategic points usually sufficient
- Can skip corrections by not adding points

### For Developers

**Integration:**
```python
# In main_gui.py
self.manual_correction_tab = ManualCorrectionTab()
self.manual_correction_tab.correctionsApplied.connect(self.onManualCorrectionsApplied)

# After registration
self.manual_correction_tab.setImages(fixed_img, warped_img)

# Get corrections
corrections = self.manual_correction_tab.getCorrections()
# Returns: [(x, y, dx, dy), ...]
```

---

## 🔮 Future Enhancements

- [ ] Zoom/pan controls for pixel-level precision
- [ ] Difference mode toggle (like previous implementation)
- [ ] Auto-suggest correction points (ML-based)
- [ ] Undo/redo stack
- [ ] Save/load correction presets
- [ ] Click table row → highlight markers
- [ ] Drag markers with constraints (grid snap, etc.)
- [ ] Show correction magnitude as color (small = green, large = red)
- [ ] Export correction report (CSV)

---

## ✅ Summary

The Manual Correction feature is now a **first-class citizen** of the GUI:
- **Integrated tab** (not dialog)
- **Blue + Red dual markers** showing camera and registered positions
- **Real-time table** synchronization
- **Optional workflow** via checkbox
- **Non-blocking** operation
- **Ready for production use**

The operator experience is now **streamlined and professional**, similar to quality control workflows in industrial printing systems.
