# Camera Configuration Quick Guide 📋

**Quick reference for using the camera configuration dialog**

---

## Opening the Dialog

### Method 1: From Menu
```
Camera Menu → Camera Configuration...
```

### Method 2: Keyboard (once camera is selected)
```
(No keyboard shortcut - intentional safety feature)
```

---

## Dialog Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Gidel CameraLink Frame Grabber Configuration              │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐ │
│  │ [CameraLink] [Acquisition] [ROI] [Advanced]           │ │
│  │                                                        │ │
│  │  TAP CONFIGURATION (CRITICAL)                         │ │
│  │  ┌──────────────────────────────────────────────┐    │ │
│  │  │ Number of Taps: [8 - Octal Tap ▼]           │    │ │
│  │  │                                               │    │ │
│  │  │ ℹ️ Octal tap: 64-bit parallel data path.    │    │ │
│  │  │    Maximum bandwidth for high-speed line     │    │ │
│  │  │    scan cameras.                             │    │ │
│  │  │                                               │    │ │
│  │  │ ☑ Force 8-tap on camera power-on            │    │ │
│  │  └──────────────────────────────────────────────┘    │ │
│  │                                                        │ │
│  │  IMAGE FORMAT                                         │ │
│  │  Format:        [Mono ▼]                             │ │
│  │  Bits Per Color: [8 ▼]                               │ │
│  │  Bayer Pattern:  [GR ▼] (disabled for Mono)         │ │
│  │                                                        │ │
│  │  SIGNAL CONTROL                                       │ │
│  │  ☐ Ignore FVAL signal                                │ │
│  │  ☐ Ignore DVAL signal                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ⚠️ Warning: Camera is configured for 2-tap mode...        │
│     Your line scan camera requires 8-tap for optimal...    │
│                                                             │
│  [🔍 Auto-Detect]  [✓ Apply]  [💾 Save]  [✕ Cancel]      │
└─────────────────────────────────────────────────────────────┘
```

---

## Common Tasks

### 1. Fix Tap Configuration After Power Cycle

**Problem**: Camera reset to 2-tap after power off

**Solution**:
1. Open dialog: `Camera → Camera Configuration...`
2. **CameraLink tab**
3. Set "Number of Taps" to: **8 - Octal Tap**
4. Check: "☑ Force 8-tap on camera power-on"
5. Click: **✓ Apply**
6. If camera is running, confirm restart

**Result**: Configuration saved, camera restarted with 8-tap

---

### 2. One-Click Optimal Setup

**Problem**: Need to configure camera quickly

**Solution**:
1. Open dialog
2. Click: **🔍 Auto-Detect**
3. Review recommended settings:
   - 8-tap configuration
   - Mono format @ 8-bit
   - LatestFrame grab mode
   - Auto-restore enabled
4. Click: **✓ Apply**

**Result**: Camera configured with optimal settings

---

### 3. Change Image Format

**Problem**: Need RGB instead of Mono

**Solution**:
1. **CameraLink tab**
2. Under "IMAGE FORMAT"
3. Set "Format" to: **RGB**
4. Adjust "Bits Per Color" if needed
5. Click: **✓ Apply**

**Result**: Camera captures RGB images

---

### 4. Configure Bayer Pattern Camera

**Problem**: Using Bayer sensor

**Solution**:
1. **CameraLink tab**
2. Set "Format" to: **Bayer**
3. Set "Bayer Pattern" to: **GR**, **RG**, **GB**, or **BG**
4. Click: **✓ Apply**

**Result**: Correct Bayer demosaicing

---

### 5. Change Grab Mode

**Problem**: Need to capture every frame (not just latest)

**Solution**:
1. **Acquisition tab**
2. Set "Grab Mode" to: **NextFrame**
3. Click: **✓ Apply**

**Note**: 
- **LatestFrame**: Skip to newest (recommended for live view)
- **NextFrame**: Process every frame (for data collection)

---

### 6. Save Configuration Without Restart

**Problem**: Want to save config for later, don't restart now

**Solution**:
1. Make changes
2. Click: **💾 Save** (not Apply)
3. Configuration saved to file
4. Camera not restarted

**Result**: Next camera start uses new config

---

### 7. Restore from Backup

**Problem**: Made wrong changes, need to undo

**Solution**:
1. Close dialog
2. Navigate to: `config/camera/`
3. Find: `FGConfig.gxfg.backup`
4. Copy to: `FGConfig.gxfg`
5. Restart camera

**Result**: Previous configuration restored

---

## Tab Contents

### CameraLink Tab (Primary)
```
✓ Number of Taps (1/2/4/8)      ← CRITICAL SETTING
✓ Number of Zones (1-4)
✓ Zones Direction (H/V)
✓ Image Format (Mono/Bayer/RGB/RGBA)
✓ Bits Per Color (8/10/12/14/16)
✓ Bayer Pattern (GR/RG/GB/BG)
✓ Signal Control (FVAL, DVAL)
```

### Acquisition Tab
```
✓ Grab Mode (LatestFrame/NextFrame)
✓ External Trigger
✓ Reverse Y axis
✓ Acquisition Delay (ms)
✓ Frame Count (0 = continuous)
✓ Device ID (multi-camera)
```

### ROI Tab
```
✓ ROI List Mode
✓ ROI List Path
✓ Manual ROI:
  - Width
  - Height
  - Offset X
  - Offset Y
