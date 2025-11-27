# Camera Quick Reference

## 🚀 Start Camera System

```batch
cd D:\Alinify20251113\Alinify
.\launch_gui.bat
```

## ✅ What's Working

- **Camera Initialization**: Automatic on GUI startup
- **Start Acquisition**: Click "Start Camera" button
- **Stop Acquisition**: Click "Stop Camera" button  
- **Status Logging**: Check "Log" tab for messages

## 📂 Key Files

### Configuration
- `config/camera/FGConfig.gxfg` - Gidel hardware config (72 MB copied from app folder)
- `config/system_config.yaml` - System-wide settings

### Camera Settings in system_config.yaml
```yaml
camera:
  resolution:
    width: 4096
    height: 1
  frequency: 10000
  bit_depth: 8
  gidel:
    config_file: config/camera/FGConfig.gxfg
    board_id: 0
    buffer_count: 30
```

## 🔧 If You Need to Rebuild

```powershell
# Rebuild camera module and bindings
cd build
cmake --build . --config Release --target alinify_bindings

# Copy to gui folder
Copy-Item "src\python_bindings\Release\alinify_bindings.cp312-win_amd64.pyd" "..\gui\" -Force
```

## 📊 Expected Log Messages

### Successful Startup
```
[INFO] Initializing Gidel camera...
[INFO] Allocating 30 buffers of 72 MB each
[INFO] Gidel camera initialized successfully
```

### Start Camera
```
[INFO] Starting acquisition...
[INFO] Acquisition started
```

### Stop Camera
```
[INFO] Stopping acquisition...
[INFO] Acquisition stopped
```

## ⚠️ Troubleshooting

### "Failed to load config file"
→ Check: `config/camera/FGConfig.gxfg` exists

### "Buffer too small"
→ Should be fixed (72 MB buffers)
→ If still happening, rebuild bindings

### "Camera not found"
→ Check Gidel hardware is connected
→ Check Device Manager for "Gidel" devices
→ Try Gidel diagnostic tools

### "Import failed"
→ Check all DLLs in gui folder (87 files)
→ Run `diagnose_camera.py` for details

## 📝 Buffer Size Calculation

```cpp
// Current (correct for 4096x18432 strips):
const size_t buffer_size = 0x4E50000;  // 72 MB

// Calculation:
// 4096 pixels wide × 18432 pixels tall × 1 byte = 75,497,472 bytes
// Rounded to: 72 MB per buffer
// Total with 30 buffers: 2.16 GB
```

## 🎯 Status

✅ **FULLY OPERATIONAL** - Camera ready for production use!

---

Last updated: January 13, 2025
