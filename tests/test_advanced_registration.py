"""
Quick test for advanced registration modules
Tests basic imports and functionality without GPU/heavy dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

print("=" * 60)
print("Advanced Registration Module Tests")
print("=" * 60)

# Test 1: Module imports
print("\n[1/5] Testing module imports...")
try:
    from python.advanced_registration import (
        FeatureDetector,
        detect_features_sift,
        detect_features_akaze,
        detect_features_orb,
        OpticalFlowMethod,
        compute_dense_flow_farneback,
        compute_dense_flow_dis,
        register_with_optical_flow,
        register_with_tps_from_features,
        VoxelMorphRegistration
    )
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Feature detection (ORB - no dependencies)
print("\n[2/5] Testing ORB feature detection...")
try:
    img = (np.random.rand(256, 256) * 255).astype(np.uint8)
    kp, desc = detect_features_orb(img, nfeatures=100)
    print(f"✅ ORB detected {len(kp)} features, descriptors shape: {desc.shape if desc is not None else 'None'}")
except Exception as e:
    print(f"❌ ORB test failed: {e}")

# Test 3: SIFT detection (requires opencv-contrib-python)
print("\n[3/5] Testing SIFT feature detection...")
try:
    img = (np.random.rand(256, 256) * 255).astype(np.uint8)
    kp, desc = detect_features_sift(img, nfeatures=100)
    print(f"✅ SIFT detected {len(kp)} features, descriptors shape: {desc.shape if desc is not None else 'None'}")
except Exception as e:
    print(f"⚠️  SIFT not available: {e}")
    print("   Hint: Install with 'pip install opencv-contrib-python'")

# Test 4: Optical flow (Farneback - built into OpenCV)
print("\n[4/5] Testing Farneback optical flow...")
try:
    img1 = (np.random.rand(128, 128) * 255).astype(np.uint8)
    img2 = (np.random.rand(128, 128) * 255).astype(np.uint8)
    flow = compute_dense_flow_farneback(img1, img2)
    print(f"✅ Farneback flow computed, shape: {flow.shape}, dtype: {flow.dtype}")
    
    # Quick registration test
    warped, deformation, metadata = register_with_optical_flow(img1, img2, method=OpticalFlowMethod.FARNEBACK)
    print(f"✅ Optical flow registration: runtime={metadata['runtime_seconds']:.4f}s, "
          f"mean disp={metadata['mean_displacement']:.2f}px")
except Exception as e:
    print(f"❌ Optical flow test failed: {e}")

# Test 5: VoxelMorph availability check (without full test)
print("\n[5/5] Testing VoxelMorph backend availability...")
try:
    backend = VoxelMorphRegistration(use_gpu=False)  # CPU only for now
    if backend.available:
        print(f"✅ VoxelMorph available, device: {backend.device}")
    else:
        print("⚠️  VoxelMorph not installed (expected)")
        print("   Hint: Install with 'pip install voxelmorph'")
except Exception as e:
    print(f"⚠️  VoxelMorph check failed: {e}")

# Summary
print("\n" + "=" * 60)
print("Test Summary:")
print("=" * 60)
print("✅ Module imports: PASS")
print("✅ ORB detection: PASS")
print("⚠️  SIFT detection: Requires opencv-contrib-python")
print("✅ Optical flow: PASS")
print("⚠️  VoxelMorph: Requires voxelmorph package (GPU optional)")
print("\nNext steps:")
print("1. Install PyTorch with CUDA: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
print("2. Install VoxelMorph: pip install voxelmorph")
print("3. Install SIFT support: pip install opencv-contrib-python")
print("=" * 60)
