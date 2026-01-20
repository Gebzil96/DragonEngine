Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """" & WScript.ScriptFullName & "\..\start_DragonEngine.bat""", 0, False
