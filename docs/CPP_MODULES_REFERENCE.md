# Alinify C++ Modules Reference

Complete documentation for all compiled C++ modules in the Alinify system.

---

## Table of Contents

1. [Build System Overview](#build-system-overview)
2. [Module Summary](#module-summary)
3. [Core Module](#core-module-alinify_core)
4. [Preprocessing Module](#preprocessing-module-alinify_preprocessing)
5. [Stitching Module](#stitching-module-alinify_stitching)
6. [Printer Module](#printer-module-alinify_printer)
7. [Python Bindings](#python-bindings-alinify_bindings)
8. [Building the Modules](#building-the-modules)
9. [Integration Examples](#integration-examples)

---

## Build System Overview

The Alinify C++ codebase uses CMake as its build system. The project is structured as a collection of modular static libraries that are linked together.

### CMake Configuration

```cmake
# Main CMakeLists.txt options
option(BUILD_PYTHON_BINDINGS "Build Python bindings" ON)
option(BUILD_TESTS "Build tests" ON)

# Required packages
find_package(ITK REQUIRED)           # For elastix registration
find_package(OpenCV REQUIRED)        # For image processing
find_package(pybind11 CONFIG)        # For Python bindings (optional)
```

### Build Directory Structure

```
build/
├── src/
│   ├── camera/          # alinify_camera.lib
│   ├── core/            # (header-only)
│   ├── preprocessing/   # alinify_preprocessing.lib
│   ├── printer/         # alinify_printer.lib
│   ├── stitching/       # alinify_stitching.lib
│   └── python_bindings/ # alinify_bindings.pyd (if enabled)
└── x64/Release/
    └── alinify_bindings.pyd
```

---

## Module Summary

| Module | Library Type | Status | Dependencies | Purpose |
|--------|-------------|--------|--------------|---------|
| `alinify_core` | INTERFACE | ✅ Active | None | Core types and structures |
| `alinify_camera` | STATIC | ✅ Active | ProcFgApi, InfiniVision | Gidel camera control |
| `alinify_preprocessing` | STATIC | ✅ Active | ITK, OpenCV | Image preprocessing pipeline |
| `alinify_stitching` | STATIC | ✅ Active | OpenCV | Strip stitching |
| `alinify_printer` | STATIC | ✅ Active | Windows DLL | Printer communication |
| `alinify_bindings` | pybind11 | ⚠️ Conditional | All above + pybind11 | Python interface |

**Legend:**
- ✅ Active = Compiles with standard dependencies
- ⚠️ Conditional = Requires optional dependencies (BUILD_PYTHON_BINDINGS=ON)

---

## Core Module (alinify_core)

**Type:** INTERFACE (header-only library)  
**Location:** `include/alinify/types.h`  
**Dependencies:** None

### Purpose

Defines all core data structures used across the Alinify system. As an INTERFACE library, no compilation is needed - headers are included directly.

### Data Structures

#### Image<T>

```cpp
template<typename T>
struct Image {
    std::vector<T> data;    // Pixel data
    int width;              // Image width
    int height;             // Image height
    int channels;           // Number of channels (1=grayscale, 3=RGB)
    double pixel_size_mm;   // Physical size per pixel
};

// Common type aliases
using GrayImage = Image<uint8_t>;
using FloatImage = Image<float>;
using RGBImage = Image<uint8_t>;  // channels=3
```

#### ScanStrip

```cpp
struct ScanStrip {
    GrayImage image;         // Strip image data
    int strip_id;            // Sequential identifier
    double position_mm;      // Physical position in scan
    double overlap_percent;  // Overlap with previous strip
};
```

#### DeformationField

```cpp
struct DeformationField {
    std::vector<float> dx;   // X displacement at each pixel
    std::vector<float> dy;   // Y displacement at each pixel
    int width;               // Field width
    int height;              // Field height
    double grid_spacing_mm;  // Spacing between grid points
};
```

#### RegistrationResult

```cpp
struct RegistrationResult {
    DeformationField field;     // Computed deformation
    double similarity_score;    // Final similarity metric
    int iterations;             // Iterations to converge
    bool success;               // Whether registration succeeded
    std::string error_message;  // Error details if failed
};
```

#### CameraConfig

```cpp
struct CameraConfig {
    int width = 4096;           // Image width in pixels
    int height = 1;             // Lines per acquisition
    int frequency_hz = 10000;   // Scan frequency
    int bit_depth = 8;          // Bits per pixel
    double pixel_size_mm = 0.010256;
    double fov_width_mm = 42.0;
};
```

#### ScanningParams

```cpp
struct ScanningParams {
    double scan_speed_mm_s = 100.0;
    double line_frequency_hz = 10000.0;
    double strip_overlap_percent = 10.0;
    int strips_per_scan = 10;
};
```

#### RegistrationParams

```cpp
struct RegistrationParams {
    std::string method = "bspline";  // "bspline", "demons", "hybrid"
    int grid_spacing = 50;
    int max_iterations = 1000;
    double convergence_threshold = 1e-6;
    std::string similarity_metric = "NMI";  // NMI, NCC, MI, MSE
    bool use_mask = false;
    bool use_gpu = true;
};
```

#### GPUConfig

```cpp
struct GPUConfig {
    bool enabled = true;
    int device_id = 0;
    size_t max_memory_mb = 4096;
    bool prefer_cuda = true;
};
```

#### StatusCode

```cpp
enum class StatusCode {
    OK = 0,
    ERROR_INITIALIZATION,
    ERROR_CONFIGURATION,
    ERROR_MEMORY,
    ERROR_PROCESSING,
    ERROR_IO,
    ERROR_HARDWARE,
    ERROR_TIMEOUT,
    ERROR_CANCELLED
};
```

---

## Preprocessing Module (alinify_preprocessing)

**Type:** STATIC library  
**Location:** `src/preprocessing/image_processor.cpp`  
**Header:** `include/alinify/image_processor.h`  
**Dependencies:** alinify_core, ITK, OpenCV

### Purpose

Provides image preprocessing functions for fabric scan optimization. All methods are static for stateless, functional-style processing.

### API Reference

```cpp
class ImageProcessor {
public:
    // Blur filters
    static GrayImage gaussianBlur(const GrayImage& input, int kernel_size);
    static GrayImage bilateralFilter(const GrayImage& input, 
                                     int diameter, 
                                     double sigma_color, 
                                     double sigma_space);
    static GrayImage medianFilter(const GrayImage& input, int kernel_size);
    
    // Enhancement
    static GrayImage histogramEqualization(const GrayImage& input);
    static GrayImage histogramMatching(const GrayImage& source, 
                                       const GrayImage& reference);
    static GrayImage normalize(const GrayImage& input, 
                               double min_val = 0.0, 
                               double max_val = 255.0);
    static GrayImage unsharpMask(const GrayImage& input, 
                                 double amount = 1.0, 
                                 double radius = 1.0, 
                                 double threshold = 0.0);
    
    // Pipeline processing
    static GrayImage applyPipeline(const GrayImage& input, 
                                   const std::vector<std::string>& operations);
};
```

### Function Details

| Function | Parameters | Description |
|----------|------------|-------------|
| `gaussianBlur` | kernel_size (odd integer) | Smooths image reducing noise |
| `bilateralFilter` | diameter, sigma_color, sigma_space | Edge-preserving smoothing |
| `medianFilter` | kernel_size (odd integer) | Salt-and-pepper noise removal |
| `histogramEqualization` | - | Enhances contrast |
| `histogramMatching` | reference image | Matches histogram to reference |
| `normalize` | min_val, max_val | Scales intensity range |
| `unsharpMask` | amount, radius, threshold | Sharpens image details |
| `applyPipeline` | operation list | Applies sequence of operations |

### Pipeline Format

```cpp
// Example pipeline configuration
std::vector<std::string> pipeline = {
    "gaussian:5",           // Gaussian blur, kernel=5
    "histogram_eq",         // Histogram equalization
    "normalize:0:255",      // Normalize to 0-255
    "unsharp:1.5:1.0:0"     // Unsharp mask
};

GrayImage result = ImageProcessor::applyPipeline(input, pipeline);
```

---

## Stitching Module (alinify_stitching)

**Type:** STATIC library  
**Location:** `src/stitching/strip_stitcher.cpp`  
**Header:** `include/alinify/strip_stitcher.h`  
**Dependencies:** alinify_core, OpenCV

### Purpose

Stitches multiple scan strips into a single continuous image using phase correlation for sub-pixel alignment.

### API Reference

```cpp
class StripStitcher {
public:
    StripStitcher();
    ~StripStitcher();
    
    // Main interface
    bool initialize(int expected_strips = 10);
    bool addStrip(const ScanStrip& strip);
    GrayImage getStitchedImage() const;
    void reset();
    
    // Statistics
    struct AlignmentStats {
        double mean_shift_x;      // Average X offset
        double mean_shift_y;      // Average Y offset
        double std_shift_x;       // X offset std deviation
        double std_shift_y;       // Y offset std deviation
        int strips_processed;     // Total strips added
        int alignment_failures;   // Failed alignments
    };
    
    AlignmentStats getStatistics() const;
    
private:
    // Internal alignment methods
    Point2d phaseCorrelation(const GrayImage& img1, const GrayImage& img2);
    Point2d templateMatching(const GrayImage& img1, const GrayImage& img2);
    void blendOverlapRegion(GrayImage& target, const GrayImage& source, 
                            int overlap_start, int blend_width);
};
```

### Function Details

| Function | Description |
|----------|-------------|
| `initialize(n)` | Prepares for stitching n strips, allocates buffers |
| `addStrip(strip)` | Adds a strip, aligns with previous, updates composite |
| `getStitchedImage()` | Returns the current stitched result |
| `reset()` | Clears all strips and resets state |
| `getStatistics()` | Returns alignment quality metrics |

### Alignment Algorithm

1. **Phase Correlation** (primary): FFT-based sub-pixel alignment
   - Computes cross-power spectrum
   - Finds peak for shift estimation
   - Sub-pixel refinement via parabolic fitting

2. **Template Matching** (fallback): For poor phase correlation results
   - Uses OpenCV's `matchTemplate` with `TM_CCOEFF_NORMED`
   - Searches within expected overlap region

3. **Blending**: Linear alpha blend in overlap regions
   - Prevents visible seams
   - Configurable blend width

---

## Printer Module (alinify_printer)

**Type:** STATIC library  
**Location:** `src/printer/printer_interface.cpp`  
**Header:** `include/alinify/printer_interface.h`  
**Dependencies:** alinify_core, Windows API

### Purpose

Interfaces with industrial textile printers via Windows DLL. Handles image transfer and status monitoring.

### API Reference

```cpp
class PrinterInterface {
public:
    PrinterInterface();
    ~PrinterInterface();
    
    // Lifecycle
    bool initialize(const std::string& dll_path);
    void close();
    
    // Operations
    bool sendImage(const RGBImage& image);
    bool isReady() const;
    std::string getStatus() const;
    
private:
    HMODULE printer_dll_;
    // Function pointers to DLL exports
    typedef bool (*SendImageFunc)(const uint8_t*, int, int, int);
    typedef bool (*IsReadyFunc)();
    typedef const char* (*GetStatusFunc)();
    
    SendImageFunc send_image_;
    IsReadyFunc is_ready_;
    GetStatusFunc get_status_;
};
```

### Function Details

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `initialize` | dll_path | bool | Loads printer DLL, resolves functions |
| `close` | - | void | Unloads DLL, releases resources |
| `sendImage` | RGBImage | bool | Sends image to printer queue |
| `isReady` | - | bool | Checks printer ready status |
| `getStatus` | - | string | Gets human-readable status |

### DLL Requirements

The printer DLL must export:
```cpp
extern "C" {
    bool PrinterSendImage(const uint8_t* data, int width, int height, int channels);
    bool PrinterIsReady();
    const char* PrinterGetStatus();
}
```

---

## Python Bindings (alinify_bindings)

**Type:** pybind11 MODULE  
**Location:** `src/python_bindings/bindings.cpp`  
**Output:** `alinify_bindings.pyd` (Windows) or `.so` (Linux)  
**Dependencies:** All modules + pybind11

### Build Requirement

```bash
cmake -DBUILD_PYTHON_BINDINGS=ON ..
```

### Exposed Classes

| C++ Class | Python Class | Status |
|-----------|--------------|--------|
| `GidelCamera` | `alinify.GidelCamera` | ✅ Active |
| `StripStitcher` | `alinify.StripStitcher` | ✅ Active |
| `ImageProcessor` | `alinify.ImageProcessor` | ✅ Active |
| `PrinterInterface` | `alinify.PrinterInterface` | ✅ Active |
| `ElastixWrapper` | - | ❌ Disabled (use Python ITK) |
| `CudaWarper` | - | ❌ Disabled (use PyTorch) |

### Python Usage Examples

#### Camera Control

```python
import alinify_bindings as alinify

# Camera setup
camera = alinify.GidelCamera()
config = alinify.CameraConfig()
config.width = 4096
config.frequency_hz = 10000
camera.initialize(config)

# Callback for frames
def on_frame(image, strip_id, position):
    print(f"Got frame {strip_id}")

camera.set_image_callback(on_frame)
camera.start_acquisition()
# ... capture ...
camera.stop_acquisition()
```

#### Strip Stitching

```python
import alinify_bindings as alinify
import numpy as np

stitcher = alinify.StripStitcher()
stitcher.initialize(10)

# Add strips (numpy arrays)
for i, strip_array in enumerate(strips):
    strip = alinify.ScanStrip()
    strip.image = strip_array
    strip.strip_id = i
    strip.position_mm = i * 40.0
    strip.overlap_percent = 10.0
    stitcher.addStrip(strip)

# Get result
result = stitcher.getStitchedImage()  # Returns numpy array

# Check quality
stats = stitcher.getStatistics()
print(f"Mean shift: ({stats.mean_shift_x}, {stats.mean_shift_y})")
```

#### Image Preprocessing

```python
import alinify_bindings as alinify
import numpy as np

# All methods are static
processor = alinify.ImageProcessor

# Individual operations
blurred = processor.gaussianBlur(image, 5)
enhanced = processor.histogramEqualization(image)
sharpened = processor.unsharpMask(image, 1.5, 1.0, 0)

# Pipeline processing
pipeline = ["gaussian:3", "histogram_eq", "unsharp:1.5:1.0:0"]
result = processor.applyPipeline(image, pipeline)
```

#### Printer Interface

```python
import alinify_bindings as alinify

printer = alinify.PrinterInterface()
if printer.initialize("C:/PrinterSDK/printer.dll"):
    if printer.isReady():
        # RGB image as numpy array (H, W, 3)
        success = printer.sendImage(rgb_image)
        print(f"Send status: {printer.getStatus()}")
    printer.close()
```

### Data Type Conversions

| C++ Type | Python Type | Notes |
|----------|-------------|-------|
| `GrayImage` | `numpy.ndarray` (uint8, 2D) | Automatic conversion |
| `RGBImage` | `numpy.ndarray` (uint8, 3D) | Shape: (H, W, 3) |
| `FloatImage` | `numpy.ndarray` (float32, 2D) | For deformation fields |
| `std::vector<T>` | `list[T]` or `numpy.ndarray` | Depends on context |
| `std::string` | `str` | UTF-8 encoded |

---

## Building the Modules

### Prerequisites

| Dependency | Version | Required For |
|------------|---------|--------------|
| CMake | 3.15+ | Build system |
| Visual Studio | 2019+ | Windows compiler |
| ITK | 5.x | Preprocessing, registration |
| OpenCV | 4.x | Image processing |
| pybind11 | 2.10+ | Python bindings (optional) |
| Python | 3.8+ | Python bindings (optional) |
| Gidel SDK | 4.x | Camera module |

### Build Commands

#### Windows (PowerShell)

```powershell
# Create build directory
mkdir build
cd build

# Configure (all options)
cmake -G "Visual Studio 16 2019" -A x64 `
      -DBUILD_PYTHON_BINDINGS=ON `
      -DBUILD_TESTS=ON `
      -DOpenCV_DIR="C:/opencv/build" `
      -DITK_DIR="C:/ITK/build" `
      -Dpybind11_DIR="C:/pybind11/share/cmake/pybind11" `
      ..

# Build Release
cmake --build . --config Release

# Install
cmake --install . --prefix ../install
```

#### Using build.ps1

```powershell
# Quick build script
.\build.ps1
```

### Build Outputs

After successful build:
```
install/
├── bin/
│   └── alinify_bindings.pyd    # Python module
├── lib/
│   ├── alinify_camera.lib
│   ├── alinify_preprocessing.lib
│   ├── alinify_stitching.lib
│   └── alinify_printer.lib
└── include/
    └── alinify/
        ├── types.h
        ├── gidel_camera.h
        ├── image_processor.h
        ├── strip_stitcher.h
        └── printer_interface.h
```

---

## Integration Examples

### Complete Scanning Pipeline (C++)

```cpp
#include <alinify/gidel_camera.h>
#include <alinify/strip_stitcher.h>
#include <alinify/image_processor.h>
#include <alinify/printer_interface.h>

int main() {
    // Initialize components
    GidelCamera camera;
    CameraConfig config;
    config.width = 4096;
    config.frequency_hz = 10000;
    camera.initialize(config);
    
    StripStitcher stitcher;
    stitcher.initialize(10);
    
    PrinterInterface printer;
    printer.initialize("printer.dll");
    
    // Set up callback to process strips
    camera.setImageCallback([&](const ScanStrip& strip) {
        // Preprocess
        auto processed = ImageProcessor::histogramEqualization(strip.image);
        processed = ImageProcessor::unsharpMask(processed, 1.0, 1.0, 0);
        
        // Add to stitcher
        ScanStrip proc_strip = strip;
        proc_strip.image = processed;
        stitcher.addStrip(proc_strip);
    });
    
    // Run scan
    camera.startAcquisition();
    // ... wait for scan complete ...
    camera.stopAcquisition();
    
    // Get stitched result
    GrayImage result = stitcher.getStitchedImage();
    
    // Convert to RGB and print
    RGBImage rgb = convertToRGB(result);  // Application-specific
    printer.sendImage(rgb);
    
    return 0;
}
```

### Complete Pipeline (Python)

```python
import alinify_bindings as alinify
import numpy as np

# Initialize
camera = alinify.GidelCamera()
config = alinify.CameraConfig()
config.width = 4096
camera.initialize(config)

stitcher = alinify.StripStitcher()
stitcher.initialize(10)

strips = []

def on_frame(image, strip_id, position):
    # Preprocess
    processed = alinify.ImageProcessor.histogramEqualization(image)
    processed = alinify.ImageProcessor.unsharpMask(processed, 1.0, 1.0, 0)
    
    # Create strip
    strip = alinify.ScanStrip()
    strip.image = processed
    strip.strip_id = strip_id
    strip.position_mm = position
    stitcher.addStrip(strip)

camera.set_image_callback(on_frame)
camera.start_acquisition()

# Wait for scan...
import time
time.sleep(10)

camera.stop_acquisition()

# Get result
result = stitcher.getStitchedImage()
print(f"Stitched image shape: {result.shape}")

# Check quality
stats = stitcher.getStatistics()
print(f"Alignment stats: {stats.strips_processed} strips, "
      f"mean shift: ({stats.mean_shift_x:.2f}, {stats.mean_shift_y:.2f})")
```

---

## Troubleshooting

### Common Build Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `ITK not found` | ITK not installed or path wrong | Set `ITK_DIR` to ITK build folder |
| `OpenCV not found` | OpenCV not installed | Set `OpenCV_DIR` to OpenCV build folder |
| `pybind11 not found` | pybind11 not installed | `pip install pybind11` or set `pybind11_DIR` |
| `LINK error: ProcFgApi.lib` | Gidel SDK not installed | Install Gidel SDK, add to PATH |

### Runtime Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `ImportError: alinify_bindings` | DLL not found | Add install/bin to PYTHONPATH |
| `Camera init failed` | No hardware | Check Gidel device manager |
| `Printer DLL not found` | Wrong path | Verify DLL path in initialize() |

---

## Module Dependency Graph

```
┌─────────────────────────────────────────────────────────┐
│                   alinify_bindings                       │
│                   (Python Interface)                     │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│alinify_camera │   │alinify_stitch │   │alinify_printer│
│   (STATIC)    │   │   (STATIC)    │   │   (STATIC)    │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        │           ┌───────┴───────┐           │
        │           │               │           │
        ▼           ▼               ▼           ▼
┌───────────────────────────────────────────────────────┐
│                     alinify_core                       │
│                  (INTERFACE/Headers)                   │
└───────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐        ┌──────────┐        ┌──────────┐
  │   ITK    │        │  OpenCV  │        │ Gidel SDK│
  └──────────┘        └──────────┘        └──────────┘
```

---

*Document Version: 1.0*  
*Last Updated: 2025*  
*Maintained by Alinify Development Team*
