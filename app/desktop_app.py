import webview
import threading
import uvicorn
import sys
import os
import socket
import time

# 获取当前脚本所在目录 (app 目录)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (app 的上一级目录)
project_root = os.path.dirname(current_dir)

# 将项目根目录添加到 sys.path，确保能以 app.main 的方式导入
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 静默模式：如果是 pythonw 运行，重定向输出以防报错
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
    """启动 FastAPI 服务"""
    # log_level="error" 让控制台清爽一些
    # 使用 uvicorn.run 时，若是在 pywebview 中，最好不要用 reload=True，除非是开发调试
    # 并且，在 pythonw 环境下，reload 可能会有问题。
    # 这里确保没有 reload
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
    except Exception as e:
        # 如果启动失败，可能是端口被占用等，尝试写入日志文件以便排查（因为没有 stdout）
        with open(os.path.join(current_dir, "server_error.log"), "w") as f:
            f.write(str(e))

def main():
    # 1. 获取端口 (使用动态端口避免冲突)
    port = get_free_port() 
    # port = 8000 
    
    # 2. 在独立线程中启动服务器
    t = threading.Thread(target=start_server, args=(port,))
    t.daemon = True
    t.start()
    
    # 减少等待时间，采用轮询检测端口方式
    start_time = time.time()
    server_started = False
    while time.time() - start_time < 5: # 增加超时时间到 5 秒
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            server_started = True
            break
        time.sleep(0.1)
    
    if not server_started:
        # 如果超时仍未启动，可能是端口被占用或其他错误
        # 尝试弹窗提示（仅限有 GUI 环境）
        # 这里为了简单，如果检测不到端口，还是尝试打开窗口，或者直接退出
        pass

    # 3. 创建 Webview 窗口
    # 注意：pywebview.create_window 必须在主线程调用
    window = webview.create_window(
        'AI 视觉特征分析平台', 
        f'http://127.0.0.1:{port}',
        width=1280, 
        height=850,
        resizable=True,
        min_size=(1024, 768) # 调整最小尺寸以适配宽屏分析
    )
    
    # 4. 启动 GUI 循环
    # debug=True 会开启开发者工具，但在 pythonw 下可能无效或报错，保持 False
    # gui='cef' 可能在某些环境下更稳定，或者默认 gui=None 自动选择
    webview.start(debug=False)

if __name__ == '__main__':
    main()
