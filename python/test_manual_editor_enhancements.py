"""
Test script for enhanced manual deformation editor
Tests overlay modes, image adjustments, and bypass functionality
"""

import sys
import numpy as np
import cv2
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from gui.widgets.manual_deformation_editor import ManualDeformationEditor, ImageProcessor


def test_image_processor():
    """Test ImageProcessor utility functions"""
    print("Testing ImageProcessor...")
    
    # Create test images
    fixed = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    warped = np.roll(fixed, shift=10, axis=1)  # Shift by 10 pixels
    
    # Test blend
    blended = ImageProcessor.blend_images(fixed, warped, alpha=0.5)
    assert blended.shape == fixed.shape
    print("✓ Blend test passed")
    
    # Test difference
    diff = ImageProcessor.difference_image(fixed, warped)
    assert diff.shape == fixed.shape
    assert np.max(diff) > 0  # Should show difference
    print("✓ Difference test passed")
    
    # Test checkerboard
    checker = ImageProcessor.checkerboard(fixed, warped, tile_size=64)
    assert checker.shape == fixed.shape
    print("✓ Checkerboard test passed")
    
    # Test adjustments
    adjusted = ImageProcessor.adjust_image(fixed, invert=True, contrast=2.0, brightness=30)
    assert adjusted.shape == fixed.shape
    print("✓ Adjustment test passed")
    
    print("✅ All ImageProcessor tests passed!\n")


def test_manual_editor_gui():
    """Test manual editor GUI with all enhancements"""
    print("Testing Manual Editor GUI...")
    
    app = QApplication(sys.argv)
    
    # Create test images with visible misalignment
    h, w = 512, 512
    fixed = np.zeros((h, w, 3), dtype=np.uint8)
    # Draw some patterns in fixed image
    fixed[100:150, 100:450] = [255, 0, 0]  # Red horizontal bar
    fixed[200:450, 200:250] = [0, 255, 0]  # Green vertical bar
    
    # Create warped image with shift
    warped = np.roll(fixed, shift=20, axis=1)  # 20 pixel horizontal shift
    
    # Create dummy deformation field
    x_grid = np.arange(0, w, 50)
    y_grid = np.arange(0, h, 50)
    dx = np.ones((len(y_grid), len(x_grid))) * 20  # Constant 20px shift
    dy = np.zeros((len(y_grid), len(x_grid)))
    deformation = (x_grid, y_grid, dx, dy)
    
    # Create editor
    editor = ManualDeformationEditor(fixed, warped, deformation)
    
    # Test that all controls exist
    assert hasattr(editor, 'chk_bypass'), "Missing bypass checkbox"
    assert hasattr(editor, 'combo_overlay'), "Missing overlay combo"
    assert hasattr(editor, 'slider_blend'), "Missing blend slider"
    assert hasattr(editor, 'chk_invert'), "Missing invert checkbox"
    assert hasattr(editor, 'slider_contrast'), "Missing contrast slider"
    assert hasattr(editor, 'slider_brightness'), "Missing brightness slider"
    
    print("✓ All controls exist")
    
    # Test overlay modes
    for mode_idx, mode_name in enumerate(["blend", "difference", "checkerboard", "warped", "fixed"]):
        editor.combo_overlay.setCurrentIndex(mode_idx)
        assert editor.overlay_mode == mode_name
        print(f"✓ Overlay mode '{mode_name}' works")
    
    # Test adjustments
    editor.slider_contrast.setValue(200)  # 2.0x
    assert editor.contrast == 2.0
    print("✓ Contrast adjustment works")
    
    editor.slider_brightness.setValue(50)
    assert editor.brightness == 50
    print("✓ Brightness adjustment works")
    
    editor.chk_invert.setChecked(True)
    assert editor.invert == True
    print("✓ Invert works")
    
    # Test bypass mode
    editor.chk_bypass.setChecked(True)
    assert editor.bypass_mode == True
    assert not editor.view.isEnabled()
    print("✓ Bypass mode works")
    
    editor.chk_bypass.setChecked(False)
    assert editor.bypass_mode == False
    assert editor.view.isEnabled()
    print("✓ Bypass toggle works")
    
    print("✅ All Manual Editor GUI tests passed!\n")
    
    # Show editor for visual inspection (optional)
    print("Opening editor for visual inspection...")
    print("Features to test manually:")
    print("  1. Difference mode should show bright vertical line (20px shift)")
    print("  2. Try adjusting contrast/brightness/invert")
    print("  3. Try different overlay modes")
    print("  4. Check bypass checkbox - controls should disable")
    print("  5. Click to add control points, drag to adjust")
    
    editor.exec()


def test_bypass_workflow():
    """Test bypass workflow returns empty corrections"""
    print("Testing bypass workflow...")
    
    app = QApplication(sys.argv)
    
    # Create dummy images
    fixed = np.zeros((256, 256, 3), dtype=np.uint8)
    warped = fixed.copy()
    deformation = (np.array([0, 100, 200]), np.array([0, 100, 200]), 
                   np.zeros((3, 3)), np.zeros((3, 3)))
    
    editor = ManualDeformationEditor(fixed, warped, deformation)
    
    # Enable bypass
    editor.chk_bypass.setChecked(True)
    
    # Add a control point (should be ignored)
    from gui.widgets.manual_deformation_editor import ControlPointMarker
    point = ControlPointMarker(100, 100)
    editor.control_points.append(point)
    
    # Get corrections - should be empty due to bypass
    corrections_received = []
    editor.editingComplete.connect(lambda c: corrections_received.append(c))
    
    # Trigger apply
    editor.applyCorrections()
    
    # Check that empty list was emitted
    assert len(corrections_received) == 1
    assert len(corrections_received[0]) == 0
    
    print("✅ Bypass workflow test passed!\n")


if __name__ == "__main__":
    print("="*70)
    print("ENHANCED MANUAL DEFORMATION EDITOR TEST SUITE")
    print("="*70)
    print()
    
    # Run tests
    test_image_processor()
    
    # GUI tests require user interaction
    choice = input("Run GUI tests? (y/n): ").lower()
    if choice == 'y':
        test_manual_editor_gui()
        test_bypass_workflow()
    else:
        print("Skipping GUI tests")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETED")
    print("="*70)
