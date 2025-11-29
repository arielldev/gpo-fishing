"""
Zoom Controller for automatic zoom management
Handles zoom out and zoom in operations for optimal game view
"""

import logging
import time
from typing import Optional

try:
    import win32api
    import win32con
    ZOOM_AVAILABLE = True
except ImportError:
    ZOOM_AVAILABLE = False
    logging.warning("Zoom control not available. Install: pip install pywin32")

class ZoomController:
    """Manages automatic zoom control for the game"""
    
    def __init__(self, app=None):
        self.zoom_available = ZOOM_AVAILABLE
        self.app = app
        
        # Default settings (will be updated from app settings)
        self.zoom_settings = {
            "zoom_out_steps": 5,
            "zoom_in_steps": 3,
            "step_delay": 0.05,  # Faster steps
            "sequence_delay": 0.2  # Shorter delay between operations
        }
        self.last_zoom_time = 0
        self.zoom_cooldown = 2.0  # Longer cooldown to prevent conflicts
        self.zoom_in_progress = False  # Lock to prevent overlapping zoom operations
        
        # Load settings from app if available
        if self.app:
            self.load_settings_from_app()
        
    def is_available(self) -> bool:
        """Check if zoom control is available"""
        return self.zoom_available
    
    def load_settings_from_app(self):
        """Load zoom settings from the app"""
        if not self.app:
            return
            
        try:
            # Get settings from GUI variables
            if hasattr(self.app, 'zoom_out_var'):
                self.zoom_settings["zoom_out_steps"] = self.app.zoom_out_var.get()
            if hasattr(self.app, 'zoom_in_var'):
                self.zoom_settings["zoom_in_steps"] = self.app.zoom_in_var.get()
                
            # Get settings from loaded settings
            if hasattr(self.app, 'settings') and 'zoom_settings' in self.app.settings:
                zoom_config = self.app.settings['zoom_settings']
                self.zoom_settings["zoom_out_steps"] = zoom_config.get("zoom_out_steps", 5)
                self.zoom_settings["zoom_in_steps"] = zoom_config.get("zoom_in_steps", 3)
                self.zoom_settings["step_delay"] = zoom_config.get("step_delay", 0.05)
                self.zoom_settings["sequence_delay"] = zoom_config.get("sequence_delay", 0.2)
                self.zoom_cooldown = zoom_config.get("zoom_cooldown", 0.5)
                
            logging.info(f"Zoom settings loaded: {self.zoom_settings}")
        except Exception as e:
            logging.error(f"Failed to load zoom settings: {e}")
    
    def update_settings(self, settings: dict):
        """Update zoom settings"""
        self.zoom_settings.update(settings)
        logging.info(f"Zoom settings updated: {self.zoom_settings}")
    
    def zoom_out(self, steps: Optional[int] = None) -> bool:
        """
        Zoom out by scrolling down
        
        Args:
            steps: Number of zoom steps (uses default if None)
            
        Returns:
            True if zoom operation was performed
        """
        if not self.zoom_available:
            return False
            
        # Check cooldown and lock (allow if part of zoom sequence)
        current_time = time.time()
        if not self.zoom_in_progress and current_time - self.last_zoom_time < self.zoom_cooldown:
            return False
            
        steps = steps or self.zoom_settings["zoom_out_steps"]
        
        try:
            for i in range(steps):
                # Scroll down (negative wheel delta = zoom out)
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
                time.sleep(self.zoom_settings["step_delay"])
                
            self.last_zoom_time = current_time
            logging.info(f"Zoomed out {steps} steps")
            return True
            
        except Exception as e:
            logging.error(f"Zoom out failed: {e}")
            return False
    
    def zoom_in(self, steps: Optional[int] = None) -> bool:
        """
        Zoom in by scrolling up
        
        Args:
            steps: Number of zoom steps (uses default if None)
            
        Returns:
            True if zoom operation was performed
        """
        if not self.zoom_available:
            return False
            
        # Check cooldown and lock (allow if part of zoom sequence)
        current_time = time.time()
        if not self.zoom_in_progress and current_time - self.last_zoom_time < self.zoom_cooldown:
            return False
            
        steps = steps or self.zoom_settings["zoom_in_steps"]
        
        try:
            for i in range(steps):
                # Scroll up (positive wheel delta = zoom in)
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
                time.sleep(self.zoom_settings["step_delay"])
                
            self.last_zoom_time = current_time
            logging.info(f"Zoomed in {steps} steps")
            return True
            
        except Exception as e:
            logging.error(f"Zoom in failed: {e}")
            return False
    
    def zoom_to_optimal(self) -> bool:
        """
        Perform optimal zoom sequence: zoom out then zoom in to specific level
        Also forces optimal layout coordinates when auto zoom is enabled
        
        Returns:
            True if zoom sequence was performed
        """
        if not self.zoom_available or self.zoom_in_progress:
            return False
            
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_zoom_time < self.zoom_cooldown:
            logging.info("Zoom operation skipped - cooldown active")
            return False
            
        self.zoom_in_progress = True
        try:
            logging.info("🔍 Starting zoom sequence...")
            
            # First zoom out completely
            if self.zoom_out():
                # Wait between operations
                time.sleep(self.zoom_settings["sequence_delay"])
                
                # Then zoom in to optimal level
                zoom_success = self.zoom_in()
                
                # Force optimal layout coordinates when auto zoom is enabled
                if zoom_success and self.app:
                    self._force_optimal_layout_coordinates()
                
                self.last_zoom_time = current_time
                logging.info("✅ Zoom sequence completed")
                return zoom_success
                
        except Exception as e:
            logging.error(f"Optimal zoom sequence failed: {e}")
        finally:
            self.zoom_in_progress = False
            
        return False
    
    def _force_optimal_layout_coordinates(self):
        """Force the layout coordinates to optimal values for auto zoom mode"""
        try:
            # Check if auto zoom is enabled
            if not (hasattr(self.app, 'settings') and 
                   self.app.settings.get('zoom_settings', {}).get('auto_zoom_enabled', False)):
                return
                
            # Optimal coordinates for auto zoom mode
            optimal_layout = {
                "bar": {
                    "name": "BAR LAYOUT",
                    "color": [85, 170, 255],
                    "border_color": [0, 100, 200],
                    "area": {
                        "x": 1058,
                        "y": 377,
                        "width": 183,
                        "height": 472
                    },
                    "description": "Fishing Bar Detection"
                },
                "drop": {
                    "name": "DROP LAYOUT",
                    "color": [85, 255, 85],
                    "border_color": [0, 200, 0],
                    "area": {
                        "x": 705,
                        "y": 76,
                        "width": 497,
                        "height": 122
                    },
                    "description": "Loot Drop Recognition"
                }
            }
            
            # Update layout manager if available
            if hasattr(self.app, 'layout_manager') and self.app.layout_manager:
                self.app.layout_manager.layouts.update(optimal_layout)
                self.app.layout_manager.save_layout_settings()
                logging.info("🎯 Forced optimal layout coordinates for auto zoom mode")
                
            # Update settings
            if hasattr(self.app, 'settings'):
                self.app.settings['layout_settings'] = optimal_layout
                
        except Exception as e:
            logging.error(f"Failed to force optimal layout coordinates: {e}")
    
    def reset_zoom(self) -> bool:
        """
        Reset zoom to default level (zoom out completely)
        
        Returns:
            True if reset was performed
        """
        if not self.zoom_available:
            return False
            
        try:
            # Zoom out more steps to ensure we're at minimum zoom
            return self.zoom_out(steps=10)
            
        except Exception as e:
            logging.error(f"Zoom reset failed: {e}")
            return False
    
    def can_zoom(self) -> bool:
        """Check if zoom operation can be performed (cooldown check)"""
        current_time = time.time()
        return current_time - self.last_zoom_time >= self.zoom_cooldown
    
    def get_stats(self) -> dict:
        """Get zoom controller statistics"""
        return {
            "available": self.zoom_available,
            "settings": self.zoom_settings.copy(),
            "last_zoom_time": self.last_zoom_time,
            "cooldown": self.zoom_cooldown,
            "can_zoom": self.can_zoom()
        }