# Manual Correction Workflow - Redesigned Architecture

## Overview
Complete redesign of manual correction system based on flexible red/blue point clicking workflow.

## Key Design Principles

### 1. Canvas-Based Control Points
- **Main canvas is used** - no separate graphics view in Manual Correction tab
- Control points displayed as overlays on main canvas
- Leverages existing zoom/pan/scroll functionality
- Red dots = control points (reference positions)
- Blue dots = offset points (target positions)

### 2. Flexible Clicking Order
- **User can click in any order** - red first, blue first, or mixed
- Mouse buttons determine point type:
  - **Left-click** → Add RED control point
  - **Right-click** → Add BLUE offset point
- Examples:
  - 1 red, 2 blue, 2 red → valid
  - All reds first, then all blues → valid
  - Alternating red-blue-red-blue → valid

### 3. Sequence-Based Pairing
- Points paired by sequence order (not spatial proximity)
- **1st red + 1st blue = Pair A**
- **2nd red + 2nd blue = Pair B**
- **3rd red + 3rd blue = Pair C**
- etc.
- Labels: A, B, C ... Z, AA, AB, AC ...

### 4. Offset Calculation
```
Offset X = Blue X - Red X
Offset Y = Blue Y - Red Y
```

### 5. Simplified Tab
Manual Correction tab contains ONLY:
- Mode selection buttons (🔴 Add Red Points / 🔵 Add Blue Points)
- Table showing: Label, Red X, Red Y, Blue X, Blue Y, Offset X, Offset Y
- Control buttons: Remove Selected, Clear All, Apply Manual Corrections
- Status/instruction text
- **NO graphics view** - canvas is in main area

## Architecture

### Components

#### 1. ManualCorrectionTab (`gui/widgets/manual_correction_tab.py`)
**Pure data management** - no visualization
- Tracks red_points list: [(x, y), (x, y), ...]
- Tracks blue_points list: [(x, y), (x, y), ...]
- Emits signals:
  - `modeChanged(mode)` - "red", "blue", or "none"
  - `correctionsApplied(corrections)` - [(red_x, red_y, blue_x, blue_y), ...]
- Methods:
  - `addRedPoint(x, y)` - Returns index
  - `addBluePoint(x, y)` - Returns index
  - `getLabel(index)` - Generates A, B, C... label
  - `updateTable()` - Rebuilds table from point lists

#### 2. ImageCanvas (`gui/widgets/canvas_widget.py`)
**Canvas with control point overlay**
- Mode: "red", "blue", or "none"
- Storage:
  - `red_markers`: [(x, y, label), ...]
  - `blue_markers`: [(x, y, label), ...]
- Mouse handling:
  - Left-click in "red" mode → emit `controlPointAdded("red", x, y)`
  - Right-click in "blue" mode → emit `controlPointAdded("blue", x, y)`
- Drawing:
  - `drawControlPointMarkers()` - Overlays red/blue circles with labels
- Methods:
  - `setControlPointMode(mode)` - Set "red", "blue", "none"
  - `addRedMarker(x, y, label)` - Add visual marker
  - `addBlueMarker(x, y, label)` - Add visual marker
  - `clearMarkers()` - Remove all markers
  - `screenToImageCoords(screen_x, screen_y)` - Convert to image coordinates

#### 3. MainGUI (`gui/main_gui.py`)
**Coordinator between tab and canvas**
- Connects signals:
  - `manual_correction_tab.modeChanged` → `onControlPointModeChanged()`
  - `canvas.controlPointAdded` → `onCanvasControlPointAdded()`
  - `manual_correction_tab.correctionsApplied` → `onManualCorrectionsApplied()`
- Handlers:
  - `onControlPointModeChanged(mode)`:
    - Update canvas mode
    - Update status bar
  - `onCanvasControlPointAdded(mode, x, y)`:
    - Add point to tab's data (get label)
    - Add marker to canvas with label
  - `onManualCorrectionsApplied(corrections)`:
    - Store in registration backend
    - Trigger high-res warp with corrections

## Workflow

### User Workflow
1. **Load images and run registration** with "Stop before high-res warp" checked
2. **Registration completes** - preview warped image shown in layer canvas
3. **Switch to Manual Correction tab**
4. **Click mode button**: 🔴 Add Red Points or 🔵 Add Blue Points
5. **Click on canvas**:
   - In red mode: left-click adds red control point
   - In blue mode: right-click adds blue offset point
6. **Points appear as dots** with labels (A, B, C...) on canvas
7. **Table updates** showing all points and calculated offsets
8. **Toggle modes** as needed - click red, then blue, then more reds, etc.
9. **Click "Apply Manual Corrections"** when done
10. **High-res warp proceeds** with corrected deformation field

### Technical Flow
```
User clicks mode button
  ↓
Tab emits modeChanged("red") or modeChanged("blue")
  ↓
MainGUI.onControlPointModeChanged() calls canvas.setControlPointMode()
  ↓
Canvas changes cursor to crosshair
  ↓
User clicks on canvas (left for red, right for blue)
  ↓
Canvas.mousePressEvent() converts screen → image coords
  ↓
Canvas emits controlPointAdded("red"|"blue", x, y)
  ↓
MainGUI.onCanvasControlPointAdded() receives event
  ↓
MainGUI calls tab.addRedPoint() or tab.addBluePoint()
  ↓
Tab adds to red_points or blue_points list, returns index
  ↓
Tab calls updateTable() to rebuild display
  ↓
MainGUI gets label from tab.getLabel(index)
  ↓
MainGUI calls canvas.addRedMarker() or canvas.addBlueMarker()
  ↓
Canvas stores marker and triggers repaint
  ↓
Canvas.drawControlPointMarkers() draws red/blue circles with labels
```

