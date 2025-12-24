#!/usr/bin/env python3
"""
Test script to verify FFmpeg detection and provide installation guidance.
"""

import subprocess
import sys
import platform
from pathlib import Path

def check_ffmpeg_detailed():
    """Check FFmpeg with detailed information."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5, text=True)
        if result.returncode == 0:
            # Extract version information
            output_lines = result.stdout.split('\n')
            version_line = output_lines[0] if output_lines else "Unknown version"
            return "✅ Available", version_line
        else:
            return "❌ Not found", "FFmpeg command failed"
    except FileNotFoundError:
        return "❌ Not found", "FFmpeg is not installed or not in system PATH"
    except subprocess.TimeoutExpired:
        return "❌ Timeout", "FFmpeg command timed out"
    except OSError as e:
        return "❌ Error", f"System error: {str(e)}"
    except Exception as e:
        return "❌ Error", f"Unexpected error: {str(e)}"

def check_alternative_video_tools():
    """Check for alternative video creation tools."""
    alternatives = []
    
    # Check OpenCV
    try:
        import cv2
        alternatives.append(f"✅ OpenCV v{cv2.__version__} (fallback video creation)")
    except ImportError:
        alternatives.append("❌ OpenCV not available")
    
    # Check if we can create videos without FFmpeg
    try:
        import cv2
        import numpy as np
        # Test basic video writer capability
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        alternatives.append("✅ OpenCV MP4 codec support available")
    except:
        alternatives.append("❌ OpenCV MP4 codec support not available")
    
    return alternatives

def provide_installation_guidance():
    """Provide platform-specific installation guidance."""
    system = platform.system().lower()
    
    if system == "windows":
        return """
🪟 Windows Installation Options:

1. Manual Installation:
   • Download from: https://ffmpeg.org/download.html
   • Extract to C:\\ffmpeg
   • Add C:\\ffmpeg\\bin to system PATH
   • Restart computer

2. Package Managers:
   • Chocolatey: choco install ffmpeg
   • Scoop: scoop install ffmpeg
   • Winget: winget install ffmpeg

3. Portable Version:
   • Download portable build
   • Place ffmpeg.exe in project folder
"""
    
    elif system == "darwin":  # macOS
        return """
🍎 macOS Installation Options:

1. Homebrew (Recommended):
   • brew install ffmpeg

2. MacPorts:
   • sudo port install ffmpeg

3. Manual Installation:
   • Download from: https://ffmpeg.org/download.html
   • Follow installation instructions
"""
    
    elif system == "linux":
        return """
🐧 Linux Installation Options:

1. Ubuntu/Debian:
   • sudo apt update
   • sudo apt install ffmpeg

2. CentOS/RHEL/Fedora:
   • sudo dnf install ffmpeg
   • (or: sudo yum install ffmpeg)

3. Arch Linux:
   • sudo pacman -S ffmpeg

4. Snap:
   • sudo snap install ffmpeg
"""
    
    else:
        return """
❓ Unknown System:
Please visit https://ffmpeg.org/download.html for installation instructions.
"""

def main():
    """Main test function."""
    print("🔍 FFmpeg Detection and Installation Guide")
    print("=" * 60)
    
    # Check FFmpeg
    status, details = check_ffmpeg_detailed()
    print(f"FFmpeg Status: {status}")
    print(f"Details: {details}")
    print()
    
    # Check alternatives
    print("Alternative Video Tools:")
    alternatives = check_alternative_video_tools()
    for alt in alternatives:
        print(f"  {alt}")
    print()
    
    # System information
    print("System Information:")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  Architecture: {platform.machine()}")
    print()
    
    # Installation guidance if needed
    if "❌" in status:
        print("📥 Installation Guidance:")
        print(provide_installation_guidance())
        
        print("💡 Why FFmpeg is Recommended:")
        print("  • Higher quality video output")
        print("  • Better compression efficiency")
        print("  • More codec options")
        print("  • Faster processing")
        print("  • Professional video features")
        print()
        
        print("🔄 Fallback Options:")
        print("  • OpenCV will be used as fallback")
        print("  • Video creation will still work")
        print("  • Quality may be lower")
        print("  • Processing may be slower")
    
    else:
        print("✅ FFmpeg is properly installed and working!")
    
    print("=" * 60)

if __name__ == "__main__":
    main()