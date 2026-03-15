#!/usr/bin/env python3

import threading
import paho.mqtt.client as mqtt
import subprocess
import os
import RPi.GPIO as GPIO
import time
import sys
sys.path.insert(0, '/opt/badjanet/mic_hat-master')
sys.path.insert(0, '/opt/badjanet/mic_hat-master/interfaces')
from interfaces.pixels import Pixels

WAVFILE = "/tmp/capture.wav"
WM_HOST = "root@wintermute.local"
WM_WAVFILE = "/opt/badjanet/incoming/capture.wav"
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
    
    print("Button pressed, starting arecord...")
    
    proc = subprocess.Popen([
        "arecord",
        "-D", "plughw:1,0",
        "-f", "S16_LE",
        "-r", "16000",
        WAVFILE
    ], stderr=subprocess.PIPE)
    
    # Wait for arecord to confirm it's actually recording
    for line in proc.stderr:
        if b'Recording' in line:
            print("Recording started!")
            pixels.wakeup()  # NOW light up
            break
    
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

MQTT_BROKER = "172.16.100.11"
MQTT_TOPIC = "sat1/battery"

def battery_monitor():
    client = mqtt.Client()
    client.username_pw_set("mosquitto", "socius")
    client.connect(MQTT_BROKER, 1883, 60)
    while True:
        result = subprocess.run(
            ['i2cget', '-y', '1', '0x57', '0x2a'],
            capture_output=True, text=True
        )
        battery = int(result.stdout.strip(), 16)
        client.publish(MQTT_TOPIC, battery)
        print(f"Battery: {battery}%")
        if battery <= 10:
            print("Battery critical! Shutting down...")
            subprocess.run(['shutdown', '-h', 'now'])
        time.sleep(60)

MQTT_BATTERY_ANNOUNCE = "sat1/battery/announce"

def button_monitor():
    while True:
        result = subprocess.run(
            ['i2cget', '-y', '1', '0x57', '0x08'],
            capture_output=True, text=True
        )
        state = result.stdout.strip()

        if state == '0x01':
            # Single tap - announce battery level
            print("Single tap: announcing battery...")
            batt_result = subprocess.run(
                ['i2cget', '-y', '1', '0x57', '0x2a'],
                capture_output=True, text=True
            )
            battery = int(batt_result.stdout.strip(), 16)
            client = mqtt.Client()
            client.username_pw_set("mosquitto", "socius")
            client.connect(MQTT_BROKER, 1883, 60)
            client.publish(MQTT_BATTERY_ANNOUNCE, battery)
            client.disconnect()
            # Re-arm
            subprocess.run(['i2cset', '-y', '1', '0x57', '0x08', '0x03'])

        elif state == '0x02':
            # Double tap - clean shutdown
            print("Double tap: shutting down cleanly...")
            subprocess.run(['i2cset', '-y', '1', '0x57', '0x08', '0x03'])
            subprocess.run(['shutdown', '-h', 'now'])

        time.sleep(1)


if __name__ == "__main__":
    monitor_thread = threading.Thread(target=battery_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    button_thread = threading.Thread(target=button_monitor)
    button_thread.daemon = True
    button_thread.start()

    try:
        while True:
            record_ptt()
            transcribe()
    except KeyboardInterrupt:
        pixels.off()
        GPIO.cleanup()
        print("Bye!")
