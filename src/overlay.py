import tkinter as tk

class OverlayManager:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.drag_data = {'x': 0, 'y': 0, 'resize_edge': None, 'start_width': 0, 
                         'start_height': 0, 'start_x': 0, 'start_y': 0}
    
    def create(self):
        if self.window is not None:
            return
        
        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)
        self.window.attributes('-alpha', 0.5)
        self.window.attributes('-topmost', True)
        self.window.minsize(1, 1)
        
        x = self.app.overlay_area['x']
        y = self.app.overlay_area['y']
        width = self.app.overlay_area['width']
        height = self.app.overlay_area['height']
        geometry = f"{width}x{height}+{x}+{y}"
        self.window.geometry(geometry)
        
        frame = tk.Frame(self.window, bg='#1f6feb', highlightthickness=2, highlightbackground='#1f6feb')
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.window.bind("<ButtonPress-1>", self._start_action)
        self.window.bind("<B1-Motion>", self._motion)
        self.window.bind("<Motion>", self._update_cursor)
        self.window.bind("<Configure>", self._on_configure)
        
        frame.bind("<ButtonPress-1>", self._start_action)
        frame.bind("<B1-Motion>", self._motion)
        frame.bind("<Motion>", self._update_cursor)
    
    def destroy(self):
        if self.window is not None:
            self.app.overlay_area['x'] = self.window.winfo_x()
            self.app.overlay_area['y'] = self.window.winfo_y()
            self.app.overlay_area['width'] = self.window.winfo_width()
            self.app.overlay_area['height'] = self.window.winfo_height()
            self.window.destroy()
            self.window = None
    
    def _get_resize_edge(self, x, y):
        width = self.window.winfo_width()
        height = self.window.winfo_height()
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
    
    def _update_cursor(self, event):
        edge = self._get_resize_edge(event.x, event.y)
        cursor_map = {'nw': 'size_nw_se', 'ne': 'size_ne_sw', 'sw': 'size_ne_sw', 
                     'se': 'size_nw_se', 'n': 'size_ns', 's': 'size_ns', 
                     'e': 'size_we', 'w': 'size_we', None: 'arrow'}
        self.window.config(cursor=cursor_map.get(edge, 'arrow'))
    
    def _start_action(self, event):
        self.drag_data['x'] = event.x
        self.drag_data['y'] = event.y
        self.drag_data['resize_edge'] = self._get_resize_edge(event.x, event.y)
        self.drag_data['start_width'] = self.window.winfo_width()
        self.drag_data['start_height'] = self.window.winfo_height()
        self.drag_data['start_x'] = self.window.winfo_x()
        self.drag_data['start_y'] = self.window.winfo_y()
    
    def _motion(self, event):
        edge = self.drag_data['resize_edge']
        
        if edge is None:
            x = self.window.winfo_x() + event.x - self.drag_data['x']
            y = self.window.winfo_y() + event.y - self.drag_data['y']
            self.window.geometry(f'+{x}+{y}')
        else:
            dx = event.x - self.drag_data['x']
            dy = event.y - self.drag_data['y']
            
            new_width = self.drag_data['start_width']
            new_height = self.drag_data['start_height']
            new_x = self.drag_data['start_x']
            new_y = self.drag_data['start_y']
            
            if 'e' in edge:
                new_width = max(1, self.drag_data['start_width'] + dx)
            elif 'w' in edge:
                new_width = max(1, self.drag_data['start_width'] - dx)
                new_x = self.drag_data['start_x'] + dx
            
            if 's' in edge:
                new_height = max(1, self.drag_data['start_height'] + dy)
            elif 'n' in edge:
                new_height = max(1, self.drag_data['start_height'] - dy)
                new_y = self.drag_data['start_y'] + dy
            
            self.window.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
    
    def _on_configure(self, event=None):
        if self.window is not None:
            self.app.overlay_area['x'] = self.window.winfo_x()
            self.app.overlay_area['y'] = self.window.winfo_y()
            self.app.overlay_area['width'] = self.window.winfo_width()
            self.app.overlay_area['height'] = self.window.winfo_height()
