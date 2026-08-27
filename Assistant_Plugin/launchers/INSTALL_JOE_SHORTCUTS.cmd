@echo off
REM ============================================================
REM  JOE - install desktop shortcuts
REM
REM  Puts JOE on the desktop so it opens with a double-click.
REM  No terminal, no paths, no Python commands afterwards.
REM
REM  Safe to run again - it overwrites its own shortcuts and
REM  touches nothing else on the desktop.
REM ============================================================
title JOE - Install Desktop Shortcuts
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   JOE - INSTALL DESKTOP SHORTCUTS
echo  ==============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_shortcuts.ps1" -PluginRoot "%CD%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo   Done. Look on your desktop for JOE.
) else (
  echo   Something went wrong. Nothing was removed.
)
echo.
pause
