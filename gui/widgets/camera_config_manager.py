"""
Camera Configuration Manager
Handles persistent camera settings and auto-restore of critical configurations
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CameraConfigManager:
    """
    Manages camera configuration persistence and validation
    
    Features:
    - Load/save XML configuration files (Gidel .gxfg format)
    - Track configuration changes
    - Auto-restore critical settings (e.g., 8-tap on power cycle)
    - Validate configuration parameters
    - Backup/restore configuration
    """
    
    def __init__(self, config_path: str = "config/camera/FGConfig.gxfg"):
        self.config_path = config_path
        self.config_backup_path = config_path + ".backup"
        self.settings_cache_path = "config/camera/camera_settings_cache.json"
        self.config_data = {}
        self.settings_cache = {}
        
        # Critical settings that should be monitored
        self.critical_settings = {
            'num_parallel_pixels': 8,  # Must be 8 for optimal line scan
            'format': 'Mono',
            'bits_per_color': 8
        }
        
        self._load_settings_cache()
        
    def load_config(self) -> Dict:
        """Load configuration from XML file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}")
                return self._get_default_config()
                
            tree = ET.parse(self.config_path)
            root = tree.getroot()
            
            config = {}
            
            # Parse CameraLink settings
            cl = root.find('CameraLink')
            if cl:
                config['num_parallel_pixels'] = int(
                    self._get_feature_value(cl, 'NumParallelPixels', '8'))
                config['num_zones'] = int(
                    self._get_feature_value(cl, 'NumZones', '1'))
                config['zones_direction'] = int(
                    self._get_feature_value(cl, 'ZonesDirection', '0'))
                config['ignore_fval'] = self._get_feature_value(
                    cl, 'IgnoreFVALMode', 'false') == 'true'
                config['ignore_dval'] = self._get_feature_value(
                    cl, 'IgnoreDVALMode', 'false') == 'true'
                config['bits_per_color'] = int(
                    self._get_feature_value(cl, 'BitsPerColor', '8'))
                config['format'] = self._get_feature_value(cl, 'Format', 'Mono')
                config['subformat'] = int(
                    self._get_feature_value(cl, 'SubFormat', '1'))
                    
            # Parse Acquisition settings
            acq = root.find('Acquisition')
            if acq:
                config['sleep_ms'] = int(
                    self._get_feature_value(acq, 'SleepMs', '0'))
                config['frame_count'] = int(
                    self._get_feature_value(acq, 'AcqFramesCnt', '0'))
                config['reverse_y'] = self._get_feature_value(
                    acq, 'ReverseYMode', 'false') == 'true'
                config['external_source'] = self._get_feature_value(
                    acq, 'ExternalSource', 'false') == 'true'
                config['roi_list_mode'] = self._get_feature_value(
                    acq, 'RoiListMode', 'false') == 'true'
                config['roi_list_path'] = self._get_feature_value(
                    acq, 'RoiListPath', '')
                config['grab_mode'] = self._get_feature_value(
                    acq, 'GrabMode', 'LatestFrame')
                config['fg_id'] = int(
                    self._get_feature_value(acq, 'FG_ID', '0'))
                    
            # Parse ROI settings
            roi = root.find('ROI')
            if roi:
                config['roi_width'] = int(
                    self._get_feature_value(roi, 'Width', '0'))
                config['roi_height'] = int(
                    self._get_feature_value(roi, 'Height', '0'))
                config['roi_offset_x'] = int(
                    self._get_feature_value(roi, 'OffsetX', '0'))
                config['roi_offset_y'] = int(
                    self._get_feature_value(roi, 'OffsetY', '0'))
                    
            # Parse Options
            opt = root.find('Options')
            if opt:
                config['output_32rgb'] = self._get_feature_value(
                    opt, 'Output32RGB10p', 'false') == 'true'
                    
            # Parse Log settings
            log = root.find('Log')
            if log:
                config['log_verbosity'] = int(
                    self._get_feature_value(log, 'LogVerbosity', '0'))
                config['log_size_mb'] = int(
                    self._get_feature_value(log, 'LogSizeMB', '5'))
                    
            self.config_data = config
            self._update_settings_cache(config)
            
            # Validate critical settings
            self._validate_critical_settings(config)
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
            
    def save_config(self, config: Dict) -> bool:
        """Save configuration to XML file"""
        try:
            # Backup existing config
            if os.path.exists(self.config_path):
                import shutil
                shutil.copy2(self.config_path, self.config_backup_path)
                logger.info(f"Backed up config to {self.config_backup_path}")
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Build XML structure
            root = ET.Element('FG')
            
            # ROI section
            roi = ET.SubElement(root, 'ROI')
            self._add_feature(roi, 'Width', str(config.get('roi_width', 0)))
            self._add_feature(roi, 'Height', str(config.get('roi_height', 0)))
            self._add_feature(roi, 'OffsetX', str(config.get('roi_offset_x', 0)))
            self._add_feature(roi, 'OffsetY', str(config.get('roi_offset_y', 0)))
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
            self._add_feature(cl, 'NumParallelPixels', 
                            str(config.get('num_parallel_pixels', 8)))
            self._add_feature(cl, 'NumZones', str(config.get('num_zones', 1)))
            self._add_feature(cl, 'ZonesDirection', 
                            str(config.get('zones_direction', 0)))
            self._add_feature(cl, 'IgnoreFVALMode', 
                            'true' if config.get('ignore_fval', False) else 'false')
            self._add_feature(cl, 'IgnoreDVALMode', 
                            'true' if config.get('ignore_dval', False) else 'false')
            self._add_feature(cl, 'BitsPerColor', 
                            str(config.get('bits_per_color', 8)))
            
            cl.append(ET.Comment('Available formats : Mono, Bayer, RGB, RGBA'))
            self._add_feature(cl, 'Format', config.get('format', 'Mono'))
            
            cl.append(ET.Comment('Available subformats for Bayer: 0-GR, 1-RG, 2-GB, 3-BG'))
            self._add_feature(cl, 'SubFormat', str(config.get('subformat', 1)))
            
            # Acquisition section
            acq = ET.SubElement(root, 'Acquisition')
            self._add_feature(acq, 'SleepMs', str(config.get('sleep_ms', 0)))
            self._add_feature(acq, 'AcqFramesCnt', str(config.get('frame_count', 0)))
            self._add_feature(acq, 'ReverseYMode', 
                            'true' if config.get('reverse_y', False) else 'false')
            self._add_feature(acq, 'ExternalSource', 
                            'true' if config.get('external_source', False) else 'false')
            self._add_feature(acq, 'RoiListMode', 
                            'true' if config.get('roi_list_mode', False) else 'false')
            self._add_feature(acq, 'RoiListPath', 
                            config.get('roi_list_path', ''))
            
            acq.append(ET.Comment('Available modes : NextFrame, LatestFrame'))
            self._add_feature(acq, 'GrabMode', config.get('grab_mode', 'LatestFrame'))
            self._add_feature(acq, 'FG_ID', str(config.get('fg_id', 0)))
            
            # Options section
            opt = ET.SubElement(root, 'Options')
            self._add_feature(opt, 'Output32RGB10p', 
                            'true' if config.get('output_32rgb', False) else 'false')
            
            # Log section
            log = ET.SubElement(root, 'Log')
            self._add_feature(log, 'LogVerbosity', 
                            str(config.get('log_verbosity', 0)))
            self._add_feature(log, 'LogSizeMB', 
                            str(config.get('log_size_mb', 5)))
            
            # Write with formatting
            self._indent(root)
            tree = ET.ElementTree(root)
            tree.write(self.config_path, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Configuration saved to {self.config_path}")
            self._update_settings_cache(config)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
            
    def check_and_restore_taps(self, current_taps: int) -> Optional[int]:
        """
        Check if tap configuration has changed and restore if needed
        
        Args:
            current_taps: Current tap configuration from camera
            
        Returns:
            Correct tap count if restore is needed, None otherwise
        """
        expected_taps = self.critical_settings['num_parallel_pixels']
        
        if current_taps != expected_taps:
            logger.warning(
                f"Tap configuration mismatch! "
                f"Current: {current_taps}, Expected: {expected_taps}")
            logger.info(f"Restoring to {expected_taps}-tap configuration...")
            return expected_taps
            
        return None
        
    def get_expected_tap_count(self) -> int:
        """Get the expected tap count from configuration"""
        return self.config_data.get('num_parallel_pixels', 
                                   self.critical_settings['num_parallel_pixels'])
                                   
    def restore_from_backup(self) -> bool:
        """Restore configuration from backup"""
        try:
            if os.path.exists(self.config_backup_path):
                import shutil
                shutil.copy2(self.config_backup_path, self.config_path)
                logger.info(f"Restored config from backup")
                self.load_config()
                return True
            else:
                logger.warning("No backup file found")
                return False
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
            
    def _get_default_config(self) -> Dict:
        """Return default configuration for line scan camera"""
        return {
            'num_parallel_pixels': 8,
            'num_zones': 1,
            'zones_direction': 0,
            'ignore_fval': False,
            'ignore_dval': False,
            'bits_per_color': 8,
            'format': 'Mono',
            'subformat': 1,
            'sleep_ms': 0,
            'frame_count': 0,
            'reverse_y': False,
            'external_source': False,
            'roi_list_mode': False,
            'roi_list_path': '',
            'grab_mode': 'LatestFrame',
            'fg_id': 0,
            'roi_width': 0,
            'roi_height': 0,
            'roi_offset_x': 0,
            'roi_offset_y': 0,
            'output_32rgb': False,
            'log_verbosity': 0,
            'log_size_mb': 5
        }
        
    def _validate_critical_settings(self, config: Dict):
        """Validate and warn about critical settings"""
        for key, expected_value in self.critical_settings.items():
            actual_value = config.get(key)
            if actual_value != expected_value:
                logger.warning(
                    f"Critical setting mismatch: {key} = {actual_value}, "
                    f"expected {expected_value}")
                    
    def _load_settings_cache(self):
        """Load cached settings"""
        try:
            if os.path.exists(self.settings_cache_path):
                with open(self.settings_cache_path, 'r') as f:
                    self.settings_cache = json.load(f)
                logger.debug(f"Loaded settings cache from {self.settings_cache_path}")
        except Exception as e:
            logger.warning(f"Could not load settings cache: {e}")
            self.settings_cache = {}
            
    def _update_settings_cache(self, config: Dict):
        """Update cached settings"""
        try:
            os.makedirs(os.path.dirname(self.settings_cache_path), exist_ok=True)
            
            self.settings_cache = {
                'last_tap_count': config.get('num_parallel_pixels', 8),
                'last_format': config.get('format', 'Mono'),
                'last_bits': config.get('bits_per_color', 8),
                'last_modified': os.path.getmtime(self.config_path) 
                    if os.path.exists(self.config_path) else 0
            }
            
            with open(self.settings_cache_path, 'w') as f:
                json.dump(self.settings_cache, f, indent=2)
                
            logger.debug(f"Updated settings cache")
        except Exception as e:
            logger.warning(f"Could not update settings cache: {e}")
            
    def _get_feature_value(self, parent, name: str, default: str = '') -> str:
        """Get feature value from XML element"""
        feature = parent.find(f".//Feature[@Name='{name}']")
        return feature.text if feature is not None and feature.text else default
        
    def _add_feature(self, parent, name: str, text: str):
        """Add feature element to XML"""
        feature = ET.SubElement(parent, 'Feature')
        feature.set('Name', name)
        feature.text = text
        return feature
        
    def _indent(self, elem, level=0):
        """Pretty print XML"""
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
