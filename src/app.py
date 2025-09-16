import os
import queue
import sys
import tempfile
import threading
import time
import wave

import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw

# keyboard can require elevated privileges on Windows in some cases
import keyboard

# Whisper (OpenAI) - PyTorch implementation
import whisper

# Configuration
HOTKEY = 'ctrl+shift'
SAMPLE_RATE = 16000
CHANNELS = 1

# Global state
recording = False
audio_queue = queue.Queue()
frames = []

# Load whisper model (small by default for speed; change to 'base', 'small', 'medium', 'large' as needed)
MODEL_NAME = os.environ.get('WHISPER_MODEL', 'small')
print(f"Loading Whisper model: {MODEL_NAME} (this may take a while)")
model = whisper.load_model(MODEL_NAME)
print("Model loaded.")


def make_icon(text: str = "STT") -> Image.Image:
    # Create a simple square icon with text
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, size, size), fill=(30, 30, 30))
    d.text((8, 18), text, fill=(255, 255, 255))
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
    print("Starting recording...")
    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback)
    stream.start()
    record_thread = threading.Thread(target=record_thread_func, args=(stream,), daemon=True)
    record_thread.start()


def stop_recording_and_transcribe():
    global recording, stream, frames
    if not recording:
        return
    print("Stopping recording...")
    recording = False
    try:
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"Error stopping stream: {e}")

    # concatenate frames
    if not frames:
        print("No audio captured.")
        return

    audio_data = np.concatenate(frames, axis=0)
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

    # Transcribe (blocking) - run in a new thread to avoid blocking main
    t = threading.Thread(target=transcribe_and_paste, args=(path,), daemon=True)
    t.start()


def transcribe_and_paste(wav_path: str):
    try:
        result = model.transcribe(wav_path)
        text = result.get('text', '').strip()
        print(f"Transcription result: {text}")
        if text:
            # Save current clipboard
            try:
                previous_clip = pyperclip.paste()
            except Exception:
                previous_clip = None

            pyperclip.copy(text)
            # Small delay to ensure clipboard is set
            time.sleep(0.05)
            # Send Ctrl+V to paste
            keyboard.send('ctrl+v')
            time.sleep(0.05)
            # Restore previous clipboard
            if previous_clip is not None:
                pyperclip.copy(previous_clip)
    except Exception as e:
        print(f"Error during transcription: {e}")
    finally:
        try:
            os.remove(wav_path)
        except Exception:
            pass


def on_press(event):
    # Start recording when hotkey is pressed
    # Here we trigger on the hotkey combination being pressed as a whole
    # keyboard module will handle combination; we only need to start on event name
    # We use is_pressed to detect whether both keys are currently pressed
    try:
        if not recording:
            start_recording()
    except Exception as e:
        print(f"Error starting recording: {e}")


def on_release(event):
    # Stop recording when hotkey is released
    # We need to ensure both keys have been released; we'll stop when the combination is not pressed anymore
    try:
        # If neither ctrl nor shift is pressed, stop
        if recording and not (keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift')):
            stop_recording_and_transcribe()
    except Exception as e:
        print(f"Error stopping recording: {e}")


def setup_hotkeys():
    # We use low level hooks to detect press and release of the combination
    # Press: when the combination becomes active
    # Release: when the combination is no longer active

    # on press function: when any of the keys are pressed, check if combo active
    def _on_any_key(e):
        # if combo active and not recording -> start
        try:
            if keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift'):
                if not recording:
                    start_recording()
            else:
                # combo not active: if we were recording, stop
                if recording:
                    stop_recording_and_transcribe()
        except Exception as ex:
            print(f"Hotkey check error: {ex}")

    keyboard.hook(_on_any_key)


def create_tray():
    icon = pystray.Icon('stt', make_icon('STT'))

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

    icon.menu = pystray.Menu(pystray.MenuItem('Quit', on_quit))
    return icon


def main():
    # Setup hotkeys
    setup_hotkeys()
    icon = create_tray()

    # Run the tray icon (blocking). Hotkeys are handled in background threads/hooks
    icon.run()


if __name__ == '__main__':
    main()
