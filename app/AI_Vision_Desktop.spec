# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# 获取项目根目录
# SPECPATH 是 PyInstaller 注入的变量，指向 spec 文件的绝对路径
# 因为文件位于 app/AI_Vision_Desktop.spec，所以只需要向上两级找到项目根目录 (app -> root)
# 等等，如果 spec 在 app/ 目录下，向上两级是：app -> root -> parent_of_root?
# 不，SPECPATH 是文件路径， dirname(SPECPATH) 是 app/
# dirname(app/) 是 root/
spec_dir = os.path.dirname(os.path.abspath(SPECPATH))
project_root = os.path.dirname(spec_dir)

a = Analysis(
    [os.path.join(project_root, 'app', 'desktop_app.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, 'app', 'templates'), 'app/templates'), 
        (os.path.join(project_root, 'app', 'static'), 'app/static')
    ],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'jinja2', 'multipart', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PySide6', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI_Vision_Desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
