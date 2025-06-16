#!/usr/bin/env python3
"""
Simplest possible beep test - no files needed.
"""

import sys
import platform


def beep():
    """Try various methods to make a beep sound."""
    system = platform.system()
    print(f"🔊 Trying to beep on {system}...")
    
    # Method 1: Terminal bell character
    print("Method 1: Terminal bell (\\a)")
    print("\a", end="", flush=True)
    print("✓ Sent bell character")
    
    # Method 2: System-specific commands
    if system == "Darwin":  # macOS
        print("\nMethod 2: macOS system sound")
        try:
            import subprocess
            subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], check=True)
            print("✓ Played system sound")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    elif system == "Linux":
        print("\nMethod 2: Linux beep command")
        try:
            import subprocess
            # Try beep command
            if subprocess.run(["which", "beep"], capture_output=True).returncode == 0:
                subprocess.run(["beep"], check=True)
                print("✓ Used beep command")
            else:
                # Try speaker-test
                print("Trying speaker-test (1 second)...")
                subprocess.run(["speaker-test", "-t", "sine", "-f", "1000", "-l", "1"], 
                             timeout=1, capture_output=True)
                print("✓ Used speaker-test")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    elif system == "Windows":
        print("\nMethod 2: Windows beep")
        try:
            import winsound
            winsound.Beep(1000, 500)  # 1000Hz for 500ms
            print("✓ Used winsound.Beep")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    # Method 3: Print to stderr (sometimes triggers beep)
    print("\nMethod 3: stderr bell")
    sys.stderr.write('\a')
    sys.stderr.flush()
    print("✓ Sent to stderr")
    
    print("\n" + "=" * 50)
    print("If you heard a beep, audio is working!")
    print("If not, you may need to:")
    print("- Enable terminal bell in your terminal settings")
    print("- Install audio packages (see test_beep.py for details)")
    print("- Check your system volume is not muted")


if __name__ == "__main__":
    beep()