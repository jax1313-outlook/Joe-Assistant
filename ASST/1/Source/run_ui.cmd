@echo off
REM Workstream 1 - Assistant UI. Opens the driver-facing Assistant window.
setlocal
where py >nul 2>nul
if errorlevel 1 (
  echo   Python launcher "py" was not found. Assistant UI needs Python 3.10 or newer.
  exit /b 9009
)
pushd "%~dp0"
py -m assistant_ui
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
