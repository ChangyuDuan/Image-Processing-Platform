import uvicorn
import webbrowser
import threading
import time
import sys
import os
import socket

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if sys.executable.lower().endswith("pythonw.exe"):
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

from app.main import app

def get_free_port():
    """获取一个空闲端口"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def start_server(port):
    """启动服务"""
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="critical")

def main():
    port = get_free_port()

    t = threading.Thread(target=start_server, args=(port,))
    t.daemon = True
    t.start()
    
    start_time = time.time()
    server_ready = False
    
    while time.time() - start_time < 5:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            server_ready = True
            break
        time.sleep(0.1)
    
    if server_ready:
        webbrowser.open(f"http://127.0.0.1:{port}")
    else:
        webbrowser.open(f"http://127.0.0.1:{port}")

    import tkinter as tk
    from tkinter import messagebox
    
    root = tk.Tk()
    root.withdraw() 

    root.deiconify()
    root.title("服务运行中")
    root.geometry("300x100")
    root.resizable(False, False)
    
    lbl = tk.Label(root, text="AI 视觉分析 Web 服务正在运行...", pady=20)
    lbl.pack()
    
    def on_closing():
        root.destroy()
        sys.exit(0)
        
    btn = tk.Button(root, text="停止服务并退出", command=on_closing)
    btn.pack(pady=5)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
