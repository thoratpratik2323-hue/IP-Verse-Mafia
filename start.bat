@echo off
chcp 65001 > nul
title IP PRIME - AI Assistant

echo.
echo  ============================================================
echo      IP PRIME  --  Intelligent Personal AI Assistant
echo                      by Pratik Thorat
echo  ============================================================
echo.

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found! Install Python 3.11+ first.
    pause
    exit /b 1
)

python --version
echo.

if exist ".venv\Scripts\activate.bat" (
    echo  [OK] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo  [OK] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo  [INFO] No venv found - using system Python
)

echo.
echo  [>>] Launching IP Prime...
echo  ============================================================
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] IP Prime crashed - Error code: %errorlevel%
    echo  Agar import error aaya ho toh run karo:
    echo     pip install -r requirements.txt
    echo.
    pause
)
