# Manual Deformation Editor - Quick Start Card

## 🚀 5-SECOND DECISION TREE

```
Registration Complete → Manual Correction Prompt
                              ↓
                    Open Manual Editor
                              ↓
                  Switch to DIFFERENCE mode
                              ↓
                     Look at the image
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
        Mostly DARK                      BRIGHT areas
    (good alignment)                    (misalignment)
              ↓                               ↓
      Check "BYPASS"                    Mark & drag
      Click "Done"                    control points
         (5 sec)                         (1-3 min)
```

---

## 🎨 ONE-PAGE CHEAT SHEET

### VIEW MODES (Combo Box)
| Mode | When to Use | What You See |
|------|-------------|--------------|
| **Difference** ⭐ | **ALWAYS START HERE** | Bright = errors, Dark = good |
| Blend | See both images | Overlay with slider |
| Checkerboard | Verify edges | Alternating tiles |
| Warped/Fixed | Inspect single image | One image only |

### ADJUSTMENTS (Sliders)
| Control | Range | Recommended | Purpose |
|---------|-------|-------------|---------|
| **Contrast** | 0.5x - 3.0x | **2.0x - 2.5x** | Make errors visible |
| Brightness | -100 to +100 | ±20-40 | See dark/bright areas |
| **Invert** | Checkbox | Try if needed | Flip black ↔ white |

### BYPASS MODE (Top Checkbox)
✓ Check if: Difference mode mostly dark  
✓ Effect: Skips all corrections (5 sec)  
✓ Result: Returns empty list `[]`

### CONTROL POINTS
- **Click** = Add point
- **Drag** = Correct alignment
- **Auto Grid** = Place many points automatically
- **Clear All** = Remove all points
- **Undo** = Remove last point

---

## ⚡ 3 COMMON SCENARIOS

### Scenario 1: Perfect Registration (5 seconds)
1. Open editor
2. Difference mode → **Mostly dark**
3. ✓ Check "Bypass"
4. Click "Done"

### Scenario 2: Small Local Error (30 seconds)
1. Open editor
2. Difference mode → **One bright spot**
3. Contrast 2.0x
4. Click on bright spot
5. Drag to align
6. Click "Done"

### Scenario 3: Multiple Errors (2-3 minutes)
1. Open editor
2. Difference mode → **Several bright areas**
3. Contrast 2.5x, adjust brightness if needed
4. Click on each bright area
5. Drag each point to align
6. Verify: Checkerboard → edges should align
7. Verify: Difference → should be darker now
8. Click "Done"

---

## 🎯 PRO TIPS

### Finding Errors Fast
1. **Difference mode** (always!)
2. **Contrast 2.5x** (make errors obvious)
3. **Bright = bad**, Dark = good

### Marking Precisely
- Use **Invert** for dark fabrics
- Increase **Contrast** to see small shifts
- Adjust **Brightness** to see details

### Efficient Corrections
- **5-10 strategic points** > 50 random points
- Place points **at bright areas** in Difference mode
- **Drag to dark** = correct alignment
- Verify in **Checkerboard** mode

### When to Bypass
- ✅ Difference mode mostly dark
- ✅ Testing/prototyping
- ✅ Registration already acceptable
- ❌ Don't bypass if bright areas exist

---

## 🔥 GOLDEN RULE

**START WITH DIFFERENCE MODE + HIGH CONTRAST**

This shows exactly where problems are.  
If mostly dark → Bypass (5 sec)  
If bright areas → Mark & fix (1-3 min)

---

## 📊 Keyboard Reference (Future)

| Key | Action |
|-----|--------|
| Space | Toggle Blend ↔ Difference |
| I | Toggle Invert |
| Ctrl+Z | Undo last point |
| Del | Remove selected point |
| Esc | Cancel |
| Enter | Apply corrections |

*(Not yet implemented)*

---

## 🆘 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| Can't see errors | Difference mode + Contrast 2.5x |
| Image too dark | Brightness +40 or Invert |
| Points not visible | Try Invert or adjust Contrast |
| Not sure if good | Check Difference mode - dark = good |
| Want to skip | Check Bypass at top |

---

## 📞 QUICK HELP

**Q: How do I know if I need corrections?**  
A: Difference mode. Bright = errors. Dark = good. If mostly dark, Bypass.

**Q: What's the best way to find errors?**  
A: Difference mode with Contrast 2.5x. Bright areas show misalignment.

**Q: How many points should I add?**  
A: 5-10 at bright areas is usually enough. Quality over quantity.

**Q: Can I skip this step?**  
A: Yes! Check "Bypass" at top if Difference mode shows mostly dark.

**Q: What if I make a mistake?**  
A: Click "Undo" to remove last point, or "Clear All" to start over.

---

## ✅ COMPLETION CHECKLIST

Before clicking "Done":
- [ ] Checked Difference mode - bright areas reduced?
- [ ] Verified in Checkerboard - edges align?
- [ ] Control points placed at error locations?
- [ ] OR checked Bypass if registration already good?

---

## 📈 TIME ESTIMATES

| Task | Time |
|------|------|
| Quick check + Bypass | **5 seconds** |
| Single point correction | **30 seconds** |
| 5-10 point correction | **2-3 minutes** |
| Complex manual editing | **5-10 minutes** |

**Average**: Most cases either Bypass (5s) or simple fix (1-2 min)

---

## 🎓 LEARNING PATH

### Beginner (Day 1)
1. Always open Difference mode first
2. Learn: Bright = bad, Dark = good
3. Use Bypass when mostly dark
4. Add 1-2 points when bright areas exist

### Intermediate (Week 1)
1. Use Contrast 2.0x-2.5x routinely
2. Try different overlay modes
3. Use Invert for dark fabrics
4. Place 5-10 strategic points efficiently

### Advanced (Month 1)
1. Adjust Brightness for specific fabric types
2. Combine modes (Difference → Blend → Checkerboard)
3. Recognize patterns (systematic shifts vs local distortion)
4. Optimize point placement for minimal corrections

---

**Print this card and keep it near your workstation!**
