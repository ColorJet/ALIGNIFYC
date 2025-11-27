# Advanced Registration Methods Implementation Plan
**Timeline: 1 Month (November 14 - December 14, 2025)**

## Overview
Integrate learning-based deformable registration (VoxelMorph, DeepReg) and conventional alternatives (SIFT/SURF, thin-plate splines) as optional backends with comparative benchmarking.

## GitHub References
- **VoxelMorph**: https://github.com/voxelmorph/voxelmorph
  - State-of-the-art unsupervised learning for deformable medical image registration
  - Pre-trained models available, PyTorch support
  
- **DeepReg**: https://github.com/DeepRegNet/DeepReg
  - Unified deep learning framework for medical image registration
  - TensorFlow 2.x based, extensible architecture
  
- **Survey Paper**: https://arxiv.org/abs/2111.10480
  - Comprehensive review of deep learning in medical image registration
  - Algorithm taxonomy and performance benchmarks

---

## Phase 1: Foundation (Week 1, Nov 14-21)
**Goal**: Set up ML infrastructure and missing conventional methods

### Tasks
1. **Environment Setup** (2 days)
   - ✅ Already have: PyTorch placeholder in requirements.txt
   - [ ] Install PyTorch with CUDA 12.1 support
   - [ ] Add VoxelMorph, SimpleITK, scikit-image dependencies
   - [ ] Create GPU detection/fallback logic
   - [ ] Document installation steps

2. **SIFT/SURF Feature Matching** (2 days)
   - [ ] Implement SIFT/AKAZE as alternatives to ORB
   - [ ] Add dropdown: "Feature detector: ORB/SIFT/AKAZE"
   - [ ] Test on fabric patterns vs line-scan images
   - [ ] Compare inlier counts and alignment quality

3. **Thin-Plate Spline Registration** (1 day)
   - [ ] Use SimpleITK's `ThinPlateSplineTransform`
   - [ ] Add to fine registration options
   - [ ] Compare with B-spline on controlled test cases

4. **Benchmarking Framework** (2 days)
   - [ ] Extend `tests/preproc_smoke.py` to `tests/benchmark_registration.py`
   - [ ] Metrics: MI (mutual information), TRE (target registration error), RMSE, time
   - [ ] Auto-generate comparison tables and plots
   - [ ] Test dataset: 10 fabric image pairs with ground truth annotations

**Deliverable**: Working SIFT/TPS, initial benchmark harness, GPU setup verified

---

## Phase 2: VoxelMorph Integration (Week 2, Nov 22-28)
**Goal**: Integrate pre-trained VoxelMorph for 2D fabric registration

### Tasks
1. **VoxelMorph Backend** (3 days)
   - [ ] Clone VoxelMorph repo, study 2D registration examples
   - [ ] Create `python/voxelmorph_registration.py` wrapper
   - [ ] Load pre-trained 2D model or train lightweight model on fabric data
   - [ ] Handle GPU/CPU inference with proper error handling
   - [ ] Return deformation field in same format as Elastix

2. **GUI Integration** (1 day)
   - [ ] Add "Fine registration: B-spline / Thin-plate / VoxelMorph" dropdown
   - [ ] Show GPU status indicator (green = available, red = CPU fallback)
   - [ ] Add progress bar for ML inference

3. **Testing & Validation** (2 days)
   - [ ] Run on 20 fabric test cases
   - [ ] Compare VoxelMorph vs B-spline: speed, accuracy, robustness
   - [ ] Document failure modes (e.g., extreme deformations)
   - [ ] Measure GPU memory usage

4. **Optimization** (1 day)
   - [ ] Batch processing for multiple frames
   - [ ] Model quantization (FP16) for faster inference
   - [ ] Cache compiled models to avoid JIT overhead

**Deliverable**: VoxelMorph running in GUI, preliminary comparison showing 2-5x speedup vs Elastix

---

## Phase 3: DeepReg & Advanced Features (Week 3, Nov 29-Dec 5)
**Goal**: Add DeepReg alternative, optical flow methods

