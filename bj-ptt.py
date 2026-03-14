#!/usr/bin/env python3

import subprocess
import os
import RPi.GPIO as GPIO
import time
import sys
sys.path.insert(0, '/root/mic_hat-master')
sys.path.insert(0, '/root/mic_hat-master/interfaces')
from interfaces.pixels import Pixels

WAVFILE = "/root/capture.wav"
WM_HOST = "root@YOUR_WM_IP"
WM_WAVFILE = "/root/janet_incoming/capture.wav"
BUTTON = 17

# Dim the LEDs way down
pixels = Pixels()
pixels.dev.global_brightness = 3  # 0-31, keeping it easy on the eyes

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON, GPIO.IN)

def record_ptt():
    print("Waiting for button press...")
    pixels.off()
    
    # Wait for button press
    while GPIO.input(BUTTON):
        time.sleep(0.01)
    
    print("Recording... (release button to stop)")
    pixels.wakeup()
    
    proc = subprocess.Popen([
        "arecord",
        "-D", "plughw:1,0",
        "-f", "S16_LE",
        "-r", "16000",
        WAVFILE
    ])
    
    # Wait for button release
    while not GPIO.input(BUTTON):
        time.sleep(0.01)
    
    proc.terminate()
    pixels.think()
    print("Done recording.")

def transcribe():
    print("Copying to Wintermute...")
    subprocess.run(["scp", WAVFILE, f"{WM_HOST}:{WM_WAVFILE}"])
    print("Waiting for response...")

if __name__ == "__main__":
    try:
        while True:
            record_ptt()
            transcribe()
    except KeyboardInterrupt:
        pixels.off()
        GPIO.cleanup()
        print("Bye!")
