# Thread Pattern Registration Guide

## Problem Analysis: Thread vs Intensity-Based Images

### **Your Examples:**
1. **Floral Pattern** (Top image): 
   - ✅ Works well with intensity-based registration
   - Clear color boundaries, white background
   - Features defined by **color contrast**

2. **Thread Texture** (Bottom image):
   - ❌ Fails with standard registration  
   - Features defined by **thread direction/orientation**
   - Similar gray intensities but different **gradient directions**

## Root Cause

**Standard registration metrics:**
- `AdvancedMeanSquares`: Compares pixel intensities
- `AdvancedMattesMutualInformation`: Compares intensity distributions

**Thread patterns need:**
- `NormalizedGradientCorrelation`: Compares **gradient directions**
- Focus on **texture orientation** rather than pixel values

## Solutions for Thread Patterns

### **1. Automatic Thread Detection** ✨
The system now auto-detects thread-like textures by analyzing:
- **Gradient magnitude**: High gradients indicate directional patterns
- **Gradient consistency**: Thread patterns have strong directional gradients
- **Low intensity variation**: Threads often have similar colors but different orientations

**Auto-detection triggers when:**
```python
# Thread-like conditions:
fixed_gradient_mean > 15 AND moving_gradient_mean > 15
# OR manual thread mode enabled
```

### **2. Thread-Optimized Registration**

#### **New GUI Controls:**
- ✅ **"Thread/Texture" preset button**
- ✅ **"Thread/texture mode" checkbox** 
- ✅ **NormalizedGradientCorrelation metric**

#### **Optimal Thread Parameters:**
```
Grid Spacing: 48 (medium - captures thread weave patterns)
Max Iterations: 800 (more time for texture matching)  
Spatial Samples: 12000 (higher sampling for texture correlation)
Step Size: 0.4 (careful steps for precision)
Metric: AdvancedNormalizedCorrelation (2D-compatible)
Thread Enhancement: Enabled (bilateral filter + sharpening)
```

### **3. Enhanced Preprocessing for Threads**

**Standard images:** Aggressive CLAHE (clipLimit=3.0, tiles=8x8)
**Thread images:** Gentle CLAHE (clipLimit=2.0, tiles=16x16)
- Preserves gradient information
- Avoids over-enhancement that destroys directional patterns

## How to Use for Thread Patterns

### **Method 1: Automatic (Recommended)**
1. Load your thread images
2. Keep **"Auto-detect best metric"** ✅ enabled
3. Run registration
4. System detects thread patterns and switches to gradient-based registration automatically

### **Method 2: Manual**
1. Load your thread images  
2. Click **"Thread/Texture"** preset button
3. Verify settings:
   - Metric: `NormalizedGradientCorrelation`
   - Thread mode: ✅ enabled
4. Run registration

### **Method 3: Fine-tuning**
If automatic detection doesn't work:
1. **Enable "Thread/texture mode"** manually
2. **Adjust grid spacing**:
   - `32`: Fine thread details
   - `48`: Medium weave patterns  
   - `64`: Coarse fabric textures
3. **Increase samples** to 10000+ for complex patterns

## Expected Results

### **Before (Standard Registration):**
- Thread patterns appear "blurry" or misaligned
- System tries to match pixel intensities (wrong approach)
- Poor registration quality

### **After (Gradient Registration):**  
- ✅ Thread orientations properly aligned
- ✅ Weave patterns match correctly
- ✅ Better handling of similar-colored threads with different directions

## Technical Details

### **Gradient Analysis Pipeline:**
```python
1. Compute Sobel gradients (X and Y directions)
2. Calculate gradient magnitude and direction
3. Compare gradient patterns instead of intensities  
4. Use NormalizedGradientCorrelation metric
5. Optimize for directional alignment
```

### **Thread Detection Algorithm:**
```python
# Calculate gradients for both images
grad_x = cv2.Sobel(image, CV_64F, 1, 0, ksize=3)  
grad_y = cv2.Sobel(image, CV_64F, 0, 1, ksize=3)
grad_mag = sqrt(grad_x² + grad_y²)

# Thread detection criteria
if grad_mag.mean() > 15:
    # Strong directional patterns detected
    switch_to_gradient_registration()
```

## Testing Your Thread Images

### **For the bottom image (thread texture):**
1. **Expected detection**: "Thread-like texture detected - switching to NormalizedGradientCorrelation"
2. **Parameters**: Grid=48, Samples=8000, Gradient-based metric
3. **Result**: Much better alignment of thread directions

### **Troubleshooting:**
- **Still not working?** Try **"Fine Details"** preset + manual **"Thread mode"**
- **Over-registered?** Increase grid spacing to 64-80
- **Under-registered?** Decrease grid spacing to 32, increase samples to 12000

## When to Use Each Approach

| Image Type | Best Metric | Grid Size | Use Case |
|------------|-------------|-----------|----------|
| **Color patterns** | AdvancedMeanSquares | 64 | Your floral example |
| **Different backgrounds** | AdvancedMattesMutualInformation | 64 | Mixed intensity ranges |
| **Thread textures** | NormalizedGradientCorrelation | 48 | Your thread example |
| **Fine thread details** | NormalizedGradientCorrelation | 32 | High-resolution fabric |

---

**Bottom Line:** Your thread pattern should now register correctly with the new gradient-based approach! 🧵✨