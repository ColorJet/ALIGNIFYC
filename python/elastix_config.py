"""
Elastix Configuration Manager
Loads/saves all Elastix parameters from/to YAML config file
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ElastixConfig:
    """Manages Elastix registration parameters from config file"""
    
    DEFAULT_CONFIG = {
        # Debug and logging
        'debug_mode': False,  # Set to True to see all terminal output
        'log_to_file': None,  # Path to log file, None = no file logging
        'log_to_console': True,  # Show Elastix terminal output
        
        # Registration method selection
        'registration_method': 'bspline',  # 'bspline', 'demons', or 'hybrid'
        'demons_iterations': 200,  # Iterations for Demons stage
        
        # Transform parameters
        'transform_type': 'BSplineTransform',
        'grid_spacing': 64,
        'bspline_transform_spline_order': 4,
        'bspline_interpolation_order': 4,
        'final_bspline_interpolation_order': 4,
        'use_cyclic_transform': True,
        
        # Metric
        'metric': 'AdvancedMattesMutualInformation',
        'number_of_histogram_bins': 32,
        'number_of_fixed_histogram_bins': 32,
        'number_of_moving_histogram_bins': 32,
        
        # Optimizer
        'optimizer': 'AdaptiveStochasticGradientDescent',
        'max_iterations': 500,
        'step_size': 0.6,  # SP_alpha
        'sp_a': 50.0,  # Iteration where step size starts decreasing
        'auto_parameter_estimation': True,
        'auto_scales_estimation': True,
        
        # NOTE: ASGD optimizer does NOT support convergence-based early stopping
        # The only way to save iterations is to distribute them adaptively across pyramid levels
        # See adaptive iteration distribution in elastix_registration.py
        
        # Multi-resolution pyramid
        'pyramid_levels': 4,
        'fixed_image_pyramid': 'FixedSmoothingImagePyramid',
        'moving_image_pyramid': 'MovingSmoothingImagePyramid',
        'pyramid_schedule': '8 8 4 4 2 2 1 1',
        
        # Sampling
        'sampler': 'RandomCoordinate',
        'spatial_samples': 5000,
        'max_sampling_attempts': 4,
        'new_samples_every_iteration': True,
        'check_number_of_samples': True,
        'use_normalization': True,
        
        # ASGD-specific parameters (for stage 2 of hybrid)
        'sp_a_stage2': 400.0,  # For second stage
        'sp_alpha_stage2': 0.602,  # For second stage
        
        # Advanced parameters (prevent warnings)
        'fixed_limit_range_ratio': 0.01,
        'moving_limit_range_ratio': 0.01,
        'fixed_kernel_bspline_order': 3,
        'moving_kernel_bspline_order': 3,
        'use_fast_and_low_memory': True,
        'use_jacobian_preconditioning': True,
        'finite_difference_derivative': True,
        
        # Output settings
        'write_result_image': True,
        'write_transform_parameters_each_iteration': False,
        'write_transform_parameters_each_resolution': False,
    }
    
    def __init__(self, config_path: str = "config/elastix_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
        
    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        self.config.update(loaded_config)
                print(f"✓ Loaded Elastix config from {self.config_path}")
            except Exception as e:
                print(f"⚠ Could not load config: {e}, using defaults")
        else:
            print(f"ℹ Config file not found, using defaults")
            # Save defaults
            self.save()
        
        return self.config
    
    def save(self):
        """Save current configuration to YAML file"""
        # Create config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        
        print(f"✓ Saved Elastix config to {self.config_path}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def update(self, new_config: Dict[str, Any]):
        """Update multiple configuration values"""
        self.config.update(new_config)
    
    def to_elastix_params(self) -> Dict[str, list]:
        """
        Convert config to Elastix parameter map format
        (all values must be lists of strings)
        """
        params = {}
        
        # Transform
        params["Transform"] = [self.config['transform_type']]
        params["FinalGridSpacingInPhysicalUnits"] = [str(self.config['grid_spacing'])]
        params["BSplineTransformSplineOrder"] = [str(self.config['bspline_transform_spline_order'])]
        params["BSplineInterpolationOrder"] = [str(self.config['bspline_interpolation_order'])]
        params["FinalBSplineInterpolationOrder"] = [str(self.config['final_bspline_interpolation_order'])]
        params["UseCyclicTransform"] = ["true" if self.config['use_cyclic_transform'] else "false"]
        
        # Metric
        params["Metric"] = [self.config['metric']]
        params["NumberOfHistogramBins"] = [str(self.config['number_of_histogram_bins'])]
        params["NumberOfFixedHistogramBins"] = [str(self.config['number_of_fixed_histogram_bins'])]
        params["NumberOfMovingHistogramBins"] = [str(self.config['number_of_moving_histogram_bins'])]
        
        # Optimizer
        params["Optimizer"] = [self.config['optimizer']]
        params["MaximumNumberOfIterations"] = [str(self.config['max_iterations'])]
        params["SP_alpha"] = [str(self.config['step_size'])]
        params["SP_A"] = [str(self.config['sp_a'])]
        params["AutomaticParameterEstimation"] = ["true" if self.config['auto_parameter_estimation'] else "false"]
        params["AutomaticScalesEstimation"] = ["true" if self.config['auto_scales_estimation'] else "false"]
        
        # Pyramid
        params["NumberOfResolutions"] = [str(self.config['pyramid_levels'])]
        params["FixedImagePyramid"] = [self.config['fixed_image_pyramid']]
        params["MovingImagePyramid"] = [self.config['moving_image_pyramid']]
        
        # Parse pyramid schedule
        schedule = self.config['pyramid_schedule'].split()
        params["ImagePyramidSchedule"] = schedule
        
        # Sampling
        params["ImageSampler"] = [self.config['sampler']]
        params["NumberOfSpatialSamples"] = [str(self.config['spatial_samples'])]
        params["MaximumNumberOfSamplingAttempts"] = [str(self.config['max_sampling_attempts'])]
        params["NewSamplesEveryIteration"] = ["true" if self.config['new_samples_every_iteration'] else "false"]
        
        # Advanced
        params["FixedLimitRangeRatio"] = [str(self.config['fixed_limit_range_ratio'])]
        params["MovingLimitRangeRatio"] = [str(self.config['moving_limit_range_ratio'])]
        params["FixedKernelBSplineOrder"] = [str(self.config['fixed_kernel_bspline_order'])]
        params["MovingKernelBSplineOrder"] = [str(self.config['moving_kernel_bspline_order'])]
        params["UseFastAndLowMemoryVersion"] = ["true" if self.config['use_fast_and_low_memory'] else "false"]
        params["UseJacobianPreconditioning"] = ["true" if self.config['use_jacobian_preconditioning'] else "false"]
        params["FiniteDifferenceDerivative"] = ["true" if self.config['finite_difference_derivative'] else "false"]
        
        # Output
        params["WriteResultImage"] = ["true" if self.config['write_result_image'] else "false"]
        params["WriteTransformParametersEachIteration"] = ["true" if self.config['write_transform_parameters_each_iteration'] else "false"]
        params["WriteTransformParametersEachResolution"] = ["true" if self.config['write_transform_parameters_each_resolution'] else "false"]
        
        # Basic registration setup (required)
        params["Registration"] = ["MultiResolutionRegistration"]
        params["ResampleInterpolator"] = ["FinalBSplineInterpolator"]
        params["Resampler"] = ["DefaultResampler"]
        params["FixedImageDimension"] = ["2"]
        params["MovingImageDimension"] = ["2"]
        params["UseDirectionCosines"] = ["true"]
        params["HowToCombineTransforms"] = ["Compose"]
        params["Interpolator"] = ["BSplineInterpolator"]
        
        # Additional parameters to prevent warnings (only real Elastix parameters)
        params["ShowExactMetricValue"] = ["false"]
        params["CheckNumberOfSamples"] = ["true"]
        params["UseMultiThreadingForMetrics"] = ["true"]
        params["FixedImageBSplineInterpolationOrder"] = ["1"]
        params["UseRandomSampleRegion"] = ["false"]
        params["UseNormalization"] = ["false"]
        params["SigmoidInitialTime"] = ["0"]
        params["MaxBandCovSize"] = ["192"]
        params["NumberOfBandStructureSamples"] = ["10"]
        params["MaximumStepLengthRatio"] = ["1"]
        params["MaximumStepLength"] = ["1"]
        params["SigmoidScaleFactor"] = ["0.1"]
        params["FixedInternalImagePixelType"] = ["float"]
        params["MovingInternalImagePixelType"] = ["float"]
        
        # REMOVED: Non-existent parameters that cause warnings:
        # - UseAdaptiveStepSizes (doesn't exist)
        # - UseConstantStep (doesn't exist)
        # - NumberOfGradientMeasurements (doesn't exist)
        # - NumberOfJacobianMeasurements (doesn't exist)
        # - NumberOfSamplesForExactGradient (doesn't exist)
        # - ASGDParameterEstimationMethod (doesn't exist)
        
        return params


# Example usage
if __name__ == "__main__":
    config = ElastixConfig()
    
    # Enable debug mode
    config.set('debug_mode', True)
    config.set('log_to_console', True)
    config.save()
    
    # Get Elastix parameters
    elastix_params = config.to_elastix_params()
    print("\nElastix Parameters:")
    for key, value in elastix_params.items():
        print(f"  {key}: {value}")
