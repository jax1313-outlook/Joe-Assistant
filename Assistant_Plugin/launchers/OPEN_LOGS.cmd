@echo off
cd /d "%~dp0.."
if not exist "logs" mkdir "logs"
start "" explorer "%CD%\logs"
exit /b 0
