@echo off
title Assistant Tests
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   JOE, THE LEVEL 1 ASSISTANT - AUTOMATED TESTS
echo  ==============================================================
py -X utf8 -m unittest discover -s tests -v > "logs\last_test_run.txt" 2>&1
set "RC=%ERRORLEVEL%"
type "logs\last_test_run.txt"
echo.
if "%RC%"=="0" (echo   RESULT: all tests passed.) else (echo   RESULT: tests FAILED. See logs\last_test_run.txt)
echo   Raw output: %CD%\logs\last_test_run.txt
echo.
pause
exit /b %RC%
