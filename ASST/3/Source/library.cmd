@echo off
REM Workstream 3 - Assistant Library. Read-only Company Library access.
setlocal
where py >nul 2>nul
if errorlevel 1 (echo   Python launcher "py" was not found. Needs Python 3.10 or newer.& exit /b 9009)
pushd "%~dp0"
py -m assistant_library %*
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
