@echo off
setlocal
cd /d "%~dp0.."

echo Starting AI Vision Desktop App...
echo.

:: 检查是否安装了 pywebview
pip show pywebview >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing pywebview...
    pip install pywebview
)

:: 启动桌面应用
python app/desktop_app.py

pause
