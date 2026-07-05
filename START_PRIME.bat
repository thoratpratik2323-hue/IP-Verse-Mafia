@echo off
chcp 65001 > nul
title IP PRIME OS
cls

:: Change directory to the folder where this batch file is located
cd /d "%~dp0"

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Launch directly into OS Shell mode
python main.py --os-mode

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] IP Prime crashed with code %errorlevel%.
    pause
)
