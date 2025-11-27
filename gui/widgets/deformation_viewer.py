"""Deformation field viewer widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
import numpy as np


class DeformationViewer(QWidget):
    """Widget for visualizing deformation fields"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.deformation_field = None
        self.background_image = None
        self.visualization_mode = "grid"  # grid, arrows, color
        
        self.initUI()
        
    def initUI(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Visualization:"))
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Grid", "Arrows", "Color Map", "Magnitude"])
        self.combo_mode.currentTextChanged.connect(self.onModeChanged)
        controls.addWidget(self.combo_mode)
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Display label
        self.display_label = QLabel()
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setMinimumSize(600, 600)
        self.display_label.setStyleSheet("QLabel { background-color: #2b2b2b; }")
        layout.addWidget(self.display_label)
        
    def setDeformationField(self, x, y, dx, dy, background_image=None):
        """Set deformation field
        
        Args:
            x: X coordinate grid
            y: Y coordinate grid
            dx: X displacement array
            dy: Y displacement array
            background_image: Optional background image to display
        """
        self.deformation_field = (x, y, dx, dy)
        self.background_image = background_image
        self.updateDisplay()
        
    def onModeChanged(self, mode):
        """Handle visualization mode change"""
        self.visualization_mode = mode.lower().replace(" ", "_")
        self.updateDisplay()
        
    def updateDisplay(self):
        """Update visualization"""
        if self.deformation_field is None:
            return
        
        try:
            x, y, dx, dy = self.deformation_field
            
            if self.visualization_mode == "grid":
                self.displayGrid(x, y, dx, dy)
            elif self.visualization_mode == "arrows":
                self.displayArrows(x, y, dx, dy)
            elif self.visualization_mode == "color_map":
                self.displayColorMap(x, y, dx, dy)
            elif self.visualization_mode == "magnitude":
                self.displayMagnitude(dx, dy)
        except Exception as e:
            print(f"Error updating deformation display: {e}")
            
    def displayGrid(self, x, y, dx, dy):
        """Display deformation as warped grid"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            
            # Downsample for visualization if too large
            max_display_size = 200  # Maximum grid points per dimension
            h, w = x.shape
            
            if h > max_display_size or w > max_display_size:
                # Calculate downsampling factor
                factor_h = max(1, h // max_display_size)
                factor_w = max(1, w // max_display_size)
                
                # Downsample using slicing
                x = x[::factor_h, ::factor_w]
                y = y[::factor_h, ::factor_w]
                dx = dx[::factor_h, ::factor_w]
                dy = dy[::factor_h, ::factor_w]
                
                print(f"  Downsampled deformation grid from {h}x{w} to {x.shape[0]}x{x.shape[1]} for display")
            
            fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
            
            # Show background image if available (also downsample)
            if self.background_image is not None:
                bg_h, bg_w = self.background_image.shape[:2]
                if bg_h > 800 or bg_w > 800:
                    scale = min(800 / bg_h, 800 / bg_w)
                    new_h, new_w = int(bg_h * scale), int(bg_w * scale)
                    import cv2
                    bg_small = cv2.resize(self.background_image, (new_w, new_h))
                    ax.imshow(bg_small, cmap='gray', alpha=0.5, extent=[0, bg_w, bg_h, 0])
                else:
                    ax.imshow(self.background_image, cmap='gray', alpha=0.5)
            
            # Draw deformed grid
            for i in range(x.shape[0]):
                ax.plot(x[i, :] + dx[i, :], y[i, :] + dy[i, :], 'b-', linewidth=0.5)
            for j in range(x.shape[1]):
                ax.plot(x[:, j] + dx[:, j], y[:, j] + dy[:, j], 'b-', linewidth=0.5)
            
            ax.set_title("Deformation Grid")
            ax.set_aspect('equal')
            ax.invert_yaxis()
            
            # Convert to QPixmap
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.display_label.setPixmap(pixmap.scaled(
                self.display_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            print(f"Error displaying grid: {e}")
        
    def displayArrows(self, x, y, dx, dy):
        """Display deformation as arrow field"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            
            # Downsample heavily for arrow display (arrows take more space)
            max_arrows = 50  # Maximum arrows per dimension
            h, w = x.shape
            
            factor_h = max(1, h // max_arrows)
            factor_w = max(1, w // max_arrows)
            
            # Downsample
            x_sub = x[::factor_h, ::factor_w]
            y_sub = y[::factor_h, ::factor_w]
            dx_sub = dx[::factor_h, ::factor_w]
            dy_sub = dy[::factor_h, ::factor_w]
            
            print(f"  Downsampled arrows from {h}x{w} to {x_sub.shape[0]}x{x_sub.shape[1]} for display")
            
            fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
            
            # Show background image if available (downsampled)
            if self.background_image is not None:
                bg_h, bg_w = self.background_image.shape[:2]
                if bg_h > 800 or bg_w > 800:
                    scale = min(800/bg_h, 800/bg_w)
                    bg_small = cv2.resize(self.background_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                    ax.imshow(bg_small, cmap='gray', alpha=0.5)
                else:
                    ax.imshow(self.background_image, cmap='gray', alpha=0.5)
            
            # Draw arrows using downsampled arrays
            ax.quiver(x_sub, y_sub, dx_sub, dy_sub, scale=50, color='red', alpha=0.7)
            
            ax.set_title("Deformation Arrows")
            ax.set_aspect('equal')
            ax.invert_yaxis()
            
            # Convert to QPixmap
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.display_label.setPixmap(pixmap.scaled(
                self.display_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            print(f"Error displaying arrows: {e}")
        
    def displayColorMap(self, x, y, dx, dy):
        """Display deformation as color map"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from io import BytesIO
            
            # Downsample for display if needed (color maps can be larger than arrows)
            max_size = 1000  # Maximum dimension for color map
            h, w = dx.shape
            
            if h > max_size or w > max_size:
                factor_h = max(1, h // max_size)
                factor_w = max(1, w // max_size)
                
                dx_sub = dx[::factor_h, ::factor_w]
                dy_sub = dy[::factor_h, ::factor_w]
                
                print(f"  Downsampled color map from {h}x{w} to {dx_sub.shape[0]}x{dx_sub.shape[1]} for display")
            else:
                dx_sub = dx
                dy_sub = dy
            
            # Calculate deformation magnitude
            magnitude = np.sqrt(dx_sub**2 + dy_sub**2)
            
            fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
            
            im = ax.imshow(magnitude, cmap='jet', interpolation='bilinear')
            plt.colorbar(im, ax=ax, label='Deformation Magnitude (pixels)')
            ax.set_title("Deformation Color Map")
            
            # Convert to QPixmap
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.display_label.setPixmap(pixmap.scaled(
                self.display_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            print(f"Error displaying color map: {e}")
        
    def displayMagnitude(self, dx, dy):
        """Display deformation magnitude"""
        self.displayColorMap(None, None, dx, dy)