### Tasks
1. **DeepReg Integration** (3 days)
   - [ ] Install DeepReg (TensorFlow 2.x)
   - [ ] Adapt their unsupervised registration pipeline for fabrics
   - [ ] Convert TF models to ONNX for cross-framework compatibility
   - [ ] Benchmark against VoxelMorph

2. **Optical Flow Fallback** (2 days)
   - [ ] Implement dense optical flow using `cv2.calcOpticalFlowFarneback`
   - [ ] Add RAFT (optical flow transformer) as advanced option
   - [ ] Compare flow fields with deformation fields from registration
   - [ ] Use for real-time preview during camera acquisition

3. **SuperPoint Feature Detector** (Optional, 2 days)
   - [ ] Download pre-trained SuperPoint weights
   - [ ] Integrate into smart tiling workflow
   - [ ] Benchmark vs SIFT on low-texture fabrics

**Deliverable**: DeepReg available, optical flow working, optional SuperPoint path

---

## Phase 4: Comprehensive Benchmarking (Week 4, Dec 6-14)
**Goal**: Scientific comparison of all methods with publication-quality results

### Tasks
1. **Benchmark Suite** (3 days)
   - [ ] Curate 50+ diverse fabric test cases:
     - Tone-on-tone white embroidery
     - High-contrast printed patterns
     - Elastic/stretched fabrics
     - Multi-scale patterns (short repeats)
   - [ ] Generate synthetic ground-truth deformations
   - [ ] Run all methods with identical preprocessing

2. **Metrics & Analysis** (2 days)
   - [ ] Quantitative: MI, TRE, RMSE, Dice coefficient, Jacobian determinant
   - [ ] Qualitative: Visual inspection, checkerboard overlays
   - [ ] Performance: Runtime, GPU memory, CPU fallback speed
   - [ ] Robustness: Success rate vs failure modes

3. **Automated Comparison** (2 days)
   - [ ] Generate comparison matrix (methods × metrics × datasets)
   - [ ] Create visualizations: box plots, scatter plots, heatmaps
   - [ ] Write markdown report with recommendations
   - [ ] Add to GUI: "Run Benchmark Suite" menu option

4. **Documentation** (2 days)
   - [ ] Method selection guide (when to use B-spline vs VoxelMorph vs DeepReg)
   - [ ] Installation guide for GPU dependencies
   - [ ] Troubleshooting FAQ
   - [ ] Update README with benchmark results

**Deliverable**: Complete comparison document, production-ready multi-method system

---

## Implementation Details

### New Python Modules
```
python/
├── voxelmorph_registration.py    # VoxelMorph backend wrapper
├── deepreg_registration.py       # DeepReg backend wrapper
├── optical_flow.py                # Dense flow methods (Farneback, RAFT)
├── feature_detectors.py           # SIFT, AKAZE, SuperPoint
└── benchmark_framework.py         # Automated testing harness

tests/
├── benchmark_registration.py     # Main benchmark script
├── test_voxelmorph.py             # VoxelMorph unit tests
├── test_deepreg.py                # DeepReg unit tests
└── generate_test_data.py          # Synthetic deformation generator
```

### GUI Changes
```python
# Registration Settings
combo_fine_registration = QComboBox()
combo_fine_registration.addItems([
    "B-spline (Elastix)",           # Default
    "Thin-plate Spline",            # SimpleITK
    "VoxelMorph (GPU)",             # Deep learning
    "DeepReg (GPU)",                # Deep learning
    "Dense Optical Flow"            # Real-time fallback
])

# Coarse Alignment
combo_feature_detector = QComboBox()
combo_feature_detector.addItems([
    "ORB (Fast)",                   # Current default
    "SIFT (Robust)",                # OpenCV
    "AKAZE (Hybrid)",               # OpenCV
    "SuperPoint (GPU)",             # Deep learning
    "Phase Correlation (FFT)"       # No features
])

# GPU Status
lbl_gpu_status = QLabel()
if torch.cuda.is_available():
    lbl_gpu_status.setText("🟢 GPU Available (CUDA 12.1)")
else:
    lbl_gpu_status.setText("🔴 CPU Only (Install CUDA for speedup)")
```

