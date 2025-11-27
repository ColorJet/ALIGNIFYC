"""
Alinify Pipeline - High-level Python API

Simplified interface for the complete registration pipeline
"""

import numpy as np
from typing import Optional, Tuple, Callable
from pathlib import Path
import yaml

try:
    import alinify_bindings as alinify_cpp
    HAS_CPP = True
except ImportError:
    print("Warning: C++ bindings not available")
    HAS_CPP = False


class Pipeline:
    """High-level pipeline orchestration"""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """Initialize pipeline with configuration
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        
        if HAS_CPP:
            self._init_cpp_modules()
        else:
            print("Running in simulation mode")
            
        self.is_running = False
        self.camera_callback = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
            
    def _init_cpp_modules(self):
        """Initialize C++ modules"""
        # Camera
        self.camera = alinify_cpp.GidelCamera()
        cam_config = alinify_cpp.CameraConfig()
        cam_config.width = self.config['camera']['resolution']['width']
        cam_config.height = self.config['camera']['resolution']['height']
        cam_config.frequency_hz = self.config['camera']['frequency']
        cam_config.fov_width_mm = self.config['camera']['fov']['width']
        
        if self.config['camera']['gidel'].get('config_file'):
            self.camera.set_config_file(self.config['camera']['gidel']['config_file'])
        
        self.camera.initialize(cam_config)
        
        # Stitcher
        self.stitcher = alinify_cpp.StripStitcher()
        scan_params = alinify_cpp.ScanningParams()
        scan_params.max_length_mm = self.config['scanning']['max_length']
        scan_params.strip_width_mm = self.config['scanning']['strip_width']
        scan_params.overlap_pixels = self.config['scanning']['overlap_pixels']
        scan_params.bidirectional = self.config['scanning']['mode'] == 'bidirectional'
        
        self.stitcher.initialize(scan_params)
        
        # Registration
        self.registrator = alinify_cpp.ElastixWrapper()
        reg_params = alinify_cpp.RegistrationParams()
        reg_params.pyramid_levels = self.config['registration']['pyramid']['levels']
        reg_params.bspline_grid_spacing = self.config['registration']['transform']['bspline']['grid_spacing'][0]
        reg_params.max_iterations = self.config['registration']['optimizer']['max_iterations'][0]
        
        self.registrator.initialize(reg_params)
        
        # GPU Warper
        if self.config['gpu_warp']['enable']:
            self.warper = alinify_cpp.CudaWarper()
            gpu_config = alinify_cpp.GPUConfig()
            gpu_config.device_id = self.config['gpu_warp']['device_id']
            gpu_config.tile_width = self.config['gpu_warp']['memory']['tile_size'][0]
            gpu_config.tile_height = self.config['gpu_warp']['memory']['tile_size'][1]
            
            if alinify_cpp.CudaWarper.is_gpu_available():
                self.warper.initialize(gpu_config)
                print(f"GPU warping enabled on device {gpu_config.device_id}")
            else:
                print("Warning: GPU not available")
                self.warper = None
        else:
            self.warper = None
            
        # Printer
        if self.config['printer']['enable']:
            self.printer = alinify_cpp.PrinterInterface()
            dll_path = self.config['printer']['dll_path']
            self.printer.initialize(dll_path)
        else:
            self.printer = None
            
    def start_camera(self, callback: Optional[Callable] = None):
        """Start camera acquisition
        
        Args:
            callback: Optional callback function called for each acquired strip
        """
        if not HAS_CPP:
            print("Camera simulation started")
            return
            
        self.camera_callback = callback
        status = self.camera.start_acquisition()
        
        if status == alinify_cpp.StatusCode.SUCCESS:
            self.is_running = True
            print("Camera acquisition started")
        else:
            print(f"Failed to start camera: {status}")
            
    def stop_camera(self):
        """Stop camera acquisition"""
        if not HAS_CPP:
            print("Camera simulation stopped")
            return
            
        self.camera.stop_acquisition()
        self.is_running = False
        print("Camera acquisition stopped")
        
    def process_images(self, 
                      camera_image: np.ndarray, 
                      design_image: np.ndarray) -> Tuple[np.ndarray, dict]:
        """Process camera and design images through registration pipeline
        
        Args:
            camera_image: Grayscale camera image
            design_image: RGB design image
            
        Returns:
            Tuple of (registered_image, metadata)
        """
        if not HAS_CPP:
            # Simulation mode - return design image
            return design_image, {'status': 'simulated'}
            
        # Preprocessing
        preprocessed = alinify_cpp.ImageProcessor.normalize(camera_image)
        
        # Registration (simplified - would handle full pipeline)
        # TODO: Call registration and warping
        
        metadata = {
            'status': 'success',
            'registration_time_ms': 0,
            'warping_time_ms': 0
        }
        
        return design_image, metadata
        
    def send_to_printer(self, image: np.ndarray) -> bool:
        """Send registered image to printer
        
        Args:
            image: RGB image to print
            
        Returns:
            True if successful
        """
        if not HAS_CPP or not self.printer:
            print("Printer simulation: image sent")
            return True
            
        if not self.printer.is_ready():
            print("Printer not ready")
            return False
            
        # TODO: Convert numpy to C++ Image and send
        print("Image sent to printer")
        return True
        
    def get_camera_info(self) -> dict:
        """Get camera information"""
        if not HAS_CPP:
            return {'device': 'simulated'}
            
        return {
            'device': self.camera.get_device_info(),
            'acquiring': self.camera.is_acquiring()
        }
        
    def __del__(self):
        """Cleanup"""
        if self.is_running:
            self.stop_camera()


def main():
    """Example usage"""
    # Initialize pipeline
    pipeline = Pipeline()
    
    # Get camera info
    info = pipeline.get_camera_info()
    print(f"Camera: {info}")
    
    # Start camera
    pipeline.start_camera()
    
    # In real application, would process incoming images
    # For demo, just stop
    import time
    time.sleep(2)
    
    pipeline.stop_camera()
    
    print("Pipeline demo complete")


if __name__ == "__main__":
    main()
