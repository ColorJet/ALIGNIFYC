# Pattern Tiling → B-spline Warping Workflow

## 🎯 What Happens Step-by-Step

```
INPUT:
┌─────────────────────┐         ┌─────────────────────┐
│  Camera Image       │         │  Design (1 pattern) │
│  (Fabric with       │         │                     │
│   5×3 grid)         │         │    [Pattern]        │
│                     │         │                     │
│  [P] [P] [P] [P] [P]│         │   80×80 pixels      │
│  [P] [P] [P] [P] [P]│         │                     │
│  [P] [P] [P] [P] [P]│         └─────────────────────┘
│                     │
│  650×430 pixels     │
└─────────────────────┘

                ↓

STEP 1: PATTERN TILING (5% - 8%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creates full pattern-filled image matching fabric size

Two modes:

A) Simple Tiling (wallpaper):
   - Just repeats pattern with np.tile()
   - No intelligence about positions

B) Smart Alignment (recommended):
   - Detects pattern positions in camera
   - Places pattern at detected locations
   - Handles rotation/scale variations

Result:
┌─────────────────────┐
│  Tiled Pattern      │
│  (Full coverage)    │
│                     │
│  [P] [P] [P] [P] [P]│
│  [P] [P] [P] [P] [P]│
│  [P] [P] [P] [P] [P]│
│                     │
│  650×430 pixels     │
│                     │
│  ⚠️ Still FLAT,     │
│     no deformation  │
└─────────────────────┘

Saved to: output/tiled_pattern_before_registration.png
Layer added: "Tiled Pattern (before warp)"

                ↓

STEP 2: PREPROCESSING (10% - 25%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Optional: Enhance images for better registration
- Fixed (Camera): Texture enhance, edge detect, etc.
- Moving (Tiled Pattern): Edge enhance, etc.

                ↓

STEP 3: B-SPLINE REGISTRATION (30% - 100%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Elastix B-spline algorithm warps the tiled pattern
to match fabric deformations:
- Stretching
- Wrinkles
- Perspective distortion
- Local deformations

┌─────────────────────┐         ┌─────────────────────┐
│  Tiled Pattern      │         │  Camera (Fabric)    │
│  (FLAT)             │   →→→   │  (Has distortions)  │
│                     │  WARP   │                     │
│  [P] [P] [P] [P] [P]│         │  [P] [P] [P] [P][P] │
│  [P] [P] [P] [P] [P]│         │ [P] [P]  [P] [P] [P]│
│  [P] [P] [P] [P] [P]│         │  [P][P] [P] [P] [P] │
└─────────────────────┘         └─────────────────────┘
     Moving Image                     Fixed Image

Result:
┌─────────────────────┐
│  Registered Pattern │
│  (WARPED to match   │
│   fabric)           │
│                     │
│  [P] [P] [P] [P][P] │
│ [P] [P]  [P] [P] [P]│
│  [P][P] [P] [P] [P] │
│                     │
│  Now matches fabric │
│  deformations! ✓    │
└─────────────────────┘

Layer added: "Registered"

                ↓

OUTPUT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Registered image (warped pattern)
✓ Deformation field (for high-res warping)
✓ Can export or apply manual corrections
```

## 📊 What You See in GUI

### Layer Panel (Left):
```
👁 Camera                [Opacity: 100%]
👁 Tiled Pattern         [Opacity: 70%]  ← Added at step 1
👁 Registered            [Opacity: 80%]  ← Added at step 3
```

### Log Messages:
```
[0%]  Starting registration...
[5%]  🔲 Creating full pattern-filled image (smart alignment)...
[8%]  ✓ Pattern-filled image ready: 650×430
[8%]  📐 Pattern-filled image created (BEFORE B-spline warping)
[9%]  → Now B-spline will warp this pattern to match fabric deformations
[30%] Running registration algorithm...
[50%] Registration iteration 100/200...
[100%] Registration complete!
[100%] ✅ Background registration completed!
```

## 🔍 Files Created

1. **`output/tiled_pattern_before_registration.png`**
   - Full pattern-filled image (BEFORE warping)
   - Shows pattern tiled across entire fabric size
   - This is what gets fed into B-spline

2. **Registered image (in memory)**
   - Result after B-spline warping
   - Pattern now matches fabric deformations
   - Can be exported

## 🎛️ How to Control This

### GUI Checkboxes:
```
☑ Tile pattern across fabric
   → Enables pattern tiling (Step 1)
   
☑ Smart pattern alignment (recommended)
   → Uses intelligent detection
   → Places pattern at detected positions
   
☐ Smart pattern alignment
   → Uses simple wallpaper tiling
```

### What Happens:
1. **No tiling checkbox**: Single design → B-spline → Warped
2. **Simple tiling**: Design → Repeat pattern → B-spline → Warped
3. **Smart tiling**: Design → Detect positions → Place pattern → B-spline → Warped

## 💡 Key Insight

**Pattern tiling does NOT replace B-spline!**

- **Tiling** = Creates full pattern-filled image
- **B-spline** = Warps that image to match fabric deformations

Both work together:
```
Single Pattern → [TILING] → Full Pattern → [B-SPLINE] → Warped Pattern
     80×80                    650×430                      650×430
                                                         (matches fabric)
```

## ✅ Verification

To confirm it's working:

1. **Check layer panel**: Should see "Tiled Pattern (before warp)" layer
2. **Check output folder**: Should have `tiled_pattern_before_registration.png`
3. **Toggle layer visibility**: Compare tiled vs registered
4. **Look at log**: Should show both tiling (8%) and registration (30%+) steps

This is exactly what you wanted:
- ✅ Pattern filled across fabric
- ✅ THEN B-spline warps it for deformations
