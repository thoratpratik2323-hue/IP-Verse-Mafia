@echo off
chcp 65001 > nul
title IP PRIME - MASTER LAUNCHER
color 0A
cls

echo.
echo  ============================================================
echo               IP PRIME MASTER LAUNCHER (v1.0)
echo                      by Pratik Thorat
echo  ============================================================
echo.
echo   [1] Launch OS Shell Mode (Desktop Shell GUI) [DEFAULT]
echo   [2] Launch Simple GUI Mode (Floating Assistant Window)
echo   [3] Launch Saturday Voice Server Only (Headless)
echo.
echo  ============================================================
echo  Select mode (auto-selecting [1] in 5 seconds)...

choice /c 123 /t 5 /d 1 /n /m " > Select (1-3): "
set mode=%errorlevel%

:: Detect and activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo  [OK] Activating virtual env (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo  [OK] Activating virtual env (venv)...
    call venv\Scripts\activate.bat
) else (
    echo  [INFO] No venv found - running with global Python...
)

echo.
echo  [>>] Spawning Saturday Voice Worker in background...
start "Saturday Voice Agent" /min cmd /c "title Saturday Voice Agent && python core\livekit_voice_agent.py dev"

if "%mode%"=="1" (
    echo  [>>] Launching IP Prime OS Shell GUI...
    echo  ============================================================
    python main.py --os-mode
)
if "%mode%"=="2" (
    echo  [>>] Launching IP Prime Simple GUI...
    echo  ============================================================
    python main.py
)
if "%mode%"=="3" (
    echo  [>>] Headless Voice Mode Active. Press Ctrl+C to close.
    echo  ============================================================
    python core/livekit_voice_agent.py dev
)

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Execution exited with error code %errorlevel%.
    pause
)
