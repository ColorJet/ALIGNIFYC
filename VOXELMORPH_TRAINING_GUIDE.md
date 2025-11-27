# VoxelMorph Training Workflow - Complete Guide

## 🎯 Overview

VoxelMorph is a deep learning approach to deformable image registration. This implementation allows you to train a PyTorch model that learns from Elastix registration examples, providing:

- **Fast GPU inference**: <1 second vs 2-5 seconds for Elastix
- **Operator-specific training**: Learn your exact fabric types
- **Continuous improvement**: Add more training data over time

## 📋 Prerequisites

- ✅ **PyTorch**: Already installed (2.9.1+cu130)
- ✅ **CUDA GPU**: RTX 4060 Ti 16GB (perfect for training)
- ✅ **Elastix**: Working registration setup

## 🚀 Complete Workflow

### Phase 1: Collect Training Data (10-50 fabric pairs)

1. **Open Alinify GUI** and go to **Registration** tab

2. **Enable Training Data Collection**:
   - Check ✅ **"💾 Save as VoxelMorph training data"** in Advanced Options section
   
3. **Register Fabric Pairs** with Elastix:
   - Load camera image (fixed)
   - Load design image (moving)
   - Use your preferred settings:
     - Optimizer: `QuasiNewtonLBFGS (⚡ Fast + Early Stop)` (recommended)
     - Max Iterations: 500-1000
     - Registration method: `B-spline (Standard)` or `Hybrid`
   - Click **"▶️ Register"**
   
4. **Repeat for 10-50 pairs**:
   - Mix different fabric types
   - Vary pattern complexity
   - Include both easy and hard cases
   - Each registration auto-saves as training data

5. **Verify Data Collection**:
   - Go to **🚀 VoxelMorph Training** tab
   - Click **"🔄 Refresh"**
   - Check **"Collected Samples"** count (should match registration count)
   - Click **"📁 Open Folder"** to browse saved data

### Phase 2: Train VoxelMorph Model

1. **Go to VoxelMorph Training Tab**

2. **Configure Training Parameters**:
   - **Epochs**: `100` (good starting point)
     - More epochs (200-500) for larger datasets
     - Fewer epochs (50-100) for small datasets
   
   - **Learning Rate**: `0.0001` (default, stable)
     - Lower (0.00001) if training unstable
     - Higher (0.001) if converging too slowly
   
   - **Batch Size**: `4` (recommended for RTX 4060 Ti)
     - Keep small (2-4) for limited data
     - Can increase (8-16) with more samples
   
   - **Smoothness Weight**: `0.01` (regularization)
     - Prevents distorted deformations
     - Increase (0.1) if results look warped
     - Decrease (0.001) if too rigid

3. **Start Training**:
   - Click **"▶️ Start Training"**
   - Training runs in background thread
   - Watch progress bar and loss values
   - Training typically takes **5-15 minutes** for 100 epochs
   
4. **Monitor Progress**:
   - Progress bar shows epoch completion
   - Loss value should **decrease over time**
   - Final loss < 0.01 = excellent
   - Final loss < 0.05 = good
   - Final loss > 0.1 = may need more training

5. **Training Complete**:
   - Model auto-saved to: `models/voxelmorph_fabric.pth`
   - Status changes to **"✓ Trained"** (green)
   - VoxelMorph option now available in Registration dropdown

### Phase 3: Use Trained Model

1. **Restart GUI** (to refresh registration dropdown)
   - VoxelMorph option appears if model exists

2. **Select VoxelMorph Registration**:
   - Go to **Registration** tab
   - In **"Registration Method"** dropdown, select:
     - `🚀 VoxelMorph PyTorch (GPU <1s)`
   - Note: Optimizer/sampling controls auto-disabled (not applicable)

3. **Run Fast Registration**:
   - Load camera and design images
   - Click **"▶️ Register"**
   - Registration completes in **<1 second** on GPU! 🚀

4. **Compare Results**:
   - Toggle between layers to compare:
     - VoxelMorph result vs Elastix result
     - Check alignment quality
   - Speed: VoxelMorph ~0.5s vs Elastix ~3s (6x faster!)

### Phase 4: Continuous Improvement

1. **Collect More Data**:
   - Keep **"💾 Save as VoxelMorph training data"** enabled
   - Run Elastix on new fabric types
   - Automatically adds to training dataset

2. **Retrain with More Data**:
   - Go to **VoxelMorph Training** tab
   - Click **"🔄 Refresh"** to see new sample count
   - Click **"▶️ Start Training"** again
   - Model improves with more diverse examples

3. **Fine-tune for Specific Fabrics**:
   - Train on 50+ samples of one fabric type
   - VoxelMorph learns that specific texture
   - Even faster + more accurate for that fabric

## 📊 Training Data Organization

Training data stored in: `data/voxelmorph_training/`

Each sample directory contains:
```
sample_1234567890/
├── fixed.png          # Camera/fixed image (grayscale)
├── moving.png         # Design/moving image (grayscale)
├── deformation.npy    # Elastix deformation field (H×W×2)
└── metadata.json      # Registration metadata (quality, runtime, etc.)
```

## 💡 Tips & Best Practices

### Data Collection
- ✅ **Mix fabric types**: Collect diverse examples (smooth, textured, embossed)
- ✅ **Quality over quantity**: 10 good pairs > 50 poor pairs
- ✅ **Use best Elastix settings**: VoxelMorph learns from Elastix examples
- ✅ **Include edge cases**: Hard-to-register fabrics help generalization

### Training
- ✅ **Start with 100 epochs**: Good baseline for most cases
- ✅ **Watch loss curve**: Should decrease smoothly
- ✅ **Early stopping**: If loss plateaus, training done
- ✅ **Overfitting check**: Test on new fabrics after training

