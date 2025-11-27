# Alinify - Real-time Line Scan Registration System

High-performance image acquisition, registration, and warping system for line scan cameras with print head integration.

## System Overview

**Hardware Requirements:**
- 4K Line Scan Camera @ 10 kHz (42mm FOV)
- CameraLink Frame Grabber (Gidel)
- RTX 5090 GPU (16GB+ VRAM)
- 20+ Core CPU
- 64-128GB RAM
- NVMe SSD for image buffer

**Image Specifications:**
- Scan width: 42mm per strip
- Maximum scan length: 1.8 meters
- Bi-directional scanning (left-right, right-left)
- Final image size: Up to 1000 megapixels (RGB)
- Camera output: Grayscale

## Architecture

```
Camera Acquisition (C++)
    ↓
Strip Stitching (C++/CUDA)
    ↓
Preprocessing (ITK/C++)
    ↓
Registration Engine (Elastix/ITK)
    ↓
GPU Warping (LibTorch/CUDA)
    ↓
Printer Interface (DLL)

GUI (Qt/Python) - Monitoring & Manual Correction
```

## Build Instructions

### Prerequisites

1. **Install Dependencies:**
   - CMake 3.20+
   - Visual Studio 2019/2022 with C++ and CUDA support
   - CUDA Toolkit 12.0+
   - ITK 5.3+ (build from source with Elastix)
   - LibTorch (PyTorch C++)
   - OpenCV 4.8+
   - Python 3.10+
   - Qt 6.5+

2. **Gidel SDK:**
   - Already installed at `C:\Gidel`
   - Ensure GenTL provider is configured

### Building

```powershell
# Clone and navigate
cd d:\Alinify

# Create build directory
mkdir build
cd build

# Configure
cmake .. -G "Visual Studio 17 2022" -A x64 `
    -DCMAKE_PREFIX_PATH="C:/libtorch;C:/ITK/build;C:/Qt/6.5.0/msvc2019_64" `
    -DUSE_CUDA=ON `
    -DBUILD_PYTHON_BINDINGS=ON

# Build
cmake --build . --config Release -j 20

# Install
cmake --install . --prefix ../install
```

### Python Environment

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### 1. Configuration

Edit `config/system_config.yaml`:
```yaml
camera:
  resolution: [4096, 1]
  frequency: 10000  # Hz
  fov_width: 42  # mm
  
scanning:
  max_length: 1800  # mm
  overlap_pixels: 100
  
registration:
  pyramid_levels: 5
  bspline_grid_spacing: 50
  
gpu:
  device_id: 0
  batch_size: 4
```

### 2. Run Pipeline

**Command Line:**
```powershell
# Full automatic pipeline
.\build\Release\alinify_pipeline.exe --config config/system_config.yaml

# With GUI
python gui/main_gui.py
```

**Python API:**
```python
from alinify import Pipeline, CameraConfig

# Initialize pipeline
pipeline = Pipeline(config_path="config/system_config.yaml")

# Start acquisition
pipeline.start_camera()

# Process in real-time
while pipeline.is_scanning():
    if pipeline.has_new_strip():
        strip = pipeline.get_strip()
        # Process...

# Get final registered image
registered_rgb = pipeline.get_registered_image()

# Send to printer
pipeline.send_to_printer(registered_rgb)
```

### 3. GUI Application

```powershell
python gui/main_gui.py
```

**Features:**
- Live camera preview
- Strip stitching visualization
- Registration parameter tuning
- Manual B-spline control points adjustment
- Deformation field visualization
- Side-by-side comparison (camera vs design)

## Module Documentation

### Camera Acquisition (`src/camera`)
- Gidel CameraLink interface
- GenTL integration
- Trigger control (auto/encoder/external)
- Raw buffer management

### Stitching (`src/stitching`)
- Bi-directional strip merging
- Sub-pixel alignment
- Overlap region cross-correlation
- Mechanical error compensation

### Preprocessing (`src/preprocessing`)
- ITK-based filtering
- Normalization
- Edge enhancement
- Noise reduction

### Registration (`src/registration`)
- Elastix multi-resolution framework
- B-spline transformation
- Multiple optimizers (LBFGS, Adam)
- Multiple metrics (MI, NCC, MSE)
- Automatic parameter selection

### GPU Warping (`src/gpu_warp`)
- LibTorch CUDA implementation
- Deformation field application
- Large image handling (1000MP+)
- Memory-efficient tiling

### Printer Interface (`src/printer`)
- DLL abstraction layer
- Image format conversion
- Buffering and flow control

## Performance Targets

- **Acquisition:** 10,000 lines/second
- **Stitching:** < 10ms per strip pair
- **Registration:** < 500ms for full 1.8m image
- **GPU Warping:** < 200ms for 1000MP image
- **End-to-end latency:** < 1 second

## Troubleshooting

### Camera Issues
```powershell
# Test camera connection
.\build\Release\test_camera.exe

# Check GenTL providers
.\build\Release\list_devices.exe
```

### GPU Memory
- Reduce `gpu.batch_size` in config
- Enable memory pooling
- Use image tiling for large images

### Registration Quality
- Adjust `pyramid_levels`
- Tune `bspline_grid_spacing`
- Try different similarity metrics

## License

Proprietary - All Rights Reserved

## Contact

For support and questions, contact the development team.
