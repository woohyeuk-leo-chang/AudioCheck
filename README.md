# AudioCheck

**AudioCheck** is a user-friendly tool for verifying and correcting audio transcriptions. It uses local AI (OpenAI Whisper) to automatically transcribe potential participant audio and compares it against target phrases, highlighting errors for easy verification.

Designed with minimal technical setup required.

## ✨ Key Features

*   **🚀 One-Click Startup**: Double-click `Run AudioCheck.command` to handle all dependencies (Python, AI models, libraries) automatically.
*   **💾 Auto-Save**: Every edit, correction, or checkbox toggle is saved **instantly**. You never need to worry about losing work.
*   **🤖 Local AI**: Uses **OpenAI Whisper** running locally on your Mac. No internet required after initial setup, no API keys, and complete data privacy.
*   **🧠 Smart Scoring**: Automatically calculates similarity scores between the participant's speech and the target phrase, ignoring capitalization and punctuation.
*   **📂 Smart Loading**: Automatically detects your data folder. No need to type complex file paths.

---

## 🛠️ Installation & Setup

### Prerequisites

* **Operating System**: macOS or Windows 10/11
* **FFmpeg** (Required for Whisper)
  + *macOS*: Script installs via Homebrew
  + *Windows*: Script guides you to install via `winget` or manual download

### First Time Setup

**Choose one of the following methods:**

#### Option 1: Clone with Git (Recommended)

If you have Git installed on your computer:

1. **Open Terminal** (macOS) or **Command Prompt/PowerShell** (Windows)

2. **Navigate to where you want to install AudioCheck**:
   ```bash
   cd ~/Desktop  # Or any folder you prefer
   ```

3. **Clone the repository**:
   ```bash
   git clone https://github.com/woohyeuk-leo-chang/AudioCheck.git
   ```

4. **Navigate into the folder**:
   ```bash
   cd AudioCheck
   ```

5. **Continue to "Running the Application"** below

#### Option 2: Download ZIP

If you don't have Git installed:

1. **Download** the repository:
   * Click the green **"Code"** button
   * Select **"Download ZIP"**

2. **Extract** the ZIP file to a location on your computer (e.g., Desktop or Documents)

3. **Continue to "Running the Application"** below

---

### Running the Application

1. **Locate** the startup script in the `AudioCheck` folder:
   * **macOS**: `Run AudioCheck.command`
   * **Windows**: `Run AudioCheck.bat`

2. **Launch the application**:
   * **macOS**: 
     - Right-click on `Run AudioCheck.command`
     - Select **"Open"**
     - If prompted, click **"Open"** again to authorize
   * **Windows**: 
     - Double-click `Run AudioCheck.bat`
     - If "Windows protected your PC" appears:
       + Click **"More info"**
       + Click **"Run anyway"**

3. **First-time setup** (automatic):
   * The script will create a Python virtual environment
   * Download and install necessary libraries
   * This takes ~2-5 minutes
   * A browser window will open when ready

---

### Updating AudioCheck

If you used **Git clone**, you can easily update to the latest version:

```bash
cd AudioCheck
git pull origin main
```

If you **downloaded the ZIP**, you'll need to download the latest version manually and extract it again.

---

## 📂 Folder Structure

The tool expects your folders to be organized as follows:

```text
AudioCheck/
├── Run AudioCheck.command   <-- Double-click this to start
├── audiocheck_gui.py
├── data/                    <-- Create this folder!
│   ├── 101/                 <-- Participant ID Folder
│   │   ├── 101_data.csv     <-- Input CSV
│   │   └── audio/           <-- Audio files folder
│   │       ├── block1/
│   │       │   └── trial1.wav
│   │       └── ...
│   └── 102/
│       └── ...
```

**Note**: If the `data` folder is missing, the app will show a help screen instructing you where to put it.

---

## 🚀 How to Use

1.  **Launch**: Double-click `Run AudioCheck` (macOS: `.command` / Windows: `.bat`). A browser window will open.
2.  **Select Participant**: Use the sidebar dropdown to choose a participant ID (e.g., `101`, `102`).
3.  **Transcription**:
    *   If no results exist, click **"Run Transcription Now"**.
    *   *First Run Note*: If this is your very first time, the tool will download the Whisper AI model (~140MB). This takes about 1 minute.
    *   Once complete, the page refreshes with the data.
4.  **Review & Verify**:
    *   **Listen**: Use the audio player to hear the recording.
    *   **Compare**: Look at the **Target Phrase** (what they should have said) vs. **Transcribed Text** (what the AI heard).
    *   **Score**: A similarity score (0.0 to 1.0) indicates accuracy.
5.  **Correct**:
    *   **Edit**: Type in the text box to fix the transcription. *Autosaves instantly.*
    *   **Mark Correct**: Check the box if the response is valid despite minor differences. *Autosaves instantly.*

### Filters
*   **Similarity Threshold**: Use the slider in the sidebar to only show "Problem Trials" (e.g., score < 0.8) so you don't have to review perfect matches.

---

## ⚠️ Troubleshooting

**"FFMPEG is missing"**
*   The startup script tries to install it. If it fails, install Homebrew by pasting this into your Terminal:
    `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
    Then run the script again.

**"Transcription is slow"**
*   Whisper runs on your computer's CPU/GPU. Older Macs may take 2-5 seconds per audio file. Newer M1/M2/M3 Macs are very fast.

**"I don't see my changes"**
*   Changes are saved to `[ID]_transcription_results.csv` inside the participant's folder. If you re-run the transcription, this file might be overwritten, so be careful using the "Re-run" button if you have manually edited many variations.

