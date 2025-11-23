import tkinter as tk
from tkinter import ttk

# Consistent Dark Red Color Palette
MAIN_COLOR = "#DC2626"      # Tailwind red-600 (consistent dark red)
BUTTON_COLOR = "#DC2626"    # Same as main for consistency
BG_COLOR = "#FFFFFF"        # White for section backgrounds
CARD_COLOR = "#DC2626"      # Same dark red for status cards
BORDER_COLOR = "#B91C1C"    # Tailwind red-700 for borders (darker)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.delay = 500  # 500ms delay before showing
        self.after_id = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
    
    def on_enter(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
        self.after_id = self.widget.after(self.delay, self.show_tooltip)
    
    def on_motion(self, event=None):
        if self.tooltip_window:
            self.hide_tooltip()
        if self.after_id:
            self.widget.after_cancel(self.after_id)
        self.after_id = self.widget.after(self.delay, self.show_tooltip)
    
    def on_leave(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide_tooltip()
    
    def show_tooltip(self):
        if self.tooltip_window or not self.text:
            return
        
        # Get widget position and size
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty()
        widget_height = self.widget.winfo_height()
        
        # Position tooltip below the widget
        tooltip_x = x + 10
        tooltip_y = y + widget_height + 5
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes('-topmost', True)
        
        # Simple tooltip with regular tkinter
        label = tk.Label(
            tw,
            text=self.text,
            justify='left',
            background="#1F2937",
            foreground="white",
            relief='solid',
            borderwidth=1,
            wraplength=350,
            font=('Arial', 10)
        )
        label.pack()
        
        # Position the tooltip
        tw.wm_geometry(f"+{tooltip_x}+{tooltip_y}")
        
        # Auto-hide after 10 seconds
        tw.after(10000, self.hide_tooltip)
    
    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class GlassFrame(tk.Frame):
    """Modern white frame with red border"""
    def __init__(self, master, **kwargs):
        glass_color = kwargs.pop('glass_color', BG_COLOR)  # White background
        
        super().__init__(
            master,
            bg=glass_color,
            relief='solid',
            bd=2,
            **kwargs
        )

class AnimatedButton(ctk.CTkButton):
    """Button with hover animation effects"""
    def __init__(self, master, **kwargs):
        self.hover_color = kwargs.pop('hover_color', MAIN_COLOR)
        self.normal_color = kwargs.pop('normal_color', BUTTON_COLOR)
        
        if 'font' not in kwargs:
            kwargs['font'] = ctk.CTkFont(size=12, weight="bold")
        
        super().__init__(
            master,
            fg_color=self.normal_color,
            hover_color=self.hover_color,
            corner_radius=10,
            border_width=1,
            border_color=BORDER_COLOR,
            text_color="white",
            **kwargs
        )
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, event=None):
        self.configure(border_width=2)
    
    def _on_leave(self, event=None):
        self.configure(border_width=1)

class ToggleButton(ctk.CTkButton):
    """Toggle button that changes color when enabled/disabled"""
    def __init__(self, master, text="Toggle", enabled=False, on_toggle=None, **kwargs):
        self.enabled = enabled
        self.on_toggle_callback = on_toggle
        self.base_text = text
        
        # Colors for enabled/disabled states
        self.enabled_color = "#16A34A"  # Green when enabled
        self.disabled_color = "#6B7280"  # Gray when disabled
        self.enabled_hover = "#15803D"  # Darker green hover
        self.disabled_hover = "#4B5563"  # Darker gray hover
        
        if 'font' not in kwargs:
            kwargs['font'] = ctk.CTkFont(size=12, weight="bold")
        
        super().__init__(
            master,
            text=self._get_display_text(),
            command=self._toggle,
            corner_radius=10,
            border_width=2,
            text_color="white",
            **kwargs
        )
        
        self._update_appearance()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _get_display_text(self):
        status = "ENABLED" if self.enabled else "DISABLED"
        return f"{self.base_text}: {status}"
    
    def _toggle(self):
        self.enabled = not self.enabled
        self.configure(text=self._get_display_text())
        self._update_appearance()
        
        if self.on_toggle_callback:
            self.on_toggle_callback(self.enabled)
    
    def _update_appearance(self):
        if self.enabled:
            self.configure(
                fg_color=self.enabled_color,
                hover_color=self.enabled_hover,
                border_color="#22C55E"  # Light green border
            )
        else:
            self.configure(
                fg_color=self.disabled_color,
                hover_color=self.disabled_hover,
                border_color="#9CA3AF"  # Light gray border
            )
    
    def _on_enter(self, event=None):
        self.configure(border_width=3)
    
    def _on_leave(self, event=None):
        self.configure(border_width=2)
    
    def set_enabled(self, enabled):
        """Programmatically set the enabled state"""
        self.enabled = enabled
        self.configure(text=self._get_display_text())
        self._update_appearance()

class CollapsibleFrame:
    def __init__(self, parent, title, row, columnspan=4, icon="▼"):
        self.parent = parent
        self.title = title
        self.row = row
        self.columnspan = columnspan
        self.is_expanded = True
        self.icon = icon
        
        self.container = GlassFrame(parent)
        self.container.grid(row=row, column=0, columnspan=columnspan, sticky='ew', pady=(0, 12), padx=15)
        
        self.header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header_frame.pack(fill='x', pady=8, padx=12)
        self.header_frame.columnconfigure(0, weight=1)
        
        header_content = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_content.grid(row=0, column=0, sticky='ew')
        header_content.columnconfigure(1, weight=1)
        
        self.icon_label = ctk.CTkLabel(header_content, text=self.icon, 
                                       font=ctk.CTkFont(size=16))
        self.icon_label.grid(row=0, column=0, padx=(0, 10))
        
        self.title_label = ctk.CTkLabel(header_content, text=title, 
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        anchor="w")
        self.title_label.grid(row=0, column=1, sticky='w')
        
        self.toggle_btn = AnimatedButton(
            self.header_frame, 
            text='−', 
            width=35,
            height=35,
            command=self.toggle,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.toggle_btn.grid(row=0, column=1, sticky='e', padx=(10, 0))
        
        self.separator = ctk.CTkFrame(self.container, height=2, 
                                     fg_color=BORDER_COLOR)
        self.separator.pack(fill='x', padx=12, pady=(0, 8))
        
        self.content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 12))
        
        parent.grid_rowconfigure(row, weight=0)
        self.container.columnconfigure(0, weight=1)
    
    def toggle(self):
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.separator.pack_forget()
            self.toggle_btn.configure(text='+')
            self.is_expanded = False
        else:
            self.separator.pack(fill='x', padx=12, pady=(0, 8))
            self.content_frame.pack(fill='both', expand=True, padx=15, pady=(0, 12))
            self.toggle_btn.configure(text='−')
            self.is_expanded = True
    
    def get_content_frame(self):
        return self.content_frame

