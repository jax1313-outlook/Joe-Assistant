@echo off
REM Sandbox Engine v1 - run the ten local proofs and regenerate
REM Testing\LOCAL_PROOF_REPORT_v1.md
REM
REM NOTE: this resets the demonstration Sandbox so the visible result is
REM reproducible. Pass --no-reset to keep what is already there.

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
py "Testing\proof_local.py" %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo   RESULT: all ten proofs passed.
) else (
  echo   RESULT: one or more proofs FAILED.
)
echo   Report: %CD%\Testing\LOCAL_PROOF_REPORT_v1.md
popd
endlocal & exit /b %RC%
