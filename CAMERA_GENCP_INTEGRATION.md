# Camera Configuration - GenCP Integration Guide

**Using Gidel's GenICam Camera Protocol for Configuration**

---

## Overview

The GenCPConfigExample.cpp shows the **proper** way to read/write camera configurations using GenICam protocol, which is more sophisticated than directly editing XML files.

---

## GenCP vs Direct XML Editing

### Current Approach (Phase 1) ✅
```python
# Direct XML editing via camera_config_manager.py
config_manager = CameraConfigManager()
config = config_manager.load_config()  # Parse FGConfig.gxfg
config['num_parallel_pixels'] = 8
config_manager.save_config(config)     # Write XML
```

**Pros:**
- ✅ Works immediately
- ✅ No additional SDK dependencies
- ✅ Simple to implement
- ✅ Full control over file format

**Cons:**
- ⚠️ Bypasses camera's internal validation
- ⚠️ Changes require camera restart
- ⚠️ No live feature discovery
- ⚠️ Manual XML structure management

---

### GenCP Approach (Phase 2 - Recommended) 🎯

```cpp
// From GenCPConfigExample.cpp
GidelInCam::CGenCPInCam gencp;
gencp.Open(camera_id);

// Read camera features
int64_t width, height;
gencp.GetIntValue(camera_id, "Width", width);
gencp.GetIntValue(camera_id, "Height", height);

// Save camera configuration
gencp.SaveXML(camera_id, "camera.xml");

// Get XML programmatically
std::vector<uint8_t> buf;
int size = 0;
gencp.GetXML(camera_id, nullptr, size);  // Get size
buf.resize(size);
gencp.GetXML(camera_id, buf.data(), size);  // Get data
```

**Pros:**
- ✅ GenICam standard protocol
- ✅ Camera validates all settings
- ✅ Live feature discovery
- ✅ Read/write access modes
- ✅ Real-time configuration updates
- ✅ Cross-vendor compatibility

**Cons:**
- ⚠️ Requires GenCP SDK integration
- ⚠️ More complex implementation
- ⚠️ Need to handle compressed XML (ZIP format)

---

## Key Components from GenCPConfigExample

### 1. **Opening GenCP Interface**

```cpp
GidelInCam::CGenCPInCam gencp;

if (!gencp.Open(camera_id)) {
    std::cout << gencp.GetErrorMsg() << std::endl;
    return 1;
}
```

### 2. **Reading Features**

```cpp
// Integer features
int64_t value;
gencp.GetIntValue(camera_id, "Width", value);
gencp.GetIntValue(camera_id, "Height", value);
gencp.GetIntValue(camera_id, "NumParallelPixels", value);  // TAP COUNT!

// String features
std::string format;
gencp.GetStringValue(camera_id, "PixelFormat", format);

// Boolean features
bool enable;
gencp.GetBoolValue(camera_id, "AcquisitionFrameRateEnable", enable);
```

### 3. **Writing Features**

```cpp
// Set tap configuration
gencp.SetIntValue(camera_id, "NumParallelPixels", 8);

// Set pixel format
gencp.SetStringValue(camera_id, "PixelFormat", "Mono8");

// Enable feature
gencp.SetBoolValue(camera_id, "AcquisitionFrameRateEnable", true);
```

### 4. **Saving Configuration**

```cpp
// Save camera's internal configuration to XML
const char* xmlPath = "camera_config.xml";
bool saved = gencp.SaveXML(camera_id, xmlPath);

// Or get XML programmatically
std::vector<uint8_t> xmlBuffer;
int xmlSize = 0;
gencp.GetXML(camera_id, nullptr, xmlSize);  // Get required size
xmlBuffer.resize(xmlSize);
gencp.GetXML(camera_id, xmlBuffer.data(), xmlSize);  // Get XML data
```

### 5. **Feature Discovery**

```cpp
// The camera returns an XML with all features
// Parse XML to find:
// - Feature names (Name="...")
// - Access modes (AccessMode="RO" | "RW")
// - Current values
// - Valid ranges

// Example XML structure:
// <Integer Name="NumParallelPixels">
//   <AccessMode>RW</AccessMode>
//   <Value>8</Value>
//   <Min>1</Min>
//   <Max>8</Max>
//   <Inc>1</Inc>
// </Integer>
```

---

## Integration Path

### Phase 1 (Current) ✅ DONE
- [x] Direct XML editing via Python
- [x] Configuration dialog UI
- [x] Manual backup/restore
- [x] Settings cache

### Phase 2 (Recommended) 🎯 NEXT
**Add GenCP C++ bindings:**

