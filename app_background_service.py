import os
import queue
import sys
import tempfile
import threading
import time
import wave
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import font

import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw

# keyboard can require elevated privileges on Windows in some cases
import keyboard

# Whisper (OpenAI) - PyTorch implementation
import whisper

# Set process name for Task Manager
try:
    from setproctitle import setproctitle
    setproctitle("Voice2Text")
except ImportError:
    pass

# Configuration
HOTKEY = 'ctrl+win'
SAMPLE_RATE = 16000
CHANNELS = 1

# GPU/Device settings
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# Data storage
APP_DATA_DIR = Path(os.path.expanduser('~')) / '.voz-pra-texto'
DB_PATH = APP_DATA_DIR / 'transcriptions.db'
AUDIO_DIR = APP_DATA_DIR / 'audio_files'

# Global state
recording = False
audio_queue = queue.Queue()
frames = []
stream = None
record_thread = None
popup_window = None
popup_label = None
popup_queue = queue.Queue()  # Queue for popup commands
gui_thread = None

# Load whisper model
MODEL_NAME = os.environ.get('WHISPER_MODEL', 'small')
print(f"Loading Whisper model: {MODEL_NAME} (this may take a while)")
model = whisper.load_model(MODEL_NAME, device=DEVICE)
print(f"✅ Whisper loaded on {DEVICE}")


def setup_directories():
    """Create necessary directories for storing data"""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def setup_database():
    """Initialize SQLite database for storing transcriptions and summaries"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            audio_file TEXT,
            transcription TEXT NOT NULL,
            summary TEXT,
            duration REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def gui_thread_func():
    """Dedicated GUI thread that runs tkinter mainloop"""
    global popup_window, popup_label
    
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    def check_queue():
        """Check for popup commands from other threads"""
        global popup_window, popup_label
        
        try:
            while not popup_queue.empty():
                command = popup_queue.get_nowait()
                
                if command['action'] == 'show':
                    # Close existing popup if any
                    if popup_window is not None:
                        try:
                            popup_window.destroy()
                        except:
                            pass
                    
                    # Create new popup
                    popup_window = tk.Toplevel(root)
                    popup_window.geometry("250x120")
                    popup_window.config(bg="#2b2b2b")
                    popup_window.attributes('-topmost', True)
                    popup_window.resizable(False, False)
                    popup_window.overrideredirect(True)
                    
                    # Center on screen
                    popup_window.update_idletasks()
                    x = (popup_window.winfo_screenwidth() // 2) - (250 // 2)
                    y = (popup_window.winfo_screenheight() // 2) - (120 // 2)
                    popup_window.geometry(f"250x120+{x}+{y}")
                    
                    # Add label
                    font_style = font.Font(family="Arial", size=16, weight="bold")
                    popup_label = tk.Label(popup_window, text=command['message'], 
                                          fg="#4da6ff", bg="#2b2b2b", font=font_style)
                    popup_label.pack(expand=True)
                    
                elif command['action'] == 'hide':
                    if popup_window is not None:
                        try:
                            popup_window.destroy()
                            popup_window = None
                            popup_label = None
                        except:
                            pass
                
                elif command['action'] == 'update':
                    if popup_label is not None:
                        try:
                            popup_label.config(text=command['message'])
                        except:
                            pass
        
        except queue.Empty:
            pass
        
        # Schedule next check
        root.after(50, check_queue)
    
    # Start checking queue
    check_queue()
    
    # Run tkinter mainloop
    root.mainloop()


def show_popup(message: str):
    """Show popup window with message (thread-safe)"""
    popup_queue.put({'action': 'show', 'message': message})


def hide_popup():
    """Hide popup window (thread-safe)"""
    popup_queue.put({'action': 'hide'})


def update_popup(message: str):
    """Update popup message (thread-safe)"""
    popup_queue.put({'action': 'update', 'message': message})


def animate_popup_thread():
    """Animate popup with dots in background thread"""
    dots = ["●", "●●", "●●●"]
    for dot in dots * 3:
        try:
            update_popup(f"Transcribing...\n{dot}")
            time.sleep(0.3)
        except:
            break


def make_icon() -> Image.Image:
    """Create a notepad icon"""
    size = 64
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    # Draw notepad paper
    d.rectangle((12, 10, 52, 54), fill=(245, 245, 200), outline=(120, 120, 120), width=2)
    # Draw lines on notepad
    for i in range(18, 52, 7):
        d.line([(15, i), (49, i)], fill=(200, 200, 150), width=1)
    # Draw microphone indicator
    d.ellipse((26, 8, 38, 14), fill=(255, 80, 80))
    return img


def audio_callback(indata, frames_count, time_info, status):
    if status:
        print(f"Sounddevice status: {status}")
    # copy data to queue as bytes
    audio_queue.put(indata.copy())


def record_thread_func(stream):
    global recording, frames
    frames = []
    while recording:
        try:
            chunk = audio_queue.get(timeout=0.5)
            frames.append(chunk)
        except queue.Empty:
            continue


def start_recording():
    global recording, stream, record_thread
    if recording:
        return
    recording = True
    show_popup("🎙️ Listening...")
    print("🎙️ Starting recording...")
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback)
    stream.start()
    record_thread = threading.Thread(target=record_thread_func, args=(stream,), daemon=True)
    record_thread.start()


def stop_recording_and_transcribe():
    global recording, stream, frames
    if not recording:
        return
    print("⏹️ Stopping recording...")
    recording = False
    try:
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"Error stopping stream: {e}")

    # concatenate frames
    if not frames:
        print("⚠️ No audio captured. Skipping transcription.")
        return

    audio_data = np.concatenate(frames, axis=0)
    duration = len(audio_data) / SAMPLE_RATE
    
    # Verify we have valid audio data
    if len(audio_data) == 0:
        print("⚠️ No valid audio data. Skipping transcription.")
        return
    audio_data = (audio_data * 32767).astype(np.int16)

    # Save to temp WAV
    fd, path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    print(f"Saved recording to {path}, launching transcription...")

    # Transcribe and paste - run in a new thread to avoid blocking main
    t = threading.Thread(target=transcribe_and_paste, args=(path, duration), daemon=True)
    t.start()


def check_ollama_available():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False


def summarize_with_ollama(text: str) -> str:
    """
    Summarize text using Ollama (free, local LLM)
    Falls back to extractive summary if Ollama unavailable
    """
    if not check_ollama_available():
        print("⚠️ Ollama not running. Using simple summarization...")
        return simple_summarize(text)
    
    try:
        prompt = f"""You will receive a raw voice-note transcription.
