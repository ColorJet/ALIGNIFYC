"""
Manual Correction Tab - Canvas-Integrated Control Point Management
Shows only table and controls - points displayed on main canvas
Red dots = control points, Blue dots = offset points
Sequence-based pairing (1st red + 1st blue = pair A, etc.)
"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QCheckBox, QMessageBox, 
    QGroupBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


class ControlPointMarker(QGraphicsEllipseItem):
    """Draggable control point marker - blue for camera, red for registered"""
    
    def __init__(self, x, y, point_id, label, is_camera_layer=True, radius=8, parent_tab=None):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.setPos(x, y)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges)
        
        self.point_id = point_id
        self.label = label  # A, B, C, D...
        self.is_camera_layer = is_camera_layer  # True = blue, False = red
        self.parent_tab = parent_tab
        self.radius = radius
        
        # Visual styling
        if is_camera_layer:
            # Blue point for camera layer
            self.setBrush(QBrush(QColor(0, 120, 255, 200)))
            self.setPen(QPen(QColor(255, 255, 255), 2))
        else:
            # Red point for registered layer
            self.setBrush(QBrush(QColor(255, 50, 50, 200)))
            self.setPen(QPen(QColor(255, 255, 255), 2))
        
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Add text label
        self.text_item = QGraphicsTextItem(label, self)
        self.text_item.setDefaultTextColor(QColor(255, 255, 255))
        from PySide6.QtGui import QFont
        font = QFont("Arial", 10, QFont.Bold)
        self.text_item.setFont(font)
        # Center text
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(-text_rect.width()/2, -text_rect.height()/2)
        
        # Store initial position
        self.initial_pos = QPointF(x, y)
    
    def itemChange(self, change, value):
        """Track position changes and update table"""
        if change == QGraphicsEllipseItem.ItemPositionChange and self.parent_tab:
            new_pos = value
            # Notify parent tab to update table
            self.parent_tab.onControlPointMoved(self.point_id, self.is_camera_layer, new_pos)
        return super().itemChange(change, value)
    
    def updatePosition(self, x, y):
        """Update position without triggering itemChange callback"""
        self.setPos(x, y)


class ManualCorrectionTab(QWidget):
    """
    Manual Correction Tab integrated in main GUI
    Shows camera layer (blue points) + registered layer (red points)
    Table displays corrections, Apply button commits to deformation field
    """
    
    correctionsApplied = Signal(list)  # [(x, y, dx, dy), ...]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Control point data: {point_id: {'camera_x': x, 'camera_y': y, 'registered_x': x, 'registered_y': y}}
        self.control_points = {}
        self.next_point_id = 1
        
        # Graphics items: {point_id: {'camera_marker': marker, 'registered_marker': marker}}
        self.point_markers = {}
        
        # Images
        self.camera_image = None  # Fixed/camera image
        self.registered_image = None  # Registered/warped preview
        
        # Scene for overlay visualization
        self.scene = None
        self.camera_pixmap_item = None
        self.registered_pixmap_item = None
        
        self.setupUI()
    
    def setupUI(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        
        # Top info panel
        info_layout = QHBoxLayout()
        info_label = QLabel(
            "🔵 Blue = Camera layer  |  🔴 Red = Registered layer  |  "
            "Click to add point pair (labeled A, B, C...)  |  Drag to adjust"
        )
        info_label.setStyleSheet("QLabel { font-size: 10px; color: #666; padding: 5px; }")
        info_layout.addWidget(info_label)
        layout.addLayout(info_layout)
        
        # === Layer Controls ===
        layer_group = QGroupBox("🎨 Layer Visualization Controls")
        layer_layout = QVBoxLayout()
        
        # Camera layer controls
        camera_row = QHBoxLayout()
        camera_row.addWidget(QLabel("Camera Layer:"))
        camera_row.addWidget(QLabel("Opacity:"))
        self.slider_camera_opacity = QSlider(Qt.Horizontal)
        self.slider_camera_opacity.setRange(0, 100)
        self.slider_camera_opacity.setValue(100)
        self.slider_camera_opacity.setFixedWidth(100)
        self.slider_camera_opacity.valueChanged.connect(self.updateDisplay)
        camera_row.addWidget(self.slider_camera_opacity)
        self.lbl_camera_opacity = QLabel("100%")
        self.lbl_camera_opacity.setFixedWidth(40)
        camera_row.addWidget(self.lbl_camera_opacity)
        
        camera_row.addWidget(QLabel("  Contrast:"))
        self.slider_camera_contrast = QSlider(Qt.Horizontal)
        self.slider_camera_contrast.setRange(50, 300)
        self.slider_camera_contrast.setValue(100)
        self.slider_camera_contrast.setFixedWidth(100)
        self.slider_camera_contrast.valueChanged.connect(self.updateDisplay)
        camera_row.addWidget(self.slider_camera_contrast)
        self.lbl_camera_contrast = QLabel("1.0x")
        self.lbl_camera_contrast.setFixedWidth(40)
        camera_row.addWidget(self.lbl_camera_contrast)
        
        camera_row.addWidget(QLabel("  Brightness:"))
        self.slider_camera_brightness = QSlider(Qt.Horizontal)
        self.slider_camera_brightness.setRange(-100, 100)
        self.slider_camera_brightness.setValue(0)
        self.slider_camera_brightness.setFixedWidth(100)
        self.slider_camera_brightness.valueChanged.connect(self.updateDisplay)
        camera_row.addWidget(self.slider_camera_brightness)
        self.lbl_camera_brightness = QLabel("0")
        self.lbl_camera_brightness.setFixedWidth(40)
        camera_row.addWidget(self.lbl_camera_brightness)
        
        self.chk_camera_invert = QCheckBox("Invert")
        self.chk_camera_invert.stateChanged.connect(self.updateDisplay)
        camera_row.addWidget(self.chk_camera_invert)
        camera_row.addStretch()
        
        layer_layout.addLayout(camera_row)
        
        # Registered layer controls
        reg_row = QHBoxLayout()
        reg_row.addWidget(QLabel("Registered:"))
        reg_row.addWidget(QLabel("Opacity:"))
        self.slider_reg_opacity = QSlider(Qt.Horizontal)
        self.slider_reg_opacity.setRange(0, 100)
        self.slider_reg_opacity.setValue(30)
        self.slider_reg_opacity.setFixedWidth(100)
        self.slider_reg_opacity.valueChanged.connect(self.updateDisplay)
        reg_row.addWidget(self.slider_reg_opacity)
        self.lbl_reg_opacity = QLabel("30%")
        self.lbl_reg_opacity.setFixedWidth(40)
        reg_row.addWidget(self.lbl_reg_opacity)
        
        reg_row.addWidget(QLabel("  Contrast:"))
        self.slider_reg_contrast = QSlider(Qt.Horizontal)
        self.slider_reg_contrast.setRange(50, 300)
        self.slider_reg_contrast.setValue(100)
        self.slider_reg_contrast.setFixedWidth(100)
        self.slider_reg_contrast.valueChanged.connect(self.updateDisplay)
        reg_row.addWidget(self.slider_reg_contrast)
        self.lbl_reg_contrast = QLabel("1.0x")
        self.lbl_reg_contrast.setFixedWidth(40)
        reg_row.addWidget(self.lbl_reg_contrast)
        
        reg_row.addWidget(QLabel("  Brightness:"))
        self.slider_reg_brightness = QSlider(Qt.Horizontal)
        self.slider_reg_brightness.setRange(-100, 100)
        self.slider_reg_brightness.setValue(0)
        self.slider_reg_brightness.setFixedWidth(100)
        self.slider_reg_brightness.valueChanged.connect(self.updateDisplay)
        reg_row.addWidget(self.slider_reg_brightness)
        self.lbl_reg_brightness = QLabel("0")
        self.lbl_reg_brightness.setFixedWidth(40)
        reg_row.addWidget(self.lbl_reg_brightness)
        
        self.chk_reg_invert = QCheckBox("Invert")
        self.chk_reg_invert.stateChanged.connect(self.updateDisplay)
        reg_row.addWidget(self.chk_reg_invert)
        reg_row.addStretch()
        
        layer_layout.addLayout(reg_row)
        
        # Reset button
        btn_reset = QPushButton("Reset All Adjustments")
        btn_reset.clicked.connect(self.resetAdjustments)
        layer_layout.addWidget(btn_reset)
        
        layer_group.setLayout(layer_layout)
        layout.addWidget(layer_group)
        
        # Graphics view for overlaid images
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Connect mouse press for adding points
        self.view.mousePressEvent = self.onViewMousePress
        
        layout.addWidget(self.view, stretch=3)
        
        # Control points table
        table_label = QLabel("Control Points (Label identifies point pair, X/Y = Camera position, Offsets = Correction)")
        table_label.setStyleSheet("QLabel { font-weight: bold; font-size: 11px; margin-top: 10px; }")
        layout.addWidget(table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Label", "X", "Y", "Offset X", "Offset Y"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMaximumHeight(200)
        layout.addWidget(self.table, stretch=1)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Add Control Point")
        self.btn_add.setToolTip("Click on the image to add a control point")
        self.btn_add.clicked.connect(self.enableAddMode)
        button_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.removeSelectedPoint)
        button_layout.addWidget(self.btn_remove)
        
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self.clearAllPoints)
        button_layout.addWidget(self.btn_clear)
        
        button_layout.addStretch()
        
        # Point counter
        self.lbl_count = QLabel("Points: 0")
        self.lbl_count.setStyleSheet("font-weight: bold; font-size: 12px;")
        button_layout.addWidget(self.lbl_count)
        
        layout.addLayout(button_layout)
        
        # Apply button
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()
        
        self.btn_apply = QPushButton("Apply Manual Correction")
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.btn_apply.clicked.connect(self.applyCorrections)
        self.btn_apply.setEnabled(False)
        apply_layout.addWidget(self.btn_apply)
        
        apply_layout.addStretch()
        layout.addLayout(apply_layout)
    
    def setImages(self, camera_image, registered_image):
        """Set camera and registered images for overlay display"""
        self.camera_image = camera_image
        self.registered_image = registered_image
        
        self.updateDisplay()
    
    def updateDisplay(self):
        """Update the overlay display with independent layer controls"""
        if self.camera_image is None or self.registered_image is None:
            return
        
        # Get slider values
        camera_opacity = self.slider_camera_opacity.value() / 100.0
        camera_contrast = self.slider_camera_contrast.value() / 100.0
        camera_brightness = self.slider_camera_brightness.value()
        camera_invert = self.chk_camera_invert.isChecked()
        
        reg_opacity = self.slider_reg_opacity.value() / 100.0
        reg_contrast = self.slider_reg_contrast.value() / 100.0
        reg_brightness = self.slider_reg_brightness.value()
        reg_invert = self.chk_reg_invert.isChecked()
        
        # Update labels
        self.lbl_camera_opacity.setText(f"{int(camera_opacity*100)}%")
        self.lbl_camera_contrast.setText(f"{camera_contrast:.1f}x")
        self.lbl_camera_brightness.setText(f"{camera_brightness:+d}")
        
        self.lbl_reg_opacity.setText(f"{int(reg_opacity*100)}%")
        self.lbl_reg_contrast.setText(f"{reg_contrast:.1f}x")
        self.lbl_reg_brightness.setText(f"{reg_brightness:+d}")
        
        # Apply adjustments to camera layer
        camera_adjusted = self.camera_image.astype(np.float32)
        camera_adjusted = camera_adjusted * camera_contrast + camera_brightness
        camera_adjusted = np.clip(camera_adjusted, 0, 255).astype(np.uint8)
        if camera_invert:
            camera_adjusted = 255 - camera_adjusted
        
        # Apply adjustments to registered layer
        reg_adjusted = self.registered_image.astype(np.float32)
        reg_adjusted = reg_adjusted * reg_contrast + reg_brightness
        reg_adjusted = np.clip(reg_adjusted, 0, 255).astype(np.uint8)
        if reg_invert:
            reg_adjusted = 255 - reg_adjusted
        
        # Blend with opacity
        blended = np.clip(
            camera_opacity * camera_adjusted.astype(np.float32) + 
            reg_opacity * reg_adjusted.astype(np.float32),
            0, 255
        ).astype(np.uint8)
        
        # Convert to QPixmap
        h, w = blended.shape[:2]
        bytes_per_line = 3 * w
        qimage = QImage(blended.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        
        # Update scene
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(pixmap.rect())
        
        # Restore all control point markers
        for point_id, markers in self.point_markers.items():
            if 'camera_marker' in markers:
                self.scene.addItem(markers['camera_marker'])
            if 'registered_marker' in markers:
                self.scene.addItem(markers['registered_marker'])
        
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def resetAdjustments(self):
        """Reset all layer adjustments to defaults"""
        # Camera layer
        self.slider_camera_opacity.setValue(100)
        self.slider_camera_contrast.setValue(100)
        self.slider_camera_brightness.setValue(0)
        self.chk_camera_invert.setChecked(False)
        
        # Registered layer
        self.slider_reg_opacity.setValue(30)
        self.slider_reg_contrast.setValue(100)
        self.slider_reg_brightness.setValue(0)
        self.chk_reg_invert.setChecked(False)
    
    def enableAddMode(self):
        """Enable click-to-add mode"""
        # Visual feedback
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
        """)
        self.view.setCursor(QCursor(Qt.CrossCursor))
    
    def onViewMousePress(self, event):
        """Handle mouse press on view to add control point"""
        # Get scene position
        scene_pos = self.view.mapToScene(event.pos())
        
        # Check if clicked on empty area (not on existing marker)
        item = self.scene.itemAt(scene_pos, self.view.transform())
        if isinstance(item, ControlPointMarker):
            # Clicked on existing marker, let it handle the event
            super(QGraphicsView, self.view).mousePressEvent(event)
            return
        
        # Add new control point
        x, y = scene_pos.x(), scene_pos.y()
        self.addControlPoint(x, y)
        
        # Reset button style
        self.btn_add.setStyleSheet("")
        self.view.setCursor(QCursor(Qt.ArrowCursor))
        
        # Don't propagate event to avoid moving markers
        event.accept()
    
    def addControlPoint(self, x, y):
        """Add a control point at the given position"""
        point_id = self.next_point_id
        self.next_point_id += 1
        
        # Generate label (A, B, C, ... Z, AA, AB, ...)
        label = self.getPointLabel(point_id - 1)  # 0-indexed for label generation
        
        # Store data (initially no offset)
        self.control_points[point_id] = {
            'camera_x': x,
            'camera_y': y,
            'registered_x': x,
            'registered_y': y,
            'label': label
        }
        
        # Create visual markers with label
        camera_marker = ControlPointMarker(x, y, point_id, label, is_camera_layer=True, parent_tab=self)
        registered_marker = ControlPointMarker(x, y, point_id, label, is_camera_layer=False, parent_tab=self)
        
        self.point_markers[point_id] = {
            'camera_marker': camera_marker,
            'registered_marker': registered_marker
        }
        
        # Add to scene
        self.scene.addItem(camera_marker)
        self.scene.addItem(registered_marker)
        
        # Update table
        self.updateTable()
        self.updatePointCount()
        self.btn_apply.setEnabled(True)
    
    def getPointLabel(self, index):
        """Generate label for control point (A, B, C, ... Z, AA, AB, ...)"""
        label = ""
        while index >= 0:
            label = chr(65 + (index % 26)) + label
            index = index // 26 - 1
        return label
    
    def onControlPointMoved(self, point_id, is_camera_layer, new_pos):
        """Handle control point being dragged"""
        if point_id not in self.control_points:
            return
        
        x, y = new_pos.x(), new_pos.y()
        
        # Update stored position
        if is_camera_layer:
            self.control_points[point_id]['camera_x'] = x
            self.control_points[point_id]['camera_y'] = y
        else:
            self.control_points[point_id]['registered_x'] = x
            self.control_points[point_id]['registered_y'] = y
        
        # Update table
        self.updateTable()
    
    def updateTable(self):
        """Update table with current control points"""
        self.table.setRowCount(len(self.control_points))
        
        row = 0
        for point_id in sorted(self.control_points.keys()):
            data = self.control_points[point_id]
            
            # Get label
            label = data.get('label', '?')
            
            # Camera position (X, Y)
            camera_x = data['camera_x']
            camera_y = data['camera_y']
            
            # Offset = registered - camera (how much to correct)
            offset_x = data['registered_x'] - camera_x
            offset_y = data['registered_y'] - camera_y
            
            # Fill table with label in first column
            label_item = QTableWidgetItem(label)
            label_item.setData(Qt.UserRole, point_id)
            from PySide6.QtGui import QFont
            font = QFont()
            font.setBold(True)
            label_item.setFont(font)
            self.table.setItem(row, 0, label_item)
            self.table.setItem(row, 1, QTableWidgetItem(f"{camera_x:.1f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{camera_y:.1f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{offset_x:.1f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{offset_y:.1f}"))
            
            row += 1
    
    def updatePointCount(self):
        """Update point counter label"""
        self.lbl_count.setText(f"Points: {len(self.control_points)}")
    
    def removeSelectedPoint(self):
        """Remove selected control point"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select a control point to remove.")
            return
        
        row = selected_rows[0].row()
        point_id = self.table.item(row, 0).data(Qt.UserRole)
        
        # Remove markers from scene
        if point_id in self.point_markers:
            markers = self.point_markers[point_id]
            if 'camera_marker' in markers:
                self.scene.removeItem(markers['camera_marker'])
            if 'registered_marker' in markers:
                self.scene.removeItem(markers['registered_marker'])
            del self.point_markers[point_id]
        
        # Remove data
        if point_id in self.control_points:
            del self.control_points[point_id]
        
        # Update UI
        self.updateTable()
        self.updatePointCount()
        
        if len(self.control_points) == 0:
            self.btn_apply.setEnabled(False)
    
    def clearAllPoints(self):
        """Clear all control points"""
        if not self.control_points:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear All",
            f"Remove all {len(self.control_points)} control points?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Remove all markers
        for markers in self.point_markers.values():
            if 'camera_marker' in markers:
                self.scene.removeItem(markers['camera_marker'])
            if 'registered_marker' in markers:
                self.scene.removeItem(markers['registered_marker'])
        
        # Clear data
        self.control_points.clear()
        self.point_markers.clear()
        
        # Update UI
        self.updateTable()
        self.updatePointCount()
        self.btn_apply.setEnabled(False)
    
    def applyCorrections(self):
        """Apply manual corrections to deformation field"""
        if not self.control_points:
            QMessageBox.information(
                self,
                "No Corrections",
                "No control points have been added."
            )
            return
        
        # Build corrections list: [(x, y, dx, dy), ...]
        corrections = []
        for point_id, data in self.control_points.items():
            camera_x = data['camera_x']
            camera_y = data['camera_y']
            offset_x = data['registered_x'] - camera_x
            offset_y = data['registered_y'] - camera_y
            
            corrections.append((camera_x, camera_y, offset_x, offset_y))
        
        # Emit signal with corrections
        self.correctionsApplied.emit(corrections)
        
        # Show confirmation
        QMessageBox.information(
            self,
            "Corrections Applied",
            f"Applied {len(corrections)} manual corrections.\n"
            "These will be used during high-resolution warping."
        )
    
    def getCorrections(self):
        """Get current corrections as list"""
        corrections = []
        for point_id, data in self.control_points.items():
            camera_x = data['camera_x']
            camera_y = data['camera_y']
            offset_x = data['registered_x'] - camera_x
            offset_y = data['registered_y'] - camera_y
            corrections.append((camera_x, camera_y, offset_x, offset_y))
        return corrections
