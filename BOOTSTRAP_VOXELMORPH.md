# Bootstrap VoxelMorph from Existing Registrations

## 🎯 Perfect for Your Use Case!

You have **perfectly registered fabric images** from past work. Instead of waiting months to collect Elastix deformations, you can **immediately train VoxelMorph** on your existing data!

## 🔑 Key Insight

**VoxelMorph doesn't need deformation fields!** For already-registered images, it learns the **identity transform** (no warping needed). Once trained:
- ✅ Use VoxelMorph for <1s registration of NEW designs
- ✅ Skip Elastix entirely for production
- ✅ Only run Elastix when you get a completely new fabric type
- ✅ Retrain VoxelMorph every few months with new samples

## 🚀 Quick Start (3 Commands)

### Option 1: Two Directories (Matched by Filename)

If you have directories like this:
```
camera_images/
├── fabric_001.png
├── fabric_002.png
└── fabric_003.png

registered_designs/
├── fabric_001.png  (already registered to camera_images/fabric_001.png)
├── fabric_002.png
└── fabric_003.png
```

Run:
```bash
python bootstrap_voxelmorph.py --fixed-dir camera_images --moving-dir registered_designs
```

### Option 2: Pairs List File

Create `registered_pairs.csv`:
```csv
fixed_path,moving_path
camera/fabric1.png,registered/design1.png
camera/fabric2.png,registered/design2.png
camera/fabric3.png,registered/design3.png
```

Run:
```bash
python bootstrap_voxelmorph.py --pairs-file registered_pairs.csv
```

### Option 3: Single Pair (Testing)

```bash
python bootstrap_voxelmorph.py --fixed camera.png --moving registered_design.png
```

## 📊 What Happens

1. **Script loads your images** (camera + registered design)
2. **Creates identity deformation** (zero displacement - images already aligned!)
3. **Saves to training data**: `data/voxelmorph_training/sample_XXXXX/`
4. **Shows progress**: "✓ Added: fabric_001.png → sample_1234567890"
5. **Summary**: "✅ Successfully added: 50 training pairs"

## 🎓 Training Workflow

After bootstrap:
```bash
# 1. Verify data added
python bootstrap_voxelmorph.py --fixed-dir ... --moving-dir ...
# Output: "✅ Successfully added: 50 training pairs"

# 2. Launch GUI
python gui/main_gui.py

# 3. Go to "🚀 VoxelMorph Training" tab

# 4. Click "🔄 Refresh"
# Shows: "Collected Samples: 50"

# 5. Click "▶️ Start Training"
# Settings: 100 epochs, 0.0001 lr, batch=4
# Wait ~15 minutes (50 samples × 100 epochs)

# 6. Training complete!
# Status: "✓ Trained" (green)

# 7. Restart GUI to refresh dropdown

# 8. Select "🚀 VoxelMorph PyTorch (GPU <1s)"

# 9. Register NEW designs in <1 second! ⚡
```

## 💡 Real-World Workflow

### Initial Setup (One Time)
```
Day 1: Bootstrap existing registrations (50+ samples)
    ↓
Day 1: Train VoxelMorph (15-20 minutes)
    ↓
Ready! Use VoxelMorph for all NEW designs
```

### Production (Daily)
```
New design arrives
    ↓
Select "VoxelMorph PyTorch" in GUI
    ↓
Register in <1 second ⚡
    ↓
Send to printer
```

### Monthly Maintenance (Optional)
```
New fabric type arrives
    ↓
Run Elastix once for this fabric
    ↓
Enable "💾 Save as VoxelMorph training data"
    ↓
Adds to training dataset
    ↓
Retrain VoxelMorph (20 minutes)
    ↓
Model improved!
```

## 📈 Benefits for Your Case

| Scenario | Time | Method |
|----------|------|--------|
| **First training** | 15-20 mins | Bootstrap from 50 existing pairs |
| **Daily production** | <1 second | VoxelMorph inference |
| **New fabric (rare)** | 3-5 seconds | Elastix once |
| **Retraining (monthly)** | 20 minutes | After collecting 10-20 new samples |

## 🎯 Your Specific Use Case

You mentioned:
- ✅ **"have so much of files to train"** → Perfect! Use bootstrap script
- ✅ **"perfect registration"** → Ideal! VoxelMorph learns identity transform
- ✅ **"not needing any bspline"** → Correct! Already registered = no deformation
- ✅ **"elastix will run for few months"** → No! Bootstrap now, train today
- ✅ **"after few months no elastix required"** → Exactly! VoxelMorph replaces it
- ✅ **"once every new design"** → No! Once per NEW FABRIC, not per design

## 🔧 Advanced Usage

### Filter by Pattern
```bash
# Only JPG files
python bootstrap_voxelmorph.py --fixed-dir camera --moving-dir designs --pattern "*.jpg"

# Only specific prefix
python bootstrap_voxelmorph.py --fixed-dir camera --moving-dir designs --pattern "fabric_*.png"
```

### Verify Before Training
```python
# Check what's in training data
python -c "
from python.advanced_registration.voxelmorph_pytorch import VoxelMorphTrainer
trainer = VoxelMorphTrainer()
stats = trainer.get_training_stats()
print(f'Samples: {stats[\"n_samples\"]}')
print(f'Directory: {stats[\"training_data_dir\"]}')
"
```

### Dry Run (See What Would Be Added)
The script shows progress:
```
Found 50 fixed images in: camera_images
Adding training pairs...
  ✓ Added: fabric_001.png → sample_1234567890
  ✓ Added: fabric_002.png → sample_1234567891
  ...
✅ Successfully added: 50 training pairs
```

## 🐛 Troubleshooting

### "No matching moving image"
- **Cause**: Filenames don't match exactly
- **Solution**: Use `--pairs-file` with explicit paths

### "Cannot load fixed image"
- **Cause**: File path wrong or image corrupted
- **Solution**: Check path exists with `ls` or `dir`

### "Resizing moving → fixed"
- **Normal**: Script auto-resizes if sizes differ
- **No action needed**: VoxelMorph handles this

### "Need more data: 5/10 samples"
- **Cause**: Less than 10 samples added
- **Solution**: Add more pairs (minimum 10, recommend 20-50)

## ✅ Verification Checklist

After running bootstrap:
- [ ] Script shows "✅ Successfully added: N training pairs"
- [ ] N ≥ 10 (minimum) or N ≥ 20 (recommended)
- [ ] Directory `data/voxelmorph_training/` contains `sample_*` folders
- [ ] Each `sample_*` folder has: `fixed.png`, `moving.png`, `deformation.npy`, `metadata.json`
- [ ] Open GUI → VoxelMorph Training tab → Click Refresh → Shows correct count
- [ ] Ready to click "▶️ Start Training"!

## 🎉 Expected Results

With 50 existing pairs:
- **Bootstrap**: 2-5 minutes
- **Training**: 15-20 minutes (100 epochs)
- **Result**: <1s registration for all future designs! ⚡

**No need to wait months for Elastix!** Start training today with your existing data.

---

**Next Step**: Run the bootstrap script on your existing registered images right now!