### Config File Extension
```yaml
# config/registration_config.yaml
advanced:
  fine_registration_method: "bspline"  # bspline | tps | voxelmorph | deepreg | optical_flow
  feature_detector: "orb"              # orb | sift | akaze | superpoint
  use_gpu: true
  gpu_memory_limit_gb: 4
  enable_benchmarking: true

voxelmorph:
  model_path: "models/voxelmorph_2d_fabric.pt"
  inference_batch_size: 1
  half_precision: true

deepreg:
  model_path: "models/deepreg_unet.h5"
  use_onnx: true
```

---

## Benchmark Comparison Matrix (Expected Results)

| Method | Speed (GPU) | Speed (CPU) | Accuracy | Robustness | GPU Memory | Best For |
|--------|-------------|-------------|----------|------------|------------|----------|
| **B-spline (Elastix)** | 5-10s | 5-10s | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | General purpose, interpretable |
| **Thin-plate Spline** | 3-5s | 3-5s | ⭐⭐⭐ | ⭐⭐⭐ | N/A | Sparse landmarks, fast |
| **VoxelMorph** | 0.5-1s | 10-15s | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 2GB | Large deformations, fast |
| **DeepReg** | 0.8-1.5s | 12-18s | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 3GB | Multi-modal, uncertainty |
| **Optical Flow** | 0.2-0.5s | 1-2s | ⭐⭐⭐ | ⭐⭐ | 0.5GB | Real-time preview |

### Feature Detection Comparison

| Detector | Speed | Inliers (avg) | Low-Texture | GPU | Notes |
|----------|-------|---------------|-------------|-----|-------|
| **ORB** | Fast | 150 | ⭐⭐ | No | Current default |
| **SIFT** | Medium | 300 | ⭐⭐⭐⭐ | No | Best quality |
| **AKAZE** | Fast | 200 | ⭐⭐⭐ | No | Good balance |
| **SuperPoint** | Very Fast | 400 | ⭐⭐⭐⭐⭐ | Yes | Tone-on-tone expert |
| **Phase Correlation** | Very Fast | N/A | ⭐⭐⭐⭐ | No | Periodic patterns |

---

## Risk Assessment & Mitigation

### High Risk
1. **GPU Dependency Issues**
   - *Risk*: Users may not have CUDA installed or compatible GPUs
   - *Mitigation*: CPU fallbacks for all ML methods, clear error messages, optional GPU features
   
2. **Model Training Data Mismatch**
   - *Risk*: Pre-trained medical image models may not generalize to fabrics
   - *Mitigation*: Fine-tune on 100+ fabric pairs, provide pre-trained checkpoint

3. **Integration Complexity**
   - *Risk*: TensorFlow (DeepReg) vs PyTorch (VoxelMorph) version conflicts
   - *Mitigation*: Use ONNX runtime for cross-framework compatibility

### Medium Risk
4. **Performance on Edge Cases**
   - *Risk*: Extreme deformations or very low-texture images may fail
   - *Mitigation*: Ensemble approach (try ML first, fall back to conventional)

5. **Timeline Slippage**
   - *Risk*: One month may be tight for full DeepReg integration + benchmarking
   - *Mitigation*: Prioritize VoxelMorph (Week 2-3), make DeepReg optional (Week 4)

### Low Risk
6. **SIFT/SURF Patent Issues**
   - *Risk*: SIFT algorithm was patented (expired 2020)
   - *Mitigation*: Use OpenCV's SIFT (post-patent) or AKAZE (free alternative)

---

## Success Criteria

### Must-Have (MVP)
- ✅ All conventional methods working (SIFT, TPS, CLAHE, Gabor, Frangi, Structure Tensor)
- ✅ VoxelMorph integrated with GPU support and CPU fallback
- ✅ Benchmark framework comparing 5+ methods on 20+ test cases
- ✅ GUI dropdowns for method selection
- ✅ Documentation with installation guide

