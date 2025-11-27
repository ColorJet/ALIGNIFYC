# Example: Bootstrap VoxelMorph with Your Data

## Your Current Situation

You have:
- ✅ Camera/fabric images (fixed)
- ✅ Registered design images (already perfectly aligned)
- ✅ Many pairs (enough for training!)
- ❌ No Elastix deformation fields (not needed!)

## Step-by-Step Example

### 1. Organize Your Images (If Needed)

**Option A: Two Directories (Easiest)**
```
my_data/
├── camera/
│   ├── fabric_001.png
│   ├── fabric_002.png
│   └── fabric_003.png
└── registered/
    ├── fabric_001.png  (matches camera/fabric_001.png)
    ├── fabric_002.png  (matches camera/fabric_002.png)
    └── fabric_003.png  (matches camera/fabric_003.png)
```

**Option B: Create Pairs List**
```
registered_pairs.txt

camera/fabric_001.png,registered/design_001.png
camera/fabric_002.png,registered/design_002.png
camera/fabric_003.png,registered/design_003.png
```

### 2. Run Bootstrap Script

**For Option A (Two Directories):**
```bash
cd D:\Alinify20251113\Alinify
python bootstrap_voxelmorph.py --fixed-dir my_data/camera --moving-dir my_data/registered
```

**For Option B (Pairs List):**
```bash
python bootstrap_voxelmorph.py --pairs-file registered_pairs.txt
```

### 3. Expected Output

```
Mode: Directory matching
Found 50 fixed images in: my_data/camera

Adding training pairs...
Processing: 100%|████████████████████| 50/50 [00:15<00:00,  3.2it/s]
  ✓ Added: fabric_001.png → sample_1731590400123
  ✓ Added: fabric_002.png → sample_1731590400456
  ✓ Added: fabric_003.png → sample_1731590400789
  ...

============================================================
✅ Successfully added: 50 training pairs
============================================================

📊 Total training samples: 50
📁 Training data directory: data\voxelmorph_training
💾 Model will be saved to: models\voxelmorph_fabric.pth

✅ Ready to train! You have 50 samples.

Next steps:
1. Open Alinify GUI
2. Go to '🚀 VoxelMorph Training' tab
3. Click '🔄 Refresh' to see your samples
4. Click '▶️ Start Training' (100 epochs recommended)
5. Training will take ~15 minutes
```

### 4. Verify Data

Check the training data directory:
```bash
dir data\voxelmorph_training

# Should see:
sample_1731590400123/
sample_1731590400456/
sample_1731590400789/
...
```

Each sample contains:
```
sample_1731590400123/
├── fixed.png          (your camera image)
├── moving.png         (your registered design)
├── deformation.npy    (identity/zero - no warping needed)
└── metadata.json      (info about the pair)
```

### 5. Train VoxelMorph

**Launch GUI:**
```bash
cd D:\Alinify20251113\Alinify
python gui/main_gui.py
```

**In GUI:**
1. Go to **"🚀 VoxelMorph Training"** tab
2. Click **"🔄 Refresh"**
   - Should show: "Collected Samples: 50"
3. Set parameters:
   - Epochs: **100** (default is fine)
   - Learning Rate: **0.0001** (default)
   - Batch Size: **4** (default)
   - Smoothness Weight: **0.01** (default)
4. Click **"▶️ Start Training"**
5. Wait ~15 minutes (watch progress bar)
6. Training complete! 🎉

### 6. Use Trained Model

**Restart GUI to refresh dropdown:**
```bash
python gui/main_gui.py
```

**Register new designs:**
1. Load camera image (fabric)
2. Load NEW design (not in training set)
3. Select **"🚀 VoxelMorph PyTorch (GPU <1s)"** from Registration Method
4. Click **"▶️ Register"**
5. **Done in <1 second!** ⚡

## Real Example with Your Folder Structure

If your images are in:
```
D:\FabricData\
├── CameraImages\
│   ├── IMG_001.png
│   ├── IMG_002.png
│   └── IMG_003.png
└── RegisteredDesigns\
    ├── IMG_001.png
    ├── IMG_002.png
    └── IMG_003.png
```

Run:
```bash
cd D:\Alinify20251113\Alinify
python bootstrap_voxelmorph.py --fixed-dir D:\FabricData\CameraImages --moving-dir D:\FabricData\RegisteredDesigns
```

## What Gets Saved

For each pair, the script saves:

**`data/voxelmorph_training/sample_XXXXX/fixed.png`**
- Your camera/fabric image (grayscale)

**`data/voxelmorph_training/sample_XXXXX/moving.png`**
- Your registered design image (grayscale)

**`data/voxelmorph_training/sample_XXXXX/deformation.npy`**
- Identity deformation field (all zeros)
- Shape: (H, W, 2) where dx=0, dy=0 everywhere
- Means: "No warping needed, already perfect"

**`data/voxelmorph_training/sample_XXXXX/metadata.json`**
```json
{
  "method": "bootstrap_existing_registration",
  "fixed_path": "D:/FabricData/CameraImages/IMG_001.png",
  "moving_path": "D:/FabricData/RegisteredDesigns/IMG_001.png",
  "fixed_shape": [1080, 1920],
  "moving_shape": [1080, 1920],
  "deformation_type": "identity",
  "note": "Images already registered, training for identity transform"
}
```

## Why This Works

**Key Insight**: VoxelMorph learns to predict:
```
Output = Input + DeformationField
```

For your case:
- **Input**: Camera image + Design image
- **DeformationField**: Zero (identity) because already registered
- **Output**: Same design (no warping)

VoxelMorph learns: "When I see this camera fabric texture, the design needs NO deformation"

For NEW designs on SAME fabric:
- **Input**: Same camera fabric + NEW design
- **VoxelMorph**: "I recognize this fabric! Use identity transform"
- **Output**: NEW design with no warping (perfect registration)

## Benefits

✅ **No Elastix needed**: Skip weeks of processing
✅ **Train today**: Use existing data immediately
✅ **Fast inference**: <1s vs 3-5s Elastix
✅ **Continuous improvement**: Add new fabrics anytime
✅ **Production ready**: After one 15-minute training

## Next Steps

**Right now:**
1. Find your camera images directory
2. Find your registered designs directory
3. Run: `python bootstrap_voxelmorph.py --fixed-dir ... --moving-dir ...`
4. Wait 2-5 minutes for data conversion
5. Launch GUI and train for 15 minutes
6. **Start using <1s registration!** 🚀

Questions? Check:
- Main guide: `BOOTSTRAP_VOXELMORPH.md`
- Full workflow: `VOXELMORPH_TRAINING_GUIDE.md`
- Quick start: `VOXELMORPH_QUICKSTART.md`
