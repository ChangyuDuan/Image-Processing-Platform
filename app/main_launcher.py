import tkinter as tk
from tkinter import ttk
import subprocess
import sys
import os
from PIL import Image, ImageTk, ImageDraw

current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = current_dir
project_root = os.path.dirname(current_dir)
if sys.executable.lower().endswith("pythonw.exe"):
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 图片特征分析")
        self.root.geometry("600x450") 
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=600, height=450, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.draw_gradient_background()
        self.floaters = []
        self.create_floaters()
        self.create_glass_card()
        self.draw_ui()
        self.center_window()
        self.animate_floaters()

    def draw_gradient_background(self):
        self.canvas.create_oval(-100, -100, 400, 400, fill="#ffe3e3", outline="", tags="bg")
        self.canvas.create_oval(300, -50, 700, 350, fill="#d6f5f3", outline="", tags="bg")
        self.canvas.create_oval(-50, 250, 350, 650, fill="#dbe0fc", outline="", tags="bg")
        self.canvas.create_oval(350, 300, 750, 600, fill="#fff4d6", outline="", tags="bg")

    def create_floaters(self):
        emojis = ['🎨', '🧬', '📐', '📊', '📷', '✨']
        import random
        for _ in range(8):
            emoji = random.choice(emojis)
            x = random.randint(0, 600)
            y = random.randint(0, 450)
            item = self.canvas.create_text(x, y, text=emoji, font=("Segoe UI Emoji", 24), fill="#a0a0a0", tags="floater")
            self.floaters.append([item, random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8)])

    def create_glass_card(self):
        width, height = 500, 350
        radius = 20
        color = (255, 255, 255, 220) 
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle([(0, 0), (width, height)], radius=radius, fill=color)
        self.card_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(300, 225, image=self.card_image, tags="card")

    def create_glass_button(self, x, y, width, height, text, command):
        """
        Creates a glassmorphism button on the canvas.
        Returns the group of item IDs.
        """
        radius = height // 2
        
        def make_btn_img(bg_color, outline_color, w, h):
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([(0, 0), (w, h)], radius=radius, fill=bg_color, outline=outline_color, width=1)
            return ImageTk.PhotoImage(img)

        img_normal = make_btn_img((255, 255, 255, 120), (255, 255, 255, 160), width, height)

        zoom_factor = 1.05
        w_zoom, h_zoom = int(width * zoom_factor), int(height * zoom_factor)
        img_hover = make_btn_img((255, 255, 255, 190), (255, 255, 255, 220), w_zoom, h_zoom)
        img_pressed = make_btn_img((220, 230, 255, 200), (0, 113, 227, 100), width, height)
        if not hasattr(self, 'btn_images'): self.btn_images = []
        self.btn_images.extend([img_normal, img_hover, img_pressed])
        btn_id = self.canvas.create_image(x, y, image=img_normal, tags="button")
        text_id = self.canvas.create_text(x, y, text=text, font=("Microsoft YaHei UI", 12, "bold"), fill="#1d1d1f")
        def on_enter(e):
            self.canvas.itemconfig(btn_id, image=img_hover)
            self.root.config(cursor="hand2")
            self.canvas.itemconfig(text_id, fill="#0071e3")
            
        def on_leave(e):
            self.canvas.itemconfig(btn_id, image=img_normal)
            self.root.config(cursor="")
            self.canvas.itemconfig(text_id, fill="#1d1d1f")
            
        def on_press(e):
            self.canvas.itemconfig(btn_id, image=img_pressed)
            self.canvas.move(text_id, 0, 1)
            
        def on_release(e):
            x_mouse, y_mouse = e.x, e.y
            bbox = self.canvas.bbox(btn_id)
            is_over = bbox[0] <= x_mouse <= bbox[2] and bbox[1] <= y_mouse <= bbox[3]
            
            if is_over:
                self.canvas.itemconfig(btn_id, image=img_hover)
                self.root.after(50, command)
            else:
                self.canvas.itemconfig(btn_id, image=img_normal)
            self.canvas.move(text_id, 0, -1)
        for item in [btn_id, text_id]:
            self.canvas.tag_bind(item, "<Enter>", on_enter)
            self.canvas.tag_bind(item, "<Leave>", on_leave)
            self.canvas.tag_bind(item, "<Button-1>", on_press)
            self.canvas.tag_bind(item, "<ButtonRelease-1>", on_release)
            
        return btn_id, text_id

    def draw_ui(self):
        self.emoji_id = self.canvas.create_text(300, 100, text="✨", font=("Segoe UI Emoji", 48), fill="#1d1d1f")
        self.canvas.tag_bind(self.emoji_id, "<Enter>", self.on_emoji_hover)
        self.canvas.tag_bind(self.emoji_id, "<Leave>", self.on_emoji_leave)
        self.canvas.tag_bind(self.emoji_id, "<Button-1>", self.on_emoji_click)
        self.canvas.create_text(300, 160, text="AI 图片特征分析", font=("Microsoft YaHei UI", 24, "bold"), fill="#1d1d1f")
        self.canvas.create_text(300, 360, text="请选择一种方式启动服务", font=("Microsoft YaHei UI", 10), fill="#86868b")
        self.create_glass_button(300, 230, 420, 50, "🖥️  启动桌面客户端", self.launch_desktop)
        self.create_glass_button(300, 300, 420, 50, "🌐  启动 Web 浏览器", self.launch_web)


    def animate_floaters(self):
        for floater in self.floaters:
            item, dx, dy = floater
            self.canvas.move(item, dx, dy)
            coords = self.canvas.coords(item)
            if coords[0] < -20 or coords[0] > 620: floater[1] *= -1
            if coords[1] < -20 or coords[1] > 470: floater[2] *= -1
            
        self.root.after(40, self.animate_floaters)

    def on_emoji_hover(self, event):
        self.canvas.itemconfig(self.emoji_id, text="🚀", fill="#0071e3")
        self.root.config(cursor="hand2")
        
    def on_emoji_leave(self, event):
        self.canvas.itemconfig(self.emoji_id, text="✨", fill="#1d1d1f")
        self.root.config(cursor="")

    def on_emoji_click(self, event):
        self.canvas.itemconfig(self.emoji_id, fill="#ff3b30")
        self.root.after(200, lambda: self.canvas.itemconfig(self.emoji_id, fill="#0071e3"))

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def launch_desktop(self):
        script_path = os.path.join(app_dir, 'desktop_app.py')
        
        self.canvas.itemconfig(self.emoji_id, text="⏳", fill="#86868b")
        self.root.config(cursor="wait")
        self.root.update()

        import platform
        if platform.system() == "Windows":
             cmd = f'start "" "{sys.executable.replace("python.exe", "pythonw.exe")}" "{script_path}"'
             # 确保在项目根目录执行
             os.system(f'cd /d "{project_root}" && {cmd}')
        else:
             subprocess.Popen([sys.executable, script_path], cwd=project_root)

        self.root.after(3000, self.root.destroy)

    def launch_web(self):
        script_path = os.path.join(app_dir, 'web_launcher.py')
        
        self.canvas.itemconfig(self.emoji_id, text="⏳", fill="#86868b")
        self.root.config(cursor="wait")
        self.root.update()
        
        import platform
        if platform.system() == "Windows":
             cmd = f'start "" "{sys.executable.replace("python.exe", "pythonw.exe")}" "{script_path}"'
             os.system(f'cd /d "{project_root}" && {cmd}')
        else:
             subprocess.Popen([sys.executable, script_path], cwd=project_root)
        
        self.root.after(3000, self.root.destroy)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = LauncherApp(root)
    root.mainloop()
