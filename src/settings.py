import json
import os
import tkinter as tk
from datetime import datetime

class SettingsManager:
    def __init__(self, app):
        self.app = app
        self.presets_dir = "presets"
        if not os.path.exists(self.presets_dir):
            os.makedirs(self.presets_dir)
    
    def auto_save(self):
        # Get auto purchase enabled state from toggle button or var
        auto_purchase_enabled = False
        if hasattr(self.app, 'auto_purchase_toggle_btn'):
            auto_purchase_enabled = self.app.auto_purchase_toggle_btn.enabled
        elif hasattr(self.app, 'auto_purchase_var'):
            auto_purchase_enabled = self.app.auto_purchase_var.get()
            
        # Get webhook settings
        webhook_enabled = False
        if hasattr(self.app, 'webhook_toggle_btn'):
            webhook_enabled = self.app.webhook_toggle_btn.enabled
        elif hasattr(self.app, 'webhook_enabled'):
            webhook_enabled = self.app.webhook_enabled
            
        # Get fruit storage settings
        fruit_storage_enabled = getattr(self.app, 'fruit_storage_enabled', True)
        if hasattr(self.app, 'fruit_storage_toggle_btn'):
            fruit_storage_enabled = self.app.fruit_storage_toggle_btn.enabled
            
        # Get zoom settings
        zoom_settings = {
            'auto_zoom_enabled': getattr(self.app, 'auto_zoom_enabled', False),
            'zoom_out_steps': getattr(self.app.zoom_out_var, 'get', lambda: 5)() if hasattr(self.app, 'zoom_out_var') else 5,
            'zoom_in_steps': getattr(self.app.zoom_in_var, 'get', lambda: 3)() if hasattr(self.app, 'zoom_in_var') else 3,
            'step_delay': getattr(self.app, 'step_delay', 0.1),
            'sequence_delay': getattr(self.app, 'sequence_delay', 0.5),
            'zoom_cooldown': getattr(self.app, 'zoom_cooldown', 2.0)
        }
        
        if hasattr(self.app, 'auto_zoom_toggle_btn'):
            zoom_settings['auto_zoom_enabled'] = self.app.auto_zoom_toggle_btn.enabled
            
        # Save all settings including webhook and theme settings
        preset_data = {
            # Auto purchase settings
            'auto_purchase_enabled': auto_purchase_enabled,
            'auto_purchase_amount': getattr(self.app.amount_var, 'get', lambda: getattr(self.app, 'auto_purchase_amount', 100))() if hasattr(self.app, 'amount_var') else getattr(self.app, 'auto_purchase_amount', 100),
            'loops_per_purchase': getattr(self.app.loops_var, 'get', lambda: getattr(self.app, 'loops_per_purchase', 1))() if hasattr(self.app, 'loops_var') else getattr(self.app, 'loops_per_purchase', 1),
            
            # Point coordinates
            'point_coords': getattr(self.app, 'point_coords', {}),
            'fruit_coords': getattr(self.app, 'fruit_coords', {}),
            'fishing_location': getattr(self.app, 'fishing_location', None),
            
            # Fruit storage settings
            'fruit_storage_enabled': fruit_storage_enabled,
            'fruit_storage_key': getattr(self.app, 'fruit_storage_key', '2'),
            'rod_key': getattr(self.app, 'rod_key', '1'),
            
            # PD Controller settings
            'kp': getattr(self.app.kp_var, 'get', lambda: getattr(self.app, 'kp', 0.1))() if hasattr(self.app, 'kp_var') else getattr(self.app, 'kp', 0.1),
            'kd': getattr(self.app.kd_var, 'get', lambda: getattr(self.app, 'kd', 0.5))() if hasattr(self.app, 'kd_var') else getattr(self.app, 'kd', 0.5),
            
            # Timeout settings
            'scan_timeout': getattr(self.app.scan_timeout_var, 'get', lambda: getattr(self.app, 'scan_timeout', 15.0))() if hasattr(self.app, 'scan_timeout_var') else getattr(self.app, 'scan_timeout', 15.0),
            'wait_after_loss': getattr(self.app, 'wait_after_loss', 1.0),
            'smart_check_interval': getattr(self.app, 'smart_check_interval', 15.0),
            
            # Webhook settings
            'webhook_url': getattr(self.app.webhook_url_var, 'get', lambda: getattr(self.app, 'webhook_url', ''))() if hasattr(self.app, 'webhook_url_var') else getattr(self.app, 'webhook_url', ''),
            'webhook_enabled': webhook_enabled,
            'webhook_interval': getattr(self.app.webhook_interval_var, 'get', lambda: getattr(self.app, 'webhook_interval', 10))() if hasattr(self.app, 'webhook_interval_var') else getattr(self.app, 'webhook_interval', 10),
            
            # Theme settings
            'dark_theme': getattr(self.app, 'dark_theme', True),
            'current_theme': getattr(self.app, 'current_theme', 'default'),
            
            # Layout settings
            'layout_settings': getattr(self.app, 'layout_settings', {}),
            
            # Zoom settings
            'zoom_settings': zoom_settings,
            
            # Other settings
            'auto_update_enabled': getattr(self.app, 'auto_update_enabled', False),
            'hotkeys': getattr(self.app, 'hotkeys', {}),
            'last_saved': datetime.now().isoformat()
        }
        
        settings_file = "default_settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
            print(f"Settings auto-saved successfully (excluding webhook settings)")
        except Exception as e:
            print(f'Error auto-saving settings: {e}')
    
    def load_basic(self):
        settings_file = "default_settings.json"
        if not os.path.exists(settings_file):
            return
            
        try:
            with open(settings_file, 'r') as f:
                preset_data = json.load(f)
            
            # Auto purchase settings
            self.app.auto_purchase_amount = preset_data.get('auto_purchase_amount', 100)
            self.app.loops_per_purchase = preset_data.get('loops_per_purchase', 1)
            
            # Convert string keys back to integers for point_coords
            loaded_coords = preset_data.get('point_coords', {})
            self.app.point_coords = {}
            for key, value in loaded_coords.items():
                try:
                    int_key = int(key)
                    self.app.point_coords[int_key] = value
                except (ValueError, TypeError):
                    pass
                    
            # Fruit coordinates
            self.app.fruit_coords = preset_data.get('fruit_coords', {})
            
            # Fishing location
            self.app.fishing_location = preset_data.get('fishing_location', None)
            
            # Fruit storage settings
            self.app.fruit_storage_enabled = preset_data.get('fruit_storage_enabled', True)
            self.app.fruit_storage_key = preset_data.get('fruit_storage_key', '2')
            self.app.rod_key = preset_data.get('rod_key', '1')
            
            # PD Controller settings
            self.app.kp = preset_data.get('kp', 0.1)
            self.app.kd = preset_data.get('kd', 0.5)
            
            # Timeout settings
            self.app.scan_timeout = preset_data.get('scan_timeout', 15.0)
            self.app.wait_after_loss = preset_data.get('wait_after_loss', 1.0)
            self.app.smart_check_interval = preset_data.get('smart_check_interval', 15.0)
            
            # Webhook settings
            self.app.webhook_url = preset_data.get('webhook_url', '')
            self.app.webhook_enabled = preset_data.get('webhook_enabled', False)
            self.app.webhook_interval = preset_data.get('webhook_interval', 10)
            
            # Theme settings
            self.app.auto_update_enabled = preset_data.get('auto_update_enabled', False)
            self.app.dark_theme = preset_data.get('dark_theme', True)
            self.app.current_theme = preset_data.get('current_theme', 'default')
            
            # Layout settings
            if 'layout_settings' in preset_data:
                self.app.layout_settings = preset_data['layout_settings']
            
            # Zoom settings
            zoom_settings = preset_data.get('zoom_settings', {})
            self.app.auto_zoom_enabled = zoom_settings.get('auto_zoom_enabled', False)
            self.app.zoom_out_steps = zoom_settings.get('zoom_out_steps', 5)
            self.app.zoom_in_steps = zoom_settings.get('zoom_in_steps', 3)
            self.app.step_delay = zoom_settings.get('step_delay', 0.1)
            self.app.sequence_delay = zoom_settings.get('sequence_delay', 0.5)
            self.app.zoom_cooldown = zoom_settings.get('zoom_cooldown', 2.0)
            
            # Load hotkeys if they exist
            if 'hotkeys' in preset_data:
                self.app.hotkeys.update(preset_data['hotkeys'])
            
        except Exception as e:
            print(f'Error loading basic settings: {e}')
    
    def load_ui(self):
        settings_file = "default_settings.json"
        if not os.path.exists(settings_file):
            return
            
        try:
            with open(settings_file, 'r') as f:
                preset_data = json.load(f)
            
            # Update toggle buttons
            if hasattr(self.app, 'auto_purchase_toggle_btn'):
                self.app.auto_purchase_toggle_btn.set_enabled(preset_data.get('auto_purchase_enabled', False))
            if hasattr(self.app, 'auto_update_btn'):
                self.app.auto_update_btn.set_enabled(self.app.auto_update_enabled)
            if hasattr(self.app, 'webhook_toggle_btn'):
                self.app.webhook_toggle_btn.set_enabled(self.app.webhook_enabled)
            if hasattr(self.app, 'fruit_storage_toggle_btn'):
                self.app.fruit_storage_toggle_btn.set_enabled(self.app.fruit_storage_enabled)
            if hasattr(self.app, 'auto_zoom_toggle_btn'):
                self.app.auto_zoom_toggle_btn.set_enabled(self.app.auto_zoom_enabled)
            
            # Update input fields
            if hasattr(self.app, 'amount_var'):
                self.app.amount_var.set(self.app.auto_purchase_amount)
            if hasattr(self.app, 'loops_var'):
                self.app.loops_var.set(self.app.loops_per_purchase)
            if hasattr(self.app, 'webhook_url_var'):
                self.app.webhook_url_var.set(self.app.webhook_url)
            if hasattr(self.app, 'webhook_interval_var'):
                self.app.webhook_interval_var.set(self.app.webhook_interval)
                
            # Update PD controller variables
            if hasattr(self.app, 'kp_var'):
                self.app.kp_var.set(self.app.kp)
            if hasattr(self.app, 'kd_var'):
                self.app.kd_var.set(self.app.kd)
                
            # Update timeout variables
            if hasattr(self.app, 'scan_timeout_var'):
                self.app.scan_timeout_var.set(self.app.scan_timeout)
                
            # Update zoom variables
            if hasattr(self.app, 'zoom_out_var'):
                self.app.zoom_out_var.set(self.app.zoom_out_steps)
            if hasattr(self.app, 'zoom_in_var'):
                self.app.zoom_in_var.set(self.app.zoom_in_steps)
            
            # Update point buttons
            if hasattr(self.app, 'point_buttons'):
                self._update_point_buttons()
                
            # Update fruit point buttons
            if hasattr(self.app, 'fruit_point_button') and 'fruit_point' in self.app.fruit_coords:
                coords = self.app.fruit_coords['fruit_point']
                self.app.fruit_point_button.config(text=f'Fruit Point: {coords}')
            if hasattr(self.app, 'bait_point_button') and 'bait_point' in self.app.fruit_coords:
                coords = self.app.fruit_coords['bait_point']
                self.app.bait_point_button.config(text=f'Bait Point: {coords}')
                
            # Update fishing location button
            if hasattr(self.app, 'fishing_location_button') and self.app.fishing_location:
                coords = self.app.fishing_location
                self.app.fishing_location_button.config(text=f'🎯 Location: {coords}')
            
            # Create auto_purchase_var for compatibility
            if hasattr(self.app, 'auto_purchase_toggle_btn') and not hasattr(self.app, 'auto_purchase_var'):
                self.app.auto_purchase_var = tk.BooleanVar()
                self.app.auto_purchase_var.set(preset_data.get('auto_purchase_enabled', False))
                
            # Update zoom controller with loaded settings
            if hasattr(self.app, 'update_zoom_controller_settings'):
                self.app.update_zoom_controller_settings()
                
            # Apply the loaded theme
            if hasattr(self.app, 'apply_theme'):
                self.app.apply_theme()
            
        except Exception as e:
            print(f'Error loading UI settings: {e}')
    
    def _update_point_buttons(self):
        for idx, coords in self.app.point_coords.items():
            if coords and idx in self.app.point_buttons:
                self.app.point_buttons[idx].config(text=f'Point {idx}: {coords}')
    
    def _update_auto_update_button(self):
        try:
            if self.app.auto_update_enabled:
                self.app.auto_update_btn.config(text='🔄 Auto Update: ON')
            else:
                self.app.auto_update_btn.config(text='🔄 Auto Update: OFF')
        except AttributeError:
            pass
