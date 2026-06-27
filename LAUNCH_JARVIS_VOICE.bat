@echo off
title Saturday AI - LiveKit Voice Worker (JARVIS)
color 0B
set PYTHONIOENCODING=utf-8
cls
echo ======================================================================
echo           S.A.T.U.R.D.A.Y  -  L I V E K I T  V O I C E  A G E N T
echo ======================================================================
echo [SYSTEM] Initializing voice assistant worker subsystem...
echo.

:: Check environment variables
if not exist ".env" (
    echo [WARNING] No .env file found in active workspace!
    echo Please create one containing your LIVEKIT_URL, API keys, etc.
    echo.
)

:: Check python is on PATH
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found on system PATH!
    echo Please make sure Python is installed and configured.
    pause
    exit /b 1
)

echo [SYSTEM] Starting LiveKit Worker...
echo [INFO] Press Ctrl+C to terminate the voice session.
echo ======================================================================
echo.

python core/livekit_voice_agent.py dev

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Voice agent exited with code %errorlevel%.
    echo Please verify that all requirements are installed and .env keys are correct.
    pause
)
