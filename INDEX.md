# Alinify - Documentation Index

Welcome to the Alinify line scan registration system!

## 📚 Documentation Guide

### Start Here
1. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete overview of the entire system
2. **[QUICKSTART.md](QUICKSTART.md)** - Get up and running quickly
3. **[README.md](README.md)** - General project information and usage

### Deep Dive
4. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed technical architecture
5. **[config/system_config.yaml](config/system_config.yaml)** - Configuration reference

## 🗂️ Code Organization

### By Language

#### C++ Core (`include/` + `src/`)
- **Common**: [types.h](include/alinify/common/types.h), [logger.h](include/alinify/common/logger.h)
- **Camera**: [gidel_camera.h](include/alinify/camera/gidel_camera.h), [gidel_camera.cpp](src/camera/gidel_camera.cpp)
- **Stitching**: [strip_stitcher.h](include/alinify/stitching/strip_stitcher.h), [strip_stitcher.cpp](src/stitching/strip_stitcher.cpp)
- **Preprocessing**: [image_processor.h](include/alinify/preprocessing/image_processor.h), [image_processor.cpp](src/preprocessing/image_processor.cpp)
- **Registration**: [elastix_wrapper.h](include/alinify/registration/elastix_wrapper.h), [elastix_wrapper.cpp](src/registration/elastix_wrapper.cpp)
- **GPU Warping**: [cuda_warper.h](include/alinify/gpu_warp/cuda_warper.h), [cuda_warper.cpp](src/gpu_warp/cuda_warper.cpp)
- **Printer**: [printer_interface.h](include/alinify/printer/printer_interface.h), [printer_interface.cpp](src/printer/printer_interface.cpp)

#### Python (`python/` + `gui/`)
- **Pipeline API**: [pipeline.py](python/pipeline.py)
- **GUI Application**: [main_gui.py](gui/main_gui.py)
- **Widgets**: [gui/widgets/](gui/widgets/)

#### Bindings
- **Python-C++ Bridge**: [bindings.cpp](src/python_bindings/bindings.cpp)

### By Function

#### Image Acquisition
- [camera_interface.h](include/alinify/camera/camera_interface.h) - Abstract interface
- [gidel_camera.h](include/alinify/camera/gidel_camera.h) - Gidel implementation
- [gidel_camera.cpp](src/camera/gidel_camera.cpp) - Full implementation

#### Image Processing
- [strip_stitcher.cpp](src/stitching/strip_stitcher.cpp) - Bidirectional stitching
- [image_processor.cpp](src/preprocessing/image_processor.cpp) - Filtering/normalization

#### Registration
- [elastix_wrapper.cpp](src/registration/elastix_wrapper.cpp) - B-spline registration

#### GPU Acceleration
- [cuda_warper.cpp](src/gpu_warp/cuda_warper.cpp) - CUDA warping with tiling

#### User Interface
- [main_gui.py](gui/main_gui.py) - Main application window
- [image_viewer.py](gui/widgets/image_viewer.py) - Image display
- [deformation_viewer.py](gui/widgets/deformation_viewer.py) - Deformation visualization
- [control_point_editor.py](gui/widgets/control_point_editor.py) - Manual correction
- [performance_monitor.py](gui/widgets/performance_monitor.py) - Metrics display

## 🔍 Quick Reference

### Configuration
| File | Purpose |
|------|---------|
| [system_config.yaml](config/system_config.yaml) | Main system configuration |
| [CMakeLists.txt](CMakeLists.txt) | Build configuration |
| [requirements.txt](requirements.txt) | Python dependencies |

### Build & Setup
| File | Purpose |
|------|---------|
| [build.ps1](build.ps1) | Build C++ components |
| [setup_python.ps1](setup_python.ps1) | Setup Python environment |

### Examples
| File | Purpose |
|------|---------|
| [main_pipeline.cpp](examples/main_pipeline.cpp) | Complete C++ pipeline example |
| [pipeline.py](python/pipeline.py) | Python API example |

## 🎯 Common Tasks

