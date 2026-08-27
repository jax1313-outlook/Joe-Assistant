@echo off
title JOE - Microphone Test
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   JOE - MICROPHONE TEST AND DIAGNOSTICS
echo  ==============================================================
echo.
echo   Shows every recording device Windows knows, says which one
echo   JOE will hear, then asks you to speak one test phrase.
echo.
echo   Connect your headset FIRST if you want to test it.
echo.
py -X utf8 proof\prove_microphone.py %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo   RESULT: JOE heard you, and did not hear itself.
) else if "%RC%"=="2" (
  echo   RESULT: NOT TESTED - no device connected, or run without a console.
) else (
  echo   RESULT: FAILED - see the detail above.
)
echo   Evidence: %CD%\proof\MICROPHONE_PROOF.md
echo.
pause
