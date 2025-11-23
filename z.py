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
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

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
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_loop_active = False
        self.overlay_active = False
        self.main_loop_thread = None
        self.recording_hotkey = None
        self.overlay_window = None
        self.overlay_drag_data = {'x': 0, 'y': 0, 'resize_edge': None, 'start_width': 0, 'start_height': 0, 'start_x': 0, 'start_y': 0}
        self.real_area = None
        self.is_clicking = False
        self.kp = 0.1
        self.kd = 0.5
        self.previous_error = 0
        self.scan_timeout = 15.0
        self.wait_after_loss = 1.0
        self.dpi_scale = self.get_dpi_scale()
        base_width = 172
        base_height = 495
        self.overlay_area = {'x': int(100 * self.dpi_scale), 'y': int(100 * self.dpi_scale), 'width': int(base_width * self.dpi_scale), 'height': int(base_height * self.dpi_scale)}
        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3', 'toggle_tray': 'f4'}
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
        
        # Auto-update settings
        self.auto_update_enabled = False
        self.last_update_check = 0
        self.update_check_interval = 300  # Check every 5min
        self.pending_update = None  # Store update info when main loop is active
        self.current_version = "1.4.4"  # Current version
        self.repo_url = "https://api.github.com/repos/arielldev/gpo-fishing/commits/main"
        
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
            "idle": 45.0           # Between actions
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
        self.tray_icon = None
        self.collapsible_sections = {}
        
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
        self.root.geometry('420x550')
        self.root.resizable(True, True)
        self.root.update_idletasks()
        self.root.minsize(400, 450)
        
        # Setup system tray if available
        if TRAY_AVAILABLE:
            self.setup_system_tray()
        
        # Check for updates immediately on startup if enabled, then start regular loop
        if self.auto_update_enabled:
            self.root.after(2000, self.startup_update_check)  # Check after 2 seconds for startup
        self.root.after(5000, self.start_auto_update_loop)  # Start regular loop after 5 seconds
    
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
        
        # App title with modern styling
        title = ttk.Label(header_frame, text='🎣 GPO Autofish', style='Title.TLabel')
        title.grid(row=0, column=0, pady=(0, 5))
        
        # Subtitle
        credits = ttk.Label(header_frame, text='by Ariel', 
                           style='Subtitle.TLabel')
        credits.grid(row=1, column=0, pady=(0, 15))
        
        # Modern control panel
        control_panel = ttk.Frame(header_frame)
        control_panel.grid(row=2, column=0, sticky='ew', pady=(0, 10))
        control_panel.columnconfigure(1, weight=1)  # Center spacing
        
        # Left controls
        left_controls = ttk.Frame(control_panel)
        left_controls.grid(row=0, column=0, sticky='w')
        
        self.theme_btn = ttk.Button(left_controls, text='☀ Light Mode', 
                                   command=self.toggle_theme, style='TButton')
        self.theme_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Right controls - removed Load button, only auto-save now
        right_controls = ttk.Frame(control_panel)
        right_controls.grid(row=0, column=2, sticky='e')
        
        # Auto-update toggle button
        self.auto_update_btn = ttk.Button(right_controls, text='🔄 Auto Update: OFF', 
                                         command=self.toggle_auto_update, style='TButton')
        self.auto_update_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        if TRAY_AVAILABLE:
            ttk.Button(right_controls, text='📌 Tray', command=self.minimize_to_tray,
                      style='TButton').pack(side=tk.LEFT)
        
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
        
        self.fish_counter_label = ttk.Label(status_frame, text='🐟 Fish: 0', style='Counter.TLabel')
        self.fish_counter_label.grid(row=0, column=2, padx=10, pady=8)
        
        # Second row - Just runtime (centered)
        self.runtime_label = ttk.Label(status_frame, text='⏱️ Runtime: 00:00:00', style='Counter.TLabel')
        self.runtime_label.grid(row=1, column=0, columnspan=3, padx=10, pady=8)
        
        current_row += 1
        
        # Create modern collapsible sections
        self.create_auto_purchase_section(current_row)
        current_row += 1
        
        self.create_pd_controller_section(current_row)
        current_row += 1
        
        self.create_timing_section(current_row)
        current_row += 1
        
        self.create_presets_section(current_row)
        current_row += 1
        
        self.create_hotkeys_section(current_row)
        current_row += 1
        
        self.create_webhook_section(current_row)
        current_row += 1
        
        # Discord join section at bottom
        self.create_discord_section(current_row)
        current_row += 1
        
        # Status message for dynamic updates
        self.status_msg = ttk.Label(self.main_frame, text='Ready to fish! 🎣', 
                                   font=('Segoe UI', 9), foreground='#58a6ff')
        self.status_msg.grid(row=current_row, column=0, pady=(10, 0))

    def capture_mouse_click(self, idx):
        """Start a listener to capture the next mouse click and store its coordinates."""  # inserted
        try:
            self.status_msg.config(text=f'Click anywhere to set Point {idx}...', foreground='blue')

            def _on_click(x, y, button, pressed):
                if pressed:
                    self.point_coords[idx] = (x, y)
                    try:
                        self.root.after(0, lambda: self.update_point_button(idx))
                        self.root.after(0, lambda: self.status_msg.config(text=f'Point {idx} set: ({x}, {y})', foreground='green'))
                        self.root.after(0, lambda: self.auto_save_settings())  # Auto-save when point is set
                    except Exception:
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
        
        # Type amount with state tracking
        self.set_recovery_state("typing", {"action": "typing_amount", "amount": amount})
        self.log(f'Typing amount: {amount}', "verbose")
        keyboard.write(amount)
        threading.Event().wait(self.purchase_after_type_delay)
        
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
        
        # Right-click point 4 to close menu with state tracking
        self.set_recovery_state("clicking", {"action": "right_click_point_4_close", "point": pts[4]})
        print(f'Right-clicking Point 4: {pts[4]}')
        self._right_click_at(pts[4])
        threading.Event().wait(self.purchase_click_delay)
        
        # Send webhook notification for auto purchase
        self.send_purchase_webhook(amount)
        print()

    def start_rebind(self, action):
        """Start recording a new hotkey"""  # inserted
        self.recording_hotkey = action
        self.status_msg.config(text=f'Press a key to rebind \'{action}\'...', foreground='blue')
        self.loop_rebind_btn.config(state='disabled')
        self.overlay_rebind_btn.config(state='disabled')
        self.exit_rebind_btn.config(state='disabled')
        self.tray_rebind_btn.config(state='disabled')
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
                elif self.recording_hotkey == 'toggle_overlay':
                    self.overlay_key_label.config(text=key_str.upper())
                elif self.recording_hotkey == 'exit':
                    self.exit_key_label.config(text=key_str.upper())
                elif self.recording_hotkey == 'toggle_tray':
                    self.tray_key_label.config(text=key_str.upper())
                
                self.recording_hotkey = None
                self.loop_rebind_btn.config(state='normal')
                self.overlay_rebind_btn.config(state='normal')
                self.exit_rebind_btn.config(state='normal')
                self.tray_rebind_btn.config(state='normal')
                self.status_msg.config(text=f'Hotkey set to {key_str.upper()}', foreground='green')
                self.register_hotkeys()
                return False  # Stop the listener
            except Exception as e:
                self.status_msg.config(text=f'Error setting hotkey: {e}', foreground='red')
                self.recording_hotkey = None
                self.loop_rebind_btn.config(state='normal')
                self.overlay_rebind_btn.config(state='normal')
                self.exit_rebind_btn.config(state='normal')
                self.tray_rebind_btn.config(state='normal')
                return False
        return False

    def register_hotkeys(self):
        """Register all hotkeys"""  # inserted
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkeys['toggle_loop'], self.toggle_main_loop)
            keyboard.add_hotkey(self.hotkeys['toggle_overlay'], self.toggle_overlay)
            keyboard.add_hotkey(self.hotkeys['exit'], self.exit_app)
            keyboard.add_hotkey(self.hotkeys['toggle_tray'], self.toggle_tray_hotkey)
        except Exception as e:
            print(f'Error registering hotkeys: {e}')
    
    def toggle_tray_hotkey(self):
        """Toggle between tray and normal window via F4 hotkey"""
        if TRAY_AVAILABLE:
            if self.root.state() == 'withdrawn':
                self.restore_from_tray()
            else:
                self.minimize_to_tray()
        else:
            print("System tray not available")
    



    def toggle_main_loop(self):
        """Toggle between Start/Pause/Resume with smart detection"""
        if not self.main_loop_active and not self.is_paused:
            # Starting fresh
            self.start_fishing()
        elif self.main_loop_active and not self.is_paused:
            # Currently running - pause it
            self.pause_fishing()
        elif not self.main_loop_active and self.is_paused:
            # Currently paused - resume it
            self.resume_fishing()
    
    def start_fishing(self):
        """Start fishing from scratch"""
        # Check auto-purchase points if enabled
        if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
            pts = getattr(self, 'point_coords', {})
            missing = [i for i in [1, 2, 3, 4] if not pts.get(i)]
            if missing:
                messagebox.showwarning('Auto Purchase: Points missing', f'Please set Point(s) {missing} before starting Auto Purchase.')
                return
        
        # Reset everything for fresh start
        self.main_loop_active = True
        self.is_paused = False
        self.start_time = time.time()
        self.total_paused_time = 0
        self.reset_fish_counter()
        
        # Clear any pending updates since we're starting fishing again
        if self.pending_update:
            self.pending_update = None
        
        # Update UI
        self.loop_status.config(text='● Main Loop: ACTIVE', style='StatusOn.TLabel')
        
        # Notify about auto-update status if enabled
        if self.auto_update_enabled:
            self.status_msg.config(text='Auto-update paused during fishing', foreground='orange')
        
        # Start the loop
        self.main_loop_thread = threading.Thread(target=self.main_loop, daemon=True)
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
        
        # Check for pending updates first, then check for new updates
        if self.pending_update:
            # Show the pending update dialog now that fishing stopped
            self.root.after(1000, lambda: self.show_pending_update())  # Small delay to let UI settle
        elif self.auto_update_enabled:
            import threading
            threading.Thread(target=self.check_for_updates, daemon=True).start()
        
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
            x = self.overlay_area['x']
            y = self.overlay_area['y']
            width = self.overlay_area['width']
            height = self.overlay_area['height']
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
            # Jump directly into the main loop detection
            self.main_loop()
        else:
            self.log('🎣 No fishing bar detected - starting fresh', "important")
            # Start from scratch with auto-purchase check and casting
            self.main_loop()

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
            self.send_discord_webhook()
            self.webhook_counter = 0

    def reset_fish_counter(self):
        """Reset fish counter when main loop starts"""
        self.fish_count = 0
        self.webhook_counter = 0
        try:
            self.root.after(0, lambda: self.fish_counter_label.config(text=f'🐟 Fish: {self.fish_count}'))
        except Exception:
            pass

    def send_discord_webhook(self):
        """Send Discord webhook with fishing progress"""
        if not self.webhook_url or not self.webhook_enabled:
            return
            
        try:
            import requests
            import json
            from datetime import datetime
            
            # Create embed with nice design
            embed = {
                "title": "🎣 GPO Autofish Progress",
                "description": f"Successfully caught **{self.webhook_interval}** fish!",
                "color": 0x00ff00,  # Green color
                "fields": [
                    {
                        "name": "🐟 Total Fish Caught",
                        "value": str(self.fish_count),
                        "inline": True
                    },
                    {
                        "name": "⏱️ Session Progress",
                        "value": f"{self.webhook_interval} fish in last interval",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "GPO Autofish - Open Source",
                    "icon_url": "https://cdn.discordapp.com/emojis/🎣.png"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed],
                "username": "GPO Autofish Bot",
                "avatar_url": "https://cdn.discordapp.com/emojis/🎣.png"
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                print(f"✅ Webhook sent: {self.webhook_interval} fish caught!")
            else:
                print(f"❌ Webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Webhook error: {e}")

    def send_purchase_webhook(self, amount):
        """Send Discord webhook when auto purchase runs"""
        if not self.webhook_url or not self.webhook_enabled:
            return
            
        try:
            import requests
            from datetime import datetime
            
            # Create embed for auto purchase
            embed = {
                "title": "🛒 GPO Autofish - Auto Purchase",
                "description": f"Successfully purchased **{amount}** bait!",
                "color": 0xffa500,  # Orange color
                "fields": [
                    {
                        "name": "🎣 Bait Purchased",
                        "value": str(amount),
                        "inline": True
                    },
                    {
                        "name": "🐟 Total Fish Caught",
                        "value": str(self.fish_count),
                        "inline": True
                    },
                    {
                        "name": "🔄 Status",
                        "value": "Auto purchase completed successfully",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "GPO Autofish - Auto Purchase System",
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed],
                "username": "GPO Autofish Bot"
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                print(f"✅ Purchase webhook sent: Bought {amount} bait!")
            else:
                print(f"❌ Purchase webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Purchase webhook error: {e}")

    def send_recovery_webhook(self, recovery_info):
        """Send Discord webhook when recovery system triggers"""
        if not self.webhook_url or not self.webhook_enabled:
            return
            
        try:
            import requests
            from datetime import datetime
            
            # Determine color based on recovery count
            if recovery_info["recovery_number"] == 1:
                color = 0xffff00  # Yellow for first recovery
            elif recovery_info["recovery_number"] <= 3:
                color = 0xffa500  # Orange for few recoveries
            else:
                color = 0xff0000  # Red for many recoveries
            
            # Create detailed embed for recovery
            embed = {
                "title": "🔄 GPO Autofish - Recovery Triggered",
                "description": f"Recovery #{recovery_info['recovery_number']} - System detected stuck state",
                "color": color,
                "fields": [
                    {
                        "name": "🚨 Stuck Action",
                        "value": recovery_info["stuck_state"],
                        "inline": True
                    },
                    {
                        "name": "⏱️ Stuck Duration",
                        "value": f"{recovery_info['stuck_duration']:.1f}s",
                        "inline": True
                    },
                    {
                        "name": "🔢 Recovery Count",
                        "value": str(recovery_info["recovery_number"]),
                        "inline": True
                    },
                    {
                        "name": "🐟 Fish Caught",
                        "value": str(self.fish_count),
                        "inline": True
                    },
                    {
                        "name": "📊 Status",
                        "value": "System automatically restarted",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "GPO Autofish - Recovry",
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add dev details if available
            if (self.dev_mode or self.verbose_logging) and recovery_info.get("state_details"):
                embed["fields"].append({
                    "name": "🔍 Dev Details",
                    "value": str(recovery_info["state_details"])[:1000],  # Limit length
                    "inline": False
                })
            
            payload = {
                "embeds": [embed],
                "username": "GPO Autofish Recovery Bot"
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                print(f"✅ Recovery webhook sent: Recovery #{recovery_info['recovery_number']}")
            else:
                print(f"❌ Recovery webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Recovery webhook error: {e}")

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
        """Main loop that runs when activated"""
        print('Main loop started')
        target_color = (85, 170, 255)
        dark_color = (25, 25, 25)
        white_color = (255, 255, 255)
        import time
        
        # Set dev mode based on verbose logging
        self.dev_mode = self.verbose_logging
        
        with mss.mss() as sct:
            # Auto-purchase sequence with detailed state tracking
            if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
                self.set_recovery_state("purchasing", {"sequence": "auto_purchase", "loops_per_purchase": getattr(self, 'loops_per_purchase', 1)})
                self.perform_auto_purchase_sequence()
            
            # Main fishing loop with improved state management
            while self.main_loop_active:
                try:
                    # Casting with state tracking
                    self.set_recovery_state("casting", {"action": "initial_cast"})
                    self.cast_line()
                    cast_time = time.time()
                    
                    # Fishing detection with state tracking
                    self.set_recovery_state("fishing", {"action": "blue_bar_detection", "scan_timeout": self.scan_timeout})
                    detected = False
                    last_detection_time = time.time()
                    was_detecting = False
                    print('Entering main detection loop with smart monitoring...')
                    
                    # Blue bar detection loop with timeout protection
                    detection_start_time = time.time()
                    while self.main_loop_active:
                        # Check if recovery is needed
                        if self.check_recovery_needed():
                            self.perform_recovery()
                            return
                        
                        # Force timeout if detection takes too long (prevents infinite loops)
                        current_time = time.time()
                        if current_time - detection_start_time > self.scan_timeout + 10:  # Extra 10s buffer
                            print(f'🚨 FORCE TIMEOUT: Detection loop exceeded {self.scan_timeout + 10}s, breaking...')
                            self.set_recovery_state("idle", {"action": "force_timeout_break"})
                            break
                        
                        x = self.overlay_area['x']
                        y = self.overlay_area['y']
                        width = self.overlay_area['width']
                        height = self.overlay_area['height']
                        monitor = {'left': x, 'top': y, 'width': width, 'height': height}
                        screenshot = sct.grab(monitor)
                        img = np.array(screenshot)
                        point1_x = None
                        point1_y = None
                        found_first = False
                        for row_idx in range(height):
                            for col_idx in range(width):
                                b, g, r = img[row_idx, col_idx, 0:3]
                                if r == target_color[0] and g == target_color[1] and b == target_color[2]:
                                    point1_x = x + col_idx
                                    point1_y = y + row_idx
                                    found_first = True
                                    break
                            if found_first:
                                break
                        current_time = time.time()
                        
                        if found_first:
                            detected = True
                            last_detection_time = current_time
                        else:
                            # No blue bar found - check if we should timeout (enhanced with smart tracking)
                            if not detected and current_time - cast_time > self.scan_timeout:
                                print(f'Cast timeout after {self.scan_timeout}s, recasting...')
                                self.set_recovery_state("casting", {"action": "recast_after_timeout", "timeout_duration": self.scan_timeout})
                                break  # Break out of detection loop to recast
                            
                            # If we were previously detecting but now lost it
                            if was_detecting:
                                print('Lost detection, waiting...')
                                threading.Event().wait(self.wait_after_loss)
                                was_detecting = False
                                self.check_and_purchase()
                                self.set_recovery_state("idle", {"action": "fish_caught_processing"})
                                break  # Break out of detection loop to start new cycle
                            
                            threading.Event().wait(0.1)
                            continue
                        point2_x = None
                        row_idx = point1_y - y
                        for col_idx in range(width - 1, -1, -1):
                            b, g, r = img[row_idx, col_idx, 0:3]
                            if r == target_color[0] and g == target_color[1] and b == target_color[2]:
                                point2_x = x + col_idx
                                break
                        if point2_x is None:
                            threading.Event().wait(0.1)
                            continue
                        temp_area_x = point1_x
                        temp_area_width = point2_x - point1_x + 1
                        temp_monitor = {'left': temp_area_x, 'top': y, 'width': temp_area_width, 'height': height}
                        temp_screenshot = sct.grab(temp_monitor)
                        temp_img = np.array(temp_screenshot)
                        dark_color = (25, 25, 25)
                        top_y = None
                        for row_idx in range(height):
                            found_dark = False
                            for col_idx in range(temp_area_width):
                                b, g, r = temp_img[row_idx, col_idx, 0:3]
                                if r == dark_color[0] and g == dark_color[1] and b == dark_color[2]:
                                    top_y = y + row_idx
                                    found_dark = True
                                    break
                            if found_dark:
                                break
                        bottom_y = None
                        for row_idx in range(height - 1, -1, -1):
                            found_dark = False
                            for col_idx in range(temp_area_width):
                                b, g, r = temp_img[row_idx, col_idx, 0:3]
                                if r == dark_color[0] and g == dark_color[1] and b == dark_color[2]:
                                    bottom_y = y + row_idx
                                    found_dark = True
                                    break
                            if found_dark:
                                break
                        if top_y is None or bottom_y is None:
                            threading.Event().wait(0.1)
                            continue
                        self.real_area = {'x': temp_area_x, 'y': top_y, 'width': temp_area_width, 'height': bottom_y - top_y + 1}
                        real_x = self.real_area['x']
                        real_y = self.real_area['y']
                        real_width = self.real_area['width']
                        real_height = self.real_area['height']
                        real_monitor = {'left': real_x, 'top': real_y, 'width': real_width, 'height': real_height}
                        real_screenshot = sct.grab(real_monitor)
                        real_img = np.array(real_screenshot)
                        white_color = (255, 255, 255)
                        white_top_y = None
                        white_bottom_y = None
                        for row_idx in range(real_height):
                            for col_idx in range(real_width):
                                b, g, r = real_img[row_idx, col_idx, 0:3]
                                if r == white_color[0] and g == white_color[1] and b == white_color[2]:
                                    white_top_y = real_y + row_idx
                                    break
                            if white_top_y is not None:
                                break
                        for row_idx in range(real_height - 1, -1, -1):
                            for col_idx in range(real_width):
                                b, g, r = real_img[row_idx, col_idx, 0:3]
                                if r == white_color[0] and g == white_color[1] and b == white_color[2]:
                                    white_bottom_y = real_y + row_idx
                                    break
                            if white_bottom_y is not None:
                                break
                        if white_top_y is not None and white_bottom_y is not None:
                            white_height = white_bottom_y - white_top_y + 1
                            max_gap = white_height * 2
                        dark_sections = []
                        current_section_start = None
                        gap_counter = 0
                        for row_idx in range(real_height):
                            has_dark = False
                            for col_idx in range(real_width):
                                b, g, r = real_img[row_idx, col_idx, 0:3]
                                if r == dark_color[0] and g == dark_color[1] and b == dark_color[2]:
                                    has_dark = True
                                    break
                            if has_dark:
                                gap_counter = 0
                                if current_section_start is None:
                                    current_section_start = real_y + row_idx
                            else:
                                if current_section_start is not None:
                                    gap_counter += 1
                                    if gap_counter > max_gap:
                                        section_end = real_y + row_idx - gap_counter
                                        dark_sections.append({'start': current_section_start, 'end': section_end, 'middle': (current_section_start + section_end) // 2})
                                        current_section_start = None
                                        gap_counter = 0
                        if current_section_start is not None:
                            section_end = real_y + real_height - 1 - gap_counter
                            dark_sections.append({'start': current_section_start, 'end': section_end, 'middle': (current_section_start + section_end) // 2})
                        if dark_sections and white_top_y is not None:
                            # If this is the first time detecting this fish, increment counter
                            if not was_detecting:
                                self.increment_fish_counter()
                                self.set_recovery_state("idle")  # Reset to idle after successful catch
                            was_detecting = True
                            last_detection_time = time.time()
                            for section in dark_sections:
                                section['size'] = section['end'] - section['start'] + 1
                            largest_section = max(dark_sections, key=lambda s: s['size'])
                            print(f'y:{white_top_y}')
                            print(f"y:{largest_section['middle']}")
                            raw_error = largest_section['middle'] - white_top_y
                            normalized_error = raw_error / real_height if real_height > 0 else raw_error
                            derivative = normalized_error - self.previous_error
                            self.previous_error = normalized_error
                            pd_output = self.kp * normalized_error + self.kd * derivative
                            print(f'Error: {raw_error}px ({normalized_error:.3f} normalized), PD Output: {pd_output:.2f}')
                            
                            # Decide whether to hold or release based on PD output
                            # Positive error/output = middle is below, need to go up = hold click
                            # Negative error/output = middle is above, need to go down = release click
                            if pd_output > 0:
                                # Need to accelerate up - hold left click
                                if not self.is_clicking:
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                    self.is_clicking = True
                            else:
                                # Need to accelerate down - release left click
                                if self.is_clicking:
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                    self.is_clicking = False
                            
                            print()
                        threading.Event().wait(0.1)
                    
                    # End of detection loop - set idle state before next iteration
                    self.set_recovery_state("idle", {"action": "detection_loop_complete"})
                    
                except Exception as e:
                    print(f'🚨 Main loop error: {e}')
                    self.log(f'Main loop error: {e}', "error")
                    # Set recovery state and continue to next iteration
                    self.set_recovery_state("idle", {"action": "error_recovery", "error": str(e)})
                    threading.Event().wait(1.0)  # Brief pause before retry
                    
        print('Main loop stopped')
        
        # Ensure mouse is released when loop stops
        if self.is_clicking:
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.is_clicking = False
            except:
                pass
    
    def check_recovery_needed(self):
        """smart recovery - detects specific stuck actions with detailed logging"""
        if not self.recovery_enabled or not self.main_loop_active:
            return False
            
        current_time = time.time()
        
        # Check more frequently for faster recovery (every 10 seconds instead of 15)
        if current_time - self.last_smart_check < 10.0:
            return False
            
        self.last_smart_check = current_time
        
        # Check if current state has been running too long
        state_duration = current_time - self.state_start_time
        max_duration = self.max_state_duration.get(self.current_state, 60.0)
        
        # More aggressive timeout for idle state (common stuck state)
        if self.current_state == "idle" and state_duration > 30.0:  # Reduced from 45s to 30s
            max_duration = 30.0
        
        if state_duration > max_duration:
            # Create detailed stuck action report
            stuck_info = {
                "action": self.current_state,
                "duration": state_duration,
                "max_allowed": max_duration,
                "details": self.state_details.copy(),
                "timestamp": current_time
            }
            self.stuck_actions.append(stuck_info)
            
            # Log with different levels based on action type
            if self.current_state == "fishing":
                # Blue bar detection rarely gets stuck, this is unusual
                self.log(f'🚨 UNUSUAL: Fishing state stuck for {state_duration:.0f}s (blue bar detection issue?)', "error")
            elif self.current_state == "purchasing":
                self.log(f'⚠️ Purchase sequence stuck for {state_duration:.0f}s - likely menu/UI issue', "error")
            elif self.current_state == "menu_opening":
                self.log(f'⚠️ Menu opening stuck for {state_duration:.0f}s - E key or game response issue', "error")
            elif self.current_state == "typing":
                self.log(f'⚠️ Typing stuck for {state_duration:.0f}s - input field or keyboard issue', "error")
            elif self.current_state == "clicking":
                self.log(f'⚠️ Click action stuck for {state_duration:.0f}s - UI element or mouse issue', "error")
            elif self.current_state == "idle":
                self.log(f'� IDLE SSTUCK: System idle for {state_duration:.0f}s - main loop may be frozen', "error")
            else:
                self.log(f'⚠️ State "{self.current_state}" stuck for {state_duration:.0f}s (max: {max_duration}s)', "error")
            
            # Dev mode detailed logging
            if self.dev_mode or self.verbose_logging:
                self.log(f'🔍 DEV: Stuck action details: {stuck_info}', "verbose")
            
            return True
            
        # More aggressive check for completely frozen state (reduced from 2 minutes to 90 seconds)
        time_since_activity = current_time - self.last_activity_time
        if time_since_activity > 90:  # 90 seconds instead of 120
            self.log(f'⚠️ Complete freeze detected - no activity for {time_since_activity:.0f}s', "error")
            return True
            
        return False
    
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
    
    def perform_recovery(self):
        """smart recovery with detailed logging and webhook notifications"""
        if not self.main_loop_active:
            return
            
        current_time = time.time()
        
        # Prevent spam recovery (reduced from 15 to 10 seconds for faster response)
        if current_time - self.last_recovery_time < 10:
            return
            
        self.recovery_count += 1
        self.last_recovery_time = current_time
        
        # Create detailed recovery report
        recovery_info = {
            "recovery_number": self.recovery_count,
            "stuck_state": self.current_state,
            "stuck_duration": current_time - self.state_start_time,
            "state_details": self.state_details.copy(),
            "recent_stuck_actions": self.stuck_actions[-3:] if len(self.stuck_actions) > 0 else [],
            "timestamp": current_time
        }
        
        self.log(f'🔄 Smart Recovery #{self.recovery_count} - State: {self.current_state} - Restarting...', "error")
        
        # Dev mode detailed recovery logging
        if self.dev_mode or self.verbose_logging:
            self.log(f'🔍 DEV: Recovery details: {recovery_info}', "verbose")
        
        # Send webhook notification about recovery
        self.send_recovery_webhook(recovery_info)
        
        # Force release mouse if stuck clicking
        if self.is_clicking:
            try:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.is_clicking = False
                self.log('🔧 Released stuck mouse click', "verbose")
            except Exception as e:
                self.log(f'⚠️ Error releasing mouse: {e}', "error")
        
        # Reset all timers and state
        self.last_activity_time = current_time
        self.last_fish_time = current_time
        self.set_recovery_state("idle", {"action": "recovery_reset"})
        self.stuck_actions.clear()  # Clear stuck actions after recovery
        
        # Stop current loop
        self.main_loop_active = False
        
        # Wait a moment for cleanup
        threading.Event().wait(2.0)  # Increased wait time for better cleanup
        
        # Restart the loop with better error handling
        try:
            if hasattr(self, 'main_loop_thread') and self.main_loop_thread and self.main_loop_thread.is_alive():
                self.main_loop_thread.join(timeout=5.0)  # Increased timeout
        except Exception as e:
            self.log(f'⚠️ Error joining thread: {e}', "error")
        
        # Restart with fresh state
        self.main_loop_active = True
        self.main_loop_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.main_loop_thread.start()
        
        self.log('✅ Smart Recovery complete - Enhanced monitoring active', "important")
    
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


    def toggle_overlay(self):
        """Toggle the overlay on/off"""
        self.overlay_active = not self.overlay_active
        if self.overlay_active:
            self.overlay_status.config(text='● Overlay: ACTIVE', style='StatusOn.TLabel')
            self.create_overlay()
            print(f'Overlay activated at: {self.overlay_area}')
        else:
            self.overlay_status.config(text='● Overlay: OFF', style='StatusOff.TLabel')
            self.destroy_overlay()
            print(f'Overlay deactivated. Saved area: {self.overlay_area}')

    def create_overlay(self):
        """Create a draggable, resizable overlay window"""
        if self.overlay_window is not None:
            return
        
        # Create overlay window
        self.overlay_window = tk.Toplevel(self.root)
        
        # Remove window decorations (title bar, borders)
        self.overlay_window.overrideredirect(True)
        
        # Set window properties
        self.overlay_window.attributes('-alpha', 0.5)  # Semi-transparent
        self.overlay_window.attributes('-topmost', True)  # Always on top
        
        # Remove minimum size restrictions
        self.overlay_window.minsize(1, 1)
        
        # Set geometry from saved area
        x = self.overlay_area['x']
        y = self.overlay_area['y']
        width = self.overlay_area['width']
        height = self.overlay_area['height']
        geometry = f"{width}x{height}+{x}+{y}"
        self.overlay_window.geometry(geometry)
        
        # Create frame with border (using #55aaff color)
        frame = tk.Frame(self.overlay_window, bg='#55aaff', highlightthickness=2, highlightbackground='#55aaff')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events for dragging and resizing
        self.overlay_window.bind("<ButtonPress-1>", self.start_overlay_action)
        self.overlay_window.bind("<B1-Motion>", self.overlay_motion)
        self.overlay_window.bind("<Motion>", self.update_cursor)
        self.overlay_window.bind("<Configure>", self.on_overlay_configure)
        
        # Bind to frame as well
        frame.bind("<ButtonPress-1>", self.start_overlay_action)
        frame.bind("<B1-Motion>", self.overlay_motion)
        frame.bind("<Motion>", self.update_cursor)

    def get_resize_edge(self, x, y):
        """Determine which edge/corner is near the mouse"""
        width = self.overlay_window.winfo_width()
        height = self.overlay_window.winfo_height()
        edge_size = 10
        on_left = x < edge_size
        on_right = x > width - edge_size
        on_top = y < edge_size
        on_bottom = y > height - edge_size
        
        if on_top and on_left:
            return "nw"
        elif on_top and on_right:
            return "ne"
        elif on_bottom and on_left:
            return "sw"
        elif on_bottom and on_right:
            return "se"
        elif on_left:
            return "w"
        elif on_right:
            return "e"
        elif on_top:
            return "n"
        elif on_bottom:
            return "s"
        return None

    def update_cursor(self, event):
        """Update cursor based on position"""  # inserted
        edge = self.get_resize_edge(event.x, event.y)
        cursor_map = {'nw': 'size_nw_se', 'ne': 'size_ne_sw', 'sw': 'size_ne_sw', 'se': 'size_nw_se', 'n': 'size_ns', 's': 'size_ns', 'e': 'size_we', 'w': 'size_we', None: 'arrow'}
        self.overlay_window.config(cursor=cursor_map.get(edge, 'arrow'))

    def start_overlay_action(self, event):
        """Start dragging or resizing the overlay"""  # inserted
        self.overlay_drag_data['x'] = event.x
        self.overlay_drag_data['y'] = event.y
        self.overlay_drag_data['resize_edge'] = self.get_resize_edge(event.x, event.y)
        self.overlay_drag_data['start_width'] = self.overlay_window.winfo_width()
        self.overlay_drag_data['start_height'] = self.overlay_window.winfo_height()
        self.overlay_drag_data['start_x'] = self.overlay_window.winfo_x()
        self.overlay_drag_data['start_y'] = self.overlay_window.winfo_y()

    def overlay_motion(self, event):
        """Handle dragging or resizing the overlay"""
        edge = self.overlay_drag_data['resize_edge']
        
        if edge is None:
            # Dragging
            x = self.overlay_window.winfo_x() + event.x - self.overlay_drag_data['x']
            y = self.overlay_window.winfo_y() + event.y - self.overlay_drag_data['y']
            self.overlay_window.geometry(f'+{x}+{y}')
        else:
            # Resizing
            dx = event.x - self.overlay_drag_data['x']
            dy = event.y - self.overlay_drag_data['y']
            
            new_width = self.overlay_drag_data['start_width']
            new_height = self.overlay_drag_data['start_height']
            new_x = self.overlay_drag_data['start_x']
            new_y = self.overlay_drag_data['start_y']
            
            # Handle horizontal resize
            if 'e' in edge:
                new_width = max(1, self.overlay_drag_data['start_width'] + dx)
            elif 'w' in edge:
                new_width = max(1, self.overlay_drag_data['start_width'] - dx)
                new_x = self.overlay_drag_data['start_x'] + dx
            
            # Handle vertical resize
            if 's' in edge:
                new_height = max(1, self.overlay_drag_data['start_height'] + dy)
            elif 'n' in edge:
                new_height = max(1, self.overlay_drag_data['start_height'] - dy)
                new_y = self.overlay_drag_data['start_y'] + dy
            
            self.overlay_window.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")

    def on_overlay_configure(self, event=None):
        """Save overlay position and size when it changes"""  # inserted
        if self.overlay_window is not None:
            self.overlay_area['x'] = self.overlay_window.winfo_x()
            self.overlay_area['y'] = self.overlay_window.winfo_y()
            self.overlay_area['width'] = self.overlay_window.winfo_width()
            self.overlay_area['height'] = self.overlay_window.winfo_height()
        return None

    def destroy_overlay(self):
        """Destroy the overlay window"""
        if self.overlay_window is not None:
            self.overlay_area['x'] = self.overlay_window.winfo_x()
            self.overlay_area['y'] = self.overlay_window.winfo_y()
            self.overlay_area['width'] = self.overlay_window.winfo_width()
            self.overlay_area['height'] = self.overlay_window.winfo_height()
            self.overlay_window.destroy()
            self.overlay_window = None

    def exit_app(self):
        """Exit the application"""
        print('Exiting application...')
        self.main_loop_active = False
        
        # Auto-save settings before exit
        self.auto_save_settings()

        # Stop system tray if running
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        # Destroy overlay window if it exists
        if self.overlay_window is not None:
            try:
                self.overlay_window.destroy()
                self.overlay_window = None
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
        ToolTip(help_btn, "Automatically buy bait after catching fish. Requires setting Points 1-4.")
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
        self.point_coords = {1: None, 2: None, 3: None, 4: None}
        
        for i in range(1, 5):
            ttk.Label(frame, text=f'Point {i}:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
            self.point_buttons[i] = ttk.Button(frame, text=f'Point {i}', command=lambda idx=i: self.capture_mouse_click(idx))
            self.point_buttons[i].grid(row=row, column=1, pady=5, sticky='w')
            help_btn = ttk.Button(frame, text='?', width=3)
            help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
            
            tooltips = {
                1: "Click to set: yes/buy button (same area)",
                2: "Click to set: Input amount area (also ... area)", 
                3: "Click to set: Close button",
                4: "Click to set: Where you want to throw the rod at. (location on the screen where the water is)"
            }
            ToolTip(help_btn, tooltips[i])
            row += 1

    def create_pd_controller_section(self, start_row):
        """Create the PD controller collapsible section"""
        section = CollapsibleFrame(self.main_frame, "⚙️ PD Controller", start_row)
        # Start collapsed by default
        section.is_expanded = False
        section.content_frame.pack_forget()
        section.toggle_btn.config(text='+')
        self.collapsible_sections['pd_controller'] = section
        frame = section.get_content_frame()
        
        # Configure frame for centering
        frame.columnconfigure((0, 1, 2), weight=1)
        
        row = 0
        ttk.Label(frame, text='Kp (Proportional):').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.kp_var = tk.DoubleVar(value=self.kp)
        kp_spinbox = ttk.Spinbox(frame, from_=0.0, to=2.0, increment=0.1, textvariable=self.kp_var, width=10)
        kp_spinbox.grid(row=row, column=1, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "How strongly to react to fish position. Higher = more aggressive corrections")
        self.kp_var.trace_add('write', lambda *args: setattr(self, 'kp', self.kp_var.get()))
        row += 1
        
        ttk.Label(frame, text='Kd (Derivative):').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.kd_var = tk.DoubleVar(value=self.kd)
        kd_spinbox = ttk.Spinbox(frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.kd_var, width=10)
        kd_spinbox.grid(row=row, column=1, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Smooths movement to prevent overshooting. Higher = smoother but slower")
        self.kd_var.trace_add('write', lambda *args: setattr(self, 'kd', self.kd_var.get()))

    def create_timing_section(self, start_row):
        """Create the timing settings collapsible section"""
        section = CollapsibleFrame(self.main_frame, "⏱️ Timing Settings", start_row)
        # Start collapsed by default
        section.is_expanded = False
        section.content_frame.pack_forget()
        section.toggle_btn.config(text='+')
        self.collapsible_sections['timing'] = section
        frame = section.get_content_frame()
        
        # Configure frame for centering
        frame.columnconfigure((0, 1, 2), weight=1)
        
        row = 0
        ttk.Label(frame, text='Scan Timeout (s):').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.timeout_var = tk.DoubleVar(value=self.scan_timeout)
        timeout_spinbox = ttk.Spinbox(frame, from_=1.0, to=60.0, increment=1.0, textvariable=self.timeout_var, width=10)
        timeout_spinbox.grid(row=row, column=1, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "How long to wait for fish before recasting line (seconds)")
        self.timeout_var.trace_add('write', lambda *args: setattr(self, 'scan_timeout', self.timeout_var.get()))
        row += 1
        
        ttk.Label(frame, text='Wait After Loss (s):').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.wait_var = tk.DoubleVar(value=self.wait_after_loss)
        wait_spinbox = ttk.Spinbox(frame, from_=0.0, to=10.0, increment=0.1, textvariable=self.wait_var, width=10)
        wait_spinbox.grid(row=row, column=1, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Pause time after losing a fish before recasting (seconds)")
        self.wait_var.trace_add('write', lambda *args: setattr(self, 'wait_after_loss', self.wait_var.get()))

    def create_presets_section(self, start_row):
        """Create the presets save/load section"""
        section = CollapsibleFrame(self.main_frame, "💾 Presets", start_row)
        frame = section.get_content_frame()
        frame.columnconfigure(1, weight=1)  # Center column expands
        
        row = 0
        
        # Save preset button (centered layout like point buttons)
        ttk.Label(frame, text='Save:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        save_btn = ttk.Button(frame, text='💾 Save Preset', command=self.save_preset)
        save_btn.grid(row=row, column=1, pady=5, sticky='w')
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Save current settings (excluding webhooks and keybinds) to a preset file")
        row += 1
        
        # Load preset button (centered layout like point buttons)
        ttk.Label(frame, text='Load:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        load_btn = ttk.Button(frame, text='📁 Load Preset', command=self.load_preset)
        load_btn.grid(row=row, column=1, pady=5, sticky='w')
        help_btn2 = ttk.Button(frame, text='?', width=3)
        help_btn2.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn2, "Load settings from a preset file")

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
        
        ttk.Label(frame, text='Toggle Overlay:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.overlay_key_label = ttk.Label(frame, text=self.hotkeys['toggle_overlay'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.overlay_key_label.grid(row=row, column=1, pady=5)
        self.overlay_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_overlay'))
        self.overlay_rebind_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Show/hide blue detection area overlay")
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
        
        ttk.Label(frame, text='Toggle Tray:').grid(row=row, column=0, sticky='e', pady=5, padx=(0, 10))
        self.tray_key_label = ttk.Label(frame, text=self.hotkeys['toggle_tray'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.tray_key_label.grid(row=row, column=1, pady=5)
        self.tray_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_tray'))
        self.tray_rebind_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Toggle between system tray and normal window")

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
        
        # Test webhook button
        test_btn = ttk.Button(frame, text='Test Webhook', command=self.test_webhook)
        test_btn.grid(row=row, column=0, columnspan=2, pady=10)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=2, padx=(10, 0), pady=5)
        ToolTip(help_btn, "Send a test message to verify webhook is working")

    def create_discord_section(self, start_row):
        """Create the Discord join section at the bottom"""
        discord_frame = ttk.Frame(self.main_frame)
        discord_frame.grid(row=start_row, column=0, sticky='ew', pady=(25, 10))
        discord_frame.columnconfigure(0, weight=1)
        
        # Try to load Discord icon, fallback to text if not available
        discord_icon = None
        try:
            from PIL import Image, ImageTk
            import os
            if os.path.exists("images/discord.png"):
                img = Image.open("images/discord.png")
                img = img.resize((24, 24), Image.Resampling.LANCZOS)
                discord_icon = ImageTk.PhotoImage(img)
        except:
            pass  # Fallback to text-only button
        
        button_bg = '#21262d' if self.dark_theme else '#f6f8fa'
        button_fg = '#58a6ff' if self.dark_theme else '#0969da'
        button_hover_bg = '#30363d' if self.dark_theme else '#f3f4f6'
        
        if discord_icon:
            discord_btn = tk.Button(discord_frame, text='  Join our Discord!', 
                                  image=discord_icon, compound='left',
                                  command=self.open_discord,
                                  bg=button_bg, fg=button_fg,
                                  activebackground=button_hover_bg,
                                  activeforeground=button_fg,
                                  relief='flat', borderwidth=1,
                                  font=('Segoe UI', 9),
                                  cursor='hand2',
                                  padx=10, pady=5)
            discord_btn.image = discord_icon
        else:
            discord_btn = tk.Button(discord_frame, text='💬 Join our Discord!', 
                                  command=self.open_discord,
                                  bg=button_bg, fg=button_fg,
                                  activebackground=button_hover_bg,
                                  activeforeground=button_fg,
                                  relief='flat', borderwidth=1,
                                  font=('Segoe UI', 9),
                                  cursor='hand2',
                                  padx=10, pady=5)
        
        discord_btn.pack(pady=5, padx=10, fill='x')
        
        # Add combined hover effects and tooltip
        tooltip_window = None
        
        def on_enter(e):
            nonlocal tooltip_window
            discord_btn.config(bg=button_hover_bg)
            
            # Show tooltip
            if tooltip_window is None:
                x = discord_btn.winfo_rootx() + 20
                y = discord_btn.winfo_rooty() + 20
                
                tooltip_window = tk.Toplevel(discord_btn)
                tooltip_window.wm_overrideredirect(True)
                tooltip_window.wm_attributes('-topmost', True)
                tooltip_window.wm_geometry(f"+{x}+{y}")
                
                label = tk.Label(tooltip_window, text="Click to join our Discord community!", 
                               justify='left', background="#ffffe0", relief='solid', 
                               borderwidth=1, font=("Arial", 9), padx=5, pady=3)
                label.pack()
        
        def on_leave(e):
            nonlocal tooltip_window
            discord_btn.config(bg=button_bg)
            
            # Hide tooltip
            if tooltip_window:
                tooltip_window.destroy()
                tooltip_window = None
        
        discord_btn.bind("<Enter>", on_enter)
        discord_btn.bind("<Leave>", on_leave)

    def open_discord(self):
        """Open Discord invite link in browser"""
        import webbrowser
        try:
            webbrowser.open('https://discord.gg/5Gtsgv46ce')
            self.status_msg.config(text='Opened Discord invite', foreground='#0DA50DFF')
        except Exception as e:
            self.status_msg.config(text=f'Error opening Discord: {e}', foreground='red')

    def toggle_auto_update(self):
        """Toggle auto-update feature on/off"""
        self.auto_update_enabled = not self.auto_update_enabled
        
        if self.auto_update_enabled:
            self.auto_update_btn.config(text='🔄 Auto Update: ON')
            if self.main_loop_active:
                self.status_msg.config(text='Auto-update enabled (will check when fishing stops)', foreground='#58a6ff')
            else:
                self.status_msg.config(text='Auto-update enabled - checking for updates...', foreground='#58a6ff')
                # Start update checking thread only if main loop is not active
                import threading
                threading.Thread(target=self.check_for_updates, daemon=True).start()
        else:
            self.auto_update_btn.config(text='🔄 Auto Update: OFF')
            self.status_msg.config(text='Auto-update disabled', foreground='orange')
        
        # Auto-save the setting immediately
        self.auto_save_settings()

    def check_for_updates(self):
        """Check for updates from GitHub repository"""
        # Don't check for updates while main loop is running
        if self.main_loop_active:
            return
            
        try:
            import requests
            import time
            
            current_time = time.time()
            if current_time - self.last_update_check < self.update_check_interval:
                return  # Don't check too frequently
            
            self.last_update_check = current_time
            
            # Get latest commit info from GitHub API
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                latest_commit = commit_data['sha'][:7]  # Short commit hash
                commit_message = commit_data['commit']['message'].split('\n')[0]  # First line only
                commit_date = commit_data['commit']['committer']['date']
                
                # Check if we have a newer commit (simple check)
                if self.should_update(commit_date):
                    self.root.after(0, lambda: self.prompt_update(latest_commit, commit_message))
                else:
                    self.root.after(0, lambda: self.status_msg.config(text='✅ Up to date!', foreground='green'))
            else:
                self.root.after(0, lambda: self.status_msg.config(text='❌ Update check failed', foreground='red'))
                
        except Exception as e:
            self.root.after(0, lambda: self.status_msg.config(text=f'Update check error: {str(e)[:30]}...', foreground='red'))

    def should_update(self, commit_date):
        """Simple check if we should update based on commit date"""
        try:
            from datetime import datetime
            import os
            
            # Get current file modification time
            current_file_time = os.path.getmtime(__file__)
            
            # Parse GitHub commit date
            commit_time = datetime.fromisoformat(commit_date.replace('Z', '+00:00')).timestamp()
            
            # Update if commit is newer than current file
            return commit_time > current_file_time
        except:
            return False  # Don't update if we can't determine

    def prompt_update(self, commit_hash, commit_message):
        """Prompt user about available update"""
        # Don't show update dialog while main loop is running
        if self.main_loop_active:
            # Store update info to show later when fishing stops
            self.pending_update = {
                'commit_hash': commit_hash,
                'commit_message': commit_message
            }
            self.status_msg.config(text='Update available - will prompt when fishing stops', foreground='#58a6ff')
            return
        
        import tkinter.messagebox as msgbox
        
        message = f"New update available!\n\nLatest commit: {commit_hash}\nChanges: {commit_message}\n\nWould you like to download the update?"
        
        if msgbox.askyesno("Update Available", message):
            self.download_update()
        else:
            self.status_msg.config(text='Update skipped', foreground='orange')

    def show_pending_update(self):
        """Show the pending update dialog that was delayed during fishing"""
        if not self.pending_update:
            return
            
        import tkinter.messagebox as msgbox
        
        commit_hash = self.pending_update['commit_hash']
        commit_message = self.pending_update['commit_message']
        
        message = f"Update available (found while fishing)!\n\nLatest commit: {commit_hash}\nChanges: {commit_message}\n\nWould you like to download the update?"
        
        if msgbox.askyesno("Update Available", message):
            self.download_update()
        else:
            self.status_msg.config(text='Update skipped', foreground='orange')
        
        # Clear the pending update
        self.pending_update = None

    def startup_update_check(self):
        """Check for updates immediately on startup (bypasses interval check)"""
        if not self.auto_update_enabled or self.main_loop_active:
            return
            
        # Run immediate update check in background thread
        import threading
        threading.Thread(target=self.immediate_update_check, daemon=True).start()

    def immediate_update_check(self):
        """Perform update check without interval restrictions"""
        try:
            import requests
            import time
            
            # Update last check time
            self.last_update_check = time.time()
            
            # Get latest commit info from GitHub API
            response = requests.get(self.repo_url, timeout=10)
            if response.status_code == 200:
                commit_data = response.json()
                latest_commit = commit_data['sha'][:7]  # Short commit hash
                commit_message = commit_data['commit']['message'].split('\n')[0]  # First line only
                commit_date = commit_data['commit']['committer']['date']
                
                # Check if we have a newer commit (simple check)
                if self.should_update(commit_date):
                    self.root.after(0, lambda: self.prompt_update(latest_commit, commit_message))
                else:
                    self.root.after(0, lambda: self.status_msg.config(text='✅ Up to date!', foreground='green'))
            else:
                self.root.after(0, lambda: self.status_msg.config(text='❌ Update check failed', foreground='red'))
                
        except Exception as e:
            self.root.after(0, lambda: self.status_msg.config(text=f'Update check error: {str(e)[:30]}...', foreground='red'))

    def download_update(self):
        """Download and apply update automatically while preserving user settings"""
        try:
            import requests
            import os
            import sys
            import shutil
            import zipfile
            import tempfile
            from datetime import datetime
            
            self.status_msg.config(text='Downloading update...', foreground='#58a6ff')
            
            # Download the entire repository as ZIP
            zip_url = "https://github.com/arielldev/gpo-fishing/archive/refs/heads/main.zip"
            response = requests.get(zip_url, timeout=60)
            
            if response.status_code == 200:
                # Create temporary directory for extraction
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_path = os.path.join(temp_dir, "update.zip")
                    
                    # Save ZIP file
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Extract ZIP
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find extracted folder (usually repo-name-main)
                    extracted_folder = None
                    for item in os.listdir(temp_dir):
                        if os.path.isdir(os.path.join(temp_dir, item)) and 'gpo-fishing' in item:
                            extracted_folder = os.path.join(temp_dir, item)
                            break
                    
                    if not extracted_folder:
                        self.status_msg.config(text='❌ Update extraction failed', foreground='red')
                        return
                    
                    # Files to preserve (user settings)
                    preserve_files = [
                        'default_settings.json',
                        'presets/',
                        '.git/',
                        '.gitignore'
                    ]
                    
                    # Create backup timestamp
                    backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    # Backup current installation
                    backup_dir = os.path.join(current_dir, f"backup_{backup_timestamp}")
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    # Copy current files to backup
                    for item in os.listdir(current_dir):
                        if item.startswith('backup_'):
                            continue
                        src = os.path.join(current_dir, item)
                        dst = os.path.join(backup_dir, item)
                        try:
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        except:
                            pass
                    
                    self.status_msg.config(text='Installing update...', foreground='#58a6ff')
                    
                    # Update files (except preserved ones)
                    for item in os.listdir(extracted_folder):
                        src = os.path.join(extracted_folder, item)
                        dst = os.path.join(current_dir, item)
                        
                        # Skip preserved files/folders
                        if any(item.startswith(preserve.rstrip('/')) for preserve in preserve_files):
                            continue
                        
                        try:
                            if os.path.exists(dst):
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        except Exception as e:
                            print(f"Error updating {item}: {e}")
                    
                    self.status_msg.config(text='✅ Update installed! Restarting...', foreground='green')
                    
                    # Schedule restart after showing message
                    self.root.after(2000, self.restart_application)
                    
            else:
                self.status_msg.config(text='❌ Download failed', foreground='red')
                
        except Exception as e:
            self.status_msg.config(text=f'Update error: {str(e)[:30]}...', foreground='red')

    def restart_application(self):
        """Restart the application after update"""
        try:
            import sys
            import os
            import subprocess
            
            # Get the current script path
            script_path = os.path.abspath(__file__)
            
            # Close current application
            self.root.quit()
            self.root.destroy()
            
            # Start new instance
            if getattr(sys, 'frozen', False):
                # If running as exe
                subprocess.Popen([sys.executable])
            else:
                # If running as Python script
                subprocess.Popen([sys.executable, script_path])
            
            # Exit current process
            sys.exit(0)
            
        except Exception as e:
            print(f"Restart failed: {e}")
            sys.exit(1)

    def start_auto_update_loop(self):
        """Start the auto-update checking loop"""
        if self.auto_update_enabled and not self.main_loop_active:
            import threading
            threading.Thread(target=self.check_for_updates, daemon=True).start()
        
        # Schedule next check regardless (but it will skip if main loop is active)
        if self.auto_update_enabled:
            self.root.after(self.update_check_interval * 1000, self.start_auto_update_loop)

    def test_webhook(self):
        """Send a test webhook message"""
        if not self.webhook_url:
            print("❌ Please enter a webhook URL first")
            return
            
        try:
            import requests
            from datetime import datetime
            
            embed = {
                "title": "🧪 GPO Autofish Test",
                "description": "Webhook test successful! ✅",
                "color": 0x0099ff,  # Blue color
                "fields": [
                    {
                        "name": "🔧 Status",
                        "value": "Webhook is working correctly",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "GPO Autofish - Open Source",
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed],
                "username": "GPO Autofish Bot"
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                print("✅ Test webhook sent successfully!")
            else:
                print(f"❌ Test webhook failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test webhook error: {e}")

    def apply_theme(self):
        """Apply the current theme to the application"""
        style = ttk.Style()
        
        if self.dark_theme:
            # Modern dark theme with gradients and rounded corners
            self.root.configure(bg='#0d1117')
            style.theme_use('clam')
            
            # Modern dark colors
            style.configure('TFrame', 
                          background='#0d1117',
                          relief='flat',
                          borderwidth=0)
            
            style.configure('TLabel', 
                          background='#0d1117', 
                          foreground='#f0f6fc',
                          font=('Segoe UI', 9))
            
            # Modern button styling
            style.configure('TButton',
                          background='#21262d',
                          foreground='#f0f6fc',
                          borderwidth=1,
                          focuscolor='none',
                          font=('Segoe UI', 9),
                          relief='flat')
            style.map('TButton',
                     background=[('active', '#30363d'), ('pressed', '#1c2128')],
                     bordercolor=[('active', '#58a6ff'), ('pressed', '#1f6feb')])
            
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
                          background='#0d1117',
                          foreground='#f0f6fc',
                          focuscolor='none',
                          font=('Segoe UI', 9))
            style.map('TCheckbutton',
                     background=[('active', '#0d1117')])
            
            style.configure('TSpinbox',
                          fieldbackground='#21262d',
                          background='#21262d',
                          foreground='#f0f6fc',
                          bordercolor='#30363d',
                          arrowcolor='#f0f6fc',
                          font=('Segoe UI', 9))
            
            # Scrollbar styling for dark mode
            style.configure('Vertical.TScrollbar',
                          background='#21262d',
                          troughcolor='#0d1117',
                          bordercolor='#30363d',
                          arrowcolor='#8b949e',
                          darkcolor='#21262d',
                          lightcolor='#30363d')
            style.map('Vertical.TScrollbar',
                     background=[('active', '#30363d'), ('pressed', '#484f58')])
            
            # Header styling
            style.configure('Title.TLabel',
                          background='#0d1117',
                          foreground='#58a6ff',
                          font=('Segoe UI', 18, 'bold'))
            
            style.configure('Subtitle.TLabel',
                          background='#0d1117',
                          foreground='#8b949e',
                          font=('Segoe UI', 8))
            
            # Section title styling - blue color for dark mode
            style.configure('SectionTitle.TLabel',
                          background='#0d1117',
                          foreground='#58a6ff',
                          font=('Segoe UI', 11, 'bold'))
            
            # Status labels
            style.configure('StatusOn.TLabel',
                          background='#0d1117',
                          foreground='#3fb950',
                          font=('Segoe UI', 10, 'bold'))
            
            style.configure('StatusOff.TLabel',
                          background='#0d1117',
                          foreground='#f85149',
                          font=('Segoe UI', 10))
            
            style.configure('Counter.TLabel',
                          background='#0d1117',
                          foreground='#a5a5a5',
                          font=('Segoe UI', 11, 'bold'))
            
            # Update canvas background for dark mode
            if hasattr(self, 'canvas'):
                self.canvas.configure(bg='#0d1117')
            
            self.theme_btn.config(text='☀ Light Mode')
        else:
            # Modern light theme with clean styling
            self.root.configure(bg='#fafbfc')
            style.theme_use('clam')
            
            # Light theme colors
            style.configure('TFrame', 
                          background='#fafbfc',
                          relief='flat',
                          borderwidth=0)
            
            style.configure('TLabel', 
                          background='#fafbfc', 
                          foreground='#24292f',
                          font=('Segoe UI', 9))
            
            # Modern button styling for light mode
            style.configure('TButton',
                          background='#e1e4e8',
                          foreground='#24292f',
                          borderwidth=1,
                          focuscolor='none',
                          font=('Segoe UI', 9),
                          relief='flat')
            style.map('TButton',
                     background=[('active', '#d0d7de'), ('pressed', '#c6cbd1')],
                     bordercolor=[('active', '#0969da'), ('pressed', '#0550ae')])
            
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
                          background='#fafbfc',
                          foreground='#24292f',
                          focuscolor='none',
                          font=('Segoe UI', 9))
            style.map('TCheckbutton',
                     background=[('active', '#fafbfc')])
            
            style.configure('TSpinbox',
                          fieldbackground='#f6f8fa',
                          background='#e1e4e8',
                          foreground='#24292f',
                          bordercolor='#d0d7de',
                          arrowcolor='#24292f',
                          font=('Segoe UI', 9))
            
            # Entry styling to match the gray theme
            style.configure('TEntry',
                          fieldbackground='#f6f8fa',
                          background='#e1e4e8',
                          foreground='#24292f',
                          bordercolor='#d0d7de',
                          font=('Segoe UI', 9))
            
            # Scrollbar styling for light mode
            style.configure('Vertical.TScrollbar',
                          background='#e1e4e8',
                          troughcolor='#fafbfc',
                          bordercolor='#d0d7de',
                          arrowcolor='#656d76',
                          darkcolor='#e1e4e8',
                          lightcolor='#f6f8fa')
            style.map('Vertical.TScrollbar',
                     background=[('active', '#d0d7de'), ('pressed', '#c6cbd1')])
            
            # Header styling
            style.configure('Title.TLabel',
                          background='#fafbfc',
                          foreground='#0969da',
                          font=('Segoe UI', 18, 'bold'))
            
            style.configure('Subtitle.TLabel',
                          background='#fafbfc',
                          foreground='#656d76',
                          font=('Segoe UI', 8))
            
            # Section title styling - blue color for light mode
            style.configure('SectionTitle.TLabel',
                          background='#fafbfc',
                          foreground='#0969da',
                          font=('Segoe UI', 11, 'bold'))
            
            # Status labels
            style.configure('StatusOn.TLabel',
                          background='#fafbfc',
                          foreground='#1a7f37',
                          font=('Segoe UI', 10, 'bold'))
            
            style.configure('StatusOff.TLabel',
                          background='#fafbfc',
                          foreground='#cf222e',
                          font=('Segoe UI', 10))
            
            style.configure('Counter.TLabel',
                          background='#fafbfc',
                          foreground='#656d76',
                          font=('Segoe UI', 11, 'bold'))
            
            # Update canvas background for light mode
            if hasattr(self, 'canvas'):
                self.canvas.configure(bg='#fafbfc')
            
            self.theme_btn.config(text='🌙 Dark Mode')

    def toggle_theme(self):
        """Toggle between dark and light themes"""
        self.dark_theme = not self.dark_theme
        self.apply_theme()

    def auto_save_settings(self):
        """Auto-save current settings to default.json"""
        if not hasattr(self, 'auto_purchase_var'):
            return  # Skip if not fully initialized
            
        preset_data = {
            'auto_purchase_enabled': getattr(self.auto_purchase_var, 'get', lambda: False)(),
            'auto_purchase_amount': getattr(self.amount_var, 'get', lambda: getattr(self, 'auto_purchase_amount', 100))(),
            'loops_per_purchase': getattr(self.loops_var, 'get', lambda: getattr(self, 'loops_per_purchase', 1))(),
            'point_coords': getattr(self, 'point_coords', {}),
            'kp': getattr(self, 'kp', 0.1),
            'kd': getattr(self, 'kd', 0.5),
            'scan_timeout': getattr(self, 'scan_timeout', 15.0),
            'wait_after_loss': getattr(self, 'wait_after_loss', 1.0),
            'smart_check_interval': getattr(self, 'smart_check_interval', 15.0),
            'webhook_url': getattr(self, 'webhook_url', ''),
            'webhook_enabled': getattr(self, 'webhook_enabled', False),
            'webhook_interval': getattr(self, 'webhook_interval', 10),
            'auto_update_enabled': getattr(self, 'auto_update_enabled', False),
            'dark_theme': getattr(self, 'dark_theme', True),
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
                
                # Overlay settings
                'overlay_area': getattr(self, 'overlay_area', {}),
                
                # Recovery settings
                'recovery_enabled': getattr(self, 'recovery_enabled', True),
                
                # Performance settings
                'silent_mode': getattr(self, 'silent_mode', False),
                'verbose_logging': getattr(self, 'verbose_logging', False),
                
                # Theme settings
                'dark_theme': getattr(self, 'dark_theme', True),
                
                # Auto-update settings
                'auto_update_enabled': getattr(self, 'auto_update_enabled', False),
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
            
            self.point_coords = preset_data.get('point_coords', {})
            # Update point buttons if they exist
            for idx in range(1, 5):
                if hasattr(self, 'point_buttons') and idx in self.point_buttons:
                    self.update_point_button(idx)
            
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
            
            # Overlay settings
            if 'overlay_area' in preset_data and preset_data['overlay_area']:
                self.overlay_area = preset_data['overlay_area']
            
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
                self.theme_btn.config(text='☀ Light Mode' if self.dark_theme else '🌙 Dark Mode')
            
            # Auto-update settings
            self.auto_update_enabled = preset_data.get('auto_update_enabled', False)
            if hasattr(self, 'auto_update_btn'):
                self.auto_update_btn.config(text=f'🔄 Auto Update: {"ON" if self.auto_update_enabled else "OFF"}')
            
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
            return  # No saved settings, use defaults
            
        try:
            with open(settings_file, 'r') as f:
                preset_data = json.load(f)
            
            # Load basic settings that don't require UI elements
            self.auto_purchase_amount = preset_data.get('auto_purchase_amount', 100)
            self.loops_per_purchase = preset_data.get('loops_per_purchase', 1)
            self.point_coords = preset_data.get('point_coords', {})
            self.kp = preset_data.get('kp', 0.1)
            self.kd = preset_data.get('kd', 0.5)
            self.scan_timeout = preset_data.get('scan_timeout', 15.0)
            self.wait_after_loss = preset_data.get('wait_after_loss', 1.0)
            self.smart_check_interval = preset_data.get('smart_check_interval', 15.0)
            self.webhook_url = preset_data.get('webhook_url', '')
            self.webhook_enabled = preset_data.get('webhook_enabled', False)
            self.webhook_interval = preset_data.get('webhook_interval', 10)
            self.auto_update_enabled = preset_data.get('auto_update_enabled', False)
            self.dark_theme = preset_data.get('dark_theme', True)
            
        except Exception as e:
            print(f'Error loading basic settings: {e}')

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
            
            # Update UI elements
            if hasattr(self, 'point_buttons'):
                self.update_point_buttons()
            if hasattr(self, 'auto_update_btn'):
                self.update_auto_update_button()
            
        except Exception as e:
            print(f'Error loading UI settings: {e}')

    def update_point_buttons(self):
        """Update point button texts with coordinates"""
        for idx, coords in self.point_coords.items():
            if coords and idx in self.point_buttons:
                self.point_buttons[idx].config(text=f'Point {idx}: {coords}')

    def update_hotkey_labels(self):
        """Update hotkey label texts"""
        try:
            self.loop_key_label.config(text=self.hotkeys['toggle_loop'].upper())
            self.overlay_key_label.config(text=self.hotkeys['toggle_overlay'].upper())
            self.exit_key_label.config(text=self.hotkeys['exit'].upper())
            self.tray_key_label.config(text=self.hotkeys['toggle_tray'].upper())
        except AttributeError:
            pass  # Labels not created yet

    def update_auto_update_button(self):
        """Update auto-update button text based on current state"""
        try:
            if self.auto_update_enabled:
                self.auto_update_btn.config(text='🔄 Auto Update: ON')
            else:
                self.auto_update_btn.config(text='🔄 Auto Update: OFF')
        except AttributeError:
            pass  # Button not created yet

    def setup_system_tray(self):
        """Setup system tray functionality"""
        try:
            # Create a simple icon
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
        """Minimize the application to system tray"""
        if self.tray_icon:
            self.root.withdraw()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self):
        """Show the application from system tray"""
        self.root.deiconify()
        self.root.lift()
        if self.tray_icon:
            self.tray_icon.stop()
    
    def restore_from_tray(self):
        """Alias for show_from_tray for consistency"""
        self.show_from_tray()

def main():
    root = tk.Tk()
    app = HotkeyGUI(root)
    root.protocol('WM_DELETE_WINDOW', app.exit_app)
    root.mainloop()
if __name__ == '__main__':
    main()
