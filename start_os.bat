@echo off
chcp 65001 > nul
title IP PRIME OS - AI Desktop Environment

echo.
echo  ============================================================
echo      IP PRIME OS  --  AI Desktop Shell Environment
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
echo  [>>] Launching IP Prime OS Shell...
echo  ============================================================
echo.

python main.py --os-mode

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] IP Prime OS exited - Error code: %errorlevel%
    echo  Agar import error aaya ho toh run karo:
    echo     pip install -r requirements.txt
    echo.
    pause
)
