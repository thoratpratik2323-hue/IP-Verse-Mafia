@echo off
chcp 65001 >nul
title IP PRIME — AI Assistant
color 0A

echo.
echo  ██╗██████╗     ██████╗ ██████╗ ██╗███╗   ███╗███████╗
echo  ██║██╔══██╗    ██╔══██╗██╔══██╗██║████╗ ████║██╔════╝
echo  ██║██████╔╝    ██████╔╝██████╔╝██║██╔████╔██║█████╗
echo  ██║██╔═══╝     ██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝
echo  ██║██║         ██║     ██║  ██║██║██║ ╚═╝ ██║███████╗
echo  ╚═╝╚═╝         ╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝
echo.
echo  ============================================================
echo   IP PRIME — Intelligent Personal Assistant  ^| by Pratik
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found! Please install Python 3.11+
    echo  Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Show Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] %PYVER% detected
echo.

:: Check if venv exists, activate it
if exist ".venv\Scripts\activate.bat" (
    echo  [OK] Virtual environment found — activating...
    call .venv\Scripts\activate.bat
    echo  [OK] Venv activated
) else if exist "venv\Scripts\activate.bat" (
    echo  [OK] Virtual environment found — activating...
    call venv\Scripts\activate.bat
    echo  [OK] Venv activated
) else (
    echo  [INFO] No venv found — using system Python
)

echo.
echo  [>>] Launching IP Prime...
echo  ============================================================
echo.

:: Launch main.py
python main.py

:: If it crashes, show error
if %errorlevel% neq 0 (
    echo.
    echo  ============================================================
    echo  [WARNING] IP Prime exited with error code: %errorlevel%
    echo  ============================================================
    echo.
    echo  Agar koi import error aaya ho toh run karo:
    echo    pip install -r requirements.txt
    echo.
    pause
)
