#!/usr/bin/env python3
"""
WSL Audio Configuration Test Suite
"""

import subprocess
import os
import sys

def run_command(cmd, description):
    """Run a command and display results."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"Command: {cmd}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print("Output:")
            print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Failed: {e}")
        return False

def test_pulseaudio():
    """Test PulseAudio configuration."""
    print("\n" + "="*60)
    print("🎧 PULSEAUDIO TESTS")
    print("="*60)
    
    # Check if PulseAudio is installed
    if not run_command("which pulseaudio", "Check if PulseAudio is installed"):
        print("\n❌ PulseAudio not installed!")
        print("Install with: sudo apt update && sudo apt install pulseaudio")
        return False
    
    # Check PulseAudio status
    run_command("pulseaudio --check", "Check PulseAudio daemon status")
    run_command("ps aux | grep pulseaudio", "Check running PulseAudio processes")
    
    # Try to start PulseAudio if not running
    run_command("pulseaudio --start", "Start PulseAudio daemon")
    
    # List audio devices
    run_command("pactl info", "Get PulseAudio server info")
    run_command("pactl list short sources", "List audio input sources")
    run_command("pactl list short sinks", "List audio output sinks")
    
    return True

def test_alsa():
    """Test ALSA configuration."""
    print("\n" + "="*60)
    print("🔊 ALSA TESTS")
    print("="*60)
    
    # Check ALSA devices
    run_command("aplay -l", "List ALSA playback devices")
    run_command("arecord -l", "List ALSA recording devices")
    
    # Check ALSA configuration
    run_command("cat /proc/asound/cards", "Show ALSA sound cards")
    run_command("cat /proc/asound/devices", "Show ALSA devices")
    
    return True

def test_wsl_audio_setup():
    """Test WSL audio bridge setup."""
    print("\n" + "="*60)
    print("🌉 WSL AUDIO BRIDGE SETUP")
    print("="*60)
    
    # Check WSL version
    run_command("wsl.exe --version 2>/dev/null || echo 'WSL version command not available'", "Check WSL version")
    
    # Check if running WSL2
    run_command("uname -r", "Check kernel version")
    
    # Check for WSLg (GUI/Audio support)
    if os.path.exists("/mnt/wslg"):
        print("✅ WSLg detected (GUI/Audio support available)")
        run_command("ls -la /mnt/wslg/", "List WSLg mount contents")
    else:
        print("❌ WSLg not detected")
    
    # Check environment variables
    print("\n🔧 Audio-related environment variables:")
    for var in ["PULSE_SERVER", "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"]:
        value = os.environ.get(var, "Not set")
        print(f"  {var}: {value}")
    
    return True

def setup_pulseaudio_tcp():
    """Setup PulseAudio TCP connection to Windows."""
    print("\n" + "="*60)
    print("🔧 SETTING UP PULSEAUDIO TCP CONNECTION")
    print("="*60)
    
    print("""
To enable audio from WSL to Windows, you need to:

1. On Windows side:
   - Install PulseAudio for Windows: https://www.freedesktop.org/wiki/Software/PulseAudio/Ports/Windows/Support/
   - Or use: https://github.com/pgaskin/pulseaudio-win32
   - Configure it to accept network connections
   
2. On WSL side, add to ~/.bashrc or ~/.zshrc:
   export PULSE_SERVER=tcp:$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
   
3. Or for WSL2 with WSLg (newer versions):
   export PULSE_SERVER=/mnt/wslg/PulseServer
""")
    
    # Try to detect Windows host IP
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if "nameserver" in line:
                    ip = line.split()[1]
                    print(f"\n📍 Detected Windows host IP: {ip}")
                    print(f"   Test connection: export PULSE_SERVER=tcp:{ip}")
                    break
    except:
        pass

def test_pyaudio():
    """Test PyAudio configuration."""
    print("\n" + "="*60)
    print("🐍 PYAUDIO TESTS")
    print("="*60)
    
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        
        print(f"PyAudio version: {pyaudio.get_portaudio_version_text()}")
        print(f"Number of devices: {p.get_device_count()}")
        
        print("\n📥 INPUT DEVICES:")
        input_found = False
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_found = True
                print(f"  [{i}] {info['name']}")
                print(f"      Channels: {info['maxInputChannels']}")
                print(f"      Sample Rate: {info['defaultSampleRate']}")
        
        if not input_found:
            print("  ❌ No input devices found!")
        
        print("\n📤 OUTPUT DEVICES:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                print(f"  [{i}] {info['name']}")
                print(f"      Channels: {info['maxOutputChannels']}")
                print(f"      Sample Rate: {info['defaultSampleRate']}")
        
        # Try to get default devices
        try:
            default_input = p.get_default_input_device_info()
            print(f"\n✅ Default input device: {default_input['name']}")
        except:
            print("\n❌ No default input device!")
        
        try:
            default_output = p.get_default_output_device_info()
            print(f"✅ Default output device: {default_output['name']}")
        except:
            print("❌ No default output device!")
        
        p.terminate()
        
    except ImportError:
        print("❌ PyAudio not installed!")
    except Exception as e:
        print(f"❌ PyAudio error: {e}")

def suggest_fixes():
    """Suggest fixes based on test results."""
    print("\n" + "="*60)
    print("💡 SUGGESTED FIXES")
    print("="*60)
    
    print("""
Common solutions for WSL audio:

1. **For WSL2 with WSLg (Windows 11):**
   - Audio should work automatically
   - Check: ls /mnt/wslg/PulseServer
   - Set: export PULSE_SERVER=/mnt/wslg/PulseServer

2. **For older WSL2 (Windows 10):**
   - Install PulseAudio on Windows
   - Set: export PULSE_SERVER=tcp:$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')

3. **Install required packages:**
   sudo apt update
   sudo apt install pulseaudio pulseaudio-utils alsa-base alsa-utils

4. **Start PulseAudio:**
   pulseaudio --start --log-target=syslog

5. **Test microphone:**
   # Record 5 seconds
   arecord -d 5 -f cd test.wav
   # Play back
   aplay test.wav

6. **For USB headsets:**
   - Enable USB passthrough in WSL2
   - Check: lsusb
   - May need usbipd-win on Windows side
""")

def main():
    """Run all audio tests."""
    print("🎤 WSL AUDIO CONFIGURATION TESTER")
    print("=" * 60)
    
    # Run tests
    test_pulseaudio()
    test_alsa()
    test_wsl_audio_setup()
    test_pyaudio()
    suggest_fixes()
    
    print("\n" + "="*60)
    print("✅ Tests complete! Check output above for issues.")

if __name__ == "__main__":
    main()