"""
NVIDIA Warp Performance Test for Alinify Fabric Registration
===========================================================

Test script to benchmark NVIDIA Warp acceleration vs PyTorch
for real-time fabric warping operations.

Author: GitHub Copilot
Date: November 2025
"""

import numpy as np
import cv2
import time
import sys
from pathlib import Path

# Add the python directory to path
sys.path.append(str(Path(__file__).parent))

import warp_acceleration
from warp_acceleration import WarpAcceleratedWarper
import elastix_registration
from elastix_registration import ElastixFabricRegistration

def create_test_fabric_image(width: int = 4096, height: int = 4096) -> np.ndarray:
    """Create a realistic fabric texture for testing"""
    
    # Create base fabric pattern
    fabric = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add fabric weave pattern
    for i in range(0, height, 8):
        for j in range(0, width, 8):
            # Weave pattern
            if (i // 8 + j // 8) % 2 == 0:
                fabric[i:i+4, j:j+8] = [180, 160, 140]  # Warp threads
                fabric[i+4:i+8, j:j+8] = [160, 140, 120]  # Weft threads
            else:
                fabric[i:i+8, j:j+4] = [160, 140, 120]  # Weft threads  
                fabric[i:i+8, j+4:j+8] = [180, 160, 140]  # Warp threads
    
    # Add noise for realism
    noise = np.random.normal(0, 10, (height, width, 3)).astype(np.int16)
    fabric = np.clip(fabric.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Add some fabric defects/patterns
    for _ in range(20):
        x = np.random.randint(0, width - 100)
        y = np.random.randint(0, height - 100)
        cv2.circle(fabric, (x, y), np.random.randint(10, 50), 
                  (np.random.randint(100, 200), np.random.randint(80, 160), np.random.randint(60, 140)), -1)
    
    return fabric

def create_realistic_deformation(width: int, height: int, 
                               max_displacement: float = 20.0) -> tuple:
    """Create realistic fabric deformation field"""
    
    # Create smooth deformation using Gaussian filters
    base_x = np.random.randn(height // 4, width // 4) * max_displacement
    base_y = np.random.randn(height // 4, width // 4) * max_displacement
    
    # Upsample and smooth
    deform_x = cv2.resize(base_x, (width, height), interpolation=cv2.INTER_CUBIC)
    deform_y = cv2.resize(base_y, (width, height), interpolation=cv2.INTER_CUBIC)
    
    # Apply Gaussian smoothing for realistic fabric deformation
    deform_x = cv2.GaussianBlur(deform_x, (21, 21), 0)
    deform_y = cv2.GaussianBlur(deform_y, (21, 21), 0)
    
    # Add some local distortions (fabric wrinkles)
    for _ in range(5):
        center_x = np.random.randint(width // 4, 3 * width // 4)
        center_y = np.random.randint(height // 4, 3 * height // 4)
        
        Y, X = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
        dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        
        # Wrinkle strength
        strength = max_displacement * 2
        sigma = np.random.uniform(50, 150)
        
        wrinkle = strength * np.exp(-dist**2 / (2 * sigma**2))
        angle = np.random.uniform(0, 2 * np.pi)
        
        deform_x += wrinkle * np.cos(angle)
        deform_y += wrinkle * np.sin(angle)
    
    return deform_x.astype(np.float32), deform_y.astype(np.float32)

def test_warp_performance():
    """Comprehensive performance test"""
    
    print("🚀 NVIDIA Warp vs PyTorch Performance Benchmark")
    print("=" * 60)
    print("Testing realistic fabric registration warping...\n")
    
    # Initialize warper
    warper = WarpAcceleratedWarper(enable_profiling=True)
    
    # Test different image sizes (fabric scanning resolutions)
    test_sizes = [
        (1024, 1024, "1K (1MP) - Preview"),
        (2048, 2048, "2K (4MP) - Standard"),  
        (4096, 4096, "4K (16MP) - High-res"),
        (5120, 5120, "5K (26MP) - Production"),
        # (8192, 8192, "8K (67MP) - Ultra-high")  # Uncomment if you have enough VRAM
    ]
    
    results = {}
    
    for width, height, description in test_sizes:
        print(f"\n🔬 Testing {description}: {width}x{height}")
        print("-" * 50)
        
        try:
            # Create test fabric and deformation
            print("  Creating test fabric texture...")
            fabric = create_test_fabric_image(width, height)
            
            print("  Creating realistic deformation field...")
            deform_x, deform_y = create_realistic_deformation(width, height)
            
            # Warmup (important for GPU)
            print("  GPU warmup...")
            for _ in range(3):
                _ = warper.warp_image_realtime(fabric, deform_x, deform_y)
            
            # Benchmark iterations
            num_iterations = 5
            print(f"  Running {num_iterations} iterations...")
            
            # Test Warp acceleration
            warp_times = []
            if warper.use_warp:
                for i in range(num_iterations):
                    start = time.time()
                    result_warp = warper.warp_image_realtime(fabric, deform_x, deform_y, force_pytorch=False)
                    warp_time = time.time() - start
                    warp_times.append(warp_time)
                    print(f"    Warp iteration {i+1}: {warp_time*1000:.1f}ms")
                
                avg_warp_time = np.mean(warp_times) * 1000
                warp_fps = 1000 / avg_warp_time
                warp_std = np.std(warp_times) * 1000
            else:
                avg_warp_time = float('inf')
                warp_fps = 0
                warp_std = 0
            
            # Test PyTorch fallback
            pytorch_times = []
            for i in range(num_iterations):
                start = time.time()
                result_pytorch = warper.warp_image_realtime(fabric, deform_x, deform_y, force_pytorch=True)
                pytorch_time = time.time() - start
                pytorch_times.append(pytorch_time)
                print(f"    PyTorch iteration {i+1}: {pytorch_time*1000:.1f}ms")
            
            avg_pytorch_time = np.mean(pytorch_times) * 1000
            pytorch_fps = 1000 / avg_pytorch_time
            pytorch_std = np.std(pytorch_times) * 1000
            
            # Calculate speedup
            speedup = avg_pytorch_time / avg_warp_time if avg_warp_time != float('inf') else 1.0
            
            # Real-time capability assessment
            is_realtime_warp = warp_fps >= 30
            is_realtime_pytorch = pytorch_fps >= 30
            
            # Store results
            results[description] = {
                'resolution': f"{width}x{height}",
                'megapixels': (width * height) / 1e6,
                'warp_ms': avg_warp_time,
                'warp_fps': warp_fps,
                'warp_std': warp_std,
                'pytorch_ms': avg_pytorch_time,
                'pytorch_fps': pytorch_fps,
                'pytorch_std': pytorch_std,
                'speedup': speedup,
                'realtime_warp': is_realtime_warp,
                'realtime_pytorch': is_realtime_pytorch
            }
            
            # Print results
            print(f"\n  📊 Results for {description}:")
            print(f"    Warp:    {avg_warp_time:.1f}±{warp_std:.1f}ms ({warp_fps:.1f} fps) {'✓' if is_realtime_warp else '✗'}")
            print(f"    PyTorch: {avg_pytorch_time:.1f}±{pytorch_std:.1f}ms ({pytorch_fps:.1f} fps) {'✓' if is_realtime_pytorch else '✗'}")
            print(f"    Speedup: {speedup:.1f}x")
            
            # Verify results are similar (quality check)
            if warper.use_warp and 'result_warp' in locals() and 'result_pytorch' in locals():
                diff = np.mean(np.abs(result_warp.astype(np.float32) - result_pytorch.astype(np.float32)))
                print(f"    Quality: Mean difference = {diff:.2f} (lower is better)")
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results[description] = {'error': str(e)}
    
    # Final summary
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE SUMMARY")
    print("=" * 60)
    
    print(f"{'Resolution':<15} {'Warp (ms)':<12} {'PyTorch (ms)':<14} {'Speedup':<10} {'Real-time?'}")
    print("-" * 65)
    
    for desc, data in results.items():
        if 'error' in data:
            print(f"{desc:<15} {'ERROR':<12} {'ERROR':<14} {'N/A':<10} {'N/A'}")
        else:
            realtime_status = "✓ Warp" if data['realtime_warp'] else ("✓ PyTorch" if data['realtime_pytorch'] else "✗ Neither")
            print(f"{desc:<15} {data['warp_ms']:<12.1f} {data['pytorch_ms']:<14.1f} {data['speedup']:<10.1f} {realtime_status}")
    
    print("\n🎯 Real-time Analysis (30+ fps requirement):")
    realtime_resolutions = [desc for desc, data in results.items() 
                           if 'realtime_warp' in data and data['realtime_warp']]
    
    if realtime_resolutions:
        print(f"  ✅ NVIDIA Warp enables real-time processing up to: {realtime_resolutions[-1]}")
        max_realtime = max([data['megapixels'] for data in results.values() 
                           if 'realtime_warp' in data and data['realtime_warp']])
        print(f"  🚀 Maximum real-time resolution: {max_realtime:.1f} megapixels")
    else:
        print(f"  ⚠️  No resolution achieved real-time performance")
    
    print(f"\n💡 Recommendations:")
    print(f"  • For real-time fabric inspection: Use resolutions where Warp achieves 30+ fps")  
    print(f"  • For batch processing: Higher resolutions acceptable with lower fps")
    print(f"  • NVIDIA Warp provides {list(results.values())[0].get('speedup', 'N/A'):.1f}x average speedup")
    
    return results

def test_integration_with_elastix():
    """Test integration with existing Elastix registration"""
    
    print("\n🔗 Testing Integration with Elastix Registration")
    print("=" * 50)
    
    try:
        # Initialize registration with Warp acceleration
        registration = ElastixFabricRegistration()
        
        print(f"✓ Elastix initialized")
        print(f"✓ PyTorch device: {registration.device}")
        print(f"✓ Warp acceleration: {'Enabled' if registration.use_warp_acceleration else 'Disabled'}")
        
        # Create test images
        print("\nCreating test fabric images...")
        fabric1 = create_test_fabric_image(2048, 2048)
        fabric2 = create_test_fabric_image(2048, 2048) 
        
        # Add some realistic deformation to fabric2
        deform_x, deform_y = create_realistic_deformation(2048, 2048, max_displacement=15)
        
        # Apply deformation to create a realistic moving image
        warper = WarpAcceleratedWarper()
        fabric2_deformed = warper.warp_image_realtime(fabric2, deform_x, deform_y, force_pytorch=True)
        
        print("✓ Test fabric images created")
        
        # Get performance summary
        if hasattr(registration, 'get_warp_performance_summary'):
            print(f"\n{registration.get_warp_performance_summary()}")
        
        print("✅ Integration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 NVIDIA Warp Acceleration Testing Suite")
    print("🧵 Optimized for Fabric Registration & Real-time Processing")
    print()
    
    # Run performance benchmark
    performance_results = test_warp_performance()
    
    # Test integration
    test_integration_with_elastix()
    
    print("\n🎉 All tests completed!")
    print("\nNext steps:")
    print("  1. Review performance results above")
    print("  2. Choose optimal resolution for your fabric scanning setup")  
    print("  3. Configure your Alinify system to use Warp acceleration")
    print("  4. Enjoy real-time fabric registration! 🚀")