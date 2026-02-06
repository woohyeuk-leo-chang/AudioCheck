#!/bin/bash
cd "$(dirname "$0")"

# --- Auto-Setup for portability ---
VENV_DIR=".venv"

echo "========================================"
echo "   Starting AudioCheck"
echo "========================================"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please ask the user to install Python (e.g., from python.org)."
    read -p "Press enter to exit..."
    exit 1
fi

# 2. Setup/Verify Virtual Environment
# Check if activate script exists, not just the directory
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "First-time setup: Creating isolated environment..."
    # Remove potentially broken directory
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    
    # Check if venv creation succeeded
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo "Error: Failed to create virtual environment."
        read -p "Press enter to exit..."
        exit 1
    fi
fi

# Activate
source "$VENV_DIR/bin/activate"

# 3. Ensure Dependencies are Installed
# 3. Ensure Dependencies are Installed
echo "Checking dependencies..."
# Check for system dependency: FFMPEG (Required for Whisper)
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFMPEG is missing! This is required for Whisper transcription."
    if command -v brew &> /dev/null; then
        echo "Attempting to install via Homebrew..."
        brew install ffmpeg
    else
        echo "❌  Could not find Homebrew. Please install FFMPEG manually."
        echo "    Visit: https://ffmpeg.org/download.html"
        echo "    Or install Homebrew: https://brew.sh/"
        read -p "Press enter to continue (transcription might fail)..."
    fi
fi

# Always run install to ensure new requirements (like whisper) are picked up
# --upgrade strategy only-if-needed is default, so it's fast if already satisfied
pip install -r requirements.txt

# 4. Run the App
echo "Launching GUI..."
streamlit run audiocheck_gui.py

# Keep terminal open if it crashes
if [ $? -ne 0 ]; then
    read -p "Press enter to exit..."
fi
