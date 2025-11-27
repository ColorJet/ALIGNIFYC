"""
Manual Deformation Field Editor
Allows operators to correct deformation fields by marking control points
Enhanced with overlay modes (blend/difference), image adjustments (invert/contrast/brightness)
"""

import numpy as np
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QDialog, QMessageBox, QGroupBox, QSpinBox,
    QSlider, QComboBox, QCheckBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QTimer
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont,
    QTransform, QCursor
)


class ImageProcessor:
    """Image processing utilities for visualization modes"""
    
    @staticmethod
    def blend_images(fixed, warped, alpha=0.5):
        """Blend fixed and warped images"""
        return cv2.addWeighted(fixed, alpha, warped, 1-alpha, 0)
    
    @staticmethod
    def difference_image(fixed, warped):
        """Compute absolute difference (highlights misalignment)"""
        diff = cv2.absdiff(fixed, warped)
        # Enhance contrast for visibility
        diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        return diff
    
    @staticmethod
    def checkerboard(fixed, warped, tile_size=64):
        """Create checkerboard pattern alternating between images"""
        h, w = fixed.shape[:2]
        result = fixed.copy()
        
        for i in range(0, h, tile_size):
            for j in range(0, w, tile_size):
                # Checkerboard pattern
                if ((i // tile_size) + (j // tile_size)) % 2 == 0:
                    i_end = min(i + tile_size, h)
                    j_end = min(j + tile_size, w)
                    result[i:i_end, j:j_end] = warped[i:i_end, j:j_end]
        
        return result
    
    @staticmethod
    def adjust_image(img, invert=False, contrast=1.0, brightness=0):
        """Apply image adjustments for better control point marking"""
        adjusted = img.astype(np.float32)
        
        # Contrast (multiply by factor)
        adjusted = adjusted * contrast
        
        # Brightness (add offset)
        adjusted = adjusted + brightness
        
        # Clip to valid range
        adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
        
        # Invert if requested
        if invert:
            adjusted = 255 - adjusted
        
        return adjusted


class ControlPointMarker(QGraphicsEllipseItem):
    """Draggable control point marker"""
    
    def __init__(self, x, y, radius=8, color=QColor(255, 0, 0)):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.setPos(x, y)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges)
        
        # Visual styling
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(255, 255, 255), 2))
        
        # Store original position
        self.original_pos = QPointF(x, y)
        self.correction_vector = QPointF(0, 0)
        
        # Cursor
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
    def itemChange(self, change, value):
        """Track position changes"""
        if change == QGraphicsEllipseItem.ItemPositionChange:
            new_pos = value
            # Calculate correction vector from original position
            self.correction_vector = new_pos - self.original_pos
        return super().itemChange(change, value)
    
    def getCorrectionVector(self):
        """Get the displacement from original position"""
        return (self.correction_vector.x(), self.correction_vector.y())
    
    def getOriginalPosition(self):
        """Get original position"""
        return (self.original_pos.x(), self.original_pos.y())
    
    def getCurrentPosition(self):
        """Get current position"""
        pos = self.pos()
        return (pos.x(), pos.y())


