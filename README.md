PoC: Dictation tray app (press-and-hold) using OpenAI Whisper

Overview

This project is a minimal proof-of-concept for a Windows tray app that records while a global hotkey is pressed and, on release, transcribes the recording and pastes the text to the active input.

Stack

- Python
- sounddevice (audio capture)
- whisper (OpenAI PyTorch implementation)
- keyboard (global hotkeys and typing)
- pystray (tray icon)
- pyperclip (clipboard handling)

Quick start (PowerShell)

1. Create a virtual environment and activate it (PowerShell):

```powershell
# from project root
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```

3. Run the app:

```powershell
python -m src.app
```

Notes

- `whisper` requires PyTorch. Installing CPU-only PyTorch via `pip` can be slow; consider following official PyTorch instructions for your platform if you want GPU support.
- This is a minimal POC, not production-ready. Hotkeys, permissions, error handling, and packaging will need improvements.
