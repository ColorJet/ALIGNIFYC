# Alinify Project Structure

## Overview
Complete line scan camera registration system with real-time processing, GPU acceleration, and print head integration.

## Directory Structure

```
Alinify/
├── CMakeLists.txt              # Root CMake configuration
├── README.md                   # Main documentation
├── .gitignore                  # Git ignore rules
├── build.ps1                   # Windows build script
├── setup_python.ps1            # Python environment setup
├── requirements.txt            # Python dependencies
│
├── config/                     # Configuration files
│   ├── system_config.yaml      # Main system configuration
│   └── camera/                 # Camera-specific configs
│       └── FGConfig.gxfg       # Gidel frame grabber config
│
├── include/                    # C++ header files
│   └── alinify/
│       ├── common/             # Common types and utilities
│       │   ├── types.h         # Core data structures
│       │   └── logger.h        # Logging system
│       ├── camera/             # Camera acquisition
│       │   ├── camera_interface.h
│       │   └── gidel_camera.h
│       ├── stitching/          # Strip stitching
│       │   └── strip_stitcher.h
│       ├── preprocessing/      # Image preprocessing
│       │   └── image_processor.h
│       ├── registration/       # Elastix/ITK registration
│       │   └── elastix_wrapper.h
│       ├── gpu_warp/           # GPU warping
│       │   └── cuda_warper.h
│       └── printer/            # Printer interface
│           └── printer_interface.h
│
├── src/                        # C++ source files
│   ├── core/                   # Core library
│   │   └── CMakeLists.txt
│   ├── camera/                 # Camera implementation
│   │   ├── gidel_camera.cpp
│   │   └── CMakeLists.txt
│   ├── stitching/              # Stitching implementation
│   │   ├── strip_stitcher.cpp
│   │   └── CMakeLists.txt
│   ├── preprocessing/          # Preprocessing implementation
│   │   ├── image_processor.cpp
│   │   └── CMakeLists.txt
│   ├── registration/           # Registration implementation
│   │   ├── elastix_wrapper.cpp
│   │   └── CMakeLists.txt
│   ├── gpu_warp/               # GPU warping implementation
│   │   ├── cuda_warper.cpp
│   │   └── CMakeLists.txt
│   ├── printer/                # Printer implementation
│   │   ├── printer_interface.cpp
│   │   └── CMakeLists.txt
│   └── python_bindings/        # Python bindings
│       ├── bindings.cpp
│       └── CMakeLists.txt
│
├── python/                     # Python code
│   └── pipeline.py             # High-level Python API
│
├── gui/                        # GUI application
│   ├── __init__.py
│   ├── main_gui.py             # Main GUI application
│   └── widgets/                # Custom Qt widgets
│       ├── __init__.py
│       ├── image_viewer.py
│       ├── deformation_viewer.py
│       ├── control_point_editor.py
│       └── performance_monitor.py
│
├── examples/                   # Example applications
│   └── main_pipeline.cpp       # Complete pipeline example
│
├── tests/                      # Unit tests (future)
│
├── docs/                       # Additional documentation (future)
│
└── logs/                       # Log files (created at runtime)
```

## Module Descriptions

### 1. Camera Acquisition (`src/camera/`)
- **Purpose**: Interface with Gidel CameraLink frame grabber
- **Key Features**:
  - 4K @ 10kHz line scanning
  - GenTL producer integration
  - Hardware trigger control (auto, external, encoder)
  - Multi-buffer management
  - Real-time strip callback
- **Dependencies**: Gidel SDK (ProcFgApi, InfiniVision)

### 2. Strip Stitching (`src/stitching/`)
- **Purpose**: Merge 42mm scan strips into complete image
- **Key Features**:
  - Bidirectional scanning support
  - Sub-pixel alignment (phase correlation)
  - Overlap blending
  - Mechanical error compensation
- **Dependencies**: OpenCV

### 3. Preprocessing (`src/preprocessing/`)
- **Purpose**: Prepare images for registration
- **Key Features**:
  - Gaussian/bilateral/median filtering
  - Histogram equalization/matching
  - Normalization
  - Edge enhancement
- **Dependencies**: ITK, OpenCV

### 4. Registration (`src/registration/`)
- **Purpose**: Compute deformation field between images
- **Key Features**:
  - Elastix multi-resolution framework
  - B-spline transformation
  - Multiple optimizers (LBFGS, SGD)
  - Multiple metrics (MI, NCC, MSE)
  - Automatic parameter tuning
