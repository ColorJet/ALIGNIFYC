# Optimizer Quick Reference Card

## 🎯 Which Optimizer Should I Use?

### ⚡ QuasiNewtonLBFGS (DEFAULT)
**Best for**: Real-time fabric alignment  
**Speed**: ⚡⚡⚡ (Fastest)  
**Early Stop**: ✅ Yes  
**When**: Interactive registration, well-aligned images  
**Speedup**: 50-70% faster than ASGD  

### ⚖️ ConjugateGradientFRPR
**Best for**: General-purpose registration  
**Speed**: ⚡⚡ (Fast)  
**Early Stop**: ✅ Yes  
**When**: Unknown image types, balanced needs  
**Speedup**: 30-50% faster than ASGD  

### 🎯 RegularStepGradientDescent
**Best for**: Difficult registrations  
**Speed**: ⚡ (Moderate)  
**Early Stop**: ✅ Yes  
**When**: Severely misaligned, stability critical  
**Speedup**: 10-30% faster than ASGD  

### 🔄 AdaptiveStochasticGradientDescent
**Best for**: Batch processing with consistent timing  
**Speed**: ⚡⚡ (Fast but no early stop)  
**Early Stop**: ❌ No  
**When**: Noisy images, predictable timing needed  
**Speedup**: None (always runs full iterations)  

### 📊 StandardGradientDescent
**Best for**: Simple cases, learning  
**Speed**: ⚡ (Moderate)  
**Early Stop**: ✅ Yes  
**When**: Basic registration, debugging  
**Speedup**: 20-40% faster than ASGD  

---

## 📋 Decision Tree

```
Start: Need to register fabric images
│
├─ Is speed critical? (real-time, interactive)
│  YES → QuasiNewtonLBFGS ⚡
│  │
│  └─ Are images similar/well-aligned?
│     YES → QuasiNewtonLBFGS ⚡ (70% faster!)
│     NO  → Try RegularStepGradientDescent 🎯
│
├─ Is stability most important?
│  YES → RegularStepGradientDescent 🎯
│  │
│  └─ Are images severely misaligned?
│     YES → RegularStepGradientDescent 🎯
│     NO  → ConjugateGradientFRPR ⚖️
│
├─ Need consistent timing? (batch processing)
│  YES → AdaptiveStochasticGradientDescent 🔄
│  │
│  └─ Are images noisy/have outliers?
│     YES → AdaptiveStochasticGradientDescent 🔄
│     NO  → QuasiNewtonLBFGS ⚡ (faster with early stop)
│
└─ Don't know what to choose?
   → QuasiNewtonLBFGS ⚡ (best default)
```

---

## 🚦 Quick Settings Guide

### For Speed (Real-time)
```
Optimizer:        QuasiNewtonLBFGS
Max Iterations:   500 (will stop early ~100-200)
Grid Spacing:     32-48 (coarser = faster)
Spatial Samples:  3000-5000
Pyramid Levels:   3
```

### For Quality (Batch)
```
Optimizer:        QuasiNewtonLBFGS or RegularStepGradientDescent
Max Iterations:   800-1000
Grid Spacing:     16-24 (finer = better quality)
Spatial Samples:  8000-10000
Pyramid Levels:   4
```

### For Difficult Cases
```
Optimizer:        RegularStepGradientDescent
Max Iterations:   1000-1500
Grid Spacing:     24-32
Spatial Samples:  6000-8000
Pyramid Levels:   4-5
```

### For Consistent Timing
```
Optimizer:        AdaptiveStochasticGradientDescent
Max Iterations:   500 (always runs full)
Grid Spacing:     32-64
Spatial Samples:  5000
Pyramid Levels:   3
```

---

## ⏱️ Expected Performance

| Optimizer | Typical Time | Iterations | Early Stop |
|-----------|--------------|------------|------------|
| QuasiNewtonLBFGS | 0.8-1.5s | 100-200 | ✅ |
| ConjugateGradientFRPR | 1.2-2.0s | 150-300 | ✅ |
| RegularStepGradientDescent | 1.5-2.5s | 200-400 | ✅ |
| ASGD | 2.5s | 500 | ❌ |
| StandardGradientDescent | 1.8-2.3s | 180-350 | ✅ |

*Based on 1024x1024 fabric images, 3 pyramid levels, 5000 samples*

---

## 🎨 GUI Quick Access

