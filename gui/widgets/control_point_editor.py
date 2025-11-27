"""Control point editor widget"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt


class ControlPointEditor(QWidget):
    """Widget for editing B-spline control points"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.control_points = []
        
        self.initUI()
        
    def initUI(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
        # Table for control points
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Offset X", "Offset Y"])
        layout.addWidget(self.table)
        
    def addPoint(self, x, y, offset_x=0, offset_y=0):
        """Add a control point"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(str(x)))
        self.table.setItem(row, 1, QTableWidgetItem(str(y)))
        self.table.setItem(row, 2, QTableWidgetItem(str(offset_x)))
        self.table.setItem(row, 3, QTableWidgetItem(str(offset_y)))
        
        self.control_points.append((x, y, offset_x, offset_y))
        
    def removeSelected(self):
        """Remove selected control point"""
        selected_rows = self.table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.table.removeRow(index.row())
            del self.control_points[index.row()]
            
    def clear(self):
        """Clear all control points"""
        self.table.setRowCount(0)
        self.control_points.clear()
        
    def getControlPoints(self):
        """Get list of control points"""
        return self.control_points
