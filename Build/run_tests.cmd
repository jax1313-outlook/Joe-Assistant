@echo off
REM Sandbox Engine v1 - run the automated test suite.
REM Writes the raw console output to Testing\_last_test_run.txt

setlocal
where py >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python launcher "py" was not found on this machine.
  echo   Sandbox Engine v1 needs Python 3.10 or newer.
  echo.
  exit /b 9009
)
pushd "%~dp0.."
echo.
echo ====================================================================
echo  SANDBOX ENGINE v1 - AUTOMATED TESTS
echo ====================================================================
py -m unittest discover -s Testing -v > "Testing\_last_test_run.txt" 2>&1
set "RC=%ERRORLEVEL%"
type "Testing\_last_test_run.txt"
echo.
if "%RC%"=="0" (
  echo   RESULT: all tests passed.
) else (
  echo   RESULT: one or more tests FAILED. See Testing\_last_test_run.txt
)
echo   Raw output: %CD%\Testing\_last_test_run.txt
popd
endlocal & exit /b %RC%
