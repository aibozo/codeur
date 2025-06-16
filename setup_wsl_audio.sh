#!/bin/bash
# WSL Audio Setup Script

echo "🔊 WSL Audio Setup and Diagnostics"
echo "=================================="

# Check WSL version
echo -e "\n1. Checking WSL version:"
wsl.exe --version 2>/dev/null || echo "WSL version command not available"

# Check if WSLg is available
echo -e "\n2. Checking WSLg:"
if [ -d "/mnt/wslg" ]; then
    echo "✅ WSLg is available"
    ls -la /mnt/wslg/
else
    echo "❌ WSLg not found"
fi

# Check PulseAudio
echo -e "\n3. Checking PulseAudio:"
if command -v pulseaudio &> /dev/null; then
    echo "✅ PulseAudio is installed"
    pulseaudio --version
    
    # Check if daemon is running
    if pgrep -x "pulseaudio" > /dev/null; then
        echo "✅ PulseAudio daemon is running"
    else
        echo "⚠️  PulseAudio daemon is not running"
        echo "Starting PulseAudio..."
        pulseaudio --start --log-target=syslog 2>/dev/null || echo "Failed to start"
    fi
else
    echo "❌ PulseAudio not installed"
    echo "Install with: sudo apt-get install pulseaudio"
fi

# Check ALSA
echo -e "\n4. Checking ALSA:"
if command -v aplay &> /dev/null; then
    echo "✅ ALSA is installed"
    # List audio devices
    echo "Audio devices:"
    aplay -l 2>/dev/null || echo "No ALSA devices found"
else
    echo "❌ ALSA not installed"
    echo "Install with: sudo apt-get install alsa-utils"
fi

# Check audio environment variables
echo -e "\n5. Checking audio environment:"
echo "PULSE_SERVER: ${PULSE_SERVER:-not set}"
echo "DISPLAY: ${DISPLAY:-not set}"
echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-not set}"

# Check Windows audio service
echo -e "\n6. Checking Windows audio redirection:"
if [ -e "/mnt/wslg/PulseAudioRDPSource" ]; then
    echo "✅ PulseAudioRDPSource exists"
else
    echo "❌ PulseAudioRDPSource not found"
fi

if [ -e "/mnt/wslg/PulseAudioRDPSink" ]; then
    echo "✅ PulseAudioRDPSink exists"
else
    echo "❌ PulseAudioRDPSink not found"
fi

# Test PulseAudio connection
echo -e "\n7. Testing PulseAudio connection:"
if command -v pactl &> /dev/null; then
    echo "PulseAudio info:"
    pactl info 2>/dev/null | grep -E "Server Name|Default Source|Default Sink" || echo "Cannot get PA info"
    
    echo -e "\nAudio sources:"
    pactl list short sources 2>/dev/null || echo "No sources found"
    
    echo -e "\nAudio sinks:"
    pactl list short sinks 2>/dev/null || echo "No sinks found"
else
    echo "❌ pactl not available"
fi

# Suggest fixes
echo -e "\n8. Suggested fixes:"
echo "-------------------"

# Check if we need to set PULSE_SERVER
if [ -z "$PULSE_SERVER" ] && [ -e "/mnt/wslg/PulseServer" ]; then
    echo "📌 Add to ~/.bashrc:"
    echo "export PULSE_SERVER=/mnt/wslg/PulseServer"
fi

# Check if audio group exists
if getent group audio > /dev/null; then
    if ! groups | grep -q audio; then
        echo "📌 Add user to audio group:"
        echo "sudo usermod -a -G audio $USER"
    fi
else
    echo "📌 Create audio group:"
    echo "sudo groupadd audio"
    echo "sudo usermod -a -G audio $USER"
fi

# Final recommendations
echo -e "\n9. Quick setup commands:"
echo "------------------------"
echo "# Install required packages"
echo "sudo apt-get update"
echo "sudo apt-get install -y pulseaudio pulseaudio-utils alsa-utils"
echo ""
echo "# Set environment (add to ~/.bashrc)"
echo "export PULSE_SERVER=/mnt/wslg/PulseServer"
echo ""
echo "# Restart WSL after making changes"
echo "wsl.exe --shutdown"
echo ""
echo "# Test audio"
echo "speaker-test -t wav -c 2"