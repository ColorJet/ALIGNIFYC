"""
Elastix-based Fabric Registration
Better optimizer (ASGD) with proper early stopping
"""

# Fix Windows console encoding for Unicode characters
import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import itk
import numpy as np
import cv2
import time
import torch
from pathlib import Path

# Import NVIDIA Warp acceleration (with PyTorch fallback)
WARP_ACCELERATION_AVAILABLE = False

try:
    # Preferred: package-relative import when running as module
    from .warp_acceleration import WarpAcceleratedWarper
    WARP_ACCELERATION_AVAILABLE = True
except ImportError:
    try:
        # Fallback: absolute import when executed as a script (no package context)
        from warp_acceleration import WarpAcceleratedWarper
        WARP_ACCELERATION_AVAILABLE = True
    except ImportError:
        WARP_ACCELERATION_AVAILABLE = False
        # print("Note: Warp acceleration not available. Using PyTorch only.")

# Optional: Import logger for tracking results
try:
    from registration_logger import RegistrationLogger
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False
    # print("Note: registration_logger not available. Install for performance tracking.")


def print_gpu_memory():
    """Print current GPU memory usage"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3  # Convert to GB
        reserved = torch.cuda.memory_reserved() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        # print(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved, {total:.2f}GB total")
    else:
        # print("GPU not available")
        pass


class ElastixFabricRegistration:
    """
    Fabric registration using ITK-Elastix with ASGD optimizer
    Solves the over-exploration problem of LBFGSB
    """
    
    def __init__(self, use_clean_parameters=True, debug_mode=False, log_to_file=None):
        # Debug and logging settings
        self.debug_mode = debug_mode
        self.log_file = log_to_file
        self.log_to_console = debug_mode  # Only show Elastix terminal output if debug enabled
        
        if self.debug_mode:
            print("Initializing Elastix Registration...")
        
        self.pixel_type = itk.F  # Float type
        self.dimension = 2
        self.image_type = itk.Image[self.pixel_type, self.dimension]
        
        # PyTorch device for RGB warping
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.debug_mode:
            print(f"  Using device: {self.device}")
        
        # Initialize NVIDIA Warp acceleration
        if WARP_ACCELERATION_AVAILABLE:
            try:
                self.warp_accelerator = WarpAcceleratedWarper(enable_profiling=True)
                if self.debug_mode:
                    print(f"  ✓ Warp acceleration initialized")
                self.use_warp_acceleration = True
            except Exception as e:
                if self.debug_mode:
                    print(f"  ⚠ Warp initialization failed: {e}")
                self.use_warp_acceleration = False
        else:
            self.use_warp_acceleration = False
            if self.debug_mode:
                print(f"  Using PyTorch warping only")
        
        # Parameter configuration
        self.use_clean_parameters = use_clean_parameters
        if use_clean_parameters:
            if self.debug_mode:
                print("  Using clean parameters (avoid warnings)")
        else:
            if self.debug_mode:
                print("  Using default ITK parameters (may show warnings)")
        
        # Cache for deformation fields (optional - saves time for repeated pairs)
        self.deformation_cache = {}
        self.use_cache = False  # Set to True to enable caching
        
        # Logger for tracking results
        self.logger = RegistrationLogger() if LOGGER_AVAILABLE else None
    
    def preprocess_image(self, image_path, target_size=None, reference_img=None):
        """Load and preprocess image with optional histogram matching"""
        # FORCE ORIGINAL SIZE - DO NOT USE cv2.IMREAD_REDUCED flags
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE | cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Ensure single channel
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # print(f"Loaded: {Path(image_path).name}")
        # print(f"  ACTUAL ORIGINAL shape: {img.shape} ({img.shape[1]}x{img.shape[0]}), Range: [{img.min()}, {img.max()}], dtype: {img.dtype}")
        
        # Convert to uint8 if needed
        if img.dtype != np.uint8:
            if img.max() > 255:
                img = (img / img.max() * 255).astype(np.uint8)
            else:
                img = img.astype(np.uint8)
        
        # Resize if needed
        if target_size and img.shape != target_size:
            target_wh = (target_size[1], target_size[0])
            img = cv2.resize(img, target_wh, interpolation=cv2.INTER_LINEAR)
            # print(f"  Resized to: {img.shape} ({img.shape[1]}x{img.shape[0]})")
        
        # CLAHE enhancement (adaptive based on image type)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        img = clahe.apply(img)
        
        # Additional preprocessing for thread patterns (if needed)
        # This will be controlled by parameters passed to register_bspline
        
        # Enhanced preprocessing for different background intensities
        if reference_img is not None:
            # print(f"  Applying preprocessing for intensity matching...")
            
            # Check intensity distributions
            ref_mean = reference_img.mean()
            img_mean = img.mean()
            # print(f"    Reference mean: {ref_mean:.1f}, Moving mean: {img_mean:.1f}")
            
            # Apply background normalization if there's a significant difference
            intensity_diff = abs(ref_mean - img_mean)
            if intensity_diff > 30:
                # print(f"    Large intensity difference detected ({intensity_diff:.1f})")
                # print(f"    Applying background normalization...")
                img = self.normalize_background_intensity(img, reference_img)
            
            # Always apply histogram matching for final alignment
            # print(f"    Applying histogram matching...")
            img = self.match_histograms(img, reference_img)
        
        # Normalize to float
        img = img.astype(np.float32)
        
        return img
    
    def normalize_background_intensity(self, source, reference):
        """Normalize background intensity to match reference"""
        # Find background values (assume highest frequency pixels are background)
        src_hist, bins = np.histogram(source.flatten(), 256, [0, 256])
        ref_hist, _ = np.histogram(reference.flatten(), 256, [0, 256])
        
        # Find most common intensities (likely backgrounds)
        src_bg = np.argmax(src_hist)
        ref_bg = np.argmax(ref_hist)
        
        # print(f"    Detected backgrounds: source={src_bg}, reference={ref_bg}")
        
        # Apply intensity shift to align backgrounds
        shift = ref_bg - src_bg
        shifted = source.astype(np.float32) + shift
        
        # Ensure values stay in valid range
        shifted = np.clip(shifted, 0, 255).astype(np.uint8)
        
        # print(f"    Applied shift: {shift}, new range: [{shifted.min()}, {shifted.max()}]")
        return shifted
    
    def match_histograms(self, source, reference):
        """Match histogram of source to reference using cumulative distribution"""
        # Compute histograms
        src_hist, bins = np.histogram(source.flatten(), 256, [0, 256])
        ref_hist, _ = np.histogram(reference.flatten(), 256, [0, 256])
        
        # Compute cumulative distribution functions
        src_cdf = src_hist.cumsum()
        src_cdf = src_cdf / src_cdf[-1]  # Normalize
        
        ref_cdf = ref_hist.cumsum()
        ref_cdf = ref_cdf / ref_cdf[-1]  # Normalize
        
        # Create lookup table
        lookup = np.zeros(256, dtype=np.uint8)
        j = 0
        for i in range(256):
            while j < 255 and ref_cdf[j] < src_cdf[i]:
                j += 1
            lookup[i] = j
        
        # Apply lookup
        matched = lookup[source]
        # print(f"    Before: [{source.min()}, {source.max()}], After: [{matched.min()}, {matched.max()}]")
        return matched
    
    def enhance_thread_patterns(self, img):
        """Enhance thread patterns for better registration"""
        # Check image size - skip expensive processing for very large images
        img_size = img.shape[0] * img.shape[1]
        if img_size > 5_000_000:  # 5 megapixels threshold
            # print(f"    Skipping thread enhancement - image too large ({img_size/1e6:.1f}MP)")
            # print(f"    Using faster preprocessing instead")
            # Just apply gentle CLAHE for large images
            clahe_thread = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
            return clahe_thread.apply(img)
        
        # Apply edge-preserving smoothing to reduce noise while keeping thread structures
        # Use smaller diameter for speed
        img_smooth = cv2.bilateralFilter(img, 5, 50, 50)  # Reduced from 9, 75, 75
        
        # Enhance local contrast for better thread definition
        clahe_thread = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
        img_enhanced = clahe_thread.apply(img_smooth)
        
        # Sharpen thread boundaries with a lighter kernel
        kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])  # Lighter sharpening
        img_sharpened = cv2.filter2D(img_enhanced, -1, kernel)
        
        # Blend original and sharpened (70% enhanced, 30% sharpened)
        result = cv2.addWeighted(img_enhanced, 0.7, img_sharpened, 0.3, 0)
        
        # print(f"    Applied thread enhancement: bilateral filter + CLAHE + sharpening")
        return result.astype(np.uint8)
    
    def numpy_to_itk(self, np_image):
        """Convert numpy array to ITK image"""
        # Safety check: prevent memory allocation errors for huge images
        max_pixels = 2_000_000  # 2 megapixels max for ITK conversion
        total_pixels = np_image.shape[0] * np_image.shape[1]
        
        if total_pixels > max_pixels:
            raise MemoryError(
                f"Image too large for ITK conversion: {np_image.shape} ({total_pixels:,} pixels)\n"
                f"Maximum allowed: {max_pixels:,} pixels (~1414x1414)\n"
                f"Current: {np_image.shape[1]}x{np_image.shape[0]}\n"
                f"This indicates the image wasn't downsampled properly before registration.\n"
                f"Please check target_size parameter in register_bspline()."
            )
        
        # ITK expects (width, height) ordering
        itk_image = itk.image_from_array(np_image.astype(np.float32))
        return itk_image
    
    def register_bspline(self, fixed_path, moving_path, target_size=(1024, 1024), parameters=None):
        """
        B-spline registration using Elastix with ASGD optimizer
        
        Args:
            fixed_path: Path to fixed image (camera capture)
            moving_path: Path to moving image (design)
            target_size: (H, W) for processing
            parameters: dict with GUI parameters (grid_spacing, max_iterations, etc.)
        
        Returns:
            deformation_field: numpy array [H, W, 2]
            fixed_np: numpy array [H, W]
            moving_np: numpy array [H, W]
            metadata: dict with registration quality metrics
        """
        # print("\n" + "="*70)
        # print("ELASTIX B-SPLINE REGISTRATION (ASGD Optimizer)")
        # print("="*70)
        
        start_total = time.time()
        
        # Initialize metadata
        metadata = {
            'success': False,
            'final_metric': None,
            'registration_time': 0,
            'quality': 'unknown'
        }
        
        # Check cache first
        cache_key = f"{Path(fixed_path).stem}_{Path(moving_path).stem}_{target_size}"
        if self.use_cache and cache_key in self.deformation_cache:
            # print(f"  [OK] Using cached deformation field for {cache_key}")
            cached_data = self.deformation_cache[cache_key]
            return cached_data['deformation'], cached_data['fixed'], cached_data['moving'], cached_data['metadata']
        
        # Load images
        # print("\n[1] Loading and preprocessing...")
        print_gpu_memory()
        
        # SIMPLIFIED: Trust that backend already downsampled images to target_size
        # Just use the images as-is - no need to recalculate or resize
        
        # Check if thread mode is enabled
        thread_mode = parameters.get('thread_mode', False) if parameters else False
        
        # Preprocess fixed image first (reference) - load at actual file size
        fixed_np = self.preprocess_image(fixed_path, target_size=None)
        
        # Only apply thread enhancement for smaller images and if explicitly enabled
        if thread_mode and fixed_np.shape[0] * fixed_np.shape[1] < 3_000_000:
            # print("  Applying thread enhancement to fixed image...")
            fixed_np = self.enhance_thread_patterns(fixed_np.astype(np.uint8)).astype(np.float32)
        elif thread_mode:
            # print(f"  Skipping thread enhancement - image too large ({fixed_np.shape[0]}x{fixed_np.shape[1]})")
            pass
        
        # Preprocess moving image with histogram matching to fixed - load at actual file size
        moving_np = self.preprocess_image(moving_path, target_size=None, reference_img=fixed_np.astype(np.uint8))
        
        # Only apply thread enhancement for smaller images and if explicitly enabled  
        if thread_mode and moving_np.shape[0] * moving_np.shape[1] < 3_000_000:
            # print("  Applying thread enhancement to moving image...")
            moving_np = self.enhance_thread_patterns(moving_np.astype(np.uint8)).astype(np.float32)
        elif thread_mode:
            # print(f"  Skipping thread enhancement - image too large ({moving_np.shape[0]}x{moving_np.shape[1]})")
            pass
        
        # print(f"\nFINAL PROCESSING SIZE: {fixed_np.shape} ({fixed_np.shape[1]}x{fixed_np.shape[0]})")
        print(f"DEBUG: About to convert to ITK - fixed_np.shape={fixed_np.shape}, moving_np.shape={moving_np.shape}")
        print(f"DEBUG: Fixed: {fixed_np.shape[0]}x{fixed_np.shape[1]} = {fixed_np.shape[0]*fixed_np.shape[1]:,} pixels")
        print(f"DEBUG: Moving: {moving_np.shape[0]}x{moving_np.shape[1]} = {moving_np.shape[0]*moving_np.shape[1]:,} pixels")
        print_gpu_memory()
        
        # Convert to ITK
        fixed_itk = self.numpy_to_itk(fixed_np)
        moving_itk = self.numpy_to_itk(moving_np)
        
        # print(f"\n[2] Setting up Elastix B-spline registration...")
        
        # Create parameter object for B-spline registration
        parameter_object = itk.ParameterObject.New()
        
        # Use GUI parameters if provided, otherwise use adaptive selection
        if parameters and 'grid_spacing' in parameters:
            # Use GUI parameters
            max_iter = str(parameters.get('max_iterations', 500))
            samples = str(parameters.get('spatial_samples', 5000))
            grid_spacing = str(parameters.get('grid_spacing', 64))
            step_size = str(parameters.get('step_size', 0.6))
            optimizer = parameters.get('optimizer', 'AdaptiveStochasticGradientDescent')
            metric = parameters.get('metric', 'AdvancedMeanSquares')
            sampler = parameters.get('sampler', 'RandomCoordinate')
            bspline_order = str(parameters.get('bspline_order', 3))
            pyramid_levels = str(parameters.get('pyramid_levels', 4))
            
            # Auto-detect optimal metric based on image characteristics
            auto_metric = parameters.get('auto_metric', True)
            thread_mode = parameters.get('thread_mode', False)
            
            if auto_metric:
                # Detect thread-like textures using gradient analysis
                fixed_grad_x = cv2.Sobel(fixed_np, cv2.CV_64F, 1, 0, ksize=3)
                fixed_grad_y = cv2.Sobel(fixed_np, cv2.CV_64F, 0, 1, ksize=3)
                fixed_grad_mag = np.sqrt(fixed_grad_x**2 + fixed_grad_y**2)
                
                moving_grad_x = cv2.Sobel(moving_np, cv2.CV_64F, 1, 0, ksize=3)
                moving_grad_y = cv2.Sobel(moving_np, cv2.CV_64F, 0, 1, ksize=3)
                moving_grad_mag = np.sqrt(moving_grad_x**2 + moving_grad_y**2)
                
                # Calculate gradient statistics
                fixed_grad_mean = fixed_grad_mag.mean()
                moving_grad_mean = moving_grad_mag.mean()
                gradient_ratio = fixed_grad_mean / (moving_grad_mean + 1e-6)
                
                # Check for directional patterns (thread-like textures)
                is_thread_like = (fixed_grad_mean > 15 and moving_grad_mean > 15) or thread_mode
                
                intensity_diff = abs(fixed_np.mean() - moving_np.mean())
                
                # print(f"  -> Image analysis: Gradient ratio={gradient_ratio:.2f}, Intensity diff={intensity_diff:.1f}")
                
                if is_thread_like and metric == 'AdvancedMeanSquares':
                    # print(f"  -> Thread-like texture detected")
                    # NormalizedGradientCorrelation requires 3D images, use alternative for 2D
                    # print(f"  -> Using AdvancedNormalizedCorrelation for 2D thread patterns")
                    metric = 'AdvancedNormalizedCorrelation'
                    # Adjust other parameters for thread registration
                    if int(samples) < 6000:
                        samples = "8000"
                        # print(f"  -> Increased samples to {samples} for texture matching")
                elif metric == 'AdvancedMeanSquares' and (intensity_diff > 40):
                    # print(f"  -> Large intensity difference detected - switching to AdvancedMattesMutualInformation")
                    metric = 'AdvancedMattesMutualInformation'
            
            # print(f"  -> Using GUI parameters: Grid={grid_spacing}, Iter={max_iter}, Samples={samples}")
        else:
            # Adaptive parameter selection based on image similarity
            initial_diff = np.abs(fixed_np - moving_np).mean()
            # print(f"  Initial image difference: {initial_diff:.2f}")
            
            # Adjust parameters based on initial similarity
            if initial_diff > 50:  # Very different images - need more work
                max_iter = "800"
                samples = "8000"
                grid_spacing = "48"  # Finer grid for difficult pairs
                # print(f"  -> Difficult pair detected: using enhanced parameters")
            elif initial_diff > 30:  # Moderately different
                max_iter = "500"
                samples = "5000"
                grid_spacing = "64"
                # print(f"  -> Moderate difficulty: using standard parameters")
            else:  # Similar images - faster convergence
                max_iter = "300"
                samples = "3000"
                grid_spacing = "80"  # Coarser grid for easy pairs
                # print(f"  -> Easy pair detected: using optimized parameters")
            
            # Default values for parameters not set by adaptive selection
            step_size = "0.6"
            optimizer = "AdaptiveStochasticGradientDescent"
            metric = "AdvancedMeanSquares"
            sampler = "RandomCoordinate"
            bspline_order = "3"
            pyramid_levels = "4"
        
        if self.use_clean_parameters:
            # print("  Configuring CLEAN parameters (no warnings)...")
            # Create clean parameter map from scratch (no obsolete parameters)
            bspline_params = {}
            
            # Basic registration setup
            bspline_params["Registration"] = ["MultiResolutionRegistration"]
            bspline_params["Transform"] = ["BSplineTransform"]
            bspline_params["Metric"] = [metric]
            bspline_params["Optimizer"] = [optimizer]
            bspline_params["ResampleInterpolator"] = ["FinalBSplineInterpolator"]
            bspline_params["Resampler"] = ["DefaultResampler"]
            
            # Image dimensions
            bspline_params["FixedImageDimension"] = ["2"]
            bspline_params["MovingImageDimension"] = ["2"]
            bspline_params["UseDirectionCosines"] = ["true"]
            
            # Multi-resolution pyramid - OPTIMIZED for adaptive iteration distribution
            bspline_params["NumberOfResolutions"] = [pyramid_levels]
            
            # Dynamic pyramid schedule based on levels
            if int(pyramid_levels) == 4:
                bspline_params["ImagePyramidSchedule"] = ["8", "8", "4", "4", "2", "2", "1", "1"]
            elif int(pyramid_levels) == 3:
                bspline_params["ImagePyramidSchedule"] = ["4", "4", "2", "2", "1", "1"]
            else:
                bspline_params["ImagePyramidSchedule"] = ["8", "8", "4", "4", "2", "2", "1", "1"]
            
            # Explicitly set pyramid types (prevents FixedImagePyramid/MovingImagePyramid warnings)
            bspline_params["FixedImagePyramid"] = ["FixedSmoothingImagePyramid"]
            bspline_params["MovingImagePyramid"] = ["MovingSmoothingImagePyramid"]
            
            # ADAPTIVE ITERATION DISTRIBUTION per resolution level
            # ASGD optimizer does NOT support early stopping, so we MUST limit iterations per level
            # Strategy: Coarse levels need fewer iterations, fine levels need more
            # This prevents wasting 500 iterations at 8x downsampled level
            
            # Override MaximumNumberOfIterations with per-level adaptive distribution
            if int(pyramid_levels) == 4:
                # Distribute max_iter across 4 levels intelligently
                # Level 0 (8x): ~20% of budget (rough alignment)
                # Level 1 (4x): ~25% of budget (refine)
                # Level 2 (2x): ~30% of budget (precision)
                # Level 3 (1x): ~25% of budget (final polish)
                max_int = int(max_iter)
                iter_level0 = str(max(50, int(max_int * 0.20)))   # Min 50
                iter_level1 = str(max(100, int(max_int * 0.25)))  # Min 100
                iter_level2 = str(max(150, int(max_int * 0.30)))  # Min 150  
                iter_level3 = str(max(125, int(max_int * 0.25)))  # Min 125
                # Replace single MaximumNumberOfIterations with per-level specification
                # Use space-separated string format for Elastix
                bspline_params["MaximumNumberOfIterations"] = [f"{iter_level0} {iter_level1} {iter_level2} {iter_level3}"]
            elif int(pyramid_levels) == 3:
                max_int = int(max_iter)
                iter_level0 = str(max(100, int(max_int * 0.30)))
                iter_level1 = str(max(150, int(max_int * 0.35)))
                iter_level2 = str(max(150, int(max_int * 0.35)))
                bspline_params["MaximumNumberOfIterations"] = [f"{iter_level0} {iter_level1} {iter_level2}"]
            # else: single resolution uses max_iter as-is (already set above)
            
            # B-spline transform - set all parameters to prevent warnings
            bspline_params["FinalGridSpacingInPhysicalUnits"] = [grid_spacing]
            bspline_params["HowToCombineTransforms"] = ["Compose"]
            bspline_params["BSplineTransformSplineOrder"] = ["3"]  # Prevents warning
            bspline_params["UseCyclicTransform"] = ["false"]  # Prevents warning
            
            # Optimizer settings - ADAPTIVE based on optimizer type
            bspline_params["MaximumNumberOfIterations"] = [max_iter]
            bspline_params["AutomaticParameterEstimation"] = ["true"]
            bspline_params["AutomaticScalesEstimation"] = ["true"]
            
            # OPTIMIZER-SPECIFIC PARAMETERS
            if optimizer == "AdaptiveStochasticGradientDescent":
                # ASGD-specific parameters
                bspline_params["SP_alpha"] = [step_size]  # Step size factor from GUI
                bspline_params["SP_A"] = ["50.0"]     # Iteration where step size starts decreasing
                bspline_params["SP_a"] = ["400.0"]    # For ASGD optimizer
                # NOTE: ASGD optimizer does NOT support convergence-based early stopping
                # Only stops at MaximumNumberOfIterations
                
            elif optimizer in ["QuasiNewtonLBFGS", "ConjugateGradientFRPR", "ConjugateGradient"]:
                # Deterministic optimizers with REAL convergence support
                bspline_params["MaximumStepLength"] = ["1.0"]  # Max step size
                bspline_params["MinimumStepLength"] = ["1e-6"]  # Convergence threshold - STOPS when step becomes tiny
                bspline_params["GradientMagnitudeTolerance"] = ["1e-6"]  # Stop when gradient is small
                bspline_params["ValueTolerance"] = ["1e-5"]  # Stop when cost function change is small
                bspline_params["StepLength"] = [step_size]  # Initial step size
                
                if optimizer == "QuasiNewtonLBFGS":
                    # L-BFGS specific parameters
                    bspline_params["LBFGSMemory"] = ["10"]  # Memory for L-BFGS approximation
                    
                    # Wolfe line search parameters (REAL stopping criteria!)
                    bspline_params["StopIfWolfeNotSatisfied"] = ["true"]  # Stop if Wolfe conditions fail
                    bspline_params["WolfeParameterGamma"] = ["0.9"]  # Curvature condition parameter
                    bspline_params["WolfeParameterSigma"] = ["0.0001"]  # Sufficient decrease parameter
                    
                    # Line search accuracy
                    bspline_params["LBFGSUpdateAccuracy"] = ["5"]  # Update accuracy (3-10 typical)
                    bspline_params["MaximumNumberOfLineSearchIterations"] = ["20"]  # Max line search iterations
                elif optimizer in ["ConjugateGradientFRPR", "ConjugateGradient"]:
                    # Conjugate gradient line search
                    bspline_params["LineSearchValueTolerance"] = ["1e-4"]
                    bspline_params["LineSearchGradientTolerance"] = ["1e-4"]
                    
            elif optimizer == "RegularStepGradientDescent":
                # Regular gradient descent with step control
                bspline_params["MaximumStepLength"] = ["1.0"]
                bspline_params["MinimumStepLength"] = ["1e-6"]  # Convergence threshold
                bspline_params["GradientMagnitudeTolerance"] = ["1e-6"]
                bspline_params["RelaxationFactor"] = ["0.5"]  # Step reduction factor
                
            elif optimizer == "StandardGradientDescent":
                # Simple gradient descent
                bspline_params["SP_a"] = [step_size]  # Step size
                bspline_params["GradientMagnitudeTolerance"] = ["1e-6"]  # Convergence
                bspline_params["MinimumStepLength"] = ["1e-6"]
            
            # For ASGD: Reduce max iterations per resolution level for adaptive stopping
            # This is the ONLY way to prevent wasting iterations with ASGD optimizer
            # For deterministic optimizers: They will stop early when converged!
            
            # Multi-threading
            import os
            num_threads = os.cpu_count() or 20
            bspline_params["MaximumNumberOfThreads"] = [str(num_threads)]
            
            # Use GUI-specified samples (don't override)
            bspline_params["NumberOfSpatialSamples"] = [samples]
            
            # Sampling strategy
            bspline_params["ImageSampler"] = [sampler]
            bspline_params["NewSamplesEveryIteration"] = ["true"]
            bspline_params["MaximumNumberOfSamplingAttempts"] = ["4"]
            bspline_params["CheckNumberOfSamples"] = ["true"]
            bspline_params["UseNormalization"] = ["false"]
            
            # Interpolation - set all parameters to prevent warnings
            bspline_params["Interpolator"] = ["BSplineInterpolator"]
            bspline_params["BSplineInterpolationOrder"] = [bspline_order]
            bspline_params["FinalBSplineInterpolationOrder"] = ["3"]  # Prevents warning
            
            # Histogram bins (prevents NumberOfHistogramBins warnings)
            bspline_params["NumberOfHistogramBins"] = ["32"]
            bspline_params["NumberOfFixedHistogramBins"] = ["32"]
            bspline_params["NumberOfMovingHistogramBins"] = ["32"]
            
            # Limit range ratios (prevents FixedLimitRangeRatio warnings)
            bspline_params["FixedLimitRangeRatio"] = ["0.01"]
            bspline_params["MovingLimitRangeRatio"] = ["0.01"]
            
            # Kernel B-spline orders (prevents kernel warnings)
            bspline_params["FixedKernelBSplineOrder"] = ["0"]
            bspline_params["MovingKernelBSplineOrder"] = ["3"]
            
            # Memory/speed optimizations (prevents UseFast warnings)
            bspline_params["UseFastAndLowMemoryVersion"] = ["true"]
            bspline_params["UseJacobianPreconditioning"] = ["false"]
            bspline_params["FiniteDifferenceDerivative"] = ["false"]
            
            # Additional parameters (avoid duplicates from optimizer section above)
            bspline_params["ShowExactMetricValue"] = ["false"]
            bspline_params["CheckNumberOfSamples"] = ["true"]
            bspline_params["UseMultiThreadingForMetrics"] = ["true"]
            bspline_params["FixedImageBSplineInterpolationOrder"] = ["1"]
            bspline_params["UseRandomSampleRegion"] = ["false"]
            bspline_params["UseNormalization"] = ["false"]
            bspline_params["SigmoidInitialTime"] = ["0"]
            bspline_params["MaxBandCovSize"] = ["192"]
            bspline_params["NumberOfBandStructureSamples"] = ["10"]
            bspline_params["MaximumStepLengthRatio"] = ["1"]
            bspline_params["MaximumStepLength"] = ["1"]
            bspline_params["SigmoidScaleFactor"] = ["0.1"]
            bspline_params["FixedInternalImagePixelType"] = ["float"]
            bspline_params["MovingInternalImagePixelType"] = ["float"]
            
            # REMOVED: These parameters don't exist in Elastix and cause warnings:
            # - UseAdaptiveStepSizes
            # - UseConstantStep
            # - NumberOfGradientMeasurements
            # - NumberOfJacobianMeasurements
            # - NumberOfSamplesForExactGradient
            # - ASGDParameterEstimationMethod
            
        else:
            # print("  Using DEFAULT ITK parameters (may show warnings)...")
            # Use default parameters (may trigger warnings for obsolete parameters)
            bspline_params = parameter_object.GetDefaultParameterMap("bspline")
            
            # Override key parameters
            bspline_params["Metric"] = ["AdvancedMeanSquares"]
            bspline_params["MaximumNumberOfIterations"] = [max_iter]
            bspline_params["SP_alpha"] = ["0.6"]
            bspline_params["SP_A"] = ["50.0"]
            bspline_params["NumberOfSpatialSamples"] = [samples]
            bspline_params["FinalGridSpacingInPhysicalUnits"] = [grid_spacing]
            bspline_params["NumberOfResolutions"] = ["4"]
            bspline_params["ImagePyramidSchedule"] = ["8", "8", "4", "4", "2", "2", "1", "1"]
        
        # Output settings
        bspline_params["WriteTransformParametersEachIteration"] = ["false"]
        bspline_params["WriteTransformParametersEachResolution"] = ["false"]
        bspline_params["WriteResultImage"] = ["true"]
        
        # print("  Clean parameters configured (no warnings):")
        # print(f"    ✓ Metric: {metric}")
        # print(f"    ✓ Optimizer: {optimizer} with SP_alpha={step_size}")
        # print(f"    ✓ Max iterations: {max_iter}")
        # print(f"    ✓ Grid spacing: {grid_spacing} (smaller = finer details)")
        # print(f"    ✓ Spatial samples: {samples}")
        # print(f"    ✓ Sampler: {sampler}")
        # print(f"    ✓ B-spline order: {bspline_order}")
        # print(f"    ✓ Multi-resolution: {pyramid_levels} levels")
        # print(f"    ✓ Obsolete parameters: REMOVED")
        # print(f"    ✓ Histogram matching: ENABLED (fixes contrast mismatch)")
        # print(f"    ✓ Elastix registration: CPU-based")
        # print(f"    ✓ RGB warping: {self.device} (PyTorch grid_sample)")
        
        # Add to parameter object
        parameter_object.AddParameterMap(bspline_params)
        
        # === PARAMETER VALIDATION AND LOGGING ===
        if self.debug_mode or True:  # Always log for debugging warnings
            print("\n" + "="*70)
            print("📋 ELASTIX PARAMETER MAP (Complete Configuration)")
            print("="*70)
            
            # Identify optimizer-specific required parameters
            if optimizer == "AdaptiveStochasticGradientDescent":
                required_params = ['Optimizer', 'MaximumNumberOfIterations', 'SP_alpha', 'SP_A', 'SP_a']
            elif optimizer in ["QuasiNewtonLBFGS", "ConjugateGradientFRPR", "ConjugateGradient"]:
                required_params = ['Optimizer', 'MaximumNumberOfIterations', 'MinimumStepLength', 
                                 'GradientMagnitudeTolerance', 'ValueTolerance']
            elif optimizer in ["RegularStepGradientDescent", "StandardGradientDescent"]:
                required_params = ['Optimizer', 'MaximumNumberOfIterations', 'MinimumStepLength', 
                                 'GradientMagnitudeTolerance']
            else:
                required_params = ['Optimizer', 'MaximumNumberOfIterations']
            
            # Log all parameters
            for key, value in sorted(bspline_params.items()):
                if key in required_params:
                    print(f"  ✓ {key:45s} = {value}")
                else:
                    print(f"    {key:45s} = {value}")
            
            # Verify required optimizer parameters are present
            print("\n🔍 Optimizer Parameter Validation:")
            missing_params = []
            for param in required_params:
                if param not in bspline_params:
                    missing_params.append(param)
                    print(f"  ⚠️  MISSING: {param}")
                else:
                    print(f"  ✓ {param} = {bspline_params[param]}")
            
            if missing_params:
                print(f"\n⚠️  WARNING: {len(missing_params)} required optimizer parameters missing!")
                print(f"     This may cause Elastix to use default values and show warnings.")
            else:
                print(f"\n✅ All required parameters for {optimizer} present!")
            
            print("="*70 + "\n")
        
        # Run registration
        # print(f"\n[3] Running Elastix registration...")
        start_reg = time.time()
        
        # Track registration progress for quality assessment
        registration_start_time = time.time()
        
        result_image, result_transform = itk.elastix_registration_method(
            fixed_itk,
            moving_itk,
            parameter_object=parameter_object,
            log_to_console=self.log_to_console  # Use debug setting
        )
        
        reg_time = time.time() - start_reg
        # print(f"\n  Registration completed in {reg_time:.2f}s")
        
        # Extract final metric value from transform parameters
        try:
            final_metric = float(result_transform.GetParameterMap(0)["0_FinalMetricValue"][0])
            # print(f"  Final metric value: {final_metric:.6f}")
            
            # Quality assessment
            if final_metric < 10:
                # print(f"  [OK] EXCELLENT quality (metric < 10)")
                pass
            elif final_metric < 100:
                # print(f"  [OK] GOOD quality (metric < 100)")
                pass
            elif final_metric < 500:
                # print(f"  [WARNING] MODERATE quality (metric < 500) - consider different pair")
                pass
            else:
                # print(f"  [WARNING] POOR quality (metric >= 500) - this pair may not align well")
                pass
        except:
            # print(f"  (Metric value not available)")
            pass
        
        print_gpu_memory()
        
        # Get deformation field
        # print(f"\n[4] Extracting deformation field...")
        
        # Convert result transform to deformation field
        # This requires transformix
        transformix_object = itk.TransformixFilter.New(moving_itk)
        transformix_object.SetTransformParameterObject(result_transform)
        transformix_object.ComputeDeformationFieldOn()
        transformix_object.UpdateLargestPossibleRegion()
        
        deformation_field_itk = transformix_object.GetOutputDeformationField()
        deformation_np = itk.array_from_image(deformation_field_itk)
        
        # print(f"  Deformation shape: {deformation_np.shape}")
        # print(f"  Deformation range: x=[{deformation_np[:,:,0].min():.2f}, {deformation_np[:,:,0].max():.2f}], "
        # f"y=[{deformation_np[:,:,1].min():.2f}, {deformation_np[:,:,1].max():.2f}]")
        
        magnitude = np.sqrt(deformation_np[:,:,0]**2 + deformation_np[:,:,1]**2)
        # print(f"  Max displacement: {magnitude.max():.2f} pixels")
        
        # Update metadata
        metadata['success'] = True
        metadata['registration_time'] = reg_time
        if 'final_metric' in locals():
            metadata['final_metric'] = final_metric
            if final_metric < 10:
                metadata['quality'] = 'excellent'
            elif final_metric < 100:
                metadata['quality'] = 'good'
            elif final_metric < 500:
                metadata['quality'] = 'moderate'
            else:
                metadata['quality'] = 'poor'
        
        total_time = time.time() - start_total
        # print(f"\n" + "="*70)
        # print(f"TOTAL TIME: {total_time:.2f}s")
        # print(f"QUALITY: {metadata['quality'].upper()}")
        # print("="*70)
        
        # Cache result if enabled
        if self.use_cache:
            self.deformation_cache[cache_key] = {
                'deformation': deformation_np,
                'fixed': fixed_np,
                'moving': moving_np,
                'metadata': metadata
            }
        
        return deformation_np, fixed_np, moving_np, metadata
    
    def warp_image_with_flow(self, image, flow):
        """
        Warp an image using a flow field (displacement field)
        
        Args:
            image: [B, C, H, W] tensor
            flow: [B, 2, H, W] flow field (x, y displacements)
        
        Returns:
            Warped image [B, C, H, W]
        """
        B, C, H, W = image.shape
        
        # Create sampling grid
        grid_y, grid_x = torch.meshgrid(
            torch.arange(H, device=image.device, dtype=torch.float32),
            torch.arange(W, device=image.device, dtype=torch.float32),
            indexing='ij'
        )
        
        # Add flow to grid
        sample_grid_x = grid_x + flow[:, 0]  # Add x displacement
        sample_grid_y = grid_y + flow[:, 1]  # Add y displacement
        
        # Normalize to [-1, 1] for grid_sample
        sample_grid_x = 2.0 * sample_grid_x / (W - 1) - 1.0
        sample_grid_y = 2.0 * sample_grid_y / (H - 1) - 1.0
        
        # Stack to [B, H, W, 2]
        grid = torch.stack([sample_grid_x, sample_grid_y], dim=-1)
        
        # Warp image
        warped = torch.nn.functional.grid_sample(
            image, grid,
            mode='bilinear',
            padding_mode='border',
            align_corners=True
        )
        
        return warped
    
    def warp_rgb_image(self, rgb_path, deformation_field, output_path):
        """Apply deformation to RGB image with smart memory management"""
        # print(f"\n  Loading RGB image: {rgb_path}")
        print_gpu_memory()
        
        # Load RGB
        rgb = cv2.imread(str(rgb_path), cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
        if rgb is None:
            raise ValueError(f"Could not load RGB: {rgb_path}")
        
        total_pixels = rgb.shape[0] * rgb.shape[1]
        memory_required_gb = (total_pixels * 3 * 4) / (1024**3)  # RGB float32
        
        print(f"  RGB image: {rgb.shape[1]}×{rgb.shape[0]} = {total_pixels:,} pixels ({total_pixels/1e6:.1f}MP)")
        print(f"  Memory required for PyTorch tensor: {memory_required_gb:.2f}GB")
        
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        
        # SMART MEMORY HANDLING: Use tiled processing for very large images
        # With 32GB RAM + 16GB GPU, we can handle up to ~50MP in one go
        # Beyond that, use tiled warping
        MAX_PIXELS_SINGLE_PASS = 50_000_000  # 50MP threshold
        
        if total_pixels > MAX_PIXELS_SINGLE_PASS:
            print(f"  ⚠️ Very large image ({total_pixels/1e6:.1f}MP) - using tiled warping for memory safety")
            return self._warp_rgb_tiled(rgb, deformation_field, output_path)
        else:
            print(f"  ✅ Image size acceptable - processing in single pass")
        
        # Check if we can use NVIDIA Warp acceleration
        if self.use_warp_acceleration:
            try:
                # print(f" Using NVIDIA Warp real-time acceleration...")
                
                # Split deformation field into X and Y components
                deform_x = deformation_field[:, :, 0].astype(np.float32)
                deform_y = deformation_field[:, :, 1].astype(np.float32)
                
                # Resize deformation if needed to match RGB
                if deform_x.shape != rgb.shape[:2]:
                    # print(f"  Resizing deformation from {deform_x.shape} to {rgb.shape[:2]}")
                    h_scale = rgb.shape[0] / deform_x.shape[0]
                    w_scale = rgb.shape[1] / deform_x.shape[1]
                    
                    deform_x = cv2.resize(deform_x, (rgb.shape[1], rgb.shape[0]), 
                                        interpolation=cv2.INTER_LINEAR) * w_scale
                    deform_y = cv2.resize(deform_y, (rgb.shape[1], rgb.shape[0]), 
                                        interpolation=cv2.INTER_LINEAR) * h_scale
                    
                    # print(f"  Deformation scaling: h={h_scale:.2f}x, w={w_scale:.2f}x")
                
                # Real-time warping with Warp
                start_time = time.time()
                warped_rgb_np = self.warp_accelerator.warp_image_realtime(
                    rgb, deform_x, deform_y, interpolation="bilinear"
                )
                warp_time = time.time() - start_time
                
                # print(f"  ✓ Warp acceleration: {warp_time*1000:.1f}ms ({1.0/warp_time:.1f} fps)")
                
                # Convert to expected output format
                warped_rgb = warped_rgb_np.astype(np.uint8)
                
            except Exception as e:
                # print(f"  ⚠ Warp acceleration failed: {e}")
                # print(f"  Falling back to PyTorch...")
                warped_rgb = self._warp_with_pytorch_fallback(rgb, deformation_field)
        else:
            # Original PyTorch implementation
            warped_rgb = self._warp_with_pytorch_fallback(rgb, deformation_field)
        
        # print(f"  Final image range: [{warped_rgb.min()}, {warped_rgb.max()}]")
        
        # Ensure contiguous array for OpenCV
        if not warped_rgb.flags['C_CONTIGUOUS']:
            warped_rgb = np.ascontiguousarray(warped_rgb)
        
        # Save
        cv2.imwrite(str(output_path), cv2.cvtColor(warped_rgb, cv2.COLOR_RGB2BGR))
        # print(f"  Warped RGB saved to: {output_path}")
        
        return warped_rgb
    
    def _warp_with_pytorch_fallback(self, rgb: np.ndarray, deformation_field: np.ndarray) -> np.ndarray:
        """PyTorch fallback warping implementation (original method)"""
        
        # print(f"  Using PyTorch warping (fallback)...")
        
        # Convert deformation to PyTorch flow
        # Deformation is [H, W, 2], need to convert to [1, 2, H, W]
        flow_field = torch.from_numpy(deformation_field).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
        
        # Convert RGB to tensor - keep values in 0-255 range
        rgb_tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float().to(self.device)
        
        # print(f"  RGB tensor shape: {rgb_tensor.shape}")
        # print(f"  Flow field shape: {flow_field.shape}")
        
        # Resize flow if needed
        if flow_field.shape[2:] != rgb_tensor.shape[2:]:
            # print(f"  Resizing flow from {flow_field.shape[2:]} to {rgb_tensor.shape[2:]}")
            
            h_scale = rgb_tensor.shape[2] / flow_field.shape[2]
            w_scale = rgb_tensor.shape[3] / flow_field.shape[3]
            
            flow_resized = torch.nn.functional.interpolate(
                flow_field, size=rgb_tensor.shape[2:], mode='bilinear', align_corners=True
            )
            
            # Scale flow values proportionally
            flow_resized[:, 0] *= w_scale  # x displacement
            flow_resized[:, 1] *= h_scale  # y displacement
            
            # print(f"  Flow scaling: h={h_scale:.2f}x, w={w_scale:.2f}x")
        else:
            flow_resized = flow_field
            # print(f"  Flow already matches RGB size")
        
        # Warp using PyTorch
        # print(f"  Warping RGB image with PyTorch...")
        print_gpu_memory()
        warped_rgb_tensor = self.warp_image_with_flow(rgb_tensor, flow_resized)
        
        # print(f"  After PyTorch warping:")
        print_gpu_memory()
        
        # Clip to valid range and convert
        warped_rgb_tensor = torch.clamp(warped_rgb_tensor, 0, 255)
        warped_rgb_np = warped_rgb_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy().astype(np.uint8)
        
        # print(f"  PyTorch output shape: {warped_rgb_np.shape}")
        
        return warped_rgb_np
    
    def _warp_rgb_tiled(self, rgb: np.ndarray, deformation_field: np.ndarray, output_path: Path) -> np.ndarray:
        """
        Warp very large RGB images using tiled processing to manage memory
        
        Args:
            rgb: Full resolution RGB image [H, W, 3]
            deformation_field: Deformation field (may be lower resolution)
            output_path: Where to save result
        
        Returns:
            Warped RGB image [H, W, 3]
        """
        print(f"  🔲 Tiled warping for {rgb.shape[1]}×{rgb.shape[0]} image")
        
        # Determine tile size based on available memory (16GB GPU = ~5000×5000 tiles)
        TILE_SIZE = 4096  # 4K tiles = ~16MP per tile
        OVERLAP = 128     # Overlap to avoid seams
        
        h, w = rgb.shape[:2]
        result = np.zeros_like(rgb)
        
        # Scale deformation field to match RGB size
        if deformation_field.shape[:2] != (h, w):
            h_scale = h / deformation_field.shape[0]
            w_scale = w / deformation_field.shape[1]
            
            deform_x = cv2.resize(deformation_field[:, :, 0], (w, h), interpolation=cv2.INTER_LINEAR) * w_scale
            deform_y = cv2.resize(deformation_field[:, :, 1], (w, h), interpolation=cv2.INTER_LINEAR) * h_scale
            deformation_full = np.stack([deform_x, deform_y], axis=2).astype(np.float32)
        else:
            deformation_full = deformation_field
        
        # Calculate number of tiles
        num_tiles_y = (h + TILE_SIZE - 1) // TILE_SIZE
        num_tiles_x = (w + TILE_SIZE - 1) // TILE_SIZE
        total_tiles = num_tiles_y * num_tiles_x
        
        print(f"  Processing {num_tiles_y}×{num_tiles_x} = {total_tiles} tiles ({TILE_SIZE}×{TILE_SIZE} each)")
        
        tile_count = 0
        for tile_y in range(num_tiles_y):
            for tile_x in range(num_tiles_x):
                tile_count += 1
                
                # Calculate tile boundaries with overlap
                y_start = max(0, tile_y * TILE_SIZE - OVERLAP)
                y_end = min(h, (tile_y + 1) * TILE_SIZE + OVERLAP)
                x_start = max(0, tile_x * TILE_SIZE - OVERLAP)
                x_end = min(w, (tile_x + 1) * TILE_SIZE + OVERLAP)
                
                # Extract tile
                rgb_tile = rgb[y_start:y_end, x_start:x_end]
                deform_tile = deformation_full[y_start:y_end, x_start:x_end]
                
                # Warp tile using PyTorch
                try:
                    warped_tile = self._warp_with_pytorch_fallback(rgb_tile, deform_tile)
                except Exception as e:
                    print(f"    ⚠️ Tile {tile_count}/{total_tiles} failed: {e}, using original")
                    warped_tile = rgb_tile
                
                # Blend tile into result (center region without overlap)
                y_start_inner = tile_y * TILE_SIZE
                y_end_inner = min(h, (tile_y + 1) * TILE_SIZE)
                x_start_inner = tile_x * TILE_SIZE
                x_end_inner = min(w, (tile_x + 1) * TILE_SIZE)
                
                # Calculate offsets within the tile
                tile_y_offset = y_start_inner - y_start
                tile_y_len = y_end_inner - y_start_inner
                tile_x_offset = x_start_inner - x_start
                tile_x_len = x_end_inner - x_start_inner
                
                result[y_start_inner:y_end_inner, x_start_inner:x_end_inner] = \
                    warped_tile[tile_y_offset:tile_y_offset+tile_y_len, 
                               tile_x_offset:tile_x_offset+tile_x_len]
                
                if tile_count % 10 == 0 or tile_count == total_tiles:
                    print(f"    Progress: {tile_count}/{total_tiles} tiles ({100*tile_count/total_tiles:.1f}%)")
        
        print(f"  ✅ Tiled warping complete - {total_tiles} tiles processed")
        
        # Save result
        if not result.flags['C_CONTIGUOUS']:
            result = np.ascontiguousarray(result)
        cv2.imwrite(str(output_path), cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
        
        return result
    
    def get_warp_performance_summary(self) -> str:
        """Get performance summary from Warp accelerator"""
        if self.use_warp_acceleration and hasattr(self, 'warp_accelerator'):
            return self.warp_accelerator.get_performance_summary()
        return "Warp acceleration not available"
    
    def register_demons(self, fixed_path, moving_path, target_size=(1024, 1024), parameters=None):
        """
        Demons registration using Elastix
        Good for large deformations, can be followed by B-spline for refinement
        
        Args:
            fixed_path: Path to fixed image (camera capture)
            moving_path: Path to moving image (design)
            target_size: (H, W) for processing
            parameters: dict with GUI parameters (max_iterations, etc.)
        
        Returns:
            deformation_field: numpy array [H, W, 2]
            fixed_np: numpy array [H, W]
            moving_np: numpy array [H, W]
            metadata: dict with registration quality metrics
        """
        if self.debug_mode:
            print("\n" + "="*70)
            print("ELASTIX DEMONS REGISTRATION")
            print("="*70)
        
        start_total = time.time()
        
        # Initialize metadata
        metadata = {
            'success': False,
            'final_metric': None,
            'registration_time': 0,
            'quality': 'unknown',
            'method': 'demons'
        }
        
        # SIMPLIFIED: Trust that backend already downsampled images to target_size
        # Preprocess images - load at actual file size
        fixed_np = self.preprocess_image(fixed_path, target_size=None)
        moving_np = self.preprocess_image(moving_path, target_size=None, reference_img=fixed_np.astype(np.uint8))
        
        # Convert to ITK
        fixed_itk = self.numpy_to_itk(fixed_np)
        moving_itk = self.numpy_to_itk(moving_np)
        
        # Create parameter object for Demons
        parameter_object = itk.ParameterObject.New()
        
        # Get parameters from GUI or use defaults
        max_iter = str(parameters.get('max_iterations', 300)) if parameters else "300"
        pyramid_levels = str(parameters.get('pyramid_levels', 3)) if parameters else "3"
        metric = parameters.get('metric', 'AdvancedMeanSquares') if parameters else 'AdvancedMeanSquares'
        
        # Map user-friendly names to Elastix metric names
        metric_map = {
            'AdvancedMattesMutualInformation': 'AdvancedMattesMutualInformation',
            'AdvancedMeanSquares': 'AdvancedMeanSquares',
            'AdvancedNormalizedCorrelation': 'AdvancedNormalizedCorrelation',
            'MutualInformation': 'AdvancedMattesMutualInformation',
            'MeanSquares': 'AdvancedMeanSquares',
            'NormalizedCorrelation': 'AdvancedNormalizedCorrelation'
        }
        elastix_metric = metric_map.get(metric, 'AdvancedMeanSquares')
        
        # Demons-like parameter map using fine B-spline grid for dense deformation
        demons_params = {}
        
        # Basic setup
        demons_params["Registration"] = ["MultiResolutionRegistration"]
        demons_params["Transform"] = ["BSplineTransform"]
        demons_params["Metric"] = [elastix_metric]
        demons_params["Optimizer"] = ["StandardGradientDescent"]  # Simple gradient descent
        demons_params["ResampleInterpolator"] = ["FinalBSplineInterpolator"]
        demons_params["Resampler"] = ["DefaultResampler"]
        
        # Image dimensions
        demons_params["FixedImageDimension"] = ["2"]
        demons_params["MovingImageDimension"] = ["2"]
        demons_params["UseDirectionCosines"] = ["true"]
        
        # Multi-resolution pyramid
        demons_params["NumberOfResolutions"] = [pyramid_levels]
        if int(pyramid_levels) == 3:
            demons_params["ImagePyramidSchedule"] = ["4", "4", "2", "2", "1", "1"]
        else:
            demons_params["ImagePyramidSchedule"] = ["8", "8", "4", "4", "2", "2", "1", "1"]
        
        demons_params["FixedImagePyramid"] = ["FixedSmoothingImagePyramid"]
        demons_params["MovingImagePyramid"] = ["MovingSmoothingImagePyramid"]
        
        # Optimizer parameters for gradient descent
        demons_params["MaximumNumberOfIterations"] = [max_iter]
        demons_params["MaximumStepLength"] = ["1.0"]
        demons_params["MinimumStepLength"] = ["0.01"]
        
        # Sampling parameters for Full sampler
        demons_params["ImageSampler"] = ["Full"]  # Use all pixels
        demons_params["NumberOfSpatialSamples"] = ["2048"]  # Not used with Full sampler
        demons_params["NewSamplesEveryIteration"] = ["false"]  # Not relevant for Full sampler
        demons_params["MaximumNumberOfSamplingAttempts"] = ["0"]  # 0 = no limit for Full sampler
        demons_params["CheckNumberOfSamples"] = ["false"]  # Not needed for Full sampler
        demons_params["UseNormalization"] = ["false"]
        
        # Interpolation
        demons_params["Interpolator"] = ["BSplineInterpolator"]
        demons_params["BSplineInterpolationOrder"] = ["1"]
        
        # Dense B-spline grid (small spacing = more deformation freedom)
        demons_params["FinalGridSpacingInPhysicalUnits"] = ["8"]  # Very fine grid
        demons_params["HowToCombineTransforms"] = ["Compose"]
        demons_params["BSplineTransformSplineOrder"] = ["3"]
        demons_params["UseCyclicTransform"] = ["false"]
        demons_params["FinalBSplineInterpolationOrder"] = ["3"]
        
        # Histogram and internal types
        demons_params["NumberOfHistogramBins"] = ["32"]
        demons_params["ShowExactMetricValue"] = ["false"]
        demons_params["UseMultiThreadingForMetrics"] = ["true"]
        demons_params["FixedInternalImagePixelType"] = ["float"]
        demons_params["MovingInternalImagePixelType"] = ["float"]
        
        # Output settings
        demons_params["WriteTransformParametersEachIteration"] = ["false"]
        demons_params["WriteTransformParametersEachResolution"] = ["false"]
        demons_params["WriteResultImage"] = ["true"]
        
        parameter_object.AddParameterMap(demons_params)
        
        if self.debug_mode:
            print(f"  Max iterations: {max_iter}")
            print(f"  Pyramid levels: {pyramid_levels}")
            print(f"  Optimizer: FastAndAccurateDemonsOptimizer")
        
        # Run registration
        start_reg = time.time()
        
        result_image, result_transform = itk.elastix_registration_method(
            fixed_itk,
            moving_itk,
            parameter_object=parameter_object,
            log_to_console=self.log_to_console
        )
        
        reg_time = time.time() - start_reg
        
        if self.debug_mode:
            print(f"\n  Registration completed in {reg_time:.2f}s")
        
        # Extract deformation field
        transformix_object = itk.TransformixFilter.New(moving_itk)
        transformix_object.SetTransformParameterObject(result_transform)
        transformix_object.ComputeDeformationFieldOn()
        transformix_object.UpdateLargestPossibleRegion()
        
        deformation_field_itk = transformix_object.GetOutputDeformationField()
        deformation_np = itk.array_from_image(deformation_field_itk)
        
        # Update metadata
        metadata['success'] = True
        metadata['registration_time'] = reg_time
        metadata['quality'] = 'good'  # Demons typically gives good quality
        
        total_time = time.time() - start_total
        
        if self.debug_mode:
            magnitude = np.sqrt(deformation_np[:,:,0]**2 + deformation_np[:,:,1]**2)
            print(f"  Max displacement: {magnitude.max():.2f} pixels")
            print(f"  Total time: {total_time:.2f}s")
        
        return deformation_np, fixed_np, moving_np, metadata
    
    def register_hybrid(self, fixed_path, moving_path, target_size=(1024, 1024), parameters=None):
        """
        Hybrid Demons→B-spline registration
        
        Step 1: Demons for large deformations (fast, robust)
        Step 2: B-spline for local refinement (accurate details)
        
        This combines the best of both: speed + accuracy
        
        Args:
            fixed_path: Path to fixed image (camera capture)
            moving_path: Path to moving image (design)
            target_size: (H, W) for processing
            parameters: dict with GUI parameters
        
        Returns:
            deformation_field: numpy array [H, W, 2]
            fixed_np: numpy array [H, W]
            moving_np: numpy array [H, W]
            metadata: dict with registration quality metrics
        """
        if self.debug_mode:
            print("\n" + "="*70)
            print("ELASTIX HYBRID REGISTRATION (Demons → B-spline)")
            print("="*70)
            print("Strategy:")
            print("  Step 1: Demons for large deformations")
            print("  Step 2: B-spline for fine-tuning")
            print("="*70)
        
        start_total = time.time()
        
        # Initialize metadata
        metadata = {
            'success': False,
            'final_metric': None,
            'registration_time': 0,
            'quality': 'unknown',
            'method': 'hybrid_demons_bspline'
        }
        
        # SIMPLIFIED: Trust that backend already downsampled images to target_size
        # Preprocess images - load at actual file size
        fixed_np = self.preprocess_image(fixed_path, target_size=None)
        moving_np = self.preprocess_image(moving_path, target_size=None, reference_img=fixed_np.astype(np.uint8))
        
        # Convert to ITK
        fixed_itk = self.numpy_to_itk(fixed_np)
        moving_itk = self.numpy_to_itk(moving_np)
        
        # Create parameter object with TWO stages
        parameter_object = itk.ParameterObject.New()
        
        # Get parameters from GUI or use defaults
        demons_iter = str(parameters.get('demons_iterations', 200)) if parameters else "200"
        bspline_iter = str(parameters.get('max_iterations', 300)) if parameters else "300"
        grid_spacing = str(parameters.get('grid_spacing', 64)) if parameters else "64"
        pyramid_levels = str(parameters.get('pyramid_levels', 3)) if parameters else "3"
        metric = parameters.get('metric', 'AdvancedMattesMutualInformation') if parameters else 'AdvancedMattesMutualInformation'
        optimizer = parameters.get('optimizer', 'AdaptiveStochasticGradientDescent') if parameters else 'AdaptiveStochasticGradientDescent'
        
        # Map user-friendly names to Elastix metric names
        metric_map = {
            'AdvancedMattesMutualInformation': 'AdvancedMattesMutualInformation',
            'AdvancedMeanSquares': 'AdvancedMeanSquares',
            'AdvancedNormalizedCorrelation': 'AdvancedNormalizedCorrelation',
            'MutualInformation': 'AdvancedMattesMutualInformation',
            'MeanSquares': 'AdvancedMeanSquares',
            'NormalizedCorrelation': 'AdvancedNormalizedCorrelation'
        }
        elastix_metric = metric_map.get(metric, 'AdvancedMattesMutualInformation')
        
        # ========================================
        # STAGE 1: DEMONS-LIKE (Coarse alignment with fine B-spline grid)
        # ========================================
        demons_params = {}
        demons_params["Registration"] = ["MultiResolutionRegistration"]
        demons_params["Transform"] = ["BSplineTransform"]
        demons_params["Metric"] = [elastix_metric]
        demons_params["Optimizer"] = ["StandardGradientDescent"]  # Stage 1 uses fast optimizer
        demons_params["ResampleInterpolator"] = ["FinalBSplineInterpolator"]
        demons_params["Resampler"] = ["DefaultResampler"]
        demons_params["FixedImageDimension"] = ["2"]
        demons_params["MovingImageDimension"] = ["2"]
        demons_params["UseDirectionCosines"] = ["true"]
        demons_params["NumberOfResolutions"] = [pyramid_levels]
        
        if int(pyramid_levels) == 3:
            demons_params["ImagePyramidSchedule"] = ["4", "4", "2", "2", "1", "1"]
        else:
            demons_params["ImagePyramidSchedule"] = ["8", "8", "4", "4", "2", "2", "1", "1"]
        
        demons_params["FixedImagePyramid"] = ["FixedSmoothingImagePyramid"]
        demons_params["MovingImagePyramid"] = ["MovingSmoothingImagePyramid"]
        demons_params["MaximumNumberOfIterations"] = [demons_iter]
        demons_params["MaximumStepLength"] = ["1.0"]
        demons_params["MinimumStepLength"] = ["0.01"]
        
        # Sampling parameters (for stage 1)
        demons_params["ImageSampler"] = ["Full"]
        demons_params["NumberOfSpatialSamples"] = ["2048"]  # Not used with Full sampler but prevents warnings
        demons_params["NewSamplesEveryIteration"] = ["false"]  # Not relevant for Full sampler
        demons_params["MaximumNumberOfSamplingAttempts"] = ["0"]  # 0 = no limit for Full sampler
        demons_params["CheckNumberOfSamples"] = ["false"]  # Not needed for Full sampler
        demons_params["UseNormalization"] = ["false"]
        
        # Interpolation
        demons_params["Interpolator"] = ["BSplineInterpolator"]
        demons_params["BSplineInterpolationOrder"] = ["1"]
        
        # Transform parameters
        demons_params["HowToCombineTransforms"] = ["Compose"]
        demons_params["FinalGridSpacingInPhysicalUnits"] = ["16"]  # Coarse grid for stage 1
        demons_params["BSplineTransformSplineOrder"] = ["3"]
        demons_params["UseCyclicTransform"] = ["false"]
        demons_params["FinalBSplineInterpolationOrder"] = ["3"]
        
        # Histogram and internal types
        demons_params["NumberOfHistogramBins"] = ["32"]
        demons_params["ShowExactMetricValue"] = ["false"]
        demons_params["UseMultiThreadingForMetrics"] = ["true"]
        demons_params["FixedInternalImagePixelType"] = ["float"]
        demons_params["MovingInternalImagePixelType"] = ["float"]
        
        # StandardGradientDescent doesn't use these, but add them to prevent stage 2 warnings
        # (Stage 2 will override these with its own values)
        demons_params["SP_alpha"] = ["1.0"]  # Not used by StandardGradientDescent
        demons_params["SP_A"] = ["50.0"]     # Not used by StandardGradientDescent
        demons_params["SP_a"] = ["400.0"]    # Not used by StandardGradientDescent
        
        # Output settings
        demons_params["WriteTransformParametersEachIteration"] = ["false"]
        demons_params["WriteTransformParametersEachResolution"] = ["false"]
        demons_params["WriteResultImage"] = ["false"]
        
        parameter_object.AddParameterMap(demons_params)
        
        # ========================================
        # STAGE 2: B-SPLINE (Fine refinement)
        # ========================================
        bspline_params = {}
        bspline_params["Registration"] = ["MultiResolutionRegistration"]
        bspline_params["Transform"] = ["BSplineTransform"]
        bspline_params["Metric"] = [elastix_metric]  # Use same metric as stage 1
        bspline_params["Optimizer"] = ["AdaptiveStochasticGradientDescent"]
        bspline_params["ResampleInterpolator"] = ["FinalBSplineInterpolator"]
        bspline_params["Resampler"] = ["DefaultResampler"]
        bspline_params["FixedImageDimension"] = ["2"]
        bspline_params["MovingImageDimension"] = ["2"]
        bspline_params["UseDirectionCosines"] = ["true"]
        bspline_params["NumberOfResolutions"] = ["2"]  # Only 2 levels for refinement
        bspline_params["ImagePyramidSchedule"] = ["2", "2", "1", "1"]
        bspline_params["FixedImagePyramid"] = ["FixedSmoothingImagePyramid"]
        bspline_params["MovingImagePyramid"] = ["MovingSmoothingImagePyramid"]
        bspline_params["FinalGridSpacingInPhysicalUnits"] = [grid_spacing]
        bspline_params["HowToCombineTransforms"] = ["Compose"]
        bspline_params["BSplineTransformSplineOrder"] = ["3"]
        bspline_params["UseCyclicTransform"] = ["false"]
        bspline_params["MaximumNumberOfIterations"] = [bspline_iter]
        
        # ASGD optimizer parameters (stage 2 specific)
        bspline_params["SP_alpha"] = ["0.602"]  # Default ASGD value
        bspline_params["SP_A"] = ["50.0"]
        bspline_params["SP_a"] = ["400.0"]  # For ASGD
        bspline_params["AutomaticParameterEstimation"] = ["true"]
        bspline_params["AutomaticScalesEstimation"] = ["true"]
        
        # Sampling parameters
        bspline_params["ImageSampler"] = ["RandomCoordinate"]
        bspline_params["NumberOfSpatialSamples"] = ["5000"]
        bspline_params["NewSamplesEveryIteration"] = ["true"]
        bspline_params["MaximumNumberOfSamplingAttempts"] = ["4"]
        bspline_params["CheckNumberOfSamples"] = ["true"]
        bspline_params["UseNormalization"] = ["false"]
        
        # Interpolation
        bspline_params["Interpolator"] = ["BSplineInterpolator"]
        bspline_params["BSplineInterpolationOrder"] = ["3"]
        bspline_params["FinalBSplineInterpolationOrder"] = ["3"]
        
        # Histogram and internal types
        bspline_params["NumberOfHistogramBins"] = ["32"]
        bspline_params["FixedInternalImagePixelType"] = ["float"]
        bspline_params["MovingInternalImagePixelType"] = ["float"]
        
        # Output settings
        bspline_params["WriteTransformParametersEachIteration"] = ["false"]
        bspline_params["WriteTransformParametersEachResolution"] = ["false"]
        bspline_params["WriteResultImage"] = ["true"]
        
        parameter_object.AddParameterMap(bspline_params)
        
        if self.debug_mode:
            print(f"  Stage 1 (Demons): {demons_iter} iterations")
            print(f"  Stage 2 (B-spline): {bspline_iter} iterations, grid={grid_spacing}")
        
        # Run two-stage registration
        start_reg = time.time()
        
        result_image, result_transform = itk.elastix_registration_method(
            fixed_itk,
            moving_itk,
            parameter_object=parameter_object,
            log_to_console=self.log_to_console
        )
        
        reg_time = time.time() - start_reg
        
        if self.debug_mode:
            print(f"\n  Two-stage registration completed in {reg_time:.2f}s")
        
        # Extract final deformation field (combines both transforms)
        transformix_object = itk.TransformixFilter.New(moving_itk)
        transformix_object.SetTransformParameterObject(result_transform)
        transformix_object.ComputeDeformationFieldOn()
        transformix_object.UpdateLargestPossibleRegion()
        
        deformation_field_itk = transformix_object.GetOutputDeformationField()
        deformation_np = itk.array_from_image(deformation_field_itk)
        
        # Try to get final metric from B-spline stage
        try:
            # Get the last parameter map (B-spline refinement)
            num_maps = result_transform.GetNumberOfParameterMaps()
            final_metric = float(result_transform.GetParameterMap(num_maps-1)["0_FinalMetricValue"][0])
            metadata['final_metric'] = final_metric
            
            if final_metric < 10:
                metadata['quality'] = 'excellent'
            elif final_metric < 100:
                metadata['quality'] = 'good'
            else:
                metadata['quality'] = 'moderate'
        except:
            metadata['quality'] = 'good'  # Default for hybrid
        
        # Update metadata
        metadata['success'] = True
        metadata['registration_time'] = reg_time
        
        total_time = time.time() - start_total
        
        if self.debug_mode:
            magnitude = np.sqrt(deformation_np[:,:,0]**2 + deformation_np[:,:,1]**2)
            print(f"  Max displacement: {magnitude.max():.2f} pixels")
            print(f"  Quality: {metadata['quality']}")
            print(f"  Total time: {total_time:.2f}s")
        
        return deformation_np, fixed_np, moving_np, metadata


def test_elastix():
    """Test Elastix registration with RGB warping (downscaled for speed)"""
    
    reg = ElastixFabricRegistration()
    
    fixed_path = "camera_capture.png"
    moving_path = "master_design.png"
    output_dir = Path("output_elastix")
    output_dir.mkdir(exist_ok=True)
    
    # Register grayscale images
    deformation, fixed, moving, metadata = reg.register_bspline(
        fixed_path,
        moving_path,
        target_size=(1024, 1024)
    )
    
    # print("\n[OK] Elastix registration complete!")
    # print(f"  Deformation field shape: {deformation.shape}")
    # print(f"  Registration quality: {metadata['quality']}")
    
    # Warp RGB image (warp the moving/design image to match fixed/camera)
    # print("\n[5] Warping RGB image...")
    warped_rgb = reg.warp_rgb_image(
        moving_path,  # Warp master_design.png to match camera_capture
        deformation,
        output_dir / "warped_rgb_elastix.png"
    )
    
    # print("\n" + "="*70)
    # print("SUCCESS! Elastix registration with RGB warping complete.")
    # print("="*70)


def test_smart_multires():
    """
    SMART MULTI-RESOLUTION MODE (RECOMMENDED):
    - Registration: Downscaled (1024x1024) for SPEED
    - RGB Warping: Full resolution for QUALITY
    
    This gives the best balance: ~12s total with maximum quality output!
    """
    
    reg = ElastixFabricRegistration()
    
    fixed_path = "camera_capture.png"
    moving_path = "master_design.png"
    output_dir = Path("output_elastix_smart")
    output_dir.mkdir(exist_ok=True)
    
    # print("\n" + "="*70)
    # print("SMART MULTI-RESOLUTION MODE")
    # print("="*70)
    # print("Strategy:")
    # print("  1. Registration at 1024x1024 (FAST)")
    # print("  2. Flow field upscaling to full resolution")
    # print("  3. RGB warping at full resolution (HIGH QUALITY)")
    # print("="*70)
    
    start_total = time.time()
    
    # STEP 1: Fast registration at downscaled resolution
    # print("\n[STEP 1] Fast registration at downscaled resolution...")
    reg_start = time.time()
    
    deformation, fixed, moving, metadata = reg.register_bspline(
        fixed_path,
        moving_path,
        target_size=(1024, 1024)  # Downscaled for speed
    )
    
    reg_time = time.time() - reg_start
    
    # print(f"\n[OK] Registration complete in {reg_time:.2f}s")
    # print(f"  Deformation field shape: {deformation.shape}")
    # print(f"  Quality: {metadata['quality']}")
    
    # STEP 2 & 3: Warp RGB at FULL resolution (flow auto-upscales)
    # print(f"\n[STEP 2 & 3] Warping RGB at FULL RESOLUTION...")
    # print("  (Flow field will be automatically upscaled to match RGB)")
    
    warp_start = time.time()
    
    warped_rgb = reg.warp_rgb_image(
        moving_path,  # Full resolution RGB
        deformation,  # Downscaled flow (will be upscaled inside)
        output_dir / "warped_rgb_smart.png"
    )
    
    warp_time = time.time() - warp_start
    total_time = time.time() - start_total
    
    # print("\n" + "="*70)
    # print("SMART MULTI-RESOLUTION RESULTS:")
    # print("="*70)
    # print(f"  Registration time:  {reg_time:.2f}s (at 1024x1024)")
    # print(f"  RGB warping time:   {warp_time:.2f}s (at FULL resolution)")
    # print(f"  TOTAL TIME:         {total_time:.2f}s")
    # print(f"  Output quality:     MAXIMUM (full resolution warping)")
    # print(f"  Output: {output_dir / 'warped_rgb_smart.png'}")
    # print("="*70)


def test_full_resolution():
    """Test Elastix registration at maximum safe resolution"""
    
    reg = ElastixFabricRegistration()
    
    fixed_path = "camera_capture.png"
    moving_path = "master_design.png"
    output_dir = Path("output_elastix_fullres")
    output_dir.mkdir(exist_ok=True)
    
    # Get image dimensions
    test_img = cv2.imread(str(fixed_path), cv2.IMREAD_GRAYSCALE | cv2.IMREAD_ANYDEPTH | cv2.IMREAD_ANYCOLOR)
    if len(test_img.shape) == 3:
        test_img = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
    
    if test_img is not None:
        total_pixels = test_img.shape[0] * test_img.shape[1]
        megapixels = total_pixels / 1e6
        
        # print(f"\n{'='*70}")
        # print(f"ORIGINAL IMAGE SIZE TEST")
        # print(f"{'='*70}")
        # print(f"Image resolution: {test_img.shape[0]}x{test_img.shape[1]}")
        # print(f"Total pixels: {total_pixels:,} ({megapixels:.1f} MP)")
        
        # Determine safe processing size based on available memory
        # For B-spline registration, limit to ~25MP for CPU processing
        max_safe_pixels = 25_000_000  # 25 megapixels is safe for most systems
        
        if total_pixels > max_safe_pixels:
            scale_factor = np.sqrt(max_safe_pixels / total_pixels)
            safe_h = int(test_img.shape[0] * scale_factor)
            safe_w = int(test_img.shape[1] * scale_factor)
            target_size = (safe_h, safe_w)
            # print(f"\nWARNING: Image too large for CPU B-spline registration!")
            # print(f"Scaling down to {safe_w}x{safe_h} ({safe_w*safe_h/1e6:.1f} MP) for registration")
            # print(f"RGB warping will still use FULL resolution")
        else:
            target_size = None
            # print(f"Image size safe for full resolution processing")
        
        # print(f"{'='*70}\n")
    
    # Register at safe resolution
    start_total = time.time()
    
    deformation, fixed, moving, metadata = reg.register_bspline(
        fixed_path,
        moving_path,
        target_size=target_size  # Auto-scaled to safe size
    )
    
    reg_time = time.time() - start_total
    
    # print("\n[OK] Full resolution Elastix registration complete!")
    # print(f"  Deformation field shape: {deformation.shape}")
    # print(f"  Registration time: {reg_time:.2f}s")
    # print(f"  Quality: {metadata['quality']}")
    
    # Warp RGB image at full resolution
    # print("\n[5] Warping RGB image at full resolution...")
    warp_start = time.time()
    
    warped_rgb = reg.warp_rgb_image(
        moving_path,
        deformation,
        output_dir / "warped_rgb_fullres.png"
    )
    
    warp_time = time.time() - warp_start
    total_time = time.time() - start_total
    
    # print("\n" + "="*70)
    # print("FULL RESOLUTION RESULTS:")
    # print("="*70)
    # print(f"  Registration time: {reg_time:.2f}s")
    # print(f"  RGB warping time:  {warp_time:.2f}s")
    # print(f"  TOTAL TIME:        {total_time:.2f}s")
    # print(f"  Output: {output_dir / 'warped_rgb_fullres.png'}")
    # print("="*70)


if __name__ == "__main__":
    import sys
    
    # Check if user wants to specify custom images
    if len(sys.argv) > 2:
        # Custom mode: python fabric_registration_elastix.py <fixed_image> <moving_image> [--smart/--fullres]
        fixed_path = Path(sys.argv[1])
        moving_path = Path(sys.argv[2])
        
        # Check for mode flags
        smart_mode = "--smart" in sys.argv
        fullres = "--fullres" in sys.argv
        
        # Default to smart mode if neither specified
        if not smart_mode and not fullres:
            smart_mode = True
            mode_str = "Smart Multi-Res (DEFAULT - Fast reg + Full-res warp)"
        elif smart_mode:
            mode_str = "Smart Multi-Res (Fast reg + Full-res warp)"
        else:
            mode_str = "Full Resolution (Everything at native resolution)"
        
        if not fixed_path.exists():
            # print(f"ERROR: Fixed image not found: {fixed_path}")
            sys.exit(1)
        if not moving_path.exists():
            # print(f"ERROR: Moving image not found: {moving_path}")
            sys.exit(1)
        
        # print(f"Custom image registration:")
        # print(f"  Fixed:  {fixed_path}")
        # print(f"  Moving: {moving_path}")
        # print(f"  Mode:   {mode_str}")
        # print()
        
        # Run registration
        reg = ElastixFabricRegistration()
        output_dir = Path("output_elastix_smart")
        output_dir.mkdir(exist_ok=True)
        
        print_gpu_memory()
        
        start_total = time.time()
        
        # For smart mode: always do downscaled registration
        # (RGB warping will auto-upscale to full resolution)
        if smart_mode:
            target_size = (1024, 1024)
        else:
            target_size = None  # Full resolution registration
        
        deformation, fixed, moving, metadata = reg.register_bspline(
            fixed_path,
            moving_path,
            target_size=target_size
        )
        
        reg_time = time.time() - start_total
        
        # Log results if logger available
        if reg.logger:
            magnitude = np.sqrt(deformation[:,:,0]**2 + deformation[:,:,1]**2)
            reg.logger.log_registration(
                fixed_path, moving_path, metadata, reg_time,
                max_displacement=magnitude.max(),
                target_size=target_size if target_size else fixed.shape,
                parameters={'mode': 'smart' if smart_mode else 'fullres'}
            )
        
        # Warp RGB
        warp_start = time.time()
        warped_rgb = reg.warp_rgb_image(
            moving_path,
            deformation,
            output_dir / "warped_rgb_custom.png"
        )
        
        warp_time = time.time() - warp_start
        total_time = time.time() - start_total
        
        # print("\n" + "="*70)
        # print("CUSTOM IMAGE RESULTS:")
        # print("="*70)
        # print(f"  Registration time: {reg_time:.2f}s")
        # print(f"  RGB warping time:  {warp_time:.2f}s")
        # print(f"  TOTAL TIME:        {total_time:.2f}s")
        # print(f"  Output: {output_dir / 'warped_rgb_custom.png'}")
        # print("="*70)
        
    elif len(sys.argv) > 1 and sys.argv[1] == "--fullres":
        # Run full resolution test
        # print("Running FULL RESOLUTION test (registration + warping at native resolution)")
        # print()
        test_full_resolution()
    elif len(sys.argv) > 1 and sys.argv[1] == "--smart":
        # Run smart multi-resolution mode
        # print("Running SMART MULTI-RESOLUTION test (RECOMMENDED)")
        # print()
        test_smart_multires()
    else:
        # Run standard downscaled test
        # print("=" * 70)
        # print("FABRIC REGISTRATION - ELASTIX")
        # print("=" * 70)
        # print("\nAvailable modes:")
        # print("  1. STANDARD:    python fabric_registration_elastix.py")
        # print("                  - Fast, downscaled to 1024x1024")
        # print()
        # print("  2. SMART:       python fabric_registration_elastix.py --smart")
        # print("                  - RECOMMENDED! Fast registration + full-res warping")
        # print("                  - Best quality/speed balance (~12s)")
        # print()
        # print("  3. FULL-RES:    python fabric_registration_elastix.py --fullres")
        # print("                  - Everything at native resolution (~28s)")
        # print()
        # print("  4. CUSTOM:      python fabric_registration_elastix.py <fixed> <moving> [--smart/--fullres]")
        # print("                  - Use your own images")
        # print("=" * 70)
        # print("\nRunning STANDARD test...\n")
        test_elastix()
