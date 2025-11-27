# Quick Start Guide - Alinify

## Prerequisites Checklist

- [ ] Windows 10/11 (64-bit)
- [ ] Visual Studio 2019/2022 with C++ Desktop Development
- [ ] CUDA Toolkit 12.0+ (for GPU support)
- [ ] CMake 3.20+
- [ ] Python 3.10+
- [ ] Git
- [ ] Gidel SDK installed at `C:\Gidel`

## Installation Steps

### 1. Clone Repository (if needed)
```powershell
git clone <repository-url> d:\Alinify
cd d:\Alinify
```

### 2. Install External Dependencies

Download and install the following:

#### ITK with Elastix
```powershell
# Download ITK 5.3+ source
git clone https://github.com/InsightSoftwareConsortium/ITK.git
cd ITK
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=C:/ITK/install
cmake --build . --config Release
cmake --install .
```

#### LibTorch (PyTorch C++)
```powershell
# Download from: https://pytorch.org/get-started/locally/
# Select: Windows, LibTorch, C++/Java, CUDA 12.1
# Extract to: C:/libtorch
```

#### OpenCV
```powershell
# Download pre-built from: https://opencv.org/releases/
# Or install via vcpkg:
vcpkg install opencv:x64-windows
```

#### Qt 6
```powershell
# Download installer from: https://www.qt.io/download-qt-installer
# Install to: C:/Qt/6.5.0/msvc2019_64
```

### 3. Build Alinify

```powershell
cd d:\Alinify

# Build C++ components
.\build.ps1

# Setup Python environment
.\setup_python.ps1
```

### 4. Configure System

Edit `config/system_config.yaml` for your setup:

```yaml
camera:
  resolution:
    width: 4096
    height: 1
  frequency: 10000  # Hz
  
  gidel:
    config_file: "config/camera/FGConfig.gxfg"
    board_id: 0

gpu_warp:
  enable: true
  device_id: 0  # Your GPU ID
```

## Running the System

### Option 1: GUI Application (Recommended)

```powershell
# Activate Python environment
.\venv\Scripts\Activate.ps1

# Launch GUI
python gui/main_gui.py
```

**GUI Features:**
- Load camera/design images
- Start/stop camera acquisition
- Real-time registration
- Manual deformation correction
- Performance monitoring

### Option 2: Python Pipeline

```powershell
.\venv\Scripts\Activate.ps1
python python/pipeline.py
```

### Option 3: C++ Example

```powershell
.\build\Release\alinify_pipeline.exe
```

## First Test Run (Without Camera)

1. **Launch GUI:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   python gui/main_gui.py
   ```

2. **Load Test Images:**
   - Click "Load Camera Image" → Select a grayscale test image
   - Click "Load Design Image" → Select an RGB design image

3. **Run Registration:**
   - Click "Register Images"
   - View results in "Registered" tab
   - Check "Deformation Field" tab for visualization

4. **Adjust Parameters:**
   - Go to "Registration" tab in control panel
   - Modify pyramid levels, grid spacing, etc.
   - Re-run registration

## Testing with Real Camera

### 1. Connect Camera
- Ensure Gidel frame grabber is installed
- Connect CameraLink cable
- Power on camera

### 2. Verify Connection
```powershell
# Run Gidel utilities
C:\Gidel\Utilities.lnk
```

### 3. Configure Camera
- Edit `config/camera/FGConfig.gxfg` using Gidel Configuration Tool
- Set resolution: 4096 x 1
- Set line rate: 10 kHz
- Set trigger mode

### 4. Start Acquisition
In GUI:
1. Click "Start Camera"
2. Monitor "Camera" tab for live feed
3. Watch stitching in real-time
4. Performance metrics in "Performance" tab

## Common Issues

### Build Errors

**"Cannot find ITK"**
```powershell
# Set CMAKE_PREFIX_PATH in build.ps1
-DCMAKE_PREFIX_PATH="C:/ITK/build;C:/libtorch;..."
```

**"CUDA not found"**
- Install CUDA Toolkit
- Ensure nvcc is in PATH
- Or disable CUDA: `-DUSE_CUDA=OFF`

**"Python bindings failed"**
- Ensure Python 3.10+ with development headers
- Install pybind11: `pip install pybind11`

### Runtime Errors

**"Camera init failed"**
- Check Gidel driver installation
- Verify board ID in config
- Run Gidel test utilities

**"GPU out of memory"**
- Reduce `gpu_warp.batch_size` in config
- Reduce `tile_size`
- Enable memory pooling

**"Import alinify_bindings failed"**
- Rebuild with Python bindings: `-DBUILD_PYTHON_BINDINGS=ON`
- Check Python version matches build
- Copy .pyd file to gui/ folder

## Performance Tuning

### For Maximum Speed

1. **CPU**:
   ```yaml
   registration:
     threads: 0  # Auto-detect all cores
     sampling:
       percentage: 0.1  # Reduce for speed
   ```

2. **GPU**:
   ```yaml
   gpu_warp:
     batch_size: 8  # Increase if VRAM allows
     use_streams: true
     num_streams: 4
   ```

3. **Camera**:
   ```yaml
   camera:
     buffer_count: 50  # Increase for high speed
   ```

### For Maximum Quality

1. **Registration**:
   ```yaml
   registration:
     pyramid:
       levels: 6  # More levels
     optimizer:
       max_iterations: [1000, 1000, 500, 250, 100, 50]
     sampling:
       percentage: 0.5  # More samples
   ```

2. **Stitching**:
   ```yaml
   stitching:
     overlap_region: 200  # Larger overlap
     quality_check:
       min_correlation: 0.85  # Higher threshold
   ```

## Next Steps

1. **Calibration**: Run camera calibration routine
2. **Test Patterns**: Use test patterns to verify alignment
3. **Production Run**: Start with slow speed, gradually increase
4. **Monitor Performance**: Use GUI performance tab
5. **Fine-tune**: Adjust parameters based on results

## Support

For issues:
1. Check logs in `logs/alinify.log`
2. Review ARCHITECTURE.md for system details
3. Check Gidel SDK documentation
4. Enable debug logging: `log_level: "DEBUG"`

## Resources

- **Gidel Documentation**: `C:\Gidel\Doc.lnk`
- **ITK Guide**: https://itk.org/ItkSoftwareGuide.pdf
- **Elastix Manual**: https://elastix.lumc.nl/manual.php
- **LibTorch API**: https://pytorch.org/cppdocs/
- **Qt Documentation**: https://doc.qt.io/qt-6/

---

**Ready to start? Run:**
```powershell
.\venv\Scripts\Activate.ps1
python gui/main_gui.py
```
