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
        
        # Title label with modern typography (left side)
        self.title_label = ttk.Label(self.header_frame, text=title, 
                                   font=('Segoe UI', 11, 'bold'))
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
        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3'}
        self.purchase_counter = 0
        self.purchase_delay_after_key = 2.0
        self.purchase_click_delay = 1.0
        self.purchase_after_type_delay = 1.0
        self.fish_count = 0  # Track successful fishing attempts
        
        # UI/UX improvements
        self.dark_theme = True  # Default to dark theme
        self.tray_icon = None
        self.collapsible_sections = {}
        
        # Preset management
        self.presets_dir = "presets"
        if not os.path.exists(self.presets_dir):
            os.makedirs(self.presets_dir)
        
        self.create_widgets()
        self.apply_theme()
        self.register_hotkeys()
        self.root.update_idletasks()
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        
        # Setup system tray if available
        if TRAY_AVAILABLE:
            self.setup_system_tray()

    def get_dpi_scale(self):
        """Get the DPI scaling factor for the current display"""  # inserted
        try:
            dpi = self.root.winfo_fpixels('1i')
            scale = dpi / 96.0
            return scale
        except:
            return 1.0

    def create_widgets(self):
        # Configure root window (will be updated by apply_theme)
        pass
        
        # Main container with modern padding
        self.main_frame = ttk.Frame(self.root, padding='25')
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
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
        credits = ttk.Label(header_frame, text='by asphalt_cake | Reworked/Published by Ariel', 
                           style='Subtitle.TLabel')
        credits.grid(row=1, column=0, pady=(0, 15))
        
        # Modern control panel
        control_panel = ttk.Frame(header_frame)
        control_panel.grid(row=2, column=0, sticky='ew', pady=(0, 10))
        control_panel.columnconfigure(1, weight=1)  # Center spacing
        
        # Left controls
        left_controls = ttk.Frame(control_panel)
        left_controls.grid(row=0, column=0, sticky='w')
        
        self.theme_btn = ttk.Button(left_controls, text='☀️ Light Mode', 
                                   command=self.toggle_theme, style='TButton')
        self.theme_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Right controls
        right_controls = ttk.Frame(control_panel)
        right_controls.grid(row=0, column=2, sticky='e')
        
        ttk.Button(right_controls, text='💾 Save', command=self.save_preset, 
                  style='TButton').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(right_controls, text='📁 Load', command=self.load_preset,
                  style='TButton').pack(side=tk.LEFT, padx=(0, 8))
        
        if TRAY_AVAILABLE:
            ttk.Button(right_controls, text='📌 Tray', command=self.minimize_to_tray,
                      style='TButton').pack(side=tk.LEFT)
        
        current_row += 1
        
        # Modern status dashboard
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=current_row, column=0, sticky='ew', pady=(0, 25))
        status_frame.columnconfigure((0, 1, 2), weight=1)
        
        # Status cards
        self.loop_status = ttk.Label(status_frame, text='● Main Loop: OFF', style='StatusOff.TLabel')
        self.loop_status.grid(row=0, column=0, padx=10, pady=8)
        
        self.overlay_status = ttk.Label(status_frame, text='● Overlay: OFF', style='StatusOff.TLabel')
        self.overlay_status.grid(row=0, column=1, padx=10, pady=8)
        
        self.fish_counter_label = ttk.Label(status_frame, text='🐟 Fish: 0', style='Counter.TLabel')
        self.fish_counter_label.grid(row=0, column=2, padx=10, pady=8)
        
        current_row += 1
        
        # Create modern collapsible sections
        self.create_auto_purchase_section(current_row)
        current_row += 1
        
        self.create_pd_controller_section(current_row)
        current_row += 1
        
        self.create_timing_section(current_row)
        current_row += 1
        
        self.create_hotkeys_section(current_row)
        current_row += 1
        
        # Modern status message at bottom
        self.status_msg = ttk.Label(self.main_frame, text='Ready to fish! 🎣', 
                                   font=('Segoe UI', 9), foreground='#58a6ff')
        self.status_msg.grid(row=current_row, column=0, pady=(25, 0))

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
        print('=== AUTO-PURCHASE SEQUENCE START ===')
        pts = self.point_coords
        if not pts or not pts.get(1) or not pts.get(2) or not pts.get(3) or not pts.get(4):
            print('Auto purchase aborted: points not fully set (need points 1-4).')
            return
        
        # Check if main loop is still active before starting
        if not self.main_loop_active:
            print('Auto purchase aborted: main loop stopped.')
            return
        
        amount = str(self.auto_purchase_amount)
        
        # Press 'e' key
        print('Pressing E key...')
        keyboard.press_and_release('e')
        threading.Event().wait(self.purchase_delay_after_key)
        
        if not self.main_loop_active:
            return
        
        # Click point 1
        print(f'Clicking Point 1: {pts[1]}')
        self._click_at(pts[1])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 2
        print(f'Clicking Point 2: {pts[2]}')
        self._click_at(pts[2])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Type amount
        print(f'Typing amount: {amount}')
        keyboard.write(amount)
        threading.Event().wait(self.purchase_after_type_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 1 again
        print(f'Clicking Point 1: {pts[1]}')
        self._click_at(pts[1])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 3
        print(f'Clicking Point 3: {pts[3]}')
        self._click_at(pts[3])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Click point 2
        print(f'Clicking Point 2: {pts[2]}')
        self._click_at(pts[2])
        threading.Event().wait(self.purchase_click_delay)
        
        if not self.main_loop_active:
            return
        
        # Right-click point 4 to close menu
        print(f'Right-clicking Point 4: {pts[4]}')
        self._right_click_at(pts[4])
        threading.Event().wait(self.purchase_click_delay)
        
        print('=== AUTO-PURCHASE SEQUENCE COMPLETE ===')
        print()

    def start_rebind(self, action):
        """Start recording a new hotkey"""  # inserted
        self.recording_hotkey = action
        self.status_msg.config(text=f'Press a key to rebind \'{action}\'...', foreground='blue')
        self.loop_rebind_btn.config(state='disabled')
        self.overlay_rebind_btn.config(state='disabled')
        self.exit_rebind_btn.config(state='disabled')
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
                
                self.recording_hotkey = None
                self.loop_rebind_btn.config(state='normal')
                self.overlay_rebind_btn.config(state='normal')
                self.exit_rebind_btn.config(state='normal')
                self.status_msg.config(text=f'Hotkey set to {key_str.upper()}', foreground='green')
                self.register_hotkeys()
                return False  # Stop the listener
            except Exception as e:
                self.status_msg.config(text=f'Error setting hotkey: {e}', foreground='red')
                self.recording_hotkey = None
                self.loop_rebind_btn.config(state='normal')
                self.overlay_rebind_btn.config(state='normal')
                self.exit_rebind_btn.config(state='normal')
                return False
        return False

    def register_hotkeys(self):
        """Register all hotkeys"""  # inserted
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.hotkeys['toggle_loop'], self.toggle_main_loop)
            keyboard.add_hotkey(self.hotkeys['toggle_overlay'], self.toggle_overlay)
            keyboard.add_hotkey(self.hotkeys['exit'], self.exit_app)
        except Exception as e:
            print(f'Error registering hotkeys: {e}')

    def toggle_main_loop(self):
        """Toggle the main loop on/off"""
        new_state = not self.main_loop_active
        
        if new_state:
            # We're turning the loop ON. If Auto Purchase is active, ensure points are set.
            if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
                pts = getattr(self, 'point_coords', {})
                missing = [i for i in [1, 2, 3, 4] if not pts.get(i)]
                if missing:
                    messagebox.showwarning('Auto Purchase: Points missing', f'Please set Point(s) {missing} before starting Auto Purchase.')
                    return
        
        # Apply new state
        self.main_loop_active = new_state
        
        if self.main_loop_active:
            self.loop_status.config(text='● Main Loop: ACTIVE', style='StatusOn.TLabel')
            self.reset_fish_counter()  # Reset counter when starting
            self.main_loop_thread = threading.Thread(target=self.main_loop, daemon=True)
            self.main_loop_thread.start()
        else:
            self.loop_status.config(text='● Main Loop: OFF', style='StatusOff.TLabel')
            # Release mouse button if it's being held when stopping
            if self.is_clicking:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.is_clicking = False
            # Reset PD controller state
            self.previous_error = 0

    def increment_fish_counter(self):
        """Increment fish counter and update display"""
        self.fish_count += 1
        try:
            self.root.after(0, lambda: self.fish_counter_label.config(text=f'🐟 Fish: {self.fish_count}'))
        except Exception:
            pass
        print(f'Fish caught: {self.fish_count}')

    def reset_fish_counter(self):
        """Reset fish counter when main loop starts"""
        self.fish_count = 0
        try:
            self.root.after(0, lambda: self.fish_counter_label.config(text=f'🐟 Fish: {self.fish_count}'))
        except Exception:
            pass

    def check_and_purchase(self):
        """Check if we need to auto-purchase and run sequence if needed"""  # inserted
        if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
            self.purchase_counter += 1
            loops_needed = int(getattr(self, 'loops_per_purchase', 1)) if getattr(self, 'loops_per_purchase', None) is not None else 1
            print(f'Purchase counter: {self.purchase_counter}/{loops_needed}')
            if self.purchase_counter >= max(1, loops_needed):
                print('Triggering auto-purchase sequence...')
                try:
                    self.perform_auto_purchase_sequence()
                    self.purchase_counter = 0
                except Exception as e:
                    print(f'Error during auto-purchase: {e}')

    def cast_line(self):
        """Perform the casting action: hold click for 1 second then release"""  # inserted
        print('Casting line...')
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        threading.Event().wait(1.0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.is_clicking = False
        print('Line cast')

    def main_loop(self):
        """Main loop that runs when activated"""
        print('Main loop started')
        target_color = (85, 170, 255)
        dark_color = (25, 25, 25)
        white_color = (255, 255, 255)
        import time
        
        with mss.mss() as sct:
            if getattr(self, 'auto_purchase_var', None) and self.auto_purchase_var.get():
                print('Running initial auto-purchase...')
                self.perform_auto_purchase_sequence()
            self.cast_line()
            cast_time = time.time()
            detected = False
            last_detection_time = time.time()
            was_detecting = False
            print('Entering main detection loop...')
            
            while self.main_loop_active:
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
                    # No blue bar found - check if we should timeout
                    if not detected and current_time - cast_time > self.scan_timeout:
                        print(f'Cast timeout after {self.scan_timeout}s, recasting...')
                        self.cast_line()
                        cast_time = time.time()
                        detected = False
                        threading.Event().wait(0.1)
                        continue
                    
                    # If we were previously detecting but now lost it
                    if was_detecting:
                        print('Lost detection, waiting...')
                        threading.Event().wait(self.wait_after_loss)
                        was_detecting = False
                        self.check_and_purchase()
                        self.cast_line()
                        detected = False
                        cast_time = time.time()
                        last_detection_time = time.time()
                    
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
        print('Main loop stopped')


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
        
        # Auto Purchase Active
        row = 0
        ttk.Label(frame, text='Active:').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.auto_purchase_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(frame, variable=self.auto_purchase_var, text='Enabled')
        auto_check.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "Automatically buy bait after catching fish. Requires setting Points 1-4.")
        row += 1
        
        # Purchase Amount
        ttk.Label(frame, text='Amount:').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.amount_var = tk.IntVar(value=10)
        amount_spinbox = ttk.Spinbox(frame, from_=0, to=1000000, increment=1, textvariable=self.amount_var, width=10)
        amount_spinbox.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "How much bait to buy each time (e.g., 10 = buy 10 bait)")
        self.amount_var.trace_add('write', lambda *args: setattr(self, 'auto_purchase_amount', self.amount_var.get()))
        self.auto_purchase_amount = self.amount_var.get()
        row += 1
        
        # Loops per Purchase
        ttk.Label(frame, text='Loops per Purchase:').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.loops_var = tk.IntVar(value=10)
        loops_spinbox = ttk.Spinbox(frame, from_=1, to=1000000, increment=1, textvariable=self.loops_var, width=10)
        loops_spinbox.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "Buy bait every X fish caught (e.g., 10 = buy bait after every 10 fish)")
        self.loops_var.trace_add('write', lambda *args: setattr(self, 'loops_per_purchase', self.loops_var.get()))
        self.loops_per_purchase = self.loops_var.get()
        row += 1
        
        # Point buttons for auto-purchase
        self.point_buttons = {}
        self.point_coords = {1: None, 2: None, 3: None, 4: None}
        
        for i in range(1, 5):
            ttk.Label(frame, text=f'Point {i}:').grid(row=row, column=0, sticky=tk.W, pady=5)
            self.point_buttons[i] = ttk.Button(frame, text=f'Point {i}', command=lambda idx=i: self.capture_mouse_click(idx))
            self.point_buttons[i].grid(row=row, column=1, pady=5, sticky=tk.W)
            help_btn = ttk.Button(frame, text='?', width=3)
            help_btn.grid(row=row, column=3, padx=5, pady=5)
            
            tooltips = {
                1: "Click to set: Shop NPC or buy button location",
                2: "Click to set: Amount input field location", 
                3: "Click to set: Confirm/purchase button location",
                4: "Click to set: Close menu/exit shop location"
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
        
        row = 0
        ttk.Label(frame, text='Kp (Proportional):').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.kp_var = tk.DoubleVar(value=self.kp)
        kp_spinbox = ttk.Spinbox(frame, from_=0.0, to=2.0, increment=0.1, textvariable=self.kp_var, width=10)
        kp_spinbox.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "How strongly to react to fish position. Higher = more aggressive corrections")
        self.kp_var.trace_add('write', lambda *args: setattr(self, 'kp', self.kp_var.get()))
        row += 1
        
        ttk.Label(frame, text='Kd (Derivative):').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.kd_var = tk.DoubleVar(value=self.kd)
        kd_spinbox = ttk.Spinbox(frame, from_=0.0, to=1.0, increment=0.01, textvariable=self.kd_var, width=10)
        kd_spinbox.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
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
        
        row = 0
        ttk.Label(frame, text='Scan Timeout (s):').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.DoubleVar(value=self.scan_timeout)
        timeout_spinbox = ttk.Spinbox(frame, from_=1.0, to=60.0, increment=1.0, textvariable=self.timeout_var, width=10)
        timeout_spinbox.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "How long to wait for fish before recasting line (seconds)")
        self.timeout_var.trace_add('write', lambda *args: setattr(self, 'scan_timeout', self.timeout_var.get()))
        row += 1
        
        ttk.Label(frame, text='Wait After Loss (s):').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.wait_var = tk.DoubleVar(value=self.wait_after_loss)
        wait_spinbox = ttk.Spinbox(frame, from_=0.0, to=10.0, increment=0.1, textvariable=self.wait_var, width=10)
        wait_spinbox.grid(row=row, column=1, pady=5, sticky=tk.W)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "Pause time after losing a fish before recasting (seconds)")
        self.wait_var.trace_add('write', lambda *args: setattr(self, 'wait_after_loss', self.wait_var.get()))

    def create_hotkeys_section(self, start_row):
        """Create the hotkey bindings collapsible section"""
        section = CollapsibleFrame(self.main_frame, "⌨️ Hotkey Bindings", start_row)
        self.collapsible_sections['hotkeys'] = section
        frame = section.get_content_frame()
        
        row = 0
        ttk.Label(frame, text='Toggle Main Loop:').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.loop_key_label = ttk.Label(frame, text=self.hotkeys['toggle_loop'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.loop_key_label.grid(row=row, column=1, pady=5)
        self.loop_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_loop'))
        self.loop_rebind_btn.grid(row=row, column=2, padx=5, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "Start/stop the fishing bot")
        row += 1
        
        ttk.Label(frame, text='Toggle Overlay:').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.overlay_key_label = ttk.Label(frame, text=self.hotkeys['toggle_overlay'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.overlay_key_label.grid(row=row, column=1, pady=5)
        self.overlay_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('toggle_overlay'))
        self.overlay_rebind_btn.grid(row=row, column=2, padx=5, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "Show/hide blue detection area overlay")
        row += 1
        
        ttk.Label(frame, text='Exit:').grid(row=row, column=0, sticky=tk.W, pady=5)
        self.exit_key_label = ttk.Label(frame, text=self.hotkeys['exit'].upper(), relief=tk.RIDGE, padding=5, width=10)
        self.exit_key_label.grid(row=row, column=1, pady=5)
        self.exit_rebind_btn = ttk.Button(frame, text='Rebind', command=lambda: self.start_rebind('exit'))
        self.exit_rebind_btn.grid(row=row, column=2, padx=5, pady=5)
        help_btn = ttk.Button(frame, text='?', width=3)
        help_btn.grid(row=row, column=3, padx=5, pady=5)
        ToolTip(help_btn, "Close the application completely")

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
            
            # Header styling
            style.configure('Title.TLabel',
                          background='#0d1117',
                          foreground='#58a6ff',
                          font=('Segoe UI', 18, 'bold'))
            
            style.configure('Subtitle.TLabel',
                          background='#0d1117',
                          foreground='#8b949e',
                          font=('Segoe UI', 8))
            
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
            
            self.theme_btn.config(text='☀️ Light Mode')
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
                          background='#f6f8fa',
                          foreground='#24292f',
                          borderwidth=1,
                          focuscolor='none',
                          font=('Segoe UI', 9),
                          relief='flat')
            style.map('TButton',
                     background=[('active', '#f3f4f6'), ('pressed', '#e1e4e8')],
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
                          fieldbackground='#ffffff',
                          background='#f6f8fa',
                          foreground='#24292f',
                          bordercolor='#d0d7de',
                          arrowcolor='#24292f',
                          font=('Segoe UI', 9))
            
            # Header styling
            style.configure('Title.TLabel',
                          background='#fafbfc',
                          foreground='#0969da',
                          font=('Segoe UI', 18, 'bold'))
            
            style.configure('Subtitle.TLabel',
                          background='#fafbfc',
                          foreground='#656d76',
                          font=('Segoe UI', 8))
            
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
            
            self.theme_btn.config(text='🌙 Dark Mode')

    def toggle_theme(self):
        """Toggle between dark and light themes"""
        self.dark_theme = not self.dark_theme
        self.apply_theme()

    def save_preset(self):
        """Save current settings as a preset"""
        preset_name = simpledialog.askstring("Save Preset", "Enter preset name:")
        if not preset_name:
            return
            
        preset_data = {
            'auto_purchase_enabled': self.auto_purchase_var.get(),
            'auto_purchase_amount': self.amount_var.get(),
            'loops_per_purchase': self.loops_var.get(),
            'point_coords': self.point_coords,
            'kp': self.kp_var.get(),
            'kd': self.kd_var.get(),
            'scan_timeout': self.timeout_var.get(),
            'wait_after_loss': self.wait_var.get(),
            'hotkeys': self.hotkeys.copy(),
            'overlay_area': self.overlay_area.copy(),
            'dark_theme': self.dark_theme,
            'created': datetime.now().isoformat()
        }
        
        preset_file = os.path.join(self.presets_dir, f"{preset_name}.json")
        try:
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
            self.status_msg.config(text=f'Preset "{preset_name}" saved successfully!', foreground='green')
        except Exception as e:
            self.status_msg.config(text=f'Error saving preset: {e}', foreground='red')

    def load_preset(self):
        """Load a preset configuration"""
        preset_file = filedialog.askopenfilename(
            title="Load Preset",
            initialdir=self.presets_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not preset_file:
            return
            
        try:
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)
            
            # Apply preset data
            self.auto_purchase_var.set(preset_data.get('auto_purchase_enabled', True))
            self.amount_var.set(preset_data.get('auto_purchase_amount', 10))
            self.loops_var.set(preset_data.get('loops_per_purchase', 10))
            self.point_coords = preset_data.get('point_coords', {1: None, 2: None, 3: None, 4: None})
            self.kp_var.set(preset_data.get('kp', 0.1))
            self.kd_var.set(preset_data.get('kd', 0.5))
            self.timeout_var.set(preset_data.get('scan_timeout', 15.0))
            self.wait_var.set(preset_data.get('wait_after_loss', 1.0))
            self.hotkeys = preset_data.get('hotkeys', {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3'})
            self.overlay_area = preset_data.get('overlay_area', self.overlay_area)
            self.dark_theme = preset_data.get('dark_theme', True)
            
            # Update UI elements
            self.update_point_buttons()
            self.update_hotkey_labels()
            self.apply_theme()
            self.register_hotkeys()
            
            preset_name = os.path.basename(preset_file).replace('.json', '')
            self.status_msg.config(text=f'Preset "{preset_name}" loaded successfully!', foreground='green')
            
        except Exception as e:
            self.status_msg.config(text=f'Error loading preset: {e}', foreground='red')

    def update_point_buttons(self):
        """Update point button texts with coordinates"""
        for idx, coords in self.point_coords.items():
            if coords and idx in self.point_buttons:
                self.point_buttons[idx].config(text=f'Point {idx}: {coords}')

    def update_hotkey_labels(self):
        """Update hotkey label texts"""
        self.loop_key_label.config(text=self.hotkeys['toggle_loop'].upper())
        self.overlay_key_label.config(text=self.hotkeys['toggle_overlay'].upper())
        self.exit_key_label.config(text=self.hotkeys['exit'].upper())

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

def main():
    root = tk.Tk()
    app = HotkeyGUI(root)
    root.protocol('WM_DELETE_WINDOW', app.exit_app)
    root.mainloop()
if __name__ == '__main__':
    main()
