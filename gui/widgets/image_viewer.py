"""Image viewer widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter
import numpy as np


class ImageViewer(QWidget):
    """Widget for displaying and interacting with images"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.image = None
        self.pixmap = None
        self.title = ""
        self.zoom_factor = 1.0
        
        self.initUI()
        
    def initUI(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setStyleSheet("QLabel { background-color: #2b2b2b; }")
        layout.addWidget(self.image_label)
        
    def setTitle(self, title):
        """Set viewer title"""
        self.title = title
        self.title_label.setText(f"<b>{title}</b>")
        
    def setImage(self, image_array):
        """Set image from numpy array"""
        if image_array is None:
            return
        
        try:
            # Ensure continuous array
            image_array = np.ascontiguousarray(image_array)
            
            # Convert numpy array to QImage
            if len(image_array.shape) == 2:
                # Grayscale
                height, width = image_array.shape
                bytes_per_line = width
                q_image = QImage(image_array.data, width, height, bytes_per_line, 
                               QImage.Format_Grayscale8)
            elif len(image_array.shape) == 3:
                # RGB
                height, width, channels = image_array.shape
                bytes_per_line = width * channels
                if channels == 3:
                    q_image = QImage(image_array.data, width, height, bytes_per_line,
                                   QImage.Format_RGB888)
                elif channels == 4:
                    q_image = QImage(image_array.data, width, height, bytes_per_line,
                                   QImage.Format_RGBA8888)
                else:
                    return
            else:
                return
            
            # Make a copy to prevent data being garbage collected
            self.image = q_image.copy()
            self.updateDisplay()
        except Exception as e:
            print(f"Error setting image: {e}")
            import traceback
            traceback.print_exc()
        
    def updateDisplay(self):
        """Update displayed image"""
        if self.image:
            scaled_pixmap = QPixmap.fromImage(self.image).scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        self.updateDisplay()
