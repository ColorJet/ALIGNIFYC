# Camera Integration Guide

## Overview
The Gidel camera integration for the Alinify system has been implemented in the Python GUI. The camera control is now functional, connecting the GUI buttons to the C++ camera module via Python bindings.

## What Was Implemented

### 1. **Camera Initialization** (`initializeCamera()`)
- Automatically initializes Gidel camera after UI is ready
- Loads configuration from `config/system_config.yaml`
- Parses nested YAML structure (resolution, frequency, FOV, pixel size)
- Sets Gidel-specific config file path
- Provides detailed logging and error messages

### 2. **Start Camera** (`startCamera()`)
- Connected to "Start Camera" menu item and button
- Validates that C++ bindings are available
- Checks camera initialization status
- Starts acquisition via C++ `GidelCamera::startAcquisition()`
- Updates UI state (disables start button, shows status)
- Starts polling timer to monitor acquisition

### 3. **Stop Camera** (`stopCamera()`)
- Stops camera acquisition cleanly
- Stops polling timer
- Updates UI state
- Handles errors gracefully

### 4. **Frame Polling** (`pollCameraFrames()`)
- Periodically checks if camera is still acquiring
- Placeholder for actual frame retrieval
- Detects unexpected acquisition stop

### 5. **Configuration Loading**
- Reads camera settings from `config/system_config.yaml`:
  - Resolution (width x height)
  - Frequency (Hz)
  - Bit depth
  - Pixel size (mm)
  - FOV width (mm)
  - Gidel config file path

## Current Status

### ✅ Completed
- Camera instance creation and initialization
- Configuration loading from YAML
- Start/Stop camera methods
- Error handling and user feedback
- UI integration (buttons, status messages, logging)

### ⚠️ Requires C++ Build
The camera functionality **requires the C++ bindings to be built**:

```powershell
# Navigate to build directory
cd d:\Alinify20251113\Alinify\build

# Run CMake configuration
cmake ..

# Build the project
cmake --build . --config Release

# Install Python bindings
pip install -e ..
```

### 🔧 Next Steps for Full Integration

#### 1. **Frame Callback Implementation**
The current implementation uses polling (`pollCameraFrames()`), but the ideal approach is callback-based:

**In `src/python_bindings/bindings.cpp`**, add:
```cpp
.def("set_image_callback", [](camera::GidelCamera& cam, py::function callback) {
    cam.setImageCallback([callback](const ScanStrip& strip) {
        // Convert Image to numpy array
        py::array_t<byte_t> np_array({strip.image.height, strip.image.width}, 
                                     strip.image.ptr());
        // Call Python callback
        callback(np_array, strip.strip_id, strip.physical_position);
    });
})
```

**In `main_gui.py`**, add callback:
```python
def onCameraFrame(self, image_array, strip_id, position):
    """Called when new camera frame arrives"""
    # Convert numpy array to QImage and display
    self.camera_image = image_array
    self.updateCameraDisplay()
```

#### 2. **Image Display**
Add real-time display of camera frames in the layer canvas:
```python
def updateCameraDisplay(self):
    """Update camera layer with latest frame"""
    if self.camera_image is not None:
        # Convert to RGB for display
        img_rgb = cv2.cvtColor(self.camera_image, cv2.COLOR_GRAY2RGB)
        
        # Update Camera layer
        self.layer_canvas.updateLayer("Camera", img_rgb)
```

#### 3. **Frame Stitching**
Integrate with the strip stitcher for line-scan imaging:
```python
# Initialize stitcher
self.stitcher = alinify.StripStitcher()
self.stitcher.initialize(scanning_params)

def onCameraFrame(self, image_array, strip_id, position):
    # Add strip to stitcher
    self.stitcher.add_strip(image_array, position)
    
    # Get stitched result
    stitched = self.stitcher.get_stitched_image()
    self.updateCameraDisplay()
```

## Testing Without Hardware

For testing without the Gidel camera hardware:

### Option 1: Mock Camera
Create a mock camera for testing:
```python
class MockCamera:
    def __init__(self):
        self.acquiring = False
    
    def initialize(self, config):
        return StatusCode.SUCCESS
    
    def start_acquisition(self):
        self.acquiring = True
        return StatusCode.SUCCESS
    
    def stop_acquisition(self):
        self.acquiring = False
        return StatusCode.SUCCESS
    
    def is_acquiring(self):
        return self.acquiring
```

### Option 2: Load Test Images
Use "Load Camera Image" to load test images from files instead of live camera.

## Configuration Example

The system reads from `config/system_config.yaml`:

```yaml
camera:
  type: gidel_cameralink
  resolution:
    width: 4096
    height: 1
  frequency: 10000  # Hz
  bit_depth: 8
  pixel_size: 0.010256  # mm
  fov:
    width: 42.0  # mm
  gidel:
    board_id: 0
    config_file: config/camera/FGConfig.gxfg
    buffer_count: 30
    buffer_size: 20971520
  trigger:
    mode: auto
    frequency: 10000
    encoder_step: 0.0
```

## Error Messages and Troubleshooting

### "C++ bindings not available"
**Solution**: Build and install the C++ project:
```powershell
cd build
cmake .. && cmake --build . --config Release
pip install -e ..
```

### "Camera not initialized"
**Solution**: Check:
1. Gidel frame grabber drivers are installed
2. Camera is physically connected
3. Config file path is correct (`config/camera/FGConfig.gxfg`)
4. Board ID matches your hardware

### "Failed to start acquisition"
**Solution**: 
1. Verify camera is not already in use by another application
2. Check Gidel configuration file is valid
3. Ensure sufficient system memory for buffers
4. Check camera power and connection

## Architecture

```
Python GUI (main_gui.py)
    ↓
Python Bindings (alinify_bindings)
    ↓
C++ Camera Module (gidel_camera.cpp)
    ↓
Gidel API (ProcFgApi)
    ↓
Frame Grabber Hardware
    ↓
Camera
```

## Comparison with FgExample.cpp

Your `gidel_camera.cpp` provides:
- ✅ Object-oriented, maintainable design
- ✅ Thread-safe buffer management
- ✅ Statistics tracking (FPS, frames)
- ✅ Extensible callbacks
- ✅ Error handling and logging
- ✅ Integration with larger system

FgExample.cpp provides:
- ✅ Image saving (single PNG, clubbed)
- ✅ OpenGL display
- ✅ Progress animation
- ✅ Multiple capture modes

**Recommendation**: Your camera module is better for production. Consider adding FgExample's image saving features if needed.

## Next Actions

1. **Build C++ Project**: Compile bindings to enable camera
2. **Test Initialization**: Run GUI and check "Log" tab for camera messages
3. **Test Start/Stop**: Click camera buttons and monitor status
4. **Add Callbacks**: Implement frame callback for live display
5. **Test with Hardware**: Connect camera and verify acquisition
6. **Add Stitching**: Integrate strip stitcher for full-width images

---

**Status**: Camera integration code is complete and ready for testing once C++ bindings are built.
