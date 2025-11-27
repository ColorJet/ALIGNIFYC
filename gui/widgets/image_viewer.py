"""
Enhanced Image Viewer with Intensity Analysis

Features:
- Real-time histogram display
- Intensity statistics (min, max, mean, std)
- ROI selection for detailed analysis
- Intensity profile line tool
- Mouse hover pixel info
- Zoom and pan
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QGridLayout, QPushButton, QCheckBox, QComboBox, QSplitter,
    QFrame, QToolButton, QButtonGroup
)
from PySide6.QtCore import Qt, QRect, QPoint, QPointF, Signal, QSize
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QBrush,
    QMouseEvent, QWheelEvent, QPainterPath, QFont
)
import numpy as np


class HistogramWidget(QWidget):
    """Widget to display image histogram"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.histogram = None
        self.channel_colors = [QColor(255, 255, 255)]  # Grayscale default
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        
    def setHistogram(self, image_array):
        """Calculate and set histogram from image"""
        if image_array is None:
            self.histogram = None
            self.update()
            return
            
        try:
            if len(image_array.shape) == 2:
                # Grayscale
                hist, _ = np.histogram(image_array.flatten(), bins=256, range=(0, 256))
                self.histogram = [hist]
                self.channel_colors = [QColor(200, 200, 200)]
            elif len(image_array.shape) == 3:
                # RGB
                self.histogram = []
                self.channel_colors = [QColor(255, 80, 80), QColor(80, 255, 80), QColor(80, 80, 255)]
                for i in range(min(3, image_array.shape[2])):
                    hist, _ = np.histogram(image_array[:,:,i].flatten(), bins=256, range=(0, 256))
                    self.histogram.append(hist)
            self.update()
        except Exception as e:
            print(f"Histogram error: {e}")
            
    def paintEvent(self, event):
        """Draw histogram"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        if not self.histogram:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignCenter, "No image")
            return
            
        w = self.width() - 10
        h = self.height() - 20
        
        # Draw each channel
        for idx, hist in enumerate(self.histogram):
            if hist is None:
                continue
                
            # Normalize
            max_val = hist.max() if hist.max() > 0 else 1
            normalized = hist / max_val * h
            
            # Draw histogram bars
            color = self.channel_colors[idx % len(self.channel_colors)]
            color.setAlpha(180 if len(self.histogram) > 1 else 255)
            painter.setPen(QPen(color, 1))
            
            for i, val in enumerate(normalized):
                x = 5 + int(i * w / 256)
                painter.drawLine(x, h + 10, x, h + 10 - int(val))
                
        # Draw axis labels
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(5, h + 18, "0")
        painter.drawText(w - 15, h + 18, "255")


class IntensityStatsWidget(QWidget):
    """Widget to display intensity statistics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Create stat labels
        self.labels = {}
        stats = [
            ('min', 'Min:'), ('max', 'Max:'), 
            ('mean', 'Mean:'), ('std', 'Std:'),
            ('size', 'Size:'), ('dtype', 'Type:')
        ]
        
        for i, (key, text) in enumerate(stats):
            row, col = i // 2, (i % 2) * 2
            label = QLabel(text)
            label.setStyleSheet("color: #888; font-size: 10px;")
            layout.addWidget(label, row, col)
            
            value = QLabel("--")
            value.setStyleSheet("color: #fff; font-size: 10px; font-weight: bold;")
            layout.addWidget(value, row, col + 1)
            self.labels[key] = value
            
    def updateStats(self, image_array):
        """Update statistics from image array"""
        if image_array is None:
            for label in self.labels.values():
                label.setText("--")
            return
            
        try:
            self.labels['min'].setText(f"{image_array.min()}")
            self.labels['max'].setText(f"{image_array.max()}")
            self.labels['mean'].setText(f"{image_array.mean():.1f}")
            self.labels['std'].setText(f"{image_array.std():.1f}")
            self.labels['size'].setText(f"{image_array.shape[1]}×{image_array.shape[0]}")
            self.labels['dtype'].setText(str(image_array.dtype))
        except Exception as e:
            print(f"Stats error: {e}")