- **Dependencies**: ITK, Elastix

### 5. GPU Warping (`src/gpu_warp/`)
- **Purpose**: Apply deformation to large RGB images
- **Key Features**:
  - LibTorch CUDA implementation
  - Memory-efficient tiling for 1000MP+ images
  - Multiple interpolation modes
  - GPU memory management
- **Dependencies**: LibTorch, CUDA

### 6. Printer Interface (`src/printer/`)
- **Purpose**: Send registered images to print head
- **Key Features**:
  - DLL abstraction layer
  - TCP/UDP communication
  - Buffer management
  - Format conversion
- **Dependencies**: Windows API

### 7. Python Bindings (`src/python_bindings/`)
- **Purpose**: Expose C++ API to Python
- **Key Features**:
  - pybind11 bindings
  - NumPy array integration
  - High-level Pipeline API
  - Error handling
- **Dependencies**: pybind11, Python 3.10+

### 8. GUI Application (`gui/`)
- **Purpose**: Monitoring and manual correction interface
- **Key Features**:
  - Real-time camera preview
  - Side-by-side comparison
  - Deformation field visualization
  - Manual B-spline control point editing
  - Performance metrics
  - Log viewer
- **Dependencies**: PySide6 (Qt 6)

## Data Flow

```
Camera (Gidel)
    ↓ [Raw strips @ 10kHz]
Strip Stitching
    ↓ [Merged grayscale image]
Preprocessing (ITK)
    ↓ [Filtered/normalized image]
Registration (Elastix)
    ↓ [Deformation field]
GPU Warping (LibTorch/CUDA)
    ↓ [Warped RGB design image]
Printer (DLL)
    ↓ [Physical output]
```

## Configuration

All system parameters are configured via `config/system_config.yaml`:

- **Camera**: Resolution, frequency, FOV, trigger mode
- **Scanning**: Max length, overlap, bidirectional mode
- **Stitching**: Alignment method, blending, quality checks
- **Preprocessing**: Filters, normalization methods
- **Registration**: Pyramid levels, B-spline parameters, optimizer settings
- **GPU**: Device ID, memory limits, tiling parameters
- **Printer**: DLL path, communication settings

## Build Process

1. **Install Prerequisites**:
   - Visual Studio 2019/2022 with C++ and CUDA
   - CMake 3.20+
   - CUDA Toolkit 12.0+
   - ITK 5.3+ (with Elastix)
   - LibTorch (PyTorch C++)
   - OpenCV 4.8+
   - Qt 6.5+
   - Python 3.10+

2. **Build C++ Libraries**:
   ```powershell
   .\build.ps1
   ```

3. **Setup Python Environment**:
   ```powershell
   .\setup_python.ps1
   ```

4. **Run GUI**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python gui/main_gui.py
   ```

## Performance Targets

| Operation | Target | Hardware |
|-----------|--------|----------|
| Acquisition | 10,000 lines/sec | Gidel Frame Grabber |
| Stitching | < 10ms/strip | CPU (multi-threaded) |
| Registration | < 500ms (1.8m image) | CPU (20 cores) |
| GPU Warping | < 200ms (1000MP) | RTX 5090 |
| **Total Latency** | **< 1 second** | Full system |

## Key Technologies

- **C++17**: Core implementation
- **CUDA**: GPU acceleration
- **ITK/Elastix**: Medical imaging registration
- **LibTorch**: Deep learning framework (for warping)
- **OpenCV**: Computer vision operations
- **Qt/PySide6**: GUI framework
- **pybind11**: Python bindings
- **CMake**: Build system

## Next Steps

To fully implement this system:

1. **Complete Registration Module**: Integrate full Elastix API
2. **Optimize GPU Warping**: Fine-tune memory management and tiling
3. **Implement Printer Protocol**: Complete DLL interface based on actual printer SDK
4. **Add Unit Tests**: Comprehensive test suite
5. **Performance Profiling**: Identify and optimize bottlenecks
6. **Documentation**: API reference, user manual
7. **Calibration Tools**: Camera and mechanical calibration utilities

## Notes

- Some modules have stub implementations (marked with TODO comments)
- Full ITK/Elastix integration requires complete parameter tuning
- Printer DLL interface needs actual printer SDK
- GUI is fully functional but needs backend integration
- All modules are designed with real-time constraints in mind
