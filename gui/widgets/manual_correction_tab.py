"""
Manual Correction Tab - Canvas-Integrated Control Point Management
Shows only table and controls - points displayed on main canvas
Red dots = control points, Blue dots = offset points
Sequence-based pairing (1st red + 1st blue = pair A, etc.)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


class ManualCorrectionTab(QWidget):
    """
    Manual Correction Tab - Pure Data Management
    No visualization - points shown on main canvas
    Tracks red (control) and blue (offset) points separately
    Pairs by sequence: 1st red + 1st blue = A, 2nd red + 2nd blue = B, etc.
    """
    
    correctionsApplied = Signal(list)  # [(red_x, red_y, blue_x, blue_y), ...]
    modeChanged = Signal(str)  # "red", "blue", or "none"
    markerPairRemoved = Signal(int)  # index of pair to remove
    allMarkersCleared = Signal()  # clear all markers
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage - separate lists
        self.red_points = []   # [(x, y), (x, y), ...]
        self.blue_points = []  # [(x, y), (x, y), ...]
        self.current_mode = "none"  # "red", "blue", or "none"
        
        self.initUI()
    
    def initUI(self):
        """Build UI - only table and buttons"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Manual Control Point Corrections")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Instructions - SIMPLIFIED
        instructions = QLabel(
            "🔴 LEFT-CLICK on canvas = Add RED control point (where feature currently is)\n"
            "🔵 RIGHT-CLICK on canvas = Add BLUE target point (where feature should be)\n"
            "Pairs automatically matched by sequence (A, B, C...)"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #333; padding: 8px; background-color: #ffffcc; border: 1px solid #ccc;")
        layout.addWidget(instructions)
        
        # Enable/Disable control point mode with influence area size
        mode_layout = QHBoxLayout()
        self.btn_toggle_mode = QPushButton("🎯 Enable Control Point Mode")
        self.btn_toggle_mode.setCheckable(True)
        self.btn_toggle_mode.setStyleSheet("""
            QPushButton { 
                background-color: #e0e0e0; 
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:checked { 
                background-color: #88ff88;
                border: 2px solid #00aa00;
            }
        """)
        self.btn_toggle_mode.clicked.connect(self.onToggleMode)
        mode_layout.addWidget(self.btn_toggle_mode)
        
        # Influence area size (1/10 of grid spacing by default)
        mode_layout.addWidget(QLabel("Influence Area:"))
        from PySide6.QtWidgets import QSpinBox
        self.spline_size_spin = QSpinBox()
        self.spline_size_spin.setRange(50, 1000)
        self.spline_size_spin.setValue(320)  # Default for grid spacing 32
        self.spline_size_spin.setSuffix(" px")
        self.spline_size_spin.setToolTip("Control point influence area (Photoshop puppet warp style)\n"
                                         "Default: ~10x grid spacing\n"
                                         "Keyboard: [ to decrease, ] to increase")
        self.spline_size_spin.setFixedWidth(90)
        mode_layout.addWidget(self.spline_size_spin)
        
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # Table with 7 columns
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Label", "Red X", "Red Y", "Blue X", "Blue Y", "Offset X", "Offset Y"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Status label
        self.lbl_status = QLabel("Ready - Click a mode button to start adding points")
        self.lbl_status.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(self.lbl_status)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.btn_remove = QPushButton("Remove Selected Pair")
        self.btn_remove.clicked.connect(self.onRemoveSelected)
        btn_layout.addWidget(self.btn_remove)
        
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self.onClearAll)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        
        self.btn_apply = QPushButton("Apply Manual Corrections")
        self.btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_apply.clicked.connect(self.onApply)
        btn_layout.addWidget(self.btn_apply)
        
        layout.addLayout(btn_layout)
    
    def onToggleMode(self, checked):
        """Toggle control point mode - SIMPLIFIED (no separate red/blue modes)"""
        if checked:
            self.current_mode = "enabled"
            self.btn_toggle_mode.setText("🎯 Control Point Mode ACTIVE")
            self.lbl_status.setText("🔴 LEFT-CLICK = Red  |  🔵 RIGHT-CLICK = Blue")
            self.lbl_status.setStyleSheet("padding: 8px; background-color: #ccffcc; font-weight: bold;")
            self.modeChanged.emit("enabled")
        else:
            self.current_mode = "none"
            self.btn_toggle_mode.setText("🎯 Enable Control Point Mode")
            self.lbl_status.setText("Control point mode OFF - Click button to enable")
            self.lbl_status.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
            self.modeChanged.emit("none")
    
    def addRedPoint(self, x, y):
        """Add a red control point at (x, y)"""
        self.red_points.append((x, y))
        self.updateTable()
        self.lbl_status.setText(f"🔴 Added red point #{len(self.red_points)} at ({x:.1f}, {y:.1f})")
        return len(self.red_points) - 1  # Return index
    
    def addBluePoint(self, x, y):
        """Add a blue offset point at (x, y)"""
        self.blue_points.append((x, y))
        self.updateTable()
        self.lbl_status.setText(f"🔵 Added blue point #{len(self.blue_points)} at ({x:.1f}, {y:.1f})")
        return len(self.blue_points) - 1  # Return index
    
    def updateTable(self):
        """Rebuild table from current red/blue point lists"""
        # Determine how many pairs we can make
        num_pairs = max(len(self.red_points), len(self.blue_points))
        self.table.setRowCount(num_pairs)
        
        for i in range(num_pairs):
            # Label (A, B, C, ... Z, AA, AB, ...)
            label = self.getLabel(i)
            
            # Get red point if exists
            red_x, red_y = self.red_points[i] if i < len(self.red_points) else (None, None)
            
            # Get blue point if exists
            blue_x, blue_y = self.blue_points[i] if i < len(self.blue_points) else (None, None)
            
            # Calculate offsets if both exist
            offset_x = (blue_x - red_x) if (red_x is not None and blue_x is not None) else None
            offset_y = (blue_y - red_y) if (red_y is not None and blue_y is not None) else None
            
            # Populate row
            self.table.setItem(i, 0, QTableWidgetItem(label))
            self.table.setItem(i, 1, QTableWidgetItem(f"{red_x:.2f}" if red_x is not None else "—"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{red_y:.2f}" if red_y is not None else "—"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{blue_x:.2f}" if blue_x is not None else "—"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{blue_y:.2f}" if blue_y is not None else "—"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{offset_x:.2f}" if offset_x is not None else "—"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{offset_y:.2f}" if offset_y is not None else "—"))
            
            # Highlight incomplete pairs
            if red_x is None or blue_x is None:
                for col in range(7):
                    item = self.table.item(i, col)
                    if item:
                        item.setBackground(QColor(255, 255, 200))  # Light yellow
    
    def getLabel(self, index):
        """Generate label A, B, C ... Z, AA, AB, AC ..."""
        label = ""
        num = index
        while True:
            label = chr(65 + (num % 26)) + label
            num = num // 26
            if num == 0:
                break
            num -= 1
        return label
    
    def onRemoveSelected(self):
        """Remove the selected pair (row)"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a row to remove.")
            return
        
        # Remove from both lists if they exist at this index
        if current_row < len(self.red_points):
            self.red_points.pop(current_row)
        if current_row < len(self.blue_points):
            self.blue_points.pop(current_row)
        
        # Notify canvas to remove markers
        self.markerPairRemoved.emit(current_row)
        
        self.updateTable()
        self.lbl_status.setText(f"Removed pair at row {current_row + 1}")
    
    def onClearAll(self):
        """Clear all points"""
        reply = QMessageBox.question(
            self, "Clear All",
            "Are you sure you want to clear all control points?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.red_points.clear()
            self.blue_points.clear()
            
            # Notify canvas to clear markers
            self.allMarkersCleared.emit()
            
            self.updateTable()
            self.lbl_status.setText("All points cleared")
    
    def onApply(self):
        """Apply corrections - emit complete pairs only"""
        # Get only complete pairs
        complete_pairs = []
        num_pairs = min(len(self.red_points), len(self.blue_points))
        
        for i in range(num_pairs):
            red_x, red_y = self.red_points[i]
            blue_x, blue_y = self.blue_points[i]
            complete_pairs.append((red_x, red_y, blue_x, blue_y))
        
        if not complete_pairs:
            QMessageBox.warning(
                self, "No Complete Pairs",
                "Please add at least one complete red+blue point pair before applying."
            )
            return
        
        # Emit signal
        self.correctionsApplied.emit(complete_pairs)
        self.lbl_status.setText(f"✓ Applied {len(complete_pairs)} correction pairs")
        self.lbl_status.setStyleSheet("padding: 5px; background-color: #ccffcc;")
    
    def getCurrentMode(self):
        """Get current click mode"""
        return self.current_mode
    
    def getRedPoints(self):
        """Get list of red control points"""
        return self.red_points.copy()
    
    def getBluePoints(self):
        """Get list of blue offset points"""
        return self.blue_points.copy()
    
    def getCompletePairs(self):
        """Get list of complete (red, blue) pairs"""
        pairs = []
        num_pairs = min(len(self.red_points), len(self.blue_points))
        for i in range(num_pairs):
            pairs.append((self.red_points[i], self.blue_points[i]))
        return pairs
