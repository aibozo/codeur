# WSL Audio Setup for Voice Agent

## Current Status
- ✅ WSLg with PulseAudio is installed and working
- ✅ RDPSource and RDPSink are available
- ✅ PyAudio can record (but getting low-level noise)
- ⚠️ Microphone input through RDP may need Windows configuration

## To Enable Microphone in WSL:

### 1. Windows Side Configuration
1. **Set Default Recording Device**:
   - Right-click speaker icon → Sound settings
   - Under "Input", select your headset as default device
   - Test microphone to ensure Windows is receiving audio

2. **Check Privacy Settings**:
   - Windows Settings → Privacy & Security → Microphone
   - Enable "Microphone access" 
   - Enable "Let desktop apps access your microphone"

3. **Remote Desktop Audio**:
   - The WSLg uses RDP (Remote Desktop Protocol) for audio
   - Your headset audio needs to be captured by Windows first

### 2. Test in WSL
```bash
# Check if audio is being received
pactl list sources short

# Monitor input levels
pavucontrol  # GUI tool if you have X11
# or
pactl subscribe  # Watch for audio events
```

### 3. Alternative Solutions

#### Option A: USB Passthrough (Best for USB Headsets)
```powershell
# On Windows (PowerShell as Admin)
winget install usbipd

# List USB devices
usbipd list

# Attach your headset (replace X-X with your device ID)
usbipd attach --wsl --busid X-X
```

#### Option B: Virtual Audio Cable
1. Install VB-Audio Virtual Cable on Windows
2. Route headset → Virtual Cable → WSL
3. More complex but reliable

#### Option C: Native Linux Audio (WSL2 only)
- Use PipeWire instead of PulseAudio
- Requires more setup but better latency

## Quick Test
```bash
# Test recording
arecord -f cd -d 5 test.wav
aplay test.wav

# Or with Python
python test_mic_recording.py
```

## For Voice Agent
The current implementation should work once Windows audio is configured correctly. The agent will automatically use the default audio input device detected by PyAudio.