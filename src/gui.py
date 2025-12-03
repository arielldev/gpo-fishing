import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
import threading
import keyboard
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse
from tkinter import messagebox
import sys
import ctypes
import mss
import numpy as np
import win32api
import win32con
import json
import os
import time
from datetime import datetime
# Tray functionality removed - F4 now minimizes to taskbar

try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import the theme manager
try:
    from src.themes import ThemeManager
    from src.fishing import FishingBot
    from src.layout_manager import LayoutManager
except ImportError:
    from themes import ThemeManager
    from fishing import FishingBot
    from layout_manager import LayoutManager

class ToolTip:
    """Simple tooltip class for hover explanations"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes('-topmost', True)  # Force tooltip to stay on top
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("Arial", 9), wraplength=300, padx=5, pady=3)
        label.pack()
    
    def on_leave(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class CollapsibleFrame:
    """Modern collapsible frame widget with sleek styling"""
    def __init__(self, parent, title, row, columnspan=4):
        self.parent = parent
        self.title = title
        self.row = row
        self.columnspan = columnspan
        self.is_expanded = True
        
        # Main container with modern styling
        self.container = ttk.Frame(parent)
        self.container.grid(row=row, column=0, columnspan=columnspan, sticky='ew', pady=(8, 0), padx=10)
        
        # Header frame with modern card-like appearance
        self.header_frame = ttk.Frame(self.container)
        self.header_frame.pack(fill='x', pady=(0, 2))
        self.header_frame.columnconfigure(0, weight=1)  # Make title expand
        
        # Title label with modern typography (left side) - using blue section title style
        self.title_label = ttk.Label(self.header_frame, text=title, 
                                   style='SectionTitle.TLabel')
        self.title_label.grid(row=0, column=0, sticky='w', padx=(10, 0), pady=5)
        
        # Modern toggle button on the right side
        self.toggle_btn = ttk.Button(self.header_frame, text='−', width=3, 
                                   command=self.toggle, style='TButton')
        self.toggle_btn.grid(row=0, column=1, sticky='e', padx=(0, 10), pady=2)
        
        # Separator line for visual separation
        separator = ttk.Frame(self.container, height=1)
        separator.pack(fill='x', pady=(0, 8))
        
        # Content frame with padding
        self.content_frame = ttk.Frame(self.container)
        self.content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 10))
        
        # Configure grid weights for responsive design
        parent.grid_rowconfigure(row, weight=0)
        self.container.columnconfigure(0, weight=1)
        
    def toggle(self):
        """Toggle the visibility of the content frame with smooth animation"""
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text='+')
            self.is_expanded = False
        else:
            self.content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 10))
            self.toggle_btn.config(text='−')
            self.is_expanded = True
    
    def get_content_frame(self):
        """Return the content frame for adding widgets"""
        return self.content_frame

class HotkeyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('GPO Autofish')
        self.root.attributes('-topmost', True)
        
        # Set window icon
        try:
            if PIL_AVAILABLE and os.path.exists("images/icon.webp"):
                icon_image = Image.open("images/icon.webp")
                icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, icon_photo)
        except Exception as e:
            print(f"Could not set window icon: {e}")
        
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_loop_active = False

        self.main_loop_thread = None
        self.recording_hotkey = None

        self.real_area = None
        self.is_clicking = False
        self.kp = 0.1
        self.kd = 0.5
        self.previous_error = 0
        self.scan_timeout = 15.0
        self.wait_after_loss = 1.0
        self.dpi_scale = self.get_dpi_scale()

        self.hotkeys = {'toggle_loop': 'f1', 'toggle_layout': 'f2', 'exit': 'f3', 'toggle_minimize': 'f4'}
        print(f"🔧 Hotkeys initialized: {self.hotkeys}")
        self.purchase_counter = 0
        self.purchase_delay_after_key = 2.0
        self.purchase_click_delay = 1.0
        self.purchase_after_type_delay = 1.0
        self.fish_count = 0  # Track successful fishing attempts
        
        # Discord webhook settings
        self.webhook_url = ""
        self.webhook_enabled = False
        self.webhook_interval = 10  # Send webhook every X loops
        self.webhook_counter = 0  # Track loops for webhook

        
        # Fruit storage settings
        self.fruit_storage_enabled = False
        self.fruit_storage_key = '3'  # Default fruit key
        self.rod_key = '1'  # Default rod key
        self.fruit_coords = {}  # Store fruit and bait point coordinates
        
        # Update manager - will be initialized after GUI is ready
        self.update_manager = None
        
        # Performance settings
        self.silent_mode = False  # Reduce console logging
        self.verbose_logging = False  # Detailed logging for debugging
        
        # Smart Recovery System with detailed detection
        self.last_activity_time = time.time()
        self.last_fish_time = time.time()
        self.recovery_enabled = True
        self.smart_check_interval = 15.0  # Check every 15 seconds
        self.last_smart_check = time.time()
        self.recovery_count = 0
        self.last_recovery_time = 0
        
        # Advanced state tracking for smart recovery
        self.current_state = "idle"  # idle, fishing, purchasing, casting, menu_opening, typing, clicking
        self.state_start_time = time.time()
        self.state_details = {}  # Store additional state info
        self.stuck_actions = []  # Track what got stuck for logging
        
        # Smart timeouts for each specific action
        self.max_state_duration = {
            "fishing": 50.0,        # Blue bar detection (rarely gets stuck)
            "purchasing": 60.0,     # Full purchase sequence
            "casting": 15.0,        # Line casting
            "menu_opening": 10.0,   # Opening shop menu with 'E'
            "typing": 8.0,          # Typing purchase amount
            "clicking": 5.0,        # Individual clicks
            "idle": 45.0,          # Between actions
            "initial_setup": 120.0  # Initial setup with zoom and auto-purchase
        }
        
        # Dev mode logging
        self.dev_mode = False  # Will be set based on verbose_logging
        
        # Runtime tracking
        self.start_time = None
        self.pause_time = None
        self.total_paused_time = 0
        self.is_paused = False
        
        # Check if running with pythonw (silent mode)
        import sys
        if 'pythonw' in sys.executable.lower():
            self.silent_mode = True
        
        # UI/UX improvements
        self.dark_theme = True  # Default to dark theme
        self.current_theme = "default"  # Default theme

        self.collapsible_sections = {}
        self.theme_window = None
        
        # Initialize theme manager
        self.theme_manager = ThemeManager(self)
        
        # Initialize layout manager
        self.layout_manager = LayoutManager(self)
        
        # Initialize webhook manager
        try:
            from src.webhook import WebhookManager
        except ImportError:
            from webhook import WebhookManager
        self.webhook_manager = WebhookManager(self)
        
        # Initialize overlay manager
        try:
            from src.overlay import OverlayManager
        except ImportError:
            from overlay import OverlayManager
        self.overlay_manager = OverlayManager(self)
        
        # Initialize OCR manager
        try:
            from src.ocr_manager import OCRManager
        except ImportError:
            from ocr_manager import OCRManager
        self.ocr_manager = OCRManager()
        
        # Initialize zoom controller
        try:
            from src.zoom_controller import ZoomController
        except ImportError:
            from zoom_controller import ZoomController
        self.zoom_controller = ZoomController(self)
        
        # Initialize fishing bot
        self.fishing_bot = FishingBot(self)
        
        # Preset management
        self.presets_dir = "presets"
        if not os.path.exists(self.presets_dir):
            os.makedirs(self.presets_dir)
        
        # Load basic settings before creating widgets
        self.load_basic_settings()
        
        self.create_widgets()
        
        # Load UI-specific settings after widgets are created
        self.load_ui_settings()
        
        self.apply_theme()
        self.register_hotkeys()
        
        # Set compact window size with modern scrolling
        self.root.geometry('420x650')  # Increased height from 550 to 650
        self.root.resizable(True, True)
        self.root.update_idletasks()
        self.root.minsize(400, 500)  # Increased minimum height from 450 to 500
        

        
        # Initialize UpdateManager after GUI is ready
        try:
            try:
                from src.updater import UpdateManager
            except ImportError:
                from updater import UpdateManager
            self.update_manager = UpdateManager(self)
            print("✅ Simple UpdateManager initialized")
        except Exception as e:
            print(f"❌ Failed to initialize UpdateManager: {e}")
            self.update_manager = None
    
    def create_scrollable_frame(self):
        """Create a modern scrollable frame using tkinter Canvas and Scrollbar"""
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar with theme-aware colors
        canvas_bg = '#0d1117' if self.dark_theme else '#fafbfc'
        self.canvas = tk.Canvas(self.main_container, highlightthickness=0, bg=canvas_bg)
        self.scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        
        # Create the scrollable frame
        self.main_frame = ttk.Frame(self.canvas, padding='10')
        
        # Configure scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack scrollbar and canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        
        # Bind events for proper scrolling
        self.main_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        """Configure the canvas window to match the canvas width"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def log(self, message, level="info"):
        """Smart logging that respects silent mode"""
        if self.silent_mode and level == "verbose":
            return
        if not self.silent_mode or level in ["error", "important"]:
            print(message)

    def get_dpi_scale(self):
        """Get the DPI scaling factor for the current display"""  # inserted
        try:
            dpi = self.root.winfo_fpixels('1i')
            scale = dpi / 96.0
            return scale
        except:
            return 1.0

    def create_widgets(self):
        # Create scrollable main container with more width
        self.create_scrollable_frame()
        self.main_frame.columnconfigure(0, weight=1)
        
        current_row = 0
        
        # Modern header section
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=current_row, column=0, sticky='ew', pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)
        
        # Logo at the top
        try:
            if PIL_AVAILABLE and os.path.exists("images/icon.webp"):
                logo_image = Image.open("images/icon.webp")
                # Resize logo to appropriate size for header
                logo_image = logo_image.resize((64, 64), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_image)
                logo_label = ttk.Label(header_frame, image=logo_photo)
                logo_label.image = logo_photo  # Keep a reference to prevent garbage collection
                logo_label.grid(row=0, column=0, pady=(0, 10))
        except Exception as e:
            print(f"Could not load header logo: {e}")
        
        # App title with modern styling
        title = ttk.Label(header_frame, text='GPO Autofish', style='Title.TLabel')
        title.grid(row=1, column=0, pady=(0, 5))
        
        # Subtitle
        credits = ttk.Label(header_frame, text='by Ariel', 
                           style='Subtitle.TLabel')
        credits.grid(row=2, column=0, pady=(0, 15))
        
        # Modern control panel
        control_panel = ttk.Frame(header_frame)
        control_panel.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        control_panel.columnconfigure(1, weight=1)  # Center spacing
        
        # Left controls
        left_controls = ttk.Frame(control_panel)
        left_controls.grid(row=0, column=0, sticky='w')
        
        # Settings button (moved to left where theme button was)
        self.settings_btn = ttk.Button(left_controls, text='⚙️ Settings', 
                                      command=self.open_settings_window, style='TButton')
        self.settings_btn.pack(side=tk.LEFT, padx=(0, 8))
        ToolTip(self.settings_btn, "Open timing settings and theme options")
        
        # Right controls - removed Load button, only auto-save now
        right_controls = ttk.Frame(control_panel)
        right_controls.grid(row=0, column=2, sticky='e')
        
        # Manual update button
        self.update_btn = ttk.Button(right_controls, text='🔄 Update', 
                                    command=self.check_for_updates, style='TButton')
        self.update_btn.pack(side=tk.LEFT, padx=(0, 8))
        ToolTip(self.update_btn, "Check for and install updates from GitHub")
        

        
        current_row += 1
        
        # Modern status dashboard
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=current_row, column=0, sticky='ew', pady=(0, 25))
        status_frame.columnconfigure((0, 1, 2), weight=1)
        
        # Status cards - First row
        self.loop_status = ttk.Label(status_frame, text='● Main Loop: OFF', style='StatusOff.TLabel')
        self.loop_status.grid(row=0, column=0, padx=10, pady=8)
        
        self.overlay_status = ttk.Label(status_frame, text='● Overlay: OFF', style='StatusOff.TLabel')
        self.overlay_status.grid(row=0, column=1, padx=10, pady=8)
        
        self.fish_counter_label = ttk.Label(status_frame, text='Fish: 0', style='Counter.TLabel')
        self.fish_counter_label.grid(row=0, column=2, padx=10, pady=8)
        
        # Second row - Runtime only
        self.runtime_label = ttk.Label(status_frame, text='⏱️ Runtime: 00:00:00', style='Counter.TLabel')
        self.runtime_label.grid(row=1, column=0, columnspan=3, padx=10, pady=8)
        
        current_row += 1
        
        # Fishing Location Section (new)
        self.create_fishing_location_section(current_row)
        current_row += 1
        
        # Create modern collapsible sections - ordered by user priority
        
        # 1. Auto Setup - Most important for quick setup
        self.create_startup_section(current_row)
        current_row += 1
        
        # 2. Fruit Storage - Core functionality
        self.create_fruit_storage_section(current_row)
        current_row += 1
        
        # 3. Auto Purchase - Core functionality
        self.create_auto_purchase_section(current_row)
        current_row += 1
        
        # 4. Discord Webhook - Popular notifications
        self.create_webhook_section(current_row)
        current_row += 1
        
        # 5. Hotkeys - Essential controls
        self.create_hotkeys_section(current_row)
        current_row += 1
        

        

        
        # Discord join section at bottom
        self.create_discord_section(current_row)
        current_row += 1
        
        # Status message for dynamic updates
        self.status_msg = ttk.Label(self.main_frame, text='Ready to fish!', 
                                   font=('Segoe UI', 9), foreground='#58a6ff')
        self.status_msg.grid(row=current_row, column=0, pady=(10, 0))

    def create_fishing_location_section(self, start_row):
        """Create the fishing location section (non-collapsible like settings)"""
        # Create a frame similar to settings sections
        theme_colors = self.theme_manager.themes[self.current_theme]["colors"]
        
        # Main section frame
        fishing_frame = tk.LabelFrame(self.main_frame, text="🎣 Fishing Location", 
                                     bg=theme_colors["bg"], fg=theme_colors["accent"],
                                     font=('Segoe UI', 11, 'bold'), padx=20, pady=15)
        fishing_frame.grid(row=start_row, column=0, sticky='ew', pady=(0, 20), padx=10)
        
        # Initialize fishing location if not set
        if not hasattr(self, 'fishing_location'):
            self.fishing_location = None
            
        # Fishing location button
        location_label = tk.Label(fishing_frame, text="Cast Location:", 
                                 bg=theme_colors["bg"], fg=theme_colors["fg"])
        location_label.grid(row=0, column=0, sticky='w', pady=5)
        
        # Button text based on whether location is set
        button_text = f"🎯 Location: {self.fishing_location}" if self.fishing_location else "🎯 Set Fishing Location"
        
        self.fishing_location_button = tk.Button(fishing_frame, text=button_text,
                                               bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                                               command=lambda: self.capture_mouse_click('fishing_location'),
                                               width=25, relief='flat')
        self.fishing_location_button.grid(row=0, column=1, sticky='w', padx=(10, 0), pady=5)
        
        # Info text
        info_label = tk.Label(fishing_frame, 
                             text="Click to set where you want to cast your fishing rod", 
                             bg=theme_colors["bg"], fg=theme_colors["fg"],
                             font=('Segoe UI', 8))
        info_label.grid(row=1, column=0, columnspan=2, sticky='w', pady=(5, 0))
        
        fishing_frame.columnconfigure(1, weight=1)

    def update_fishing_location_colors(self):
        """Update fishing location section colors when theme changes"""
        try:
            theme_colors = self.theme_manager.themes[self.current_theme]["colors"]
            
            # Find the fishing frame by searching through main_frame children
            for child in self.main_frame.winfo_children():
                if isinstance(child, tk.LabelFrame) and "Fishing Location" in child.cget("text"):
                    # Update frame colors
                    child.configure(bg=theme_colors["bg"], fg=theme_colors["accent"])
                    
                    # Update all child widgets
                    for widget in child.winfo_children():
                        if isinstance(widget, tk.Label):
                            widget.configure(bg=theme_colors["bg"], fg=theme_colors["fg"])
                        elif isinstance(widget, tk.Button):
                            widget.configure(bg=theme_colors["button_bg"], fg=theme_colors["fg"])
                    break
        except Exception as e:
            print(f"Error updating fishing location colors: {e}")

    def update_status(self, message, status_type='info', icon='ℹ️'):
        """Update the status message with color coding"""
        try:
            theme_colors = self.theme_manager.themes[self.current_theme]["colors"]
            color_map = {
                'info': theme_colors["accent"],
                'success': theme_colors["success"],
                'error': theme_colors["error"],
                'warning': theme_colors["warning"]
            }
            color = color_map.get(status_type, theme_colors["fg"])
            self.status_msg.config(text=f'{icon} {message}', foreground=color)
        except Exception:
            # Fallback if theme system fails
            self.status_msg.config(text=f'{icon} {message}', foreground='blue')

    def capture_mouse_click(self, idx):
        """Start a listener to capture the next mouse click and store its coordinates."""  # inserted
        try:
            # Handle different point types
            if isinstance(idx, int):
                # Original auto-purchase points (1-3)
                self.status_msg.config(text=f'Click anywhere to set Point {idx}...', foreground='blue')
            elif idx == 'fruit_point':
                self.status_msg.config(text='Click anywhere to set Fruit Point...', foreground='blue')
            elif idx == 'bait_point':
                self.status_msg.config(text='Click anywhere to set Bait Point...', foreground='blue')
            elif idx == 'fishing_location':
                self.status_msg.config(text='Click anywhere to set Fishing Location...', foreground='blue')

            def _on_click(x, y, button, pressed):
                if pressed:
                    if isinstance(idx, int):
                        # Original auto-purchase points
                        self.point_coords[idx] = (x, y)
                        try:
                            self.root.after(0, lambda: self.update_point_button(idx))
                            self.root.after(0, lambda: self.status_msg.config(text=f'Point {idx} set: ({x}, {y})', foreground='green'))
                        except Exception:
                            pass
                    elif idx == 'fruit_point':
                        # Fruit storage point
                        if not hasattr(self, 'fruit_coords'):
                            self.fruit_coords = {}
                        self.fruit_coords['fruit_point'] = (x, y)
                        try:
                            # Capture variables properly in lambda
                            self.root.after(0, lambda coords=(x, y): self.fruit_point_button.config(text=f'Fruit Point: {coords}'))
                            self.root.after(0, lambda coords=(x, y): self.status_msg.config(text=f'Fruit Point set: {coords}', foreground='green'))
                        except Exception:
                            pass
                    elif idx == 'bait_point':
                        # Bait selection point
                        if not hasattr(self, 'fruit_coords'):
                            self.fruit_coords = {}
                        self.fruit_coords['bait_point'] = (x, y)
                        try:
                            # Capture variables properly in lambda
                            self.root.after(0, lambda coords=(x, y): self.bait_point_button.config(text=f'Bait Point: {coords}'))
                            self.root.after(0, lambda coords=(x, y): self.status_msg.config(text=f'Bait Point set: {coords}', foreground='green'))
                        except Exception:
                            pass
                    elif idx == 'fishing_location':
                        # Fishing location point
                        self.fishing_location = (x, y)
                        try:
                            # Capture variables properly in lambda
                            self.root.after(0, lambda coords=(x, y): self.fishing_location_button.config(text=f'🎯 Location: {coords}'))
                            self.root.after(0, lambda coords=(x, y): self.status_msg.config(text=f'Fishing Location set: {coords}', foreground='green'))
                        except Exception:
                            pass
                    
                    try:
                        self.root.after(0, lambda: self.auto_save_settings())  # Auto-save when point is set
                    except Exception as e:
                        print(f"Error auto-saving after point set: {e}")
                        pass
                    return False  # Stop listener after first click
            
            listener = pynput_mouse.Listener(on_click=_on_click)
            listener.start()
        except Exception as e:
            try:
                self.status_msg.config(text=f'Error capturing point: {e}', foreground='red')
            except Exception:
                return None

    def update_point_button(self, idx):
        coords = self.point_coords.get(idx)
        if coords and idx in self.point_buttons:
            self.point_buttons[idx].config(text=f'Point {idx}: {coords}')
        return None

    def capture_key_press(self, key_type):
        """Capture key press for fruit storage or rod selection"""
        try:
            if key_type == 'fruit':
                self.status_msg.config(text='Press a key (1-9) for Fruit Storage...', foreground='blue')
            elif key_type == 'rod':
                self.status_msg.config(text='Press a key (1-9) for Rod Selection...', foreground='blue')

            def _on_key(key):
                try:
                    # Get the character representation
                    key_char = key.char if hasattr(key, 'char') and key.char else None
                    
                    # Only accept keys 1-9
                    if key_char and key_char in '123456789':
                        if key_type == 'fruit':
                            self.fruit_storage_key = key_char
                            try:
                                self.root.after(0, lambda: self.fruit_key_button.config(text=f'Key {key_char} ✓'))
                                self.root.after(0, lambda: self.status_msg.config(text=f'Fruit key set: {key_char}', foreground='green'))
                            except Exception:
                                pass
                        elif key_type == 'rod':
                            self.rod_key = key_char
                            try:
                                self.root.after(0, lambda: self.rod_key_button.config(text=f'Key {key_char} ✓'))
                                self.root.after(0, lambda: self.status_msg.config(text=f'Rod key set: {key_char}', foreground='green'))
                            except Exception:
                                pass
                        
                        try:
                            self.root.after(0, lambda: self.auto_save_settings())
                        except Exception:
                            pass
                        return False  # Stop listener
                except Exception:
                    pass
            
            listener = pynput_keyboard.Listener(on_press=_on_key)
            listener.start()
        except Exception as e:
            try:
                self.status_msg.config(text=f'Error capturing key: {e}', foreground='red')
            except Exception:
                return None

    def _click_at(self, coords):
        """Move cursor to coords and perform a left click."""  # inserted
        try:
            x, y = (int(coords[0]), int(coords[1]))
            win32api.SetCursorPos((x, y))
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pass
        except Exception as e:
            print(f'Error clicking at {coords}: {e}')

    def _right_click_at(self, coords):
        """Move cursor to coords and perform a right click."""  # inserted
        try:
            x, y = (int(coords[0]), int(coords[1]))
            win32api.SetCursorPos((x, y))
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 1, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                threading.Event().wait(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            except Exception:
                pass
        except Exception as e:
            print(f'Error right-clicking at {coords}: {e}')

    def perform_auto_purchase_sequence(self):
        """Perform the auto-purchase sequence using saved points and amount.

Sequence (per user spec):
- press 'e', wait
- click point1, wait
- click point2, wait
- type amount, wait
- click point1, wait
- click point3, wait
- click point2, wait
- right-click point4 to close menu
"""
        from datetime import datetime
        pts = self.point_coords
        if not pts or not pts.get(1) or not pts.get(2) or not pts.get(3) or not pts.get(4):
            print('Auto purchase aborted: points not fully set (need points 1-4).')
            return
        
        # Check if main loop is still active before starting
        if not self.main_loop_active:
            print('Auto purchase aborted: main loop stopped.')
            return
        
        amount = str(self.auto_purchase_amount)
        
        # Press 'e' key with detailed state tracking
        self.set_recovery_state("menu_opening", {"action": "pressing_e_key", "amount": amount})
        self.log('Pressing E key...', "verbose")
        keyboard.press_and_release('e')
        threading.Event().wait(self.purchase_delay_after_key)
        
        if not self.main_loop_active:
            return
        
        # Click point 1 with state tracking
        self.set_recovery_state("clicking", {"action": "click_point_1", "point": pts[1]})
        self.log(f'Clicking Point 1: {pts[1]}', "verbose")
        self._click_at(pts[1])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 2 with state tracking
        self.set_recovery_state("clicking", {"action": "click_point_2", "point": pts[2]})
        self.log(f'Clicking Point 2: {pts[2]}', "verbose")
        self._click_at(pts[2])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Double-click point 2 to ensure field is focused and selected
        self.log(f'Double-clicking Point 2 to focus: {pts[2]}', "verbose")
        self._click_at(pts[2])
        threading.Event().wait(0.1)
        
        if not self.main_loop_active:
            return
        
        # Type amount with state tracking
        self.set_recovery_state("typing", {"action": "typing_amount", "amount": amount})
        self.log(f'Typing amount: {amount}', "verbose")
        # Type amount
        keyboard.write(amount)
        # Extra delay to ensure typing is complete
        threading.Event().wait(self.purchase_after_type_delay + 0.5)
        
        if not self.main_loop_active:
            return
        
        # Click point 1 again with state tracking
        self.set_recovery_state("clicking", {"action": "click_point_1_confirm", "point": pts[1]})
        print(f'Clicking Point 1: {pts[1]}')
        self._click_at(pts[1])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 3 with state tracking
        self.set_recovery_state("clicking", {"action": "click_point_3", "point": pts[3]})
        print(f'Clicking Point 3: {pts[3]}')
        self._click_at(pts[3])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 2 with state tracking
        self.set_recovery_state("clicking", {"action": "click_point_2_final", "point": pts[2]})
        print(f'Clicking Point 2: {pts[2]}')
        self._click_at(pts[2])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Right-click point 4 with state tracking
        self.set_recovery_state("clicking", {"action": "right_click_point_4", "point": pts[4]})
        print(f'Right-clicking Point 4: {pts[4]}')
        self._right_click_at(pts[4])
        threading.Event().wait(self.purchase_click_delay)
        
        # Send webhook notification for auto purchase
        self.webhook_manager.send_purchase(amount)
        print()

    def start_rebind(self, action):
        """Start recording a new hotkey"""  # inserted
        self.recording_hotkey = action
        self.status_msg.config(text=f'Press a key to rebind \'{action}\'...', foreground='blue')
        self.loop_rebind_btn.config(state='disabled')
        self.layout_rebind_btn.config(state='disabled')  # Fixed: was overlay_rebind_btn
        self.exit_rebind_btn.config(state='disabled')
        self.minimize_rebind_btn.config(state='disabled')
        listener = pynput_keyboard.Listener(on_press=self.on_key_press)
        listener.start()

    def on_key_press(self, key):
        """Handle key press during rebinding"""
        if self.recording_hotkey:
            try:
                if hasattr(key, 'char') and key.char:
                    key_str = key.char.lower()
                elif hasattr(key, 'name'):
                    key_str = key.name.lower()
                else:
                    key_str = str(key).split('.')[-1].lower()
                
                self.hotkeys[self.recording_hotkey] = key_str
                
                # Update the label
                if self.recording_hotkey == 'toggle_loop':
                    self.loop_key_label.config(text=key_str.upper())
                elif self.recording_hotkey == 'toggle_layout':
                    self.layout_key_label.config(text=key_str.upper())
                elif self.recording_hotkey == 'exit':
                    self.exit_key_label.config(text=key_str.upper())
                elif self.recording_hotkey == 'toggle_minimize':
                    self.minimize_key_label.config(text=key_str.upper())
                
                self.recording_hotkey = None
                self.loop_rebind_btn.config(state='normal')
                self.layout_rebind_btn.config(state='normal')
                self.exit_rebind_btn.config(state='normal')
                self.minimize_rebind_btn.config(state='normal')
                self.status_msg.config(text=f'Hotkey set to {key_str.upper()}', foreground='green')
                self.register_hotkeys()
                return False  # Stop the listener
            except Exception as e:
                self.status_msg.config(text=f'Error setting hotkey: {e}', foreground='red')
                self.recording_hotkey = None
                self.loop_rebind_btn.config(state='normal')
                self.layout_rebind_btn.config(state='normal')
                self.exit_rebind_btn.config(state='normal')
                self.minimize_rebind_btn.config(state='normal')
                return False
        return False

    def register_hotkeys(self):
        """Register all hotkeys"""  # inserted
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkeys['toggle_loop'], self.toggle_main_loop)
            keyboard.add_hotkey(self.hotkeys['toggle_layout'], self.toggle_layout)
            keyboard.add_hotkey(self.hotkeys['exit'], self.exit_app)
            keyboard.add_hotkey(self.hotkeys['toggle_minimize'], self.toggle_minimize_hotkey)
            print(f"✅ Hotkeys registered: {self.hotkeys}")
        except Exception as e:
            print(f'❌ Error registering hotkeys: {e}')
    
    def toggle_layout(self):
        """Toggle dual overlay mode via F2 hotkey"""
        if not hasattr(self, 'dual_overlay_active'):
            self.dual_overlay_active = False
        
        self.dual_overlay_active = not self.dual_overlay_active
        
        if self.dual_overlay_active:
            # Show both overlays
            self.show_dual_overlays()
            print("🔄 Dual overlay mode: ON (showing both bar and drop overlays)")
        else:
            # Hide both overlays
            self.hide_dual_overlays()
            print("🔄 Dual overlay mode: OFF")
    
    def show_dual_overlays(self):
        """Show both bar and drop overlays simultaneously"""
        if not hasattr(self, 'overlay_manager_bar'):
            try:
                from src.overlay import OverlayManager
            except ImportError:
                from overlay import OverlayManager
            self.overlay_manager_bar = OverlayManager(self, fixed_layout='bar')
            self.overlay_manager_drop = OverlayManager(self, fixed_layout='drop')
        
        # Create both overlays
        self.overlay_manager_bar.create()
        self.overlay_manager_drop.create()
        
        self.overlay_status.config(text='● Overlay: ON', style='StatusOn.TLabel')
    
    def hide_dual_overlays(self):
        """Hide both overlays"""
        if hasattr(self, 'overlay_manager_bar') and self.overlay_manager_bar.window:
            self.overlay_manager_bar.destroy()
        if hasattr(self, 'overlay_manager_drop') and self.overlay_manager_drop.window:
            self.overlay_manager_drop.destroy()
        
        self.overlay_status.config(text='○ Overlay: OFF', style='StatusOff.TLabel')
    
    def update_layout_display(self):
        """Update GUI to show current layout"""
        layout_info = self.layout_manager.get_layout_info()
        layout_name = layout_info['name']
        
        # Layout status removed - using overlay on/off only
    
    def toggle_minimize_hotkey(self):
        """Toggle between minimized and normal window via F4 hotkey"""
        print(f"🔧 F4 pressed - window state: {self.root.state()}")
        if self.root.state() == 'iconic':
            print("🔧 Restoring from taskbar")
            self.root.deiconify()
            self.root.lift()
        else:
            print("🔧 Minimizing to taskbar")
            self.root.iconify()
    



    def toggle_main_loop(self):
        """Toggle between Start/Pause/Resume with smart detection"""
        print(f"🔧 Toggle called - main_loop_active: {self.main_loop_active}, is_paused: {self.is_paused}")
        
        if not self.main_loop_active and not self.is_paused:
            # Starting fresh
            print("🔧 Calling start_fishing() - fresh start")
            self.start_fishing()
        elif self.main_loop_active and not self.is_paused:
            # Currently running - pause it
            print("🔧 Calling pause_fishing() - pausing active loop")
            self.pause_fishing()
        elif not self.main_loop_active and self.is_paused:
            # Currently paused - resume it
            print("🔧 Calling resume_fishing() - resuming paused loop")
            self.resume_fishing()
        else:
            print(f"🔧 Unexpected state - main_loop_active: {self.main_loop_active}, is_paused: {self.is_paused}")
    
    def start_fishing(self):
        """Start fishing from scratch"""
        # Check auto-purchase points if enabled
        if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
            pts = getattr(self, 'point_coords', {})
            missing = [i for i in [1, 2, 3] if not pts.get(i)]
            if missing:
                messagebox.showwarning('Auto Purchase: Points missing', f'Please set Point(s) {missing} before starting Auto Purchase.')
                return
        
        # Reset everything for fresh start
        self.main_loop_active = True
        self.is_paused = False
        self.start_time = time.time()
        self.total_paused_time = 0
        self.reset_fish_counter()
        
        # Update UI
        self.loop_status.config(text='● Main Loop: ACTIVE', style='StatusOn.TLabel')
        
        # Start the loop directly (no smart detection needed for fresh start)
        self.main_loop_thread = threading.Thread(target=lambda: self.fishing_bot.run_main_loop(skip_initial_setup=False), daemon=True)
        self.main_loop_thread.start()
        
        # Start runtime timer
        self.update_runtime_timer()
        
        self.log('🎣 Started fishing!', "important")
    
    def pause_fishing(self):
        """Pause the current fishing session"""
        self.main_loop_active = False
        self.is_paused = True
        self.pause_time = time.time()
        
        # Release mouse if clicking
        if self.is_clicking:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.is_clicking = False
        
        # Update UI
        self.loop_status.config(text='● Main Loop: PAUSED', style='StatusOff.TLabel')
        
        self.log('⏸️ Fishing paused', "important")
    
    def resume_fishing(self):
        """Resume fishing with smart detection"""
        # Update pause tracking
        if self.pause_time:
            self.total_paused_time += time.time() - self.pause_time
            self.pause_time = None
        
        self.main_loop_active = True
        self.is_paused = False
        
        # Update UI
        self.loop_status.config(text='● Main Loop: ACTIVE', style='StatusOn.TLabel')
        
        # Start the loop with smart detection
        self.main_loop_thread = threading.Thread(target=self.smart_resume_loop, daemon=True)
        self.main_loop_thread.start()
        
        # Resume runtime timer
        self.update_runtime_timer()
        
        self.log('▶️ Fishing resumed with smart detection', "important")
    
    def smart_resume_loop(self):
        """Resume loop with smart detection of current state"""
        import mss
        import numpy as np
        
        # Check if there's already a blue fishing bar visible
        target_color = (85, 170, 255)
        
        with mss.mss() as sct:
            # Use current layout area for screenshot
            current_area = self.layout_manager.get_layout_area(self.layout_manager.current_layout)
            if not current_area:
                current_area = {'x': 700, 'y': 400, 'width': 200, 'height': 100}  # Default bar area
            x = current_area['x']
            y = current_area['y']
            width = current_area['width']
            height = current_area['height']
            monitor = {'left': x, 'top': y, 'width': width, 'height': height}
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            
            # Look for blue fishing bar
            blue_found = False
            for row_idx in range(height):
                for col_idx in range(width):
                    b, g, r = img[row_idx, col_idx, 0:3]
                    if r == target_color[0] and g == target_color[1] and b == target_color[2]:
                        blue_found = True
                        break
                if blue_found:
                    break
        
        if blue_found:
            self.log('🎯 Blue fishing bar detected - resuming from current state', "important")
            # Jump directly into the main loop detection (skip initial setup)
            self.fishing_bot.run_main_loop(skip_initial_setup=True)
        else:
            self.log('🎣 No fishing bar detected - starting fresh', "important")
            # Start from scratch with auto-purchase check and casting
            self.fishing_bot.run_main_loop(skip_initial_setup=False)

    def increment_fish_counter(self):
        """Increment fish counter and update display"""
        self.fish_count += 1
        self.webhook_counter += 1
        
        # Update recovery tracking
        self.last_fish_time = time.time()
        self.last_activity_time = time.time()
        
        try:
            self.root.after(0, lambda: self.fish_counter_label.config(text=f'🐟 Fish: {self.fish_count}'))
        except Exception:
            pass
        self.log(f'🐟 Fish caught: {self.fish_count}', "important")
        
        # Check if we should send webhook
        if self.webhook_enabled and self.webhook_counter >= self.webhook_interval:
            self.webhook_manager.send_fishing_progress()
            self.webhook_counter = 0

    def reset_fish_counter(self):
        """Reset fish counter when main loop starts"""
        self.fish_count = 0
        self.webhook_counter = 0
        try:
            self.root.after(0, lambda: self.fish_counter_label.config(text=f'🐟 Fish: {self.fish_count}'))
        except Exception:
            pass

    def check_and_purchase(self):
        """Check if we need to auto-purchase and run sequence if needed"""  # inserted
        if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
            self.purchase_counter += 1
            loops_needed = int(getattr(self, 'loops_per_purchase', 1)) if getattr(self, 'loops_per_purchase', None) is not None else 1
            print(f'🔄 Purchase counter: {self.purchase_counter}/{loops_needed}')
            if self.purchase_counter >= max(1, loops_needed):
                try:
                    self.perform_auto_purchase_sequence()
                    self.purchase_counter = 0
                except Exception as e:
                    print(f'❌ AUTO-PURCHASE ERROR: {e}')

    def cast_line(self):
        """Perform the casting action: hold click for 1 second then release"""  # inserted
        self.log('Casting line...', "verbose")
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        threading.Event().wait(1.0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.is_clicking = False
        
        # Update activity tracking
        self.last_activity_time = time.time()
        
        self.log('Line cast', "verbose")

    def main_loop(self):
        """Main loop that runs when activated - delegates to fishing bot"""
        self.fishing_bot.run_main_loop()
    

    
    def set_recovery_state(self, state, details=None):
        """Update current state for smart recovery tracking"""
        self.current_state = state
        self.state_start_time = time.time()
        self.last_activity_time = time.time()
        self.state_details = details or {}
        
        # Dev mode state tracking
        if self.dev_mode or self.verbose_logging:
            detail_str = f" - {details}" if details else ""
            self.log(f'🔄 State: {state}{detail_str}', "verbose")
    

    
    def update_runtime_timer(self):
        """Update the runtime display"""
        if not self.main_loop_active and not self.is_paused:
            return
            
        if self.start_time:
            current_time = time.time()
            if self.is_paused and self.pause_time:
                # Currently paused - don't count pause time
                elapsed = (self.pause_time - self.start_time) - self.total_paused_time
            else:
                # Currently running - count total time minus pauses
                elapsed = (current_time - self.start_time) - self.total_paused_time
            
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            runtime_text = f'⏱️ Runtime: {hours:02d}:{minutes:02d}:{seconds:02d}'
            
            try:
                self.root.after(0, lambda: self.runtime_label.config(text=runtime_text))
            except Exception:
                pass
        
        # Schedule next update if still active
        if self.main_loop_active or self.is_paused:
            self.root.after(1000, self.update_runtime_timer)




    def exit_app(self):
        """Exit the application"""
        print('Exiting application...')
        self.main_loop_active = False
        
        # Auto-save settings before exit
        self.auto_save_settings()



        # Destroy dual overlays if they exist
        if hasattr(self, 'overlay_manager_bar') and self.overlay_manager_bar.window:
            try:
                self.overlay_manager_bar.destroy()
            except Exception:
                pass
        if hasattr(self, 'overlay_manager_drop') and self.overlay_manager_drop.window:
            try:
                self.overlay_manager_drop.destroy()
            except Exception:
                pass

        # Unhook all keyboard events
        try:
            keyboard.unhook_all()
        except Exception:
            pass

        # Destroy main root window
        try:
            self.root.destroy()
        except Exception:
            pass

        # Exit the program
        sys.exit(0)

    def create_auto_purchase_section(self, start_row):
        """Create the auto purchase collapsible section"""
        section = CollapsibleFrame(self.main_frame, "🛒 Auto Purchase Settings", start_row)
        self.collapsible_sections['auto_purchase'] = section
        frame = section.get_content_frame()
        
        # Configure frame for centering
        frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        # Auto Purchase Active
        row = 0
        ttk.Label(frame, text='Active:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.auto_purchase_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(frame, variable=self.auto_purchase_var, text='Enabled')
        auto_check.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Automatically buy bait after catching fish. Requires setting Points 1-3.")
        # Auto-save when auto-purchase is toggled
        self.auto_purchase_var.trace_add('write', lambda *args: self.auto_save_settings())
        row += 1
        
        # Purchase Amount
        ttk.Label(frame, text='Amount:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.amount_var = tk.IntVar(value=10)
        amount_spinbox = ttk.Spinbox(frame, from_=0, to=1000000, increment=1, textvariable=self.amount_var, width=10)
        amount_spinbox.grid(row=row, column=1, pady=5, sticky='w')
        # Auto-save when amount changes
        self.amount_var.trace_add('write', lambda *args: self.auto_save_settings())
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "How much bait to buy each time (e.g., 10 = buy 10 bait)")
        self.amount_var.trace_add('write', lambda *args: setattr(self, 'auto_purchase_amount', self.amount_var.get()))
        self.auto_purchase_amount = self.amount_var.get()
        row += 1
        
        # Loops per Purchase
        ttk.Label(frame, text='Loops per Purchase:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.loops_var = tk.IntVar(value=10)
        loops_spinbox = ttk.Spinbox(frame, from_=1, to=1000000, increment=1, textvariable=self.loops_var, width=10)
        loops_spinbox.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Buy bait every X fish caught (e.g., 10 = buy bait after every 10 fish)")
        self.loops_var.trace_add('write', lambda *args: setattr(self, 'loops_per_purchase', self.loops_var.get()))
        # Auto-save when loops per purchase changes
        self.loops_var.trace_add('write', lambda *args: self.auto_save_settings())
        self.loops_per_purchase = self.loops_var.get()
        row += 1
        
        # Point buttons for auto-purchase
        self.point_buttons = {}
        # Initialize point_coords only if not already set (preserve loaded values)
        if not hasattr(self, 'point_coords'):
            self.point_coords = {1: None, 2: None, 3: None}
        
        for i in range(1, 4):
            ttk.Label(frame, text=f'Point {i}:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
            self.point_buttons[i] = ttk.Button(frame, text=f'Point {i}', command=lambda idx=i: self.capture_mouse_click(idx))
            self.point_buttons[i].grid(row=row, column=1, pady=5, sticky='w')
            help_btn = ttk.Button(frame, text='?', width=3)
            help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
            
            tooltips = {
                1: "Click to set: yes/buy button (same area)",
                2: "Click to set: Input amount area (also ... area)", 
                3: "Click to set: Close button"
            }
            ToolTip(help_btn, tooltips[i])
            row += 1

    def create_fruit_storage_section(self, start_row):
        """Create the fruit storage collapsible section"""
        section = CollapsibleFrame(self.main_frame, "🍎 Fruit Storage Settings", start_row)
        self.collapsible_sections['fruit_storage'] = section
        frame = section.get_content_frame()
        
        # Configure frame for centering like auto purchase
        frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        row = 0
        
        # Fruit storage enabled checkbox
        ttk.Label(frame, text='Active:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.fruit_storage_var = tk.BooleanVar(value=getattr(self, 'fruit_storage_enabled', False))
        fruit_check = ttk.Checkbutton(frame, variable=self.fruit_storage_var, text='Enabled')
        fruit_check.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Automatically store fruits in inventory slot after fishing")
        self.fruit_storage_var.trace_add('write', lambda *args: (setattr(self, 'fruit_storage_enabled', self.fruit_storage_var.get()), self.auto_save_settings()))
        row += 1
        
        # Fruit storage key
        ttk.Label(frame, text='Fruit Key:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.fruit_key_var = tk.IntVar(value=int(getattr(self, 'fruit_storage_key', '3')))
        fruit_key_spinbox = ttk.Spinbox(frame, from_=1, to=9, increment=1, textvariable=self.fruit_key_var, width=10)
        fruit_key_spinbox.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Select which key (1-9) to press for fruit storage")
        self.fruit_key_var.trace_add('write', lambda *args: (setattr(self, 'fruit_storage_key', str(self.fruit_key_var.get())), self.auto_save_settings()))
        row += 1
        
        # Fruit point
        ttk.Label(frame, text='Fruit Point:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.fruit_point_button = ttk.Button(frame, text='Fruit Point',
                                            command=lambda: self.capture_mouse_click('fruit_point'))
        self.fruit_point_button.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Click to set where to click for fruit selection")
        row += 1
        
        # Rod key
        ttk.Label(frame, text='Rod Key:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.rod_key_var = tk.IntVar(value=int(getattr(self, 'rod_key', '1')))
        rod_key_spinbox = ttk.Spinbox(frame, from_=1, to=9, increment=1, textvariable=self.rod_key_var, width=10)
        rod_key_spinbox.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Select which key (1-9) to press for rod selection")
        self.rod_key_var.trace_add('write', lambda *args: (setattr(self, 'rod_key', str(self.rod_key_var.get())), self.auto_save_settings()))
        row += 1
        
        # Bait point
        ttk.Label(frame, text='Bait Point:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.bait_point_button = ttk.Button(frame, text='Bait Point',
                                           command=lambda: self.capture_mouse_click('bait_point'))
        self.bait_point_button.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Click to set where to click for bait selection")





    def create_hotkeys_section(self, start_row):
        """Create the hotkey bindings collapsible section"""
        section = CollapsibleFrame(self.main_frame, "⌨️ Hotkey Bindings", start_row)
        # Start collapsed by default
        section.is_expanded = False
        section.content_frame.pack_forget()
        section.toggle_btn.config(text='+')
        self.collapsible_sections['hotkeys'] = section
        frame = section.get_content_frame()
        
        # Configure frame for centering
        frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        row = 0
        ttk.Label(frame, text='Toggle Main Loop:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.loop_key_label = ttk.Label(frame, text=self.hotkeys['toggle_loop'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.loop_key_label.grid(row=row, column=1, pady=5)
        self.loop_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_loop'))
        self.loop_rebind_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Start/stop the fishing bot")
        row += 1
        
        ttk.Label(frame, text='Toggle Layout:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.layout_key_label = ttk.Label(frame, text=self.hotkeys['toggle_layout'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.layout_key_label.grid(row=row, column=1, pady=5)
        self.layout_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_layout'))
        self.layout_rebind_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Switch between Bar Layout (blue) and Drop Layout (green)")
        row += 1
        

        
        ttk.Label(frame, text='Exit:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.exit_key_label = ttk.Label(frame, text=self.hotkeys['exit'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.exit_key_label.grid(row=row, column=1, pady=5)
        self.exit_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('exit'))
        self.exit_rebind_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Close the application completely")
        row += 1
        
        ttk.Label(frame, text='Toggle Minimize:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.minimize_key_label = ttk.Label(frame, text=self.hotkeys['toggle_minimize'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.minimize_key_label.grid(row=row, column=1, pady=5)
        self.minimize_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_minimize'))
        self.minimize_rebind_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Toggle between minimized and normal window")

    def create_webhook_section(self, start_row):
        """Create the Discord webhook collapsible section"""
        section = CollapsibleFrame(self.main_frame, "🔗 Discord Webhook", start_row)
        self.collapsible_sections['webhook'] = section
        frame = section.get_content_frame()
        
        # Configure frame for centering
        frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        row = 0
        # Enable webhook checkbox
        self.webhook_enabled_var = tk.BooleanVar(value=self.webhook_enabled)
        webhook_check = ttk.Checkbutton(frame, text='Enable Discord Webhook', variable=self.webhook_enabled_var)
        webhook_check.grid(row=row, column=0, columnspan=2, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Send fishing progress updates to Discord")
        self.webhook_enabled_var.trace_add('write', lambda *args: (setattr(self, 'webhook_enabled', self.webhook_enabled_var.get()), self.auto_save_settings()))
        row += 1
        
        # Webhook URL
        ttk.Label(frame, text='Webhook URL:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.webhook_url_var = tk.StringVar(value=self.webhook_url)
        webhook_entry = ttk.Entry(frame, textvariable=self.webhook_url_var, width=25)
        webhook_entry.grid(row=row, column=1, sticky='ew', pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Discord webhook URL from your server settings")
        self.webhook_url_var.trace_add('write', lambda *args: (setattr(self, 'webhook_url', self.webhook_url_var.get()), self.auto_save_settings()))
        row += 1
        
        # Webhook interval
        ttk.Label(frame, text='Send Every X Fish:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.webhook_interval_var = tk.IntVar(value=self.webhook_interval)
        interval_spinbox = ttk.Spinbox(frame, from_=1, to=100, textvariable=self.webhook_interval_var, width=10)
        interval_spinbox.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Send webhook message every X fish caught (e.g., 10 = message every 10 fish)")
        self.webhook_interval_var.trace_add('write', lambda *args: (setattr(self, 'webhook_interval', self.webhook_interval_var.get()), self.auto_save_settings()))
        row += 1
        
        # Devil fruit webhook notifications
        self.devil_fruit_webhook_var = tk.BooleanVar(value=getattr(self, 'devil_fruit_webhook_enabled', True))
        devil_fruit_check = ttk.Checkbutton(frame, text='🍎 Devil Fruit Alerts', variable=self.devil_fruit_webhook_var)
        devil_fruit_check.grid(row=row, column=0, columnspan=2, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Send Discord notifications when devil fruits are caught")
        self.devil_fruit_webhook_var.trace_add('write', lambda *args: (setattr(self, 'devil_fruit_webhook_enabled', self.devil_fruit_webhook_var.get()), self.auto_save_settings()))
        row += 1
        
        # Test webhook button
        test_btn = ttk.Button(frame, text='Test Webhook', command=self.test_webhook)
        test_btn.grid(row=row, column=0, columnspan=2, pady=10)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Send a test message to verify webhook is working")



    def create_startup_section(self, start_row):
        """Create the Auto Setup settings section"""
        section = CollapsibleFrame(self.main_frame, "🚀 Auto Setup Settings", start_row)
        # Start collapsed by default
        section.is_expanded = False
        section.toggle()
        self.collapsible_sections['zoom'] = section
        frame = section.get_content_frame()
        
        row = 0
        
        # Auto zoom enabled checkbox
        self.auto_zoom_var = tk.BooleanVar(value=False)
        zoom_check = ttk.Checkbutton(frame, text="Enable Auto Zoom on Startup", 
                                    variable=self.auto_zoom_var)
        zoom_check.grid(row=row, column=0, sticky='w', pady=2)
        ToolTip(zoom_check, "Automatically zoom out when fishing starts for better visibility")
        
        row += 1
        
        # Info label
        info_label = ttk.Label(frame, text="When enabled, automatically zooms out for optimal fishing view", 
                              foreground="gray")
        info_label.grid(row=row, column=0, sticky='w', pady=(0, 5))
        
        # Set default zoom values (hidden from user)
        self.zoom_out_var = tk.IntVar(value=5)
        self.zoom_in_var = tk.IntVar(value=8)
        
        # Add auto-save functionality to zoom variables
        self.zoom_out_var.trace_add('write', lambda *args: (setattr(self, 'zoom_out_steps', self.zoom_out_var.get()), self.auto_save_settings()))
        self.zoom_in_var.trace_add('write', lambda *args: (setattr(self, 'zoom_in_steps', self.zoom_in_var.get()), self.auto_save_settings()))
        
        row += 1
        


    def create_discord_section(self, start_row):
        """Create the Discord join section at the bottom"""
        discord_frame = ttk.Frame(self.main_frame)
        discord_frame.grid(row=start_row, column=0, sticky='ew', pady=(25, 10))
        discord_frame.columnconfigure(0, weight=1)
        
        # Create Discord button using ttk for proper theme support
        discord_btn = ttk.Button(discord_frame, text='💬 Join our Discord!', 
                               command=self.open_discord)
        
        discord_btn.pack(pady=5, padx=10, fill='x')
        
        # Add tooltip using the existing ToolTip class
        ToolTip(discord_btn, "Click to join our Discord community!")

    def open_settings_window(self):
        """Open modern settings window with timing and theme options"""
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title('⚙️ Settings')
        self.settings_window.geometry('700x750')
        self.settings_window.attributes('-topmost', True)
        self.settings_window.resizable(False, False)
        
        # Apply current theme colors to settings window
        theme_colors = self.theme_manager.themes[self.current_theme]["colors"]
        self.settings_window.configure(bg=theme_colors["bg"])
        
        # Configure ttk styles for settings window to match main GUI
        style = ttk.Style()
        
        # Frame styles
        style.configure('Settings.TFrame', 
                       background=theme_colors["bg"],
                       relief='flat')
        
        # Label styles  
        style.configure('Settings.TLabel',
                       background=theme_colors["bg"],
                       foreground=theme_colors["fg"],
                       font=('Segoe UI', 9))
        
        # Section title style
        style.configure('SectionTitle.TLabel',
                       background=theme_colors["bg"],
                       foreground=theme_colors["accent"],
                       font=('Segoe UI', 10, 'bold'))
        
        # Subtitle style
        style.configure('Subtitle.TLabel',
                       background=theme_colors["bg"],
                       foreground=theme_colors["accent"],
                       font=('Segoe UI', 9, 'bold'))
        
        # LabelFrame styles (for sections)
        style.configure('Settings.TLabelFrame',
                       background=theme_colors["bg"],
                       foreground=theme_colors["accent"],
                       relief='solid',
                       borderwidth=1,
                       bordercolor=theme_colors["accent"])
        style.configure('Settings.TLabelFrame.Label',
                       background=theme_colors["bg"],
                       foreground=theme_colors["accent"],
                       font=('Segoe UI', 11, 'bold'))
        
        # Button styles
        style.configure('Settings.TButton',
                       background=theme_colors["button_bg"],
                       foreground=theme_colors["fg"],
                       borderwidth=1,
                       relief='flat',
                       font=('Segoe UI', 9))
        style.map('Settings.TButton',
                 background=[('active', theme_colors["button_hover"])])
        
        # Spinbox styles
        style.configure('Settings.TSpinbox',
                       fieldbackground=theme_colors["button_bg"],
                       background=theme_colors["button_bg"],
                       foreground=theme_colors["fg"],
                       bordercolor=theme_colors["accent"],
                       insertcolor=theme_colors["fg"],
                       font=('Segoe UI', 9))
        
        # Separator styles
        style.configure('Settings.TSeparator',
                       background=theme_colors["accent"])
        
        # Main container - simplified approach without canvas
        main_container = ttk.Frame(self.settings_window, style='Settings.TFrame')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Top section with close button
        top_frame = ttk.Frame(main_container, style='Settings.TFrame')
        top_frame.pack(fill='x', pady=(0, 20))
        top_frame.columnconfigure(1, weight=1)
        
        # Settings title (left)
        title_label = ttk.Label(top_frame, text='⚙️ Settings', style='SectionTitle.TLabel')
        title_label.grid(row=0, column=0, sticky='w')
        
        # Close button (center-right)
        close_btn = ttk.Button(top_frame, text='✕ Close', command=self.settings_window.destroy, 
                              style='Settings.TButton')
        close_btn.grid(row=0, column=2, sticky='e')
        
        # Content frame - direct approach
        content_frame = ttk.Frame(main_container, style='Settings.TFrame')
        content_frame.pack(fill='both', expand=True)
        
        # Create sections directly
        self.create_simple_timing_section(content_frame, theme_colors)
        self.create_simple_theme_section(content_frame, theme_colors)
        self.create_simple_presets_section(content_frame, theme_colors)
    
    def create_simple_timing_section(self, parent, theme_colors):
        """Create simplified timing settings section"""
        # Timing Settings Section
        timing_frame = tk.LabelFrame(parent, text="⏱️ Timing Settings", 
                                    bg=theme_colors["bg"], fg=theme_colors["accent"],
                                    font=('Segoe UI', 11, 'bold'), padx=20, pady=15)
        timing_frame.pack(fill='x', padx=10, pady=(0, 20))
        
        # PD Controller settings
        pd_label = tk.Label(timing_frame, text="🎛️ PD Controller", 
                           bg=theme_colors["bg"], fg=theme_colors["accent"],
                           font=('Segoe UI', 10, 'bold'))
        pd_label.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # KP setting
        kp_label = tk.Label(timing_frame, text="Proportional Gain (KP):", 
                           bg=theme_colors["bg"], fg=theme_colors["fg"])
        kp_label.grid(row=1, column=0, sticky='w', pady=2)
        
        self.kp_var = tk.DoubleVar(value=getattr(self, 'kp', 0.2))
        kp_spinbox = tk.Spinbox(timing_frame, from_=0.01, to=1.0, increment=0.01, 
                               textvariable=self.kp_var, width=15,
                               bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                               insertbackground=theme_colors["fg"], selectbackground=theme_colors["accent"],
                               selectforeground=theme_colors["bg"], relief='flat', bd=1,
                               highlightthickness=1, highlightcolor=theme_colors["accent"],
                               highlightbackground=theme_colors["button_bg"])
        kp_spinbox.grid(row=1, column=1, sticky='e', padx=(10, 0), pady=2)
        self.kp_var.trace_add('write', lambda *args: (setattr(self, 'kp', self.kp_var.get()), self.auto_save_settings()))
        
        # KD setting
        kd_label = tk.Label(timing_frame, text="Derivative Gain (KD):", 
                           bg=theme_colors["bg"], fg=theme_colors["fg"])
        kd_label.grid(row=2, column=0, sticky='w', pady=2)
        
        self.kd_var = tk.DoubleVar(value=getattr(self, 'kd', 0.6))
        kd_spinbox = tk.Spinbox(timing_frame, from_=0.01, to=2.0, increment=0.01, 
                               textvariable=self.kd_var, width=15,
                               bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                               insertbackground=theme_colors["fg"], selectbackground=theme_colors["accent"],
                               selectforeground=theme_colors["bg"], relief='flat', bd=1,
                               highlightthickness=1, highlightcolor=theme_colors["accent"],
                               highlightbackground=theme_colors["button_bg"])
        kd_spinbox.grid(row=2, column=1, sticky='e', padx=(10, 0), pady=2)
        self.kd_var.trace_add('write', lambda *args: (setattr(self, 'kd', self.kd_var.get()), self.auto_save_settings()))
        
        # Timeout settings
        timeout_label = tk.Label(timing_frame, text="⏰ Timeout Settings", 
                                bg=theme_colors["bg"], fg=theme_colors["accent"],
                                font=('Segoe UI', 10, 'bold'))
        timeout_label.grid(row=3, column=0, columnspan=2, sticky='w', pady=(15, 10))
        
        # Scan timeout
        scan_label = tk.Label(timing_frame, text="Fish Detection Timeout (s):", 
                             bg=theme_colors["bg"], fg=theme_colors["fg"])
        scan_label.grid(row=4, column=0, sticky='w', pady=2)
        
        self.scan_timeout_var = tk.DoubleVar(value=getattr(self, 'scan_timeout', 15.0))
        scan_spinbox = tk.Spinbox(timing_frame, from_=5.0, to=60.0, increment=1.0, 
                                 textvariable=self.scan_timeout_var, width=15,
                                 bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                                 insertbackground=theme_colors["fg"], selectbackground=theme_colors["accent"],
                                 selectforeground=theme_colors["bg"], relief='flat', bd=1,
                                 highlightthickness=1, highlightcolor=theme_colors["accent"],
                                 highlightbackground=theme_colors["button_bg"])
        scan_spinbox.grid(row=4, column=1, sticky='e', padx=(10, 0), pady=2)
        self.scan_timeout_var.trace_add('write', lambda *args: (setattr(self, 'scan_timeout', self.scan_timeout_var.get()), self.auto_save_settings()))
        
        timing_frame.columnconfigure(1, weight=1)

    def create_simple_theme_section(self, parent, theme_colors):
        """Create simplified theme settings section"""
        # Theme Settings Section
        theme_frame = tk.LabelFrame(parent, text="🎨 Theme Settings", 
                                   bg=theme_colors["bg"], fg=theme_colors["accent"],
                                   font=('Segoe UI', 11, 'bold'), padx=20, pady=15)
        theme_frame.pack(fill='x', padx=10, pady=(0, 20))
        
        # Current theme display
        current_label = tk.Label(theme_frame, text="Current Theme:", 
                                bg=theme_colors["bg"], fg=theme_colors["accent"],
                                font=('Segoe UI', 10, 'bold'))
        current_label.grid(row=0, column=0, sticky='w', pady=(0, 15))
        
        current_theme_name = getattr(self, 'current_theme', 'default').title()
        theme_name_label = tk.Label(theme_frame, text=current_theme_name, 
                                   bg=theme_colors["bg"], fg=theme_colors["fg"])
        theme_name_label.grid(row=0, column=1, sticky='w', padx=(10, 0), pady=(0, 15))
        
        # Theme buttons
        themes_info = [
            ("Default", "default", "🔵"), ("Dark Mode", "dark", "⚫"),
            ("Pink", "pink", "💖"), ("Christmas", "christmas", "🎄"),
            ("Ocean", "ocean", "🌊"), ("Sunset", "sunset", "🌅"), 
            ("Purple", "purple", "💜"), ("Neon", "neon", "⚡")
        ]
        
        row = 1
        for i, (name, theme_id, icon) in enumerate(themes_info):
            if i % 4 == 0:  # New row every 4 themes
                row += 1
            col = i % 4
            
            theme_btn = tk.Button(theme_frame, text=f"{icon} {name}", 
                                 bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                                 command=lambda t=theme_id: self.apply_theme_and_update(t),
                                 width=12, relief='flat')
            theme_btn.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            
            # Highlight current theme
            if theme_id == getattr(self, 'current_theme', 'default'):
                theme_btn.configure(bg=theme_colors["accent"], fg=theme_colors["bg"])
        
        # Configure grid weights
        for i in range(4):
            theme_frame.columnconfigure(i, weight=1)

    def create_simple_presets_section(self, parent, theme_colors):
        """Create simplified presets section for settings window"""
        # Presets Section
        presets_frame = tk.LabelFrame(parent, text="💾 Presets", 
                                     bg=theme_colors["bg"], fg=theme_colors["accent"],
                                     font=('Segoe UI', 11, 'bold'), padx=20, pady=15)
        presets_frame.pack(fill='x', padx=10, pady=(0, 20))
        
        # Save preset
        save_label = tk.Label(presets_frame, text="Save:", 
                             bg=theme_colors["bg"], fg=theme_colors["fg"])
        save_label.grid(row=0, column=0, sticky='w', pady=5)
        
        save_btn = tk.Button(presets_frame, text="💾 Save Preset", 
                            bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                            command=self.save_preset, width=15, relief='flat')
        save_btn.grid(row=0, column=1, sticky='w', padx=(10, 0), pady=5)
        
        # Load preset
        load_label = tk.Label(presets_frame, text="Load:", 
                             bg=theme_colors["bg"], fg=theme_colors["fg"])
        load_label.grid(row=1, column=0, sticky='w', pady=5)
        
        load_btn = tk.Button(presets_frame, text="📁 Load Preset", 
                            bg=theme_colors["button_bg"], fg=theme_colors["fg"],
                            command=self.load_preset, width=15, relief='flat')
        load_btn.grid(row=1, column=1, sticky='w', padx=(10, 0), pady=5)
        
        # Info text
        info_label = tk.Label(presets_frame, 
                             text="Save/load all settings except webhooks and keybinds", 
                             bg=theme_colors["bg"], fg=theme_colors["fg"],
                             font=('Segoe UI', 8))
        info_label.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 0))
        
        presets_frame.columnconfigure(1, weight=1)

    def create_timing_settings_section_old(self, parent):
        """Create timing settings section"""
        # Timing Settings Section
        timing_section = ttk.LabelFrame(parent, text="⏱️ Timing Settings", padding=20, style='Settings.TLabelFrame')
        timing_section.pack(fill='x', padx=10, pady=(0, 20))
        timing_section.columnconfigure(1, weight=1)
        
        row = 0
        
        # PD Controller subsection
        pd_frame = ttk.Frame(timing_section, style='Settings.TFrame')
        pd_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(0, 15))
        pd_frame.columnconfigure(1, weight=1)
        row += 1
        
        ttk.Label(pd_frame, text="🎛️ PD Controller", style='SectionTitle.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # KP setting
        ttk.Label(pd_frame, text="Proportional Gain (KP):", style='Settings.TLabel').grid(row=1, column=0, sticky='w', pady=2)
        self.kp_var = tk.DoubleVar(value=getattr(self, 'kp', 0.2))
        kp_spinbox = ttk.Spinbox(pd_frame, from_=0.01, to=1.0, increment=0.01, 
                                textvariable=self.kp_var, width=15, style='Settings.TSpinbox')
        kp_spinbox.grid(row=1, column=1, sticky='e', padx=(10, 0), pady=2)
        self.kp_var.trace_add('write', lambda *args: (setattr(self, 'kp', self.kp_var.get()), self.auto_save_settings()))
        
        # KD setting
        ttk.Label(pd_frame, text="Derivative Gain (KD):", style='Settings.TLabel').grid(row=2, column=0, sticky='w', pady=2)
        self.kd_var = tk.DoubleVar(value=getattr(self, 'kd', 0.6))
        kd_spinbox = ttk.Spinbox(pd_frame, from_=0.01, to=2.0, increment=0.01, 
                                textvariable=self.kd_var, width=15, style='Settings.TSpinbox')
        kd_spinbox.grid(row=2, column=1, sticky='e', padx=(10, 0), pady=2)
        self.kd_var.trace_add('write', lambda *args: (setattr(self, 'kd', self.kd_var.get()), self.auto_save_settings()))
        
        # Separator
        separator1 = ttk.Separator(timing_section, orient='horizontal', style='Settings.TSeparator')
        separator1.grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        
        # Timeout subsection
        timeout_frame = ttk.Frame(timing_section, style='Settings.TFrame')
        timeout_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(0, 15))
        timeout_frame.columnconfigure(1, weight=1)
        row += 1
        
        ttk.Label(timeout_frame, text="⏰ Timeout Settings", style='SectionTitle.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # Scan timeout
        ttk.Label(timeout_frame, text="Fish Detection Timeout (s):", style='Settings.TLabel').grid(row=1, column=0, sticky='w', pady=2)
        self.scan_timeout_var = tk.DoubleVar(value=getattr(self, 'scan_timeout', 15.0))
        scan_spinbox = ttk.Spinbox(timeout_frame, from_=5.0, to=60.0, increment=1.0, 
                                  textvariable=self.scan_timeout_var, width=15, style='Settings.TSpinbox')
        scan_spinbox.grid(row=1, column=1, sticky='e', padx=(10, 0), pady=2)
        self.scan_timeout_var.trace_add('write', lambda *args: (setattr(self, 'scan_timeout', self.scan_timeout_var.get()), self.auto_save_settings()))
        
        # Wait after loss
        ttk.Label(timeout_frame, text="Wait After Catch (s):", style='Settings.TLabel').grid(row=2, column=0, sticky='w', pady=2)
        self.wait_after_loss_var = tk.DoubleVar(value=getattr(self, 'wait_after_loss', 1.0))
        wait_spinbox = ttk.Spinbox(timeout_frame, from_=0.1, to=10.0, increment=0.1, 
                                  textvariable=self.wait_after_loss_var, width=15, style='Settings.TSpinbox')
        wait_spinbox.grid(row=2, column=1, sticky='e', padx=(10, 0), pady=2)
        self.wait_after_loss_var.trace_add('write', lambda *args: (setattr(self, 'wait_after_loss', self.wait_after_loss_var.get()), self.auto_save_settings()))
        
        # Separator
        separator2 = ttk.Separator(timing_section, orient='horizontal', style='Settings.TSeparator')
        separator2.grid(row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        
        # Purchase timing subsection
        purchase_frame = ttk.Frame(timing_section, style='Settings.TFrame')
        purchase_frame.grid(row=row, column=0, columnspan=2, sticky='ew')
        purchase_frame.columnconfigure(1, weight=1)
        
        ttk.Label(purchase_frame, text="🛒 Purchase Timing", style='SectionTitle.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # Purchase delay after key
        ttk.Label(purchase_frame, text="Delay After 'E' Key (s):", style='Settings.TLabel').grid(row=1, column=0, sticky='w', pady=2)
        self.purchase_delay_var = tk.DoubleVar(value=getattr(self, 'purchase_delay_after_key', 2.0))
        delay_spinbox = ttk.Spinbox(purchase_frame, from_=0.5, to=10.0, increment=0.1, 
                                   textvariable=self.purchase_delay_var, width=15, style='Settings.TSpinbox')
        delay_spinbox.grid(row=1, column=1, sticky='e', padx=(10, 0), pady=2)
        self.purchase_delay_var.trace_add('write', lambda *args: (setattr(self, 'purchase_delay_after_key', self.purchase_delay_var.get()), self.auto_save_settings()))
        
        # Click delay
        ttk.Label(purchase_frame, text="Click Delay (s):", style='Settings.TLabel').grid(row=2, column=0, sticky='w', pady=2)
        self.click_delay_var = tk.DoubleVar(value=getattr(self, 'purchase_click_delay', 1.0))
        click_spinbox = ttk.Spinbox(purchase_frame, from_=0.1, to=5.0, increment=0.1, 
                                   textvariable=self.click_delay_var, width=15, style='Settings.TSpinbox')
        click_spinbox.grid(row=2, column=1, sticky='e', padx=(10, 0), pady=2)
        self.click_delay_var.trace_add('write', lambda *args: (setattr(self, 'purchase_click_delay', self.click_delay_var.get()), self.auto_save_settings()))
        
        # Type delay
        ttk.Label(purchase_frame, text="After Type Delay (s):", style='Settings.TLabel').grid(row=3, column=0, sticky='w', pady=2)
        self.type_delay_var = tk.DoubleVar(value=getattr(self, 'purchase_after_type_delay', 1.0))
        type_spinbox = ttk.Spinbox(purchase_frame, from_=0.1, to=5.0, increment=0.1, 
                                  textvariable=self.type_delay_var, width=15, style='Settings.TSpinbox')
        type_spinbox.grid(row=3, column=1, sticky='e', padx=(10, 0), pady=2)
        self.type_delay_var.trace_add('write', lambda *args: (setattr(self, 'purchase_after_type_delay', self.type_delay_var.get()), self.auto_save_settings()))

    def create_theme_settings_section(self, parent):
        """Create theme settings section with banner-style theme cards"""
        # Get current theme colors
        theme_colors = self.theme_manager.themes[self.current_theme]["colors"]
        
        # Theme Settings Section
        theme_section = ttk.LabelFrame(parent, text="🎨 Theme Settings", padding=20, style='Settings.TLabelFrame')
        theme_section.pack(fill='x', padx=10, pady=(0, 20))
        
        # Current theme display
        current_frame = ttk.Frame(theme_section, style='Settings.TFrame')
        current_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(current_frame, text="Current Theme:", style='SectionTitle.TLabel').pack(side='left')
        current_theme_name = getattr(self, 'current_theme', 'default').title()
        ttk.Label(current_frame, text=current_theme_name, 
                 style='Subtitle.TLabel').pack(side='left', padx=(10, 0))
        
        # Theme selection with banner-style cards
        themes_info = [
            ("Default", "default", "🔵", "Classic blue theme with modern styling"),
            ("Dark Mode", "dark", "⚫", "Pure black theme with gray accents"),
            ("Pink", "pink", "💖", "Light, cute pink theme with soft pastel vibes"),
            ("Christmas", "christmas", "🎄", "Festive holiday theme with red and green"),
            ("Ocean", "ocean", "🌊", "Cool ocean blues and aqua tones"),
            ("Sunset", "sunset", "🌅", "Warm sunset oranges and purples"),
            ("Purple", "purple", "💜", "Royal purple with elegant styling"),
            ("Neon", "neon", "⚡", "Bright neon colors for vibrant experience")
        ]
        
        # Create banner-style theme buttons (2 columns, wider layout)
        themes_frame = ttk.Frame(theme_section, style='Settings.TFrame')
        themes_frame.pack(fill='x')
        themes_frame.columnconfigure(0, weight=1)
        themes_frame.columnconfigure(1, weight=1)
        
        for i, (name, theme_id, icon, description) in enumerate(themes_info):
            row = i // 2
            col = i % 2
            
            # Create banner-style button frame using tk.Frame for better control
            banner_frame = tk.Frame(themes_frame, 
                                   bg=theme_colors["button_bg"], 
                                   relief='solid', 
                                   borderwidth=1,
                                   highlightbackground=theme_colors["accent"],
                                   highlightthickness=1)
            banner_frame.grid(row=row, column=col, padx=5, pady=3, sticky='ew')
            banner_frame.columnconfigure(1, weight=1)
            
            # Theme icon
            icon_label = tk.Label(banner_frame, text=icon, font=('Segoe UI', 14),
                                 bg=theme_colors["button_bg"], fg=theme_colors["fg"])
            icon_label.grid(row=0, column=0, padx=(10, 5), pady=8)
            
            # Theme info
            info_frame = tk.Frame(banner_frame, bg=theme_colors["button_bg"])
            info_frame.grid(row=0, column=1, sticky='ew', padx=(0, 5), pady=5)
            info_frame.columnconfigure(0, weight=1)
            
            # Theme name
            name_label = tk.Label(info_frame, text=name, font=('Segoe UI', 10, 'bold'),
                                 bg=theme_colors["button_bg"], fg=theme_colors["fg"])
            name_label.grid(row=0, column=0, sticky='w')
            
            # Theme description
            desc_label = tk.Label(info_frame, text=description, font=('Segoe UI', 8),
                                 bg=theme_colors["button_bg"], fg=theme_colors["fg"])
            desc_label.grid(row=1, column=0, sticky='w')
            
            # Apply button
            apply_btn = ttk.Button(banner_frame, text='Apply', width=8, style='Settings.TButton',
                                  command=lambda t=theme_id: self.apply_theme_and_update(t))
            apply_btn.grid(row=0, column=2, padx=(5, 10), pady=8)
            
            # Highlight current theme
            if theme_id == getattr(self, 'current_theme', 'default'):
                banner_frame.configure(highlightbackground=theme_colors["accent"], highlightthickness=2)
                name_label.configure(fg=theme_colors["accent"])
    
    def apply_theme_and_update(self, theme_id):
        """Apply theme and update current theme display"""
        print(f"Applying theme: {theme_id}")
        if hasattr(self, 'theme_manager') and theme_id in self.theme_manager.themes:
            # Apply the theme directly
            self.current_theme = theme_id
            self.apply_theme()
            self.auto_save_settings()
            
            # Close and reopen settings window to refresh theme display
            if hasattr(self, 'settings_window') and self.settings_window:
                self.settings_window.destroy()
                # Small delay to ensure window is closed
                self.root.after(100, self.open_settings_window)
            
            print(f"Successfully applied {theme_id} theme")
        else:
            print(f"Theme {theme_id} not found or theme_manager not available")



    def open_discord(self):
        """Open Discord invite link in browser"""
        import webbrowser
        try:
            webbrowser.open('https://discord.gg/5Gtsgv46ce')
            self.status_msg.config(text='Opened Discord invite', foreground='#0DA50DFF')
        except Exception as e:
            self.status_msg.config(text=f'Error opening Discord: {e}', foreground='red')

    def check_for_updates(self):
        """Manual update check triggered by user"""
        if not self.update_manager:
            self.update_status('UpdateManager not available', 'error', '❌')
            return
        
        # Run update check in background thread
        threading.Thread(target=self.update_manager.check_for_updates_manual, daemon=True).start()


    
    def update_status(self, message, status_type='info', icon=''):
        """Update status message from UpdateManager"""
        color_map = {
            'success': 'green',
            'error': 'red',
            'warning': 'orange',
            'info': '#58a6ff'
        }
        color = color_map.get(status_type, '#58a6ff')
        
        full_message = f'{icon} {message}' if icon else message
        self.status_msg.config(text=full_message, foreground=color)

    def test_webhook(self):
        """Send a test webhook message"""
        self.webhook_manager.test()
    

    

    
    def on_zoom_settings_change(self, *args):
        """Called when zoom settings change in GUI"""
        if hasattr(self, 'zoom_controller'):
            self.update_zoom_controller_settings()
    
    def update_zoom_controller_settings(self):
        """Update zoom controller with current GUI settings"""
        if hasattr(self, 'zoom_controller'):
            self.zoom_controller.update_settings({
                'zoom_out_steps': self.zoom_out_var.get(),
                'zoom_in_steps': self.zoom_in_var.get()
            })
            print(f"🔧 Zoom settings updated: Out={self.zoom_out_var.get()}, In={self.zoom_in_var.get()}")

    def apply_theme(self):
        """Apply the current theme to the application"""
        style = ttk.Style()
        
        # Get theme colors from theme manager
        theme_colors = self.theme_manager.themes[self.current_theme]["colors"]
        is_dark = theme_colors["bg"] == "#0d1117"
        
        if is_dark:
            # Modern dark theme with gradients and rounded corners
            self.root.configure(bg=theme_colors["bg"])
            style.theme_use('clam')
            
            # Modern dark colors
            style.configure('TFrame', 
                          background=theme_colors["bg"],
                          relief='flat',
                          borderwidth=0)
            
            style.configure('TLabel', 
                          background=theme_colors["bg"], 
                          foreground=theme_colors["fg"],
                          font=('Segoe UI', 9))
            
            # Modern button styling
            style.configure('TButton',
                          background=theme_colors["button_bg"],
                          foreground=theme_colors["fg"],
                          borderwidth=1,
                          focuscolor='none',
                          font=('Segoe UI', 9),
                          relief='flat')
            style.map('TButton',
                     background=[('active', theme_colors["button_hover"]), ('pressed', theme_colors["button_hover"])],
                     bordercolor=[('active', theme_colors["accent"]), ('pressed', theme_colors["accent"])])
            
            # Accent button for primary actions
            style.configure('Accent.TButton',
                          background='#238636',
                          foreground='#ffffff',
                          borderwidth=0,
                          font=('Segoe UI', 9, 'bold'))
            style.map('Accent.TButton',
                     background=[('active', '#2ea043'), ('pressed', '#1a7f37')])
            
            # Status buttons
            style.configure('Status.TButton',
                          background='#1f6feb',
                          foreground='#ffffff',
                          borderwidth=0,
                          font=('Segoe UI', 9))
            style.map('Status.TButton',
                     background=[('active', '#388bfd'), ('pressed', '#0969da')])
            
            style.configure('TCheckbutton',
                          background=theme_colors["bg"],
                          foreground=theme_colors["fg"],
                          focuscolor='none',
                          font=('Segoe UI', 9))
            style.map('TCheckbutton',
                     background=[('active', theme_colors["bg"]),
                               ('selected', theme_colors["bg"])])
            
            style.configure('TSpinbox',
                          fieldbackground=theme_colors["button_bg"],
                          background=theme_colors["button_bg"],
                          foreground=theme_colors["fg"],
                          bordercolor=theme_colors["accent"],
                          arrowcolor=theme_colors["fg"],
                          insertcolor=theme_colors["fg"],
                          selectbackground=theme_colors["accent"],
                          selectforeground=theme_colors["bg"],
                          font=('Segoe UI', 9))
            style.map('TSpinbox',
                     fieldbackground=[('focus', theme_colors["button_hover"])],
                     bordercolor=[('focus', theme_colors["accent"])])
            
            # Scrollbar styling using theme colors
            style.configure('Vertical.TScrollbar',
                          background=theme_colors["scrollbar_bg"],
                          troughcolor=theme_colors["scrollbar_trough"],
                          bordercolor=theme_colors["scrollbar_active"],
                          arrowcolor=theme_colors["fg"],
                          darkcolor=theme_colors["scrollbar_bg"],
                          lightcolor=theme_colors["scrollbar_active"])
            style.map('Vertical.TScrollbar',
                     background=[('active', theme_colors["scrollbar_active"]), ('pressed', theme_colors["scrollbar_pressed"])])
            
            # Header styling
            style.configure('Title.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["accent"],
                          font=('Segoe UI', 18, 'bold'))
            
            style.configure('Subtitle.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["fg"],
                          font=('Segoe UI', 8))
            
            # Section title styling
            style.configure('SectionTitle.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["accent"],
                          font=('Segoe UI', 11, 'bold'))
            
            # Status labels
            style.configure('StatusOn.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["success"],
                          font=('Segoe UI', 10, 'bold'))
            
            style.configure('StatusOff.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["error"],
                          font=('Segoe UI', 10))
            
            style.configure('StatusInfo.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["accent"],
                          font=('Segoe UI', 10, 'bold'))
            
            style.configure('Counter.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["fg"],
                          font=('Segoe UI', 11, 'bold'))
            
            # Update canvas background for dark mode
            if hasattr(self, 'canvas'):
                self.canvas.configure(bg=theme_colors["bg"])
            
            # Update fishing location section colors
            self.update_fishing_location_colors()
        else:
            # Modern light theme with clean styling
            self.root.configure(bg=theme_colors["bg"])
            style.theme_use('clam')
            
            # Light theme colors
            style.configure('TFrame', 
                          background=theme_colors["bg"],
                          relief='flat',
                          borderwidth=0)
            
            style.configure('TLabel', 
                          background=theme_colors["bg"], 
                          foreground=theme_colors["fg"],
                          font=('Segoe UI', 9))
            
            # Modern button styling for light mode
            style.configure('TButton',
                          background=theme_colors["button_bg"],
                          foreground=theme_colors["fg"],
                          borderwidth=1,
                          focuscolor='none',
                          font=('Segoe UI', 9),
                          relief='flat')
            style.map('TButton',
                     background=[('active', theme_colors["button_hover"]), ('pressed', theme_colors["button_hover"])],
                     bordercolor=[('active', theme_colors["accent"]), ('pressed', theme_colors["accent"])])
            
            # Accent button for primary actions
            style.configure('Accent.TButton',
                          background='#2da44e',
                          foreground='#ffffff',
                          borderwidth=0,
                          font=('Segoe UI', 9, 'bold'))
            style.map('Accent.TButton',
                     background=[('active', '#2c974b'), ('pressed', '#298e46')])
            
            # Status buttons
            style.configure('Status.TButton',
                          background='#0969da',
                          foreground='#ffffff',
                          borderwidth=0,
                          font=('Segoe UI', 9))
            style.map('Status.TButton',
                     background=[('active', '#0860ca'), ('pressed', '#0757ba')])
            
            style.configure('TCheckbutton',
                          background=theme_colors["bg"],
                          foreground=theme_colors["fg"],
                          focuscolor='none',
                          font=('Segoe UI', 9))
            style.map('TCheckbutton',
                     background=[('active', theme_colors["bg"]),
                               ('selected', theme_colors["bg"])])
            
            style.configure('TSpinbox',
                          fieldbackground=theme_colors["button_bg"],
                          background=theme_colors["button_bg"],
                          foreground=theme_colors["fg"],
                          bordercolor=theme_colors["accent"],
                          arrowcolor=theme_colors["fg"],
                          insertcolor=theme_colors["fg"],
                          selectbackground=theme_colors["accent"],
                          selectforeground=theme_colors["bg"],
                          font=('Segoe UI', 9))
            style.map('TSpinbox',
                     fieldbackground=[('focus', theme_colors["button_hover"])],
                     bordercolor=[('focus', theme_colors["accent"])])
            
            # Entry styling to match the gray theme
            style.configure('TEntry',
                          fieldbackground='#f6f8fa',
                          background='#e1e4e8',
                          foreground='#24292f',
                          bordercolor='#d0d7de',
                          font=('Segoe UI', 9))
            
            # Scrollbar styling using theme colors
            style.configure('Vertical.TScrollbar',
                          background=theme_colors["scrollbar_bg"],
                          troughcolor=theme_colors["scrollbar_trough"],
                          bordercolor=theme_colors["scrollbar_active"],
                          arrowcolor=theme_colors["fg"],
                          darkcolor=theme_colors["scrollbar_bg"],
                          lightcolor=theme_colors["scrollbar_active"])
            style.map('Vertical.TScrollbar',
                     background=[('active', theme_colors["scrollbar_active"]), ('pressed', theme_colors["scrollbar_pressed"])])
            
            # Header styling
            style.configure('Title.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["accent"],
                          font=('Segoe UI', 18, 'bold'))
            
            style.configure('Subtitle.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["fg"],
                          font=('Segoe UI', 8))
            
            # Section title styling
            style.configure('SectionTitle.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["accent"],
                          font=('Segoe UI', 11, 'bold'))
            
            # Status labels
            style.configure('StatusOn.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["success"],
                          font=('Segoe UI', 10, 'bold'))
            
            style.configure('StatusOff.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["error"],
                          font=('Segoe UI', 10))
            
            style.configure('StatusInfo.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["accent"],
                          font=('Segoe UI', 10, 'bold'))
            
            style.configure('Counter.TLabel',
                          background=theme_colors["bg"],
                          foreground=theme_colors["fg"],
                          font=('Segoe UI', 11, 'bold'))
            
            # Update canvas background for light mode
            if hasattr(self, 'canvas'):
                self.canvas.configure(bg=theme_colors["bg"])
            
            # Update fishing location section colors
            self.update_fishing_location_colors()
        




    def auto_save_settings(self):
        """Auto-save current settings to default.json"""
        if not hasattr(self, 'auto_purchase_var'):
            return  # Skip if not fully initialized
            
        preset_data = {
            'auto_purchase_enabled': getattr(self.auto_purchase_var, 'get', lambda: False)(),
            'auto_purchase_amount': getattr(self.amount_var, 'get', lambda: getattr(self, 'auto_purchase_amount', 100))(),
            'loops_per_purchase': getattr(self.loops_var, 'get', lambda: getattr(self, 'loops_per_purchase', 1))(),
            'point_coords': getattr(self, 'point_coords', {}),
            'fruit_coords': getattr(self, 'fruit_coords', {}),
            'fishing_location': getattr(self, 'fishing_location', None),
            'fruit_storage_enabled': getattr(self, 'fruit_storage_enabled', False),
            'fruit_storage_key': getattr(self, 'fruit_storage_key', '3'),
            'rod_key': getattr(self, 'rod_key', '1'),
            'kp': getattr(self, 'kp', 0.1),
            'kd': getattr(self, 'kd', 0.5),
            'scan_timeout': getattr(self, 'scan_timeout', 15.0),
            'wait_after_loss': getattr(self, 'wait_after_loss', 1.0),
            'smart_check_interval': getattr(self, 'smart_check_interval', 15.0),
            'webhook_url': getattr(self, 'webhook_url', ''),
            'webhook_enabled': getattr(self, 'webhook_enabled', False),
            'webhook_interval': getattr(self, 'webhook_interval', 10),

            'dark_theme': getattr(self, 'dark_theme', True),
            'current_theme': getattr(self, 'current_theme', 'default'),
            'layout_settings': getattr(self.layout_manager, 'layouts', {}),

            'zoom_settings': {
                'auto_zoom_enabled': getattr(self.auto_zoom_var, 'get', lambda: False)() if hasattr(self, 'auto_zoom_var') else False,
                'zoom_out_steps': getattr(self.zoom_out_var, 'get', lambda: 5)() if hasattr(self, 'zoom_out_var') else 5,
                'zoom_in_steps': getattr(self.zoom_in_var, 'get', lambda: 3)() if hasattr(self, 'zoom_in_var') else 3,
                'step_delay': 0.1,
                'sequence_delay': 0.5,
                'zoom_cooldown': 2.0
            },
            'last_saved': datetime.now().isoformat()
        }
        
        settings_file = "default_settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
        except Exception as e:
            print(f'Error auto-saving settings: {e}')

    def save_preset(self):
        """Save current settings to a preset file (excluding webhooks and keybinds)"""
        try:
            # Ask user for preset name
            preset_name = simpledialog.askstring("Save Preset", "Enter preset name:")
            if not preset_name:
                return
            
            # Clean filename
            import re
            preset_name = re.sub(r'[<>:"/\\|?*]', '_', preset_name)
            
            # Collect all settings except webhooks and keybinds
            preset_data = {
                # Auto-purchase settings
                'auto_purchase_enabled': getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get() if hasattr(self, 'auto_purchase_var') else False,
                'auto_purchase_amount': getattr(self, 'auto_purchase_amount', 100),
                'loops_per_purchase': getattr(self, 'loops_per_purchase', 1),
                'point_coords': getattr(self, 'point_coords', {}),
                
                # PD Controller settings
                'kp': getattr(self, 'kp', 0.1),
                'kd': getattr(self, 'kd', 0.5),
                
                # Timing settings
                'scan_timeout': getattr(self, 'scan_timeout', 15.0),
                'wait_after_loss': getattr(self, 'wait_after_loss', 1.0),
                'purchase_delay_after_key': getattr(self, 'purchase_delay_after_key', 2.0),
                'purchase_click_delay': getattr(self, 'purchase_click_delay', 1.0),
                'purchase_after_type_delay': getattr(self, 'purchase_after_type_delay', 1.0),
                

                
                # Recovery settings
                'recovery_enabled': getattr(self, 'recovery_enabled', True),
                
                # Performance settings
                'silent_mode': getattr(self, 'silent_mode', False),
                'verbose_logging': getattr(self, 'verbose_logging', False),
                
                # Theme settings
                'dark_theme': getattr(self, 'dark_theme', True),
            }
            
            # Save to presets folder
            preset_file = os.path.join(self.presets_dir, f"{preset_name}.json")
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
            
            self.status_msg.config(text=f'Preset "{preset_name}" saved successfully!', foreground='green')
            print(f'✅ Preset saved: {preset_file}')
            
        except Exception as e:
            self.status_msg.config(text=f'Error saving preset: {e}', foreground='red')
            print(f'❌ Error saving preset: {e}')

    def load_preset(self):
        """Load settings from a preset file"""
        try:
            # Show file dialog to select preset
            preset_file = filedialog.askopenfilename(
                title="Load Preset",
                initialdir=self.presets_dir,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not preset_file:
                return
            
            # Load preset data
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)
            
            # Apply settings (excluding webhooks and keybinds)
            
            # Auto-purchase settings
            if hasattr(self, 'auto_purchase_var'):
                self.auto_purchase_var.set(preset_data.get('auto_purchase_enabled', False))
            self.auto_purchase_amount = preset_data.get('auto_purchase_amount', 100)
            if hasattr(self, 'amount_var'):
                self.amount_var.set(self.auto_purchase_amount)
            
            self.loops_per_purchase = preset_data.get('loops_per_purchase', 1)
            if hasattr(self, 'loops_var'):
                self.loops_var.set(self.loops_per_purchase)
            
            # Convert string keys back to integers for point_coords
            loaded_coords = preset_data.get('point_coords', {})
            self.point_coords = {}
            for key, value in loaded_coords.items():
                try:
                    int_key = int(key)
                    self.point_coords[int_key] = value
                except (ValueError, TypeError):
                    pass
            # Update point buttons if they exist
            for idx in range(1, 5):
                if hasattr(self, 'point_buttons') and idx in self.point_buttons:
                    self.update_point_button(idx)
            
            # Load fruit storage coordinates
            self.fruit_coords = preset_data.get('fruit_coords', {})
            
            # Load fruit storage settings
            self.fruit_storage_enabled = preset_data.get('fruit_storage_enabled', False)
            if hasattr(self, 'fruit_storage_var'):
                self.fruit_storage_var.set(self.fruit_storage_enabled)
            
            self.fruit_storage_key = preset_data.get('fruit_storage_key', '3')
            self.rod_key = preset_data.get('rod_key', '1')
            
            # Update fruit storage buttons if they exist
            if hasattr(self, 'fruit_key_button'):
                self.fruit_key_button.config(text=f'Key {self.fruit_storage_key} ✓')
            if hasattr(self, 'rod_key_button'):
                self.rod_key_button.config(text=f'Key {self.rod_key} ✓')
            if hasattr(self, 'fruit_point_button') and 'fruit_point' in self.fruit_coords:
                coords = self.fruit_coords['fruit_point']
                self.fruit_point_button.config(text=f'Fruit Point: {coords}')
            if hasattr(self, 'bait_point_button') and 'bait_point' in self.fruit_coords:
                coords = self.fruit_coords['bait_point']
                self.bait_point_button.config(text=f'Bait Point: {coords}')
            
            # PD Controller settings
            self.kp = preset_data.get('kp', 0.1)
            if hasattr(self, 'kp_var'):
                self.kp_var.set(self.kp)
            
            self.kd = preset_data.get('kd', 0.5)
            if hasattr(self, 'kd_var'):
                self.kd_var.set(self.kd)
            
            # Timing settings
            self.scan_timeout = preset_data.get('scan_timeout', 15.0)
            if hasattr(self, 'timeout_var'):
                self.timeout_var.set(self.scan_timeout)
            
            self.wait_after_loss = preset_data.get('wait_after_loss', 1.0)
            if hasattr(self, 'wait_var'):
                self.wait_var.set(self.wait_after_loss)
            
            self.purchase_delay_after_key = preset_data.get('purchase_delay_after_key', 2.0)
            self.purchase_click_delay = preset_data.get('purchase_click_delay', 1.0)
            self.purchase_after_type_delay = preset_data.get('purchase_after_type_delay', 1.0)
            

            
            # Recovery settings
            self.recovery_enabled = preset_data.get('recovery_enabled', True)
            
            # Performance settings
            self.silent_mode = preset_data.get('silent_mode', False)
            self.verbose_logging = preset_data.get('verbose_logging', False)
            
            # Theme settings
            new_theme = preset_data.get('dark_theme', True)
            if new_theme != self.dark_theme:
                self.dark_theme = new_theme
                self.apply_theme()
            

            
            preset_name = os.path.splitext(os.path.basename(preset_file))[0]
            self.status_msg.config(text=f'Preset "{preset_name}" loaded successfully!', foreground='green')
            print(f'✅ Preset loaded: {preset_file}')
            
            # Auto-save the loaded settings as current defaults
            self.auto_save_settings()
            
        except Exception as e:
            self.status_msg.config(text=f'Error loading preset: {e}', foreground='red')
            print(f'❌ Error loading preset: {e}')

    def load_basic_settings(self):
        """Load basic settings before UI creation"""
        settings_file = "default_settings.json"
        if not os.path.exists(settings_file):
            # Initialize with default settings
            self.settings = {
                'zoom_settings': {
                    'auto_zoom_enabled': False,
                    'zoom_out_steps': 5,
                    'zoom_in_steps': 8,
                    'step_delay': 0.1,
                    'sequence_delay': 0.5,
                    'zoom_cooldown': 2.0
                },
                'layout_settings': {}
            }
            return  # No saved settings, use defaults
            
        try:
            with open(settings_file, 'r') as f:
                preset_data = json.load(f)
            
            # Store full settings for access by other components
            self.settings = preset_data
            
            # Load basic settings that don't require UI elements
            self.auto_purchase_amount = preset_data.get('auto_purchase_amount', 100)
            self.loops_per_purchase = preset_data.get('loops_per_purchase', 1)
            
            # Convert string keys back to integers for point_coords
            loaded_coords = preset_data.get('point_coords', {})
            self.point_coords = {}
            for key, value in loaded_coords.items():
                try:
                    int_key = int(key)
                    self.point_coords[int_key] = value
                except (ValueError, TypeError):
                    pass
            self.kp = preset_data.get('kp', 0.1)
            self.kd = preset_data.get('kd', 0.5)
            self.scan_timeout = preset_data.get('scan_timeout', 15.0)
            self.wait_after_loss = preset_data.get('wait_after_loss', 1.0)
            self.smart_check_interval = preset_data.get('smart_check_interval', 15.0)
            self.webhook_url = preset_data.get('webhook_url', '')
            self.webhook_enabled = preset_data.get('webhook_enabled', False)
            self.webhook_interval = preset_data.get('webhook_interval', 10)

            self.fruit_storage_enabled = preset_data.get('fruit_storage_enabled', False)
            self.fruit_storage_key = preset_data.get('fruit_storage_key', '3')
            self.rod_key = preset_data.get('rod_key', '1')
            self.bait_point = preset_data.get('bait_point', '2')
            
            # Load fruit coordinates
            self.fruit_coords = preset_data.get('fruit_coords', {})
            
            self.dark_theme = preset_data.get('dark_theme', True)
            self.current_theme = preset_data.get('current_theme', 'default')
            
        except Exception as e:
            print(f'Error loading basic settings: {e}')
            # Initialize with default settings on error
            self.settings = {
                'zoom_settings': {
                    'auto_zoom_enabled': False,
                    'zoom_out_steps': 5,
                    'zoom_in_steps': 8,
                    'step_delay': 0.1,
                    'sequence_delay': 0.5,
                    'zoom_cooldown': 2.0
                },
                'layout_settings': {}
            }

    def load_ui_settings(self):
        """Load UI-specific settings after widgets are created"""
        settings_file = "default_settings.json"
        if not os.path.exists(settings_file):
            return  # No saved settings, use defaults
            
        try:
            with open(settings_file, 'r') as f:
                preset_data = json.load(f)
            
            # Update UI variables if they exist
            if hasattr(self, 'auto_purchase_var'):
                self.auto_purchase_var.set(preset_data.get('auto_purchase_enabled', False))
            if hasattr(self, 'amount_var'):
                self.amount_var.set(self.auto_purchase_amount)
            if hasattr(self, 'loops_var'):
                self.loops_var.set(self.loops_per_purchase)
            if hasattr(self, 'webhook_enabled_var'):
                self.webhook_enabled_var.set(self.webhook_enabled)
            if hasattr(self, 'webhook_url_var'):
                self.webhook_url_var.set(self.webhook_url)
            if hasattr(self, 'webhook_interval_var'):
                self.webhook_interval_var.set(self.webhook_interval)

            
            # Load OCR settings
            ocr_settings = preset_data.get('ocr_settings', {})
            if hasattr(self, 'ocr_enabled_var'):
                self.ocr_enabled_var.set(ocr_settings.get('enabled', True))
            if hasattr(self, 'tesseract_path_var'):
                self.tesseract_path_var.set(ocr_settings.get('tesseract_path', 
                    'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'))
            
            # Load zoom settings
            zoom_settings = preset_data.get('zoom_settings', {})
            if hasattr(self, 'auto_zoom_var'):
                self.auto_zoom_var.set(zoom_settings.get('auto_zoom_enabled', False))
            if hasattr(self, 'zoom_out_var'):
                self.zoom_out_var.set(zoom_settings.get('zoom_out_steps', 5))
            if hasattr(self, 'zoom_in_var'):
                self.zoom_in_var.set(zoom_settings.get('zoom_in_steps', 3))
            
            # Update managers with loaded settings
            if hasattr(self, 'ocr_manager') and ocr_settings.get('tesseract_path'):
                self.ocr_manager = OCRManager(ocr_settings['tesseract_path'])
            
            if hasattr(self, 'zoom_controller'):
                self.zoom_controller.update_settings({
                    'zoom_out_steps': zoom_settings.get('zoom_out_steps', 5),
                    'zoom_in_steps': zoom_settings.get('zoom_in_steps', 3),
                    'step_delay': zoom_settings.get('step_delay', 0.1),
                    'sequence_delay': zoom_settings.get('sequence_delay', 0.5),
                    'zoom_cooldown': zoom_settings.get('zoom_cooldown', 2.0)
                })
                # Also refresh from current GUI values
                self.update_zoom_controller_settings()
            
            # Load fishing location
            self.fishing_location = preset_data.get('fishing_location', None)
            
            # Update UI elements
            if hasattr(self, 'point_buttons'):
                self.update_point_buttons()
            if hasattr(self, 'fruit_point_button') or hasattr(self, 'bait_point_button') or hasattr(self, 'fishing_location_button'):
                self.update_fruit_storage_buttons()
            if hasattr(self, 'auto_update_btn'):
                self.update_auto_update_button()
            
        except Exception as e:
            print(f'Error loading UI settings: {e}')

    def update_point_buttons(self):
        """Update point button texts with coordinates"""
        for idx, coords in self.point_coords.items():
            if coords and idx in self.point_buttons:
                self.point_buttons[idx].config(text=f'Point {idx}: {coords}')
    
    def update_fruit_storage_buttons(self):
        """Update fruit storage button texts with coordinates"""
        if hasattr(self, 'fruit_coords'):
            if hasattr(self, 'fruit_point_button') and 'fruit_point' in self.fruit_coords:
                coords = self.fruit_coords['fruit_point']
                self.fruit_point_button.config(text=f'Fruit Point: {coords}')
            if hasattr(self, 'bait_point_button') and 'bait_point' in self.fruit_coords:
                coords = self.fruit_coords['bait_point']
                self.bait_point_button.config(text=f'Bait Point: {coords}')
        
        # Update fishing location button
        if hasattr(self, 'fishing_location_button') and hasattr(self, 'fishing_location') and self.fishing_location:
            coords = self.fishing_location
            self.fishing_location_button.config(text=f'🎯 Location: {coords}')

    def update_hotkey_labels(self):
        """Update hotkey label texts"""
        try:
            self.loop_key_label.config(text=self.hotkeys['toggle_loop'].upper())

            self.exit_key_label.config(text=self.hotkeys['exit'].upper())
            self.minimize_key_label.config(text=self.hotkeys['toggle_minimize'].upper())
        except AttributeError:
            pass  # Labels not created yet





def main():
    root = tk.Tk()
    app = HotkeyGUI(root)
    root.protocol('WM_DELETE_WINDOW', app.exit_app)
    root.mainloop()
if __name__ == '__main__':
    main()

def main():
    root = tk.Tk()
    app = HotkeyGUI(root)
    root.protocol('WM_DELETE_WINDOW', app.exit_app)
    root.mainloop()

if __name__ == '__main__':
    main()