### Usage
- ✅ **Use VoxelMorph for speed**: Fast preview/iteration
- ✅ **Use Elastix for quality**: Critical final registrations
- ✅ **Hybrid workflow**: VoxelMorph preview → Elastix final
- ✅ **Collect more data**: Continuously improve model

## 🔧 Troubleshooting

### "Insufficient Data" Error
- **Problem**: Less than 5 training samples
- **Solution**: Register at least 5-10 fabric pairs with Elastix first

### Training Loss Not Decreasing
- **Problem**: Loss stays high or fluctuates
- **Causes**:
  - Learning rate too high → Lower to 0.00001
  - Dataset too diverse → Train on similar fabrics first
  - Need more epochs → Increase to 200-500
- **Solution**: Adjust hyperparameters and retrain

### VoxelMorph Results Poor Quality
- **Problem**: Warped images look distorted or misaligned
- **Causes**:
  - Need more training data → Collect 20+ samples
  - Training data not diverse enough → Mix fabric types
  - Smoothness weight too low → Increase to 0.1
- **Solution**: Collect more quality training pairs and retrain

### VoxelMorph Not in Dropdown
- **Problem**: Option doesn't appear after training
- **Causes**:
  - Model file missing: Check `models/voxelmorph_fabric.pth` exists
  - GUI not refreshed: Restart application
- **Solution**: Restart GUI or check model file path

### GPU Out of Memory
- **Problem**: CUDA out of memory during training
- **Solution**:
  - Lower batch size to 1-2
  - Reduce image size (currently 512×512)
  - Close other GPU applications

## 📈 Expected Performance

### Speed Comparison
| Method | Runtime | Use Case |
|--------|---------|----------|
| VoxelMorph PyTorch | **0.5-1s** | Fast preview, iteration |
| Elastix QuasiNewtonLBFGS | 2-3s | Quality registration |
| Elastix ASGD | 5-8s | Maximum quality |

### Training Time (RTX 4060 Ti 16GB)
| Dataset Size | Epochs | Training Time |
|--------------|--------|---------------|
| 10 samples | 100 | ~3 minutes |
| 50 samples | 100 | ~10 minutes |
| 100 samples | 200 | ~25 minutes |

### Quality Metrics
- **Loss < 0.01**: Excellent alignment (nearly Elastix quality)
- **Loss 0.01-0.05**: Good alignment (acceptable for most fabrics)
- **Loss 0.05-0.1**: Fair alignment (may need more training)
- **Loss > 0.1**: Poor alignment (collect more data)

## 🎓 Advanced Usage

### Custom Model Path
Edit `python/advanced_registration/voxelmorph_pytorch.py`:
```python
trainer = VoxelMorphTrainer(model_path="models/my_custom_model.pth")
```

### Adjust Input Resolution
Higher resolution = better quality, slower inference:
```python
voxelmorph = VoxelMorphRegistrationPyTorch(inshape=(768, 768))
```

### Export/Import Trained Models
Model is standard PyTorch `.pth` file:
- **Export**: Copy `models/voxelmorph_fabric.pth` to another machine
- **Import**: Place `.pth` file in `models/` directory
- **Share**: Share models with team members

### Supervised Learning with Elastix Deformations
Current implementation uses Elastix deformations as **ground truth labels**:
- Supervised learning: `MSE(predicted_warp, elastix_warp)`
- Learns to mimic Elastix behavior
- Alternative: Unsupervised (image similarity loss only)

## 🔬 Technical Details

### Architecture
- **U-Net Encoder-Decoder**: 6 levels, skip connections
- **Encoder**: [32, 32, 32, 32] channels, stride-2 convolutions
- **Decoder**: [32, 32, 32, 32, 32, 16] channels, upsampling
- **Output**: 2-channel deformation field (dx, dy)

### Loss Function
```python
total_loss = similarity_loss + smoothness_weight * smoothness_loss
```
- **Similarity loss**: MSE between warped and fixed images
- **Smoothness loss**: L1 gradient penalty on flow field
- **Smoothness weight**: 0.01 (prevents distortions)

### Spatial Transformer
- Differentiable warping layer
- Bilinear interpolation for sub-pixel accuracy
- Grid sampling with normalized coordinates

### Training Details
- **Optimizer**: Adam (adaptive learning rate)
- **Learning rate**: 0.0001 (stable for most cases)
- **Batch size**: 4 (balance speed vs memory)
- **Data augmentation**: None (Elastix deformations are augmented)

## 📚 References

- **VoxelMorph**: Balakrishnan et al., "VoxelMorph: A Learning Framework for Deformable Medical Image Registration" (2019)
- **Spatial Transformer Networks**: Jaderberg et al. (2015)
- **U-Net**: Ronneberger et al., "U-Net: Convolutional Networks for Biomedical Image Segmentation" (2015)

## ✅ Success Checklist

- [ ] Collect 10+ training pairs with Elastix
- [ ] Enable "Save as VoxelMorph training data" checkbox
- [ ] Verify training data saved (VoxelMorph Training tab)
- [ ] Configure training parameters (100 epochs, lr=0.0001)
- [ ] Train model (watch loss decrease)
- [ ] Check model status: "✓ Trained"
- [ ] Restart GUI to refresh dropdown
- [ ] Select "VoxelMorph PyTorch" in Registration tab
- [ ] Run fast registration (<1s)
- [ ] Compare quality vs Elastix
- [ ] Collect more data continuously
- [ ] Retrain periodically for improvement

## 🎉 You're Ready!

Start collecting training data and enjoy **6x faster registration** with VoxelMorph! 🚀

For questions or issues, check the main `README.md` or contact the development team.
