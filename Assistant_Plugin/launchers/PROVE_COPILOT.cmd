@echo off
title Copilot Live Proof
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   MICROSOFT 365 COPILOT - LIVE PROOF   (PILOT / PREVIEW)
echo  ==============================================================
echo.
echo   This sends ONE real prompt to Microsoft 365 Copilot.
echo   It will ask you to sign in if you are not already.
echo.
py -X utf8 proof\prove_copilot.py %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo   RESULT: reasoning is LIVE and proven.
) else if "%RC%"=="2" (
  echo   RESULT: BLOCKED - a step only Mike can take is missing.
) else (
  echo   RESULT: FAILED - reasoning is NOT proven.
)
echo   Evidence: %CD%\proof\COPILOT_LIVE_PROOF.md
echo.
pause
