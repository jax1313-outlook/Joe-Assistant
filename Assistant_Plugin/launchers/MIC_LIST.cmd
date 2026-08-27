@echo off
title JOE - Microphone List
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   JOE - WHICH MICROPHONE CAN I HEAR?
echo  ==============================================================
echo.
echo   Lists every recording device Windows knows and marks the one
echo   JOE will hear. Nothing is recorded. You do not have to speak.
echo.
py -X utf8 proof\prove_microphone.py --list
echo.
echo   To actually test it, use the JOE Microphone Test shortcut.
echo.
pause