```

### Advanced Tab
```
✓ Output as 32-bit RGB10p
✓ Log Level (Off/Error/Warning/Info/Debug)
✓ Max Log Size (MB)
✓ Config File Path
```

---

## Button Functions

| Button | Function | When to Use |
|--------|----------|-------------|
| **🔍 Auto-Detect** | Set recommended settings | First-time setup |
| **✓ Apply** | Save + restart camera | Change active config |
| **💾 Save** | Save without restart | Prepare for next session |
| **✕ Cancel** | Close without saving | Discard changes |

---

## Warning System

### Yellow Warning Box
Appears when:
- Tap count ≠ 8
- Uncommon settings selected
- Potential configuration issues

**Action**: Review settings, fix if needed

### Critical Errors
Shown as message boxes:
- Invalid file path
- XML parse errors
- Save failures

**Action**: Check file permissions, paths

---

## Status Bar Messages

After configuration:
```
"Camera configuration updated"          (3 seconds)
```

During restart:
```
"Restarting camera with new config..."  (until done)
"Camera ready"                          (when complete)
```

---

## Log Messages

Configuration changes are logged:

```
======================================================================
📋 CAMERA CONFIGURATION CHANGED
======================================================================
• Tap Configuration: 8-tap
• Image Format: Mono @ 8-bit
• Grab Mode: LatestFrame
• Auto-restore to 8-tap: ENABLED
  → Camera will auto-restore to 8-tap on power cycle
✓ Configuration saved and applied
```

---

## Troubleshooting

### Dialog Won't Open
**Cause**: Missing PyQt6/PySide6  
**Solution**: Install GUI framework

### Settings Not Saving
**Cause**: File permissions  
**Solution**: Run as administrator or check folder permissions

### Camera Won't Restart
**Cause**: Hardware issue  
**Solution**: 
1. Manually stop camera
2. Wait 5 seconds
3. Try again

### Tap Count Keeps Resetting
**Cause**: Power cycle resets hardware  
**Solution**: Check "Force 8-tap on camera power-on" box

---

## Best Practices

### ✅ Do:
- Use **Auto-Detect** for initial setup
- Enable "**Force 8-tap on camera power-on**"
- Click **Apply** when camera is idle
- Review warnings before applying
- Keep backups (.gxfg.backup files)

### ❌ Don't:
- Change critical settings during acquisition
- Ignore warning messages
- Delete backup files
- Use 2-tap for line scan cameras
- Change config files manually (use dialog)

---

## Keyboard Navigation

| Key | Function |
|-----|----------|
| **Tab** | Move between fields |
| **Space** | Toggle checkboxes |
| **Enter** | Click focused button |
| **Esc** | Cancel dialog |
| **Ctrl+Tab** | Switch tabs |

---

## Quick Reference Card

```
┌──────────────────────────────────────┐
│  CAMERA CONFIGURATION QUICK REF      │
├──────────────────────────────────────┤
│                                      │
│  Open:                               │
│    Camera → Camera Configuration     │
│                                      │
│  Critical Settings:                  │
│    • Taps: 8 (octal)                │
│    • Format: Mono                    │
│    • Bits: 8                         │
│    • Mode: LatestFrame              │
│                                      │
│  Quick Setup:                        │
│    1. Click Auto-Detect             │
│    2. Click Apply                    │
│    3. Confirm restart                │
│                                      │
│  After Power Cycle:                  │
│    1. Open config                    │
│    2. Set taps to 8                  │
│    3. Check force restore            │
│    4. Apply                          │
│                                      │
│  Files:                              │
│    config/camera/FGConfig.gxfg       │
│    config/camera/*.backup            │
│                                      │
└──────────────────────────────────────┘
```

---

## Screenshots (Conceptual)

### Main Dialog
![Camera Config Dialog - Main](conceptual: tabbed interface with 4 tabs)

### CameraLink Tab
![CameraLink Tab](conceptual: tap config, format settings)

### Warning Display
![Warning](conceptual: yellow warning box for non-8-tap)

### Apply Confirmation
![Restart Prompt](conceptual: "Restart camera?" dialog)

---

**For detailed implementation info, see: `CAMERA_CONFIGURATION_IMPLEMENTATION.md`**
