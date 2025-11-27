"""
Test Manual Correction Tab Integration
Verify the new workflow with integrated tab
"""

import sys
import numpy as np
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "gui"))
sys.path.insert(0, str(Path(__file__).parent.parent / "gui" / "widgets"))

from PySide6.QtWidgets import QApplication
from manual_correction_tab import ManualCorrectionTab


def test_manual_correction_tab():
    """Test Manual Correction Tab standalone"""
    print("="*70)
    print("TEST 1: Manual Correction Tab Initialization")
    print("="*70)
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create tab
    tab = ManualCorrectionTab()
    
    # Check attributes exist
    assert hasattr(tab, 'control_points'), "Missing control_points dict"
    assert hasattr(tab, 'point_markers'), "Missing point_markers dict"
    assert hasattr(tab, 'scene'), "Missing scene"
    assert hasattr(tab, 'view'), "Missing view"
    assert hasattr(tab, 'table'), "Missing table"
    
    print("✓ Tab initialized successfully")
    print(f"✓ Control points dict: {type(tab.control_points)}")
    print(f"✓ Point markers dict: {type(tab.point_markers)}")
    print(f"✓ Scene: {type(tab.scene)}")
    print(f"✓ Table columns: {tab.table.columnCount()}")
    
    return tab


def test_set_images(tab):
    """Test setting images"""
    print("\n" + "="*70)
    print("TEST 2: Setting Images")
    print("="*70)
    
    # Create synthetic images
    camera_img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
    registered_img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
    
    # Set images
    tab.setImages(camera_img, registered_img)
    
    assert tab.camera_image is not None, "Camera image not set"
    assert tab.registered_image is not None, "Registered image not set"
    assert tab.scene.items(), "Scene should have items after setImages"
    
    print("✓ Images set successfully")
    print(f"✓ Camera image shape: {tab.camera_image.shape}")
    print(f"✓ Registered image shape: {tab.registered_image.shape}")
    print(f"✓ Scene items: {len(tab.scene.items())}")


def test_add_control_point(tab):
    """Test adding control points"""
    print("\n" + "="*70)
    print("TEST 3: Adding Control Points")
    print("="*70)
    
    # Add control point
    initial_count = len(tab.control_points)
    tab.addControlPoint(100, 150)
    
    assert len(tab.control_points) == initial_count + 1, "Control point not added"
    assert len(tab.point_markers) == initial_count + 1, "Markers not created"
    
    # Check table updated
    assert tab.table.rowCount() == len(tab.control_points), "Table not updated"
    
    print("✓ Control point added successfully")
    print(f"✓ Total control points: {len(tab.control_points)}")
    print(f"✓ Table rows: {tab.table.rowCount()}")
    
    # Add more points
    tab.addControlPoint(200, 250)
    tab.addControlPoint(300, 350)
    
    print(f"✓ Added 2 more points, total: {len(tab.control_points)}")


def test_get_corrections(tab):
    """Test getting corrections"""
    print("\n" + "="*70)
    print("TEST 4: Getting Corrections")
    print("="*70)
    
    corrections = tab.getCorrections()
    
    assert isinstance(corrections, list), "Corrections should be a list"
    assert len(corrections) == len(tab.control_points), "Correction count mismatch"
    
    print("✓ Corrections retrieved successfully")
    print(f"✓ Correction count: {len(corrections)}")
    
    if corrections:
        print("\n📋 Correction Details:")
        for i, (x, y, dx, dy) in enumerate(corrections, 1):
            print(f"   Point {i}: ({x:.1f}, {y:.1f}) → offset ({dx:.1f}, {dy:.1f})")


def test_control_point_movement(tab):
    """Test control point movement updates table"""
    print("\n" + "="*70)
    print("TEST 5: Control Point Movement")
    print("="*70)
    
    if not tab.control_points:
        print("⚠ No control points to test movement")
        return
    
    # Get first point
    point_id = next(iter(tab.control_points.keys()))
    initial_data = tab.control_points[point_id].copy()
    
    print(f"📍 Initial position: camera ({initial_data['camera_x']:.1f}, {initial_data['camera_y']:.1f}), "
          f"registered ({initial_data['registered_x']:.1f}, {initial_data['registered_y']:.1f})")
    
    # Simulate movement (update registered position)
    from PySide6.QtCore import QPointF
    new_pos = QPointF(initial_data['registered_x'] + 50, initial_data['registered_y'] + 30)
    tab.onControlPointMoved(point_id, is_camera_layer=False, new_pos=new_pos)
    
    updated_data = tab.control_points[point_id]
    print(f"📍 After move: camera ({updated_data['camera_x']:.1f}, {updated_data['camera_y']:.1f}), "
          f"registered ({updated_data['registered_x']:.1f}, {updated_data['registered_y']:.1f})")
    
    # Check offset
    offset_x = updated_data['registered_x'] - updated_data['camera_x']
    offset_y = updated_data['registered_y'] - updated_data['camera_y']
    print(f"📐 Offset: ({offset_x:.1f}, {offset_y:.1f})")
    
    assert abs(offset_x - 50) < 0.1, f"Offset X should be ~50, got {offset_x}"
    assert abs(offset_y - 30) < 0.1, f"Offset Y should be ~30, got {offset_y}"
    
    print("✓ Control point movement tracked correctly")


def test_clear_all(tab):
    """Test clearing all points"""
    print("\n" + "="*70)
    print("TEST 6: Clear All Points")
    print("="*70)
    
    initial_count = len(tab.control_points)
    print(f"📊 Points before clear: {initial_count}")
    
    # Clear (but don't show dialog in test)
    tab.control_points.clear()
    tab.point_markers.clear()
    tab.updateTable()
    tab.updatePointCount()
    
    assert len(tab.control_points) == 0, "Control points not cleared"
    assert tab.table.rowCount() == 0, "Table not cleared"
    
    print("✓ All control points cleared")
    print(f"✓ Control points: {len(tab.control_points)}")
    print(f"✓ Table rows: {tab.table.rowCount()}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*20)
    print("MANUAL CORRECTION TAB - INTEGRATION TESTS")
    print("🧪 "*20 + "\n")
    
    try:
        # Test 1: Initialize
        tab = test_manual_correction_tab()
        
        # Test 2: Set images
        test_set_images(tab)
        
        # Test 3: Add control points
        test_add_control_point(tab)
        
        # Test 4: Get corrections
        test_get_corrections(tab)
        
        # Test 5: Movement
        test_control_point_movement(tab)
        
        # Test 6: Clear
        test_clear_all(tab)
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\n📋 Summary:")
        print("   ✓ Tab initialization")
        print("   ✓ Image display")
        print("   ✓ Control point creation")
        print("   ✓ Table synchronization")
        print("   ✓ Movement tracking")
        print("   ✓ Clear functionality")
        print("\n🎉 Manual Correction Tab is ready for integration!")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
