@echo off
REM ============================================================
REM  LEVEL 1 ASSISTANT - DISPATCH PLUGIN
REM  Double-click this file to open JOE.
REM
REM  Dispatch does not need this program. Closing or deleting
REM  JOE does not affect Dispatch.
REM ============================================================
cd /d "%~dp0"

where pyw >nul 2>nul
if not errorlevel 1 goto :havepyw
where py >nul 2>nul
if not errorlevel 1 goto :havepy

echo.
echo   The Python launcher was not found on this machine.
echo   JOE needs Python 3.10 or newer from python.org.
echo.
pause
exit /b 9009

:havepyw
REM pyw opens the window with no console behind it
start "" pyw -X utf8 "%~dp0joe_main.py"
exit /b 0

:havepy
REM fallback: py in its own window
start "Assistant runtime" /min py -X utf8 "%~dp0joe_main.py"
exit /b 0