class ManualDeformationEditor(QDialog):
    """
    Dialog for manually editing deformation field
    Enhanced with overlay modes, image adjustments, and bypass option
    """
    
    editingComplete = Signal(list)  # List of correction points [(x, y, dx, dy), ...]
    
    def __init__(self, fixed_image, warped_image, deformation_field, parent=None):
        super().__init__(parent)
        
        # Store both images for overlay visualization
        self.fixed_image = fixed_image  # Original camera/fixed image
        self.warped_image = warped_image  # Registered/warped image
        self.deformation_field = deformation_field  # [H, W, 2] deformation
        
        self.control_points = []  # List of ControlPointMarker
        self.correction_mode = True
        self.bypass_mode = False
        
        # Image adjustment parameters
        self.invert = False
        self.contrast = 1.0
        self.brightness = 0
        self.overlay_mode = "blend"  # blend, difference, checkerboard, warped, fixed
        self.blend_alpha = 0.5
        
        self.setWindowTitle("Manual Deformation Correction")
        self.setModal(True)
        self.resize(1400, 900)
        
        self.setupUI()
        self.updateDisplay()
        
    def setupUI(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        
        # Top panel: Bypass option and instructions
        top_panel = QHBoxLayout()
        
        # Bypass checkbox
        self.chk_bypass = QCheckBox("⏭️ Bypass Manual Correction (skip this step)")
        self.chk_bypass.setStyleSheet("QCheckBox { font-weight: bold; font-size: 12px; }")
        self.chk_bypass.stateChanged.connect(self.onBypassChanged)
        top_panel.addWidget(self.chk_bypass)
        
        top_panel.addStretch()
        
        # Instructions
        instructions = QLabel(
            "📍 Click to add points | 🖱️ Drag to correct | 🎨 Adjust view to see errors clearly"
        )
        instructions.setStyleSheet("QLabel { font-size: 10px; color: #666; }")
        top_panel.addWidget(instructions)
        
        layout.addLayout(top_panel)
        
        # Graphics view for image display
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Enable mouse tracking
        self.view.viewport().setMouseTracking(True)
        self.view.mousePressEvent = self.onMousePress
        
        layout.addWidget(self.view)
        
        # === Visualization Panel ===
        viz_group = QGroupBox("🎨 Visualization & Adjustments")
        viz_layout = QVBoxLayout(viz_group)
        
        # Overlay mode selection
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(QLabel("View Mode:"))
        self.combo_overlay = QComboBox()
        self.combo_overlay.addItems([
            "Blend (Overlay)", 
            "Difference (Shows Errors)", 
            "Checkerboard",
            "Warped Only",
            "Fixed Only"
        ])
        self.combo_overlay.currentIndexChanged.connect(self.onOverlayModeChanged)
        overlay_row.addWidget(self.combo_overlay)
        
        # Blend alpha slider (for blend mode)
        overlay_row.addWidget(QLabel("  Blend:"))
        self.slider_blend = QSlider(Qt.Horizontal)
        self.slider_blend.setRange(0, 100)
        self.slider_blend.setValue(50)
        self.slider_blend.setFixedWidth(100)
        self.slider_blend.valueChanged.connect(self.onBlendChanged)
        overlay_row.addWidget(self.slider_blend)
        
        overlay_row.addStretch()
        viz_layout.addLayout(overlay_row)
        
        # Image adjustments
        adjust_row = QHBoxLayout()
        
        # Invert checkbox
        self.chk_invert = QCheckBox("Invert")
        self.chk_invert.stateChanged.connect(self.onAdjustmentChanged)
        adjust_row.addWidget(self.chk_invert)
        
        # Contrast slider
        adjust_row.addWidget(QLabel("  Contrast:"))
        self.slider_contrast = QSlider(Qt.Horizontal)
        self.slider_contrast.setRange(50, 300)  # 0.5x to 3.0x
        self.slider_contrast.setValue(100)  # 1.0x
        self.slider_contrast.setFixedWidth(120)
        self.slider_contrast.valueChanged.connect(self.onAdjustmentChanged)
        adjust_row.addWidget(self.slider_contrast)
        self.lbl_contrast = QLabel("1.0x")
        self.lbl_contrast.setFixedWidth(40)
        adjust_row.addWidget(self.lbl_contrast)
        
        # Brightness slider
        adjust_row.addWidget(QLabel("  Brightness:"))
        self.slider_brightness = QSlider(Qt.Horizontal)
        self.slider_brightness.setRange(-100, 100)
        self.slider_brightness.setValue(0)
        self.slider_brightness.setFixedWidth(120)
        self.slider_brightness.valueChanged.connect(self.onAdjustmentChanged)
        adjust_row.addWidget(self.slider_brightness)
        self.lbl_brightness = QLabel("0")
        self.lbl_brightness.setFixedWidth(40)
        adjust_row.addWidget(self.lbl_brightness)
        
        # Reset adjustments button
        btn_reset_adj = QPushButton("Reset")
        btn_reset_adj.clicked.connect(self.resetAdjustments)
        adjust_row.addWidget(btn_reset_adj)
        
        adjust_row.addStretch()
        viz_layout.addLayout(adjust_row)
        
        layout.addWidget(viz_group)
        
        # === Control Panel ===
        control_group = QGroupBox("🎯 Control Points")
        control_layout = QHBoxLayout(control_group)
        
        # Grid spacing control
        control_layout.addWidget(QLabel("Spacing:"))
        self.spin_spacing = QSpinBox()
        self.spin_spacing.setRange(20, 200)
        self.spin_spacing.setValue(50)
        self.spin_spacing.setSuffix(" px")
        control_layout.addWidget(self.spin_spacing)
        
        # Auto-generate grid button
        self.btn_auto_grid = QPushButton("🔲 Auto Grid")
        self.btn_auto_grid.clicked.connect(self.createControlPointGrid)
        self.btn_auto_grid.setToolTip("Automatically place control points in a grid")
        control_layout.addWidget(self.btn_auto_grid)
        
        # Clear all points
        self.btn_clear = QPushButton("🗑️ Clear All")
        self.btn_clear.clicked.connect(self.clearAllPoints)
        control_layout.addWidget(self.btn_clear)
        
        # Undo last point
        self.btn_undo = QPushButton("⬅️ Undo")
        self.btn_undo.clicked.connect(self.undoLastPoint)
        control_layout.addWidget(self.btn_undo)
        
        control_layout.addStretch()
        
        # Point counter
        self.lbl_point_count = QLabel("Points: 0")
        self.lbl_point_count.setStyleSheet("font-weight: bold; font-size: 12px;")
        control_layout.addWidget(self.lbl_point_count)
        
        layout.addWidget(control_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton("❌ Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        button_layout.addWidget(self.btn_cancel)
        
        button_layout.addStretch()
        
        self.btn_preview = QPushButton("👁️ Preview Changes")
        self.btn_preview.clicked.connect(self.previewCorrections)
        self.btn_preview.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.btn_preview)
        
        self.btn_done = QPushButton("✅ Done - Apply Corrections")
        self.btn_done.clicked.connect(self.applyCorrections)
        self.btn_done.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        button_layout.addWidget(self.btn_done)
        
        layout.addLayout(button_layout)
        
    def onBypassChanged(self, state):
        """Handle bypass checkbox"""
        self.bypass_mode = (state == Qt.Checked)
        
        # Disable all controls when bypassed
        enabled = not self.bypass_mode
        self.view.setEnabled(enabled)
        self.combo_overlay.setEnabled(enabled)
        self.slider_blend.setEnabled(enabled)
        self.chk_invert.setEnabled(enabled)
        self.slider_contrast.setEnabled(enabled)
        self.slider_brightness.setEnabled(enabled)
        self.spin_spacing.setEnabled(enabled)
        self.btn_auto_grid.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_undo.setEnabled(enabled)
        self.btn_preview.setEnabled(enabled)
        
        if self.bypass_mode:
            self.lbl_point_count.setText("BYPASSED - No corrections will be applied")
            self.lbl_point_count.setStyleSheet("font-weight: bold; font-size: 12px; color: #FF9800;")
        else:
            self.updatePointCount()
    
    def onOverlayModeChanged(self, index):
        """Handle overlay mode change"""
        modes = ["blend", "difference", "checkerboard", "warped", "fixed"]
        self.overlay_mode = modes[index]
        
        # Enable/disable blend slider based on mode
        self.slider_blend.setEnabled(self.overlay_mode == "blend")
        
        self.updateDisplay()
    
    def onBlendChanged(self, value):
        """Handle blend slider change"""
        self.blend_alpha = value / 100.0
        if self.overlay_mode == "blend":
            self.updateDisplay()
    
    def onAdjustmentChanged(self):
        """Handle image adjustment changes"""
        self.invert = self.chk_invert.isChecked()
        self.contrast = self.slider_contrast.value() / 100.0
        self.brightness = self.slider_brightness.value()
        
        # Update labels
        self.lbl_contrast.setText(f"{self.contrast:.1f}x")
        self.lbl_brightness.setText(f"{self.brightness:+d}")
        
        self.updateDisplay()
    
    def resetAdjustments(self):
        """Reset all image adjustments to defaults"""
        self.chk_invert.setChecked(False)
        self.slider_contrast.setValue(100)
        self.slider_brightness.setValue(0)
    
    def updateDisplay(self):
        """Update the displayed image based on current mode and adjustments"""
        if self.fixed_image is None or self.warped_image is None:
            return
        
        # Generate visualization based on overlay mode
        if self.overlay_mode == "blend":
            display_img = ImageProcessor.blend_images(
                self.fixed_image, self.warped_image, self.blend_alpha
            )
        elif self.overlay_mode == "difference":
            display_img = ImageProcessor.difference_image(
                self.fixed_image, self.warped_image
            )
        elif self.overlay_mode == "checkerboard":
            display_img = ImageProcessor.checkerboard(
                self.fixed_image, self.warped_image, tile_size=64
            )
        elif self.overlay_mode == "warped":
            display_img = self.warped_image.copy()
        else:  # fixed
            display_img = self.fixed_image.copy()
        
        # Apply image adjustments
        display_img = ImageProcessor.adjust_image(
            display_img, 
            invert=self.invert,
            contrast=self.contrast,
            brightness=self.brightness
        )
        
        # Convert to QPixmap
        h, w = display_img.shape[:2]
        if len(display_img.shape) == 2:  # Grayscale
            bytes_per_line = w
            qimage = QImage(display_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        else:  # RGB
            bytes_per_line = 3 * w
            qimage = QImage(display_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(qimage)
        
        # Update scene
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(pixmap.rect())
        
        # Restore control points
        for cp in self.control_points:
            self.scene.addItem(cp)
        
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def displayPreview(self):
        """Legacy method - redirects to updateDisplay"""
        self.updateDisplay()
        
        # Convert to QPixmap
        h, w = self.preview_image.shape[:2]
        if len(self.preview_image.shape) == 3:
            bytes_per_line = 3 * w
            q_image = QImage(
                self.preview_image.data, w, h, bytes_per_line, QImage.Format_RGB888
            )
        else:
            bytes_per_line = w
            q_image = QImage(
                self.preview_image.data, w, h, bytes_per_line, QImage.Format_Grayscale8
            )
        
        pixmap = QPixmap.fromImage(q_image)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        
        # Fit in view
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        
    def onMousePress(self, event):
        """Handle mouse press to add control points"""
        if event.button() == Qt.LeftButton and self.correction_mode:
            # Get position in scene coordinates
            scene_pos = self.view.mapToScene(event.pos())
            
            # Check if click is within image bounds
            if self.pixmap_item.boundingRect().contains(scene_pos):
                self.addControlPoint(scene_pos.x(), scene_pos.y())
        
        # Call original handler for drag behavior
        QGraphicsView.mousePressEvent(self.view, event)
    
    def addControlPoint(self, x, y):
        """Add a control point at position (x, y)"""
        marker = ControlPointMarker(x, y, radius=6, color=QColor(255, 0, 0, 200))
        self.scene.addItem(marker)
        self.control_points.append(marker)
        
        self.updatePointCount()
        
    def createControlPointGrid(self):
        """Automatically create a grid of control points"""
        if self.pixmap_item is None:
            return
        
        spacing = self.spin_spacing.value()
        bounds = self.pixmap_item.boundingRect()
        
        # Clear existing points
        self.clearAllPoints()
        
        # Create grid
        x = bounds.left() + spacing / 2
        while x < bounds.right():
            y = bounds.top() + spacing / 2
            while y < bounds.bottom():
                self.addControlPoint(x, y)
                y += spacing
            x += spacing
        
        self.updatePointCount()
        
    def clearAllPoints(self):
        """Remove all control points"""
        for marker in self.control_points:
            self.scene.removeItem(marker)
        self.control_points.clear()
        self.updatePointCount()
        
    def undoLastPoint(self):
        """Remove the last added control point"""
        if self.control_points:
            marker = self.control_points.pop()
            self.scene.removeItem(marker)
            self.updatePointCount()
    
    def updatePointCount(self):
        """Update point counter label"""
        if self.bypass_mode:
            self.lbl_point_count.setText("BYPASSED - No corrections will be applied")
            self.lbl_point_count.setStyleSheet("font-weight: bold; font-size: 12px; color: #FF9800;")
        else:
            self.lbl_point_count.setText(f"Points: {len(self.control_points)}")
            self.lbl_point_count.setStyleSheet("font-weight: bold; font-size: 12px;")
    
    def previewCorrections(self):
        """Show preview of corrections (future implementation)"""
        corrections = self.getCorrections()
        if not corrections:
            QMessageBox.information(
                self, "Preview", 
                "No corrections have been made yet.\nAdd control points and drag them to correct the deformation."
            )
            return
        
        # Show summary
        msg = f"Total correction points: {len(corrections)}\n\n"
        msg += "Sample corrections:\n"
        for i, (x, y, dx, dy) in enumerate(corrections[:5]):
            msg += f"  Point {i+1}: ({x:.1f}, {y:.1f}) → Δ({dx:.1f}, {dy:.1f})\n"
        
        if len(corrections) > 5:
            msg += f"  ... and {len(corrections) - 5} more\n"
        
        QMessageBox.information(self, "Correction Preview", msg)
    
    def getCorrections(self):
        """Get list of correction points [(x, y, dx, dy), ...]"""
        corrections = []
        
        for marker in self.control_points:
            orig_x, orig_y = marker.getOriginalPosition()
            dx, dy = marker.getCorrectionVector()
            
            # Only include points that were actually moved
            if abs(dx) > 0.5 or abs(dy) > 0.5:
                corrections.append((orig_x, orig_y, dx, dy))
        
        return corrections
    
    def applyCorrections(self):
        """Apply corrections and close dialog"""
        # If bypassed, return empty corrections
        if self.bypass_mode:
            self.editingComplete.emit([])
            self.accept()
            return
        
        corrections = self.getCorrections()
        
        if not corrections:
            reply = QMessageBox.question(
                self, "No Corrections",
                "No corrections have been made. Proceed without corrections?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.editingComplete.emit(corrections)
        self.accept()
