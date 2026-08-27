@echo off
title Assistant Status
cd /d "%~dp0.."
echo.
py -X utf8 joe_main.py --status
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*joe_main.py*' }); if ($p.Count -gt 0) { Write-Host \"  Window running: yes ($($p.Count) process)\" } else { Write-Host '  Window running: no' }"
echo.
pause
