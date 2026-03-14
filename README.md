# Bad Janet Voice Endpoint

A DIY voice endpoint using a Raspberry Pi Zero W + KEYESTUDIO ReSpeaker 2-Mic HAT, 
Whisper STT, and an OpenClaw AI agent pipeline. No Home Assistant, no Wyoming 
protocol, no cloud STT required.

Inspired by Bad Janet from *The Good Place*. 😈

## Hardware

- Raspberry Pi Zero W
- KEYESTUDIO ReSpeaker 2-Mic Pi HAT (WM8960 codec)
- Small powered speaker (3.5mm jack or XH2.54-2P)
- AI server/workstation running OpenClaw (we use an i7-8700 machine)

## Architecture
```
[Pi Zero W]                          [Wintermute/WM Server]
bj-ptt.py                            bj-watcher.py
  - GPIO17 button (PTT)                - Watches for incoming wav files
  - arecord captures audio             - Whisper STT transcription
  - SCP wav to WM server               - Sends text to bj-listener.py
  - APA102 LED feedback              
                                     bj-listener.py
                                       - Listens on localhost:9999
                                       - Passes text to OpenClaw agent
                                       - Returns agent response
                                     
                                       espeak TTS → wav → SCP back to Pi
                                       Pi plays response via aplay
```

## Files

| File | Runs On | Purpose |
|------|---------|---------|
| `bj-ptt.py` | Pi Zero W | PTT button, audio capture, LED feedback |
| `bj-watcher.py` | WM Server | File watcher, Whisper STT, TTS, orchestration |
| `bj-listener.py` | WM Server | Socket listener, OpenClaw agent interface |

## Prerequisites

### Pi Zero W
```bash
# Enable I2C and SPI via raspi-config
raspi-config  # Interface Options -> I2C -> Enable, SPI -> Enable

# Install seeed-voicecard driver
# Download seeed-voicecard-6.1.zip (kernel 6.1.x)
unzip seeed-voicecard-6.1.zip
cd seeed-voicecard-6.1
./install.sh
reboot

# Verify
aplay -l    # Should show seeed-2mic-voicecard as card 1
arecord -l  # Same

# No additional Python deps needed - RPi.GPIO and spidev included with Bullseye Lite
```

### WM Server (Debian)
```bash
pip install openai-whisper watchdog --break-system-packages
apt install espeak
```

## SSH Key Setup

The Pi needs keyless SSH to WM, and WM needs keyless SSH back to the Pi:
```bash
# On Pi
ssh-keygen -t ed25519
ssh-copy-id root@YOUR_WM_IP

# On WM
ssh-keygen -t ed25519
# Manually copy WM public key to Pi's /root/.ssh/authorized_keys
# (Pi has password auth disabled)
```

## Configuration

Edit the following in each script:

**bj-ptt.py**
```python
WM_HOST = "root@YOUR_WM_IP"
WM_WAVFILE = "/root/janet_incoming/capture.wav"
```

**bj-watcher.py**
```python
PI_HOST = "root@YOUR_PI_IP"
OPENCLAW_PORT = 9999  # Match your OpenClaw setup
```

**bj-listener.py**
```python
OPENCLAW = '/path/to/openclaw'
```

## Usage

On WM, start the listener service and watcher:
```bash
systemctl start bj-listener
python3 /root/bj-watcher.py
```

On the Pi:
```bash
python3 /root/bj-ptt.py
```

Press the button on the HAT, speak your command, release. Bad Janet will respond. 😈

## LED States (APA102)

| State | Meaning |
|-------|---------|
| Wakeup | Button pressed, recording |
| Think | Processing |
| Off | Idle |

## Notes

- Whisper model: `tiny` for speed, `small` for better accuracy
- seeed-voicecard-6.1 matches kernel 6.1.x — use HinTak fork for newer kernels
- On Pi Zero W, ALSA card index is `plughw:1,0` (card 0 is HDMI)
- Two HATs in the package is normal 😄

## Future Plans

- Wake word detection (replace PTT)
- Better TTS (Piper)
- Multiple satellite support
- Custom 3D printed enclosure (gutted Amazon Echo shell 👀)
- LED sync with response states
