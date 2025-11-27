# 🚀 VoxelMorph PyTorch - Quick Start

## What is VoxelMorph?

**VoxelMorph** is a deep learning approach to deformable image registration. Instead of running optimization algorithms (like Elastix), it uses a trained neural network to predict deformations in a single forward pass.

**Key Benefits**:
- ⚡ **6x faster**: <1 second vs 3-5 seconds for Elastix
- 🎯 **Operator-specific**: Train on your exact fabric types
- 🔄 **Continuous improvement**: Add more data over time
- 💾 **GPU-accelerated**: Leverage your RTX 4060 Ti

## How It Works

```
1. Collect Training Data (Use Elastix)
   Register 10-50 fabric pairs with Elastix
   ↓ (auto-save each registration)
   
2. Train VoxelMorph Model (One-time, 10 mins)
   Use collected data to train U-Net model
   ↓ (background training)
   
3. Use Trained Model (Fast Inference)
   Select VoxelMorph in dropdown
   ↓ (<1s GPU registration)
   
4. Keep Improving
   Add more training data → Retrain → Better results
```

## 3-Minute Setup

### Step 1: Collect Training Data (5 minutes)

1. Open Alinify GUI → **Registration** tab
2. Check ✅ **"💾 Save as VoxelMorph training data"** (Advanced Options)
3. Register 10+ fabric pairs with Elastix (your usual workflow)
   - Each registration auto-saves as training data
   - Mix different fabric types and patterns

### Step 2: Train Model (10 minutes)

1. Go to **🚀 VoxelMorph Training** tab
2. Click **"🔄 Refresh"** → Verify sample count (should be 10+)
3. Use default settings:
   - Epochs: **100**
   - Learning Rate: **0.0001**
   - Batch Size: **4**
   - Smoothness Weight: **0.01**
4. Click **"▶️ Start Training"**
5. Wait ~10 minutes (watch progress bar)
6. Training complete! → Model saved

### Step 3: Use VoxelMorph (Instant)

1. **Restart GUI** (to refresh dropdown)
2. Go to **Registration** tab
3. Select **"🚀 VoxelMorph PyTorch (GPU <1s)"** in method dropdown
4. Register as usual → **<1 second** completion! ⚡

## When to Use What?

| Scenario | Use... | Why? |
|----------|--------|------|
| First-time registration | **Elastix** | No trained model yet |
| Building training dataset | **Elastix** | Generate ground truth |
| Fast preview/iteration | **VoxelMorph** | 6x faster |
| Critical final registration | **Elastix** | Maximum quality |
| Production workflow | **VoxelMorph** | Speed + good quality |
| New fabric type | **Elastix** | Add to training data |

## Typical Workflow

```
Day 1: Setup
├── Register 10 fabrics with Elastix (checkbox on)
├── Train VoxelMorph for 100 epochs (~10 mins)
└── Ready!

Day 2+: Production
├── Use VoxelMorph for fast registration (<1s)
├── Occasionally use Elastix for critical cases
└── Collect more data when encountering new fabrics

Weekly: Improvement
├── Accumulated 20+ new samples
├── Retrain VoxelMorph (10 mins)
└── Model gets better!
```

## Troubleshooting

### "Insufficient Data" Error
- **Solution**: Register at least 5-10 fabric pairs with Elastix first

### VoxelMorph Not in Dropdown
- **Solution**: Check `models/voxelmorph_fabric.pth` exists, then restart GUI

### Poor VoxelMorph Quality
- **Solution**: Collect 20+ diverse training samples and retrain

### Slow Training
- **Normal**: 10 samples = ~3 mins, 50 samples = ~10 mins on RTX 4060 Ti

## Files & Locations

```
Alinify/
├── models/
│   └── voxelmorph_fabric.pth       # Trained model
├── data/
│   └── voxelmorph_training/        # Training data
│       ├── sample_001/
│       │   ├── fixed.png
│       │   ├── moving.png
│       │   ├── deformation.npy
│       │   └── metadata.json
│       ├── sample_002/
│       └── ...
└── python/advanced_registration/
    └── voxelmorph_pytorch.py       # Implementation
```

## Next Steps

1. ✅ **Read full guide**: `VOXELMORPH_TRAINING_GUIDE.md`
2. ✅ **Start collecting data**: Enable checkbox and register fabrics
3. ✅ **Train your first model**: VoxelMorph Training tab
4. ✅ **Test speed**: Compare VoxelMorph vs Elastix
5. ✅ **Keep improving**: Continuous data collection

## Questions?

- 📖 Full guide: `VOXELMORPH_TRAINING_GUIDE.md`
- 🔧 Technical details: `VOXELMORPH_IMPLEMENTATION.md`
- 📝 Main README: `README.md`

---

**You're ready to enjoy 6x faster registration!** 🚀
