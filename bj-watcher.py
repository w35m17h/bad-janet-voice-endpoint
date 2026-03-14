#!/usr/bin/env python3

import subprocess
import socket
import os
import time
import glob
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = "/root/janet_incoming"
OPENCLAW_HOST = "localhost"
OPENCLAW_PORT = 9999
PI_HOST = "root@YOUR_PI_IP"
TTS_WAV = "/tmp/janet_response.wav"

# Clean up any leftover wav files on startup
for f in glob.glob(f"{WATCH_DIR}/*.wav"):
    os.remove(f)

class WavHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.wav'):
            return
        
        print(f"New wav detected: {event.src_path}")
        time.sleep(0.5)  # Let the file finish writing
        
        transcription = transcribe(event.src_path)
        if transcription:
            print(f"Heard: {transcription}")
            response = send_to_openclaw(transcription)
            if response:
                print(f"Bad Janet says: {response}")
                speak(response)
            os.remove(event.src_path)  # Clean up wav after processing

def transcribe(wavfile):
    print(f"Transcribing {wavfile}...")
    subprocess.run([
        "whisper", wavfile,
        "--model", "tiny",
        "--language", "English",
        "--output_format", "txt",
        "--output_dir", WATCH_DIR
    ], capture_output=True, text=True)
    
    txtfile = wavfile.replace('.wav', '.txt')
    if os.path.exists(txtfile):
        with open(txtfile, 'r') as f:
            text = f.read().strip()
        os.remove(txtfile)
        return text
    return None

def send_to_openclaw(text):
    print(f"Sending to OpenClaw: {text}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((OPENCLAW_HOST, OPENCLAW_PORT))
            s.sendall(text.encode('utf-8'))
            response = s.recv(4096)
            return response.decode('utf-8').strip()
    except Exception as e:
        print(f"Error sending to OpenClaw: {e}")
        return None

def speak(text):
    print(f"Speaking: {text}")
    # Generate wav with espeak
    subprocess.run([
        "espeak", text,
        "--stdout"
    ], stdout=open(TTS_WAV, 'wb'))
    
    # SCP to Pi and play
    subprocess.run(["scp", TTS_WAV, f"{PI_HOST}:/root/response.wav"])
    subprocess.run(["ssh", PI_HOST, "aplay -D plughw:1,0 /root/response.wav"])

if __name__ == "__main__":
    print(f"Watching {WATCH_DIR} for wav files...")
    event_handler = WavHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
