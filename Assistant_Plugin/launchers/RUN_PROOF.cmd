@echo off
title Assistant Local Proof
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   JOE, THE LEVEL 1 ASSISTANT - LOCAL OPERATIONAL PROOF
echo  ==============================================================
py -X utf8 proof\run_proof.py %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo   RESULT: all proof steps passed.) else (echo   RESULT: one or more proof steps FAILED.)
echo   Report: %CD%\docs\JOE_LOCAL_PROOF_REPORT_v1.md
echo.
pause
exit /b %RC%
