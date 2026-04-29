@echo off
setlocal
cd /d "%~dp0.."

echo ===================================================
echo       AI Vision Feature Analysis Platform
echo ===================================================
echo.

:: 1. 尝试静默清理旧的 python 进程 (忽略错误)
taskkill /F /IM python.exe /T >nul 2>&1

:: 2. 预先打开浏览器 (等待服务启动)
echo Opening Browser...
start http://127.0.0.1:8000

:: 3. 启动服务 (在当前窗口运行，方便查看日志和关闭)
echo Starting Server...
echo.
echo [INFO] Server is starting. If the browser fails to load, please wait a moment and refresh.
echo [INFO] Press Ctrl+C in this window to stop the server.
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