```cpp
// In src/camera/gidel_camera.h
class GidelCamera {
private:
    GidelInCam::CGenCPInCam* gencp_;
    
public:
    // GenCP methods
    bool initializeGenCP();
    bool setTapConfiguration(int taps);
    int getTapConfiguration();
    bool setPixelFormat(const std::string& format);
    std::string getPixelFormat();
    std::vector<std::string> getAvailableFeatures();
    bool saveConfigurationXML(const std::string& path);
    bool loadConfigurationXML(const std::string& path);
};
```

**Python bindings:**

```python
# In src/python_bindings/bindings.cpp
py::class_<camera::GidelCamera>(m, "GidelCamera")
    .def("set_tap_configuration", &camera::GidelCamera::setTapConfiguration)
    .def("get_tap_configuration", &camera::GidelCamera::getTapConfiguration)
    .def("set_pixel_format", &camera::GidelCamera::setPixelFormat)
    .def("get_pixel_format", &camera::GidelCamera::getPixelFormat)
    .def("get_available_features", &camera::GidelCamera::getAvailableFeatures)
    .def("save_config_xml", &camera::GidelCamera::saveConfigurationXML)
    .def("load_config_xml", &camera::GidelCamera::loadConfigurationXML);
```

**Usage in GUI:**

```python
# Auto-detect and restore tap configuration
if camera.is_initialized():
    current_taps = camera.get_tap_configuration()  # Read from hardware!
    
    if current_taps != 8:
        logger.warning(f"Tap configuration is {current_taps}, restoring to 8...")
        camera.set_tap_configuration(8)  # Write directly to camera!
        logger.info("✓ Tap configuration restored")
```

### Phase 3 (Advanced) 🚀 FUTURE
**Full GenICam Feature Browser:**

```python
class GenICamFeatureBrowser(QDialog):
    """Browse and edit all camera features via GenCP"""
    
    def __init__(self, camera):
        self.features = camera.get_available_features()
        
        for feature in self.features:
            # Create UI controls based on feature type
            if feature.type == "Integer":
                self.add_spinbox(feature)
            elif feature.type == "Enumeration":
                self.add_combobox(feature)
            elif feature.type == "Boolean":
                self.add_checkbox(feature)
            # ...
```

---

## Benefits of GenCP Integration

### 1. **Live Hardware Monitoring**
```python
# Periodic check (every 60 seconds)
def check_camera_health():
    current_taps = camera.get_tap_configuration()  # From hardware
    expected_taps = 8
    
    if current_taps != expected_taps:
        # Camera power cycled, auto-restore!
        camera.set_tap_configuration(expected_taps)
        log("Auto-restored tap configuration")
```

### 2. **Validation Before Save**
```python
# Camera validates the value
try:
    camera.set_tap_configuration(16)  # Invalid!
except ValueError as e:
    print(f"Error: {e}")  # "Invalid value: must be 1, 2, 4, or 8"
```

### 3. **Feature Discovery**
```python
# Discover what the camera supports
features = camera.get_available_features()
for feature in features:
    print(f"{feature.name}: {feature.type} ({feature.access})")
    
# Output:
# Width: Integer (RO)
# Height: Integer (RO)
# NumParallelPixels: Integer (RW)
# PixelFormat: Enumeration (RW)
# AcquisitionMode: Enumeration (RW)
# ...
```

### 4. **No Restart Required**
```python
# Changes apply immediately (for some features)
camera.set_pixel_format("Mono8")  # Takes effect now!
# (Note: Some features like taps may still require restart)
```

---

## Implementation Steps

### Step 1: Add GenCP Header
```cpp
// In src/camera/gidel_camera.cpp
#include <g_InCam.h>  // Gidel GenCP interface
```

### Step 2: Initialize GenCP
```cpp
bool GidelCamera::initializeGenCP() {
    gencp_ = new GidelInCam::CGenCPInCam();
    
    if (!gencp_->Open(1)) {  // Camera ID = 1
        LOG_ERROR("GenCP Open failed: ", gencp_->GetErrorMsg());
        delete gencp_;
        gencp_ = nullptr;
        return false;
    }
    
    LOG_INFO("GenCP interface initialized");
    return true;
}
```

### Step 3: Implement Tap Configuration
```cpp
int GidelCamera::getTapConfiguration() {
    if (!gencp_) {
        LOG_ERROR("GenCP not initialized");
        return -1;
    }
    
    int64_t taps = 0;
    if (!gencp_->GetIntValue(1, "NumParallelPixels", taps)) {
        LOG_ERROR("Failed to read NumParallelPixels");
        return -1;
    }
    
    return static_cast<int>(taps);
}

bool GidelCamera::setTapConfiguration(int taps) {
    if (!gencp_) {
        LOG_ERROR("GenCP not initialized");
        return false;
    }
    
    if (!gencp_->SetIntValue(1, "NumParallelPixels", taps)) {
        LOG_ERROR("Failed to set NumParallelPixels to ", taps);
        return false;
    }
    
    LOG_INFO("Tap configuration set to ", taps);
    return true;
}
```

