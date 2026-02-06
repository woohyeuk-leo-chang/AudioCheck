@echo off
cd /d "%~dp0"
echo ========================================
echo    Starting AudioCheck (Windows)
echo ========================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation.
    pause
    exit /b
)

:: 2. Setup/Verify Virtual Environment
if not exist ".venv\Scripts\activate.bat" (
    echo First-time setup: Creating isolated environment...
    if exist ".venv" rmdir /s /q ".venv"
    python -m venv .venv
    
    if not exist ".venv\Scripts\activate.bat" (
        echo Error: Failed to create virtual environment.
        pause
        exit /b
    )
)

:: Activate
call .venv\Scripts\activate.bat

:: 3. Ensure Dependencies are Installed
echo Checking dependencies...

:: Check for FFMPEG (Required for Whisper)
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FFMPEG is missing!
    echo Whisper requires FFMPEG to process audio.
    echo.
    echo To install, open PowerShell as Administrator and run:
    echo     winget install ffmpeg
    echo.
    echo Or download from: https://ffmpeg.org/download.html
    echo.
    pause
)

:: Install Python libs
pip install -r requirements.txt

:: 4. Run the App
echo Launching GUI...
streamlit run audiocheck_gui.py

if %errorlevel% neq 0 (
    echo.
    echo App crashed or closed.
    pause
)