## Table Format
| Label | Red X  | Red Y  | Blue X | Blue Y | Offset X | Offset Y |
|-------|--------|--------|--------|--------|----------|----------|
| A     | 100.5  | 200.3  | 102.1  | 198.7  | +1.6     | -1.6     |
| B     | 450.2  | 180.9  | —      | —      | —        | —        |
| C     | —      | —      | 451.0  | 181.5  | —        | —        |

- Incomplete pairs highlighted in yellow
- Only complete pairs (both red and blue) used when applying corrections

## Advantages

### 1. Flexibility
- User decides order - no forced workflow
- Can add all reds first (easier to spot), then all blues
- Or alternate for immediate visual feedback
- Or mixed based on what's visible

### 2. Canvas Integration
- Uses existing zoom/pan tools
- No switching between views
- Markers scale with zoom
- Natural workflow

### 3. Simple Tab
- Just data table and controls
- No complex graphics view
- Clear status feedback
- Easy to understand

### 4. Sequence-Based
- No ambiguity about pairing
- Clear labels (A, B, C...)
- Table shows exactly what will be applied
- Easy to remove/modify specific pairs

## Implementation Files

### Modified Files
1. **`gui/widgets/manual_correction_tab.py`** (277 lines)
   - Removed QGraphicsView and layer controls
   - Added red_points and blue_points lists
   - Added mode toggle buttons
   - Simple 7-column table
   - Signal: modeChanged, correctionsApplied

2. **`gui/widgets/canvas_widget.py`** (485 lines)
   - Added control_point_mode field
   - Added red_markers and blue_markers lists
   - Modified mousePressEvent for left/right click detection
   - Added drawControlPointMarkers() in paintEvent
   - Signal: controlPointAdded
   - Methods: setControlPointMode, addRedMarker, addBlueMarker, clearMarkers

3. **`gui/main_gui.py`** (2016 lines)
   - Connected manual_correction_tab.modeChanged signal
   - Connected canvas.controlPointAdded signal
   - Added onControlPointModeChanged() handler
   - Added onCanvasControlPointAdded() handler
   - Updated onRegistrationFinished() - removed setImages call
   - Updated dialog text with new instructions

### Backup Files
- **`gui/widgets/manual_correction_tab_old.py`** - Previous implementation with built-in graphics view

## Testing Checklist

- [ ] Load camera and design images
- [ ] Run registration with "Stop before high-res warp" checked
- [ ] Registration completes and shows dialog
- [ ] Switch to Manual Correction tab
- [ ] Click "🔴 Add Red Points" button
- [ ] Cursor changes to crosshair
- [ ] Left-click on canvas adds red dot with label A
- [ ] Table updates with red point coordinates
- [ ] Status bar shows "Added red point #1"
- [ ] Click "🔵 Add Blue Points" button
- [ ] Right-click on canvas adds blue dot with label A
- [ ] Table updates showing complete pair A with calculated offset
- [ ] Add more points in mixed order (2 red, 1 blue, 1 red)
- [ ] Verify labels sequence correctly (A, B, C, D...)
- [ ] Zoom/pan canvas - markers scale and move correctly
- [ ] Remove selected pair works
- [ ] Clear all works
- [ ] Click "Apply Manual Corrections"
- [ ] Corrections logged and stored
- [ ] High-res warp proceeds with corrections

## Future Enhancements

### 1. Layer Panel Integration
- Add "Camera (Blue Points)" layer to Layer Panel
- Add "Registered Preview (Red Points)" layer to Layer Panel  
- Layer visibility toggles (eye icon)
- Layer opacity controls
- Contrast/brightness/invert adjustments in Layer Panel (not tab)

### 2. Menu Commands
- **Registration → Continue to High-Res Warp** - Apply corrections and warp 283.5MP
- **File → Send to Printer** - Export final result

### 3. Visual Enhancements
- Line connecting red→blue pairs when both exist
- Hover highlights
- Draggable markers (move after placement)
- Undo/redo for point additions

### 4. Advanced Features
- Import/export control points (JSON)
- Auto-suggest pairs based on deformation field
- Preview overlay of correction effect
- Heat map of deformation magnitude

## Technical Notes

### Coordinate Systems
- **Image coordinates**: (0, 0) at top-left, (width, height) at bottom-right
- **Screen coordinates**: Widget pixel position
- **Conversion**: `screenToImageCoords()` accounts for zoom and pan

### Label Generation
```python
def getLabel(index):
    label = ""
    num = index
    while True:
        label = chr(65 + (num % 26)) + label
        num = num // 26
        if num == 0:
            break
        num -= 1
    return label
```
Produces: A, B, C ... Z, AA, AB, AC ... AZ, BA, BB ...

### Offset Calculation
Applied to deformation field to refine registration:
```python
for red_x, red_y, blue_x, blue_y in corrections:
    dx = blue_x - red_x
    dy = blue_y - red_y
    # Apply to deformation field at (red_x, red_y)
```

## Status
✅ **IMPLEMENTED** - Ready for testing
- Tab redesigned
- Canvas integration complete
- Signal connections wired
- Mouse event handling added
- Marker rendering implemented
- Sequence-based pairing working
- Table updates automatically

## Date
November 10, 2025
