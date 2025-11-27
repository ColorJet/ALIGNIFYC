# Smart Pattern Tiling - Testing Guide

## 🎯 What is Smart Tiling?

**Problem:** Your fabric has a repeating pattern (e.g., 5×3 grid of designs), but your design file only shows ONE repeat.

**Old Approach (Simple Tiling):** 
- Just repeats pattern like wallpaper (`np.tile`)
- Doesn't know where patterns actually are in fabric
- ❌ Ignores fabric's actual pattern positions

**New Approach (Smart Alignment):**
- ✅ Detects where each pattern appears in camera image
- ✅ Places design at detected positions (handles rotation/scale)
- ✅ Then B-spline fine-tunes alignment
- ✅ Works even with spacing variations, slight rotations

---

## 🧪 Test Files Available

### Generated Test Images:
Located in `test_smart_tiling/` folder:

1. **`pattern_unit.png`** - Single 80×80 pattern (red circle, blue square, green triangle)
2. **`camera_image.png`** - Simulated fabric with 5×3 = 15 pattern instances
3. **`detection_threshold_60.png`** - Shows 12 detected patterns with green boxes
4. **`comparison.png`** - Side-by-side: Camera | Simple Tiling | Smart Alignment

### What the Camera Image Has:
- 5 columns × 3 rows = 15 patterns total
- Slight random rotation (±3°)
- Slight scale variation (±8%)
- Slight position jitter (±8 pixels)
- Fabric-like background texture

---

## 📋 Step-by-Step Testing in GUI

### **Test 1: Simple Tiling (Old Way)**

1. **Launch GUI:**
   ```powershell
   .\venv\Scripts\python.exe gui\main_gui.py
   ```

2. **Load Images:**
   - **Camera:** `test_smart_tiling\camera_image.png`
   - **Design:** `test_smart_tiling\pattern_unit.png`

3. **Configure Registration Tab:**
   - ✅ Check **"Tile pattern across fabric"**
   - ❌ UNCHECK **"Smart pattern alignment"**
   - Grid Spacing: 32 (default is fine)
   - Method: B-spline

4. **Click "Register"**

5. **Watch Log:**
   ```
   [5%] 🔲 Pattern tiling (simple tiling)...
   [8%] ✓ Pattern tiled to 650×430
   [30%] Running registration algorithm...
   ```

6. **Result:** Pattern repeated like wallpaper, may not align with actual fabric positions

---

### **Test 2: Smart Alignment (New Way)**

1. **Keep same images loaded**

2. **Configure Registration Tab:**
   - ✅ Check **"Tile pattern across fabric"**
   - ✅ CHECK **"Smart pattern alignment (recommended)"**

3. **Enable Debug Mode (to see detection):**
   - Menu: **Settings → Debug Mode**
   - Check your terminal/console for detailed output

4. **Click "Register"**

5. **Watch Log:**
   ```
   [5%] 🔲 Pattern tiling (smart alignment)...
   🧠 Using smart alignment - detecting pattern positions in target...
   Detected 12 pattern instances at scale 1.00
   ✓ Smart alignment: Placed pattern at 12 detected positions
   [8%] ✓ Pattern tiled to 650×430
   [30%] Running registration algorithm...
   ```

6. **Check Terminal Output:**
   You should see:
   ```
   Detecting pattern instances in target...
   ✓ Detected 12 pattern instances
   ```

7. **Result:** Pattern placed at detected locations, better initial alignment

---

## 🔍 Visual Inspection

### Compare Results:

**Layer Panel (left side):**
- You should see layers: Camera, Design, Registered

**Toggle visibility:**
- Click eye icon to show/hide layers
- Compare how well registered pattern aligns with camera

**Zoom in (mouse wheel):**
- Check individual pattern instances
- Smart alignment should match fabric positions better

---

## 🎛️ Advanced Options

### Pattern Detection Threshold:
Currently hardcoded to `0.6` in backend. To adjust:

**If too many false detections:**
- Open `python/registration_backend.py`
- Find: `instances = self.detect_pattern_instances_in_target(pattern_unit, target, threshold=0.6)`
- Increase to `0.7` or `0.8`

**If too few detections:**
- Decrease to `0.5`

### Preprocessing Combinations:

Try these for better alignment:

**For embossed/textured fabrics:**
1. Fixed (Camera): **Texture Enhance** or **Emboss Gradient**
2. Moving (Design): **Edge Enhance**
3. ✅ Smart pattern alignment

**For colored patterns:**
1. Fixed: **CLAHE** or **Histogram Eq**
2. Moving: **None** or **Edge Enhance**
3. ✅ Smart pattern alignment

---

## 🐛 Troubleshooting

### Problem: "No pattern instances detected"

**Causes:**
- Pattern too different from camera
- Threshold too high
- Scale mismatch too large

**Solutions:**
1. Lower detection threshold (edit backend)
2. Try different preprocessing
3. Check if pattern actually repeats in camera

### Problem: UI Freezes

**Should NOT happen** - pattern detection runs in background thread now!

If it still freezes:
1. Check terminal for errors
2. Enable Debug Mode (Settings menu)
3. Report which step causes freeze

### Problem: Wrong number of patterns detected

**Expected:** 15 patterns (5×3 grid)
**Detected:** 12-14 is normal (some may be at edges, low confidence)

**If detecting 0-5:**
- Pattern may be too different
- Try lowering threshold
- Check preprocessing settings

**If detecting 20+:**
- Too many false positives
- Increase threshold
- Or use simple tiling instead

---

## 📊 Performance Tips

### Background Processing:
All heavy operations now run in background:
- ✅ Pattern detection
- ✅ Template matching
- ✅ Tiling
- ✅ Preprocessing
- ✅ Registration

**UI should stay responsive!**

### Progress Updates:
- `[5%]` - Pattern detection
- `[10-25%]` - Preprocessing
- `[30%+]` - Registration algorithm
- `[100%]` - Complete

### Debug Mode:
- Shows detailed Elastix output in terminal
- Shows detection count
- Helps diagnose issues
- Toggle: **Settings → Debug Mode**

---

## 🎨 Real-World Usage

### Your Fabric Scenario:

1. **Take photo of fabric** (with 5×3 pattern grid)
2. **Load single pattern design file**
3. **Enable both:**
   - ✅ Tile pattern across fabric
   - ✅ Smart pattern alignment
4. **Run registration**
5. **System will:**
   - Detect ~15 pattern positions
   - Place design at each position
   - Fine-tune with B-spline
   - Generate aligned output

### Tips:
- Good lighting for camera image
- Pattern should be clearly visible
- Design should match one repeat from fabric
- For embossed: use Texture Enhance preprocessing

---

## 📁 Output Files

After registration completes:

**Registered Image:**
- Shown in Layer panel
- Can export via File → Export menu

**Deformation Field:**
- Saved automatically if configured
- Used for high-resolution warping

**Manual Corrections:**
- If needed, use Manual tab
- Add red/blue control points
- Click "Apply Manual Corrections"

---

## 🚀 Next Steps

1. **Test with provided images** (this guide)
2. **Try your real fabric images**
3. **Adjust detection threshold** if needed
4. **Experiment with preprocessing** combinations
5. **Use Debug Mode** to understand what's happening

**Questions or issues?** Check terminal output with Debug Mode enabled!
