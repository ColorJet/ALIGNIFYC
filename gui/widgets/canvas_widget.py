"""
Canvas Widget - Main image display area with layer composition
"""

import numpy as np
import cv2
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont

from .layer_manager import LayerCompositor


class ImageCanvas(QWidget):
    """Main canvas for displaying composed layers - Photoshop-style"""
    
    controlPointAdded = Signal(str, float, float)  # mode ("red" or "blue"), x, y in image coords
    
    def __init__(self):
        super().__init__()
        self.composed_image = None
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.dragging = False
        self.last_pos = None
        self.min_zoom = 0.01  # 1% minimum zoom
        self.max_zoom = 50.0  # 5000% maximum zoom
        
        # Canvas background pattern
        self.checkerboard_size = 16
        self.canvas_color = QColor(64, 64, 64)  # Dark gray like Photoshop
        self.current_theme = 'dark'  # Track current theme
        
        # Control point mode and markers
        self.control_point_mode = "none"  # "red", "blue", or "none"
        self.red_markers = []   # [(x, y, label), ...]
        self.blue_markers = []  # [(x, y, label), ...]
        
        # Brush size for control point influence (Photoshop puppet warp style)
        self.brush_size = 320  # Default: ~10x typical grid spacing of 32
        self._show_brush_indicator = False
        self._last_mouse_pos = None
        
        self.setupUI()
        
    def setupUI(self):
        """Setup canvas UI - Photoshop-style with maximum space"""
        # No layout needed - we paint directly on the widget
        # Create invisible labels for compatibility (other code references them)
        self.info_label = QLabel()
        self.zoom_label = QLabel()
        # Make them invisible children so they don't take up space
        self.info_label.setParent(self)
        self.zoom_label.setParent(self)
        self.info_label.setVisible(False)
        self.zoom_label.setVisible(False)
        
        # Main canvas area (no scroll area - we handle scrolling manually)
        self.setStyleSheet("""
            ImageCanvas {
                background-color: #404040;
                border: none;
            }
        """)
        
        # Set minimum size for proper canvas feel (increased height by 200px)
        self.setMinimumSize(800, 800)
        
        # Enable mouse tracking for all mouse operations
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)  # Allow wheel events
        
    def setTheme(self, theme='dark'):
        """Set canvas background color based on theme"""
        self.current_theme = theme
        if theme == 'dark':
            self.canvas_color = QColor(64, 64, 64)  # Dark gray
        elif theme == 'light':
            self.canvas_color = QColor(200, 200, 200)  # Light gray
        else:  # native
            # DISABLED: Theme switching commented out - focus on performance, not aesthetics
            # Native theme causes compatibility issues with different Qt versions
            self.canvas_color = QColor(64, 64, 64)  # Use dark gray as default
            # from PySide6.QtWidgets import QApplication
            # palette = QApplication.palette()
            # self.canvas_color = palette.color(palette.ColorRole.Window)  # Qt6 syntax
        
        self.update()
    
    def setComposedImage(self, image):
        """Set the composed image to display"""
        self.composed_image = image
        
        # Info will be shown in status bar instead of taking up canvas space
        # Trigger repaint
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for Photoshop-style canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background with canvas color
        painter.fillRect(self.rect(), self.canvas_color)
        
        if self.composed_image is not None:
            # Convert numpy array to QPixmap
            pixmap = self.arrayToPixmap(self.composed_image)
            
            if pixmap is not None:
                # Calculate display size and position
                img_w = int(pixmap.width() * self.zoom_factor)
                img_h = int(pixmap.height() * self.zoom_factor)
                
                # Center image on canvas with pan offset
                canvas_center_x = self.width() // 2
                canvas_center_y = self.height() // 2
                
                img_x = canvas_center_x - img_w // 2 + self.pan_x
                img_y = canvas_center_y - img_h // 2 + self.pan_y
                
                # Scale pixmap to zoom level
                if self.zoom_factor != 1.0:
                    scaled_pixmap = pixmap.scaled(img_w, img_h, Qt.KeepAspectRatio, 
                                                Qt.SmoothTransformation if self.zoom_factor > 1.0 else Qt.FastTransformation)
                else:
                    scaled_pixmap = pixmap
                
                # Draw the image
                painter.drawPixmap(img_x, img_y, scaled_pixmap)
                
                # Draw checkerboard pattern behind transparent areas (if needed)
                if self.hasTransparency(self.composed_image):
                    self.drawCheckerboard(painter, img_x, img_y, img_w, img_h)
                
                # Draw control point markers on top of image
                self.drawControlPointMarkers(painter, img_x, img_y, self.zoom_factor)
                
                # Draw brush size indicator (Photoshop style) at cursor position
                if hasattr(self, '_show_brush_indicator') and self._show_brush_indicator:
                    if hasattr(self, '_last_mouse_pos') and hasattr(self, 'brush_size'):
                        cursor_x = self._last_mouse_pos.x()
                        cursor_y = self._last_mouse_pos.y()
                        
                        # Draw circle showing influence area
                        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                        painter.setBrush(Qt.NoBrush)
                        scaled_size = int(self.brush_size * self.zoom_factor / 2)
                        painter.drawEllipse(int(cursor_x - scaled_size), int(cursor_y - scaled_size), 
                                          scaled_size * 2, scaled_size * 2)
                        
                        # Draw size text
                        painter.setPen(QColor(255, 255, 255))
                        font = QFont("Arial", 12)
                        font.setBold(True)
                        painter.setFont(font)
                        size_text = f"{self.brush_size}px"
                        painter.drawText(int(cursor_x + scaled_size + 10), int(cursor_y), size_text)
        else:
            # Check if parent has warmup status (during initialization)
            parent = self.parent()
            while parent is not None and not hasattr(parent, 'warmup_status'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'is_ready') and not parent.is_ready:
                # Show warmup status in BIG BOLD letters
                painter.setPen(QColor(255, 180, 0))  # Orange
                font = QFont("Arial", 32, QFont.Bold)
                painter.setFont(font)
                
                warmup_text = getattr(parent, 'warmup_status', 'Initializing...')
                painter.drawText(self.rect(), Qt.AlignCenter, warmup_text)
                
                # Show smaller progress text below
                painter.setPen(QColor(200, 200, 200))
                font = QFont("Arial", 14)
                painter.setFont(font)
                progress_text = "This may take 15-20 seconds on first launch"
                text_rect = self.rect().adjusted(0, 80, 0, 0)
                painter.drawText(text_rect, Qt.AlignCenter, progress_text)
            else:
                # Show COLORJET branding and keyboard shortcuts
                painter.setPen(QColor(0, 153, 204))  # Blue
                font = QFont("Impact", 48, QFont.Bold)
                painter.setFont(font)
                
                # COLORJET title
                title_rect = self.rect().adjusted(0, -200, 0, 0)
                painter.drawText(title_rect, Qt.AlignCenter, "COLORJET")
                
                # Keyboard shortcuts
                painter.setPen(QColor(180, 180, 180))
                font = QFont("Arial", 12)
                painter.setFont(font)
                
                shortcuts_text = """
                    Keyboard Shortcuts:
                
                    Ctrl+O - Load Camera Image
                    Ctrl+Shift+O - Load Design Image
                    Ctrl+R - Start Registration
                    Ctrl+T - Open Pattern Designer
                    Ctrl+M - Manual Correction Mode
                    Ctrl+E - Export Result

                    Mouse Controls:
                    Middle Click + Drag - Pan
                    Scroll Wheel - Zoom In/Out
                    """
                shortcuts_rect = self.rect().adjusted(0, 50, 0, 0)
                painter.drawText(shortcuts_rect, Qt.AlignCenter, shortcuts_text)
        
        # Zoom info will be shown in status bar instead of taking up canvas space
    
    def arrayToPixmap(self, array):
        """Convert numpy array to QPixmap"""
        try:
            if len(array.shape) == 2:
                # Grayscale
                h, w = array.shape
                bytes_per_line = w
                q_image = QImage(array.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            else:
                # RGB
                h, w, ch = array.shape
                bytes_per_line = ch * w
                q_image = QImage(array.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error converting array to pixmap: {e}")
            return None
    
    def hasTransparency(self, array):
        """Check if image has transparency (4 channels)"""
        return len(array.shape) > 2 and array.shape[2] == 4
    
    def drawCheckerboard(self, painter, x, y, w, h):
        """Draw checkerboard pattern for transparency"""
        painter.save()
        
        # Create checkerboard pattern
        tile_size = max(4, int(self.checkerboard_size * self.zoom_factor))
        light_color = QColor(200, 200, 200)
        dark_color = QColor(170, 170, 170)
        
        for i in range(int(x), int(x + w), tile_size):
            for j in range(int(y), int(y + h), tile_size):
                # Determine tile color based on position
                is_light = ((i - int(x)) // tile_size + (j - int(y)) // tile_size) % 2 == 0
                painter.fillRect(i, j, tile_size, tile_size, 
                               light_color if is_light else dark_color)
        
        painter.restore()
    
    def drawControlPointMarkers(self, painter, img_x, img_y, zoom):
        """Draw red and blue control point markers"""
        painter.save()
        
        # Marker size (scales with zoom, but has min/max)
        marker_radius = max(6, min(12, int(8 * zoom)))
        
        # Draw red markers (control points)
        for x, y, label in self.red_markers:
            screen_x = img_x + x * zoom
            screen_y = img_y + y * zoom
            
            # Red circle with white border
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QColor(255, 50, 50, 200))
            painter.drawEllipse(int(screen_x - marker_radius), int(screen_y - marker_radius), 
                              marker_radius * 2, marker_radius * 2)
            
            # Draw label
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(int(screen_x - 6), int(screen_y + 5), label)
        
        # Draw blue markers (offset points)
        for x, y, label in self.blue_markers:
            screen_x = img_x + x * zoom
            screen_y = img_y + y * zoom
            
            # Blue circle with white border
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QColor(0, 120, 255, 200))
            painter.drawEllipse(int(screen_x - marker_radius), int(screen_y - marker_radius), 
                              marker_radius * 2, marker_radius * 2)
            
            # Draw label
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(int(screen_x - 6), int(screen_y + 5), label)
        
        painter.restore()
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming - Photoshop style"""
        if self.composed_image is None:
            return
            
        # Get mouse position for zoom center
        mouse_pos = event.position()
        
        # Calculate zoom change
        delta = event.angleDelta().y()
        zoom_in = delta > 0
        
        # Store old zoom and position
        old_zoom = self.zoom_factor
        
        # Calculate new zoom level (exponential scaling like Photoshop)
        if zoom_in:
            self.zoom_factor = min(self.max_zoom, self.zoom_factor * 1.15)
        else:
            self.zoom_factor = max(self.min_zoom, self.zoom_factor / 1.15)
        
        if self.zoom_factor != old_zoom:
            # Zoom towards mouse position
            zoom_ratio = self.zoom_factor / old_zoom
            
            # Calculate mouse position relative to canvas center
            canvas_center_x = self.width() // 2
            canvas_center_y = self.height() // 2
            
            mouse_offset_x = mouse_pos.x() - canvas_center_x
            mouse_offset_y = mouse_pos.y() - canvas_center_y
            
            # Adjust pan to keep mouse position fixed during zoom
            self.pan_x = (self.pan_x - mouse_offset_x) * zoom_ratio + mouse_offset_x
            self.pan_y = (self.pan_y - mouse_offset_y) * zoom_ratio + mouse_offset_y
            
            self.update()  # Repaint
        
        event.accept()
    
    def mousePressEvent(self, event):
        """Handle mouse press for panning, control points, and selection"""
        # Control point mode - SIMPLIFIED: left click = red, right click = blue (no mode buttons needed)
        if self.control_point_mode == "enabled":
            if event.button() == Qt.LeftButton:
                # Add red control point (left-click)
                img_x, img_y = self.screenToImageCoords(event.pos().x(), event.pos().y())
                if img_x is not None and img_y is not None:
                    self.controlPointAdded.emit("red", img_x, img_y)
                    event.accept()
                    return
            elif event.button() == Qt.RightButton:
                # Add blue offset point (right-click)
                img_x, img_y = self.screenToImageCoords(event.pos().x(), event.pos().y())
                if img_x is not None and img_y is not None:
                    self.controlPointAdded.emit("blue", img_x, img_y)
                    event.accept()
                    return
        
        # Normal panning behavior
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() == Qt.AltModifier):
            # Start panning (middle mouse or Alt+Left)
            self.dragging = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.RightButton:
            # Right click for context menu (future) - only if not in control point mode
            if self.control_point_mode == "none":
                event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for panning and brush indicator"""
        # Track mouse position for brush size indicator
        self._last_mouse_pos = event.position()
        
        if self.dragging and self.last_pos is not None:
            # Calculate pan delta
            delta = event.pos() - self.last_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_pos = event.pos()
            
            self.update()  # Repaint with new pan
            event.accept()
        else:
            # Update cursor based on modifiers
            if event.modifiers() == Qt.AltModifier:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self.dragging):
            self.dragging = False
            self.last_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Alt:
            self.setCursor(Qt.OpenHandCursor)
        elif event.key() == Qt.Key_Space:
            # Space bar for temporary hand tool (like Photoshop)
            if not self.dragging:
                self.setCursor(Qt.OpenHandCursor)
        elif event.key() == Qt.Key_BracketLeft:  # [
            # Decrease brush size (control point influence area)
            if hasattr(self, 'brush_size'):
                self.brush_size = max(50, self.brush_size - 20)
                self.show_brush_size_indicator()
                self.update()
        elif event.key() == Qt.Key_BracketRight:  # ]
            # Increase brush size (control point influence area)
            if hasattr(self, 'brush_size'):
                self.brush_size = min(1000, self.brush_size + 20)
                self.show_brush_size_indicator()
                self.update()
        super().keyPressEvent(event)
    
    def show_brush_size_indicator(self):
        """Show temporary brush size indicator (Photoshop style)"""
        # This will be shown in the overlay during painting
        if not hasattr(self, '_brush_indicator_timer'):
            self._brush_indicator_timer = QTimer()
            self._brush_indicator_timer.setSingleShot(True)
            self._brush_indicator_timer.timeout.connect(self.update)
        
        self._show_brush_indicator = True
        self._brush_indicator_timer.start(1000)  # Show for 1 second
        self.update()
    
    def keyReleaseEvent(self, event):
        """Handle key release"""
        if event.key() == Qt.Key_Alt or event.key() == Qt.Key_Space:
            if not self.dragging:
                self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)
    
    def resetView(self):
        """Reset zoom and pan to defaults"""
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()
    
    def fitToWindow(self):
        """Fit image to window size"""
        if self.composed_image is None:
            return
        
        # Get available canvas area (accounting for margins)
        available_width = self.width() - 40  # Leave some margin
        available_height = self.height() - 40
        
        # Get image size
        img_height, img_width = self.composed_image.shape[:2]
        
        # Calculate zoom to fit both dimensions
        zoom_x = available_width / img_width
        zoom_y = available_height / img_height
        
        # Use the smaller zoom factor to ensure entire image fits
        self.zoom_factor = min(zoom_x, zoom_y)
        self.zoom_factor = max(self.min_zoom, min(self.max_zoom, self.zoom_factor))
        
        # Center the image
        self.pan_x = 0
        self.pan_y = 0
        
        self.update()
    
    def zoomToActualSize(self):
        """Zoom to 100% (actual pixel size)"""
        self.zoom_factor = 1.0
        self.pan_x = 0  
        self.pan_y = 0
        self.update()
    
    def zoomIn(self):
        """Zoom in by fixed increment"""
        self.zoom_factor = min(self.max_zoom, self.zoom_factor * 1.5)
        self.update()
    
    def zoomOut(self):
        """Zoom out by fixed increment"""
        self.zoom_factor = max(self.min_zoom, self.zoom_factor / 1.5)
        self.update()
    
    def centerImage(self):
        """Center the image in the canvas"""
        self.pan_x = 0
        self.pan_y = 0
        self.update()
    
    def setControlPointMode(self, mode):
        """Set control point mode: 'red', 'blue', or 'none'"""
        self.control_point_mode = mode
        if mode == "red":
            self.setCursor(Qt.CrossCursor)
        elif mode == "blue":
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def addRedMarker(self, x, y, label):
        """Add a red control point marker at image coordinates (x, y)"""
        self.red_markers.append((x, y, label))
        self.update()  # Repaint to show marker
    
    def addBlueMarker(self, x, y, label):
        """Add a blue offset point marker at image coordinates (x, y)"""
        self.blue_markers.append((x, y, label))
        self.update()  # Repaint to show marker
    
    def clearMarkers(self):
        """Clear all control point markers"""
        self.red_markers.clear()
        self.blue_markers.clear()
        self.update()
    
    def removeRedMarker(self, index):
        """Remove a specific red marker by index"""
        if 0 <= index < len(self.red_markers):
            self.red_markers.pop(index)
            self.update()
    
    def removeBlueMarker(self, index):
        """Remove a specific blue marker by index"""
        if 0 <= index < len(self.blue_markers):
            self.blue_markers.pop(index)
            self.update()
    
    def removeMarkerPair(self, index):
        """Remove both red and blue markers at given index"""
        removed = False
        if 0 <= index < len(self.red_markers):
            self.red_markers.pop(index)
            removed = True
        if 0 <= index < len(self.blue_markers):
            self.blue_markers.pop(index)
            removed = True
        if removed:
            self.update()
    
    def screenToImageCoords(self, screen_x, screen_y):
        """Convert screen coordinates to image coordinates"""
        if self.composed_image is None:
            return None, None
        
        # Account for zoom and pan
        img_h, img_w = self.composed_image.shape[:2]
        
        # Center of widget
        widget_center_x = self.width() / 2
        widget_center_y = self.height() / 2
        
        # Image dimensions in screen space
        scaled_w = img_w * self.zoom_factor
        scaled_h = img_h * self.zoom_factor
        
        # Top-left corner of image in screen space
        img_left = widget_center_x - scaled_w / 2 + self.pan_x
        img_top = widget_center_y - scaled_h / 2 + self.pan_y
        
        # Convert to image coordinates
        img_x = (screen_x - img_left) / self.zoom_factor
        img_y = (screen_y - img_top) / self.zoom_factor
        
        # Check bounds
        if 0 <= img_x < img_w and 0 <= img_y < img_h:
            return img_x, img_y
        return None, None


