Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strScriptPath = fso.GetParentFolderName(WScript.ScriptFullName)
' 增加 cmd /c cd /d 确保路径正确，增加双引号防止路径空格问题
WshShell.Run "cmd /c cd /d """ & strScriptPath & """ && pythonw app/main_launcher.py", 0
Set WshShell = Nothing
