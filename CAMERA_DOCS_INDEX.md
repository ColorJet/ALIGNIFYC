# Camera System Documentation Index

**Comprehensive documentation for the Alinify camera system**

---

## 📚 Documentation Structure

### 1. **Camera Configuration System** (NEW ✨)
Complete GenTL-style configuration interface for managing CameraLink settings.

- **[CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)** ⭐ **START HERE**
  - Executive summary
  - Quick start guide
  - What was built and why
  - Production ready checklist

- **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** 📖 **USER GUIDE**
  - Step-by-step instructions
  - Common tasks and workflows
  - Troubleshooting tips
  - Quick reference card

- **[CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)** 🔧 **TECHNICAL**
  - Detailed implementation
  - Architecture and design
  - API reference
  - Future enhancements

- **[CAMERA_CONFIG_SUMMARY.md](CAMERA_CONFIG_SUMMARY.md)** 📝 **OVERVIEW**
  - Feature list
  - File locations
  - Testing checklist
  - Integration points

- **[CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)** 🏗️ **DIAGRAMS**
  - System architecture
  - Data flow diagrams
  - Component relationships
  - Visual workflows

- **[CAMERA_GENCP_INTEGRATION.md](CAMERA_GENCP_INTEGRATION.md)** 🎯 **GENCP UPGRADE**
  - GenICam protocol approach
  - Comparison: XML vs GenCP
  - Phase 2 implementation guide
  - GenCPConfigExample.cpp analysis

- **[CAMERA_CONFIG_FIXES.md](CAMERA_CONFIG_FIXES.md)** ✅ **FIXES**
  - PyQt6 → PySide6 fix
  - Import corrections
  - Testing verification

---

### 2. **Camera Frame Capture**
Frame buffer handling and data extraction from Gidel frame grabber.

- **[CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)** ✅ **BUFFER FIX**
  - Problem: 1-line images instead of full strips
  - Solution: Use BufferInfoHeight from frame grabber
  - Before/after test results
  - FgExample.cpp logic integration

- **[CAMERA_FRAME_CAPTURE_SUCCESS.md](CAMERA_FRAME_CAPTURE_SUCCESS.md)** ✅ **CAPTURE TEST**
  - 30-second frame capture test
  - 298K frames received, 290 captured
  - Zero frame drops
  - 9.71 FPS performance

---

### 3. **Setup and Integration**
Initial camera setup, DLL dependencies, and system integration.

- **Camera Integration Notes** (in conversation history)
  - DLL dependency resolution
  - FGConfig.gxfg setup
  - Python bindings with callbacks
  - Test script creation

---

## 🎯 Quick Navigation by Task

### I want to...

#### Configure Camera Settings
→ **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)**
- Common tasks section
- Step-by-step workflows
- Quick reference card

#### Fix Tap Configuration (8-tap vs 2-tap)
→ **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** Section 1
```
1. Camera → Camera Configuration...
2. Set taps to 8-tap
3. Check "Force 8-tap on power-on"
4. Click Apply
```

#### Understand the System Architecture
→ **[CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)**
- Visual diagrams
- Component relationships
- Data flow

#### Implement Custom Features
→ **[CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)**
- Code structure
- API reference
- Extension points

#### Test the Camera System
→ **[CAMERA_CONFIG_SUMMARY.md](CAMERA_CONFIG_SUMMARY.md)** Testing section
- Manual test checklist
- Automated test examples
- Validation steps

#### Debug Frame Capture Issues
→ **[CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)**
- Frame dimension problems
- Buffer handling
- Reference implementation

---

## 📁 File Locations

### Source Code
```
gui/
├── main_gui.py                      # Main window + camera menu
└── widgets/
    ├── camera_config_dialog.py      # Configuration dialog UI
    └── camera_config_manager.py     # Configuration backend

src/
├── camera/
│   └── gidel_camera.cpp             # C++ camera implementation
└── python_bindings/
    └── bindings.cpp                  # Python bindings

test_camera_save_frames.py           # Frame capture test script
```

