@echo off
title Assistant - Outlook Accounts
cd /d "%~dp0.."
echo.
echo  ==============================================================
echo   OUTLOOK ACCOUNTS AVAILABLE TO THE ASSISTANT
echo  ==============================================================
echo   This briefly starts Outlook to read the account list.
echo   Read-only. Nothing is sent, changed, or deleted.
echo.
py -X utf8 joe_main.py --accounts
echo.
echo   To choose one, set  "account"  under  "outlook"  in
echo   configuration\joe.config.json  to an SMTP address above.
echo   Leave it empty to use the Outlook default store.
echo.
pause
