# Gidel Camera Implementation Guide
## Alinify Fabric Registration System

**Document Version**: 1.0  
**Date**: January 2025  
**Hardware**: Gidel CameraLink Frame Grabber + Line Scan Camera

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Hardware Architecture](#hardware-architecture)
3. [Software Components](#software-components)
4. [Configuration](#configuration)
5. [Operation Guide](#operation-guide)
6. [Debugging Guide](#debugging-guide)
7. [Performance Tuning](#performance-tuning)
8. [Troubleshooting](#troubleshooting)

---

## 1. System Overview

### Purpose
The camera subsystem captures high-resolution fabric images for pattern registration. It uses a **line scan camera** connected via **CameraLink** to a **Gidel frame grabber**.

### Key Specifications
- **Camera Type**: Line scan (CameraLink interface)
- **Frame Grabber**: Gidel Proc/InfiniVision
- **Tap Configuration**: 8-tap (80-bit, 64-bit data path)
- **Image Format**: Mono 8-bit (or 10/12/16-bit)
- **Strip Size**: Up to 4096×18432 pixels (72MB buffers)
- **Grab Mode**: LatestFrame (real-time) or NextFrame (sequential)

### Architecture Diagram

```
┌─────────────────┐     CameraLink     ┌──────────────────┐
│   Line Scan     │ ◄─────────────────►│  Gidel Frame     │
│   Camera        │    8-tap 80-bit    │  Grabber         │
│                 │                    │  (Proc API)      │
└─────────────────┘                    └────────┬─────────┘
                                                │
                                                │ PCIe
                                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Host PC                              │
│  ┌─────────────────┐    ┌─────────────────────────────┐│
│  │  GidelCamera    │◄──►│  30× 72MB Ring Buffers      ││
│  │  (C++ Class)    │    │  (DMA Transfer)             ││
│  └────────┬────────┘    └─────────────────────────────┘│
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐    ┌─────────────────────────────┐│
│  │  Processing     │◄──►│  ScanStrip Queue            ││
│  │  Thread         │    │  (Thread-safe)              ││
│  └────────┬────────┘    └─────────────────────────────┘│
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                   │
│  │  Python GUI     │◄──── Image Callback               │
│  │  (PySide6)      │                                   │
│  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Architecture

### 2.1 CameraLink Interface

| Signal | Description |
|--------|-------------|
| FVAL | Frame Valid - indicates valid frame data |
| LVAL | Line Valid - indicates valid line data |
| DVAL | Data Valid - indicates valid pixel data |
| CLK | Pixel clock from camera |

### 2.2 Tap Configuration

The camera supports multiple tap configurations:

| Taps | Data Path | Bandwidth | Use Case |
|------|-----------|-----------|----------|
| 1 | 8-bit | Low | Basic debugging |
| 2 | 16-bit | Medium | Default after power cycle ⚠️ |
| 4 | 32-bit | High | Medium-speed scanning |
| **8** | **64-bit** | **Maximum** | **Production line scan** ✓ |

**⚠️ CRITICAL**: Camera may reset to 2-tap after power cycle. Always verify!

### 2.3 Buffer Management

- **Buffer Size**: 72MB each (`0x4E50000` bytes)
- **Buffer Count**: 30 buffers (ring buffer)
- **Total Memory**: ~2.1 GB reserved for frame grabber
- **DMA**: Direct Memory Access for zero-copy transfer

---

## 3. Software Components

### 3.1 C++ Implementation

**File**: `src/camera/gidel_camera.cpp`  
**Header**: `include/alinify/camera/gidel_camera.h`

#### Class: `GidelCamera`

```cpp
class GidelCamera : public ICameraInterface {
public:
    // Initialization
    StatusCode initialize(const CameraConfig& config);
    StatusCode setConfigFile(const std::string& config_file);
    
    // Acquisition control
    StatusCode startAcquisition();
    StatusCode stopAcquisition();
    bool isAcquiring() const;
    
    // Triggering
    StatusCode setTriggerMode(const std::string& mode, int frequency);
    StatusCode setEncoderTrigger(double step);
    
    // Callbacks
    void setImageCallback(ImageCallback callback);
    void setErrorCallback(ErrorCallback callback);
    
    // Statistics
    Statistics getStatistics() const;
};
```

#### Key Methods

##### `initialize()`
```cpp
StatusCode GidelCamera::initialize(const CameraConfig& config) {
    // 1. Create ProcFg API instance
    fg_api_ = new fg::CProcFgApi();
    
    // 2. Initialize with camera detection
    fg::CAMERA_INFO cameras;
    fg_api_->Init(cameras);
    
    // 3. Load XML configuration file
    fg_api_->LoadConfig(config_file_.c_str());
    
    // 4. Allocate DMA buffers (30 × 72MB)
    for (int i = 0; i < 30; i++) {
        fg::BUFFER_HANDLE handle = fg_api_->AnnounceBuffer(0x4E50000, nullptr, this);
        fg_api_->QueueBuffer(handle);
        buffer_handles_.push_back(handle);
    }
    
    // 5. Set callbacks for async frame delivery
    fg_api_->SetImageCallBack(grabberCallback);
    fg_api_->SetFgStateCallBack(statusCallback, 100);
}
```

##### `startAcquisition()`
```cpp
StatusCode GidelCamera::startAcquisition() {
    // 1. Reset statistics
    stats_ = {};
    
    // 2. Start processing thread
    should_stop_ = false;
    processing_thread_ = std::thread(&GidelCamera::processingThread, this);
    
    // 3. Start grabbing (triggers DMA transfers)
    fg_api_->Grab();
    
    is_acquiring_ = true;
}
```

##### `processBuffer()` - Frame Callback
```cpp
void GidelCamera::processBuffer(fg::BUFFER_DATA buffer_info) {
    // 1. Update statistics (FPS, frame count)
    stats_.frames_received++;
    
    // 2. Create ScanStrip with metadata
    ScanStrip strip;
    strip.strip_id = current_strip_id_++;
    strip.physical_position = current_position_mm_;
    
    // 3. Copy image data from DMA buffer
    // Note: Uses actual buffer dimensions from frame grabber
    const int frame_height = buffer_info.BufferInfoHeight;
    const int frame_width = buffer_info.BufferInfoWidth;
    strip.image = Image<byte_t>(frame_width, frame_height, 1, config_.bit_depth);
    std::memcpy(strip.image.ptr(), buffer_ptr + buffer_info.Offset, data_size);
    
    // 4. Queue for async processing
    strip_queue_.push(strip);
    queue_cv_.notify_one();
    
    // 5. Re-queue buffer for next frame
    fg_api_->QueueBuffer(prev_handle);
}
```

### 3.2 Python GUI Integration

**Files**:
- `gui/main_gui.py` - Main window with camera controls
- `gui/widgets/camera_config_dialog.py` - Configuration dialog
- `gui/widgets/camera_config_manager.py` - Persistent settings

#### Starting Camera from GUI

```python
@Slot()
def startCamera(self):
    """Start camera acquisition"""
    if not HAS_BINDINGS:
        # C++ bindings not available
        return
        
    if not self.camera:
        # Camera not initialized
        return
        
    # Start acquisition
    status = self.camera.start_acquisition()
    
    if status == alinify.StatusCode.SUCCESS:
        self.is_camera_acquiring = True
        # Start polling timer for frame updates
        self.camera_poll_timer.start(100)  # 10 Hz polling
```

#### Camera Configuration Dialog

The dialog provides GenTL-style interface for:

| Tab | Settings |
|-----|----------|
| **CameraLink** | Tap config, format, bit depth, signal control |
| **Acquisition** | Grab mode, trigger, frame count |
| **ROI** | Region of interest settings |
| **Advanced** | Logging, output format |

---

## 4. Configuration

### 4.1 XML Configuration File

**Path**: `config/camera/FGConfig.gxfg`

```xml
<?xml version='1.0' encoding='utf-8'?>
<FG>
    <ROI>
        <Feature Name="Width">0</Feature>      <!-- 0 = use camera max -->
        <Feature Name="Height">0</Feature>
        <Feature Name="OffsetX">0</Feature>
        <Feature Name="OffsetY">0</Feature>
    </ROI>
    
    <CameraLink>
        <Feature Name="NumParallelPixels">8</Feature>  <!-- CRITICAL: Must be 8 -->
        <Feature Name="NumZones">1</Feature>
        <Feature Name="BitsPerColor">8</Feature>
        <Feature Name="Format">Mono</Feature>
    </CameraLink>
    
    <Acquisition>
        <Feature Name="GrabMode">LatestFrame</Feature>
        <Feature Name="ExternalSource">false</Feature>
    </Acquisition>
</FG>
```

### 4.2 Critical Settings

| Setting | Required Value | Why |
|---------|----------------|-----|
| `NumParallelPixels` | **8** | Maximum bandwidth for line scan |
| `Format` | **Mono** | Grayscale fabric imaging |
| `BitsPerColor` | **8** | Standard 8-bit depth |
| `GrabMode` | **LatestFrame** | Real-time, skip dropped frames |

### 4.3 Auto-Restore Feature

The `CameraConfigManager` class monitors for tap configuration resets:

```python
def check_and_restore_taps(self, current_taps: int) -> Optional[int]:
    """Check if tap configuration has changed and restore if needed"""
    expected_taps = self.critical_settings['num_parallel_pixels']
    
    if current_taps != expected_taps:
        logger.warning(f"Tap mismatch! Current: {current_taps}, Expected: {expected_taps}")
        return expected_taps  # Return correct value to restore
        
    return None
```

---

## 5. Operation Guide

### 5.1 Starting Acquisition

**From GUI**:
1. Click **Camera → Start Camera** (or toolbar button)
2. Verify "Camera acquiring" status
3. Watch for frames in layer canvas

**From Code**:
```python
# Python
status = camera.start_acquisition()
if status == alinify.StatusCode.SUCCESS:
    print("Acquisition started")
```

```cpp
// C++
StatusCode status = camera->startAcquisition();
if (status == StatusCode::SUCCESS) {
    LOG_INFO("Acquisition started");
}
```

### 5.2 Stopping Acquisition

**From GUI**:
1. Click **Camera → Stop Camera**
2. Wait for "Acquisition stopped" message

**From Code**:
```python
camera.stop_acquisition()
```

### 5.3 Configuring Camera

**From GUI**:
1. Click **Camera → Camera Configuration...**
2. Set parameters in dialog tabs
3. Click **Apply** to save and restart camera

### 5.4 Trigger Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `auto` | Internal timer trigger | Testing, calibration |
| `external` | External TTL trigger | Production encoder sync |
| `encoder` | Encoder-based trigger | Moving web/fabric |

```cpp
// Set trigger mode
camera->setTriggerMode("external", 10000);  // 10 kHz

// Or encoder trigger
camera->setEncoderTrigger(0.1);  // 0.1mm step
```

---

## 6. Debugging Guide

### 6.1 Enable Verbose Logging

**In XML Config**:
```xml
<Log>
    <Feature Name="LogVerbosity">4</Feature>  <!-- 4 = Debug -->
    <Feature Name="LogSizeMB">20</Feature>
</Log>
```

**Log Levels**:
| Value | Level | Description |
|-------|-------|-------------|
| 0 | Off | No logging |
| 1 | Error | Errors only |
| 2 | Warning | Warnings and errors |
| 3 | Info | Normal operation |
| 4 | Debug | Detailed debugging |

### 6.2 Common Debug Points

#### Check if camera is acquiring:
```cpp
// C++
bool is_acquiring = camera->isAcquiring();
LOG_DEBUG("Camera acquiring: ", is_acquiring);
```

```python
# Python
print(f"Camera acquiring: {camera.is_acquiring()}")
```

#### Check statistics:
```cpp
auto stats = camera->getStatistics();
LOG_INFO("Frames: ", stats.frames_received, ", FPS: ", stats.fps);
```

#### Check buffer status:
```cpp
// In processBuffer()
LOG_DEBUG("Buffer info - Width: ", buffer_info.BufferInfoWidth,
          ", Height: ", buffer_info.BufferInfoHeight,
          ", Offset: ", buffer_info.Offset);
```

### 6.3 Debug Callbacks

Add debug callback to track errors:

```cpp
camera->setErrorCallback([](const std::string& error) {
    LOG_ERROR("Camera error: ", error);
    // Optional: trigger alert, save diagnostic info
});
```

### 6.4 Frame Grabber Status Monitoring

The status callback provides real-time state:

```cpp
void GidelCamera::statusCallback(fg::CURRENT_STATE state) {
    // state.Received = total frames received
    // state.Fps = current frames per second
    // state.State = current state (STATE_ERROR, etc.)
    // state.ErrorMessage = error description if STATE_ERROR
    
    if (state.State == fg::STATE_ERROR) {
        LOG_ERROR("Frame grabber error: ", state.ErrorMessage);
    }
}
```

---

## 7. Performance Tuning

### 7.1 Buffer Optimization

| Parameter | Default | Tuning |
|-----------|---------|--------|
| Buffer size | 72MB | Match to max strip size |
| Buffer count | 30 | Increase for high FPS |
| Queue depth | Unlimited | Limit to prevent memory overflow |

```cpp
// Adjust buffer size for your image dimensions
const size_t buffer_size = width * height * bytes_per_pixel * 1.5;  // 50% overhead
```

### 7.2 Thread Priority

For real-time performance:

```cpp
// In processingThread()
#ifdef _WIN32
SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL);
#endif
```

### 7.3 Memory Optimization

Avoid memory copies:

```cpp
// Direct buffer access (zero-copy)
strip.image.setData(buffer_ptr + buffer_info.Offset, 
                    frame_width * frame_height);

// Instead of:
// std::memcpy(strip.image.ptr(), buffer_ptr, size);  // Extra copy!
```

### 7.4 Grab Mode Selection

| Mode | Latency | Use When |
|------|---------|----------|
| `LatestFrame` | Minimal | Real-time display, skip old frames |
| `NextFrame` | Higher | Sequential processing, no frame skipping |

---

## 8. Troubleshooting

### 8.1 Camera Won't Start

**Symptoms**: `ERROR_CAMERA_START` status

**Checklist**:
1. ✓ Check CameraLink cable connection
2. ✓ Verify power to camera
3. ✓ Check frame grabber driver installed
4. ✓ Verify config file path exists
5. ✓ Check for exclusive access conflicts

**Debug**:
```cpp
char error_desc[1024];
fg_api_->GetLastError(error_desc);
LOG_ERROR("Grab failed: ", error_desc);
```

### 8.2 Tap Configuration Reset

**Symptoms**: Camera works but bandwidth is low

**Cause**: Camera resets to 2-tap after power cycle

**Solution**:
1. Check tap count on startup
2. Restore to 8-tap if different
3. Enable "Force 8-tap on power-on" in GUI

```python
# In camera init
config_manager = CameraConfigManager()
if config_manager.check_and_restore_taps(current_taps) is not None:
    # Reconfigure camera to 8-tap
    save_and_reload_config(num_parallel_pixels=8)
```

### 8.3 Dropped Frames

**Symptoms**: `frames_dropped` increasing in statistics

**Causes**:
- CPU overloaded
- Buffer queue full
- Slow callback processing

**Solutions**:
1. Increase buffer count
2. Use `LatestFrame` grab mode
3. Optimize callback processing
4. Add frame skip logic

```cpp
// Skip frames when queue is full
if (strip_queue_.size() > MAX_QUEUE_SIZE) {
    stats_.frames_dropped++;
    return;  // Don't process this frame
}
```

### 8.4 Memory Allocation Failure

**Symptoms**: `AnnounceBuffer()` returns null

**Cause**: Insufficient contiguous memory

**Solutions**:
1. Reduce buffer count
2. Reduce buffer size
3. Close other applications
4. Check for memory leaks

### 8.5 Image Quality Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Dark image | Wrong exposure | Adjust camera exposure |
| Banding | Timing issue | Check FVAL/DVAL signals |
| Noise | Electrical interference | Shield cables, ground properly |
| Shifted columns | Tap misalignment | Recalibrate tap timing |

### 8.6 Python Binding Not Available

**Symptoms**: `HAS_BINDINGS = False` in GUI

**Solutions**:
1. Build C++ project: `cmake --build build --config Release`
2. Install Python package: `pip install -e .`
3. Check pybind11 module exists: `import alinify`

---

## Appendix A: Status Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | `SUCCESS` | Operation completed |
| 1 | `ERROR_CAMERA_INIT` | Initialization failed |
| 2 | `ERROR_CAMERA_START` | Could not start acquisition |
| 3 | `ERROR_CAMERA_STOP` | Could not stop acquisition |
| 4 | `ERROR_CAMERA_CONFIG` | Configuration error |
| 5 | `ERROR_BUFFER_ALLOC` | Buffer allocation failed |

## Appendix B: File Locations

| File | Purpose |
|------|---------|
| `src/camera/gidel_camera.cpp` | Main C++ implementation |
| `include/alinify/camera/gidel_camera.h` | C++ header |
| `include/alinify/camera/camera_interface.h` | Abstract interface |
| `config/camera/FGConfig.gxfg` | XML configuration |
| `gui/widgets/camera_config_dialog.py` | Configuration GUI |
| `gui/widgets/camera_config_manager.py` | Settings persistence |

## Appendix C: Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| Gidel ProcFgApi | 4.x+ | Frame grabber control |
| g_InfiniVision | - | Multi-camera support |
| pybind11 | 2.10+ | Python bindings |
| PySide6 | 6.x | GUI framework |

---

## Appendix D: Python Bindings Reference

### GidelCamera Class

```python
import alinify_bindings as alinify

# Create camera instance
camera = alinify.GidelCamera()

# Configuration
config = alinify.CameraConfig()
config.width = 4096
config.height = 1
config.frequency_hz = 10000
config.bit_depth = 8
config.pixel_size_mm = 0.010256
config.fov_width_mm = 42.0

# Initialize
status = camera.initialize(config)
camera.set_config_file("config/camera/FGConfig.gxfg")

# Set image callback
def on_frame(image_array, strip_id, position_mm):
    """Callback receives numpy array, strip ID, and position"""
    print(f"Frame {strip_id} at {position_mm}mm, shape: {image_array.shape}")
    # Process image...

camera.set_image_callback(on_frame)

# Start/stop acquisition
camera.start_acquisition()
# ... capture frames ...
camera.stop_acquisition()

# Get statistics
stats = camera.get_statistics()
print(f"Frames: {stats.frames_received}, FPS: {stats.fps}")

# Trigger mode
camera.set_trigger_mode("external", 10000)  # External trigger at 10kHz
```

### CameraStatistics Struct

| Field | Type | Description |
|-------|------|-------------|
| `frames_received` | int | Total frames captured |
| `frames_dropped` | int | Frames dropped due to buffer overflow |
| `fps` | float | Current frames per second |
| `temperature` | float | Camera temperature (if available) |

### CameraConfig Struct

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `width` | int | 4096 | Image width in pixels |
| `height` | int | 1 | Lines per strip (line scan) |
| `frequency_hz` | int | 10000 | Line scan frequency |
| `bit_depth` | int | 8 | Bits per pixel |
| `pixel_size_mm` | float | 0.010256 | Physical pixel size |
| `fov_width_mm` | float | 42.0 | Field of view width |

---

*Document maintained by Alinify Development Team*
