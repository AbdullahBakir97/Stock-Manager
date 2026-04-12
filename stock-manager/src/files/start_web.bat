@echo off
title Stock Manager Pro — Web Server
cd /d "%~dp0"

echo.
echo  Stock Manager Pro — Tablet Web Interface
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

:: Install Flask if missing
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo  Installing Flask...
    pip install flask
)

:: Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%

echo  Open this address on your Samsung tablet:
echo.
echo     http://%IP%:5000
echo.
echo  Make sure tablet is on the same WiFi as this PC.
echo  Press Ctrl+C to stop the server.
echo.

python web_server.py
pause
