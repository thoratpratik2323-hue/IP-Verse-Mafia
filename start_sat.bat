@echo off
chcp 65001 > nul
title IP PRIME - SAT Orb UI Skin

echo.
echo  ============================================================
echo      IP PRIME  --  SAT Orb UI Skin Mode
echo  ============================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    echo  [OK] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo  [OK] Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo  [>>] Launching IP Prime with SAT Orb UI Skin...
echo  ============================================================
echo.

python main.py --sat-mode

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Exited with error code: %errorlevel%
    pause
)
