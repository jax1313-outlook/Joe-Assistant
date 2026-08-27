@echo off
title Voice Input Proof
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   VOICE INPUT PROOF - YOU WILL BE ASKED TO SPEAK
echo  ==============================================================
echo.
echo   You will be shown three phrases. Say each one clearly into
echo   the microphone. Nothing here can pass without your voice.
echo.
py -X utf8 proof\prove_voice_input.py %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo   RESULT: voice input is proven.
) else if "%RC%"=="2" (
  echo   RESULT: BLOCKED - no recognition engine available.
) else (
  echo   RESULT: voice input is NOT proven.
)
echo   Evidence: %CD%\proof\VOICE_INPUT_PROOF.md
echo.
pause