### Configuration Files
```
config/
└── camera/
    ├── FGConfig.gxfg                # Primary config (XML)
    ├── FGConfig.gxfg.backup         # Auto-backup
    └── camera_settings_cache.json    # Fast cache

camera_captures/                      # Captured frame output
├── frame_YYYYMMDD_HHMMSS_*.png
└── ...
```

### Documentation
```
CAMERA_CONFIG_COMPLETE.md             # ⭐ Start here
CAMERA_CONFIG_QUICK_GUIDE.md          # 📖 User guide
CAMERA_CONFIGURATION_IMPLEMENTATION.md # 🔧 Technical details
CAMERA_CONFIG_SUMMARY.md              # 📝 Overview
CAMERA_CONFIG_ARCHITECTURE.md         # 🏗️ Diagrams
CAMERA_BUFFER_FIX_SUCCESS.md          # ✅ Buffer fix
CAMERA_FRAME_CAPTURE_SUCCESS.md       # ✅ Capture test
CAMERA_DOCS_INDEX.md                  # 📚 This file
```

---

## 🚀 Getting Started

### First Time Setup

1. **Launch the GUI**
   ```bash
   cd D:\Alinify20251113\Alinify
   .venv\Scripts\python.exe gui\main_gui.py
   ```

2. **Open Configuration Dialog**
   - Menu: `Camera → Camera Configuration...`

3. **Auto-Configure Camera**
   - Click: **🔍 Auto-Detect**
   - Click: **✓ Apply**
   - Confirm restart if prompted

4. **Test Frame Capture** (Optional)
   ```bash
   .venv\Scripts\python.exe test_camera_save_frames.py
   ```

5. **Verify Results**
   - Check: `camera_captures/` folder
   - Verify: Image dimensions (1024x16384)
   - Verify: File sizes (~3 MB)

---

## 📊 System Status

### ✅ Complete and Working
- [x] Camera configuration dialog (4 tabs)
- [x] XML configuration management
- [x] Backup system
- [x] Tap configuration (1/2/4/8)
- [x] GUI integration
- [x] Frame capture
- [x] Buffer dimension fix
- [x] Python callbacks
- [x] Status logging
- [x] Error handling

### 🔄 Tested and Validated
- [x] Dialog opens and loads config
- [x] Settings save to XML
- [x] Backup files created
- [x] Camera restart workflow
- [x] Frame capture (298K frames, 0 drops)
- [x] Image dimensions correct
- [x] Pixel data valid

### 🎯 Production Ready
- [x] Code complete
- [x] Error handling
- [x] User documentation
- [x] Technical documentation
- [x] Test scripts
- [x] Integration complete

---

## 🔧 Configuration Settings Reference

### Critical Settings

| Setting | Location | Options | Default | Notes |
|---------|----------|---------|---------|-------|
| **NumParallelPixels** | CameraLink tab | 1/2/4/8 | **8** | Tap configuration (CRITICAL) |
| Format | CameraLink tab | Mono/Bayer/RGB/RGBA | Mono | Image format |
| BitsPerColor | CameraLink tab | 8/10/12/14/16 | 8 | Bit depth |
| GrabMode | Acquisition tab | NextFrame/LatestFrame | LatestFrame | Frame skip mode |
| ExternalSource | Acquisition tab | true/false | false | Hardware trigger |

### Recommended Settings for Line Scan Camera

```yaml
NumParallelPixels: 8           # 8-tap for optimal bandwidth
Format: Mono                    # Single channel
BitsPerColor: 8                 # Standard bit depth
GrabMode: LatestFrame          # Skip to newest for live view
NumZones: 1                     # Single zone
ExternalSource: false           # Software trigger
```

---

## 🎓 Learning Path

### For Users (Operators)
1. **[CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)** - Understand what's available
2. **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** - Learn common tasks
3. Try it yourself in the GUI

