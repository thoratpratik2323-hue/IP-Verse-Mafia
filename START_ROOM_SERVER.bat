@echo off
title Saturday AI - Room Server (Mobile Access)
color 0A
set PYTHONIOENCODING=utf-8
cls
echo ======================================================================
echo         S.A.T.U.R.D.A.Y  --  MOBILE ROOM SERVER
echo ======================================================================
echo.
echo [1] First, make sure LAUNCH_JARVIS_VOICE.bat is running in another window!
echo [2] Then open the Mobile URL shown below on your phone (same WiFi).
echo.
echo Press Ctrl+C to stop the room server.
echo ======================================================================
echo.
python room_server.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Room server exited. Check that Flask is installed.
    echo Run: pip install flask
    pause
)
