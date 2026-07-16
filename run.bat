@echo off
echo ===================================================
echo     Karachi Flat Finder - Automated Setup and Run
echo ===================================================
echo.

:: Check if python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

:: Activate virtual environment and install packages
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Installing required packages...
pip install -r requirements.txt

echo [INFO] Initializing Playwright browser binaries...
playwright install chromium

:: Start server
echo [INFO] Starting Flask Web Server...
python app.py

pause
