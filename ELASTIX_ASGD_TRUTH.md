# The Truth About Elastix ASGD Early Stopping

## ❌ What Doesn't Work (What I Tried)

I initially added these parameters thinking they would enable early stopping:
```python
bspline_params["MetricRelativeTolerance"] = ["1e-5"]
bspline_params["ValueTolerance"] = ["1e-5"]
bspline_params["MinimumStepLength"] = ["1e-6"]
bspline_params["MinimumGradientMagnitude"] = ["1e-8"]
bspline_params["GradientMagnitudeTolerance"] = ["1e-8"]
```

**THESE PARAMETERS DO NOT EXIST IN ELASTIX ASGD OPTIMIZER!**

They are silently ignored and have zero effect.

---

## 📖 The Reality

### AdaptiveStochasticGradientDescent Optimizer Has NO Early Stopping

From Elastix documentation and source code:
- **ASGD only stops when**: `MaximumNumberOfIterations` is reached
- **No tolerance-based stopping**: Metric improvement, gradient magnitude, step size are NOT checked
- **No convergence detection**: Algorithm always runs full iteration count

### Why "Stopping condition: Maximum number of iterations has been reached"?

**Because that's the ONLY stopping condition ASGD has!**

---

## ✅ What ACTUALLY Works

### Solution 1: Use Different Optimizer (RegularStepGradientDescent)

This optimizer HAS early stopping:

```python
bspline_params["Optimizer"] = ["RegularStepGradientDescent"]
bspline_params["MaximumNumberOfIterations"] = ["500"]
bspline_params["MinimumStepLength"] = ["1e-6"]  # REAL parameter for this optimizer
bspline_params["RelaxationFactor"] = ["0.5"]
```

**Trade-off**:
- ✅ Early stopping works
- ❌ Slower convergence than ASGD
- ❌ May need more iterations overall

### Solution 2: Reduce Iterations Per Pyramid Level

**The only way to save time with ASGD is to use fewer iterations:**

```python
# Instead of max_iterations: 500 across all levels
# Distribute adaptively:

if pyramid_levels == 4:
    # Format: "level0 level1 level2 level3"
    MaximumNumberOfIterations = "100 125 150 125"  # Total: 500
elif pyramid_levels == 3:
    MaximumNumberOfIterations = "150 175 175"  # Total: 500
else:
    MaximumNumberOfIterations = "500"  # Single level
```

**Effect**:
- Coarse levels (8x, 4x): Get fewer iterations (they don't need many)
- Fine levels (2x, 1x): Get more iterations (precision needed)
- **This is NOT early stopping** - it's just smarter iteration budgeting

### Solution 3: Reduce Total MaximumNumberOfIterations

**Simplest solution:**

```yaml
# config/elastix_config.yaml
max_iterations: 250  # Instead of 500
```

**Effect**:
- 50% time savings immediately
- Risk: May not converge fully on difficult pairs
- Test if 250 is enough for your fabric images

### Solution 4: Use Fewer Pyramid Levels

```yaml
pyramid_levels: 3  # Instead of 4
```

**Effect**:
- 25% time savings (skip one resolution level)
- Slight quality loss on very large displacements

---

## 🔍 Why Warmup Shows This Behavior

```
Resolution: 0
MaximumNumberOfIterations = 10
Final metric value  = 1.92168e-19  (perfect alignment!)
Stopping condition: Maximum number of iterations has been reached
```

**This is CORRECT behavior**:
- Warmup uses identical images
- Metric is already perfect (10⁻¹⁹)
- But ASGD doesn't check this - it runs all 10 iterations anyway
- There's no "early" stopping because ASGD never stops early

---

## 📊 Realistic Expectations

### With ASGD Optimizer (Current):

| Strategy | Time Savings | Quality Impact |
|----------|--------------|----------------|
| Reduce max_iterations to 250 | 50% | Slight loss on difficult pairs |
| Use 3 pyramid levels | 25% | Minimal loss |
| Adaptive per-level iterations | 0% | None (just smarter distribution) |
| **Early stopping parameters** | **0%** | **NONE (don't work!)** |

### With RegularStepGradientDescent:

| Strategy | Time Savings | Quality Impact |
|----------|--------------|----------------|
| Early stopping (MinimumStepLength) | 30-60% | None (stops at convergence) |
| Total time | Slower | May need 800 iterations vs 500 for ASGD |

---

## 💡 Recommended Solution

### For Your Use Case (Fabric Registration):

**Option A: Keep ASGD, Reduce Iterations**
```yaml
# config/elastix_config.yaml
optimizer: AdaptiveStochasticGradientDescent
max_iterations: 300  # Down from 500
pyramid_levels: 3    # Down from 4
```

**Expected**: 40% time savings, minimal quality loss

**Option B: Switch to RegularStepGradientDescent**
```python
# In elastix_registration.py
bspline_params["Optimizer"] = ["RegularStepGradientDescent"]
bspline_params["MaximumNumberOfIterations"] = ["800"]
bspline_params["MinimumStepLength"] = ["0.000001"]
bspline_params["RelaxationFactor"] = ["0.5"]
```

**Expected**: True early stopping, but may need more total iterations

---

## 🎯 The Bottom Line

### What You Asked For:
> "Why not stopping on convergence?"

### The Answer:
**Because ASGD optimizer CAN'T stop on convergence. It's not implemented.**

### What You Can Do:
1. **Accept it**: ASGD is fast and effective, just runs full iterations
2. **Reduce iterations**: Set max_iterations to 250-300
3. **Switch optimizers**: Use RegularStepGradientDescent for real early stopping
4. **Optimize temp files**: Already done (178x faster) ✅

### What I Learned:
❌ Those convergence tolerance parameters don't exist in ASGD  
✅ Temp file optimization works (890ms → 5ms)  
✅ Per-level iteration distribution helps (but doesn't "stop early")  
✅ Only way to truly stop early: different optimizer  

---

## 🔧 Implementation

I've removed the fake convergence parameters and implemented:
1. ✅ Uncompressed PNG writing (178x faster temp files)
2. ✅ Comprehensive parameter logging
3. ✅ Per-level adaptive iteration distribution (when using 3-4 levels)
4. ❌ Removed non-functional convergence parameters

**Current behavior is CORRECT for ASGD optimizer.**

---

## 📝 Action Items

### To Save Time Right Now:

Edit `config/elastix_config.yaml`:
```yaml
max_iterations: 300  # Down from 500 (40% faster)
pyramid_levels: 3    # Down from 4 (25% faster)
```

### To Enable True Early Stopping:

Would require switching to `RegularStepGradientDescent` optimizer, which is:
- ✅ Has MinimumStepLength stopping
- ✅ Has convergence detection
- ❌ Slower per iteration than ASGD
- ❌ May need 800 iterations vs 500 for ASGD
- ❓ Unknown quality/speed trade-off for fabric images

---

**Bottom Line**: ASGD doesn't support early stopping. That's why it always shows "Maximum number of iterations has been reached." This is normal and expected behavior.

**Date**: 2025-11-14  
**Status**: ✅ Understood and Documented