Summarize it **without changing my tone, wording style, or way of speaking**.

Rules:
* Keep my natural, spoken style (including informal phrasing).
* Do NOT make it sound formal, written, or "polished".
* Remove repetitions, filler, and tangents (e.g. "like", "you know", circular explanations).
* Keep the original intent, emphasis, and ordering of ideas.
* Do not add conclusions, interpretations, or new framing.

Output format:
* Short, clean paragraphs or bullet points
* Same voice as the original, just clearer and tighter

Transcription:
{text}

Cleaned up version:"""
        
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={
                'model': OLLAMA_MODEL,
                'prompt': prompt,
                'stream': False,
                'temperature': 0.2,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result.get('response', '').strip()
            return summary
        else:
            print(f"Ollama error: {response.status_code}")
            return simple_summarize(text)
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return simple_summarize(text)


def simple_summarize(text: str) -> str:
    """
    Simple extractive summarization when LLM unavailable
    Takes first 2-3 sentences as summary
    """
    sentences = text.split('. ')
    summary = '. '.join(sentences[:3])
    if len(summary) > 200:
        summary = summary[:200] + "..."
    return summary


def save_to_database(transcription: str, duration: float, audio_file: str = None):
    """Save transcription to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO transcriptions (timestamp, audio_file, transcription, duration)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, audio_file, transcription, duration))
        
        conn.commit()
        conn.close()
        print(f"✅ Saved to database")
    except Exception as e:
        print(f"Error saving to database: {e}")


