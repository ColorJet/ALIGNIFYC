# Tiling Pattern Designer - Implementation Specification

## Overview
CAD-style pattern tiling editor for fabric registration system, similar to Autodesk Inventor's pattern command.

## Architecture

### 1. Dialog Structure
**File:** `gui/widgets/tiling_pattern_editor.py`

```
TilingPatternEditorDialog (QDialog)
├── Preview Canvas (left panel)
│   ├── Background layer (camera image or blank)
│   ├── Pattern tiles with 50% opacity
│   └── Grid overlay
├── Control Panel (right panel)
│   ├── Background Selection
│   │   ├── Use Camera Image
│   │   └── Use Blank Background (white/gray)
│   ├── Pattern Tile
│   │   ├── Load Tile Button
│   │   ├── Size (W x H) spinboxes
│   │   └── Opacity slider (0-100%)
│   ├── Tiling Mode
│   │   ├── Manual Placement (drag & drop)
│   │   └── Grid Pattern (auto)
│   ├── Grid Parameters (if Grid Pattern)
│   │   ├── Pitch X / Gap X (optional)
│   │   ├── Pitch Y / Gap Y (optional)
│   │   ├── Columns / Rows spinboxes
│   ├── Jog Controls (if Manual Placement)
│   │   ├── [X+] [X-] [Y+] [Y-] buttons with step size
│   │   └── Current position display
│   └── Actions
│       ├── Preview Pattern (render full tiling)
│       ├── Save Design File (.svg, .png, .npz)
│       └── Send to Registration Pipeline
```

### 2. Integration Points

#### A. Menu System
Add to **File Menu** (after "Load Design Image"):
```python
load_pattern_designer = QAction('Open Pattern &Designer...', self)
load_pattern_designer.setShortcut('Ctrl+Shift+D')
load_pattern_designer.triggered.connect(self.openPatternDesigner)
file_menu.addAction(load_pattern_designer)
```

#### B. Layer Panel Integration
```python
# Pattern designer output becomes a design layer
def onPatternDesignComplete(self, pattern_image, metadata):
    """Handle completed pattern from designer"""
    self.design_image = pattern_image
    self.tiled_pattern_image = pattern_image  # Mark as pre-tiled
    
    # Add to layer canvas
    preview = self._create_preview_image(pattern_image)
    self.layer_canvas.addImageLayer("Pattern Design", preview, "Normal", 0.5, True)
    
    # Store metadata (pitch, gap, original tile, etc.)
    self.pattern_metadata = metadata
    
    self.log(f"✅ Pattern design loaded: {pattern_image.shape}")
```

#### C. Registration Pipeline
```python
# In registerImages()
if hasattr(self, 'tiled_pattern_image') and self.tiled_pattern_image is not None:
    # Use pre-tiled pattern from designer
    moving_rgb = self.tiled_pattern_image
    self.log("🔲 Using pre-designed pattern from Pattern Designer")
else:
    # Use existing tiling logic
    ...
```

### 3. Vector Format Support

#### Dependencies
```bash
pip install svglib reportlab cairosvg
```

#### Implementation
```python
def loadVectorDesign(self, filename):
    """Load SVG/PDF vector design and rasterize"""
    import svglib.svglib as svglib
    from reportlab.graphics import renderPM
    
    ext = Path(filename).suffix.lower()
    
    if ext == '.svg':
        # Load SVG
        drawing = svglib.renderSVG(filename)
        
        # Rasterize at high DPI (300 for print quality)
        dpi = 300
        img_data = renderPM.drawToString(drawing, fmt='PNG', dpi=dpi)
        
        # Convert to numpy array
        from io import BytesIO
        img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        return img_rgb
    
    elif ext == '.pdf':
        # Similar approach using pdf2image or cairosvg
        pass
```

### 4. Multimodality Handling

**Already solved in your code!**

Your existing preprocessing pipeline handles this:
- Grayscale camera: `combo_fixed_preproc` with "CLAHE", "Histogram Equalization"
- Color design tiles: `combo_moving_preproc` with "Edge Enhance", "Normalize"

The pattern designer just needs to output the final tiled design - registration backend handles the rest.

### 5. Design File Format

