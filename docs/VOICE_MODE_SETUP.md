# Voice Mode Setup Guide

## Overview
The Voice Mode feature allows the Architect Agent to speak its responses using Text-to-Speech (TTS). This guide covers setup for different operating systems.

## Prerequisites

1. **Google API Key**: Required for TTS generation
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```
   Or add to `.env` file:
   ```
   GOOGLE_API_KEY=your-api-key-here
   ```

2. **Audio Playback Support**: Platform-specific requirements

## Platform-Specific Setup

### Linux

Install one of the following audio players:

```bash
# Option 1: ALSA (most common)
sudo apt-get install alsa-utils  # Ubuntu/Debian
sudo yum install alsa-utils      # RHEL/CentOS
sudo pacman -S alsa-utils        # Arch

# Option 2: PulseAudio
sudo apt-get install pulseaudio-utils  # Ubuntu/Debian
sudo yum install pulseaudio-utils      # RHEL/CentOS

# Option 3: FFmpeg (includes ffplay)
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg      # RHEL/CentOS
```

### macOS

Audio playback uses the built-in `afplay` command (pre-installed).

No additional setup required.

### Windows

Audio playback uses the built-in Windows sound APIs.

No additional setup required.

## Python Fallback Options

If system audio players are not available, install one of these Python packages:

```bash
# Option 1: pygame (recommended, cross-platform)
pip install pygame

# Option 2: pyaudio (requires system dependencies)
pip install pyaudio
```

## Testing Voice Mode

1. **Test TTS directly**:
   ```bash
   python test_tts_simple.py
   ```

2. **Test voice integration**:
   ```bash
   python test_voice_integration.py
   ```

## Troubleshooting

### "No audio player found"
- Linux: Install one of the audio players listed above
- Use Python fallback: `pip install pygame`

### "GOOGLE_API_KEY required"
- Set the environment variable: `export GOOGLE_API_KEY="your-key"`
- Or add to `.env` file: `GOOGLE_API_KEY=your-key`

### Audio files saved but not playing
- Check system volume is not muted
- Verify audio device is connected
- Try playing the saved `.wav` file manually

### Frontend not playing audio
- Check browser console for errors
- Ensure browser allows audio playback (not blocked by autoplay policy)
- Verify the audio URL is accessible

## Browser Compatibility

The frontend audio playback uses standard HTML5 Audio API, compatible with:
- Chrome 4+
- Firefox 3.5+
- Safari 4+
- Edge 12+

## Voice Quality Settings

Available voices for Gemini TTS:
- Kore (default)
- Aoede
- Aura
- Eos
- Fenrir
- Orbit
- Puck
- Glimmer
- Vega
- Eclipse

Modify in `TTSVoiceMode` initialization:
```python
tts = TTSVoiceMode(voice_name="Aoede")
```