class ImageCanvas(QLabel):
    """Interactive image canvas with zoom, pan, and pixel info"""
    
    # Signals
    pixel_hovered = Signal(int, int, object)  # x, y, value
    roi_selected = Signal(QRect)  # Selected region
    line_drawn = Signal(QPoint, QPoint)  # Line profile points
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.setMinimumSize(400, 400)
        
        # Image data
        self.image_array = None
        self.q_image = None
        self.display_pixmap = None
        
        # View state
        self.zoom_factor = 1.0
        self.pan_offset = QPointF(0, 0)
        self.is_panning = False
        self.last_pan_pos = QPoint()
        
        # Tools
        self.current_tool = 'pan'  # 'pan', 'roi', 'line'
        self.roi_start = None
        self.roi_end = None
        self.line_start = None
        self.line_end = None
        
        # Overlay settings
        self.show_grid = False
        self.show_crosshair = True
        self.mouse_pos = QPoint()
        
    def setImage(self, image_array):
        """Set image from numpy array"""
        if image_array is None:
            self.image_array = None
            self.q_image = None
            self.update()
            return
            
        try:
            self.image_array = np.ascontiguousarray(image_array)
            
            # Convert to QImage
            if len(image_array.shape) == 2:
                height, width = image_array.shape
                bytes_per_line = width
                self.q_image = QImage(self.image_array.data, width, height, 
                                      bytes_per_line, QImage.Format_Grayscale8).copy()
            elif len(image_array.shape) == 3:
                height, width, channels = image_array.shape
                bytes_per_line = width * channels
                if channels == 3:
                    self.q_image = QImage(self.image_array.data, width, height,
                                         bytes_per_line, QImage.Format_RGB888).copy()
                elif channels == 4:
                    self.q_image = QImage(self.image_array.data, width, height,
                                         bytes_per_line, QImage.Format_RGBA8888).copy()
            
            self.fitInView()
            self.update()
        except Exception as e:
            print(f"Error setting image: {e}")
            import traceback
            traceback.print_exc()
            
    def fitInView(self):
        """Fit image in view"""
        if self.q_image is None:
            return
        self.zoom_factor = min(
            self.width() / self.q_image.width(),
            self.height() / self.q_image.height()
        ) * 0.95
        self.pan_offset = QPointF(0, 0)
        self.update()
        
    def setTool(self, tool):
        """Set current tool: 'pan', 'roi', 'line'"""
        self.current_tool = tool
        if tool == 'pan':
            self.setCursor(Qt.OpenHandCursor)
        elif tool == 'roi':
            self.setCursor(Qt.CrossCursor)
        elif tool == 'line':
            self.setCursor(Qt.CrossCursor)
            
    def imageToWidget(self, img_point):
        """Convert image coordinates to widget coordinates"""
        if self.q_image is None:
            return QPointF()
        center = QPointF(self.width() / 2, self.height() / 2)
        img_center = QPointF(self.q_image.width() / 2, self.q_image.height() / 2)
        return center + (QPointF(img_point) - img_center) * self.zoom_factor + self.pan_offset
        
    def widgetToImage(self, widget_point):
        """Convert widget coordinates to image coordinates"""
        if self.q_image is None:
            return QPoint()
        center = QPointF(self.width() / 2, self.height() / 2)
        img_center = QPointF(self.q_image.width() / 2, self.q_image.height() / 2)
        img_point = img_center + (QPointF(widget_point) - center - self.pan_offset) / self.zoom_factor
        return QPoint(int(img_point.x()), int(img_point.y()))
        
    def paintEvent(self, event):
        """Draw image and overlays"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        if self.q_image is None:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignCenter, "No Image\n\nDrag & drop or load image")
            return
            
        # Calculate transform
        center = QPointF(self.width() / 2, self.height() / 2)
        img_center = QPointF(self.q_image.width() / 2, self.q_image.height() / 2)
        
        painter.translate(center + self.pan_offset)
        painter.scale(self.zoom_factor, self.zoom_factor)
        painter.translate(-img_center)
        
        # Draw image
        painter.drawImage(0, 0, self.q_image)
        
        # Draw grid overlay
        if self.show_grid and self.zoom_factor > 2:
            painter.setPen(QPen(QColor(100, 100, 100, 100), 0))
            for x in range(0, self.q_image.width(), 10):
                painter.drawLine(x, 0, x, self.q_image.height())
            for y in range(0, self.q_image.height(), 10):
                painter.drawLine(0, y, self.q_image.width(), y)
                
        # Reset transform for overlays
        painter.resetTransform()
        
        # Draw ROI selection
        if self.roi_start and self.roi_end:
            painter.setPen(QPen(QColor(0, 255, 255), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 255, 255, 30)))
            p1 = self.imageToWidget(self.roi_start)
            p2 = self.imageToWidget(self.roi_end)
            painter.drawRect(QRect(p1.toPoint(), p2.toPoint()))
            
        # Draw line profile
        if self.line_start and self.line_end:
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            p1 = self.imageToWidget(self.line_start)
            p2 = self.imageToWidget(self.line_end)
            painter.drawLine(p1.toPoint(), p2.toPoint())
            # Draw endpoints
            painter.setBrush(QBrush(QColor(255, 255, 0)))
            painter.drawEllipse(p1.toPoint(), 5, 5)
            painter.drawEllipse(p2.toPoint(), 5, 5)
            
        # Draw crosshair at mouse position
        if self.show_crosshair and self.underMouse():
            painter.setPen(QPen(QColor(255, 100, 100, 150), 1))
            painter.drawLine(self.mouse_pos.x(), 0, self.mouse_pos.x(), self.height())
            painter.drawLine(0, self.mouse_pos.y(), self.width(), self.mouse_pos.y())
            
        # Draw zoom level
        painter.setPen(QColor(200, 200, 200))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(10, self.height() - 10, f"Zoom: {self.zoom_factor:.1f}x")
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.current_tool == 'pan':
                self.is_panning = True
                self.last_pan_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
            elif self.current_tool == 'roi':
                self.roi_start = self.widgetToImage(event.pos())
                self.roi_end = self.roi_start
            elif self.current_tool == 'line':
                self.line_start = self.widgetToImage(event.pos())
                self.line_end = self.line_start
                
    def mouseMoveEvent(self, event: QMouseEvent):
        self.mouse_pos = event.pos()
        
        if self.is_panning:
            delta = event.pos() - self.last_pan_pos
            self.pan_offset += QPointF(delta)
            self.last_pan_pos = event.pos()
            self.update()
        elif self.current_tool == 'roi' and self.roi_start:
            self.roi_end = self.widgetToImage(event.pos())
            self.update()
        elif self.current_tool == 'line' and self.line_start:
            self.line_end = self.widgetToImage(event.pos())
            self.update()
        else:
            # Emit pixel info
            if self.image_array is not None:
                img_pos = self.widgetToImage(event.pos())
                if (0 <= img_pos.x() < self.image_array.shape[1] and
                    0 <= img_pos.y() < self.image_array.shape[0]):
                    value = self.image_array[img_pos.y(), img_pos.x()]
                    self.pixel_hovered.emit(img_pos.x(), img_pos.y(), value)
            self.update()
                    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.is_panning:
                self.is_panning = False
                self.setCursor(Qt.OpenHandCursor)
            elif self.current_tool == 'roi' and self.roi_start and self.roi_end:
                rect = QRect(self.roi_start, self.roi_end).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    self.roi_selected.emit(rect)
            elif self.current_tool == 'line' and self.line_start and self.line_end:
                self.line_drawn.emit(self.line_start, self.line_end)
                
    def wheelEvent(self, event: QWheelEvent):
        """Zoom with mouse wheel"""
        # Get mouse position before zoom
        old_pos = self.widgetToImage(event.position().toPoint())
        
        # Zoom
        factor = 1.15 if event.angleDelta().y() > 0 else 0.87
        self.zoom_factor = max(0.1, min(50, self.zoom_factor * factor))
        
        # Adjust pan to keep mouse position stable
        new_pos = self.widgetToImage(event.position().toPoint())
        delta = QPointF(new_pos - old_pos) * self.zoom_factor
        self.pan_offset += delta
        
        self.update()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.q_image:
            self.update()


class ImageViewer(QWidget):
    """Enhanced widget for displaying and analyzing images"""
    
    # Signals for external use
    intensity_changed = Signal(dict)  # Emits intensity stats
    roi_analyzed = Signal(dict)  # Emits ROI analysis results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.image = None
        self.image_array = None
        self.pixmap = None
        self.title = ""
        self.zoom_factor = 1.0
        
        # For backward compatibility
        self.image_label = None
        
        self.initUI()
        
    def initUI(self):
        """Initialize UI with analysis tools"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        
        # Title
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; padding: 2px;")
        main_layout.addWidget(self.title_label)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(2)
        
        # Tool buttons
        self.btn_pan = QToolButton()
        self.btn_pan.setText("🖐")
        self.btn_pan.setToolTip("Pan (drag to move)")
        self.btn_pan.setCheckable(True)
        self.btn_pan.setChecked(True)
        
        self.btn_roi = QToolButton()
        self.btn_roi.setText("⬚")
        self.btn_roi.setToolTip("ROI selection (analyze region)")
        self.btn_roi.setCheckable(True)
        
        self.btn_line = QToolButton()
        self.btn_line.setText("📏")
        self.btn_line.setToolTip("Line profile (intensity along line)")
        self.btn_line.setCheckable(True)
        
        self.btn_fit = QToolButton()
        self.btn_fit.setText("⊡")
        self.btn_fit.setToolTip("Fit to view")
        
        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.setToolTip("Zoom in")
        
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("−")
        self.btn_zoom_out.setToolTip("Zoom out")
        
        # Tool button group
        self.tool_group = QButtonGroup(self)
        self.tool_group.addButton(self.btn_pan, 0)
        self.tool_group.addButton(self.btn_roi, 1)
        self.tool_group.addButton(self.btn_line, 2)
        self.tool_group.buttonClicked.connect(self.onToolChanged)
        
        for btn in [self.btn_pan, self.btn_roi, self.btn_line]:
            btn.setFixedSize(28, 28)
            toolbar.addWidget(btn)
            
        toolbar.addWidget(QLabel(" | "))
        
        for btn in [self.btn_fit, self.btn_zoom_in, self.btn_zoom_out]:
            btn.setFixedSize(28, 28)
            toolbar.addWidget(btn)
            
        # Options
        toolbar.addStretch()
        
        self.chk_histogram = QCheckBox("Histogram")
        self.chk_histogram.setChecked(True)
        self.chk_histogram.toggled.connect(self.onHistogramToggled)
        toolbar.addWidget(self.chk_histogram)
        
        self.chk_stats = QCheckBox("Stats")
        self.chk_stats.setChecked(True)
        self.chk_stats.toggled.connect(self.onStatsToggled)
        toolbar.addWidget(self.chk_stats)
        
        main_layout.addLayout(toolbar)
        
        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Image canvas
        self.canvas = ImageCanvas()
        self.canvas.pixel_hovered.connect(self.onPixelHovered)
        self.canvas.roi_selected.connect(self.onROISelected)
        self.canvas.line_drawn.connect(self.onLineDrawn)
        content_splitter.addWidget(self.canvas)
        
        # Right panel with histogram and stats
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(2)
        
        # Histogram
        self.histogram_group = QGroupBox("Histogram")
        hist_layout = QVBoxLayout(self.histogram_group)
        self.histogram_widget = HistogramWidget()
        hist_layout.addWidget(self.histogram_widget)
        right_layout.addWidget(self.histogram_group)
        
        # Statistics
        self.stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(self.stats_group)
        self.stats_widget = IntensityStatsWidget()
        stats_layout.addWidget(self.stats_widget)
        right_layout.addWidget(self.stats_group)
        
        # Pixel info
        self.pixel_info_group = QGroupBox("Pixel Info")
        pixel_layout = QGridLayout(self.pixel_info_group)
        pixel_layout.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_pos = QLabel("Position: --")
        self.lbl_value = QLabel("Value: --")
        pixel_layout.addWidget(self.lbl_pos, 0, 0)
        pixel_layout.addWidget(self.lbl_value, 1, 0)
        right_layout.addWidget(self.pixel_info_group)
        
        # ROI analysis results
        self.roi_group = QGroupBox("ROI Analysis")
        roi_layout = QVBoxLayout(self.roi_group)
        self.roi_stats = QLabel("Select region with ROI tool")
        self.roi_stats.setWordWrap(True)
        self.roi_stats.setStyleSheet("font-size: 10px;")
        roi_layout.addWidget(self.roi_stats)
        self.roi_group.setVisible(False)
        right_layout.addWidget(self.roi_group)
        
        right_layout.addStretch()
        
        right_panel.setMaximumWidth(200)
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([600, 200])
        
        main_layout.addWidget(content_splitter, 1)
        
        # Connect buttons
        self.btn_fit.clicked.connect(self.canvas.fitInView)
        self.btn_zoom_in.clicked.connect(lambda: self.zoom(1.25))
        self.btn_zoom_out.clicked.connect(lambda: self.zoom(0.8))
        
        # Backward compatibility - create image_label reference
        self.image_label = self.canvas
        
    def setTitle(self, title):
        """Set viewer title"""
        self.title = title
        self.title_label.setText(f"<b>{title}</b>")
        
    def setImage(self, image_array):
        """Set image from numpy array"""
        if image_array is None:
            self.image_array = None
            self.canvas.setImage(None)
            self.histogram_widget.setHistogram(None)
            self.stats_widget.updateStats(None)
            return
        
        try:
            self.image_array = np.ascontiguousarray(image_array)
            
            # Update canvas
            self.canvas.setImage(self.image_array)
            
            # Update histogram
            self.histogram_widget.setHistogram(self.image_array)
            
            # Update statistics
            self.stats_widget.updateStats(self.image_array)
            
            # Emit intensity changed
            stats = self.getIntensityStats()
            self.intensity_changed.emit(stats)
            
            # Keep backward compatible image reference
            self.image = self.canvas.q_image
            
        except Exception as e:
            print(f"Error setting image: {e}")
            import traceback
            traceback.print_exc()
            
    def getIntensityStats(self):
        """Get intensity statistics as dictionary"""
        if self.image_array is None:
            return {}
        return {
            'min': int(self.image_array.min()),
            'max': int(self.image_array.max()),
            'mean': float(self.image_array.mean()),
            'std': float(self.image_array.std()),
            'shape': self.image_array.shape,
            'dtype': str(self.image_array.dtype)
        }
        
    def onToolChanged(self, button):
        """Handle tool selection change"""
        if button == self.btn_pan:
            self.canvas.setTool('pan')
        elif button == self.btn_roi:
            self.canvas.setTool('roi')
            self.roi_group.setVisible(True)
        elif button == self.btn_line:
            self.canvas.setTool('line')
            
    def onHistogramToggled(self, checked):
        """Show/hide histogram"""
        self.histogram_group.setVisible(checked)
        
    def onStatsToggled(self, checked):
        """Show/hide stats"""
        self.stats_group.setVisible(checked)
        
    def onPixelHovered(self, x, y, value):
        """Handle pixel hover event"""
        self.lbl_pos.setText(f"Position: ({x}, {y})")
        if isinstance(value, np.ndarray):
            # RGB value
            self.lbl_value.setText(f"RGB: {value[0]}, {value[1]}, {value[2]}")
        else:
            # Grayscale value
            self.lbl_value.setText(f"Value: {value}")
            
    def onROISelected(self, rect):
        """Handle ROI selection - analyze region"""
        if self.image_array is None:
            return
            
        try:
            # Clamp to image bounds
            x1 = max(0, rect.left())
            y1 = max(0, rect.top())
            x2 = min(self.image_array.shape[1], rect.right())
            y2 = min(self.image_array.shape[0], rect.bottom())
            
            if x2 <= x1 or y2 <= y1:
                return
                
            roi = self.image_array[y1:y2, x1:x2]
            
            # Calculate ROI statistics
            stats = {
                'region': f"({x1},{y1}) to ({x2},{y2})",
                'size': f"{x2-x1} × {y2-y1}",
                'min': int(roi.min()),
                'max': int(roi.max()),
                'mean': float(roi.mean()),
                'std': float(roi.std()),
                'dynamic_range': int(roi.max()) - int(roi.min())
            }
            
            # Update ROI display
            self.roi_stats.setText(
                f"Region: {stats['region']}\n"
                f"Size: {stats['size']} px\n"
                f"Min: {stats['min']}  Max: {stats['max']}\n"
                f"Mean: {stats['mean']:.1f}  Std: {stats['std']:.1f}\n"
                f"Dynamic Range: {stats['dynamic_range']}"
            )
            
            # Emit signal
            self.roi_analyzed.emit(stats)
            
        except Exception as e:
            print(f"ROI analysis error: {e}")
            
    def onLineDrawn(self, start, end):
        """Handle line profile drawn - show intensity along line"""
        if self.image_array is None:
            return
            
        try:
            # Get line profile using Bresenham's algorithm
            x0, y0 = start.x(), start.y()
            x1, y1 = end.x(), end.y()
            
            # Simple line sampling
            length = int(np.sqrt((x1-x0)**2 + (y1-y0)**2))
            if length == 0:
                return
                
            x = np.linspace(x0, x1, length).astype(int)
            y = np.linspace(y0, y1, length).astype(int)
            
            # Clamp to image bounds
            valid = (x >= 0) & (x < self.image_array.shape[1]) & \
                    (y >= 0) & (y < self.image_array.shape[0])
            x, y = x[valid], y[valid]
            
            if len(x) == 0:
                return
                
            profile = self.image_array[y, x]
            
            # Show profile info in ROI panel
            self.roi_group.setVisible(True)
            if len(profile.shape) > 1:
                # RGB - show mean
                profile = profile.mean(axis=1)
            
            self.roi_stats.setText(
                f"Line: ({x0},{y0}) → ({x1},{y1})\n"
                f"Length: {length} px\n"
                f"Min: {profile.min():.0f}  Max: {profile.max():.0f}\n"
                f"Mean: {profile.mean():.1f}\n"
                f"Range: {profile.max()-profile.min():.0f}"
            )
            
        except Exception as e:
            print(f"Line profile error: {e}")
            
    def zoom(self, factor):
        """Zoom by factor"""
        self.canvas.zoom_factor = max(0.1, min(50, self.canvas.zoom_factor * factor))
        self.canvas.update()
        
    def updateDisplay(self):
        """Update displayed image (backward compatibility)"""
        self.canvas.update()
            
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self.canvas.update()
