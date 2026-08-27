@echo off
title Stop Assistant
cd /d "%~dp0.."
echo Stopping any running Assistant window...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$n=0; Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*joe_main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $n++ }; if ($n -gt 0) { Write-Host \"  Stopped $n Assistant process(es).\" } else { Write-Host '  No Assistant process was running.' }"
echo.
echo   Dispatch is unaffected by this. JOE is a plugin.
echo.
pause
