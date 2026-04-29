Set WshShell = CreateObject("WScript.Shell")
' 获取当前脚本所在目录的上一级目录 (项目根目录)
Set fso = CreateObject("Scripting.FileSystemObject")
strScriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
strProjectRoot = fso.GetParentFolderName(strScriptPath)

' 运行命令：先切换到项目根目录，再运行 pythonw
WshShell.Run "cmd /c cd /d """ & strProjectRoot & """ && pythonw app/desktop_app.py", 0
Set WshShell = Nothing
Set fso = Nothing