class StatusCard(ctk.CTkFrame):
    """Animated status card with dynamic background colors"""
    def __init__(self, master, title, value, icon="●", **kwargs):
        # Store default colors
        self.default_bg_color = CARD_COLOR
        self.default_border_color = BORDER_COLOR
        
        super().__init__(
            master,
            fg_color=self.default_bg_color,
            corner_radius=12,
            border_width=2,
            border_color=self.default_border_color,
            **kwargs
        )
        
        self.icon_label = ctk.CTkLabel(
            self, 
            text=icon,
            font=ctk.CTkFont(size=20),
            width=30,
            text_color="white"
        )
        self.icon_label.pack(side="left", padx=(12, 8), pady=12)
        
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=12, padx=(0, 12))
        
        self.title_label = ctk.CTkLabel(
            text_frame,
            text=title,
            font=ctk.CTkFont(size=10),
            anchor="w",
            text_color="white"
        )
        self.title_label.pack(anchor="w")
        
        self.value_label = ctk.CTkLabel(
            text_frame,
            text=value,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
            text_color="white"
        )
        self.value_label.pack(anchor="w")
    
    def update_value(self, value, color=None):
        self.value_label.configure(text=value)
        if color:
            self.value_label.configure(text_color=color)
    
    def update_status(self, value, status="default"):
        """Update card with status-based colors"""
        self.value_label.configure(text=value)
        
        # Define status colors
        status_colors = {
            "active": {"bg": "#16A34A", "border": "#22C55E"},      # Green for active
            "paused": {"bg": "#F59E0B", "border": "#FCD34D"},      # Yellow for paused
            "error": {"bg": "#EF4444", "border": "#F87171"},       # Red for error
            "default": {"bg": self.default_bg_color, "border": self.default_border_color}
        }
        
        colors = status_colors.get(status, status_colors["default"])
        self.configure(
            fg_color=colors["bg"],
            border_color=colors["border"]
        )
