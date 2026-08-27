@echo off
REM Workstream 5 - Assistant Research. Analysis over supplied sources.
setlocal
where py >nul 2>nul
if errorlevel 1 (echo   Python launcher "py" was not found. Needs Python 3.10 or newer.& exit /b 9009)
pushd "%~dp0"
py -m assistant_research %*
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
