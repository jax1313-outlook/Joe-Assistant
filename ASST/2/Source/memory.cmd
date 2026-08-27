@echo off
REM Workstream 2 - Assistant Memory. Sandbox retention.
setlocal
where py >nul 2>nul
if errorlevel 1 (echo   Python launcher "py" was not found. Needs Python 3.10 or newer.& exit /b 9009)
pushd "%~dp0"
py -m assistant_memory %*
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
