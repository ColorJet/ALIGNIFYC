"""
Tiling Pattern Editor Dialog - CAD-style pattern designer for fabric registration

Allows users to:
- Load tile pattern images
- Place tiles on camera image or blank background
- Configure size, pitch, gap parameters
- Manual placement with jog controls (X+/X-/Y+/Y-)
- Preview with opacity control
- Save as design file for registration pipeline
"""

import numpy as np
import cv2
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QSlider,
    QRadioButton, QButtonGroup, QFileDialog, QComboBox, QMessageBox,
    QWidget, QSplitter, QScrollArea, QSizePolicy, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen


class PatternPreviewCanvas(QWidget):
    """Canvas for previewing tiled pattern with drag & drop placement"""
    
    def __init__(self):
        super().__init__()
        self.background_image = None  # Camera image or blank
        self.tile_image = None  # Single tile pattern
        self.tile_position = [0, 0]  # Current tile position
        self.tile_opacity = 0.5  # Tile opacity (0-1)
        self.tile_scale = 1.0  # Tile scale factor
        self.show_grid = True  # Show grid overlay
        self.grid_cols = 5  # Number of columns
        self.grid_rows = 3  # Number of rows
        self.pitch_x = 0  # Horizontal pitch (0 = auto)
        self.pitch_y = 0  # Vertical pitch (0 = auto)
        self.gap_x = 0  # Horizontal gap
        self.gap_y = 0  # Vertical gap
        self.mode = 'grid'  # 'grid' or 'manual'
        
        # Manual mode tile counts in each direction
        self.tile_count_x_plus = 0
        self.tile_count_x_minus = 0
        self.tile_count_y_plus = 0
        self.tile_count_y_minus = 0
        
        # Rendering
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.dragging = False
        self.last_pos = None
        
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)
        
        self.setStyleSheet("""
            PatternPreviewCanvas {
                background-color: #2c2c2c;
                border: 1px solid #555;
            }
        """)
    
    def setBackgroundImage(self, image):
        """Set background image (camera or blank)"""
        self.background_image = image
        self.update()
    
    def setTileImage(self, image):
        """Set tile pattern image"""
        self.tile_image = image
        self.update()
    
    def setTileOpacity(self, opacity):
        """Set tile opacity (0-100)"""
        self.tile_opacity = opacity / 100.0
        self.update()
    
    def setGridParameters(self, cols, rows, pitch_x, pitch_y, gap_x, gap_y):
        """Set grid tiling parameters"""
        self.grid_cols = cols
        self.grid_rows = rows
        self.pitch_x = pitch_x
        self.pitch_y = pitch_y
        self.gap_x = gap_x
        self.gap_y = gap_y
        self.update()
    
    def setMode(self, mode):
        """Set placement mode: 'grid' or 'manual'"""
        self.mode = mode
        self.update()
    
    def setTileCounts(self, x_plus, x_minus, y_plus, y_minus, gap_x=0, gap_y=0):
        """Set manual mode tile counts in each direction and gaps"""
        self.tile_count_x_plus = x_plus
        self.tile_count_x_minus = x_minus
        self.tile_count_y_plus = y_plus
        self.tile_count_y_minus = y_minus
        self.manual_gap_x = gap_x
        self.manual_gap_y = gap_y
        self.update()
    
    def jogTile(self, dx, dy):
        """Move tile by delta (for manual placement)"""
        self.tile_position[0] += dx
        self.tile_position[1] += dy
        self.update()
    
    def paintEvent(self, event):
        """Render preview canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(44, 44, 44))
        
        if self.background_image is not None:
            # Draw background image
            bg_pixmap = self.arrayToPixmap(self.background_image)
            if bg_pixmap:
                # Center and scale
                canvas_w = self.width()
                canvas_h = self.height()
                
                img_w = int(bg_pixmap.width() * self.zoom_factor)
                img_h = int(bg_pixmap.height() * self.zoom_factor)
                
                img_x = (canvas_w - img_w) // 2 + self.pan_x
                img_y = (canvas_h - img_h) // 2 + self.pan_y
                
                scaled = bg_pixmap.scaled(img_w, img_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(img_x, img_y, scaled)
                
                # Draw tiles on top
                if self.tile_image is not None:
                    self.drawTiles(painter, img_x, img_y, img_w, img_h)
        
        elif self.tile_image is not None:
            # Draw tiles on dark background with zoom/pan applied
            canvas_w = self.width()
            canvas_h = self.height()
            
            # Create virtual area at center with zoom applied
            virtual_w = int(canvas_w / self.zoom_factor)
            virtual_h = int(canvas_h / self.zoom_factor)
            
            area_x = (canvas_w - int(virtual_w * self.zoom_factor)) // 2 + self.pan_x
            area_y = (canvas_h - int(virtual_h * self.zoom_factor)) // 2 + self.pan_y
            area_w = int(virtual_w * self.zoom_factor)
            area_h = int(virtual_h * self.zoom_factor)
            
            self.drawTiles(painter, area_x, area_y, area_w, area_h)
        
        else:
            # No images loaded
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, 
                           "Load background and tile pattern to preview")
    
    def drawTiles(self, painter, area_x, area_y, area_w, area_h):
        """Draw tiled pattern"""
        if self.tile_image is None:
            return
        
        tile_pixmap = self.arrayToPixmap(self.tile_image)
        if not tile_pixmap:
            return
        
        # Set opacity
        painter.setOpacity(self.tile_opacity)
        
        if self.mode == 'grid':
            # Grid tiling mode
            self.drawGridTiles(painter, tile_pixmap, area_x, area_y, area_w, area_h)
        else:
            # Manual placement mode
            self.drawManualTile(painter, tile_pixmap, area_x, area_y)
        
        painter.setOpacity(1.0)
    
    def drawGridTiles(self, painter, tile_pixmap, area_x, area_y, area_w, area_h):
        """Draw tiles in grid pattern"""
        tile_w = tile_pixmap.width()
        tile_h = tile_pixmap.height()
        
        # Apply zoom to tile dimensions and pitch
        zoomed_tile_w = int(tile_w * self.zoom_factor)
        zoomed_tile_h = int(tile_h * self.zoom_factor)
        
        # Calculate pitch (spacing between tile origins)
        if self.pitch_x > 0:
            pitch_x = int(self.pitch_x * self.zoom_factor)
        else:
            pitch_x = zoomed_tile_w + int(self.gap_x * self.zoom_factor)
        
        if self.pitch_y > 0:
            pitch_y = int(self.pitch_y * self.zoom_factor)
        else:
            pitch_y = zoomed_tile_h + int(self.gap_y * self.zoom_factor)
        
        # Draw grid of tiles
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = area_x + col * pitch_x
                y = area_y + row * pitch_y
                
                # Scale tile with zoom and custom scale
                final_w = int(zoomed_tile_w * self.tile_scale)
                final_h = int(zoomed_tile_h * self.tile_scale)
                scaled = tile_pixmap.scaled(final_w, final_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(x, y, scaled)
                
                # Draw grid lines (optional)
                if self.show_grid:
                    painter.setPen(QPen(QColor(100, 180, 255, 100), 1, Qt.DashLine))
                    painter.drawRect(x, y, final_w, final_h)
    
    def drawManualTile(self, painter, tile_pixmap, area_x, area_y):
        """Draw tile(s) in manual placement mode - creates a grid based on X+/X-/Y+/Y- counts"""
        tile_w = tile_pixmap.width()
        tile_h = tile_pixmap.height()
        
        # Apply zoom and custom scale to tile size
        scaled_w = int(tile_w * self.zoom_factor * self.tile_scale)
        scaled_h = int(tile_h * self.zoom_factor * self.tile_scale)
        
        # Get directional tile counts
        x_plus = getattr(self, 'tile_count_x_plus', 0)
        x_minus = getattr(self, 'tile_count_x_minus', 0)
        y_plus = getattr(self, 'tile_count_y_plus', 0)
        y_minus = getattr(self, 'tile_count_y_minus', 0)
        
        # Get gap values
        gap_x = getattr(self, 'manual_gap_x', 0)
        gap_y = getattr(self, 'manual_gap_y', 0)
        
        # Calculate pitch (distance between tile origins) including gaps
        pitch_x = int((tile_w + gap_x) * self.zoom_factor)
        pitch_y = int((tile_h + gap_y) * self.zoom_factor)
        
        # Base position (the manually placed tile)
        base_x = area_x + int(self.tile_position[0] * self.zoom_factor)
        base_y = area_y + int(self.tile_position[1] * self.zoom_factor)
        
        # Draw grid: nested loops create rows and columns
        # Y goes UP for y_plus (negative offset), DOWN for y_minus (positive offset)
        for y_offset in range(-y_plus, y_minus + 1):
            # X goes LEFT for x_minus (negative offset), RIGHT for x_plus (positive offset)
            for x_offset in range(-x_minus, x_plus + 1):
                x = base_x + x_offset * pitch_x
                y = base_y + y_offset * pitch_y
                
                # Scale and draw tile
                scaled = tile_pixmap.scaled(scaled_w, scaled_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(x, y, scaled)
                
                # Draw border (base tile in bright red, others in lighter red)
                if x_offset == 0 and y_offset == 0:
                    painter.setPen(QPen(QColor(255, 100, 100), 2))
                else:
                    painter.setPen(QPen(QColor(255, 100, 100, 150), 1))
                painter.drawRect(x, y, scaled_w, scaled_h)
    
    def arrayToPixmap(self, array):
        """Convert numpy array to QPixmap"""
        try:
            if len(array.shape) == 2:
                # Grayscale
                h, w = array.shape
                q_image = QImage(array.data, w, h, w, QImage.Format_Grayscale8)
            else:
                # RGB
                h, w, ch = array.shape
                q_image = QImage(array.data, w, h, ch * w, QImage.Format_RGB888)
            
            return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error converting array to pixmap: {e}")
            return None
    
    def wheelEvent(self, event):
        """Zoom with mouse wheel - zooms toward cursor position (matches main canvas algorithm)"""
        # Get mouse position before zoom
        mouse_pos = event.position()
        old_zoom = self.zoom_factor
        
        # Calculate zoom factor (exponential scaling like Photoshop)
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_factor = min(5.0, self.zoom_factor * 1.15)
        else:
            self.zoom_factor = max(0.01, self.zoom_factor / 1.15)
        
        if self.zoom_factor != old_zoom:
            # Zoom towards mouse position (matches main canvas algorithm)
            zoom_ratio = self.zoom_factor / old_zoom
            
            # Calculate mouse position relative to canvas center
            canvas_center_x = self.width() // 2
            canvas_center_y = self.height() // 2
            
            mouse_offset_x = mouse_pos.x() - canvas_center_x
            mouse_offset_y = mouse_pos.y() - canvas_center_y
            
            # Adjust pan to keep mouse position fixed during zoom
            self.pan_x = (self.pan_x - mouse_offset_x) * zoom_ratio + mouse_offset_x
            self.pan_y = (self.pan_y - mouse_offset_y) * zoom_ratio + mouse_offset_y
            
            # Notify zoom change if callback exists
            if hasattr(self, 'zoom_changed') and callable(self.zoom_changed):
                self.zoom_changed(self.zoom_factor)
            
            self.update()
    
    def mousePressEvent(self, event):
        """Start panning or tile dragging"""
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() == Qt.AltModifier):
            # Pan mode
            self.dragging = True
            self.last_pos = event.pos()
        elif event.button() == Qt.LeftButton and self.mode == 'manual' and self.tile_image is not None:
            # Tile drag mode (manual placement only)
            self.dragging = True
            self.last_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        """Handle panning or tile dragging"""
        if self.dragging and self.last_pos:
            delta = event.pos() - self.last_pos
            
            if event.modifiers() == Qt.AltModifier or self.mode != 'manual':
                # Pan canvas
                self.pan_x += delta.x()
                self.pan_y += delta.y()
            elif self.mode == 'manual':
                # Drag tile - direct 1:1 mapping (screen pixels = tile pixels at 100% zoom)
                # At zoom=1.0: move 1 pixel per mouse pixel
                # At zoom=2.0: move 0.5 pixels per mouse pixel (slower, more precise)
                # At zoom=0.5: move 2 pixels per mouse pixel (faster for repositioning)
                self.tile_position[0] += int(delta.x() / self.zoom_factor)
                self.tile_position[1] += int(delta.y() / self.zoom_factor)
            
            self.last_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Stop panning or dragging"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            self.dragging = False
            self.last_pos = None
    
    def mouseDoubleClickEvent(self, event):
        """Double-click to fit to window"""
        if event.button() == Qt.LeftButton:
            self.fitToWindow()
    
    def fitToWindow(self):
        """Fit background or tile image to window"""
        # Try background first, then tile
        image = self.background_image if self.background_image is not None else self.tile_image
        
        if image is None:
            return
        
        canvas_w = self.width()
        canvas_h = self.height()
        img_h, img_w = image.shape[:2]
        
        # Calculate zoom to fit
        zoom_w = canvas_w / img_w
        zoom_h = canvas_h / img_h
        self.zoom_factor = min(zoom_w, zoom_h) * 0.95  # 95% to leave some margin
        
        # Reset pan to center
        self.pan_x = 0
        self.pan_y = 0
        
        # Notify zoom change
        if hasattr(self, 'zoom_changed') and callable(self.zoom_changed):
            self.zoom_changed(self.zoom_factor)
        
        self.update()
    
    def resetView(self):
        """Reset zoom and pan to defaults"""
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Notify zoom change
        if hasattr(self, 'zoom_changed') and callable(self.zoom_changed):
            self.zoom_changed(self.zoom_factor)
        
        self.update()


class TilingPatternEditorDialog(QDialog):
    """Main dialog for tiling pattern editor - CAD style"""
    
    patternComplete = Signal(np.ndarray, dict)  # Signal when pattern is ready: (image, metadata)
    
    def __init__(self, parent=None, camera_image=None):
        super().__init__(parent)
        
        self.camera_image = camera_image
        self.tile_image = None
        self.tile_path = None  # Store tile file path for reload
        self.background_type = 'camera' if camera_image is not None else 'blank'
        
        self.setWindowTitle("Pattern Designer - CAD Style Tiling")
        
        # Set dialog to 90% of screen size
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        self.resize(int(screen.width() * 0.9), int(screen.height() * 0.9))
        self.setMinimumSize(1200, 800)
        
        self.initUI()
        
        # Initialize background
        if self.camera_image is not None:
            self.canvas.setBackgroundImage(self.camera_image)
        
        # Load previous settings if available
        self.loadSettings()
        
        # Initialize directional tile counts
        self.updateTileCounts()
    
    def initUI(self):
        """Initialize user interface"""
        layout = QHBoxLayout(self)
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Preview canvas
        left_panel = self.createCanvasPanel()
        splitter.addWidget(left_panel)
        
        # Right panel - Controls
        right_panel = self.createControlPanel()
        splitter.addWidget(right_panel)
        
        # Set initial sizes (80% canvas, 20% controls)
        splitter.setSizes([960, 240])
        
        layout.addWidget(splitter)
    
    def log(self, message):
        """Add message to log viewer (non-blocking alternative to QMessageBox)"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_viewer.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def createCanvasPanel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create canvas FIRST
        self.canvas = PatternPreviewCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Info bar with view controls
        info_layout = QHBoxLayout()
        self.canvas_info = QLabel("Preview Canvas - Wheel: Zoom (toward cursor) | Middle-drag/Alt+drag: Pan | Double-click: Fit")
        self.canvas_info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        info_layout.addWidget(self.canvas_info)
        
        # View control buttons (now canvas exists)
        btn_fit = QPushButton("Fit")
        btn_fit.setToolTip("Fit background to window (or double-click canvas)")
        btn_fit.setMaximumWidth(60)
        btn_fit.clicked.connect(self.canvas.fitToWindow)
        info_layout.addWidget(btn_fit)
        
        btn_reset = QPushButton("Reset")
        btn_reset.setToolTip("Reset zoom to 100% and center view")
        btn_reset.setMaximumWidth(60)
        btn_reset.clicked.connect(self.canvas.resetView)
        info_layout.addWidget(btn_reset)
        
        layout.addLayout(info_layout, 0)
        
        # Connect zoom changes to update info label
        self.canvas.zoom_changed = lambda z: self.canvas_info.setText(
            f"Preview Canvas - Zoom: {int(z*100)}% | Wheel: Zoom | Middle-drag/Alt+drag: Pan | Double-click: Fit"
        )
        
        layout.addWidget(self.canvas, 1)
        
        # Log viewer at bottom
        log_label = QLabel("Activity Log:")
        log_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(log_label, 0)
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(100)
        self.log_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.log_viewer, 0)

        return panel
    
    def createControlPanel(self):
        """Create control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Scroll area for controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Background selection
        controls_layout.addWidget(self.createBackgroundGroup())
        
        # Tile pattern
        controls_layout.addWidget(self.createTileGroup())
        
        # Tiling mode
        controls_layout.addWidget(self.createModeGroup())
        
        # Grid parameters
        self.grid_group = self.createGridGroup()
        controls_layout.addWidget(self.grid_group)
        
        # Manual jog controls
        self.jog_group = self.createJogGroup()
        self.jog_group.setVisible(False)  # Hidden by default
        controls_layout.addWidget(self.jog_group)
        
        # Actions
        controls_layout.addWidget(self.createActionsGroup())
        
        controls_layout.addStretch()
        
        scroll.setWidget(controls_widget)
        layout.addWidget(scroll)
        
        return panel
    
    def createBackgroundGroup(self):
        """Create background selection group"""
        group = QGroupBox("Background")
        layout = QVBoxLayout()
        
        self.bg_group = QButtonGroup()
        
        self.rb_camera = QRadioButton("Camera Image")
        self.rb_camera.setChecked(self.background_type == 'camera')
        self.rb_camera.toggled.connect(self.onBackgroundChanged)
        self.bg_group.addButton(self.rb_camera)
        layout.addWidget(self.rb_camera)
        
        self.rb_blank = QRadioButton("Blank Background")
        self.rb_blank.setChecked(self.background_type == 'blank')
        self.rb_blank.toggled.connect(self.onBackgroundChanged)
        self.bg_group.addButton(self.rb_blank)
        layout.addWidget(self.rb_blank)
        
        # Blank color selection
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.blank_color_combo = QComboBox()
        self.blank_color_combo.addItems(["White", "Light Gray", "Dark Gray", "Black"])
        self.blank_color_combo.currentTextChanged.connect(self.onBlankColorChanged)
        color_layout.addWidget(self.blank_color_combo)
        layout.addLayout(color_layout)
        
        # Load camera button
        btn_load_camera = QPushButton("Load Camera Image...")
        btn_load_camera.clicked.connect(self.loadCameraImage)
        layout.addWidget(btn_load_camera)
        
        group.setLayout(layout)
        return group
    
    def createTileGroup(self):
        """Create tile pattern group"""
        group = QGroupBox("Tile Pattern")
        layout = QVBoxLayout()
        
        # Load tile button
        btn_load = QPushButton("Load Tile Pattern...")
        btn_load.clicked.connect(self.loadTilePattern)
        layout.addWidget(btn_load)
        
        # Tile size
        size_layout = QGridLayout()
        size_layout.addWidget(QLabel("Width:"), 0, 0)
        self.tile_width_spin = QSpinBox()
        self.tile_width_spin.setRange(10, 5000)
        self.tile_width_spin.setValue(200)
        self.tile_width_spin.setSuffix(" px")
        self.tile_width_spin.setToolTip("Target tile width in pixels")
        self.tile_width_spin.valueChanged.connect(self.onTileWidthChanged)
        size_layout.addWidget(self.tile_width_spin, 0, 1)
        
        size_layout.addWidget(QLabel("Height:"), 1, 0)
        self.tile_height_spin = QSpinBox()
        self.tile_height_spin.setRange(10, 5000)
        self.tile_height_spin.setValue(200)
        self.tile_height_spin.setSuffix(" px")
        self.tile_height_spin.setToolTip("Target tile height in pixels")
        self.tile_height_spin.valueChanged.connect(self.onTileHeightChanged)
        size_layout.addWidget(self.tile_height_spin, 1, 1)
        
        # Lock aspect ratio checkbox
        self.chk_lock_aspect = QCheckBox("Lock Aspect Ratio")
        self.chk_lock_aspect.setChecked(False)
        self.chk_lock_aspect.setToolTip("Maintain proportions when changing width or height")
        size_layout.addWidget(self.chk_lock_aspect, 2, 0, 1, 2)
        
        layout.addLayout(size_layout)
        
        # Resize tile button
        btn_resize = QPushButton("Resize Tile to Above Dimensions")
        btn_resize.clicked.connect(self.resizeTile)
        btn_resize.setToolTip("Resize the loaded tile to match width/height above")
        layout.addWidget(btn_resize)
        
        # Opacity slider
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self.onOpacityChanged)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("50%")
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)
        
        group.setLayout(layout)
        return group
    
    def createModeGroup(self):
        """Create tiling mode group"""
        group = QGroupBox("Tiling Mode")
        layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        
        self.rb_grid = QRadioButton("Grid Pattern (Auto)")
        self.rb_grid.setChecked(True)
        self.rb_grid.toggled.connect(self.onModeChanged)
        self.mode_group.addButton(self.rb_grid)
        layout.addWidget(self.rb_grid)
        
        self.rb_manual = QRadioButton("Manual Placement")
        self.rb_manual.toggled.connect(self.onModeChanged)
        self.mode_group.addButton(self.rb_manual)
        layout.addWidget(self.rb_manual)
        
        group.setLayout(layout)
        return group
    
    def createGridGroup(self):
        """Create grid parameters group"""
        group = QGroupBox("Grid Settings")
        layout = QGridLayout()
        
        # Grid size
        layout.addWidget(QLabel("Columns:"), 0, 0)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 50)
        self.cols_spin.setValue(5)
        self.cols_spin.valueChanged.connect(self.onGridChanged)
        layout.addWidget(self.cols_spin, 0, 1)
        
        layout.addWidget(QLabel("Rows:"), 1, 0)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(3)
        self.rows_spin.valueChanged.connect(self.onGridChanged)
        layout.addWidget(self.rows_spin, 1, 1)
        
        # Pitch (optional)
        layout.addWidget(QLabel("Pitch X:"), 2, 0)
        self.pitch_x_spin = QSpinBox()
        self.pitch_x_spin.setRange(0, 5000)
        self.pitch_x_spin.setValue(0)
        self.pitch_x_spin.setSuffix(" px (0=auto)")
        self.pitch_x_spin.valueChanged.connect(self.onGridChanged)
        layout.addWidget(self.pitch_x_spin, 2, 1)
        
        layout.addWidget(QLabel("Pitch Y:"), 3, 0)
        self.pitch_y_spin = QSpinBox()
        self.pitch_y_spin.setRange(0, 5000)
        self.pitch_y_spin.setValue(0)
        self.pitch_y_spin.setSuffix(" px (0=auto)")
        self.pitch_y_spin.valueChanged.connect(self.onGridChanged)
        layout.addWidget(self.pitch_y_spin, 3, 1)
        
        # Gap
        layout.addWidget(QLabel("Gap X:"), 4, 0)
        self.gap_x_spin = QSpinBox()
        self.gap_x_spin.setRange(0, 500)
        self.gap_x_spin.setValue(0)
        self.gap_x_spin.setSuffix(" px")
        self.gap_x_spin.valueChanged.connect(self.onGridChanged)
        layout.addWidget(self.gap_x_spin, 4, 1)
        
        layout.addWidget(QLabel("Gap Y:"), 5, 0)
        self.gap_y_spin = QSpinBox()
        self.gap_y_spin.setRange(0, 500)
        self.gap_y_spin.setValue(0)
        self.gap_y_spin.setSuffix(" px")
        self.gap_y_spin.valueChanged.connect(self.onGridChanged)
        layout.addWidget(self.gap_y_spin, 5, 1)
        
        group.setLayout(layout)
        return group
    
    def createJogGroup(self):
        """Create manual jog controls group"""
        group = QGroupBox("Jog Controls")
        layout = QVBoxLayout()
        
        # Tile count controls
        count_group = QGroupBox("Tile Counts")
        count_layout = QGridLayout()
        
        count_layout.addWidget(QLabel("X+ Count:"), 0, 0)
        self.x_plus_count = QSpinBox()
        self.x_plus_count.setRange(0, 50)
        self.x_plus_count.setValue(2)
        count_layout.addWidget(self.x_plus_count, 0, 1)
        
        count_layout.addWidget(QLabel("X- Count:"), 1, 0)
        self.x_minus_count = QSpinBox()
        self.x_minus_count.setRange(0, 50)
        self.x_minus_count.setValue(2)
        count_layout.addWidget(self.x_minus_count, 1, 1)
        
        count_layout.addWidget(QLabel("Y+ Count:"), 2, 0)
        self.y_plus_count = QSpinBox()
        self.y_plus_count.setRange(0, 50)
        self.y_plus_count.setValue(1)
        count_layout.addWidget(self.y_plus_count, 2, 1)
        
        count_layout.addWidget(QLabel("Y- Count:"), 3, 0)
        self.y_minus_count = QSpinBox()
        self.y_minus_count.setRange(0, 50)
        self.y_minus_count.setValue(1)
        count_layout.addWidget(self.y_minus_count, 3, 1)
        
        # Gap controls for manual mode
        count_layout.addWidget(QLabel("Gap X:"), 4, 0)
        self.manual_gap_x = QSpinBox()
        self.manual_gap_x.setRange(0, 500)
        self.manual_gap_x.setValue(0)
        self.manual_gap_x.setSuffix(" px")
        self.manual_gap_x.setToolTip("Horizontal gap between tiles")
        count_layout.addWidget(self.manual_gap_x, 4, 1)
        
        count_layout.addWidget(QLabel("Gap Y:"), 5, 0)
        self.manual_gap_y = QSpinBox()
        self.manual_gap_y.setRange(0, 500)
        self.manual_gap_y.setValue(0)
        self.manual_gap_y.setSuffix(" px")
        self.manual_gap_y.setToolTip("Vertical gap between tiles")
        count_layout.addWidget(self.manual_gap_y, 5, 1)
        
        count_group.setLayout(count_layout)
        layout.addWidget(count_group)
        
        # Step size
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("Step:"))
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 500)
        self.step_spin.setValue(10)
        self.step_spin.setSuffix(" px")
        step_layout.addWidget(self.step_spin)
        layout.addLayout(step_layout)
        
        # Arrow buttons
        arrow_layout = QGridLayout()
        
        btn_y_plus = QPushButton("Y+")
        btn_y_plus.clicked.connect(lambda: self.jogTile(0, -self.step_spin.value()))
        arrow_layout.addWidget(btn_y_plus, 0, 1)
        
        btn_x_minus = QPushButton("X-")
        btn_x_minus.clicked.connect(lambda: self.jogTile(-self.step_spin.value(), 0))
        arrow_layout.addWidget(btn_x_minus, 1, 0)
        
        self.position_label = QLabel("(0, 0)")
        self.position_label.setAlignment(Qt.AlignCenter)
        arrow_layout.addWidget(self.position_label, 1, 1)
        
        btn_x_plus = QPushButton("X+")
        btn_x_plus.clicked.connect(lambda: self.jogTile(self.step_spin.value(), 0))
        arrow_layout.addWidget(btn_x_plus, 1, 2)
        
        btn_y_minus = QPushButton("Y-")
        btn_y_minus.clicked.connect(lambda: self.jogTile(0, self.step_spin.value()))
        arrow_layout.addWidget(btn_y_minus, 2, 1)
        
        layout.addLayout(arrow_layout)
        
        # Reset position
        btn_reset = QPushButton("Reset Position")
        btn_reset.clicked.connect(self.resetTilePosition)
        layout.addWidget(btn_reset)
        
        # Connect tile counts and gaps to update preview
        self.x_plus_count.valueChanged.connect(self.updateTileCounts)
        self.x_minus_count.valueChanged.connect(self.updateTileCounts)
        self.y_plus_count.valueChanged.connect(self.updateTileCounts)
        self.y_minus_count.valueChanged.connect(self.updateTileCounts)
        self.manual_gap_x.valueChanged.connect(self.updateTileCounts)
        self.manual_gap_y.valueChanged.connect(self.updateTileCounts)
        
        group.setLayout(layout)
        return group
    
    def createActionsGroup(self):
        """Create action buttons group"""
        group = QGroupBox("Actions")
        layout = QVBoxLayout()
        
        btn_preview = QPushButton("Generate Full Pattern")
        btn_preview.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; }")
        btn_preview.clicked.connect(self.generatePattern)
        layout.addWidget(btn_preview)
        
        btn_save = QPushButton("Save Design File...")
        btn_save.clicked.connect(self.saveDesignFile)
        layout.addWidget(btn_save)
        
        btn_send = QPushButton("Send to Registration Pipeline")
        btn_send.setStyleSheet("QPushButton { background-color: #2a5; color: white; font-weight: bold; padding: 10px; }")
        btn_send.clicked.connect(self.sendToRegistration)
        layout.addWidget(btn_send)
        
        layout.addSpacing(10)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close)
        
        group.setLayout(layout)
        return group
    
    # Event handlers
    
    def onBackgroundChanged(self):
        """Handle background selection change"""
        if self.rb_camera.isChecked():
            self.background_type = 'camera'
            if self.camera_image is not None:
                self.canvas.setBackgroundImage(self.camera_image)
        else:
            self.background_type = 'blank'
            self.onBlankColorChanged(self.blank_color_combo.currentText())
    
    def onBlankColorChanged(self, color_name):
        """Handle blank background color change"""
        if self.background_type != 'blank':
            return
        
        color_map = {
            'White': 255,
            'Light Gray': 200,
            'Dark Gray': 100,
            'Black': 0
        }
        
        value = color_map.get(color_name, 255)
        blank_img = np.full((800, 1200, 3), value, dtype=np.uint8)
        self.canvas.setBackgroundImage(blank_img)
    
    def loadCameraImage(self):
        """Load camera image"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Camera Image", "",
            "Image Files (*.png *.jpg *.tif);;All Files (*)"
        )
        
        if filename:
            try:
                img = cv2.imread(filename, cv2.IMREAD_COLOR)
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.camera_image = img_rgb
                    
                    if self.rb_camera.isChecked():
                        self.canvas.setBackgroundImage(img_rgb)
                    
                    self.log(f"✓ Loaded camera image: {Path(filename).name}")
            except Exception as e:
                self.log(f"✗ Failed to load image: {e}")
    
    def loadTilePattern(self):
        """Load tile pattern"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Tile Pattern", "",
            "Image Files (*.png *.jpg *.tif);;All Files (*)"
        )
        
        if filename:
            try:
                img = cv2.imread(filename, cv2.IMREAD_COLOR)
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.tile_image = img_rgb
                    self.tile_path = filename  # Save path for persistence
                    self.canvas.setTileImage(img_rgb)
                    
                    # Update size spinboxes
                    self.tile_width_spin.setValue(img_rgb.shape[1])
                    self.tile_height_spin.setValue(img_rgb.shape[0])
                    
                    self.log(f"✓ Loaded tile pattern: {Path(filename).name}")
            except Exception as e:
                self.log(f"✗ Failed to load tile: {e}")
    
    def onTileWidthChanged(self, value):
        """Handle tile width change - update height if aspect locked"""
        if self.chk_lock_aspect.isChecked() and self.tile_image is not None:
            # Calculate aspect ratio from original tile
            aspect = self.tile_image.shape[0] / self.tile_image.shape[1]  # height / width
            new_height = int(value * aspect)
            # Block signals to prevent recursive updates
            self.tile_height_spin.blockSignals(True)
            self.tile_height_spin.setValue(new_height)
            self.tile_height_spin.blockSignals(False)
    
    def onTileHeightChanged(self, value):
        """Handle tile height change - update width if aspect locked"""
        if self.chk_lock_aspect.isChecked() and self.tile_image is not None:
            # Calculate aspect ratio from original tile
            aspect = self.tile_image.shape[1] / self.tile_image.shape[0]  # width / height
            new_width = int(value * aspect)
            # Block signals to prevent recursive updates
            self.tile_width_spin.blockSignals(True)
            self.tile_width_spin.setValue(new_width)
            self.tile_width_spin.blockSignals(False)
    
    def updateTileCounts(self):
        """Update canvas with directional tile counts and gaps"""
        self.canvas.setTileCounts(
            self.x_plus_count.value(),
            self.x_minus_count.value(),
            self.y_plus_count.value(),
            self.y_minus_count.value(),
            self.manual_gap_x.value(),
            self.manual_gap_y.value()
        )
    
    def resizeTile(self):
        """Resize tile to match width/height spinboxes"""
        if self.tile_image is None:
            self.log("✗ Please load a tile pattern first")
            return
        
        target_w = self.tile_width_spin.value()
        target_h = self.tile_height_spin.value()
        current_w = self.tile_image.shape[1]
        current_h = self.tile_image.shape[0]
        
        if target_w == current_w and target_h == current_h:
            self.log("⚠ Tile is already at target dimensions")
            return
        
        try:
            # Resize tile
            resized = cv2.resize(self.tile_image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            self.tile_image = resized
            self.canvas.setTileImage(resized)
            self.canvas.update()
            
            self.log(f"✓ Tile resized from {current_w}×{current_h} to {target_w}×{target_h}")
        except Exception as e:
            self.log(f"✗ Failed to resize tile: {e}")
    
    def onOpacityChanged(self, value):
        """Handle opacity slider change"""
        self.opacity_label.setText(f"{value}%")
        self.canvas.setTileOpacity(value)
    
    def onModeChanged(self):
        """Handle tiling mode change"""
        if self.rb_grid.isChecked():
            self.canvas.setMode('grid')
            # In Grid mode: enable grid controls, hide jog controls
            self.cols_spin.setEnabled(True)
            self.rows_spin.setEnabled(True)
            self.pitch_x_spin.setEnabled(True)
            self.pitch_y_spin.setEnabled(True)
            self.gap_x_spin.setEnabled(True)
            self.gap_y_spin.setEnabled(True)
            self.jog_group.setVisible(False)
        else:
            self.canvas.setMode('manual')
            # In Manual mode: disable ONLY rows/cols, keep pitch/gap enabled
            self.cols_spin.setEnabled(False)
            self.rows_spin.setEnabled(False)
            self.pitch_x_spin.setEnabled(True)  # Keep enabled
            self.pitch_y_spin.setEnabled(True)  # Keep enabled
            self.gap_x_spin.setEnabled(True)    # Keep enabled
            self.gap_y_spin.setEnabled(True)    # Keep enabled
            self.jog_group.setVisible(True)
    
    def onGridChanged(self):
        """Handle grid parameter changes"""
        self.canvas.setGridParameters(
            self.cols_spin.value(),
            self.rows_spin.value(),
            self.pitch_x_spin.value(),
            self.pitch_y_spin.value(),
            self.gap_x_spin.value(),
            self.gap_y_spin.value()
        )
    
    def jogTile(self, dx, dy):
        """Jog tile position"""
        self.canvas.jogTile(dx, dy)
        pos = self.canvas.tile_position
        self.position_label.setText(f"({pos[0]}, {pos[1]})")
    
    def resetTilePosition(self):
        """Reset tile to origin"""
        self.canvas.tile_position = [0, 0]
        self.position_label.setText("(0, 0)")
        self.canvas.update()
    
    def generatePattern(self):
        """Generate full tiled pattern"""
        if self.tile_image is None:
            self.log("✗ Please load a tile pattern first")
            return
        
        self.log("ℹ Full pattern will be generated when sent to registration pipeline (use 'Send to Pipeline' button)")
    
    def saveDesignFile(self):
        """Save pattern as design file"""
        if self.tile_image is None:
            self.log("✗ Please load a tile pattern first")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Design File", "",
            "NumPy Compressed (*.npz);;PNG Image (*.png);;All Files (*)"
        )
        
        if filename:
            try:
                # Generate full pattern
                pattern, metadata = self.createFullPattern()
                
                if filename.endswith('.npz'):
                    # Save as NPZ with metadata
                    np.savez_compressed(
                        filename,
                        image=pattern,
                        **metadata
                    )
                else:
                    # Save as image
                    cv2.imwrite(filename, cv2.cvtColor(pattern, cv2.COLOR_RGB2BGR))
                
                self.log(f"✓ Saved design file: {Path(filename).name}")
            except Exception as e:
                self.log(f"✗ Failed to save: {e}")
    
    def sendToRegistration(self):
        """Send pattern to registration pipeline"""
        if self.tile_image is None:
            self.log("✗ Please load a tile pattern first")
            return
        
        try:
            # Save settings before sending
            self.saveSettings()
            
            # Generate full pattern
            pattern, metadata = self.createFullPattern()
            
            # Emit signal with pattern and metadata
            self.patternComplete.emit(pattern, metadata)
            
            self.log("✓ Pattern sent to registration pipeline!")
            self.accept()
            
        except Exception as e:
            self.log(f"✗ Failed to generate pattern: {e}")
    
    def createFullPattern(self):
        """Create full tiled pattern with current settings - tiles only, no camera background"""
        if self.tile_image is None:
            raise ValueError("No tile image loaded")
        
        tile_h, tile_w = self.tile_image.shape[:2]
        
        if self.rb_grid.isChecked():
            # Grid mode - calculate exact size needed for tiles
            cols = self.cols_spin.value()
            rows = self.rows_spin.value()
            
            pitch_x = self.pitch_x_spin.value() if self.pitch_x_spin.value() > 0 else tile_w + self.gap_x_spin.value()
            pitch_y = self.pitch_y_spin.value() if self.pitch_y_spin.value() > 0 else tile_h + self.gap_y_spin.value()
            
            # Calculate canvas size to fit all tiles
            pattern_w = (cols - 1) * pitch_x + tile_w
            pattern_h = (rows - 1) * pitch_y + tile_h
            
            # Create blank canvas (white or transparent based on selection)
            blank_colors = {
                "White": 255,
                "Light Gray": 192,
                "Dark Gray": 64,
                "Black": 0
            }
            color_value = blank_colors.get(self.blank_color_combo.currentText(), 255)
            pattern = np.ones((pattern_h, pattern_w, 3), dtype=np.uint8) * color_value
            
            self.log(f"Grid mode: {cols}×{rows} tiles, canvas size: {pattern_w}×{pattern_h}")
            
            for row in range(rows):
                for col in range(cols):
                    x = col * pitch_x
                    y = row * pitch_y
                    
                    # Paste tile
                    pattern[y:y+tile_h, x:x+tile_w] = self.tile_image
        
        else:
            # Manual mode - create grid based on X+/X-/Y+/Y- counts from base position
            base_x = self.canvas.tile_position[0]
            base_y = self.canvas.tile_position[1]
            
            x_plus = self.x_plus_count.value()
            x_minus = self.x_minus_count.value()
            y_plus = self.y_plus_count.value()
            y_minus = self.y_minus_count.value()
            
            # Get gap values
            gap_x = self.manual_gap_x.value()
            gap_y = self.manual_gap_y.value()
            
            # Calculate pitch (distance between tile origins)
            pitch_x = tile_w + gap_x
            pitch_y = tile_h + gap_y
            
            # Calculate grid dimensions
            cols = x_minus + x_plus + 1
            rows = y_plus + y_minus + 1
            total_tiles = cols * rows
            
            # Calculate the bounds of all tiles
            min_x = base_x - x_minus * pitch_x
            max_x = base_x + x_plus * pitch_x + tile_w
            min_y = base_y - y_plus * pitch_y
            max_y = base_y + y_minus * pitch_y + tile_h
            
            pattern_w = max_x - min_x
            pattern_h = max_y - min_y
            
            # Create blank canvas sized to fit all tiles
            blank_colors = {
                "White": 255,
                "Light Gray": 192,
                "Dark Gray": 64,
                "Black": 0
            }
            color_value = blank_colors.get(self.blank_color_combo.currentText(), 255)
            pattern = np.ones((pattern_h, pattern_w, 3), dtype=np.uint8) * color_value
            
            self.log(f"Manual mode: {cols}×{rows} grid = {total_tiles} tiles (X-={x_minus}, X+={x_plus}, Y+={y_plus}, Y-={y_minus}, Gap X={gap_x}, Gap Y={gap_y})")
            self.log(f"Canvas size: {pattern_w}×{pattern_h}, base offset: ({base_x},{base_y})")
            
            # Draw grid: nested loops create rows and columns
            # Y goes UP for y_plus (negative offset), DOWN for y_minus (positive offset)
            tile_count = 0
            for y_offset in range(-y_plus, y_minus + 1):
                # X goes LEFT for x_minus (negative offset), RIGHT for x_plus (positive offset)
                for x_offset in range(-x_minus, x_plus + 1):
                    # Calculate absolute position
                    abs_x = base_x + x_offset * pitch_x
                    abs_y = base_y + y_offset * pitch_y
                    
                    # Convert to canvas coordinates (relative to min_x, min_y)
                    canvas_x = abs_x - min_x
                    canvas_y = abs_y - min_y
                    
                    # Paste tile
                    pattern[canvas_y:canvas_y+tile_h, canvas_x:canvas_x+tile_w] = self.tile_image
                    tile_count += 1
            
            self.log(f"✓ Placed {tile_count} tiles successfully")
        
        # Metadata
        metadata = {
            'mode': 'grid' if self.rb_grid.isChecked() else 'manual',
            'tile_size': (tile_w, tile_h),
            'background_type': self.background_type,
            'opacity': self.opacity_slider.value() / 100.0
        }
        
        if self.rb_grid.isChecked():
            metadata.update({
                'grid_cols': self.cols_spin.value(),
                'grid_rows': self.rows_spin.value(),
                'pitch_x': self.pitch_x_spin.value(),
                'pitch_y': self.pitch_y_spin.value(),
                'gap_x': self.gap_x_spin.value(),
                'gap_y': self.gap_y_spin.value()
            })
        else:
            metadata.update({
                'position': tuple(self.canvas.tile_position),
                'x_plus_count': self.x_plus_count.value(),
                'x_minus_count': self.x_minus_count.value(),
                'y_plus_count': self.y_plus_count.value(),
                'y_minus_count': self.y_minus_count.value()
            })
        
        return pattern, metadata
    
    def saveSettings(self):
        """Save current settings to temp file for restoration"""
        import json
        settings = {
            'tile_path': self.tile_path,
            'tile_position': list(self.canvas.tile_position),
            'tile_width': self.tile_width_spin.value(),
            'tile_height': self.tile_height_spin.value(),
            'mode': 'grid' if self.rb_grid.isChecked() else 'manual',
            'opacity': self.opacity_slider.value(),
            'grid_cols': self.cols_spin.value(),
            'grid_rows': self.rows_spin.value(),
            'pitch_x': self.pitch_x_spin.value(),
            'pitch_y': self.pitch_y_spin.value(),
            'gap_x': self.gap_x_spin.value(),
            'gap_y': self.gap_y_spin.value(),
            'lock_aspect': self.chk_lock_aspect.isChecked(),
            'x_plus_count': self.x_plus_count.value(),
            'x_minus_count': self.x_minus_count.value(),
            'y_plus_count': self.y_plus_count.value(),
            'y_minus_count': self.y_minus_count.value(),
            'manual_gap_x': self.manual_gap_x.value(),
            'manual_gap_y': self.manual_gap_y.value()
        }
        
        try:
            settings_path = Path("config/pattern_designer_state.json")
            settings_path.parent.mkdir(exist_ok=True)
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log(f"Could not save settings: {e}")
    
    def loadSettings(self):
        """Load previous settings from temp file"""
        import json
        try:
            settings_path = Path("config/pattern_designer_state.json")
            if not settings_path.exists():
                return
            
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            
            # Restore tile if path exists
            if settings.get('tile_path') and Path(settings['tile_path']).exists():
                try:
                    img = cv2.imread(settings['tile_path'], cv2.IMREAD_COLOR)
                    if img is not None:
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        self.tile_image = img_rgb
                        self.tile_path = settings['tile_path']
                        self.canvas.setTileImage(img_rgb)
                        self.log(f"✓ Restored previous tile: {Path(settings['tile_path']).name}")
                except Exception as e:
                    self.log(f"Could not restore tile: {e}")
            
            # Restore settings
            self.tile_width_spin.setValue(settings.get('tile_width', 200))
            self.tile_height_spin.setValue(settings.get('tile_height', 200))
            self.opacity_slider.setValue(settings.get('opacity', 50))
            self.cols_spin.setValue(settings.get('grid_cols', 3))
            self.rows_spin.setValue(settings.get('grid_rows', 3))
            self.pitch_x_spin.setValue(settings.get('pitch_x', 0))
            self.pitch_y_spin.setValue(settings.get('pitch_y', 0))
            self.gap_x_spin.setValue(settings.get('gap_x', 10))
            self.gap_y_spin.setValue(settings.get('gap_y', 10))
            self.chk_lock_aspect.setChecked(settings.get('lock_aspect', False))
            
            # Restore directional tile counts and gaps
            self.x_plus_count.setValue(settings.get('x_plus_count', 2))
            self.x_minus_count.setValue(settings.get('x_minus_count', 2))
            self.y_plus_count.setValue(settings.get('y_plus_count', 1))
            self.y_minus_count.setValue(settings.get('y_minus_count', 1))
            self.manual_gap_x.setValue(settings.get('manual_gap_x', 0))
            self.manual_gap_y.setValue(settings.get('manual_gap_y', 0))
            
            # Restore mode
            if settings.get('mode') == 'manual':
                self.rb_manual.setChecked(True)
                self.canvas.tile_position = settings.get('tile_position', [0, 0])
            else:
                self.rb_grid.setChecked(True)
            
            self.canvas.update()
            self.log("✓ Restored previous session settings")
            
        except Exception as e:
            self.log(f"Could not load settings: {e}")
    
    def closeEvent(self, event):
        """Save settings when dialog closes"""
        self.saveSettings()
        super().closeEvent(event)
