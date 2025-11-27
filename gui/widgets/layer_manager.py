"""
Layer Management Widget - Photoshop/Photopea style layer panel
"""

import numpy as np
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QSlider, QLabel, QCheckBox, QGroupBox,
    QSpinBox, QFrame, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QImage


class LayerItem(QWidget):
    """Individual layer widget with controls"""
    
    visibilityChanged = Signal(str, bool)  # layer_name, visible
    blendModeChanged = Signal(str, str)    # layer_name, blend_mode
    opacityChanged = Signal(str, float)    # layer_name, opacity
    invertChanged = Signal(str, bool)      # layer_name, inverted
    
    def __init__(self, layer_name, image_data=None):
        super().__init__()
        self.layer_name = layer_name
        self.image_data = image_data
        self.visible = True
        self.opacity = 1.0
        self.blend_mode = "Normal"
        self._commit_via_keyboard = False
        self.inverted = False
        
        self.setupUI()
        
    def setupUI(self):
        """Setup layer item UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        
        # Visibility checkbox (eye icon)
        self.visibility_cb = QCheckBox()
        self.visibility_cb.setChecked(self.visible)
        self.visibility_cb.setToolTip("Show/Hide Layer")
        self.visibility_cb.toggled.connect(self.onVisibilityChanged)
        layout.addWidget(self.visibility_cb)
        
        # Layer thumbnail (if image available)
        if self.image_data is not None:
            thumbnail = self.createThumbnail(self.image_data, (128, 128))
            thumb_label = QLabel()
            thumb_label.setPixmap(thumbnail)
            thumb_label.setFixedSize(128, 128)
            layout.addWidget(thumb_label)
        
        # Layer name
        name_label = QLabel(self.layer_name)
        name_label.setFont(QFont("Arial", 9))
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Invert checkbox
        self.invert_cb = QCheckBox("Inv")
        self.invert_cb.setToolTip("Invert layer colors (useful for registration)")
        self.invert_cb.setChecked(False)
        self.invert_cb.toggled.connect(self.onInvertChanged)
        layout.addWidget(self.invert_cb)
        
        # Opacity slider
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(60)
        self.opacity_slider.setToolTip("Layer Opacity")
        self.opacity_slider.valueChanged.connect(self.onOpacitySliderChanged)
        layout.addWidget(self.opacity_slider)
        
        # Opacity spin box for precise input
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setFixedWidth(48)
        self.opacity_spin.editingFinished.connect(self.onOpacitySpinEditingFinished)
        layout.addWidget(self.opacity_spin)
        if self.opacity_spin.lineEdit():
            self.opacity_spin.lineEdit().installEventFilter(self)
        
    def createThumbnail(self, image, size):
        """Create thumbnail from image data"""
        try:
            if len(image.shape) == 2:
                # Grayscale
                thumb_array = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
                h, w = thumb_array.shape
                bytes_per_line = w
                q_image = QImage(thumb_array.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            else:
                # RGB
                thumb_array = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
                h, w, ch = thumb_array.shape
                bytes_per_line = ch * w
                q_image = QImage(thumb_array.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            return QPixmap.fromImage(q_image)
        except:
            # Fallback to solid color
            pixmap = QPixmap(size[0], size[1])
            pixmap.fill(QColor(128, 128, 128))
            return pixmap
    
    def onVisibilityChanged(self, visible):
        """Handle visibility change"""
        self.visible = visible
        self.visibilityChanged.emit(self.layer_name, visible)
    
    def onInvertChanged(self, inverted):
        """Handle invert change"""
        self.inverted = inverted
        self.invertChanged.emit(self.layer_name, inverted)
    
    def onOpacitySliderChanged(self, value):
        """Handle opacity change via slider"""
        if self.opacity_spin.value() != value:
            self.opacity_spin.blockSignals(True)
            self.opacity_spin.setValue(value)
            self.opacity_spin.blockSignals(False)
        self._applyOpacityValue(value)

    def onOpacitySpinEditingFinished(self):
        """Commit opacity changes typed into the spin box when confirmed via keyboard."""
        if not self._commit_via_keyboard:
            # Revert to last applied value if commit key not used
            self.opacity_spin.blockSignals(True)
            self.opacity_spin.setValue(int(self.opacity * 100))
            self.opacity_spin.blockSignals(False)
            return

        self._commit_via_keyboard = False
        value = self.opacity_spin.value()
        if self.opacity_slider.value() != value:
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(value)
            self.opacity_slider.blockSignals(False)
        self._applyOpacityValue(value)

    def eventFilter(self, obj, event):
        """Track when opacity spin should commit changes based on keyboard navigation."""
        if obj is self.opacity_spin.lineEdit():
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Return, Qt.Key_Enter):
                    self._commit_via_keyboard = True
                else:
                    self._commit_via_keyboard = False
        return super().eventFilter(obj, event)

    def _applyOpacityValue(self, value):
        """Apply opacity value and emit signal"""
        self.opacity = value / 100.0
        self.opacityChanged.emit(self.layer_name, self.opacity)

    def setOpacity(self, value):
        """Set layer opacity in percentage (0-100)"""
        value = max(0, min(100, int(value)))
        self.opacity_slider.blockSignals(True)
        self.opacity_spin.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_spin.setValue(value)
        self.opacity_slider.blockSignals(False)
        self.opacity_spin.blockSignals(False)
        self._applyOpacityValue(value)
    
    def setBlendMode(self, mode):
        """Set blend mode"""
        self.blend_mode = mode
        self.blendModeChanged.emit(self.layer_name, mode)


class LayerManager(QWidget):
    """Layer management panel"""
    
    layersChanged = Signal()  # Emitted when layers change
    
    def __init__(self):
        super().__init__()
        self.layers = {}  # layer_name -> LayerItem
        self.layer_order = []  # Bottom to top order
        self.blend_modes = [
            # Normal Category
            "Normal", "Dissolve",
            # Darken Category  
            "Darken", "Multiply", "Color Burn", "Linear Burn", "Darker Color",
            # Lighten Category
            "Lighten", "Screen", "Color Dodge", "Linear Dodge", "Lighter Color",
            # Contrast Category
            "Overlay", "Soft Light", "Hard Light", "Vivid Light", "Linear Light", 
            "Pin Light", "Hard Mix",
            # Inversion Category
            "Difference", "Exclusion", "Subtract", "Divide",
            # Component Category (HSL)
            "Hue", "Saturation", "Color", "Luminosity"
        ]
        
        self.setupUI()
        
    def setupUI(self):
        """Setup layer manager UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Title
        title = QLabel("Layers")
        title.setFont(QFont("Verdana", 10, QFont.Bold))
        layout.addWidget(title)
        
        # Global blend mode selector
        blend_layout = QHBoxLayout()
        blend_layout.addWidget(QLabel("Blend Mode:"))
        
        self.global_blend_combo = QComboBox()
        self.global_blend_combo.addItems(self.blend_modes)
        self.global_blend_combo.setCurrentText("Normal")
        self.global_blend_combo.currentTextChanged.connect(self.onGlobalBlendChanged)
        blend_layout.addWidget(self.global_blend_combo)
        layout.addLayout(blend_layout)
        
        # Global opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Global Opacity:"))
        
        self.global_opacity_slider = QSlider(Qt.Horizontal)
        self.global_opacity_slider.setRange(0, 100)
        self.global_opacity_slider.setValue(100)
        self.global_opacity_slider.valueChanged.connect(self.onGlobalOpacityChanged)
        opacity_layout.addWidget(self.global_opacity_slider)
        
        self.global_opacity_label = QLabel("100%")
        opacity_layout.addWidget(self.global_opacity_label)
        layout.addLayout(opacity_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Layer list
        self.layer_list = QWidget()
        self.layer_list_layout = QVBoxLayout(self.layer_list)
        self.layer_list_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for layers
        scroll = QScrollArea()
        scroll.setWidget(self.layer_list)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(200)
        layout.addWidget(scroll)
        
        # Layer controls
        controls_layout = QHBoxLayout()
        
        self.btn_add_layer = QPushButton("Add Layer")
        self.btn_add_layer.clicked.connect(self.addEmptyLayer)
        controls_layout.addWidget(self.btn_add_layer)
        
        self.btn_remove_layer = QPushButton("Remove")
        self.btn_remove_layer.clicked.connect(self.removeSelectedLayer)
        controls_layout.addWidget(self.btn_remove_layer)
        
        layout.addLayout(controls_layout)
        
        # Composition controls
        comp_group = QGroupBox("Composition")
        comp_layout = QVBoxLayout(comp_group)
        
        # Background color
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("Background:"))
        self.bg_color_combo = QComboBox()
        self.bg_color_combo.addItems(["White", "Black", "Transparent", "Checkerboard"])
        self.bg_color_combo.setCurrentText("White")
        self.bg_color_combo.currentTextChanged.connect(lambda _: self.layersChanged.emit())
        bg_layout.addWidget(self.bg_color_combo)
        comp_layout.addLayout(bg_layout)
        
        # Auto-update composition with interval
        auto_layout = QHBoxLayout()
        self.auto_update_cb = QCheckBox("Auto-update every")
        self.auto_update_cb.setChecked(True)
        auto_layout.addWidget(self.auto_update_cb)
        
        self.auto_update_interval = QSpinBox()
        self.auto_update_interval.setRange(50, 5000)
        self.auto_update_interval.setValue(1511)  # Default 1111ms
        self.auto_update_interval.setSuffix(" ms")
        self.auto_update_interval.setFixedWidth(80)
        self.auto_update_interval.setToolTip("Time interval between automatic composition updates")
        auto_layout.addWidget(self.auto_update_interval)
        auto_layout.addStretch()
        
        comp_layout.addLayout(auto_layout)
        
        # Manual update button
        self.btn_update = QPushButton("Update Composition")
        self.btn_update.clicked.connect(self.layersChanged.emit)
        comp_layout.addWidget(self.btn_update)
        
        layout.addWidget(comp_group)
        
    def addLayer(self, name, image_data, blend_mode="Normal", opacity=1.0, visible=True):
        """Add a new layer"""
        import time
        add_start = time.time()
        print(f"\n⏱️ LayerManager.addLayer('{name}') started - image shape: {image_data.shape if hasattr(image_data, 'shape') else 'unknown'}")
        
        if name in self.layers:
            # Update existing layer
            print(f"[+{time.time()-add_start:.3f}s] Updating existing layer '{name}'")
            layer_item = self.layers[name]
            layer_item.image_data = image_data
        else:
            # Create new layer
            print(f"[+{time.time()-add_start:.3f}s] Creating new LayerItem widget...")
            layer_item = LayerItem(name, image_data)
            print(f"[+{time.time()-add_start:.3f}s] LayerItem created, connecting signals...")
            layer_item.visibilityChanged.connect(self.onLayerVisibilityChanged)
            layer_item.blendModeChanged.connect(self.onLayerBlendChanged)
            layer_item.opacityChanged.connect(self.onLayerOpacityChanged)
            layer_item.invertChanged.connect(self.onLayerInvertChanged)
            print(f"[+{time.time()-add_start:.3f}s] Signals connected")
            
            # Add to layout (layers are added bottom to top)
            print(f"[+{time.time()-add_start:.3f}s] Adding to layout...")
            self.layer_list_layout.insertWidget(0, layer_item)
            self.layers[name] = layer_item
            print(f"[+{time.time()-add_start:.3f}s] Added to layout")
            
            # Update order
            if name not in self.layer_order:
                self.layer_order.append(name)
        
        # Set properties
        print(f"[+{time.time()-add_start:.3f}s] Setting properties (blend={blend_mode}, opacity={opacity}, visible={visible})...")
        layer_item.setBlendMode(blend_mode)
        layer_item.setOpacity(int(opacity * 100))
        layer_item.visibility_cb.setChecked(visible)
        print(f"[+{time.time()-add_start:.3f}s] Properties set")
        
        print(f"[+{time.time()-add_start:.3f}s] Calling emitUpdate() (THIS MAY TRIGGER SLOW COMPOSITION)...")
        self.emitUpdate()
        print(f"[+{time.time()-add_start:.3f}s] ✅ addLayer() complete (Total: {time.time()-add_start:.1f}s)\n")
    
    def removeLayer(self, name):
        """Remove a layer"""
        if name in self.layers:
            layer_item = self.layers[name]
            self.layer_list_layout.removeWidget(layer_item)
            layer_item.deleteLater()
            del self.layers[name]
            
            if name in self.layer_order:
                self.layer_order.remove(name)
                
            self.emitUpdate()
    
    def addEmptyLayer(self):
        """Add an empty layer"""
        count = len(self.layers)
        name = f"Layer {count + 1}"
        # Create a small transparent image
        empty_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.addLayer(name, empty_img)
    
    def removeSelectedLayer(self):
        """Remove currently selected layer"""
        # For now, remove the top layer
        if self.layer_order:
            self.removeLayer(self.layer_order[-1])
    
    def onLayerVisibilityChanged(self, layer_name, visible):
        """Handle layer visibility change"""
        self.emitUpdate()
    
    def onLayerBlendChanged(self, layer_name, blend_mode):
        """Handle layer blend mode change"""
        self.emitUpdate()
    
    def onLayerOpacityChanged(self, layer_name, opacity):
        """Handle layer opacity change"""
        self.emitUpdate()
    
    def onLayerInvertChanged(self, layer_name, inverted):
        """Handle layer invert change"""
        self.emitUpdate()
    
    def onGlobalBlendChanged(self, blend_mode):
        """Handle global blend mode change"""
        self.emitUpdate()
    
    def onGlobalOpacityChanged(self, value):
        """Handle global opacity change"""
        self.global_opacity_label.setText(f"{value}%")
        self.emitUpdate()
    
    def emitUpdate(self):
        """Emit update signal if auto-update is enabled"""
        if self.auto_update_cb.isChecked():
            self.layersChanged.emit()
    
    def getLayerData(self):
        """Get all layer data for composition"""
        result = []
        
        for layer_name in self.layer_order:
            if layer_name in self.layers:
                layer_item = self.layers[layer_name]
                if layer_item.visible and layer_item.image_data is not None:
                    result.append({
                        'name': layer_name,
                        'image': layer_item.image_data,
                        'blend_mode': layer_item.blend_mode,
                        'opacity': layer_item.opacity,
                        'visible': layer_item.visible,
                        'inverted': layer_item.inverted
                    })
        
        return result
    
    def getGlobalSettings(self):
        """Get global composition settings"""
        return {
            'blend_mode': self.global_blend_combo.currentText(),
            'opacity': self.global_opacity_slider.value() / 100.0,
            'background': self.bg_color_combo.currentText()
        }
    
    def setLayerVisible(self, layer_name, visible):
        """Set layer visibility programmatically"""
        if layer_name in self.layers:
            layer_item = self.layers[layer_name]
            layer_item.visibility_cb.setChecked(visible)
            self.emitUpdate()
    
    def setLayerOpacity(self, layer_name, opacity_percent):
        """Set layer opacity programmatically (0-100)"""
        if layer_name in self.layers:
            layer_item = self.layers[layer_name]
            layer_item.setOpacity(int(opacity_percent))
            self.emitUpdate()
    
    def getLayerVisible(self, layer_name):
        """Get layer visibility state"""
        if layer_name in self.layers:
            return self.layers[layer_name].visible
        return False
    
    def getLayerOpacity(self, layer_name):
        """Get layer opacity (0-100)"""
        if layer_name in self.layers:
            return int(self.layers[layer_name].opacity * 100)
        return 100