### In Alinify GUI:
1. Click **Registration Settings** tab
2. Find **Optimizer** group box
3. Select from dropdown:
   ```
   QuasiNewtonLBFGS (⚡ Fast + Early Stop)    ← Default
   ConjugateGradientFRPR (⚖️ Balanced)
   RegularStepGradientDescent (🎯 Stable)
   AdaptiveStochasticGradientDescent (🔄 Robust)
   StandardGradientDescent (📊 Simple)
   ```
4. Read info label below for guidance
5. Click **Register Images**

### Keyboard Shortcuts (in dropdown):
- `Q` → QuasiNewtonLBFGS
- `C` → ConjugateGradientFRPR
- `R` → RegularStepGradientDescent
- `A` → AdaptiveStochasticGradientDescent
- `S` → StandardGradientDescent

---

## 🔧 Troubleshooting

### Problem: Registration is slow
**Solution**: Switch to QuasiNewtonLBFGS, reduce grid spacing, or reduce spatial samples

### Problem: Poor quality alignment
**Solution**: 
1. Increase spatial samples (5000 → 8000)
2. Decrease grid spacing (64 → 32)
3. Try RegularStepGradientDescent for stability
4. Increase max iterations

### Problem: Registration fails or crashes
**Solution**:
1. Switch to RegularStepGradientDescent (most stable)
2. Reduce pyramid levels (4 → 3)
3. Increase max iterations (500 → 1000)
4. Enable enhanced preprocessing

### Problem: Inconsistent timing in batch processing
**Solution**: Use AdaptiveStochasticGradientDescent (always runs full iterations)

### Problem: Not sure if early stopping is working
**Check console output**:
- QuasiNewtonLBFGS should show: "Converged!" or "MinimumStepLength reached"
- ASGD shows: "Maximum number of iterations has been reached"

---

## 💡 Pro Tips

1. **Start with QuasiNewtonLBFGS**: It's the best default for 90% of cases

2. **Watch the console**: Look for "Converged!" vs "Maximum iterations reached"

3. **Adjust max_iterations**: Set it high (800-1000) as safety limit - deterministic optimizers will stop early

4. **Grid spacing matters**: 
   - 16-24: Fine details (slow)
   - 32-48: Balanced (recommended)
   - 64-96: Coarse (fast, less accurate)

5. **Spatial samples trade-off**:
   - 3000: Fast but less accurate
   - 5000: Good balance (recommended)
   - 8000+: Best quality, slower

6. **Pyramid levels**:
   - 2-3: Faster, less robust
   - 4: Balanced (recommended)
   - 5+: Most robust, slower

7. **Test first**: Run a quick test with your images to find optimal settings

8. **Save presets**: Note settings that work well for your specific image types

---

## 📞 Need Help?

### Check Documentation:
- `OPTIMIZER_IMPLEMENTATION_SUMMARY.md` - Complete overview
- `GUI_OPTIMIZER_DROPDOWN.md` - GUI detailed guide
- `DETERMINISTIC_OPTIMIZER_SUCCESS.md` - Technical details

### Run Tests:
```bash
# Quick test
python test_quick_optimizer.py

# Full fabric comparison
python test_fabric_optimizers.py
```

### Common Questions:

**Q: Why is my registration still slow with QuasiNewtonLBFGS?**  
A: Images may be severely misaligned. Check console for iteration count. If hitting max_iterations, try increasing it or use RegularStepGradientDescent.

**Q: Which optimizer is most accurate?**  
A: All produce similar accuracy. QuasiNewtonLBFGS converges fastest, RegularStepGradientDescent is most stable for difficult cases.

**Q: Should I ever use ASGD?**  
A: Yes, for batch processing where consistent timing matters, or for very noisy images with many outliers.

**Q: How do I know if early stopping worked?**  
A: Check console output. Look for "Converged!" or iteration count < max_iterations.

**Q: Can I use different optimizers for different image pairs?**  
A: Yes! Select optimizer per registration. QuasiNewtonLBFGS for easy cases, RegularStepGradientDescent for hard cases.

---

**Last Updated**: January 14, 2025  
**Default Optimizer**: QuasiNewtonLBFGS (⚡ Fast + Early Stop)  
**Recommended for Real-time**: QuasiNewtonLBFGS  
**Recommended for Batch**: AdaptiveStochasticGradientDescent  
**Recommended for Quality**: RegularStepGradientDescent
