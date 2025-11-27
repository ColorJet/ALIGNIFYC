"""
Advanced Elastix Configuration Dialog
Allows fine-tuning of all Elastix parameters to eliminate warnings
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QPushButton, QTabWidget, QWidget, QLineEdit
)
from PySide6.QtCore import Signal
import yaml
from pathlib import Path


class AdvancedElastixDialog(QDialog):
    """Advanced configuration dialog for all Elastix parameters"""
    
    parameters_changed = Signal(dict)
    
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        
        # Accept either ElastixConfig object or path string
        if config is not None:
            if hasattr(config, 'config_path'):
                # It's an ElastixConfig object
                self.config_obj = config
                self.config_path = config.config_path
            else:
                # It's a path string
                self.config_path = Path(config)
                self.config_obj = None
        else:
            self.config_path = Path("config/elastix_config.yaml")
            self.config_obj = None
            
        self.setWindowTitle("Advanced Elastix Configuration")
        self.setMinimumSize(800, 600)
        
        self.initUI()
        self.loadConfig()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for organized parameters
        tabs = QTabWidget()
        
        # Tab 1: Transform & Metric
        tab1 = self.createTransformTab()
        tabs.addTab(tab1, "Transform & Metric")
        
        # Tab 2: Optimizer
        tab2 = self.createOptimizerTab()
        tabs.addTab(tab2, "Optimizer")
        
        # Tab 3: Multi-Resolution Pyramid
        tab3 = self.createPyramidTab()
        tabs.addTab(tab3, "Multi-Resolution")
        
        # Tab 4: Sampling & Interpolation
        tab4 = self.createSamplingTab()
        tabs.addTab(tab4, "Sampling")
        
        # Tab 5: Advanced (all warning-related params)
        tab5 = self.createAdvancedTab()
        tabs.addTab(tab5, "Advanced (Warnings)")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save to Config")
        btn_apply = QPushButton("Apply")
        btn_reset = QPushButton("Reset to Defaults")
        btn_close = QPushButton("Close")
        
        btn_save.clicked.connect(self.saveConfig)
        btn_apply.clicked.connect(self.applySettings)
        btn_reset.clicked.connect(self.resetToDefaults)
        btn_close.clicked.connect(self.close)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
    def createTransformTab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        
        # Transform type
        layout.addWidget(QLabel("Transform Type:"), 0, 0)
        self.combo_transform = QComboBox()
        self.combo_transform.addItems(["BSplineTransform", "AffineTransform", "EulerTransform"])
        self.combo_transform.setCurrentText("BSplineTransform")
        layout.addWidget(self.combo_transform, 0, 1)
        
        # B-spline specific
        group_bspline = QGroupBox("B-Spline Settings")
        bspline_layout = QGridLayout()
        
        bspline_layout.addWidget(QLabel("Grid Spacing:"), 0, 0)
        self.spin_grid_spacing = QSpinBox()
        self.spin_grid_spacing.setRange(8, 200)
        self.spin_grid_spacing.setValue(64)
        bspline_layout.addWidget(self.spin_grid_spacing, 0, 1)
        
        bspline_layout.addWidget(QLabel("Spline Order:"), 1, 0)
        self.spin_spline_order = QSpinBox()
        self.spin_spline_order.setRange(1, 5)
        self.spin_spline_order.setValue(3)
        self.spin_spline_order.setToolTip("BSplineTransformSplineOrder parameter")
        bspline_layout.addWidget(self.spin_spline_order, 1, 1)
        
        bspline_layout.addWidget(QLabel("Interpolation Order:"), 2, 0)
        self.spin_interp_order = QSpinBox()
        self.spin_interp_order.setRange(0, 5)
        self.spin_interp_order.setValue(3)
        bspline_layout.addWidget(self.spin_interp_order, 2, 1)
        
        bspline_layout.addWidget(QLabel("Final Interpolation Order:"), 3, 0)
        self.spin_final_interp_order = QSpinBox()
        self.spin_final_interp_order.setRange(0, 5)
        self.spin_final_interp_order.setValue(3)
        self.spin_final_interp_order.setToolTip("FinalBSplineInterpolationOrder parameter")
        bspline_layout.addWidget(self.spin_final_interp_order, 3, 1)
        
        self.chk_cyclic = QCheckBox("Use Cyclic Transform")
        self.chk_cyclic.setToolTip("UseCyclicTransform parameter")
        bspline_layout.addWidget(self.chk_cyclic, 4, 0, 1, 2)
        
        group_bspline.setLayout(bspline_layout)
        layout.addWidget(group_bspline, 1, 0, 1, 2)
        
        # Metric
        layout.addWidget(QLabel("Metric:"), 2, 0)
        self.combo_metric = QComboBox()
        self.combo_metric.addItems([
            "AdvancedMeanSquares",
            "AdvancedMattesMutualInformation", 
            "AdvancedNormalizedCorrelation"
        ])
        layout.addWidget(self.combo_metric, 2, 1)
        
        layout.setRowStretch(10, 1)
        return widget
        
    def createOptimizerTab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        
        layout.addWidget(QLabel("Optimizer:"), 0, 0)
        self.combo_optimizer = QComboBox()
        self.combo_optimizer.addItems([
            "AdaptiveStochasticGradientDescent",
            "StandardGradientDescent",
            "RegularStepGradientDescent"
        ])
        layout.addWidget(self.combo_optimizer, 0, 1)
        
        layout.addWidget(QLabel("Max Iterations:"), 1, 0)
        self.spin_max_iter = QSpinBox()
        self.spin_max_iter.setRange(50, 5000)
        self.spin_max_iter.setValue(500)
        layout.addWidget(self.spin_max_iter, 1, 1)
        
        layout.addWidget(QLabel("Step Size (SP_alpha):"), 2, 0)
        self.spin_step_size = QDoubleSpinBox()
        self.spin_step_size.setRange(0.1, 2.0)
        self.spin_step_size.setValue(0.6)
        self.spin_step_size.setSingleStep(0.1)
        layout.addWidget(self.spin_step_size, 2, 1)
        
        layout.addWidget(QLabel("SP_A (decay start):"), 3, 0)
        self.spin_sp_a = QDoubleSpinBox()
        self.spin_sp_a.setRange(10, 200)
        self.spin_sp_a.setValue(50.0)
        layout.addWidget(self.spin_sp_a, 3, 1)
        
        layout.addWidget(QLabel("SP_a (ASGD param):"), 4, 0)
        self.spin_sp_a_lower = QDoubleSpinBox()
        self.spin_sp_a_lower.setRange(100, 1000)
        self.spin_sp_a_lower.setValue(400.0)
        self.spin_sp_a_lower.setToolTip("For ASGD optimizer (lowercase sp_a)")
        layout.addWidget(self.spin_sp_a_lower, 4, 1)
        
        self.chk_auto_param = QCheckBox("Automatic Parameter Estimation")
        self.chk_auto_param.setChecked(True)
        layout.addWidget(self.chk_auto_param, 5, 0, 1, 2)
        
        self.chk_auto_scales = QCheckBox("Automatic Scales Estimation")
        self.chk_auto_scales.setChecked(True)
        layout.addWidget(self.chk_auto_scales, 6, 0, 1, 2)
        
        layout.setRowStretch(10, 1)
        return widget
        
    def createPyramidTab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        
        layout.addWidget(QLabel("Number of Resolutions:"), 0, 0)
        self.spin_pyramid_levels = QSpinBox()
        self.spin_pyramid_levels.setRange(1, 6)
        self.spin_pyramid_levels.setValue(4)
        layout.addWidget(self.spin_pyramid_levels, 0, 1)
        
        layout.addWidget(QLabel("Fixed Image Pyramid:"), 1, 0)
        self.combo_fixed_pyramid = QComboBox()
        self.combo_fixed_pyramid.addItems([
            "FixedSmoothingImagePyramid",
            "FixedRecursiveImagePyramid",
            "FixedShrinkingImagePyramid"
        ])
        self.combo_fixed_pyramid.setToolTip("Prevents FixedImagePyramid warning")
        layout.addWidget(self.combo_fixed_pyramid, 1, 1)
        
        layout.addWidget(QLabel("Moving Image Pyramid:"), 2, 0)
        self.combo_moving_pyramid = QComboBox()
        self.combo_moving_pyramid.addItems([
            "MovingSmoothingImagePyramid",
            "MovingRecursiveImagePyramid",
            "MovingShrinkingImagePyramid"
        ])
        self.combo_moving_pyramid.setToolTip("Prevents MovingImagePyramid warning")
        layout.addWidget(self.combo_moving_pyramid, 2, 1)
        
        layout.addWidget(QLabel("Pyramid Schedule:"), 3, 0)
        self.edit_pyramid_schedule = QLineEdit("8 8 4 4 2 2 1 1")
        self.edit_pyramid_schedule.setToolTip("Space-separated values for each resolution level")
        layout.addWidget(self.edit_pyramid_schedule, 3, 1)
        
        layout.setRowStretch(10, 1)
        return widget
        
    def createSamplingTab(self):
        widget = QWidget()
        layout = QGridLayout(widget)
        
        layout.addWidget(QLabel("Image Sampler:"), 0, 0)
        self.combo_sampler = QComboBox()
        self.combo_sampler.addItems([
            "RandomCoordinate",
            "Random",
            "Full",
            "Grid"
        ])
        layout.addWidget(self.combo_sampler, 0, 1)
        
        layout.addWidget(QLabel("Spatial Samples:"), 1, 0)
        self.spin_samples = QSpinBox()
        self.spin_samples.setRange(500, 50000)
        self.spin_samples.setValue(5000)
        layout.addWidget(self.spin_samples, 1, 1)
        
        layout.addWidget(QLabel("Max Sampling Attempts:"), 2, 0)
        self.spin_max_attempts = QSpinBox()
        self.spin_max_attempts.setRange(1, 20)
        self.spin_max_attempts.setValue(4)
        layout.addWidget(self.spin_max_attempts, 2, 1)
        
        self.chk_new_samples = QCheckBox("New Samples Every Iteration")
        self.chk_new_samples.setChecked(True)
        layout.addWidget(self.chk_new_samples, 3, 0, 1, 2)
        
        self.chk_check_samples = QCheckBox("Check Number of Samples")
        self.chk_check_samples.setChecked(True)
        self.chk_check_samples.setToolTip("Verify sufficient samples are available")
        layout.addWidget(self.chk_check_samples, 4, 0, 1, 2)
        
        self.chk_use_normalization = QCheckBox("Use Normalization")
        self.chk_use_normalization.setChecked(False)
        self.chk_use_normalization.setToolTip("Normalize image intensities before registration")
        layout.addWidget(self.chk_use_normalization, 5, 0, 1, 2)
        
        layout.setRowStretch(10, 1)
        return widget
        
    def createAdvancedTab(self):
        """All parameters that prevent warnings"""
        widget = QWidget()
        layout = QGridLayout(widget)
        
        # Histogram parameters
        group_hist = QGroupBox("Histogram Parameters (prevents histogram warnings)")
        hist_layout = QGridLayout()
        
        hist_layout.addWidget(QLabel("Number of Histogram Bins:"), 0, 0)
        self.spin_hist_bins = QSpinBox()
        self.spin_hist_bins.setRange(8, 256)
        self.spin_hist_bins.setValue(32)
        hist_layout.addWidget(self.spin_hist_bins, 0, 1)
        
        hist_layout.addWidget(QLabel("Fixed Histogram Bins:"), 1, 0)
        self.spin_fixed_hist_bins = QSpinBox()
        self.spin_fixed_hist_bins.setRange(8, 256)
        self.spin_fixed_hist_bins.setValue(32)
        hist_layout.addWidget(self.spin_fixed_hist_bins, 1, 1)
        
        hist_layout.addWidget(QLabel("Moving Histogram Bins:"), 2, 0)
        self.spin_moving_hist_bins = QSpinBox()
        self.spin_moving_hist_bins.setRange(8, 256)
        self.spin_moving_hist_bins.setValue(32)
        hist_layout.addWidget(self.spin_moving_hist_bins, 2, 1)
        
        group_hist.setLayout(hist_layout)
        layout.addWidget(group_hist, 0, 0, 1, 2)
        
        # Limit range ratios
        group_range = QGroupBox("Limit Range Ratios (prevents range warnings)")
        range_layout = QGridLayout()
        
        range_layout.addWidget(QLabel("Fixed Limit Range Ratio:"), 0, 0)
        self.spin_fixed_limit = QDoubleSpinBox()
        self.spin_fixed_limit.setRange(0.0, 1.0)
        self.spin_fixed_limit.setValue(0.01)
        self.spin_fixed_limit.setDecimals(3)
        self.spin_fixed_limit.setSingleStep(0.001)
        range_layout.addWidget(self.spin_fixed_limit, 0, 1)
        
        range_layout.addWidget(QLabel("Moving Limit Range Ratio:"), 1, 0)
        self.spin_moving_limit = QDoubleSpinBox()
        self.spin_moving_limit.setRange(0.0, 1.0)
        self.spin_moving_limit.setValue(0.01)
        self.spin_moving_limit.setDecimals(3)
        self.spin_moving_limit.setSingleStep(0.001)
        range_layout.addWidget(self.spin_moving_limit, 1, 1)
        
        group_range.setLayout(range_layout)
        layout.addWidget(group_range, 1, 0, 1, 2)
        
        # Kernel B-spline orders
        group_kernel = QGroupBox("Kernel B-Spline Orders (prevents kernel warnings)")
        kernel_layout = QGridLayout()
        
        kernel_layout.addWidget(QLabel("Fixed Kernel Order:"), 0, 0)
        self.spin_fixed_kernel = QSpinBox()
        self.spin_fixed_kernel.setRange(0, 5)
        self.spin_fixed_kernel.setValue(0)
        kernel_layout.addWidget(self.spin_fixed_kernel, 0, 1)
        
        kernel_layout.addWidget(QLabel("Moving Kernel Order:"), 1, 0)
        self.spin_moving_kernel = QSpinBox()
        self.spin_moving_kernel.setRange(0, 5)
        self.spin_moving_kernel.setValue(3)
        kernel_layout.addWidget(self.spin_moving_kernel, 1, 1)
        
        group_kernel.setLayout(kernel_layout)
        layout.addWidget(group_kernel, 2, 0, 1, 2)
        
        # Optimization flags
        self.chk_fast_memory = QCheckBox("Use Fast And Low Memory Version")
        self.chk_fast_memory.setChecked(True)
        layout.addWidget(self.chk_fast_memory, 3, 0, 1, 2)
        
        self.chk_jacobian_precond = QCheckBox("Use Jacobian Preconditioning")
        layout.addWidget(self.chk_jacobian_precond, 4, 0, 1, 2)
        
        self.chk_finite_diff = QCheckBox("Finite Difference Derivative")
        layout.addWidget(self.chk_finite_diff, 5, 0, 1, 2)
        
        layout.setRowStretch(10, 1)
        return widget
        
    def getParameters(self):
        """Get all parameters as dict"""
        return {
            # Transform
            'transform_type': self.combo_transform.currentText(),
            'grid_spacing': self.spin_grid_spacing.value(),
            'bspline_transform_spline_order': self.spin_spline_order.value(),
            'bspline_interpolation_order': self.spin_interp_order.value(),
            'final_bspline_interpolation_order': self.spin_final_interp_order.value(),
            'use_cyclic_transform': self.chk_cyclic.isChecked(),
            
            # Metric
            'metric': self.combo_metric.currentText(),
            
            # Optimizer
            'optimizer': self.combo_optimizer.currentText(),
            'max_iterations': self.spin_max_iter.value(),
            'step_size': self.spin_step_size.value(),
            'sp_a': self.spin_sp_a.value(),
            'auto_parameter_estimation': self.chk_auto_param.isChecked(),
            'auto_scales_estimation': self.chk_auto_scales.isChecked(),
            
            # Pyramid
            'pyramid_levels': self.spin_pyramid_levels.value(),
            'fixed_image_pyramid': self.combo_fixed_pyramid.currentText(),
            'moving_image_pyramid': self.combo_moving_pyramid.currentText(),
            'pyramid_schedule': self.edit_pyramid_schedule.text(),
            
            # Sampling
            'sampler': self.combo_sampler.currentText(),
            'spatial_samples': self.spin_samples.value(),
            'max_sampling_attempts': self.spin_max_attempts.value(),
            'new_samples_every_iteration': self.chk_new_samples.isChecked(),
            
            # Advanced (warning prevention)
            'number_of_histogram_bins': self.spin_hist_bins.value(),
            'number_of_fixed_histogram_bins': self.spin_fixed_hist_bins.value(),
            'number_of_moving_histogram_bins': self.spin_moving_hist_bins.value(),
            'fixed_limit_range_ratio': self.spin_fixed_limit.value(),
            'moving_limit_range_ratio': self.spin_moving_limit.value(),
            'fixed_kernel_bspline_order': self.spin_fixed_kernel.value(),
            'moving_kernel_bspline_order': self.spin_moving_kernel.value(),
            'use_fast_and_low_memory': self.chk_fast_memory.isChecked(),
            'use_jacobian_preconditioning': self.chk_jacobian_precond.isChecked(),
            'finite_difference_derivative': self.chk_finite_diff.isChecked(),
        }
        
    def loadConfig(self):
        """Load from ElastixConfig object or YAML file"""
        if self.config_obj:
            # Load from ElastixConfig object
            config_dict = self.config_obj.config
            # Load values if they exist - map to widgets
            # TODO: Map config values to widgets
        elif self.config_path.exists():
            # Load from YAML file
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            elastix_config = config.get('registration', {})
            # Load values if they exist
            # TODO: Map config values to widgets
        
    def saveConfig(self):
        """Save to ElastixConfig object or YAML config file"""
        params = self.getParameters()
        
        if self.config_obj:
            # Update ElastixConfig object
            self.config_obj.update(params)
            self.config_obj.save()
            print(f"✓ Saved advanced Elastix config")
        else:
            # Save to YAML file (legacy)
            # Load existing config
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                config = {}
                
            # Update elastix section
            if 'registration' not in config:
                config['registration'] = {}
                
            config['registration']['elastix_advanced'] = params
            
            # Save back
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
                
            print(f"✓ Saved advanced Elastix config to {self.config_path}")
        
    def applySettings(self):
        """Apply current settings"""
        params = self.getParameters()
        self.parameters_changed.emit(params)
        
    def resetToDefaults(self):
        """Reset all to default values"""
        self.spin_grid_spacing.setValue(64)
        self.spin_max_iter.setValue(500)
        self.spin_pyramid_levels.setValue(4)
        # ... reset other widgets
