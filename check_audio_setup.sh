#!/bin/bash
# Check audio setup for WSL

echo "🎧 WSL AUDIO CONFIGURATION CHECK"
echo "================================"

echo -e "\n1. PulseAudio Server Info:"
pactl info | grep -E "Server String|Default Source|Default Sink"

echo -e "\n2. Audio Sources (Microphones):"
pactl list short sources

echo -e "\n3. Setting RDPSource as default:"
pactl set-default-source RDPSource

echo -e "\n4. Testing microphone input levels:"
echo "Speak into your microphone for 5 seconds..."
timeout 5 parecord --channels=1 --device=RDPSource | sox -t raw -r 44100 -b 16 -c 1 -e signed - -n stat 2>&1 | grep -E "Maximum amplitude|RMS"

echo -e "\n5. Windows side configuration needed:"
echo "   - Make sure your headset is the default recording device in Windows"
echo "   - Check Windows Sound Settings > Recording devices"
echo "   - Ensure 'Allow apps to access your microphone' is enabled"
echo "   - Try: Windows Settings > Privacy > Microphone"

echo -e "\n6. Alternative test - direct recording:"
echo "Recording 3 seconds from RDPSource..."
parecord --channels=1 --device=RDPSource --format=s16le --rate=44100 test_rdp.wav -d 3

echo -e "\n✅ Check complete! File saved as test_rdp.wav"