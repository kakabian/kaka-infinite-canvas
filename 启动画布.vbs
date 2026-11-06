Option Explicit
Dim sh, fso, dir, py, ex, out
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
py = dir & "\.venv\Scripts\python.exe"

If Not fso.FileExists(py) Then
  MsgBox "Python venv not found: " & py, 16, "Infinite Canvas"
  WScript.Quit 1
End If

Set ex = sh.Exec("cmd /c netstat -ano -p tcp ^| findstr LISTENING ^| findstr "":10027""")
out = ex.StdOut.ReadAll()
If InStr(out, ":10027") = 0 Then
  sh.Run """" & py & """ -m backend.run_worker", 0, False
  WScript.Sleep 2000
  sh.Run """" & py & """ """ & dir & "\run.py""", 0, False
  WScript.Sleep 6000
End If

sh.Run "http://127.0.0.1:10027/", 1, False