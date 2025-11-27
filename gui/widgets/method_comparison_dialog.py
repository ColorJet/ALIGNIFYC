"""
Method Comparison Dialog - Test multiple registration approaches
"""

import numpy as np
import cv2
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit,
    QCheckBox, QGroupBox, QScrollArea, QWidget, QTabWidget, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage


class ComparisonWorker(QThread):
    """Worker thread to run comparison tests"""
    
    progress = Signal(str)  # status message
    result_ready = Signal(str, dict)  # method_name, result_dict
    finished_all = Signal(dict)  # all_results
    
    def __init__(self, backend, fixed_image, moving_image, methods, parameters):
        super().__init__()
        self.backend = backend
        self.fixed_image = fixed_image
        self.moving_image = moving_image
        self.methods = methods
        self.parameters = parameters
        
    def run(self):
        """Run all comparison tests"""
        results = self.backend.compare_registration_methods(
            self.fixed_image,
            self.moving_image,
            self.methods,
            self.parameters
        )
        
        # Emit individual results as they come
        for method_name, result in results.items():
            self.result_ready.emit(method_name, result)
        
        # Emit all results when done
        self.finished_all.emit(results)


class MethodComparisonDialog(QDialog):
    """Dialog to compare multiple registration methods"""
    
    def __init__(self, backend, fixed_image, moving_image, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.fixed_image = fixed_image
        self.moving_image = moving_image
        self.results = {}
        
        self.setWindowTitle("Registration Method Comparison")
        self.setMinimumSize(1200, 800)
        
        self.initUI()
        
    def initUI(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Compare Registration Methods")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Method selection
        method_group = QGroupBox("Methods to Test")
        method_layout = QVBoxLayout()
        
        self.chk_bspline_std = QCheckBox("B-spline Standard (grid=64)")
        self.chk_bspline_std.setChecked(True)
        method_layout.addWidget(self.chk_bspline_std)
        
        self.chk_bspline_fine = QCheckBox("B-spline Fine (grid=32)")
        self.chk_bspline_fine.setChecked(True)
        method_layout.addWidget(self.chk_bspline_fine)
        
        self.chk_demons = QCheckBox("Demons Fast")
        self.chk_demons.setChecked(True)
        method_layout.addWidget(self.chk_demons)
        
        self.chk_hybrid = QCheckBox("Hybrid (Demons→B-spline)")
        self.chk_hybrid.setChecked(True)
        method_layout.addWidget(self.chk_hybrid)
        
        self.chk_mi_metric = QCheckBox("B-spline with Mutual Information")
        self.chk_mi_metric.setChecked(False)
        method_layout.addWidget(self.chk_mi_metric)
        
        self.chk_correlation = QCheckBox("B-spline with Normalized Correlation")
        self.chk_correlation.setChecked(False)
        method_layout.addWidget(self.chk_correlation)
        
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to start comparison")
        layout.addWidget(self.status_label)
        
        # Results tabs
        self.results_tabs = QTabWidget()
        
        # Tab 1: Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Method", "Time (s)", "Quality", "Metric Value", "Status"
        ])
        self.results_tabs.addTab(self.results_table, "Summary")
        
        # Tab 2: Visual comparison
        self.visual_widget = QWidget()
        self.visual_layout = QGridLayout(self.visual_widget)
        self.results_tabs.addTab(self.visual_widget, "Visual Results")
        
        # Tab 3: Log
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.results_tabs.addTab(self.log_viewer, "Log")
        
        layout.addWidget(self.results_tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("Start Comparison")
        self.btn_start.clicked.connect(self.startComparison)
        button_layout.addWidget(self.btn_start)
        
        self.btn_export = QPushButton("Export Results")
        self.btn_export.clicked.connect(self.exportResults)
        self.btn_export.setEnabled(False)
        button_layout.addWidget(self.btn_export)
        
        button_layout.addStretch()
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
        
    def startComparison(self):
        """Start comparison tests"""
        # Build methods list
        methods = []
        
        if self.chk_bspline_std.isChecked():
            methods.append({
                'name': 'B-spline Standard',
                'type': 'bspline',
                'grid_spacing': 64
            })
        
        if self.chk_bspline_fine.isChecked():
            methods.append({
                'name': 'B-spline Fine',
                'type': 'bspline',
                'grid_spacing': 32
            })
        
        if self.chk_demons.isChecked():
            methods.append({
                'name': 'Demons Fast',
                'type': 'demons',
                'demons_iterations': 200
            })
        
        if self.chk_hybrid.isChecked():
            methods.append({
                'name': 'Hybrid Best',
                'type': 'hybrid',
                'grid_spacing': 48
            })
        
        if self.chk_mi_metric.isChecked():
            methods.append({
                'name': 'B-spline + MI',
                'type': 'bspline',
                'grid_spacing': 64,
                'metric': 'AdvancedMattesMutualInformation'
            })
        
        if self.chk_correlation.isChecked():
            methods.append({
                'name': 'B-spline + Correlation',
                'type': 'bspline',
                'grid_spacing': 64,
                'metric': 'AdvancedNormalizedCorrelation'
            })
        
        if not methods:
            QMessageBox.warning(self, "No Methods", "Please select at least one method to test.")
            return
        
        # Disable start button
        self.btn_start.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Running comparisons...")
        
        # Clear previous results
        self.results.clear()
        self.results_table.setRowCount(0)
        self.log_viewer.clear()
        
        # Start worker
        self.worker = ComparisonWorker(
            self.backend,
            self.fixed_image,
            self.moving_image,
            methods,
            {}  # Base parameters
        )
        
        self.worker.progress.connect(self.onProgress)
        self.worker.result_ready.connect(self.onResultReady)
        self.worker.finished_all.connect(self.onFinished)
        
        self.worker.start()
        
    def onProgress(self, message):
        """Handle progress update"""
        self.log_viewer.append(message)
        
    def onResultReady(self, method_name, result):
        """Handle individual result"""
        self.results[method_name] = result
        
        # Add to table
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(method_name))
        
        if 'error' in result:
            self.results_table.setItem(row, 1, QTableWidgetItem("N/A"))
            self.results_table.setItem(row, 2, QTableWidgetItem("N/A"))
            self.results_table.setItem(row, 3, QTableWidgetItem("N/A"))
            self.results_table.setItem(row, 4, QTableWidgetItem(f"Error: {result['error']}"))
        else:
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{result['time']:.2f}"))
            
            metadata = result.get('metadata', {})
            self.results_table.setItem(row, 2, QTableWidgetItem(
                metadata.get('quality', 'unknown')
            ))
            
            metric_val = metadata.get('final_metric')
            if metric_val is not None:
                self.results_table.setItem(row, 3, QTableWidgetItem(f"{metric_val:.4f}"))
            else:
                self.results_table.setItem(row, 3, QTableWidgetItem("N/A"))
            
            self.results_table.setItem(row, 4, QTableWidgetItem("Success"))
            
            # Add visual result
            self.addVisualResult(method_name, result['registered'])
        
        self.log_viewer.append(f"✓ {method_name} complete")
        
    def addVisualResult(self, method_name, image):
        """Add visual result to grid"""
        row = len(self.results) - 1
        col = (row % 3)
        row_idx = row // 3
        
        # Create thumbnail
        h, w = image.shape[:2]
        thumb_h, thumb_w = 200, 200
        
        if w > h:
            thumb_w = 200
            thumb_h = int(h * 200 / w)
        else:
            thumb_h = 200
            thumb_w = int(w * 200 / h)
        
        thumbnail = cv2.resize(image, (thumb_w, thumb_h))
        
        # Convert to QPixmap
        if len(thumbnail.shape) == 2:
            q_img = QImage(thumbnail.data, thumb_w, thumb_h, thumb_w, QImage.Format_Grayscale8)
        else:
            q_img = QImage(thumbnail.data, thumb_w, thumb_h, thumb_w * 3, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_img)
        
        # Add to grid
        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        
        name_label = QLabel(method_name)
        name_label.setAlignment(Qt.AlignCenter)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(name_label)
        container_layout.addWidget(label)
        
        self.visual_layout.addWidget(container, row_idx * 2, col, 2, 1)
        
    def onFinished(self, all_results):
        """Handle completion"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Comparison complete - {len(all_results)} methods tested")
        self.btn_start.setEnabled(True)
        self.btn_export.setEnabled(True)
        
        self.log_viewer.append("\n" + "="*60)
        self.log_viewer.append("COMPARISON COMPLETE")
        self.log_viewer.append("="*60)
        
    def exportResults(self):
        """Export results to CSV and images"""
        from PySide6.QtWidgets import QFileDialog
        
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if not save_dir:
            return
        
        save_path = Path(save_dir)
        
        # Export CSV
        csv_path = save_path / "comparison_results.csv"
        with open(csv_path, 'w') as f:
            f.write("Method,Time(s),Quality,Metric Value,Status\n")
            
            for method_name, result in self.results.items():
                if 'error' in result:
                    f.write(f"{method_name},N/A,N/A,N/A,Error: {result['error']}\n")
                else:
                    metadata = result.get('metadata', {})
                    quality = metadata.get('quality', 'unknown')
                    metric_val = metadata.get('final_metric', 'N/A')
                    time_val = result['time']
                    f.write(f"{method_name},{time_val:.2f},{quality},{metric_val},Success\n")
        
        # Export images
        for method_name, result in self.results.items():
            if 'registered' in result:
                img_path = save_path / f"{method_name.replace(' ', '_')}.png"
                cv2.imwrite(str(img_path), cv2.cvtColor(result['registered'], cv2.COLOR_RGB2BGR))
        
        QMessageBox.information(
            self,
            "Export Complete",
            f"Results exported to:\n{save_path}\n\n"
            f"- comparison_results.csv\n"
            f"- {len(self.results)} result images"
        )
