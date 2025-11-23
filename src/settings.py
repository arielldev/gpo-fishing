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
            
        # Save everything EXCEPT webhook settings
        preset_data = {
            'auto_purchase_enabled': auto_purchase_enabled,
            'auto_purchase_amount': getattr(self.app.amount_var, 'get', lambda: getattr(self.app, 'auto_purchase_amount', 100))() if hasattr(self.app, 'amount_var') else getattr(self.app, 'auto_purchase_amount', 100),
            'loops_per_purchase': getattr(self.app.loops_var, 'get', lambda: getattr(self.app, 'loops_per_purchase', 1))() if hasattr(self.app, 'loops_var') else getattr(self.app, 'loops_per_purchase', 1),
            'point_coords': getattr(self.app, 'point_coords', {}),
            'kp': getattr(self.app, 'kp', 0.1),
            'kd': getattr(self.app, 'kd', 0.5),
            'scan_timeout': getattr(self.app, 'scan_timeout', 15.0),
            'wait_after_loss': getattr(self.app, 'wait_after_loss', 1.0),
            'smart_check_interval': getattr(self.app, 'smart_check_interval', 15.0),
            'auto_update_enabled': getattr(self.app, 'auto_update_enabled', False),
            'dark_theme': getattr(self.app, 'dark_theme', True),
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
            
            self.app.auto_purchase_amount = preset_data.get('auto_purchase_amount', 100)
            self.app.loops_per_purchase = preset_data.get('loops_per_purchase', 1)
            self.app.point_coords = preset_data.get('point_coords', {})
            self.app.kp = preset_data.get('kp', 0.1)
            self.app.kd = preset_data.get('kd', 0.5)
            self.app.scan_timeout = preset_data.get('scan_timeout', 15.0)
            self.app.wait_after_loss = preset_data.get('wait_after_loss', 1.0)
            self.app.smart_check_interval = preset_data.get('smart_check_interval', 15.0)
            self.app.auto_update_enabled = preset_data.get('auto_update_enabled', False)
            self.app.dark_theme = preset_data.get('dark_theme', True)
            
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
            
            # Update input fields
            if hasattr(self.app, 'amount_var'):
                self.app.amount_var.set(self.app.auto_purchase_amount)
            if hasattr(self.app, 'loops_var'):
                self.app.loops_var.set(self.app.loops_per_purchase)
            if hasattr(self.app, 'webhook_url_var'):
                self.app.webhook_url_var.set(self.app.webhook_url)
            if hasattr(self.app, 'webhook_interval_var'):
                self.app.webhook_interval_var.set(self.app.webhook_interval)
            
            # Update point buttons
            if hasattr(self.app, 'point_buttons'):
                self._update_point_buttons()
            
            # Create auto_purchase_var for compatibility
            if hasattr(self.app, 'auto_purchase_toggle_btn') and not hasattr(self.app, 'auto_purchase_var'):
                self.app.auto_purchase_var = tk.BooleanVar()
                self.app.auto_purchase_var.set(preset_data.get('auto_purchase_enabled', False))
            
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
