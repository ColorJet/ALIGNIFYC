"""
Real Image Test for NVIDIA Warp Acceleration
============================================

Test NVIDIA Warp vs PyTorch with actual fabric images
from your Alinify dataset.

Author: GitHub Copilot  
Date: November 2025
"""

import sys
import numpy as np
import cv2
import time
from pathlib import Path

# Add the python directory to path
sys.path.append(str(Path(__file__).parent))

from warp_acceleration import WarpAcceleratedWarper
from elastix_registration import ElastixFabricRegistration

def test_with_real_images():
    """Test Warp acceleration with real fabric images"""
    
    print("🧵 Real Fabric Image Test - NVIDIA Warp vs PyTorch")
    print("=" * 60)
    
    # Look for example images in the project
    image_paths = []
    
    # Check common image directories
    search_dirs = [
        Path("examples"),
        Path("test_images"), 
        Path("data"),
        Path("."),
        Path("python")
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            # Look for common image formats
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']:
                image_paths.extend(search_dir.glob(ext))
                image_paths.extend(search_dir.glob(ext.upper()))
    
    if not image_paths:
        print("⚠️  No real images found. Creating synthetic fabric test...")
        return test_with_synthetic_fabric()
    
    print(f"✓ Found {len(image_paths)} images")
    
    # Initialize systems
    warper = WarpAcceleratedWarper(enable_profiling=True)
    registration = ElastixFabricRegistration()
    
    # Test with first available image
    test_image_path = image_paths[0]
    print(f"\n🔬 Testing with: {test_image_path.name}")
    
    try:
        # Load real fabric image
        image = cv2.imread(str(test_image_path))
        if image is None:
            raise ValueError(f"Could not load image: {test_image_path}")
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        original_shape = image_rgb.shape
        
        print(f"  Original size: {original_shape[1]}x{original_shape[0]} ({(original_shape[0]*original_shape[1])/1e6:.1f}MP)")
        
        # Test different resolutions
        test_sizes = []
        
        # Add original size if reasonable
        if original_shape[0] * original_shape[1] <= 25e6:  # Up to 25MP
            test_sizes.append((original_shape[1], original_shape[0], f"Original ({original_shape[1]}x{original_shape[0]})"))
        
        # Add standard test sizes
        test_sizes.extend([
            (2048, 2048, "2K Standard"),
            (1024, 1024, "1K Preview") 
        ])
        
        results = {}
        
        for width, height, description in test_sizes:
            print(f"\n📐 Testing {description}: {width}x{height}")
            print("-" * 50)
            
            # Resize image for test
            if (width, height) != (original_shape[1], original_shape[0]):
                test_image = cv2.resize(image_rgb, (width, height), interpolation=cv2.INTER_AREA)
            else:
                test_image = image_rgb
            
            # Create realistic deformation (simulate fabric stretch/shift)
            deform_x, deform_y = create_fabric_deformation(width, height, test_image)
            
            print(f"  ✓ Image prepared: {test_image.shape}")
            print(f"  ✓ Deformation created: max displacement ±{max(np.abs(deform_x).max(), np.abs(deform_y).max()):.1f}px")
            
            # Benchmark both methods
            num_iterations = 3
            
            # Test Warp
            warp_times = []
            if warper.use_warp:
                print(f"  🚀 Testing NVIDIA Warp ({num_iterations} iterations)...")
                for i in range(num_iterations):
                    start = time.time()
                    warp_result = warper.warp_image_realtime(test_image, deform_x, deform_y, interpolation="bilinear")
                    warp_time = time.time() - start
                    warp_times.append(warp_time)
                    print(f"    Iteration {i+1}: {warp_time*1000:.1f}ms")
                
                avg_warp = np.mean(warp_times) * 1000
                warp_fps = 1000 / avg_warp
            else:
                avg_warp = float('inf')
                warp_fps = 0
                warp_result = None
            
            # Test PyTorch
            print(f"  🐍 Testing PyTorch fallback ({num_iterations} iterations)...")
            pytorch_times = []
            for i in range(num_iterations):
                start = time.time()
                pytorch_result = warper.warp_image_realtime(test_image, deform_x, deform_y, force_pytorch=True)
                pytorch_time = time.time() - start
                pytorch_times.append(pytorch_time)
                print(f"    Iteration {i+1}: {pytorch_time*1000:.1f}ms")
            
            avg_pytorch = np.mean(pytorch_times) * 1000  
            pytorch_fps = 1000 / avg_pytorch
            
            speedup = avg_pytorch / avg_warp if avg_warp != float('inf') else 1.0
            
            # Quality comparison
            quality_diff = 0
            if warp_result is not None:
                quality_diff = np.mean(np.abs(warp_result.astype(np.float32) - pytorch_result.astype(np.float32)))
            
            # Store results
            results[description] = {
                'warp_ms': avg_warp,
                'pytorch_ms': avg_pytorch,
                'warp_fps': warp_fps,
                'pytorch_fps': pytorch_fps,
                'speedup': speedup,
                'quality_diff': quality_diff,
                'realtime_warp': warp_fps >= 30,
                'realtime_pytorch': pytorch_fps >= 30
            }
            
            # Print summary
            print(f"\n  📊 Results for {description}:")
            if avg_warp != float('inf'):
                print(f"    🚀 Warp:    {avg_warp:.1f}ms ({warp_fps:.1f} fps) {'✓' if warp_fps >= 30 else '✗'}")
            print(f"    🐍 PyTorch: {avg_pytorch:.1f}ms ({pytorch_fps:.1f} fps) {'✓' if pytorch_fps >= 30 else '✗'}")
            if speedup != 1.0:
                print(f"    ⚡ Speedup: {speedup:.1f}x")
                print(f"    🎯 Quality: {quality_diff:.1f} (lower = better)")
        
        # Final summary
        print(f"\n" + "=" * 60)
        print(f"🏆 REAL IMAGE PERFORMANCE SUMMARY")
        print(f"📸 Test image: {test_image_path.name}")
        print("=" * 60)
        
        print(f"{'Resolution':<20} {'Warp (fps)':<12} {'PyTorch (fps)':<14} {'Speedup':<10}")
        print("-" * 65)
        
        for desc, data in results.items():
            speedup_str = f"{data['speedup']:.1f}x" if data['speedup'] != 1.0 else "N/A"
            warp_fps_str = f"{data['warp_fps']:.1f}" if data['warp_fps'] > 0 else "N/A"
            print(f"{desc:<20} {warp_fps_str:<12} {data['pytorch_fps']:<14.1f} {speedup_str:<10}")
        
        # Recommendations
        best_realtime = [desc for desc, data in results.items() if data['realtime_warp']]
        if best_realtime:
            print(f"\n💡 For real-time fabric processing:")
            print(f"   ✅ Use NVIDIA Warp up to: {best_realtime[-1]}")
            print(f"   🎯 Recommended for live fabric inspection!")
        
        return results
        
    except Exception as e:
        print(f"❌ Error testing with real image: {e}")
        return test_with_synthetic_fabric()

def create_fabric_deformation(width: int, height: int, fabric_image: np.ndarray) -> tuple:
    """Create realistic fabric deformation based on image content"""
    
    # Analyze fabric image to create realistic deformation
    gray = cv2.cvtColor(fabric_image, cv2.COLOR_RGB2GRAY)
    
    # Detect fabric features for deformation guidance
    edges = cv2.Canny(gray, 50, 150)
    
    # Create base deformation
    max_displacement = min(width, height) * 0.02  # 2% of image size
    
    # Generate smooth deformation field
    base_x = np.random.randn(height // 8, width // 8) * max_displacement
    base_y = np.random.randn(height // 8, width // 8) * max_displacement
    
    # Upsample
    deform_x = cv2.resize(base_x, (width, height), interpolation=cv2.INTER_CUBIC)
    deform_y = cv2.resize(base_y, (width, height), interpolation=cv2.INTER_CUBIC)
    
    # Smooth for realistic fabric behavior
    deform_x = cv2.GaussianBlur(deform_x, (15, 15), 0)
    deform_y = cv2.GaussianBlur(deform_y, (15, 15), 0)
    
    # Add localized distortions based on fabric features
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours[:5]:  # Use top 5 features
        if cv2.contourArea(contour) > 100:
            # Get centroid
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Add localized deformation
                Y, X = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
                dist = np.sqrt((X - cx)**2 + (Y - cy)**2)
                
                strength = max_displacement * 0.5
                sigma = np.random.uniform(20, 80)
                
                local_deform = strength * np.exp(-dist**2 / (2 * sigma**2))
                angle = np.random.uniform(0, 2 * np.pi)
                
                deform_x += local_deform * np.cos(angle)
                deform_y += local_deform * np.sin(angle)
    
    return deform_x.astype(np.float32), deform_y.astype(np.float32)

def test_with_synthetic_fabric():
    """Fallback test with synthetic fabric"""
    print("📄 Using synthetic fabric for testing...")
    
    from test_warp_performance import create_test_fabric_image, create_realistic_deformation
    
    # Create high-quality synthetic fabric
    fabric = create_test_fabric_image(2048, 2048)
    deform_x, deform_y = create_realistic_deformation(2048, 2048, 15.0)
    
    warper = WarpAcceleratedWarper(enable_profiling=True)
    
    print(f"\n🧪 Synthetic Fabric Test: 2048x2048")
    print("-" * 40)
    
    # Test both methods
    start = time.time()
    warp_result = warper.warp_image_realtime(fabric, deform_x, deform_y)
    warp_time = (time.time() - start) * 1000
    
    start = time.time()  
    pytorch_result = warper.warp_image_realtime(fabric, deform_x, deform_y, force_pytorch=True)
    pytorch_time = (time.time() - start) * 1000
    
    print(f"🚀 Warp:    {warp_time:.1f}ms ({1000/warp_time:.1f} fps)")
    print(f"🐍 PyTorch: {pytorch_time:.1f}ms ({1000/pytorch_time:.1f} fps)")
    print(f"⚡ Speedup: {pytorch_time/warp_time:.1f}x")
    
    return {"synthetic": {"warp_ms": warp_time, "pytorch_ms": pytorch_time}}

if __name__ == "__main__":
    print("🧵 NVIDIA Warp Real Image Performance Test")
    print("🎯 Testing with actual fabric images from your dataset")
    print()
    
    results = test_with_real_images()
    
    print(f"\n🎉 Real image testing completed!")
    print(f"\nNext: Add GUI dropdown for Warp/PyTorch selection in main interface")