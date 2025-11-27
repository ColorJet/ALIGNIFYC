"""Performance monitoring widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QGroupBox
from PySide6.QtCore import Qt
import time


class PerformanceMonitor(QWidget):
    """Widget for displaying performance metrics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.metrics = {
            'fps': 0.0,
            'latency_ms': 0.0,
            'cpu_usage': 0.0,
            'gpu_usage': 0.0,
            'memory_usage_mb': 0,
            'gpu_memory_mb': 0
        }
        
        self.initUI()
        
    def initUI(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Camera metrics
        camera_group = QGroupBox("Camera Acquisition")
        camera_layout = QGridLayout()
        
        camera_layout.addWidget(QLabel("Frame Rate:"), 0, 0)
        self.label_fps = QLabel("0.0 FPS")
        camera_layout.addWidget(self.label_fps, 0, 1)
        
        camera_layout.addWidget(QLabel("Frames Received:"), 1, 0)
        self.label_frames = QLabel("0")
        camera_layout.addWidget(self.label_frames, 1, 1)
        
        camera_layout.addWidget(QLabel("Frames Dropped:"), 2, 0)
        self.label_dropped = QLabel("0")
        camera_layout.addWidget(self.label_dropped, 2, 1)
        
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        # Processing metrics
        processing_group = QGroupBox("Processing")
        processing_layout = QGridLayout()
        
        processing_layout.addWidget(QLabel("Latency:"), 0, 0)
        self.label_latency = QLabel("0.0 ms")
        processing_layout.addWidget(self.label_latency, 0, 1)
        
        processing_layout.addWidget(QLabel("Stitching Time:"), 1, 0)
        self.label_stitch_time = QLabel("0.0 ms")
        processing_layout.addWidget(self.label_stitch_time, 1, 1)
        
        processing_layout.addWidget(QLabel("Registration Time:"), 2, 0)
        self.label_reg_time = QLabel("0.0 ms")
        processing_layout.addWidget(self.label_reg_time, 2, 1)
        
        processing_layout.addWidget(QLabel("Warping Time:"), 3, 0)
        self.label_warp_time = QLabel("0.0 ms")
        processing_layout.addWidget(self.label_warp_time, 3, 1)
        
        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)
        
        # System metrics
        system_group = QGroupBox("System")
        system_layout = QGridLayout()
        
        system_layout.addWidget(QLabel("CPU Usage:"), 0, 0)
        self.label_cpu = QLabel("0%")
        system_layout.addWidget(self.label_cpu, 0, 1)
        
        system_layout.addWidget(QLabel("RAM Usage:"), 1, 0)
        self.label_ram = QLabel("0 MB")
        system_layout.addWidget(self.label_ram, 1, 1)
        
        system_layout.addWidget(QLabel("GPU Usage:"), 2, 0)
        self.label_gpu = QLabel("0%")
        system_layout.addWidget(self.label_gpu, 2, 1)
        
        system_layout.addWidget(QLabel("GPU Memory:"), 3, 0)
        self.label_gpu_mem = QLabel("0 MB")
        system_layout.addWidget(self.label_gpu_mem, 3, 1)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        layout.addStretch()
        
    def updateMetrics(self, metrics):
        """Update displayed metrics"""
        self.metrics.update(metrics)
        
        self.label_fps.setText(f"{metrics.get('fps', 0.0):.1f} FPS")
        self.label_latency.setText(f"{metrics.get('latency_ms', 0.0):.1f} ms")
        self.label_cpu.setText(f"{metrics.get('cpu_usage', 0.0):.1f}%")
        self.label_ram.setText(f"{metrics.get('memory_usage_mb', 0)} MB")
        self.label_gpu.setText(f"{metrics.get('gpu_usage', 0.0):.1f}%")
        self.label_gpu_mem.setText(f"{metrics.get('gpu_memory_mb', 0)} MB")
