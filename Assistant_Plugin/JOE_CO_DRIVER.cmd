@echo off
REM  JOE - VOICE CO-DRIVER
REM
REM  Double-click this. It opens a window, checks the microphone, the model and
REM  the Dispatch node, and then waits for you to press ENTER and speak.
REM
REM  Dispatch must be running: DISPATCH_START_HERE.cmd in D:\Dispatch.
REM  DISPATCH_JOE_TOKEN must be set in this account's environment.

chcp 65001 >nul 2>&1
cd /d "%~dp0"
set PYTHONPATH=%~dp0
set PYTHONIOENCODING=utf-8

py -3 -m app.co_driver
if errorlevel 1 (
  echo.
  echo   JOE did not start. The lines above say which part is not ready.
)

echo.
pause
