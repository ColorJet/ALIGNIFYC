# Installing PyTorch with GPU Support

## ⚠️ IMPORTANT: Manual Installation Required

PyTorch with CUDA support **cannot** be installed via `pip install -r requirements.txt` because it requires a special index URL.

## 🚀 Installation Steps

### Step 1: Activate Virtual Environment
```powershell
cd d:\Alinify
.\venv\Scripts\Activate.ps1
```

### Step 2: Check Your CUDA Version
Run this to check your NVIDIA driver and CUDA version:
```powershell
nvidia-smi
```

### Step 3: Install PyTorch with CUDA

**For CUDA 12.1 (Most Common):**
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

**For CUDA 11.8:**
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**For CUDA 12.4:**
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

**CPU-only (Fallback):**
```powershell
pip install torch torchvision
```

### Step 4: Verify Installation
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Expected output if successful:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 5090
```

## 🔍 Troubleshooting

### Issue: "CUDA available: False"

**Possible causes:**
1. **Wrong CUDA version** - PyTorch CUDA version must match your installed CUDA
2. **Missing NVIDIA drivers** - Update your GPU drivers
3. **Installed CPU-only version** - Reinstall with correct index URL

**Solution:**
```powershell
# Uninstall current version
pip uninstall torch torchvision -y

# Check CUDA version
nvidia-smi

# Reinstall with matching CUDA version (e.g., 12.1)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Issue: "ModuleNotFoundError: No module named 'torch'"

PyTorch wasn't installed. Run the installation command above.

### Issue: "GPU not available" message in GUI

The registration will still work on CPU, but GPU warping will be disabled. Install PyTorch with CUDA as shown above.

## 📊 Performance Comparison

| Component | CPU | GPU (RTX 5090) |
|-----------|-----|----------------|
| Registration (Elastix) | ~10-15s | ~10-15s (CPU-bound) |
| RGB Warping (PyTorch) | ~2-5s | ~0.2-0.5s (10x faster!) |
| Large Images (4K+) | ~10-20s | ~1-2s (10-20x faster!) |

**Bottom line:** GPU mainly accelerates the RGB warping step. Registration is still fast on CPU.

## ✅ Verification

After installation, restart the GUI and check the log:
- ✅ **Good**: "Using device: cuda" 
- ⚠️ **CPU-only**: "Using device: cpu"

GPU acceleration will be automatically used if available!

## 🧠 Installing VoxelMorph (Advanced Registration)

After PyTorch is installed, install VoxelMorph for deep learning registration:

```powershell
pip install voxelmorph
```

**Verify VoxelMorph Installation:**
```powershell
python -c "from python.advanced_registration import VoxelMorphRegistration; backend = VoxelMorphRegistration(use_gpu=True); print(f'Available: {backend.available}'); print(f'Device: {backend.device}')"
```

**Expected Output:**
```
Available: True
Device: cuda:0
```

**Performance with VoxelMorph:**
- GPU (RTX 3060+): 0.5-1s per registration
- CPU (fallback): 10-15s per registration
- Memory: ~2GB VRAM for 512x512 images

**See also**: `python/advanced_registration/README.md` for complete VoxelMorph documentation

## 🔗 Official PyTorch Installation

For the latest instructions: https://pytorch.org/get-started/locally/

Select:
- PyTorch Build: **Stable**
- Your OS: **Windows**
- Package: **Pip**
- Language: **Python**
- Compute Platform: **CUDA 12.1** (or your version)