### Step 4: Add Python Bindings
```cpp
// In bindings.cpp
.def("initialize_gencp", &camera::GidelCamera::initializeGenCP)
.def("get_tap_configuration", &camera::GidelCamera::getTapConfiguration)
.def("set_tap_configuration", &camera::GidelCamera::setTapConfiguration)
```

### Step 5: Update GUI
```python
# In main_gui.py - add periodic health check
def initializeCamera(self):
    # ... existing code ...
    
    # Initialize GenCP
    if self.camera.initialize_gencp():
        self.log("✓ GenCP interface ready")
        
        # Start health check timer
        self.config_check_timer = QTimer()
        self.config_check_timer.timeout.connect(self.checkCameraConfig)
        self.config_check_timer.start(60000)  # Check every 60 seconds

def checkCameraConfig(self):
    """Periodic health check for camera configuration"""
    try:
        current_taps = self.camera.get_tap_configuration()
        
        if current_taps != 8:
            self.log(f"⚠️ Tap configuration changed to {current_taps}-tap")
            self.log("   Auto-restoring to 8-tap...")
            
            if self.camera.set_tap_configuration(8):
                self.log("✓ Tap configuration restored to 8-tap")
            else:
                self.log("✗ Failed to restore tap configuration")
                
    except Exception as e:
        self.log(f"Config check error: {e}")
```

---

## XML Compression Handling

GenCP may return **compressed XML** (ZIP format):

```cpp
// From GenCPConfigExample.cpp
std::vector<uint8_t> buf;
gencp.GetXML(camera_id, buf.data(), size);

// Check for ZIP signature (PK..)
if (buf.size() >= 2 && buf[0] == 'P' && buf[1] == 'K') {
    // XML is compressed, need to extract
    // Save as .zip
    // Use PowerShell Expand-Archive or zlib to extract
    // Read extracted .xml file
}
```

---

## Required Libraries

### C++ Side:
```cmake
# In CMakeLists.txt
find_library(GIDEL_INCAM_LIB
    NAMES InCam
    PATHS "C:/Program Files/Common Files/Gidel/SDK/lib"
)

target_link_libraries(alinify_camera PRIVATE
    ${GIDEL_INCAM_LIB}
    # ... other libs
)
```

### Headers:
```cpp
#include <g_InCam.h>   // Gidel's GenCP wrapper
```

---

## Comparison: XML vs GenCP

| Feature | Direct XML | GenCP |
|---------|------------|-------|
| **Read config** | Parse XML | `GetIntValue()` |
| **Write config** | Edit XML | `SetIntValue()` |
| **Validation** | Manual | Automatic |
| **Live read** | File only | From camera |
| **Live write** | Restart needed | Immediate* |
| **Feature discovery** | Manual parsing | Built-in |
| **Access control** | None | RO/RW/WO |
| **Error handling** | XML errors | SDK errors |

*Some features still require restart

---

## Recommended Approach

### Now (Phase 1) ✅
Keep current XML-based system:
- Simple and working
- No dependencies
- Good for initial release

### Soon (Phase 2) 🎯
Add GenCP for critical features:
- Tap configuration auto-restore
- Live hardware monitoring
- Better validation

### Later (Phase 3) 🚀
Full GenICam integration:
- Feature browser
- Auto-configuration
- Cross-vendor support

---

## Summary

The GenCPConfigExample shows that Gidel provides a **proper GenICam interface** through the `g_InCam.h` API. This is the **recommended approach** for production systems.

### Action Items:

1. ✅ **Done**: Basic XML configuration dialog
2. 🎯 **Next**: Add GenCP C++ methods to GidelCamera
3. 🎯 **Next**: Expose GenCP via Python bindings
4. 🎯 **Next**: Add periodic tap configuration check
5. 🚀 **Future**: Full GenICam feature browser

The current implementation (Phase 1) is **production-ready** and works well. GenCP integration (Phase 2) will add **automatic restoration** after power cycles without user intervention.

---

**Files to Study:**
- `C:\GideL288l\GidelGrabbers\examples\GenCPConfigExample\GenCPConfigExample.cpp`
- `C:\Program Files\Common Files\Gidel\SDK\include\g_InCam.h`
- `C:\Program Files\Common Files\Gidel\SDK\include\InCam.h`
