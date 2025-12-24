#!/usr/bin/env python3
"""
Launch script for NASA Solar Image Downloader Web Interface
"""

import sys
import subprocess
from pathlib import Path

def install_requirements():
    """Install required packages."""
    try:
        print("📦 Installing required packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_gradio.txt'], check=True)
        print("✅ Packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def main():
    """Main launcher."""
    print("🌞 NASA Solar Image Downloader - Web Interface Launcher")
    print("=" * 60)
    
    # Check if gradio is installed
    try:
        import gradio
        print("✅ Gradio is available")
    except ImportError:
        print("⚠️  Gradio not found. Installing requirements...")
        if not install_requirements():
            print("❌ Failed to install requirements. Please install manually:")
            print("   pip install -r requirements_gradio.txt")
            return
    
    # Launch the application
    try:
        from gradio_app import main as gradio_main
        gradio_main()
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()