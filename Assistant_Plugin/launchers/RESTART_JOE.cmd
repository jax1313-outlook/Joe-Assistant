@echo off
title Restart Assistant
cd /d "%~dp0"
call "%~dp0STOP_JOE.cmd" >nul 2>nul
timeout /t 2 /nobreak >nul
cd /d "%~dp0.."
start "" /b py -X utf8 joe_main.py
echo   Assistant restarted.
timeout /t 2 /nobreak >nul
exit /b 0
