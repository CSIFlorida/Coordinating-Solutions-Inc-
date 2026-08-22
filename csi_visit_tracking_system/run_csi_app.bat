@echo off
cd /d "%~dp0"
echo ============================================
echo  CSI Visit Tracking System - setup
echo ============================================
echo.

set PYCMD=

where python >nul 2>nul
if not errorlevel 1 (
    python --version >nul 2>nul
    if not errorlevel 1 set PYCMD=python
)

if "%PYCMD%"=="" (
    where py >nul 2>nul
    if not errorlevel 1 (
        py --version >nul 2>nul
        if not errorlevel 1 set PYCMD=py
    )
)

if "%PYCMD%"=="" (
    echo Python was not found on this computer.
    echo.
    echo Opening the Python download page for you now. During installation,
    echo make sure to check "Add python.exe to PATH" on the first install
    echo screen, then close this window and double-click this file again.
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Found Python via "%PYCMD%".
echo.
echo Installing required Python packages...
%PYCMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo pip install failed. Scroll up to see the error above.
    pause
    exit /b 1
)

if not exist "data\csi_visit_tracker.db" (
    echo.
    echo First run detected - importing the starter spreadsheet...
    %PYCMD% import_consumers.py "EMedi Stats 07-01-2026 - WORKING DOC.xlsx"
)

echo.
echo Starting the app at http://localhost:5000 ...
echo First person to open it should tap "Set Up Manager Account".
start "" http://localhost:5000
%PYCMD% app.py

pause