class LayerCanvas(QWidget):
    """Combined canvas and layer management widget"""
    
    def __init__(self):
        super().__init__()
        self.layer_manager = None
        self.canvas = None
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.updateComposition)
        
        # Composition cache to avoid redundant recompositions
        self._composition_cache = None
        self._cache_hash = None
        
        self.setupUI()
        
    def setupUI(self):
        """Setup the layer canvas UI - Canvas only, layer manager moved to control panel"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main canvas area (full width now)
        self.canvas = ImageCanvas()
        layout.addWidget(self.canvas)
        
        # Import layer manager here to avoid circular imports
        from .layer_manager import LayerManager
        
        # Layer management panel (will be moved to control panel)
        self.layer_manager = LayerManager()
        self.layer_manager.layersChanged.connect(self.scheduleUpdate)
        
    def addImageLayer(self, name, image, blend_mode="Normal", opacity=1.0, visible=True):
        """Add an image layer"""
        if self.layer_manager:
            self.layer_manager.addLayer(name, image, blend_mode, opacity, visible)
    
    def removeLayer(self, name):
        """Remove a layer"""
        if self.layer_manager:
            self.layer_manager.removeLayer(name)
    
    def scheduleUpdate(self):
        """Schedule a composition update (debounced)"""
        self.update_timer.start(200)  # 200ms delay
    
    def _compute_layers_hash(self, layers_data, global_settings):
        """Compute a hash of layer data to detect changes"""
        import hashlib
        
        hash_parts = []
        for layer in layers_data:
            # Include layer properties that affect composition
            hash_parts.append(str(layer.get('name', '')))
            hash_parts.append(str(layer.get('visible', False)))
            hash_parts.append(str(layer.get('blend_mode', 'Normal')))
            hash_parts.append(str(layer.get('opacity', 1.0)))
            hash_parts.append(str(layer.get('inverted', False)))
            
            # Include image shape and data hash (not full image to save time)
            img = layer.get('image')
            if img is not None and hasattr(img, 'shape'):
                hash_parts.append(str(img.shape))
                # Sample a few pixels for quick hash (corners and center)
                if img.size > 0:
                    samples = [
                        img[0, 0] if img.ndim > 1 else img[0],
                        img[-1, -1] if img.ndim > 1 else img[-1],
                        img[img.shape[0]//2, img.shape[1]//2] if img.ndim > 1 else img[img.shape[0]//2]
                    ]
                    hash_parts.append(str(samples))
        
        # Include global settings
        hash_parts.append(str(global_settings))
        
        # Compute hash
        hash_str = '|'.join(hash_parts)
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    def updateComposition(self):
        """Update the composed image with caching"""
        import time
        comp_start = time.time()
        print(f"\n⏱️ updateComposition() started...")
        
        if not self.layer_manager:
            return
        
        print(f"[+{time.time()-comp_start:.3f}s] Getting layer data...")
        layers_data = self.layer_manager.getLayerData()
        global_settings = self.layer_manager.getGlobalSettings()
        print(f"[+{time.time()-comp_start:.3f}s] Got {len(layers_data)} visible layers")
        
        if not layers_data:
            self.canvas.setComposedImage(None)
            self._composition_cache = None
            self._cache_hash = None
            return
        
        # Check cache to avoid redundant composition
        current_hash = self._compute_layers_hash(layers_data, global_settings)
        print(f"[+{time.time()-comp_start:.3f}s] Layer hash: {current_hash[:8]}...")
        
        if current_hash == self._cache_hash and self._composition_cache is not None:
            print(f"[+{time.time()-comp_start:.3f}s] ✅ Using cached composition (no changes detected)")
            print(f"[+{time.time()-comp_start:.3f}s] ✅ updateComposition() complete (Total: {time.time()-comp_start:.1f}s) - CACHED\n")
            return
        
        # Compose layers (with preview downsampling for speed)
        print(f"[+{time.time()-comp_start:.3f}s] Calling LayerCompositor.compose_layers() (THIS IS THE SLOW PART)...")
        print(f"   → Using preview downsampling to 1024px for 4-16x speedup")
        composed = LayerCompositor.compose_layers(layers_data, global_settings, max_preview_size=1024)
        print(f"[+{time.time()-comp_start:.3f}s] Composition complete! Result shape: {composed.shape if hasattr(composed, 'shape') else 'unknown'}")
        
        # Update cache
        self._composition_cache = composed
        self._cache_hash = current_hash
        print(f"[+{time.time()-comp_start:.3f}s] Cache updated")
        
        print(f"[+{time.time()-comp_start:.3f}s] Setting composed image to canvas...")
        self.canvas.setComposedImage(composed)
        print(f"[+{time.time()-comp_start:.3f}s] ✅ updateComposition() complete (Total: {time.time()-comp_start:.1f}s)\n")
    
    def fitToWindow(self):
        """Fit canvas to window"""
        if self.canvas:
            self.canvas.fitToWindow()
    
    def resetView(self):
        """Reset canvas view"""
        if self.canvas:
            self.canvas.resetView()
    
    def zoomToActualSize(self):
        """Zoom to actual size"""
        if self.canvas:
            self.canvas.zoomToActualSize()
    
    def zoomIn(self):
        """Zoom in"""
        if self.canvas:
            self.canvas.zoomIn()
    
    def zoomOut(self):
        """Zoom out"""
        if self.canvas:
            self.canvas.zoomOut()
    
    def centerImage(self):
        """Center image"""
        if self.canvas:
            self.canvas.centerImage()
    
    def clearLayers(self):
        """Clear all layers"""
        if self.layer_manager:
            for name in list(self.layer_manager.layers.keys()):
                self.layer_manager.removeLayer(name)