def transcribe_and_paste(wav_path: str, duration: float):
    try:
        show_popup("Transcribing...\n●")
        print("🔄 Transcribing...")
        
        # Start animation in background
        animation_thread = threading.Thread(target=animate_popup_thread, daemon=True)
        animation_thread.start()
        
        # Run transcription in a thread
        def transcribe_thread():
            try:
                result = model.transcribe(wav_path)
                text = result.get('text', '').strip()
                
                print(f"✅ Transcription: {text[:100]}...")
                
                if text:
                    # Save to database
                    save_to_database(text, duration)
                    
                    # Copy transcription to clipboard
                    pyperclip.copy(text)
                    # Small delay to ensure clipboard is set
                    time.sleep(0.05)
                    # Send Ctrl+V to paste the transcription
                    keyboard.send('ctrl+v')
                    time.sleep(0.05)
                    
                    hide_popup()
                    print("✨ Transcription pasted!")
                else:
                    hide_popup()
                    print("⚠️ No text captured")
            except Exception as e:
                hide_popup()
                print(f"Error during transcription: {e}")
            finally:
                # Delete temp file after transcription completes
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
        
        t = threading.Thread(target=transcribe_thread, daemon=True)
        t.start()
        
    except Exception as e:
        hide_popup()
        print(f"Error: {e}")


def setup_hotkeys():
    """Setup keyboard hotkeys for recording"""
    # Use add_hotkey to properly detect key press
    keyboard.add_hotkey('ctrl+win', lambda: start_recording())
    
    # For key release, hook and check
    ctrl_pressed = {'value': False}
    win_pressed = {'value': False}
    
    def _on_key_event(e):
        try:
            if e.event_type == 'down':
                if e.name == 'ctrl':
                    ctrl_pressed['value'] = True
                elif e.name == 'windows' or e.name == 'cmd':
                    win_pressed['value'] = True
            elif e.event_type == 'up':
                if e.name == 'ctrl':
                    ctrl_pressed['value'] = False
                elif e.name == 'windows' or e.name == 'cmd':
                    win_pressed['value'] = False
                
                # If either key is released while recording, stop
                if recording and (not ctrl_pressed['value'] or not win_pressed['value']):
                    stop_recording_and_transcribe()
        except Exception as ex:
            print(f"Hotkey check error: {ex}")

    keyboard.hook(_on_key_event)


def open_data_folder(icon=None, item=None):
    """Open the data folder in explorer"""
    os.startfile(APP_DATA_DIR)


def open_database_viewer(icon=None, item=None):
    """Show recent transcriptions"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, transcription
            FROM transcriptions 
            ORDER BY id DESC 
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        output = "Recent Transcriptions:\n\n"
        for timestamp, transcription in rows:
            output += f"📅 {timestamp}\n"
            output += f"📝 {transcription[:100]}...\n\n"
        
        print(output)
        return output
    except Exception as e:
        print(f"Error reading database: {e}")
        return f"Error: {e}"


def create_tray():
    """Create system tray icon with menu"""
    icon = pystray.Icon('voice2text', make_icon())

    def on_quit(icon, item):
        print('Quitting...')
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            icon.stop()
        except Exception:
            pass
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem('📂 Open Data Folder', open_data_folder),
        pystray.MenuItem('📊 View Recent', open_database_viewer),
        pystray.MenuItem('Quit', on_quit),
    )
    
    icon.menu = menu
    icon.title = "Voice2Text"
    return icon


def main():
    """Main application entry point"""
    global gui_thread
    
    print("""
╔════════════════════════════════════════╗
║        VOICE2TEXT - TRANSCRIBER        ║
║                                        ║
║  🎙️  Press Ctrl+Win to record         ║
║  ✏️  Auto-transcribe & paste          ║
║  💾 Everything saved locally          ║
╚════════════════════════════════════════╝
    """)
    
    # Setup
    setup_directories()
    setup_database()
    
    # Start GUI thread for popup windows
    gui_thread = threading.Thread(target=gui_thread_func, daemon=True)
    gui_thread.start()
    time.sleep(0.5)  # Give GUI thread time to initialize
    
    setup_hotkeys()
    
    print("✅ Application started!")
    print("💡 Tip: Check tray icon menu for more options")
    
    # Create and run tray icon
    icon = create_tray()
    icon.run()


if __name__ == '__main__':
    main()
