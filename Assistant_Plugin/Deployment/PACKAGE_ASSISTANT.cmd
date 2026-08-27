@echo off
REM ============================================================
REM  Build a clean deployment candidate of JOE, the Level 1 Assistant.
REM
REM  Produces:  Deployment\Assistant_Plugin_v1.0.0\
REM  Excludes:  runtime_data, logs, __pycache__, test/proof workspaces,
REM             and the machine-specific configuration file.
REM
REM  Nothing is installed. Nothing touches Dispatch.
REM
REM  THE FILE NAMES BELOW MUST TRACK THE SOURCE. This script once excluded
REM  "assistant.config.json" and shipped "assistant_main.py". The program was
REM  renamed to JOE and this script was not, so the exclusion silently stopped
REM  matching anything and the candidate went stale for months - it was still
REM  shipping the pre-rename build long after the source had moved on. The
REM  verification block at the end exists so that can never pass unnoticed
REM  again: a package that ships the wrong thing must fail loudly here rather
REM  than quietly on the machine it is deployed to.
REM ============================================================
setlocal
cd /d "%~dp0.."
set "OUT=%~dp0Assistant_Plugin_v1.0.0"

echo.
echo   Building deployment candidate...
echo   Target: %OUT%
echo.

if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"

robocopy "%CD%" "%OUT%" /E ^
  /XD runtime_data logs __pycache__ _workspace Deployment .git ^
  /XF joe.config.json last_test_run.txt joe.log assistant.log ^
  /NFL /NDL /NJH /NJS /NP >nul

REM the candidate ships the template, not the machine-specific config
if exist "%OUT%\configuration\joe.config.json" del "%OUT%\configuration\joe.config.json"

REM empty folders the program recreates on first run
mkdir "%OUT%\runtime_data" 2>nul
mkdir "%OUT%\logs" 2>nul

echo   Verifying the candidate...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify_package.ps1" "%OUT%"
if errorlevel 1 (
  echo.
  echo   BUILD REJECTED. The candidate above was not fit to deploy.
  echo.
  pause
  exit /b 1
)

echo.
echo   To deploy: copy Assistant_Plugin_v1.0.0 anywhere, copy
echo   configuration\joe.config.template.json to
echo   configuration\joe.config.json, edit your Library path,
echo   then double-click START_JOE.cmd
echo.
pause
