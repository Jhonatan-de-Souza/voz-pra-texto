# Voice2Text - Background Speech-to-Text Service

A lightweight background service that transcribes speech to text using Whisper AI.

## Features

- 🎙️ **Background Service** - Runs silently in system tray
- ⚡ **Fast Transcription** - GPU-accelerated with Whisper (tiny model ~1 second)
- 📝 **Auto-Paste** - Transcribed text automatically pastes via Ctrl+V
- 💾 **Local Storage** - All transcriptions saved to SQLite database
- 🚀 **Auto-Start** - Included batch file for automatic startup
- 🎯 **Easy Hotkey** - Press **Ctrl+Windows** to record

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Test it:
```powershell
$env:WHISPER_MODEL = 'tiny'
pythonw c:\Git\voz-pra-texto\app_background_service.py
```

3. Press **Ctrl+Windows** → Speak → Release → Text appears!

## Auto-Start on Boot

1. Press **Win+R** and type: `shell:startup`
2. Copy `Voice2Text.bat` into that folder
3. Restart your computer - app starts automatically

## Usage

- **Ctrl+Windows** to start recording
- **Release keys** to transcribe and paste
- Click **notepad icon in tray** for options:
  - 📂 Open Data Folder
  - 📊 View Recent
  - ❌ Quit

## Data Storage

Transcriptions saved to: `C:\Users\YourUsername\.voz-pra-texto\transcriptions.db`

Includes:
- Timestamp
- Full transcription text
- Recording duration

## Performance

- **Recording to paste:** ~2-3 seconds (with GPU)
- **Idle CPU:** <1%
- **Idle RAM:** 200-300 MB
- **Disk space needed:** ~3GB for models

## Customization

### Change Speed vs Accuracy

```powershell
# Fastest (less accurate)
$env:WHISPER_MODEL = 'tiny'

# More accurate (slower)
$env:WHISPER_MODEL = 'base'
```

### Change Hotkey

Edit `app_background_service.py` line 35:
```python
HOTKEY = 'ctrl+win'  # Change to 'alt+v', 'f9', etc.
```

## Requirements

- Windows 10/11
- Python 3.8+
- 4GB RAM minimum
- 3GB disk space
- GPU recommended (NVIDIA/AMD)
