# Camera Configuration Setup Guide

## Current Status

The camera bindings are working, but initialization fails with:
```
[ERROR] Failed to load config file:
```

This is because `FGConfig.gxfg` doesn't exist yet.

---

## Solution Options

### Option 1: Copy from Gidel Examples (RECOMMENDED)

If you have the Gidel examples installed:

```powershell
# Copy the working config file
Copy-Item "C:\GideL288l\GidelGrabbers\examples\FgExample\FGConfig.gxfg" "D:\Alinify20251113\Alinify\config\camera\"

# Create the directory if it doesn't exist
New-Item -ItemType Directory -Path "D:\Alinify20251113\Alinify\config\camera\" -Force
Copy-Item "C:\GideL288l\GidelGrabbers\examples\FgExample\FGConfig.gxfg" "D:\Alinify20251113\Alinify\config\camera\"
```

### Option 2: Use Gidel's Configuration Tool

1. Open **Gidel Configuration Manager** (should be in Start Menu)
2. Configure your camera settings:
   - Resolution: 4096 x 1
   - Line rate: 10000 Hz
   - Pixel format: Mono8
   - CameraLink configuration
3. Save as: `D:\Alinify20251113\Alinify\config\camera\FGConfig.gxfg`

### Option 3: Create Minimal Config

Create a basic `.gxfg` file manually (XML format):

```xml
<?xml version="1.0" encoding="utf-8"?>
<Configuration>
  <Camera>
    <Width>4096</Width>
    <Height>1</Height>
    <PixelFormat>Mono8</PixelFormat>
    <AcquisitionMode>Continuous</AcquisitionMode>
  </Camera>
  <Grabber>
    <Board>0</Board>
    <Port>0</Port>
    <CameraLinkConfiguration>Base</CameraLinkConfiguration>
  </Grabber>
</Configuration>
```

Save this as: `D:\Alinify20251113\Alinify\config\camera\FGConfig.gxfg`

### Option 4: Point to Existing Config

Edit `config/system_config.yaml`:

```yaml
camera:
  gidel:
    config_file: "C:/GideL288l/GidelGrabbers/examples/FgExample/FGConfig.gxfg"  # Full path to existing file
    board_id: 0
    buffer_count: 30
```

---

## Verification

After setting up the config file, launch the GUI:

```powershell
.\launch_gui.bat
```

### Expected Output (with config file):

```
[INFO] Initializing Gidel camera...
[INFO] Creating CProcFgApi instance
[INFO] Loading config file: config/camera/FGConfig.gxfg
[INFO] Config loaded successfully
[INFO] Initializing frame grabber...
```

### If hardware is connected:
```
✓ Camera initialized successfully!
   Device: Gidel CameraLink Frame Grabber
   Ready to start acquisition
```

### If hardware is NOT connected:
```
✗ Camera initialization failed: ERROR_CAMERA_INIT
   Check:
   - Gidel frame grabber is installed
   - Camera is connected
   - Configuration file is correct
```

---

## Troubleshooting

### "Failed to load config file"
- Check file exists: `Test-Path "D:\Alinify20251113\Alinify\config\camera\FGConfig.gxfg"`
- Check path in `system_config.yaml` is correct
- Ensure file is valid XML/Gidel format

### "Camera initialization failed"
- Verify Gidel drivers installed: Check Device Manager for "Gidel" devices
- Check camera is powered on and connected
- Try Gidel's diagnostic tools first

### "Buffer allocation failed"
- Reduce buffer_count in `system_config.yaml` (try 10 instead of 30)
- Check available system memory
- Ensure running as Administrator

---

## Quick Start Commands

```powershell
# Create camera config directory
New-Item -ItemType Directory -Path "D:\Alinify20251113\Alinify\config\camera\" -Force

# Option A: Copy from examples
Copy-Item "C:\GideL288l\GidelGrabbers\examples\FgExample\FGConfig.gxfg" "D:\Alinify20251113\Alinify\config\camera\"

# Option B: Or point to existing file in system_config.yaml
# Edit: config/system_config.yaml
# Set: camera.gidel.config_file to full path

# Launch GUI
.\launch_gui.bat
```

---

## System Config Reference

Current settings in `config/system_config.yaml`:

```yaml
camera:
  resolution:
    width: 4096
    height: 1
  frequency: 10000
  bit_depth: 8
  pixel_size: 0.010256
  fov:
    width: 42.0
  gidel:
    config_file: config/camera/FGConfig.gxfg  # ← NEEDS TO EXIST
    board_id: 0
    buffer_count: 30
```

---

## Once Config is Set Up

The GUI will:
1. ✅ Load configuration on startup
2. ✅ Initialize camera hardware (if connected)
3. ✅ Enable "Start Camera" button
4. ✅ Show camera status in Log tab
5. ✅ Display frames when acquisition starts

**You're almost there! Just need the config file!** 🎯
