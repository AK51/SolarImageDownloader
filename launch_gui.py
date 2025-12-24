#!/usr/bin/env python3
"""
NASA Solar Image Downloader - GUI Launcher
Simple launcher script for the complete GUI application.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Launch the NASA GUI application."""
    print("🚀 Launching NASA Solar Image Downloader GUI...")
    
    # Check if required packages are installed
    required_packages = ['tkinter', 'PIL', 'cv2', 'requests', 'beautifulsoup4']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            elif package == 'PIL':
                from PIL import Image
            elif package == 'cv2':
                import cv2
            elif package == 'requests':
                import requests
            elif package == 'beautifulsoup4':
                import bs4
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("💡 Installing missing packages...")
        
        install_map = {
            'PIL': 'pillow',
            'cv2': 'opencv-python',
            'beautifulsoup4': 'beautifulsoup4'
        }
        
        for package in missing_packages:
            if package in install_map:
                package_name = install_map[package]
            else:
                package_name = package
            
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', package_name], 
                             check=True)
                print(f"✅ Installed {package_name}")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package_name}")
                return
    
    # Launch the GUI
    try:
        import nasa_gui
        print("✅ Starting GUI application...")
        nasa_gui.main()
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()