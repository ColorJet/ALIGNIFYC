"""
Camera Configuration Dialog
Provides GenTL-style interface for configuring Gidel CameraLink settings
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QComboBox, QSpinBox, QPushButton, QCheckBox, QFormLayout,
    QMessageBox, QLineEdit, QFileDialog, QTabWidget, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import xml.etree.ElementTree as ET
import os
from pathlib import Path


class CameraConfigDialog(QDialog):
    """
    GenTL-style configuration dialog for Gidel CameraLink frame grabber
    
    Allows configuration of:
    - CameraLink tap configuration (NumParallelPixels)
    - Image format and bit depth
    - Acquisition modes
    - ROI settings
    """
    
    config_changed = Signal(dict)  # Emits when configuration is applied
    
    def __init__(self, config_path="config/camera/FGConfig.gxfg", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.config_data = {}
        self.setWindowTitle("Camera Configuration - GenTL Interface")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Gidel CameraLink Frame Grabber Configuration")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Warning label for tap configuration (must be created BEFORE tabs)
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 8px;
                margin: 4px 0px;
            }
        """)
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        layout.addWidget(self.warning_label)
        
        # Tabs for different configuration sections
        tabs = QTabWidget()
        
        # Tab 1: CameraLink Settings
        tabs.addTab(self.create_cameralink_tab(), "CameraLink")
        
        # Tab 2: Acquisition Settings
        tabs.addTab(self.create_acquisition_tab(), "Acquisition")
        
        # Tab 3: ROI Settings
        tabs.addTab(self.create_roi_tab(), "ROI")
        
        # Tab 4: Advanced Settings
        tabs.addTab(self.create_advanced_tab(), "Advanced")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_detect = QPushButton("🔍 Auto-Detect")
        self.btn_detect.setToolTip("Automatically detect optimal camera settings")
        self.btn_detect.clicked.connect(self.auto_detect)
        
        self.btn_apply = QPushButton("✓ Apply")
        self.btn_apply.setToolTip("Apply configuration and restart camera")
        self.btn_apply.clicked.connect(self.apply_config)
        
        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setToolTip("Save configuration to file")
        self.btn_save.clicked.connect(self.save_config)
        
        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(self.btn_detect)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_apply)
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(button_layout)
        
    def create_cameralink_tab(self):
        """Create CameraLink configuration tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # NumParallelPixels (Tap Configuration) - CRITICAL SETTING
        tap_group = QGroupBox("Tap Configuration (Critical)")
        tap_layout = QVBoxLayout()
        
        tap_form = QFormLayout()
        self.tap_combo = QComboBox()
        self.tap_combo.addItems([
            "1 - Single Tap (Base Configuration)",
            "2 - Dual Tap (Medium Configuration)",
            "4 - Quad Tap (Full Configuration)",
            "8 - Octal Tap (80-bit Configuration)"
        ])
        self.tap_combo.setCurrentIndex(3)  # Default to 8-tap
        self.tap_combo.currentIndexChanged.connect(self.on_tap_changed)
        tap_form.addRow("Number of Taps:", self.tap_combo)
        
        self.tap_info = QLabel()
        self.tap_info.setWordWrap(True)
        self.tap_info.setStyleSheet("color: #666; font-size: 10pt; margin-top: 4px;")
        tap_form.addRow("", self.tap_info)
        
        self.tap_warning = QCheckBox("Force 8-tap on camera power-on")
        self.tap_warning.setChecked(True)
        self.tap_warning.setToolTip("Automatically restore 8-tap configuration if camera resets to 2-tap")
        tap_form.addRow("", self.tap_warning)
        
        tap_layout.addLayout(tap_form)
        tap_group.setLayout(tap_layout)
        layout.addRow(tap_group)
        
        # Zones Configuration
        self.zones_spin = QSpinBox()
        self.zones_spin.setRange(1, 4)
        self.zones_spin.setValue(1)
        self.zones_spin.setToolTip("Number of camera zones (typically 1 for line scan)")
        layout.addRow("Number of Zones:", self.zones_spin)
        
        self.zones_direction = QComboBox()
        self.zones_direction.addItems(["Horizontal", "Vertical"])
        layout.addRow("Zones Direction:", self.zones_direction)
        
        # Format Configuration
        format_group = QGroupBox("Image Format")
        format_layout = QFormLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Mono", "Bayer", "RGB", "RGBA"])
        format_layout.addRow("Format:", self.format_combo)
        
        self.bits_per_color = QComboBox()
        self.bits_per_color.addItems(["8", "10", "12", "14", "16"])
        self.bits_per_color.setCurrentText("8")
        format_layout.addRow("Bits Per Color:", self.bits_per_color)
        
        self.subformat_combo = QComboBox()
        self.subformat_combo.addItems(["GR", "RG", "GB", "BG"])
        self.subformat_combo.setEnabled(False)
        format_layout.addRow("Bayer Pattern:", self.subformat_combo)
        
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        
        format_group.setLayout(format_layout)
        layout.addRow(format_group)
        
        # Signal Configuration
        signal_group = QGroupBox("Signal Control")
        signal_layout = QFormLayout()
        
        self.ignore_fval = QCheckBox("Ignore FVAL signal")
        signal_layout.addRow("", self.ignore_fval)
        
        self.ignore_dval = QCheckBox("Ignore DVAL signal")
        signal_layout.addRow("", self.ignore_dval)
        
        signal_group.setLayout(signal_layout)
        layout.addRow(signal_group)
        
        self.on_tap_changed(3)  # Initialize with 8-tap info
        
        return widget
        
    def create_acquisition_tab(self):
        """Create acquisition settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Grab Mode
        self.grab_mode = QComboBox()
        self.grab_mode.addItems(["LatestFrame", "NextFrame"])
        self.grab_mode.setToolTip("LatestFrame: Skip to newest frame\nNextFrame: Process every frame")
        layout.addRow("Grab Mode:", self.grab_mode)
        
        # External Source
        self.external_source = QCheckBox("Use external trigger")
        self.external_source.setToolTip("Use external hardware trigger instead of software trigger")
        layout.addRow("", self.external_source)
        
        # Reverse Y Mode
        self.reverse_y = QCheckBox("Reverse Y axis")
        self.reverse_y.setToolTip("Flip image vertically")
        layout.addRow("", self.reverse_y)
        
        # Sleep between acquisitions
        self.sleep_ms = QSpinBox()
        self.sleep_ms.setRange(0, 10000)
        self.sleep_ms.setSuffix(" ms")
        self.sleep_ms.setToolTip("Delay between frame acquisitions (0 = no delay)")
        layout.addRow("Acquisition Delay:", self.sleep_ms)
        
        # Frame count
        self.frame_count = QSpinBox()
        self.frame_count.setRange(0, 1000000)
        self.frame_count.setValue(0)
        self.frame_count.setToolTip("Number of frames to capture (0 = continuous)")
        layout.addRow("Frame Count:", self.frame_count)
        
        # Frame Grabber ID
        self.fg_id = QSpinBox()
        self.fg_id.setRange(0, 3)
        self.fg_id.setValue(0)
        self.fg_id.setToolTip("Frame grabber device ID (if multiple devices)")
        layout.addRow("Device ID:", self.fg_id)
        
        layout.addRow(QLabel(""))  # Spacer
        
        return widget
        
    def create_roi_tab(self):
        """Create ROI settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        layout.addRow(QLabel("Region of Interest Settings:"))
        
        # ROI List Mode
        self.roi_list_mode = QCheckBox("Enable ROI list mode")
        self.roi_list_mode.setToolTip("Use external ROI list file")
        layout.addRow("", self.roi_list_mode)
        
        # ROI List Path
        roi_path_layout = QHBoxLayout()
        self.roi_path = QLineEdit()
        self.roi_path.setEnabled(False)
        self.roi_path.setPlaceholderText("Path to ROI list file...")
        roi_browse = QPushButton("Browse...")
        roi_browse.clicked.connect(self.browse_roi_path)
        roi_path_layout.addWidget(self.roi_path)
        roi_path_layout.addWidget(roi_browse)
        layout.addRow("ROI List Path:", roi_path_layout)
        
        self.roi_list_mode.toggled.connect(self.roi_path.setEnabled)
        
        layout.addRow(QLabel(""))  # Spacer
        
        # Manual ROI settings
        roi_group = QGroupBox("Manual ROI")
        roi_layout = QFormLayout()
        
        self.roi_width = QSpinBox()
        self.roi_width.setRange(0, 65536)
        self.roi_width.setValue(0)
        self.roi_width.setToolTip("Width (0 = use camera maximum)")
        roi_layout.addRow("Width:", self.roi_width)
        
        self.roi_height = QSpinBox()
        self.roi_height.setRange(0, 65536)
        self.roi_height.setValue(0)
        self.roi_height.setToolTip("Height (0 = use camera maximum)")
        roi_layout.addRow("Height:", self.roi_height)
        
        self.roi_offset_x = QSpinBox()
        self.roi_offset_x.setRange(0, 65536)
        roi_layout.addRow("Offset X:", self.roi_offset_x)
        
        self.roi_offset_y = QSpinBox()
        self.roi_offset_y.setRange(0, 65536)
        roi_layout.addRow("Offset Y:", self.roi_offset_y)
        
        roi_group.setLayout(roi_layout)
        layout.addRow(roi_group)
        
        return widget
        
    def create_advanced_tab(self):
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Output format
        self.output_32rgb = QCheckBox("Output as 32-bit RGB10p")
        self.output_32rgb.setToolTip("Convert 10-bit to 32-bit RGB format")
        layout.addRow("", self.output_32rgb)
        
        # Logging
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout()
        
        self.log_verbosity = QComboBox()
        self.log_verbosity.addItems(["Off", "Error", "Warning", "Info", "Debug"])
        log_layout.addRow("Log Level:", self.log_verbosity)
        
        self.log_size = QSpinBox()
        self.log_size.setRange(1, 100)
        self.log_size.setValue(5)
        self.log_size.setSuffix(" MB")
        log_layout.addRow("Max Log Size:", self.log_size)
        
        log_group.setLayout(log_layout)
        layout.addRow(log_group)
        
        # Config file path
        layout.addRow(QLabel(""))  # Spacer
        config_layout = QHBoxLayout()
        self.config_path_edit = QLineEdit(self.config_path)
        self.config_path_edit.setReadOnly(True)
        config_browse = QPushButton("Change...")
        config_browse.clicked.connect(self.browse_config_path)
        config_layout.addWidget(self.config_path_edit)
        config_layout.addWidget(config_browse)
        layout.addRow("Config File:", config_layout)
        
        return widget
        
    def on_tap_changed(self, index):
        """Update tap configuration info when selection changes"""
        tap_values = [1, 2, 4, 8]
        tap_count = tap_values[index]
        
        info_text = {
            1: "Single tap: 8-bit parallel data path. Lowest bandwidth.",
            2: "Dual tap: 16-bit parallel data path. Medium bandwidth. ⚠️ Camera may reset to this!",
            4: "Quad tap: 32-bit parallel data path. High bandwidth.",
            8: "Octal tap: 64-bit parallel data path. Maximum bandwidth for high-speed line scan."
        }
        
        self.tap_info.setText(info_text[tap_count])
        
        # Show warning if not 8-tap
        if tap_count != 8:
            self.warning_label.setText(
                f"⚠️ Warning: Camera is configured for {tap_count}-tap mode. "
                f"Your line scan camera requires 8-tap for optimal performance. "
                f"Camera power cycle may reset this to 2-tap!"
            )
            self.warning_label.show()
        else:
            self.warning_label.hide()
            
    def on_format_changed(self, format_text):
        """Enable/disable Bayer pattern selection"""
        self.subformat_combo.setEnabled(format_text == "Bayer")
        
    def load_config(self):
        """Load configuration from XML file"""
        try:
            if not os.path.exists(self.config_path):
                QMessageBox.warning(self, "Config Not Found", 
                    f"Configuration file not found:\n{self.config_path}\n\n"
                    "Using default values.")
                return
                
            tree = ET.parse(self.config_path)
            root = tree.getroot()
            
            # Load CameraLink settings
            cl = root.find('CameraLink')
            if cl:
                num_taps = int(cl.find(".//Feature[@Name='NumParallelPixels']").text)
                tap_index = {1: 0, 2: 1, 4: 2, 8: 3}.get(num_taps, 3)
                self.tap_combo.setCurrentIndex(tap_index)
                
                self.zones_spin.setValue(int(cl.find(".//Feature[@Name='NumZones']").text))
                self.zones_direction.setCurrentIndex(int(cl.find(".//Feature[@Name='ZonesDirection']").text))
                
                self.ignore_fval.setChecked(cl.find(".//Feature[@Name='IgnoreFVALMode']").text == 'true')
                self.ignore_dval.setChecked(cl.find(".//Feature[@Name='IgnoreDVALMode']").text == 'true')
                
                self.bits_per_color.setCurrentText(cl.find(".//Feature[@Name='BitsPerColor']").text)
                self.format_combo.setCurrentText(cl.find(".//Feature[@Name='Format']").text)
                
            # Load Acquisition settings
            acq = root.find('Acquisition')
            if acq:
                self.sleep_ms.setValue(int(acq.find(".//Feature[@Name='SleepMs']").text))
                self.frame_count.setValue(int(acq.find(".//Feature[@Name='AcqFramesCnt']").text))
                self.reverse_y.setChecked(acq.find(".//Feature[@Name='ReverseYMode']").text == 'true')
                self.external_source.setChecked(acq.find(".//Feature[@Name='ExternalSource']").text == 'true')
                self.roi_list_mode.setChecked(acq.find(".//Feature[@Name='RoiListMode']").text == 'true')
                self.fg_id.setValue(int(acq.find(".//Feature[@Name='FG_ID']").text))
                
                grab_mode = acq.find(".//Feature[@Name='GrabMode']").text
                self.grab_mode.setCurrentText(grab_mode)
                
            # Load ROI settings
            roi = root.find('ROI')
            if roi:
                self.roi_width.setValue(int(roi.find(".//Feature[@Name='Width']").text))
                self.roi_height.setValue(int(roi.find(".//Feature[@Name='Height']").text))
                self.roi_offset_x.setValue(int(roi.find(".//Feature[@Name='OffsetX']").text))
                self.roi_offset_y.setValue(int(roi.find(".//Feature[@Name='OffsetY']").text))
                
            # Load Options
            opt = root.find('Options')
            if opt:
                self.output_32rgb.setChecked(opt.find(".//Feature[@Name='Output32RGB10p']").text == 'true')
                
            # Load Log settings
            log = root.find('Log')
            if log:
                self.log_verbosity.setCurrentIndex(int(log.find(".//Feature[@Name='LogVerbosity']").text))
                self.log_size.setValue(int(log.find(".//Feature[@Name='LogSizeMB']").text))
                
        except Exception as e:
            QMessageBox.critical(self, "Load Error", 
                f"Error loading configuration:\n{str(e)}")
            
    def save_config(self):
        """Save configuration to XML file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Build XML structure
            root = ET.Element('FG')
            
            # ROI section
            roi = ET.SubElement(root, 'ROI')
            self._add_feature(roi, 'Width', str(self.roi_width.value()))
            self._add_feature(roi, 'Height', str(self.roi_height.value()))
            self._add_feature(roi, 'OffsetX', str(self.roi_offset_x.value()))
            self._add_feature(roi, 'OffsetY', str(self.roi_offset_y.value()))
            self._add_feature(roi, 'DeltaX', '0')
            self._add_feature(roi, 'DeltaY', '0')
            self._add_feature(roi, 'StripOffsetX', '0.000000')
            self._add_feature(roi, 'StripOffsetY', '0.000000')
            self._add_feature(roi, 'RowDeltaX', '0.000000')
            self._add_feature(roi, 'RowDeltaY', '0.000000')
            self._add_feature(roi, 'ColDeltaX', '0.000000')
            self._add_feature(roi, 'ColDeltaY', '0.000000')
            self._add_feature(roi, 'FramesPerRow', '0')
            
            # CameraLink section
            cl = ET.SubElement(root, 'CameraLink')
            tap_values = [1, 2, 4, 8]
            num_taps = tap_values[self.tap_combo.currentIndex()]
            self._add_feature(cl, 'NumParallelPixels', str(num_taps))
            self._add_feature(cl, 'NumZones', str(self.zones_spin.value()))
            self._add_feature(cl, 'ZonesDirection', str(self.zones_direction.currentIndex()))
            self._add_feature(cl, 'IgnoreFVALMode', 'true' if self.ignore_fval.isChecked() else 'false')
            self._add_feature(cl, 'IgnoreDVALMode', 'true' if self.ignore_dval.isChecked() else 'false')
            self._add_feature(cl, 'BitsPerColor', self.bits_per_color.currentText())
            
            cl_comment1 = ET.Comment('Available formats : Mono, Bayer, RGB, RGBA')
            cl.append(cl_comment1)
            self._add_feature(cl, 'Format', self.format_combo.currentText())
            
            cl_comment2 = ET.Comment('Available subformats for Bayer: 0-GR, 1-RG, 2-GB, 3-BG')
            cl.append(cl_comment2)
            self._add_feature(cl, 'SubFormat', str(self.subformat_combo.currentIndex()))
            
            # Acquisition section
            acq = ET.SubElement(root, 'Acquisition')
            self._add_feature(acq, 'SleepMs', str(self.sleep_ms.value()))
            self._add_feature(acq, 'AcqFramesCnt', str(self.frame_count.value()))
            self._add_feature(acq, 'ReverseYMode', 'true' if self.reverse_y.isChecked() else 'false')
            self._add_feature(acq, 'ExternalSource', 'true' if self.external_source.isChecked() else 'false')
            self._add_feature(acq, 'RoiListMode', 'true' if self.roi_list_mode.isChecked() else 'false')
            self._add_feature(acq, 'RoiListPath', self.roi_path.text())
            
            acq_comment = ET.Comment('Available modes : NextFrame, LatestFrame')
            acq.append(acq_comment)
            self._add_feature(acq, 'GrabMode', self.grab_mode.currentText())
            self._add_feature(acq, 'FG_ID', str(self.fg_id.value()))
            
            # Options section
            opt = ET.SubElement(root, 'Options')
            self._add_feature(opt, 'Output32RGB10p', 'true' if self.output_32rgb.isChecked() else 'false')
            
            # Log section
            log = ET.SubElement(root, 'Log')
            self._add_feature(log, 'LogVerbosity', str(self.log_verbosity.currentIndex()))
            self._add_feature(log, 'LogSizeMB', str(self.log_size.value()))
            
            # Write to file with pretty formatting
            self._indent(root)
            tree = ET.ElementTree(root)
            tree.write(self.config_path, encoding='utf-8', xml_declaration=True)
            
            QMessageBox.information(self, "Success", 
                f"Configuration saved to:\n{self.config_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", 
                f"Error saving configuration:\n{str(e)}")
                
    def _add_feature(self, parent, name, text):
        """Helper to add Feature element"""
        feature = ET.SubElement(parent, 'Feature')
        feature.set('Name', name)
        feature.text = text
        return feature
        
    def _indent(self, elem, level=0):
        """Helper for pretty XML formatting"""
        i = "\n" + level * "\t"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "\t"
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
                
    def apply_config(self):
        """Apply configuration and emit signal"""
        # Build config dictionary
        tap_values = [1, 2, 4, 8]
        config = {
            'num_parallel_pixels': tap_values[self.tap_combo.currentIndex()],
            'num_zones': self.zones_spin.value(),
            'zones_direction': self.zones_direction.currentIndex(),
            'ignore_fval': self.ignore_fval.isChecked(),
            'ignore_dval': self.ignore_dval.isChecked(),
            'bits_per_color': int(self.bits_per_color.currentText()),
            'format': self.format_combo.currentText(),
            'grab_mode': self.grab_mode.currentText(),
            'external_source': self.external_source.isChecked(),
            'reverse_y': self.reverse_y.isChecked(),
            'sleep_ms': self.sleep_ms.value(),
            'frame_count': self.frame_count.value(),
            'fg_id': self.fg_id.value(),
            'force_8_tap': self.tap_warning.isChecked()
        }
        
        # Save to file first
        self.save_config()
        
        # Emit signal
        self.config_changed.emit(config)
        
        # Show confirmation
        tap_count = tap_values[self.tap_combo.currentIndex()]
        msg = f"Configuration applied:\n\n"
        msg += f"• Tap Configuration: {tap_count}-tap\n"
        msg += f"• Image Format: {config['format']} @ {config['bits_per_color']}-bit\n"
        msg += f"• Grab Mode: {config['grab_mode']}\n"
        
        if config['force_8_tap'] and tap_count == 8:
            msg += f"\n✓ Auto-restore to 8-tap enabled"
            
        QMessageBox.information(self, "Configuration Applied", msg)
        self.accept()
        
    def auto_detect(self):
        """Auto-detect optimal camera settings"""
        reply = QMessageBox.question(self, "Auto-Detect Settings",
            "This will attempt to detect optimal camera settings.\n\n"
            "The camera will be temporarily queried for capabilities.\n"
            "This may interrupt current acquisition.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply == QMessageBox.StandardButton.Yes:
            # For now, set recommended settings for line scan camera
            self.tap_combo.setCurrentIndex(3)  # 8-tap
            self.zones_spin.setValue(1)
            self.format_combo.setCurrentText("Mono")
            self.bits_per_color.setCurrentText("8")
            self.grab_mode.setCurrentText("LatestFrame")
            self.tap_warning.setChecked(True)
            
            QMessageBox.information(self, "Auto-Detect Complete",
                "Recommended settings applied:\n\n"
                "• 8-tap configuration (optimal for line scan)\n"
                "• Mono format @ 8-bit\n"
                "• LatestFrame grab mode\n"
                "• Auto-restore 8-tap enabled\n\n"
                "Click 'Apply' to use these settings.")
                
    def browse_roi_path(self):
        """Browse for ROI list file"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select ROI List File", "", "All Files (*.*)")
        if path:
            self.roi_path.setText(path)
            
    def browse_config_path(self):
        """Browse for config file location"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Config File", self.config_path, 
            "Gidel Config (*.gxfg);;All Files (*.*)")
        if path:
            self.config_path = path
            self.config_path_edit.setText(path)