**Option 1: NPZ (Recommended for large images)**
```python
np.savez_compressed(
    'pattern_design.npz',
    image=tiled_pattern,
    tile_size=(width, height),
    pitch=(pitch_x, pitch_y),
    gap=(gap_x, gap_y),
    grid_size=(cols, rows),
    background_type='camera'  # or 'blank'
)
```

**Option 2: PNG + JSON metadata**
```python
cv2.imwrite('pattern_design.png', tiled_pattern)
json.dump(metadata, open('pattern_design.json', 'w'))
```

**Option 3: SVG (Vector - scales infinitely)**
```python
# Save as SVG with repeated tile instances
# Each tile is a <use> reference to master <symbol>
```

## UI Mockup (ASCII)

```
┌─────────────────────────────────────────────────────────┐
│ Pattern Designer                            [_][□][X]    │
├─────────────────────────┬───────────────────────────────┤
│                         │ Background                     │
│                         │ ◉ Camera Image                 │
│                         │ ○ Blank (Color: [___])         │
│   Preview Canvas        │                                │
│   (Tile with 50%        │ Pattern Tile                   │
│    opacity on           │ Load: [Choose File...]         │
│    background)          │ Size: W[___] H[___] px         │
│                         │ Opacity: [====|====] 50%       │
│                         │                                │
│                         │ Tiling Mode                    │
│                         │ ○ Manual Placement             │
│                         │ ◉ Grid Pattern                 │
│                         │                                │
│                         │ Grid Settings                  │
│                         │ Pitch X: [___] Gap X: [___]    │
│                         │ Pitch Y: [___] Gap Y: [___]    │
│                         │ Cols: [5] Rows: [3]            │
│                         │                                │
│                         │ Jog Controls (Manual Mode)     │
│                         │   [↑ Y+]                       │
│                         │ [← X-] [→ X+]  Step:[__] px    │
│                         │   [↓ Y-]                       │
│                         │ Position: (123, 456)           │
│                         │                                │
│                         │ [Preview Pattern]              │
│                         │ [Save Design File...]          │
│                         │ [Send to Registration]         │
└─────────────────────────┴───────────────────────────────┘
```

## Implementation Steps

### Phase 1: Basic Dialog (2-3 hours)
1. Create `TilingPatternEditorDialog` class
2. Add preview canvas with background selection
3. Tile loading and opacity control
4. Grid pattern generation (simple XY repeat)

### Phase 2: Advanced Controls (2-3 hours)
5. Manual placement with drag & drop
6. Arrow jog controls (X+/X-/Y+/Y-)
7. Pitch/gap parameters
8. Real-time preview updates

### Phase 3: Integration (1-2 hours)
9. Menu integration
10. Save/load design files
11. Connect to registration pipeline
12. Testing with camera images

### Phase 4: Vector Support (1-2 hours)
13. Add SVG/PDF loading
14. Rasterization at correct DPI
15. Vector metadata preservation

## Testing Scenarios

1. **Grayscale camera + Color design tile**
   - Load grayscale camera image as background
   - Load color design tile
   - Generate 5x3 grid pattern
   - Save and register

2. **Blank background + Manual placement**
   - Use white background
   - Manually place 3 tiles with jog controls
   - Adjust pitch/gap interactively
   - Export as SVG

3. **Vector workflow**
   - Load SVG tile design
   - Generate pattern at 300 DPI
   - Register with camera image
   - Warp to fabric

## Benefits

✅ **CAD-style workflow** - Familiar to textile designers  
✅ **No coding required** - GUI-only pattern creation  
✅ **Multimodal support** - Already handled by preprocessing  
✅ **Vector scalability** - SVG tiles can be scaled infinitely  
✅ **Integration** - Works with existing registration pipeline  
✅ **Preview before registration** - Save time and iterations  

## Conclusion

**Your requirements are 100% feasible** with your existing architecture. The main work is:

1. **TilingPatternEditorDialog** - New UI widget (~400 lines)
2. **Menu integration** - One function call
3. **Vector support** - Add library dependencies (~100 lines)
4. **Theme toggle** - Duplicate existing theme function (~200 lines)

**Estimated time:** 8-10 hours for complete implementation.

Would you like me to start implementing these features?
