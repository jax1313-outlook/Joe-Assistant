@echo off
REM Workstream 6 - Assistant Voice. Runs the test suite.
setlocal
where py >nul 2>nul
if errorlevel 1 (echo   Python launcher "py" was not found. Needs Python 3.10 or newer.& exit /b 9009)
pushd "%~dp0.."
py -m unittest discover -s Tests -v > "Tests\_last_test_run.txt" 2>&1
set "RC=%ERRORLEVEL%"
type "Tests\_last_test_run.txt"
if "%RC%"=="0" (echo.& echo   RESULT: all tests passed.) else (echo.& echo   RESULT: tests FAILED.)
popd
endlocal & exit /b %RC%