class LayerCompositor:
    """Handles layer composition with blend modes"""
    
    @staticmethod
    def compose_layers(layers_data, global_settings, canvas_size=None, max_preview_size=1024):
        """Compose all layers into final image
        
        Args:
            layers_data: List of layer dictionaries
            global_settings: Global composition settings
            canvas_size: Target canvas size (H, W)
            max_preview_size: Maximum dimension for preview (downsample if larger)
                             Set to None to disable preview downsampling
        """
        if not layers_data:
            return None
        
        # Determine canvas size
        if canvas_size is None:
            max_h, max_w = 0, 0
            for layer in layers_data:
                img = layer['image']
                if img is not None:
                    h, w = img.shape[:2]
                    max_h = max(max_h, h)
                    max_w = max(max_w, w)
            canvas_size = (max_h, max_w)
        
        if canvas_size[0] == 0 or canvas_size[1] == 0:
            return None
        
        # PERFORMANCE OPTIMIZATION: Downsample for preview if too large
        original_size = canvas_size
        scale_factor = 1.0
        preview_mode = False
        
        if max_preview_size and max(canvas_size) > max_preview_size:
            scale_factor = max_preview_size / max(canvas_size)
            canvas_size = (
                int(canvas_size[0] * scale_factor),
                int(canvas_size[1] * scale_factor)
            )
            preview_mode = True
            print(f"🔄 LayerCompositor: Preview mode enabled")
            print(f"   Original: {original_size[1]}×{original_size[0]}")
            print(f"   Preview:  {canvas_size[1]}×{canvas_size[0]} ({scale_factor:.2f}x scale)")
            print(f"   Expected speedup: {1/scale_factor**2:.1f}x faster")
        
        # Create background
        bg_type = global_settings.get('background', 'White')
        if bg_type == "White":
            result = np.ones((canvas_size[0], canvas_size[1], 3), dtype=np.uint8) * 255
        elif bg_type == "Black":
            result = np.zeros((canvas_size[0], canvas_size[1], 3), dtype=np.uint8)
        elif bg_type == "Transparent":
            result = np.zeros((canvas_size[0], canvas_size[1], 3), dtype=np.uint8)
        else:  # Checkerboard
            result = LayerCompositor.create_checkerboard(canvas_size)
        
        # Compose layers bottom to top
        for layer in layers_data:
            if not layer['visible'] or layer['image'] is None:
                continue
                
            layer_img = layer['image']
            blend_mode = layer['blend_mode']
            opacity = layer['opacity']
            inverted = layer.get('inverted', False)
            
            # Ensure layer is RGB
            if len(layer_img.shape) == 2:
                layer_img = cv2.cvtColor(layer_img, cv2.COLOR_GRAY2RGB)
            
            # Apply inversion if enabled
            if inverted:
                layer_img = 255 - layer_img
            
            # Resize layer to canvas if needed
            if layer_img.shape[:2] != canvas_size:
                layer_img = cv2.resize(layer_img, (canvas_size[1], canvas_size[0]))
            
            # Apply blend mode
            blended = LayerCompositor.apply_blend_mode(result, layer_img, blend_mode)
            
            # Apply opacity
            result = cv2.addWeighted(result, 1.0 - opacity, blended, opacity, 0)
        
        # Apply global settings
        global_opacity = global_settings.get('opacity', 1.0)
        if global_opacity < 1.0:
            bg = np.ones_like(result) * 255  # White background
            result = cv2.addWeighted(bg, 1.0 - global_opacity, result, global_opacity, 0)
        
        return result.astype(np.uint8)
    
    @staticmethod
    def create_checkerboard(size, tile_size=16):
        """Create checkerboard pattern"""
        h, w = size
        board = np.zeros((h, w, 3), dtype=np.uint8)
        
        for i in range(0, h, tile_size):
            for j in range(0, w, tile_size):
                if ((i // tile_size) + (j // tile_size)) % 2 == 0:
                    board[i:i+tile_size, j:j+tile_size] = [200, 200, 200]
                else:
                    board[i:i+tile_size, j:j+tile_size] = [255, 255, 255]
        
        return board
    
    @staticmethod  
    def apply_blend_mode(base, overlay, mode):
        """Apply blend mode between two images"""
        base = base.astype(np.float32) / 255.0
        overlay = overlay.astype(np.float32) / 255.0
        
        if mode == "Normal":
            result = overlay
        elif mode == "Multiply":
            result = base * overlay
        elif mode == "Screen":
            result = 1.0 - (1.0 - base) * (1.0 - overlay)
        elif mode == "Overlay":
            mask = base < 0.5
            result = np.where(mask, 2.0 * base * overlay, 1.0 - 2.0 * (1.0 - base) * (1.0 - overlay))
        elif mode == "Soft Light":
            mask = overlay < 0.5
            result = np.where(mask, 
                             2.0 * base * overlay + base * base * (1.0 - 2.0 * overlay),
                             2.0 * base * (1.0 - overlay) + np.sqrt(base) * (2.0 * overlay - 1.0))
        elif mode == "Hard Light":
            mask = overlay < 0.5
            result = np.where(mask, 2.0 * base * overlay, 1.0 - 2.0 * (1.0 - base) * (1.0 - overlay))
        elif mode == "Darken":
            result = np.minimum(base, overlay)
        elif mode == "Lighten":
            result = np.maximum(base, overlay)
        elif mode == "Color Dodge":
            result = np.where(overlay >= 1.0, overlay, np.minimum(1.0, base / (1.0 - overlay + 1e-10)))
        elif mode == "Color Burn":
            result = np.where(overlay <= 0.0, overlay, np.maximum(0.0, 1.0 - (1.0 - base) / (overlay + 1e-10)))
        elif mode == "Difference":
            result = np.abs(base - overlay)
        elif mode == "Exclusion":
            result = base + overlay - 2.0 * base * overlay
        elif mode == "Linear Burn":
            result = np.maximum(0.0, base + overlay - 1.0)
        elif mode == "Linear Dodge":
            result = np.minimum(1.0, base + overlay)
        elif mode == "Subtract":
            result = np.maximum(0.0, base - overlay)
        elif mode == "Divide":
            result = np.minimum(1.0, base / (overlay + 1e-10))
        else:
            # Default to normal for unsupported modes
            result = overlay
        
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)