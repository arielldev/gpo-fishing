import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import threading
import keyboard
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse
import sys
import win32api
import win32con
import json
import os
import time

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from utils import ToolTip, CollapsibleFrame, GlassFrame, AnimatedButton, StatusCard, ToggleButton
from settings import SettingsManager
from overlay import OverlayManager
from webhook import WebhookManager
from updater import UpdateManager
from fishing import FishingBot

class HotkeyGUI:
    def __init__(self, root, gradient_canvas=None):
        self.root = root
        self.gradient_canvas = gradient_canvas
        self.root.title('GPO Autofish')
        self.root.attributes('-topmost', True)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.main_loop_active = False
        self.overlay_active = False
        self.main_loop_thread = None
        self.recording_hotkey = None
        self.real_area = None
        self.is_clicking = False
        self.kp = 0.1
        self.kd = 0.5
        self.previous_error = 0
        self.scan_timeout = 15.0
        self.wait_after_loss = 1.0
        self.dpi_scale = self._get_dpi_scale()
        
        base_width = 172
        base_height = 495
        self.overlay_area = {
            'x': int(100 * self.dpi_scale),
            'y': int(100 * self.dpi_scale),
            'width': int(base_width * self.dpi_scale),
            'height': int(base_height * self.dpi_scale)
        }
        
        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3', 'toggle_tray': 'f4'}
        self.purchase_counter = 0
        self.purchase_delay_after_key = 2.0
        self.purchase_click_delay = 1.0
        self.purchase_after_type_delay = 1.0
        self.fish_count = 0
        
        self.webhook_url = ""
        self.webhook_enabled = False
        self.webhook_interval = 10
        self.webhook_counter = 0
        
        self.auto_update_enabled = False
        self.silent_mode = False
        self.verbose_logging = False
        
        self.last_activity_time = time.time()
        self.last_fish_time = time.time()
        self.recovery_enabled = True
        self.smart_check_interval = 15.0
        self.last_smart_check = time.time()
        self.recovery_count = 0
        self.last_recovery_time = 0
        
        self.current_state = "idle"
        self.state_start_time = time.time()
        self.state_details = {}
        self.stuck_actions = []
        
        self.max_state_duration = {
            "fishing": 50.0,
            "purchasing": 60.0,
            "casting": 15.0,
            "menu_opening": 10.0,
            "typing": 8.0,
            "clicking": 5.0,
            "idle": 45.0
        }
        
        self.dev_mode = False
        self.start_time = None
        self.pause_time = None
        self.total_paused_time = 0
        self.is_paused = False
        
        if 'pythonw' in sys.executable.lower():
            self.silent_mode = True
        
        self.dark_theme = False
        self.tray_icon = None
        self.collapsible_sections = {}
        
        self.point_buttons = {}
        self.point_coords = {1: None, 2: None, 3: None, 4: None}
        
        self.settings_manager = SettingsManager(self)
        self.overlay_manager = OverlayManager(self)
        self.webhook_manager = WebhookManager(self)
        self.updater = UpdateManager(self)
        self.fishing_bot = FishingBot(self)
        
        self.settings_manager.load_basic()
        self.create_widgets()
        self.settings_manager.load_ui()
        self.apply_theme()
        self.register_hotkeys()
        
        # Better default size and scaling
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Scale based on screen size
        if screen_width >= 1920:
            default_width, default_height = 400, 800
            min_width, min_height = 550, 700
        else:
            default_width, default_height = 520, 700
            min_width, min_height = 480, 600
        
        self.root.geometry(f'{default_width}x{default_height}')
        self.root.resizable(False, False)
        self.root.update_idletasks()
        
        if TRAY_AVAILABLE:
            self.setup_system_tray()
        
        if self.auto_update_enabled:
            self.root.after(2000, lambda: threading.Thread(target=self.updater.check, daemon=True).start())
        self.root.after(5000, self.updater.start_loop)
        
        # Save settings when window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _get_dpi_scale(self):
        try:
            dpi = self.root.winfo_fpixels('1i')
            scale = dpi / 96.0
            return scale
        except:
            return 1.0
    
    def log(self, message, level="info"):
        if self.silent_mode and level == "verbose":
            return
        if not self.silent_mode or level in ["error", "important"]:
            print(message)
    
    def on_closing(self):
        """Handle window closing - save settings and cleanup"""
        try:
            # Save settings before closing
            self.settings_manager.auto_save()
            print("Settings saved on exit")
        except Exception as e:
            print(f"Error saving settings on exit: {e}")
        finally:
            # Close the application
            self.root.destroy()
    
    def create_widgets(self):
        self._create_scrollable_frame()
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        current_row = 0
        
        # Hero Section with Glassmorphism
        hero_frame = GlassFrame(self.main_frame)
        hero_frame.grid(row=current_row, column=0, sticky='ew', pady=(0, 20), padx=15)
        hero_frame.grid_columnconfigure(0, weight=1)
        
        # Animated Title with Icon
        title_frame = ctk.CTkFrame(hero_frame, fg_color="transparent")
        title_frame.pack(pady=(20, 10))
        
        # Try to load and display icon
        try:
            from PIL import Image, ImageTk
            icon_path = os.path.join(os.path.dirname(__file__), "..", "images", "icon.webp")
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
                icon_image = icon_image.resize((64, 64), Image.Resampling.LANCZOS)
                icon_photo = ImageTk.PhotoImage(icon_image)
                
                icon_label = ctk.CTkLabel(title_frame, image=icon_photo, text="")
                icon_label.image = icon_photo  # Keep a reference
                icon_label.pack(pady=(0, 10))
        except Exception as e:
            print(f"Could not load icon in UI: {e}")
        
        title = ctk.CTkLabel(
            title_frame, 
            text='GPO Autofish', 
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#1F2937"  # Dark gray for contrast on white
        )
        title.pack()
        
        subtitle = ctk.CTkLabel(
            title_frame, 
            text='• by Ariel', 
            font=ctk.CTkFont(size=13),
            text_color="#6B7280"  # Medium gray
        )
        subtitle.pack(pady=(5, 0))
        
        # Control Panel with Glass Effect
        control_panel = ctk.CTkFrame(hero_frame, fg_color="transparent")
        control_panel.pack(pady=(15, 20), padx=20, fill='x')
        
        self.auto_update_btn = ToggleButton(
            control_panel,
            text='🔄 Auto Update',
            enabled=self.auto_update_enabled,
            on_toggle=self.on_auto_update_toggle,
            width=200,
            height=40
        )
        self.auto_update_btn.pack(expand=True)  # Center the button
        
        current_row += 1
        
        # Status Dashboard with Animated Cards
        status_container = GlassFrame(self.main_frame)
        status_container.grid(row=current_row, column=0, sticky='ew', pady=(0, 20), padx=15)
        
        status_grid = ctk.CTkFrame(status_container, fg_color="transparent")
        status_grid.pack(pady=15, padx=15, fill='both')
        status_grid.grid_columnconfigure((0, 1), weight=1)
        
        self.loop_status_card = StatusCard(
            status_grid,
            title="MAIN LOOP",
            value="OFF",
            icon="●"
        )
        self.loop_status_card.grid(row=0, column=0, padx=(0, 8), pady=8, sticky='ew')
        
        self.overlay_status_card = StatusCard(
            status_grid,
            title="OVERLAY",
            value="OFF",
            icon="◆"
        )
        self.overlay_status_card.grid(row=0, column=1, padx=(8, 0), pady=8, sticky='ew')
        
        self.fish_counter_card = StatusCard(
            status_grid,
            title="FISH CAUGHT",
            value="0",
            icon="🐟"
        )
        self.fish_counter_card.grid(row=1, column=0, padx=(0, 8), pady=8, sticky='ew')
        
        self.runtime_card = StatusCard(
            status_grid,
            title="RUNTIME",
            value="00:00:00",
            icon="⏱️"
        )
        self.runtime_card.grid(row=1, column=1, padx=(8, 0), pady=8, sticky='ew')
        
        current_row += 1
        
        # Collapsible Sections with Icons
        self._create_auto_purchase_section(current_row)
        current_row += 1
        
        self._create_pd_controller_section(current_row)
        current_row += 1
        
        self._create_timing_section(current_row)
        current_row += 1
        
        self._create_presets_section(current_row)
        current_row += 1
        
        self._create_hotkeys_section(current_row)
        current_row += 1
        
        self._create_webhook_section(current_row)
        current_row += 1
        
        # Discord Section with Glass Effect
        self._create_discord_section(current_row)
        current_row += 1
        
        # Enhanced Status Footer
        status_frame = GlassFrame(self.main_frame)
        status_frame.grid(row=current_row, column=0, sticky='ew', pady=(0, 15), padx=15)
        
        # Status container with proper padding and alignment
        status_container = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_container.pack(fill='x', pady=15, padx=20)
        
        # Status icon and message container
        self.status_content = ctk.CTkFrame(status_container, fg_color="#F8F9FA", corner_radius=12, border_width=2, border_color="#E5E7EB")
        self.status_content.pack(fill='x')
        
        # Status icon
        self.status_icon = ctk.CTkLabel(
            self.status_content,
            text='🎣',
            font=ctk.CTkFont(size=20),
            width=40,
            text_color="#1F2937"
        )
        self.status_icon.pack(side='left', padx=(15, 10), pady=12)
        
        # Status message with better typography - CENTERED
        self.status_msg = ctk.CTkLabel(
            self.status_content,
            text='Ready to fish!',
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#1F2937",
            anchor='center'  # Center the text
        )
        self.status_msg.pack(side='left', fill='x', expand=True, pady=12, padx=(0, 15))
    
    def update_status(self, message, status_type="info", icon="🎣"):
        """Update status message with enhanced styling"""
        # Status type colors
        status_colors = {
            "success": {"bg": "#DCFCE7", "border": "#22C55E", "text": "#15803D"},
            "error": {"bg": "#FEE2E2", "border": "#EF4444", "text": "#DC2626"},
            "warning": {"bg": "#FEF3C7", "border": "#F59E0B", "text": "#D97706"},
            "info": {"bg": "#F8F9FA", "border": "#E5E7EB", "text": "#1F2937"}
        }
        
        colors = status_colors.get(status_type, status_colors["info"])
        
        # Update the status container colors
        self.status_content.configure(
            fg_color=colors["bg"],
            border_color=colors["border"]
        )
        
        # Update icon and message
        self.status_icon.configure(text=icon, text_color=colors["text"])
        self.status_msg.configure(text=message, text_color=colors["text"])
    
    def _create_scrollable_frame(self):
        # Set dark red background for the main window
        self.root.configure(fg_color="#DC2626")  # Consistent dark red
        
        self.main_container = ctk.CTkFrame(self.root, fg_color="#DC2626")  # Dark red background
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="#DC2626",  # Dark red background
            scrollbar_button_color=("#FFFFFF", "#F3F4F6"),  # White scrollbar
            scrollbar_button_hover_color=("#E5E7EB", "#D1D5DB")  # Light gray hover
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.main_frame = self.scrollable_frame
    
    def auto_save_settings(self):
        self.settings_manager.auto_save()

    def _create_auto_purchase_section(self, start_row):
        section = CollapsibleFrame(self.main_frame, "Auto Purchase Settings", start_row, icon="🛒")
        self.collapsible_sections['auto_purchase'] = section
        frame = section.get_content_frame()
        
        # Active Toggle
        toggle_container = ctk.CTkFrame(frame, fg_color="transparent")
        toggle_container.pack(fill='x', pady=8)
        
        self.auto_purchase_toggle_btn = ToggleButton(
            toggle_container,
            text='🛒 Auto Purchase',
            enabled=False,
            on_toggle=self.on_auto_purchase_toggle,
            width=250,
            height=40
        )
        self.auto_purchase_toggle_btn.pack(expand=True)  # Center the button
        
        # Amount
        amount_frame = self._create_input_row(frame, "Amount:", 0)
        self.amount_var = tk.IntVar(value=10)
        amount_entry = ctk.CTkEntry(
            amount_frame, 
            textvariable=self.amount_var, 
            width=120,
            height=35,
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        )
        amount_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(amount_frame, "How much bait to buy each time")
        self.amount_var.trace_add('write', lambda *args: (setattr(self, 'auto_purchase_amount', self.amount_var.get()), self.auto_save_settings()))
        self.auto_purchase_amount = self.amount_var.get()
        
        # Loops per Purchase
        loops_frame = self._create_input_row(frame, "Loops per Purchase:", 0)
        self.loops_var = tk.IntVar(value=10)
        loops_entry = ctk.CTkEntry(
            loops_frame, 
            textvariable=self.loops_var, 
            width=120,
            height=35,
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        )
        loops_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(loops_frame, "Buy bait every X fish caught")
        self.loops_var.trace_add('write', lambda *args: (setattr(self, 'loops_per_purchase', self.loops_var.get()), self.auto_save_settings()))
        self.loops_per_purchase = self.loops_var.get()
        
        # Point Buttons
        tooltips = {
            1: "Click to set: yes/buy button",
            2: "Click to set: Input amount area", 
            3: "Click to set: Close button",
            4: "Click to set: Rod throw location"
        }
        
        for i in range(1, 5):
            point_frame = self._create_input_row(frame, f'Point {i}:', 0)
            self.point_buttons[i] = AnimatedButton(
                point_frame, 
                text=f'Set Point {i}', 
                command=lambda idx=i: self.capture_mouse_click(idx),
                width=180,
                height=35
            )
            self.point_buttons[i].pack(side='left', padx=(10, 5))
            self._create_help_button(point_frame, tooltips[i])
    
    def _create_pd_controller_section(self, start_row):
        section = CollapsibleFrame(self.main_frame, "PD Controller", start_row, icon="⚙️")
        section.is_expanded = False
        section.content_frame.pack_forget()
        section.toggle_btn.configure(text='+')
        self.collapsible_sections['pd_controller'] = section
        frame = section.get_content_frame()
        
        row = 0
        kp_frame = self._create_input_row(frame, "Kp (Proportional):", row)
        self.kp_var = tk.DoubleVar(value=self.kp)
        kp_entry = ctk.CTkEntry(kp_frame, textvariable=self.kp_var, width=120, height=35, corner_radius=8)
        kp_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(kp_frame, "Reaction strength to fish position")
        self.kp_var.trace_add('write', lambda *args: setattr(self, 'kp', self.kp_var.get()))
        row += 1
        
        kd_frame = self._create_input_row(frame, "Kd (Derivative):", row)
        self.kd_var = tk.DoubleVar(value=self.kd)
        kd_entry = ctk.CTkEntry(kd_frame, textvariable=self.kd_var, width=120, height=35, corner_radius=8)
        kd_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(kd_frame, "Movement smoothing factor")
        self.kd_var.trace_add('write', lambda *args: setattr(self, 'kd', self.kd_var.get()))
    
    def _create_timing_section(self, start_row):
        section = CollapsibleFrame(self.main_frame, "Timing Settings", start_row, icon="⏱️")
        section.is_expanded = False
        section.content_frame.pack_forget()
        section.toggle_btn.configure(text='+')
        self.collapsible_sections['timing'] = section
        frame = section.get_content_frame()
        
        row = 0
        timeout_frame = self._create_input_row(frame, "Scan Timeout (s):", row)
        self.timeout_var = tk.DoubleVar(value=self.scan_timeout)
        timeout_entry = ctk.CTkEntry(timeout_frame, textvariable=self.timeout_var, width=120, height=35, corner_radius=8)
        timeout_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(timeout_frame, "Wait time before recasting")
        self.timeout_var.trace_add('write', lambda *args: setattr(self, 'scan_timeout', self.timeout_var.get()))
        row += 1
        
        wait_frame = self._create_input_row(frame, "Wait After Loss (s):", row)
        self.wait_var = tk.DoubleVar(value=self.wait_after_loss)
        wait_entry = ctk.CTkEntry(wait_frame, textvariable=self.wait_var, width=120, height=35, corner_radius=8)
        wait_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(wait_frame, "Pause after losing fish")
        self.wait_var.trace_add('write', lambda *args: setattr(self, 'wait_after_loss', self.wait_var.get()))
    
    def _create_presets_section(self, start_row):
        section = CollapsibleFrame(self.main_frame, "Presets", start_row, icon="💾")
        frame = section.get_content_frame()
        
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill='x', pady=8)
        button_frame.grid_columnconfigure((0, 1), weight=1)
        
        save_btn = AnimatedButton(
            button_frame, 
            text='💾 Save Preset', 
            command=self.save_preset,
            width=200,
            height=40
        )
        save_btn.grid(row=0, column=0, padx=(0, 8))
        
        load_btn = AnimatedButton(
            button_frame, 
            text='📁 Load Preset', 
            command=self.load_preset,
            width=200,
            height=40
        )
        load_btn.grid(row=0, column=1, padx=(8, 0))
    
    def _create_hotkeys_section(self, start_row):
        section = CollapsibleFrame(self.main_frame, "Hotkey Bindings", start_row, icon="⌨️")
        section.is_expanded = False
        section.content_frame.pack_forget()
        section.toggle_btn.configure(text='+')
        self.collapsible_sections['hotkeys'] = section
        frame = section.get_content_frame()
        
        hotkeys_data = [
            ('toggle_loop', 'Toggle Main Loop', 'Start/stop fishing'),
            ('toggle_overlay', 'Toggle Overlay', 'Show/hide detection area'),
            ('exit', 'Exit', 'Close application'),
            ('toggle_tray', 'Toggle Tray', 'Minimize to tray')
        ]
        
        for idx, (key, label, tooltip) in enumerate(hotkeys_data):
            hotkey_container = ctk.CTkFrame(frame, fg_color="transparent")
            hotkey_container.pack(fill='x', pady=6)
            
            label_widget = ctk.CTkLabel(
                hotkey_container, 
                text=f'{label}:',
                font=ctk.CTkFont(size=12),
                width=140,
                anchor='w'
            )
            label_widget.pack(side='left', padx=(0, 10))
            
            key_label = ctk.CTkLabel(
                hotkey_container,
                text=self.hotkeys[key].upper(),
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#DC2626",  # Dark red background
                text_color="white",
                corner_radius=8,
                width=80,
                height=35
            )
            key_label.pack(side='left', padx=(0, 10))
            
            rebind_btn = AnimatedButton(
                hotkey_container,
                text='Rebind',
                command=lambda k=key: self.start_rebind(k),
                width=100,
                height=35
            )
            rebind_btn.pack(side='left')
            
            if key == 'toggle_loop':
                self.loop_key_label = key_label
                self.loop_rebind_btn = rebind_btn
            elif key == 'toggle_overlay':
                self.overlay_key_label = key_label
                self.overlay_rebind_btn = rebind_btn
            elif key == 'exit':
                self.exit_key_label = key_label
                self.exit_rebind_btn = rebind_btn
            elif key == 'toggle_tray':
                self.tray_key_label = key_label
                self.tray_rebind_btn = rebind_btn
    
    def _create_webhook_section(self, start_row):
        section = CollapsibleFrame(self.main_frame, "Discord Webhook", start_row, icon="🔗")
        self.collapsible_sections['webhook'] = section
        frame = section.get_content_frame()
        
        # Enable Toggle
        toggle_container = ctk.CTkFrame(frame, fg_color="transparent")
        toggle_container.pack(fill='x', pady=8)
        
        self.webhook_toggle_btn = ToggleButton(
            toggle_container,
            text='🔗 Discord Webhook',
            enabled=self.webhook_enabled,
            on_toggle=self.on_webhook_toggle,
            width=250,
            height=40
        )
        self.webhook_toggle_btn.pack(expand=True)  # Center the button
        
        # Webhook URL
        url_container = ctk.CTkFrame(frame, fg_color="transparent")
        url_container.pack(fill='x', pady=6)
        
        ctk.CTkLabel(
            url_container,
            text="Webhook URL:",
            font=ctk.CTkFont(size=12),
            width=160,
            anchor='w'
        ).pack(side='left')
        
        self.webhook_url_var = tk.StringVar(value=self.webhook_url)
        webhook_entry = ctk.CTkEntry(
            url_container,
            textvariable=self.webhook_url_var,
            height=35,
            corner_radius=8,
            placeholder_text="https://discord.com/api/webhooks/..."
        )
        webhook_entry.pack(side='left', fill='x', expand=True, padx=(10, 5))
        self._create_help_button(url_container, "Discord webhook URL from server settings")
        self.webhook_url_var.trace_add('write', lambda *args: (setattr(self, 'webhook_url', self.webhook_url_var.get()), self.auto_save_settings()))
        
        # Interval
        interval_container = ctk.CTkFrame(frame, fg_color="transparent")
        interval_container.pack(fill='x', pady=6)
        
        ctk.CTkLabel(
            interval_container,
            text="Send Every X Fish:",
            font=ctk.CTkFont(size=12),
            width=160,
            anchor='w'
        ).pack(side='left')
        
        self.webhook_interval_var = tk.IntVar(value=self.webhook_interval)
        interval_entry = ctk.CTkEntry(
            interval_container,
            textvariable=self.webhook_interval_var,
            width=120,
            height=35,
            corner_radius=8
        )
        interval_entry.pack(side='left', padx=(10, 5))
        self._create_help_button(interval_container, "Webhook notification frequency")
        self.webhook_interval_var.trace_add('write', lambda *args: (setattr(self, 'webhook_interval', self.webhook_interval_var.get()), self.auto_save_settings()))
        
        # Test Button
        test_btn = AnimatedButton(
            frame,
            text='🧪 Test Webhook',
            command=self.webhook_manager.test,
            width=200,
            height=40
        )
        test_btn.pack(pady=10)
    
    def _create_discord_section(self, start_row):
        discord_frame = GlassFrame(self.main_frame)
        discord_frame.grid(row=start_row, column=0, sticky='ew', pady=(0, 15), padx=15)
        
        discord_btn = AnimatedButton(
            discord_frame,
            text='💬 Join our Discord Community!',
            command=self.open_discord,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            hover_color="#B91C1C",  # Even darker red on hover
            normal_color="#DC2626"  # Dark red background
        )
        discord_btn.pack(pady=15, padx=15, fill='x')
    
    def _create_input_row(self, parent, label_text, row):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill='x', pady=6)
        
        ctk.CTkLabel(
            row_frame,
            text=label_text,
            font=ctk.CTkFont(size=12),
            width=160,
            anchor='w'
        ).pack(side='left')
        
        return row_frame
    
    def _create_help_button(self, parent, tooltip_text):
        help_btn = ctk.CTkButton(
            parent,
            text='💡',  # Light bulb icon for better visibility
            width=35,
            height=35,
            corner_radius=17,
            fg_color="#3B82F6",  # Blue background for help
            hover_color="#2563EB",  # Darker blue on hover
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            border_width=2,
            border_color="#60A5FA"  # Light blue border
        )
        help_btn.pack(side='left', padx=(5, 0))
        
        # Create tooltip with a small delay to ensure button is fully initialized
        self.root.after(100, lambda: ToolTip(help_btn, tooltip_text))
        return help_btn
    
    def open_discord(self):
        import webbrowser
        try:
            webbrowser.open('https://discord.gg/5Gtsgv46ce')
            self.update_status('Opened Discord invite', 'success', '✅')
        except Exception as e:
            self.update_status(f'Error opening Discord: {e}', 'error', '❌')

    def capture_mouse_click(self, idx):
        try:
            self.status_msg.configure(text=f'🖱️ Click anywhere to set Point {idx}...', text_color='#1F2937')

            def _on_click(x, y, button, pressed):
                if pressed:
                    self.point_coords[idx] = (x, y)
                    try:
                        self.root.after(0, lambda: self.update_point_button(idx))
                        self.root.after(0, lambda: self.update_status(f'Point {idx} set: ({x}, {y})', 'success', '✅'))
                        self.root.after(0, lambda: self.auto_save_settings())
                    except Exception:
                        pass
                    return False
            
            listener = pynput_mouse.Listener(on_click=_on_click)
            listener.start()
        except Exception as e:
            try:
                self.status_msg.configure(text=f'❌ Error: {e}', text_color='#f85149')
            except Exception:
                return None
    
    def update_point_button(self, idx):
        coords = self.point_coords.get(idx)
        if coords and idx in self.point_buttons:
            self.point_buttons[idx].configure(text=f'✓ Point {idx}: ({coords[0]}, {coords[1]})')
        return None
    
    def start_rebind(self, action):
        self.recording_hotkey = action
        self.status_msg.configure(text=f'⌨️ Press a key to rebind \'{action}\'...', text_color='#1F2937')
        self.loop_rebind_btn.configure(state='disabled')
        self.overlay_rebind_btn.configure(state='disabled')
        self.exit_rebind_btn.configure(state='disabled')
        self.tray_rebind_btn.configure(state='disabled')
        listener = pynput_keyboard.Listener(on_press=self.on_key_press)
        listener.start()
    
    def on_key_press(self, key):
        if self.recording_hotkey:
            try:
                if hasattr(key, 'char') and key.char:
                    key_str = key.char.lower()
                elif hasattr(key, 'name'):
                    key_str = key.name.lower()
                else:
                    key_str = str(key).split('.')[-1].lower()
                
                self.hotkeys[self.recording_hotkey] = key_str
                
                if self.recording_hotkey == 'toggle_loop':
                    self.loop_key_label.configure(text=key_str.upper())
                elif self.recording_hotkey == 'toggle_overlay':
                    self.overlay_key_label.configure(text=key_str.upper())
                elif self.recording_hotkey == 'exit':
                    self.exit_key_label.configure(text=key_str.upper())
                elif self.recording_hotkey == 'toggle_tray':
                    self.tray_key_label.configure(text=key_str.upper())
                
                self.recording_hotkey = None
                self.loop_rebind_btn.configure(state='normal')
                self.overlay_rebind_btn.configure(state='normal')
                self.exit_rebind_btn.configure(state='normal')
                self.tray_rebind_btn.configure(state='normal')
                self.status_msg.configure(text=f'✅ Hotkey set to {key_str.upper()}', text_color='#16A34A')
                self.register_hotkeys()
                return False
            except Exception as e:
                self.status_msg.configure(text=f'❌ Error: {e}', text_color='#f85149')
                self.recording_hotkey = None
                self.loop_rebind_btn.configure(state='normal')
                self.overlay_rebind_btn.configure(state='normal')
                self.exit_rebind_btn.configure(state='normal')
                self.tray_rebind_btn.configure(state='normal')
                return False
        return False
    
    def register_hotkeys(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkeys['toggle_loop'], self.toggle_main_loop)
            keyboard.add_hotkey(self.hotkeys['toggle_overlay'], self.toggle_overlay)
            keyboard.add_hotkey(self.hotkeys['exit'], self.exit_app)
            keyboard.add_hotkey(self.hotkeys['toggle_tray'], self.toggle_tray_hotkey)
        except Exception as e:
            print(f'Error registering hotkeys: {e}')
    
    def toggle_tray_hotkey(self):
        if TRAY_AVAILABLE:
            if self.root.state() == 'withdrawn':
                self.restore_from_tray()
            else:
                self.minimize_to_tray()
        else:
            print("System tray not available")
    
    def toggle_main_loop(self):
        if not self.main_loop_active and not self.is_paused:
            self.start_fishing()
        elif self.main_loop_active and not self.is_paused:
            self.pause_fishing()
        elif not self.main_loop_active and self.is_paused:
            self.resume_fishing()
    
    def start_fishing(self):
        if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
            pts = getattr(self, 'point_coords', {})
            missing = [i for i in [1, 2, 3, 4] if not pts.get(i)]
            if missing:
                messagebox.showwarning('Auto Purchase: Points missing', f'Please set Point(s) {missing} before starting Auto Purchase.')
                return
        
        self.main_loop_active = True
        self.is_paused = False
        self.start_time = time.time()
        self.total_paused_time = 0
        self.reset_fish_counter()
        
        if self.updater.pending_update:
            self.updater.pending_update = None
        
        self.loop_status_card.update_status('ACTIVE', 'active')
        
        if self.auto_update_enabled:
            self.status_msg.configure(text='⏸️ Auto-update paused during fishing', text_color='#f0883e')
        
        self.main_loop_thread = threading.Thread(target=self.fishing_bot.run_main_loop, daemon=True)
        self.main_loop_thread.start()
        
        self.update_runtime_timer()
        self.log('🎣 Started fishing!', "important")
    
    def pause_fishing(self):
        self.main_loop_active = False
        self.is_paused = True
        self.pause_time = time.time()
        
        if self.is_clicking:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.is_clicking = False
        
        self.loop_status_card.update_status('PAUSED', 'paused')
        
        if self.updater.pending_update:
            self.root.after(1000, lambda: self.updater.show_pending())
        elif self.auto_update_enabled:
            threading.Thread(target=self.updater.check, daemon=True).start()
        
        self.log('⏸️ Fishing paused', "important")
    
    def resume_fishing(self):
        if self.pause_time:
            self.total_paused_time += time.time() - self.pause_time
            self.pause_time = None
        
        self.main_loop_active = True
        self.is_paused = False
        
        self.loop_status_card.update_status('ACTIVE', 'active')
        
        self.main_loop_thread = threading.Thread(target=self.fishing_bot.run_main_loop, daemon=True)
        self.main_loop_thread.start()
        
        self.update_runtime_timer()
        self.log('▶️ Fishing resumed', "important")
    
    def increment_fish_counter(self):
        self.fish_count += 1
        self.webhook_counter += 1
        
        self.last_fish_time = time.time()
        self.last_activity_time = time.time()
        
        try:
            self.root.after(0, lambda: self.fish_counter_card.update_value(str(self.fish_count), '#FF6B6B'))
        except Exception:
            pass
        self.log(f'🐟 Fish caught: {self.fish_count}', "important")
        
        if self.webhook_enabled and self.webhook_counter >= self.webhook_interval:
            self.webhook_manager.send_fishing_progress()
            self.webhook_counter = 0
    
    def reset_fish_counter(self):
        self.fish_count = 0
        self.webhook_counter = 0
        try:
            self.root.after(0, lambda: self.fish_counter_card.update_value('0'))
        except Exception:
            pass
    
    def update_runtime_timer(self):
        if not self.main_loop_active and not self.is_paused:
            return
            
        if self.start_time:
            current_time = time.time()
            if self.is_paused and self.pause_time:
                elapsed = (self.pause_time - self.start_time) - self.total_paused_time
            else:
                elapsed = (current_time - self.start_time) - self.total_paused_time
            
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            runtime_text = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
            
            try:
                self.root.after(0, lambda: self.runtime_card.update_value(runtime_text))
            except Exception:
                pass
        
        if self.main_loop_active or self.is_paused:
            self.root.after(1000, self.update_runtime_timer)
    
    def check_recovery_needed(self):
        if not self.recovery_enabled or not self.main_loop_active:
            return False
            
        current_time = time.time()
        
        if current_time - self.last_smart_check < 10.0:
            return False
            
        self.last_smart_check = current_time
        
        state_duration = current_time - self.state_start_time
        max_duration = self.max_state_duration.get(self.current_state, 60.0)
        
        if self.current_state == "idle" and state_duration > 30.0:
            max_duration = 30.0
        
        if state_duration > max_duration:
            stuck_info = {
                "action": self.current_state,
                "duration": state_duration,
                "max_allowed": max_duration,
                "details": self.state_details.copy(),
                "timestamp": current_time
            }
            self.stuck_actions.append(stuck_info)
            
            self.log(f'⚠️ State "{self.current_state}" stuck for {state_duration:.0f}s', "error")
            
            if self.dev_mode or self.verbose_logging:
                self.log(f'🔍 DEV: {stuck_info}', "verbose")
            
            return True
            
        time_since_activity = current_time - self.last_activity_time
        if time_since_activity > 90:
            self.log(f'⚠️ No activity for {time_since_activity:.0f}s', "error")
            return True
            
        return False
    
    def set_recovery_state(self, state, details=None):
        self.current_state = state
        self.state_start_time = time.time()
        self.last_activity_time = time.time()
        self.state_details = details or {}
        
        if self.dev_mode or self.verbose_logging:
            detail_str = f" - {details}" if details else ""
            self.log(f'🔄 State: {state}{detail_str}', "verbose")
    
    def perform_recovery(self):
        if not self.main_loop_active:
            return
            
        current_time = time.time()
        
        if current_time - self.last_recovery_time < 10:
            return
            
        self.recovery_count += 1
        self.last_recovery_time = current_time
        
        recovery_info = {
            "recovery_number": self.recovery_count,
            "stuck_state": self.current_state,
            "stuck_duration": current_time - self.state_start_time,
            "state_details": self.state_details.copy(),
            "recent_stuck_actions": self.stuck_actions[-3:] if len(self.stuck_actions) > 0 else [],
            "timestamp": current_time
        }
        
        self.log(f'🔄 Recovery #{self.recovery_count} - Restarting...', "error")
        
        self.webhook_manager.send_recovery(recovery_info)
        
        if self.is_clicking:
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.is_clicking = False
            except Exception as e:
                self.log(f'⚠️ Error releasing mouse: {e}', "error")
        
        self.last_activity_time = current_time
        self.last_fish_time = current_time
        self.set_recovery_state("idle", {"action": "recovery_reset"})
        self.stuck_actions.clear()
        
        self.main_loop_active = False
        self.loop_status_card.update_status('RECOVERING', 'error')
        threading.Event().wait(2.0)
        
        try:
            if hasattr(self, 'main_loop_thread') and self.main_loop_thread and self.main_loop_thread.is_alive():
                self.main_loop_thread.join(timeout=5.0)
        except Exception as e:
            self.log(f'⚠️ Error joining thread: {e}', "error")
        
        self.main_loop_active = True
        self.loop_status_card.update_status('ACTIVE', 'active')
        self.main_loop_thread = threading.Thread(target=self.fishing_bot.run_main_loop, daemon=True)
        self.main_loop_thread.start()
        
        self.log('✅ Recovery complete', "important")
    
    def toggle_overlay(self):
        self.overlay_active = not self.overlay_active
        if self.overlay_active:
            self.overlay_status_card.update_status('ACTIVE', 'active')
            self.overlay_manager.create()
            print(f'Overlay activated at: {self.overlay_area}')
        else:
            self.overlay_status_card.update_status('OFF', 'default')
            self.overlay_manager.destroy()
            print(f'Overlay deactivated. Saved area: {self.overlay_area}')
    
    def on_auto_update_toggle(self, enabled):
        """Callback for auto update toggle button"""
        self.auto_update_enabled = enabled
        self.auto_save_settings()
        
        if enabled:
            self.update_status('Auto Update enabled', 'success', '✅')
        else:
            self.update_status('Auto Update disabled', 'info', '🔄')
    
    def on_webhook_toggle(self, enabled):
        """Callback for webhook toggle button"""
        self.webhook_enabled = enabled
        # Note: Webhook settings are NOT saved to default_settings.json as requested
        
        if enabled:
            self.update_status('Discord Webhook enabled', 'success', '✅')
        else:
            self.update_status('Discord Webhook disabled', 'info', '🔗')
    
    def on_auto_purchase_toggle(self, enabled):
        """Callback for auto purchase toggle button"""
        # Create the auto_purchase_var if it doesn't exist for compatibility
        if not hasattr(self, 'auto_purchase_var'):
            self.auto_purchase_var = tk.BooleanVar()
        
        self.auto_purchase_var.set(enabled)
        self.auto_save_settings()
        
        if enabled:
            self.update_status('Auto Purchase enabled', 'success', '✅')
        else:
            self.update_status('Auto Purchase disabled', 'info', '🛒')
    
    def save_preset(self):
        try:
            preset_name = simpledialog.askstring("Save Preset", "Enter preset name:")
            if not preset_name:
                return
            
            import re
            preset_name = re.sub(r'[<>:"/\\|?*]', '_', preset_name)
            
            preset_data = {
                'auto_purchase_enabled': getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get() if hasattr(self, 'auto_purchase_var') else False,
                'auto_purchase_amount': getattr(self, 'auto_purchase_amount', 100),
                'loops_per_purchase': getattr(self, 'loops_per_purchase', 1),
                'point_coords': getattr(self, 'point_coords', {}),
                'kp': getattr(self, 'kp', 0.1),
                'kd': getattr(self, 'kd', 0.5),
                'scan_timeout': getattr(self, 'scan_timeout', 15.0),
                'wait_after_loss': getattr(self, 'wait_after_loss', 1.0),
                'purchase_delay_after_key': getattr(self, 'purchase_delay_after_key', 2.0),
                'purchase_click_delay': getattr(self, 'purchase_click_delay', 1.0),
                'purchase_after_type_delay': getattr(self, 'purchase_after_type_delay', 1.0),
                'overlay_area': getattr(self, 'overlay_area', {}),
                'recovery_enabled': getattr(self, 'recovery_enabled', True),
                'silent_mode': getattr(self, 'silent_mode', False),
                'verbose_logging': getattr(self, 'verbose_logging', False),
                'dark_theme': getattr(self, 'dark_theme', True),
                'auto_update_enabled': getattr(self, 'auto_update_enabled', False),
            }
            
            preset_file = os.path.join(self.settings_manager.presets_dir, f"{preset_name}.json")
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
            
            self.status_msg.configure(text=f'✅ Preset "{preset_name}" saved!', text_color='#FF6B6B')
            print(f'✅ Preset saved: {preset_file}')
            
        except Exception as e:
            self.status_msg.configure(text=f'❌ Error: {e}', text_color='#f85149')
            print(f'❌ Error saving preset: {e}')
    
    def load_preset(self):
        try:
            preset_file = filedialog.askopenfilename(
                title="Load Preset",
                initialdir=self.settings_manager.presets_dir,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not preset_file:
                return
            
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)
            
            if hasattr(self, 'auto_purchase_var'):
                self.auto_purchase_var.set(preset_data.get('auto_purchase_enabled', False))
            self.auto_purchase_amount = preset_data.get('auto_purchase_amount', 100)
            if hasattr(self, 'amount_var'):
                self.amount_var.set(self.auto_purchase_amount)
            
            self.loops_per_purchase = preset_data.get('loops_per_purchase', 1)
            if hasattr(self, 'loops_var'):
                self.loops_var.set(self.loops_per_purchase)
            
            self.point_coords = preset_data.get('point_coords', {})
            for idx in range(1, 5):
                if hasattr(self, 'point_buttons') and idx in self.point_buttons:
                    self.update_point_button(idx)
            
            self.kp = preset_data.get('kp', 0.1)
            if hasattr(self, 'kp_var'):
                self.kp_var.set(self.kp)
            
            self.kd = preset_data.get('kd', 0.5)
            if hasattr(self, 'kd_var'):
                self.kd_var.set(self.kd)
            
            self.scan_timeout = preset_data.get('scan_timeout', 15.0)
            if hasattr(self, 'timeout_var'):
                self.timeout_var.set(self.scan_timeout)
            
            self.wait_after_loss = preset_data.get('wait_after_loss', 1.0)
            if hasattr(self, 'wait_var'):
                self.wait_var.set(self.wait_after_loss)
            
            self.purchase_delay_after_key = preset_data.get('purchase_delay_after_key', 2.0)
            self.purchase_click_delay = preset_data.get('purchase_click_delay', 1.0)
            self.purchase_after_type_delay = preset_data.get('purchase_after_type_delay', 1.0)
            
            if 'overlay_area' in preset_data and preset_data['overlay_area']:
                self.overlay_area = preset_data['overlay_area']
            
            self.recovery_enabled = preset_data.get('recovery_enabled', True)
            self.silent_mode = preset_data.get('silent_mode', False)
            self.verbose_logging = preset_data.get('verbose_logging', False)
            
            new_theme = preset_data.get('dark_theme', True)
            if new_theme != self.dark_theme:
                self.dark_theme = new_theme
                self.apply_theme()
            
            self.auto_update_enabled = preset_data.get('auto_update_enabled', False)
            if hasattr(self, 'auto_update_btn'):
                self.auto_update_btn.configure(text=f'🔄 Update: {"ON" if self.auto_update_enabled else "OFF"}')
            
            preset_name = os.path.splitext(os.path.basename(preset_file))[0]
            self.status_msg.configure(text=f'✅ Preset "{preset_name}" loaded!', text_color='#FF6B6B')
            print(f'✅ Preset loaded: {preset_file}')
            
            self.auto_save_settings()
            
        except Exception as e:
            self.status_msg.configure(text=f'❌ Error: {e}', text_color='#f85149')
            print(f'❌ Error loading preset: {e}')
    
    def exit_app(self):
        print('Exiting application...')
        self.main_loop_active = False
        
        # Update status card to show stopped state
        if hasattr(self, 'loop_status_card'):
            self.loop_status_card.update_status('OFF', 'default')
        
        self.auto_save_settings()

        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        if self.overlay_manager.window is not None:
            try:
                self.overlay_manager.destroy()
            except Exception:
                pass

        try:
            keyboard.unhook_all()
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

        sys.exit(0)
    
    def setup_system_tray(self):
        try:
            image = Image.new('RGB', (64, 64), color='blue')
            draw = ImageDraw.Draw(image)
            draw.text((10, 20), "GPO", fill='white')
            
            menu = pystray.Menu(
                pystray.MenuItem("Show", self.show_from_tray),
                pystray.MenuItem("Toggle Loop", self.toggle_main_loop),
                pystray.MenuItem("Toggle Overlay", self.toggle_overlay),
                pystray.MenuItem("Exit", self.exit_app)
            )
            
            self.tray_icon = pystray.Icon("GPO Autofish", image, menu=menu)
        except Exception as e:
            print(f"Error setting up system tray: {e}")
    
    def minimize_to_tray(self):
        if self.tray_icon:
            self.root.withdraw()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        if self.tray_icon:
            self.tray_icon.stop()
    
    def restore_from_tray(self):
        self.show_from_tray()
    
    def apply_theme(self):
        # Light mode only
        ctk.set_appearance_mode("light")
