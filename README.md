# Bad Janet Voice Endpoint

A DIY voice endpoint using a Raspberry Pi Zero W + KEYESTUDIO ReSpeaker 2-Mic HAT, 
Whisper STT, and an OpenClaw AI agent pipeline. No Home Assistant, no Wyoming 
protocol, no cloud STT required.

Inspired by Bad Janet from *The Good Place*. 😈

## Hardware

- Raspberry Pi Zero W
- KEYESTUDIO ReSpeaker 2-Mic Pi HAT (WM8960 codec, onboard APA102 LEDs, GPIO17 button)
- PiSugar3 battery module (I2C 0x57, 1200mAh, onboard RTC, custom button)
- Small powered speaker (3.5mm jack or XH2.54-2P)
- AI server/workstation running OpenClaw (we use an i7-8700 machine)

## Architecture
```
[Pi Zero W / sat1]                   [Wintermute/WM Server]
bj-ptt.py                            bj-watcher.py
  - GPIO17 button (PTT)                - Watches for incoming wav files
  - arecord captures audio             - Whisper STT transcription
  - SCP wav to WM server               - Sends text to bj-listener.py
  - APA102 LED feedback              
  - Battery monitor (MQTT)           bj-listener.py
  - Button monitor (PiSugar3)          - Listens on localhost:9999
    - Single tap → battery announce    - Passes text to OpenClaw agent
    - Double tap → clean shutdown      - Returns agent response
                                     
                                       espeak TTS → wav → SCP back to Pi
                                       Pi plays response via aplay

MQTT Topics (broker: DietPi server)
  sat1/battery         - Battery % published every 60s
  sat1/battery/announce - Battery % published on single tap
```

## Files

| File | Runs On | Purpose |
|------|---------|---------|
| `bj-ptt.py` | Pi Zero W | PTT button, audio capture, LED feedback, battery monitor, button monitor |
| `bj-watcher.py` | WM Server | File watcher, Whisper STT, TTS, orchestration |
| `bj-listener.py` | WM Server | Socket listener, OpenClaw agent interface |
| `bj-ptt.service` | Pi Zero W | systemd service for bj-ptt.py |

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

# Python deps
pip install paho-mqtt --break-system-packages
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
```

## systemd Service (Pi Zero W)

Copy `bj-ptt.service` to `/etc/systemd/system/` then:
```bash
systemctl daemon-reload
systemctl enable bj-ptt
systemctl start bj-ptt
```

The service uses a ping loop to wait for network connectivity before starting,
which is necessary on Pi Zero W where WiFi association is slow on cold boot.

## PiSugar3 I2C Button Control

The PiSugar3 exposes a custom button via I2C register `0x08`:

| Value | Event |
|-------|-------|
| `0x01` | Single tap |
| `0x02` | Double tap |
| `0x03` | Idle / cleared |

`bj-ptt.py` polls this register every second:
- **Single tap** → reads battery %, publishes to `sat1/battery/announce`
- **Double tap** → clean `shutdown -h now`
- After handling, writes `0x03` to re-arm

Battery % is read from register `0x2a`. Clear the button state by writing `0x03` to `0x08`:
```bash
i2cset -y 1 0x57 0x08 0x03
```

## Configuration

Edit the following in each script:

**bj-ptt.py**
```python
WM_HOST = "root@YOUR_WM_IP"
WM_WAVFILE = "/opt/badjanet/incoming/capture.wav"
MQTT_BROKER = "YOUR_MQTT_BROKER_IP"
```

**bj-watcher.py**
```python
PI_HOST = "root@YOUR_PI_IP"
OPENCLAW_PORT = 9999
```

**bj-listener.py**
```python
OPENCLAW = '/path/to/openclaw'
```

## Usage

On WM, start the listener and watcher:
```bash
systemctl start bj-listener
python3 /opt/badjanet/bj-watcher.py
```

On the Pi (or let systemd handle it):
```bash
systemctl start bj-ptt
```

Press the PTT button on the HAT, speak your command, release. Bad Janet will respond. 😈

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
- PiSugar3 ARMv6 incompatibility: pisugar-server doesn't support Pi Zero W — use direct I2C instead
- Two HATs in the package is normal 😄

## Important Resources

### Hardware Documentation
- [ReSpeaker 2-Mics Pi HAT (Seeed Wiki)](https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/) — schematic, pinout, general info
- [KEYESTUDIO ReSpeaker HAT Documentation](https://docs.keyestudio.com/projects/KS0314/en/latest/docs/KS0314.html) — includes driver download links
- [PiSugar3 I2C Datasheet](https://github.com/PiSugar/PiSugar/wiki/PiSugar-3-I2C-Datasheet) — register map, button control, power functions
- [PiSugar3 Series Wiki](https://github.com/PiSugar/PiSugar/wiki/PiSugar-3-Series) — general hardware info
- [PiSugar Case STLs (pihat-cap)](https://github.com/PiSugar/pisugar-case-pihat-cap) — 3D printable cases including ReSpeaker 2-mic variant

### Software / Drivers
- [Raspbian Bullseye Lite (armhf, 2023-05-03)](https://downloads.raspberrypi.com/raspios_lite_armhf/images/raspios_lite_armhf-2023-05-03/) — OS image used for sat1
- [Keyestudio Dropbox Package](https://www.dropbox.com/scl/fo/4x60kwe9gpr3no0h6s2xl/AP9QcnN3ApKXkGh9CJPLDzU?rlkey=1sjn1xxr114zviozu0pguwpnd&e=3&dl=0) — contains mic_hat-master library, seeed-voicecard-6.1 driver, and Bullseye image ⚠️ unofficial but only known source for mic_hat-master


## Future Plans

- Wake word detection (replace PTT)
- Better TTS (Piper)
- Multiple satellite support (sat2, sat3...)
- LCD display (GMG12864-06D ST7565R SPI)
- Pi Camera integration — snapshot → Bad Janet
- Music streaming from Samba share
- Node-RED flow for battery alerts via Prowl
- sat1/state MQTT topic for online/offline tracking
- Custom 3D printed enclosure (PiSugar3 case STLs + desk unit with stereo speakers)