### Should-Have
- ✅ DeepReg integration (if time permits)
- ✅ SuperPoint feature detector
- ✅ Optical flow real-time preview
- ✅ Automated report generation

### Nice-to-Have
- ✅ Model fine-tuning on fabric-specific datasets
- ✅ Uncertainty quantification for ML predictions
- ✅ Multi-GPU support for batch processing
- ✅ ONNX export for all models

---

## Team Resources Needed

| Task | Estimated Hours | Skills Required |
|------|----------------|-----------------|
| SIFT/TPS Implementation | 16 | OpenCV, SimpleITK |
| VoxelMorph Integration | 40 | PyTorch, deep learning |
| DeepReg Integration | 32 | TensorFlow, ONNX |
| Benchmark Framework | 24 | Data science, visualization |
| GUI Updates | 16 | PySide6, UX design |
| Documentation | 16 | Technical writing |
| Testing & Validation | 24 | QA, statistical analysis |
| **TOTAL** | **168 hours** | ~1 FTE month |

---

## Dependencies to Add

```txt
# requirements_advanced.txt (for full ML stack)
torch>=2.0.0
torchvision>=0.15.0
voxelmorph>=0.2
tensorflow>=2.12.0  # For DeepReg
onnxruntime-gpu>=1.15.0
neurite>=0.2        # VoxelMorph dependency
kornia>=0.7.0       # Differentiable CV operations
opencv-contrib-python>=4.8.0  # SIFT/SURF support
```

### Installation Command
```powershell
# GPU (Recommended)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements_advanced.txt

# CPU Fallback
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements_advanced.txt
```

---

## Checkpoint Milestones

### Week 1 Checkpoint (Nov 21)
- [ ] GPU setup verified on development machine
- [ ] SIFT/AKAZE working, showing better inlier counts than ORB
- [ ] TPS registration 2x faster than B-spline for simple cases
- [ ] Benchmark harness running on 10 test images

### Week 2 Checkpoint (Nov 28)
- [ ] VoxelMorph inference working on GPU (<1s per image)
- [ ] Visual comparison shows VoxelMorph handles large deformations better
- [ ] GUI dropdown for method selection functional
- [ ] CPU fallback tested and documented

### Week 3 Checkpoint (Dec 5)
- [ ] DeepReg running (optional if VoxelMorph excels)
- [ ] Optical flow preview working in camera acquisition
- [ ] 30+ test cases with ground truth annotations
- [ ] Initial benchmark results generated

### Week 4 Checkpoint (Dec 14)
- [ ] Full comparison report complete
- [ ] Recommendation guide: "Use VoxelMorph for speed, B-spline for robustness"
- [ ] Documentation updated with screenshots
- [ ] Code merged to main branch, tagged as v2.0

---

## Post-Implementation Optimization (Optional, Week 5+)

1. **Fine-tuning VoxelMorph on Fabric Dataset**
   - Collect 500+ fabric image pairs
   - Train for 10 epochs on A100 GPU (~4 hours)
   - Expected accuracy improvement: 10-15%

2. **ONNX Model Zoo**
   - Convert all models to ONNX
   - Host on GitHub releases
   - Enable cross-platform inference (Windows/Linux/Mac)

3. **Ensemble Methods**
   - Combine predictions from multiple models
   - Weighted average based on confidence scores
   - Adaptive fallback strategy

4. **Real-time Streaming**
   - Integrate with camera acquisition pipeline
   - Register frames on-the-fly at 10+ FPS
   - GPU queue for asynchronous processing

---

## Conclusion

**Is 1 month achievable?** 

**Yes, with prioritization:**
- **Weeks 1-2**: Focus on VoxelMorph + conventional methods (high confidence)
- **Week 3**: Add DeepReg *only if VoxelMorph integration is smooth*
- **Week 4**: Polish benchmarking and documentation

**Stretch goals (DeepReg, SuperPoint, fine-tuning) can slip to Week 5-6 without breaking MVP.**

The core value—operator-selectable registration backends with automated comparison—is achievable in 4 weeks with daily commits and iterative testing.

---

*Created: November 14, 2025*
*Target Completion: December 14, 2025*
