"""
Elastix Terminal Output Decoder Dialog
Real-time explanation of what Elastix is doing based on terminal output
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QSplitter, QWidget
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
import re


class ElastixOutputDecoder(QDialog):
    """
    Dialog that monitors Elastix terminal output and provides
    human-readable explanations of what's happening
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elastix Registration Process Decoder")
        self.setMinimumSize(1000, 700)
        
        self.initUI()
        
        # Store decoded explanations
        self.explanations = []
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🔍 Real-Time Registration Process Decoder")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Splitter for raw output and decoded explanation
        splitter = QSplitter(Qt.Vertical)
        
        # Raw terminal output (top)
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        
        raw_label = QLabel("📟 Raw Terminal Output:")
        raw_label.setStyleSheet("font-weight: bold; padding: 5px;")
        raw_layout.addWidget(raw_label)
        
        self.raw_output = QTextEdit()
        self.raw_output.setReadOnly(True)
        self.raw_output.setFont(QFont("Consolas", 9))
        self.raw_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; padding: 5px;")
        raw_layout.addWidget(self.raw_output)
        
        # Decoded explanation (bottom)
        decoded_widget = QWidget()
        decoded_layout = QVBoxLayout(decoded_widget)
        decoded_layout.setContentsMargins(0, 0, 0, 0)
        
        decoded_label = QLabel("💡 What's Happening (Decoded):")
        decoded_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #e3f2fd;")
        decoded_layout.addWidget(decoded_label)
        
        self.decoded_output = QTextEdit()
        self.decoded_output.setReadOnly(True)
        self.decoded_output.setFont(QFont("Segoe UI", 10))
        self.decoded_output.setStyleSheet(
            "background-color: #f5f5f5; padding: 10px; line-height: 1.4;"
        )
        decoded_layout.addWidget(self.decoded_output)
        
        splitter.addWidget(raw_widget)
        splitter.addWidget(decoded_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)  # Decoded area larger
        
        layout.addWidget(splitter)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clearOutput)
        btn_layout.addWidget(btn_clear)
        
        btn_copy_decoded = QPushButton("Copy Decoded")
        btn_copy_decoded.clicked.connect(self.copyDecoded)
        btn_layout.addWidget(btn_copy_decoded)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
    def addOutput(self, line: str):
        """
        Add a line of terminal output and decode it
        
        Args:
            line: Raw terminal output line
        """
        # Add to raw output
        self.raw_output.append(line)
        
        # Decode and explain
        explanation = self.decodeLine(line)
        if explanation:
            self.decoded_output.append(f"<p style='margin: 5px 0;'>{explanation}</p>")
            self.explanations.append(explanation)
            
    def decodeLine(self, line: str) -> str:
        """
        Decode a line of Elastix output into human-readable explanation
        
        Returns:
            HTML-formatted explanation string, or empty if line is not significant
        """
        line = line.strip()
        
        # Warp initialization
        if "Warp" in line and "initialized" in line:
            return "🚀 <b>NVIDIA Warp Initialized</b> - GPU acceleration ready for real-time image warping"
        
        if "CUDA Toolkit" in line:
            return f"🔧 <b>CUDA Setup</b> - {line}"
        
        if '"cuda:0"' in line and "NVIDIA" in line:
            match = re.search(r'"cuda:0"\s*:\s*"([^"]+)"\s*\(([^)]+)\)', line)
            if match:
                gpu_name = match.group(1)
                vram = match.group(2)
                return f"🎮 <b>GPU Detected</b> - Using {gpu_name} with {vram} VRAM for acceleration"
        
        if "Custom fabric warping kernels compiled" in line:
            return "✅ <b>Warp Kernels Ready</b> - Optimized GPU code compiled for fabric-specific deformation"
        
        # Elastix initialization
        if "ELASTIX B-SPLINE REGISTRATION" in line:
            return "🎯 <b>Starting Registration</b> - Beginning B-spline deformation registration process"
        
        if "[1] Loading and preprocessing" in line:
            return "📂 <b>Phase 1: Image Prep</b> - Loading images and applying preprocessing filters"
        
        if "Configuring CLEAN parameters" in line:
            return "⚙️ <b>Parameter Setup</b> - Configuring Elastix with warning-free parameters"
        
        # Elastix version info
        if "ELASTIX version:" in line:
            version = line.split(":")[-1].strip()
            return f"ℹ️ <b>Elastix Version</b> - Running version {version}"
        
        if "InstallingComponents was successful" in line:
            return "✅ <b>Components Loaded</b> - All Elastix registration components initialized"
        
        # Pyramid warnings
        if "pyramid schedule is not fully specified" in line:
            return "⚠️ <b>Pyramid Schedule</b> - Using default multi-resolution pyramid (4 levels: 8x→4x→2x→1x)"
        
        # Resolution processing
        match = re.match(r'Resolution:\s*(\d+)', line)
        if match:
            level = int(match.group(1))
            scales = {0: "8x downsampled (coarse)", 1: "4x downsampled", 2: "2x downsampled", 
                     3: "Full resolution (fine)", 4: "Full resolution (fine)"}
            scale_desc = scales.get(level, f"Resolution level {level}")
            return f"📊 <b>Resolution Level {level}</b> - Processing at {scale_desc} for multi-scale registration"
        
        # Metric initialization
        if "Initialization of AdvancedMattesMutualInformation metric" in line:
            return "🎲 <b>Metric Ready</b> - Mattes Mutual Information metric initialized (good for fabric intensity differences)"
        
        # ASGD optimizer
        if "Starting automatic parameter estimation for AdaptiveStochasticGradientDescent" in line:
            return "🔬 <b>Auto-Tuning Optimizer</b> - Automatically estimating best learning rate and step size"
        
        if "Computing JacobianTerms" in line:
            return "📐 <b>Computing Jacobian</b> - Calculating image gradients for optimization"
        
        if "Sampling gradients" in line:
            return "📊 <b>Gradient Sampling</b> - Testing multiple sample points to estimate optimal parameters"
        
        if "Automatic parameter estimation took" in line:
            time_match = re.search(r'([\d.]+)s', line)
            if time_match:
                time_val = time_match.group(1)
                return f"✅ <b>Auto-Tuning Complete</b> - Optimizer configured in {time_val}s"
        
        # Iteration progress
        match = re.match(r'Time spent in resolution \d+ \(ITK initialization and iterating\):\s*([\d.]+)', line)
        if match:
            time_val = match.group(1)
            return f"⏱️ <b>Resolution Complete</b> - Finished registration iterations in {time_val}s"
        
        if "Stopping condition: Maximum number of iterations has been reached" in line:
            return "🛑 <b>Iterations Done</b> - Reached maximum iterations (registration converged or time limit)"
        
        # ASGD settings
        if "Settings of AdaptiveStochasticGradientDescent" in line and "resolution" in line:
            return "📋 <b>Optimizer Settings</b> - Final ASGD parameters for this resolution level"
        
        # Final metric value
        match = re.match(r'Final metric value\s*=\s*([-\d.]+)', line)
        if match:
            metric = float(match.group(1))
            if metric < -0.8:
                quality = "EXCELLENT ✨"
            elif metric < -0.5:
                quality = "GOOD ✅"
            elif metric < -0.2:
                quality = "MODERATE ⚠️"
            else:
                quality = "POOR ❌"
            return f"🎯 <b>Final Quality</b> - Metric value = {metric:.4f} ({quality} registration)"
        
        # Warp acceleration
        if "Module warp_acceleration" in line and "load on device" in line:
            match = re.search(r'took ([\d.]+) ms', line)
            if match:
                time_val = match.group(1)
                return f"⚡ <b>Warp Module Loaded</b> - GPU warping kernel ready in {time_val}ms (cached from previous run)"
        
        # PNG warning (harmless)
        if "libpng warning: iCCP" in line:
            return "ℹ️ <b>PNG Color Profile</b> - Outdated color profile in PNG (harmless, image loads fine)"
        
        # Clean parameters message
        if "Clean parameters configured" in line:
            return "✅ <b>Parameters Set</b> - All registration parameters configured (no warnings will be shown)"
        
        # Python-Elastix ready
        if "[OK] Using Python-Elastix registration engine" in line:
            return "🐍 <b>Python-Elastix Ready</b> - Using Python ITK-Elastix backend for registration"
        
        # Registration backend messages
        if "[Registration Backend]" in line:
            if "Starting Elastix registration" in line:
                return "🚀 <b>Backend: Registration Started</b> - Beginning registration process"
            elif "Saved images to" in line:
                return "💾 <b>Backend: Temp Files Created</b> - Images saved to temporary directory for processing"
            elif "Warping full-resolution RGB image" in line:
                return "🌈 <b>Backend: High-Res Warp</b> - Applying deformation to full-resolution color image"
            elif "Complete in" in line:
                match = re.search(r'([\d.]+)s', line)
                if match:
                    time_val = match.group(1)
                    return f"✅ <b>Backend: Complete</b> - Total registration time: {time_val}s"
            elif "Deformation range" in line:
                match = re.search(r'\[([-\d.]+),\s*([-\d.]+)\]', line)
                if match:
                    min_val = match.group(1)
                    max_val = match.group(2)
                    return f"📏 <b>Backend: Deformation Stats</b> - Displacement range: {min_val} to {max_val} pixels"
        
        # If no specific decoding, return empty
        return ""
    
    def clearOutput(self):
        """Clear both raw and decoded outputs"""
        self.raw_output.clear()
        self.decoded_output.clear()
        self.explanations.clear()
        
    def copyDecoded(self):
        """Copy decoded text to clipboard"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.decoded_output.toPlainText())
        
    def getDecodedText(self) -> str:
        """Get all decoded explanations as plain text"""
        return "\n".join(self.explanations)


# Example usage
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    decoder = ElastixOutputDecoder()
    decoder.show()
    
    # Simulate terminal output
    sample_output = [
        "✓ NVIDIA Warp available - Real-time acceleration enabled",
        'Warp 1.10.0 initialized:',
        '   CUDA Toolkit 12.8, Driver 13.0',
        '     "cuda:0"   : "NVIDIA GeForce RTX 5080 Laptop GPU" (16 GiB, sm_120, mempool enabled)',
        '  ✓ Custom fabric warping kernels compiled',
        'ELASTIX B-SPLINE REGISTRATION (ASGD Optimizer)',
        '[1] Loading and preprocessing...',
        'ELASTIX version: 5.2.0',
        'InstallingComponents was successful.',
        'Resolution: 0',
        'Initialization of AdvancedMattesMutualInformation metric took: 30 ms.',
        'Starting automatic parameter estimation for AdaptiveStochasticGradientDescent ...',
        'Automatic parameter estimation took 0.23s',
        'Time spent in resolution 4 (ITK initialization and iterating): 0.486',
        'Final metric value  = -0.933261',
        'Module warp_acceleration cc470a9 load on device \'cuda:0\' took 1.64 ms  (cached)',
    ]
    
    for line in sample_output:
        decoder.addOutput(line)
    
    sys.exit(app.exec())
