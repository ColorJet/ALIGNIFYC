# Alinify GUI - Quick Start Guide

## 🚀 Launch the GUI

```powershell
cd d:\Alinify
.\venv\Scripts\Activate.ps1
python gui\main_gui.py
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Load Camera Image |
| `Ctrl+Shift+O` | Load Design Image |
| `Ctrl+R` | Run Registration |
| `Ctrl+S` | Save Registered Image |
| `Ctrl+E` | Export Deformation Field |
| `F5` | Refresh Blend View |

## 📋 Workflow

### 1. Load Images
- **Camera Image**: Grayscale image from line scan camera
  - Click "Load Camera Image" or press `Ctrl+O`
  - Automatically converted to grayscale if needed
- **Design Image**: Reference/target RGB image
  - Click "Load Design Image" or press `Ctrl+Shift+O`
  - Kept as RGB for color comparison

### 2. View & Compare
Switch between tabs:
- **Camera**: View raw camera image
- **Design**: View design/reference image
- **Comparison**: Side-by-side + blended overlay
  - Use slider to adjust blend ratio (0-100%)
  - Live update as you move the slider
- **Registered**: See registration result
- **Deformation Field**: Visualize transformation

### 3. Run Registration
- Click "Register Images" or press `Ctrl+R`
- Watch the log panel for progress
- Quality metrics displayed automatically:
  - MSE (Mean Squared Error)
  - PSNR (Peak Signal-to-Noise Ratio)
  - Correlation coefficient
  - Mutual Information

### 4. Adjust Parameters
**Right Panel > Registration Tab:**
- **Pyramid Levels**: Multi-resolution levels (1-10)
- **Grid Spacing**: B-spline control point spacing (10-200)
- **B-spline Order**: Polynomial order (1-5)
- **Optimizer**: LBFGS, Gradient Descent, etc.
- **Max Iterations**: Convergence limit (50-5000)
- **Metric**: Mutual Information, Correlation, etc.

### 5. Visualize Deformation
**Deformation Field Tab:**
- **Grid**: Warped grid overlay showing transformation
- **Arrows**: Vector field visualization
- **Color Map**: Heat map of deformation magnitude
- **Magnitude**: Scalar field display

### 6. Export Results
- **Save Registered Image**: `Ctrl+S`
  - Saves as PNG, JPEG, or TIFF
- **Export Deformation Field**: `Ctrl+E`
  - Saves as NumPy .npz file
  - Contains x, y, dx, dy arrays

## 📊 Understanding the Output

### Log Panel
Real-time messages showing:
- Image loading confirmation with statistics
- Registration progress
- Quality metrics
- Error messages with traceback

### Quality Metrics
- **MSE**: Lower is better (0 = perfect match)
- **PSNR**: Higher is better (>30 dB = good quality)
- **Correlation**: Closer to 1.0 = better alignment
- **Mutual Information**: Higher = more shared information

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  [Load Camera] [Load Design] [Start/Stop] [Register]   │
│  [Send to Printer] [Save] [Export]                     │
├──────────────────────────────┬──────────────────────────┤
│                              │  REGISTRATION PARAMS     │
│   IMAGE VIEWERS              │  - Pyramid Levels        │
│   ┌──────────────────────┐   │  - Grid Spacing         │
│   │ [Camera] [Design]    │   │  - Optimizer            │
│   │ [Registered]         │   │  - Metric               │
│   │ [Comparison]         │   ├──────────────────────────┤
│   │ [Deformation Field]  │   │  MANUAL CORRECTION       │
│   │                      │   │  - Control Points        │
│   │  [Image Display]     │   ├──────────────────────────┤
│   │                      │   │  PERFORMANCE             │
│   │                      │   │  - FPS, Timing           │
│   └──────────────────────┘   ├──────────────────────────┤
│                              │  LOG                     │
│                              │  [Messages & Errors]     │
├──────────────────────────────┴──────────────────────────┤
│  Status: Ready                                          │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Current Mode: DEMO

The GUI currently runs in **demo mode** because C++ bindings are not built yet.

**What Works:**
- ✅ Image loading and display
- ✅ Basic registration (OpenCV-based)
- ✅ Deformation visualization
- ✅ Quality metrics
- ✅ Blend comparison
- ✅ Save/Export functionality

**What Needs C++ Bindings:**
- ⚠️ Real-time camera acquisition
- ⚠️ Production ITK/Elastix registration
- ⚠️ GPU-accelerated warping
- ⚠️ Printer interface

## 🐛 Troubleshooting

### GUI doesn't start
```powershell
# Ensure venv is activated
cd d:\Alinify
.\venv\Scripts\Activate.ps1

# Verify PySide6 is installed
pip list | Select-String PySide6

# If not installed
pip install PySide6
```

### Images not loading
- Check file format (PNG, JPG, TIF supported)
- Verify file path doesn't contain special characters
- Check log panel for specific error messages

### Registration fails
- Ensure both images are loaded first
- Check that images aren't corrupted
- Review log panel for error details

### Slow performance
- Large images take longer to process
- Use smaller test images first
- Check Task Manager for memory usage

## 💡 Tips

1. **Start Small**: Test with small images first (< 2000x2000)
2. **Watch the Log**: All operations are logged with timestamps
3. **Use Shortcuts**: Keyboard shortcuts speed up workflow
4. **Adjust Blend**: Use comparison slider to find optimal overlay
5. **Check Metrics**: Quality metrics help assess registration accuracy
6. **Export Often**: Save intermediate results before trying new settings

## 📝 File Formats

### Input
- **Images**: PNG, JPEG, TIFF, RAW
- **Bit Depth**: 8-bit or 16-bit (auto-normalized)
- **Color**: Grayscale or RGB (auto-converted)

### Output
- **Images**: PNG (lossless), JPEG (lossy), TIFF (high quality)
- **Deformation**: NPZ (NumPy compressed format)

## 🎯 Next Steps

To enable full functionality:
1. Build C++ bindings: `cmake --build build --target alinify_bindings`
2. Camera integration: Connect Gidel frame grabber
3. Printer setup: Configure printer DLL interface

---

**Version**: 1.0.0 (Demo Mode)  
**Last Updated**: November 7, 2025