### For Developers
1. **[CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)** - Overview
2. **[CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)** - System design
3. **[CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)** - Code details
4. Study the source files

### For Troubleshooters
1. **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** - Troubleshooting section
2. **[CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)** - Buffer issues
3. Check error logs in GUI

---

## 💡 Common Scenarios

### Scenario 1: Camera Powered Off, Taps Reset to 2

**Problem**: Camera was 8-tap, but after power cycle it's 2-tap.

**Solution**: 
→ See **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** Section 1  
→ Or **[CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)** "Power Cycle Scenario"

### Scenario 2: Frames Saving But No Visible Pixels

**Problem**: PNG files are tiny (846 bytes), no image content.

**Solution**: 
→ See **[CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)**  
→ Use BufferInfoHeight instead of config_.height

### Scenario 3: Need to Change Image Format

**Problem**: Want RGB instead of Mono.

**Solution**: 
→ See **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** Section 3

### Scenario 4: First Time Setup

**Problem**: New installation, need to configure everything.

**Solution**: 
→ See **[CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)** "Quick Start"  
→ Use Auto-Detect button

---

## 🔍 Search Index

### By Keyword

**Tap Configuration** / **8-tap** / **2-tap**
- [CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)
- [CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md) Section 1
- [CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)

**GenTL** / **GenICam**
- [CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)
- [CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md) Phase 3

**Buffer** / **Frame Dimensions**
- [CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)
- [CAMERA_FRAME_CAPTURE_SUCCESS.md](CAMERA_FRAME_CAPTURE_SUCCESS.md)

**XML** / **FGConfig.gxfg**
- [CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)
- [CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md) "File Format"

**Configuration Dialog** / **GUI**
- [CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)
- [CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)

**Auto-Detect** / **Optimal Settings**
- [CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md) Section 2
- [CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)

**Backup** / **Restore**
- [CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md) Section 7
- [CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)

**Power Cycle** / **Reset**
- [CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)
- [CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md) "Power Cycle Scenario"

---

## 📞 Support Resources

### When You Need Help...

**"How do I...?"** → Start with **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)**

**"Why doesn't it...?"** → Check **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** Troubleshooting

**"What is...?"** → See **[CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)** for concepts

**"Can it...?"** → Check **[CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)** Features

**"It's broken..."** → **[CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)** for frame issues

---

## 🎉 Quick Win

**Want to see it work in 30 seconds?**

```bash
# 1. Open GUI
.venv\Scripts\python.exe gui\main_gui.py

# 2. Click menu
Camera → Camera Configuration...

# 3. Click button
🔍 Auto-Detect

# 4. Click button
✓ Apply

# Done! Camera configured optimally.
```

---

## 📋 Documentation Checklist

When working with the camera system, use this checklist:

- [ ] Read **[CAMERA_CONFIG_COMPLETE.md](CAMERA_CONFIG_COMPLETE.md)** for overview
- [ ] Follow **[CAMERA_CONFIG_QUICK_GUIDE.md](CAMERA_CONFIG_QUICK_GUIDE.md)** for tasks
- [ ] Check **[CAMERA_CONFIG_ARCHITECTURE.md](CAMERA_CONFIG_ARCHITECTURE.md)** for concepts
- [ ] Reference **[CAMERA_CONFIGURATION_IMPLEMENTATION.md](CAMERA_CONFIGURATION_IMPLEMENTATION.md)** for code
- [ ] Verify with **[CAMERA_BUFFER_FIX_SUCCESS.md](CAMERA_BUFFER_FIX_SUCCESS.md)** if frame issues
- [ ] Test with **[CAMERA_FRAME_CAPTURE_SUCCESS.md](CAMERA_FRAME_CAPTURE_SUCCESS.md)** procedure

---

**Complete documentation index for the Alinify camera system** 📚✅

*Last Updated: November 13, 2025*