### Building the Project
```powershell
.\build.ps1
```
See: [QUICKSTART.md](QUICKSTART.md#installation-steps)

### Running the GUI
```powershell
.\venv\Scripts\Activate.ps1
python gui/main_gui.py
```
See: [QUICKSTART.md](QUICKSTART.md#running-the-system)

### Configuring the System
Edit: [config/system_config.yaml](config/system_config.yaml)  
Reference: [README.md](README.md#usage)

### Understanding the Architecture
Read: [ARCHITECTURE.md](ARCHITECTURE.md)  
Key sections:
- [Module Descriptions](ARCHITECTURE.md#module-descriptions)
- [Data Flow](ARCHITECTURE.md#data-flow)
- [Performance Targets](ARCHITECTURE.md#performance-targets)

### Integrating with Hardware
See:
- [Camera setup](QUICKSTART.md#testing-with-real-camera)
- [Gidel SDK location](ARCHITECTURE.md#1-camera-acquisition-srccamera)

## 📖 Learning Path

### For Users
1. Read [README.md](README.md)
2. Follow [QUICKSTART.md](QUICKSTART.md)
3. Configure [system_config.yaml](config/system_config.yaml)
4. Run [main_gui.py](gui/main_gui.py)

### For Developers
1. Review [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
2. Study [ARCHITECTURE.md](ARCHITECTURE.md)
3. Examine [common/types.h](include/alinify/common/types.h)
4. Browse module headers in [include/alinify/](include/alinify/)
5. Look at [main_pipeline.cpp](examples/main_pipeline.cpp) example

### For Integrators
1. Check hardware requirements in [README.md](README.md#system-overview)
2. Install dependencies per [QUICKSTART.md](QUICKSTART.md#install-external-dependencies)
3. Configure camera in [system_config.yaml](config/system_config.yaml)
4. Test with [main_pipeline.cpp](examples/main_pipeline.cpp)

## 🔗 External Resources

### SDKs & Libraries
- **Gidel SDK**: `C:\Gidel\Doc.lnk`
- **ITK Manual**: https://itk.org/ItkSoftwareGuide.pdf
- **Elastix Documentation**: https://elastix.lumc.nl/
- **LibTorch API**: https://pytorch.org/cppdocs/
- **Qt Documentation**: https://doc.qt.io/qt-6/
- **OpenCV**: https://docs.opencv.org/

### Technologies
- **CMake**: https://cmake.org/documentation/
- **pybind11**: https://pybind11.readthedocs.io/
- **CUDA**: https://docs.nvidia.com/cuda/
- **PySide6**: https://doc.qt.io/qtforpython/

## 🆘 Troubleshooting

### Build Issues
See: [QUICKSTART.md](QUICKSTART.md#build-errors)

### Runtime Issues
See: [QUICKSTART.md](QUICKSTART.md#runtime-errors)

### Performance Issues
See: [QUICKSTART.md](QUICKSTART.md#performance-tuning)

### Logs
Check: `logs/alinify.log` after running the system

## 📊 Project Statistics

- **Total Files**: 66
- **Lines of Code**: ~6,000+
- **Languages**: C++, Python, YAML, CMake
- **Modules**: 8 (Camera, Stitching, Preprocessing, Registration, GPU Warp, Printer, Bindings, GUI)
- **External Dependencies**: ITK, Elastix, LibTorch, OpenCV, Qt, CUDA

## 🎓 Key Concepts

### Line Scanning
A 4K linear sensor captures one line at a time at 10,000 Hz while moving across the material (1.8m max length).

### Bidirectional Scanning
Scans left→right, then right→left, doubling throughput. Requires mechanical error compensation.

### Strip Stitching
Combines overlapping 42mm wide strips into a complete image using phase correlation for sub-pixel alignment.

### B-Spline Registration
Non-rigid deformation model that allows local warping to match the camera image to the design.

### Multi-Resolution Pyramid
Coarse-to-fine registration strategy that starts with downsampled images for speed and robustness.

### GPU Warping
Applies the computed deformation field to a large RGB image using CUDA, with tiling for memory efficiency.

## 📞 Support

For questions or issues:
1. Check documentation in this index
2. Review logs in `logs/`
3. Enable debug logging: `log_level: "DEBUG"` in config
4. Consult external SDK documentation

---

**Navigation Tips:**
- Start with [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for overview
- Use [QUICKSTART.md](QUICKSTART.md) for setup
- Reference [ARCHITECTURE.md](ARCHITECTURE.md) for details
- Modify [system_config.yaml](config/system_config.yaml) for configuration

**Ready to begin? → [QUICKSTART.md](QUICKSTART.md)**
