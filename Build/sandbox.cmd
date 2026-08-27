@echo off
REM Sandbox Engine v1 - main launcher
REM Usage:  sandbox.cmd <command> [options]
REM Examples:
REM   sandbox.cmd list
REM   sandbox.cmd new --request "What matters about tomorrow?"
REM   sandbox.cmd command SBX-... "Save this"
REM   sandbox.cmd sweep --advance-hours 3.1
REM   sandbox.cmd doctor

setlocal
where py >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python launcher "py" was not found on this machine.
  echo   Sandbox Engine v1 needs Python 3.10 or newer.
  echo.
  exit /b 9009
)
pushd "%~dp0"
py -m sandbox_engine.cli %*
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
