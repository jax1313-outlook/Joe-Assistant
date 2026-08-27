@echo off
cd /d "%~dp0.."
if not exist "runtime_data" mkdir "runtime_data"
start "" explorer "%CD%\runtime_data"
exit /b 0
