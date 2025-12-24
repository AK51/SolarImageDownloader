#!/usr/bin/env python3
"""
NASA Solar Image Viewer
Simple image viewer with video-like playback controls.
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.storage.storage_organizer import StorageOrganizer

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from PIL import Image, ImageTk
    HAS_GUI = True
except ImportError:
    HAS_GUI = False


class ImageViewer:
    """Simple image viewer with video-like controls."""
    
    def __init__(self, storage: StorageOrganizer):
        """Initialize the image viewer."""
        self.storage = storage
        self.images = []
        self.current_index = 0
        self.is_playing = False
        self.fps = 2  # Default 2 FPS
        self.play_thread = None
        
        if not HAS_GUI:
            raise ImportError("GUI libraries not available. Install with: pip install pillow")
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("NASA Solar Image Viewer")
        self.root.geometry("800x900")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="🌞 NASA Solar Image Viewer", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Date selection frame
        date_frame = ttk.LabelFrame(main_frame, text="Select Date", padding=10)
        date_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(date_frame, textvariable=self.date_var, 
                                      state="readonly", width=30)
        self.date_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        load_btn = ttk.Button(date_frame, text="Load Images", command=self.load_images)
        load_btn.pack(side=tk.LEFT)
        
        # Image display
        self.image_frame = ttk.LabelFrame(main_frame, text="Solar Image", padding=10)
        self.image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.image_label = ttk.Label(self.image_frame, text="No image loaded", 
                                    background="black", foreground="white")
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # Info frame
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_label = ttk.Label(info_frame, text="Ready", font=("Arial", 10))
        self.info_label.pack()
        
        # Controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Playback Controls", padding=10)
        controls_frame.pack(fill=tk.X)
        
        # Playback buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.prev_btn = ttk.Button(btn_frame, text="⏮ Previous", command=self.prev_image)
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.play_btn = ttk.Button(btn_frame, text="▶ Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.next_btn = ttk.Button(btn_frame, text="Next ⏭", command=self.next_image)
        self.next_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self.stop_play)
        self.stop_btn.pack(side=tk.LEFT)
        
        # Speed control
        speed_frame = ttk.Frame(controls_frame)
        speed_frame.pack(fill=tk.X)
        
        ttk.Label(speed_frame, text="Speed (FPS):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.speed_var = tk.DoubleVar(value=2.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.5, to=10.0, 
                               variable=self.speed_var, orient=tk.HORIZONTAL,
                               command=self.update_speed)
        speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.speed_label = ttk.Label(speed_frame, text="2.0 FPS")
        self.speed_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(controls_frame, variable=self.progress_var,
                                           maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        
        # Load available dates
        self.load_available_dates()
    
    def load_available_dates(self):
        """Load available dates with images."""
        dates = []
        data_dir = self.storage.base_data_dir
        
        if data_dir.exists():
            for year_dir in data_dir.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir() or not month_dir.name.isdigit():
                        continue
                    
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir() or not day_dir.name.isdigit():
                            continue
                        
                        images = list(day_dir.glob("*_4096_0211.jpg"))
                        if images:
                            try:
                                date = datetime(int(year_dir.name), int(month_dir.name), int(day_dir.name))
                                date_str = f"{date.strftime('%Y-%m-%d')} ({len(images)} images)"
                                dates.append((date, date_str))
                            except ValueError:
                                continue
        
        if dates:
            dates.sort()
            date_strings = [date_str for _, date_str in dates]
            self.date_combo['values'] = date_strings
            self.date_combo.current(0)  # Select first date
            self.available_dates = {date_str: date for date, date_str in dates}
        else:
            messagebox.showwarning("No Images", "No downloaded images found!\n\nRun 'python download_real_images.py' first.")
    
    def load_images(self):
        """Load images for the selected date."""
        selected = self.date_var.get()
        if not selected or selected not in self.available_dates:
            messagebox.showerror("Error", "Please select a valid date")
            return
        
        date = self.available_dates[selected]
        image_files = self.storage.list_local_images(date)
        
        if not image_files:
            messagebox.showerror("Error", f"No images found for {date.strftime('%Y-%m-%d')}")
            return
        
        # Load image paths
        self.images = []
        date_path = self.storage.get_date_path(date)
        
        for filename in sorted(image_files):
            image_path = date_path / filename
            self.images.append((image_path, filename))
        
        self.current_index = 0
        self.update_display()
        
        self.info_label.config(text=f"Loaded {len(self.images)} images for {date.strftime('%Y-%m-%d')}")
    
    def update_display(self):
        """Update the image display."""
        if not self.images:
            return
        
        image_path, filename = self.images[self.current_index]
        
        try:
            # Load and resize image
            pil_image = Image.open(image_path)
            
            # Calculate size to fit in display area (max 600x600)
            display_size = (600, 600)
            pil_image.thumbnail(display_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update display
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Keep a reference
            
            # Update info
            progress = (self.current_index + 1) / len(self.images) * 100
            self.progress_var.set(progress)
            
            # Extract timestamp from filename
            timestamp = filename.split('_')[1] if '_' in filename else "Unknown"
            if len(timestamp) == 6:
                formatted_time = f"{timestamp[:2]}:{timestamp[2:4]}:{timestamp[4:6]}"
            else:
                formatted_time = timestamp
            
            info_text = f"Image {self.current_index + 1}/{len(self.images)} - Time: {formatted_time}"
            self.image_frame.config(text=info_text)
            
        except Exception as e:
            self.image_label.config(text=f"Error loading image: {e}")
    
    def prev_image(self):
        """Go to previous image."""
        if self.images and self.current_index > 0:
            self.current_index -= 1
            self.update_display()
    
    def next_image(self):
        """Go to next image."""
        if self.images and self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.update_display()
    
    def toggle_play(self):
        """Toggle play/pause."""
        if self.is_playing:
            self.pause_play()
        else:
            self.start_play()
    
    def start_play(self):
        """Start playing images."""
        if not self.images:
            messagebox.showwarning("No Images", "Please load images first")
            return
        
        self.is_playing = True
        self.play_btn.config(text="⏸ Pause")
        
        # Start play thread
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
    
    def pause_play(self):
        """Pause playing."""
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
    
    def stop_play(self):
        """Stop playing and reset to first image."""
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
        self.current_index = 0
        self.update_display()
    
    def _play_loop(self):
        """Play loop running in background thread."""
        while self.is_playing and self.images:
            if self.current_index >= len(self.images) - 1:
                # Reached end, loop back to start
                self.current_index = 0
            else:
                self.current_index += 1
            
            # Update display in main thread
            self.root.after(0, self.update_display)
            
            # Wait based on FPS
            delay = 1.0 / self.fps
            time.sleep(delay)
    
    def update_speed(self, value):
        """Update playback speed."""
        self.fps = float(value)
        self.speed_label.config(text=f"{self.fps:.1f} FPS")
    
    def run(self):
        """Run the viewer."""
        self.root.mainloop()


def main():
    """Main viewer application."""
    if not HAS_GUI:
        print("❌ GUI libraries not available!")
        print("💡 Install with: pip install pillow")
        print("💡 Or use the video creator: python create_video.py")
        return
    
    try:
        storage = StorageOrganizer("data")
        viewer = ImageViewer(storage)
        viewer.run()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()