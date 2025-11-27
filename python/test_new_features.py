#!/usr/bin/env python3
"""
Test Script for New GUI Features
Tests manual deformation editing and background threading
"""

import sys
import cv2
import numpy as np
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


def test_background_workers():
    """Test background worker threads"""
    print("\n" + "="*70)
    print("TEST 1: Background Registration Worker")
    print("="*70)
    
    try:
        from registration_backend import RegistrationBackend
        from gui.widgets.background_workers import RegistrationWorker
        
        # Create synthetic test images
        print("Creating synthetic test images...")
        h, w = 512, 512
        fixed = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        moving = np.roll(fixed, 20, axis=0)  # Shift for testing
        moving = np.roll(moving, 10, axis=1)
        
        # Create backend
        print("Initializing registration backend...")
        backend = RegistrationBackend(mode='elastix')
        
        # Create worker
        print("Creating registration worker...")
        worker = RegistrationWorker(
            backend, fixed, moving, 
            {'grid_spacing': 64, 'max_iterations': 100}
        )
        
        # Test signals
        results = {'finished': False, 'error': None}
        
        def on_progress(percent, msg):
            print(f"  [{percent}%] {msg}")
        
        def on_finished(reg, deform, meta):
            results['finished'] = True
            print(f"  ✅ Registration finished!")
            print(f"     Output shape: {reg.shape}")
            print(f"     Deformation shape: {deform.shape}")
            worker.quit()
        
        def on_error(err):
            results['error'] = err
            print(f"  ❌ Error: {err}")
            worker.quit()
        
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        
        # Start worker
        print("Starting worker thread...")
        worker.start()
        
        # Wait for completion (max 30 seconds)
        if not worker.wait(30000):
            print("  ⚠️ Worker timeout!")
            worker.terminate()
            return False
        
        if results['error']:
            print(f"  ❌ Test failed: {results['error']}")
            return False
        
        if results['finished']:
            print("  ✅ Background worker test PASSED")
            return True
        else:
            print("  ❌ Worker did not finish properly")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_editor_standalone():
    """Test manual deformation editor widget"""
    print("\n" + "="*70)
    print("TEST 2: Manual Deformation Editor (Standalone)")
    print("="*70)
    
    try:
        from gui.widgets.manual_deformation_editor import ManualDeformationEditor, ControlPointMarker
        from PySide6.QtCore import QPointF
        
        # Create test image and deformation
        print("Creating test data...")
        test_img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        test_deform = np.random.randn(400, 600, 2).astype(np.float32) * 5
        
        print("Testing ControlPointMarker...")
        marker = ControlPointMarker(100, 100)
        
        # Simulate movement
        marker.setPos(QPointF(110, 105))
        dx, dy = marker.getCorrectionVector()
        print(f"  Original: (100, 100)")
        print(f"  Current: {marker.getCurrentPosition()}")
        print(f"  Correction: ({dx:.1f}, {dy:.1f})")
        
        if abs(dx - 10) < 0.1 and abs(dy - 5) < 0.1:
            print("  ✅ Control point tracking works correctly")
        else:
            print(f"  ❌ Control point tracking failed: expected (10, 5), got ({dx}, {dy})")
            return False
        
        print("  ✅ Manual editor components test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_corrections():
    """Test manual correction application"""
    print("\n" + "="*70)
    print("TEST 3: Manual Correction Application")
    print("="*70)
    
    try:
        from registration_backend import RegistrationBackend
        
        print("Creating backend...")
        backend = RegistrationBackend(mode='elastix')
        
        # Create test deformation field
        print("Creating test deformation field...")
        h, w = 200, 300
        deform = np.zeros((h, w, 2), dtype=np.float32)
        
        # Add some initial deformation
        deform[:, :, 0] = np.linspace(-5, 5, w)
        deform[:, :, 1] = np.linspace(-3, 3, h)[:, np.newaxis]
        
        # Create manual corrections
        corrections = [
            (150, 100, 10, 5),   # x, y, dx, dy
            (100, 50, -8, 3),
            (200, 150, 5, -10)
        ]
        
        print(f"Applying {len(corrections)} manual corrections...")
        corrected = backend.apply_manual_corrections(deform, corrections)
        
        # Verify corrections were applied
        print(f"Original deformation range: [{deform.min():.2f}, {deform.max():.2f}]")
        print(f"Corrected deformation range: [{corrected.min():.2f}, {corrected.max():.2f}]")
        
        # Check that corrections increased the range (Gaussian influence)
        if corrected.max() > deform.max() + 1:
            print("  ✅ Manual corrections applied successfully")
            return True
        else:
            print("  ❌ Manual corrections not detected in output")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gui_integration():
    """Test full GUI integration"""
    print("\n" + "="*70)
    print("TEST 4: GUI Integration Test")
    print("="*70)
    
    try:
        print("Creating QApplication...")
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("Importing main window...")
        sys.path.insert(0, str(Path(__file__).parent.parent / "gui"))
        from main_gui import AlinifyMainWindow
        
        print("Creating main window...")
        window = AlinifyMainWindow()
        
        # Check for new components
        checks = [
            ('registration_worker', "Registration worker attribute"),
            ('warping_worker', "Warping worker attribute"),
            ('manual_corrections', "Manual corrections storage"),
            ('preview_deformation', "Preview deformation storage"),
        ]
        
        all_passed = True
        for attr, desc in checks:
            if hasattr(window, attr):
                print(f"  ✅ {desc} found")
            else:
                print(f"  ❌ {desc} missing")
                all_passed = False
        
        # Check for new methods
        methods = [
            'onRegistrationProgress',
            'onRegistrationFinished',
            'onRegistrationError',
            'openManualEditor',
            'onManualCorrectionsComplete'
        ]
        
        for method in methods:
            if hasattr(window, method):
                print(f"  ✅ Method '{method}' found")
            else:
                print(f"  ❌ Method '{method}' missing")
                all_passed = False
        
        # Show window briefly to test UI creation
        print("Testing window display...")
        window.show()
        
        # Use timer to close after 1 second
        QTimer.singleShot(1000, window.close)
        QTimer.singleShot(1100, app.quit)
        
        # Run event loop briefly
        app.exec()
        
        if all_passed:
            print("  ✅ GUI integration test PASSED")
        else:
            print("  ⚠️ GUI integration test had some failures")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metric_default():
    """Test that default metric is AdvancedMattesMutualInformation"""
    print("\n" + "="*70)
    print("TEST 5: Default Metric Configuration")
    print("="*70)
    
    try:
        print("Creating QApplication...")
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        sys.path.insert(0, str(Path(__file__).parent.parent / "gui"))
        from main_gui import AlinifyMainWindow
        
        print("Creating main window...")
        window = AlinifyMainWindow()
        
        # Check default metric
        if hasattr(window, 'combo_metric'):
            current = window.combo_metric.currentText()
            print(f"  Current metric: {current}")
            
            if current == "AdvancedMattesMutualInformation":
                print("  ✅ Default metric correctly set to AdvancedMattesMutualInformation")
                return True
            else:
                print(f"  ❌ Default metric is '{current}', expected 'AdvancedMattesMutualInformation'")
                return False
        else:
            print("  ❌ combo_metric not found")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("ALINIFY GUI FEATURE TESTS")
    print("="*70)
    print("Testing new implementations:")
    print("  1. Background registration workers")
    print("  2. Manual deformation editor")
    print("  3. Manual correction application")
    print("  4. GUI integration")
    print("  5. Default metric configuration")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Background Workers", test_background_workers()))
    results.append(("Manual Editor Components", test_manual_editor_standalone()))
    results.append(("Manual Corrections", test_manual_corrections()))
    results.append(("GUI Integration", test_gui_integration()))
    results.append(("Default Metric", test_metric_default()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("="*70)
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 All tests PASSED! New features are ready to use.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
