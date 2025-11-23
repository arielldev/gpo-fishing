import customtkinter as ctk
import ctypes
import tkinter as tk
from gui import HotkeyGUI

def create_gradient_background(root):
    """Create a gradient background canvas - Light mode only"""
    canvas = tk.Canvas(root, highlightthickness=0)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    
    def update_gradient(event=None):
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        canvas.delete("gradient")
        
        # Light pink to white gradient
        start_color = (255, 232, 232)  # #FFE8E8
        end_color = (255, 255, 255)    # #FFFFFF
        
        steps = 100
        for i in range(steps):
            ratio = i / steps
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            y1 = int(height * i / steps)
            y2 = int(height * (i + 1) / steps)
            
            canvas.create_rectangle(0, y1, width, y2, fill=color, outline=color, tags="gradient")
    
    canvas.bind('<Configure>', update_gradient)
    root.update_idletasks()
    update_gradient()
    
    return canvas

def main():
    ctk.set_appearance_mode("light")
    
    # Customize switch colors to match red theme
    ctk.ThemeManager.theme["CTkSwitch"]["fg_color"] = ("#FFD0D0", "#FFD0D0")
    ctk.ThemeManager.theme["CTkSwitch"]["progress_color"] = ("#E85555", "#E85555")
    ctk.ThemeManager.theme["CTkSwitch"]["button_color"] = ("#FFFFFF", "#FFFFFF")
    ctk.ThemeManager.theme["CTkSwitch"]["button_hover_color"] = ("#FFE8E8", "#FFE8E8")
    
    root = ctk.CTk()
    
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # Set window icon
    try:
        from PIL import Image, ImageTk
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "..", "images", "icon.webp")
        if os.path.exists(icon_path):
            icon_image = Image.open(icon_path)
            # Convert to PhotoImage for tkinter
            photo = ImageTk.PhotoImage(icon_image)
            root.iconphoto(True, photo)
    except Exception as e:
        print(f"Could not load icon: {e}")
    
    # Create gradient background
    gradient_canvas = create_gradient_background(root)
    
    app = HotkeyGUI(root, gradient_canvas)
    root.protocol('WM_DELETE_WINDOW', app.exit_app)
    root.mainloop()

if __name__ == '__main__':
    main()
