#!/usr/bin/env python3
"""
NASA Solar Image Downloader - Complete GUI Application
Combines downloading, viewing, video creation, and MP4 playback.
"""

import sys
import os
import threading
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    from PIL import Image, ImageTk
    import cv2
    HAS_GUI = True
except ImportError as e:
    print(f"❌ GUI libraries not available: {e}")
    print("💡 Install with: pip install pillow opencv-python")
    HAS_GUI = False
    sys.exit(1)

# Try to import Plotly for enhanced plotting
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    import webbrowser
    import tempfile
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("⚠️  Plotly not available. Install with: pip install plotly")

# Try to import Seaborn for statistical plotting
try:
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    print("⚠️  Seaborn not available. Install with: pip install seaborn pandas")

from src.downloader.directory_scraper import DirectoryScraper
from src.storage.storage_organizer import StorageOrganizer
from src.downloader.image_fetcher import ImageFetcher, DownloadManager


class NASADownloaderGUI:
    """Complete NASA Solar Image Downloader GUI."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("🌞 NASA Solar Image Downloader")
        self.root.geometry("1200x800")
        
        # Load and set background image
        self.setup_background_image()
        
        # Configure ttk styles for modern appearance with transparency
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles with semi-transparent backgrounds
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#ecf0f1', background='#2c3e50')
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('TNotebook', background='rgba(236, 240, 241, 0.95)', borderwidth=0)
        style.configure('TNotebook.Tab', padding=[20, 10], font=('Arial', 10, 'bold'))
        style.configure('TButton', font=('Arial', 9, 'bold'), padding=(10, 5))
        
        # Maximize the window
        self.root.state('zoomed')  # Windows
        try:
            self.root.attributes('-zoomed', True)  # Linux
        except:
            pass
        
        # Image filter settings (initialize before components)
        self.resolution_var = tk.StringVar(value="1024")
        self.solar_filter_var = tk.StringVar(value="0211")
        
        # Initialize filter data and buttons dictionary
        self.filter_data = {
            "0193": {"name": "193 Å", "desc": "Coronal loops", "color": "#ff6b6b"},
            "0304": {"name": "304 Å", "desc": "Chromosphere", "color": "#4ecdc4"},
            "0171": {"name": "171 Å", "desc": "Quiet corona", "color": "#45b7d1"},
            "0211": {"name": "211 Å", "desc": "Active regions", "color": "#f9ca24"},
            "0131": {"name": "131 Å", "desc": "Flaring regions", "color": "#f0932b"},
            "0335": {"name": "335 Å", "desc": "Active cores", "color": "#eb4d4b"},
            "0094": {"name": "94 Å", "desc": "Hot plasma", "color": "#6c5ce7"},
            "1600": {"name": "1600 Å", "desc": "Transition region", "color": "#a29bfe"},
            "1700": {"name": "1700 Å", "desc": "Temperature min", "color": "#fd79a8"},
            "094335193": {"name": "094+335+193", "desc": "Hot plasma + Active cores\n+ Coronal loops", "color": "#8e44ad"},
            "304211171": {"name": "304+211+171", "desc": "Chromosphere + Active regions\n+ Quiet corona", "color": "#e67e22"},
            "211193171": {"name": "211+193+171", "desc": "Active regions + Coronal loops\n+ Quiet corona", "color": "#27ae60"}
        }
        self.filter_buttons = {}
        self._filter_initialized = False
        
        # Initialize components
        self.storage = StorageOrganizer("data", 
                                       resolution=self.resolution_var.get(), 
                                       solar_filter=self.solar_filter_var.get())
        self.scraper = DirectoryScraper(rate_limit_delay=1.0, 
                                       resolution=self.resolution_var.get(), 
                                       solar_filter=self.solar_filter_var.get())
        self.fetcher = ImageFetcher(rate_limit_delay=1.0)
        self.download_manager = DownloadManager(self.fetcher, self.storage)
        
        # GUI state
        self.current_images = []
        self.current_image_index = 0
        self.is_playing = False
        self.play_thread = None
        self.download_thread = None
        
        # Video playback state
        self.video_cap = None
        self.video_playing = False
        self.video_thread = None
        self.selected_video_path = None
        self.fullscreen_mode = False
        self.fullscreen_window = None
        
        self.setup_ui()
        self.refresh_available_dates()
    
    def setup_background_image(self):
        """Set up the background image for the GUI."""
        try:
            # Load the background image
            background_path = Path("background_solar.jpg")
            if background_path.exists():
                # Load and resize the image to fit the screen
                pil_image = Image.open(background_path)
                
                # Get screen dimensions
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                
                # Resize image to cover the screen while maintaining aspect ratio
                pil_image = pil_image.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
                
                # Apply a stronger semi-transparent overlay to make text more readable
                overlay = Image.new('RGBA', (screen_width, screen_height), (0, 0, 0, 150))  # Darker overlay
                pil_image = pil_image.convert('RGBA')
                pil_image = Image.alpha_composite(pil_image, overlay)
                
                # Convert to PhotoImage
                self.background_image = ImageTk.PhotoImage(pil_image)
                
                # Create a label to hold the background image
                self.background_label = tk.Label(self.root, image=self.background_image)
                self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
                
                # Make sure the background stays behind other widgets
                self.background_label.lower()
                
                print("✅ Background image loaded successfully")
            else:
                print("⚠️  Background image not found, using default styling")
                self.root.configure(bg="#2c3e50")
        except Exception as e:
            print(f"❌ Error loading background image: {e}")
            self.root.configure(bg="#2c3e50")
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create notebook for tabs with modern styling and transparency
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Configure notebook styling with transparency
        style = ttk.Style()
        
        # Create all tab frames first to ensure consistent sizing
        self.download_frame = tk.Frame(self.notebook, bg='#1a1a1a', highlightthickness=0)
        self.viewer_frame = tk.Frame(self.notebook, bg='#1a1a1a', highlightthickness=0)
        self.video_frame = tk.Frame(self.notebook, bg='#1a1a1a', highlightthickness=0)
        self.rtsw_frame = tk.Frame(self.notebook, bg='#1a1a1a', highlightthickness=0)
        self.settings_frame = tk.Frame(self.notebook, bg='#1a1a1a', highlightthickness=0)
        
        # Configure frames with semi-transparent dark background
        for frame in [self.download_frame, self.viewer_frame, self.video_frame, self.rtsw_frame, self.settings_frame]:
            frame.configure(bg='#1a1a1a')  # Dark semi-transparent background
        
        # Add tabs to notebook
        self.notebook.add(self.download_frame, text="📥 Download Images")
        self.notebook.add(self.viewer_frame, text="👁️ View Images")
        self.notebook.add(self.video_frame, text="🎬 Videos")
        self.notebook.add(self.rtsw_frame, text="🌬️ Solar Wind")
        self.notebook.add(self.settings_frame, text="⚙️ Settings")
        
        # Configure all frames to have consistent sizing
        for frame in [self.download_frame, self.viewer_frame, self.video_frame, self.rtsw_frame, self.settings_frame]:
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
        
        # Create tab content
        self.create_download_tab()
        self.create_viewer_tab()
        self.create_video_tab()
        self.create_rtsw_tab()
        self.create_settings_tab()
    
    def create_download_tab(self):
        """Create the download tab."""
        # Use the pre-created frame
        download_frame = self.download_frame
        
        # Create a full-width container that ignores frame padding
        title_container = tk.Frame(download_frame, height=150)
        title_container.pack(fill=tk.X, padx=0, pady=(0, 20))
        title_container.pack_propagate(False)
        
        # Title with modern styling and background image
        title_frame = tk.Frame(title_container, height=150)
        title_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        
        # Try to load a background image
        try:
            # Use the specified background image
            bg_image_file = Path("src/ui_img/background.png")
            
            if bg_image_file.exists():
                # Load the background image
                pil_bg_image = Image.open(bg_image_file)
                
                # Get the actual available width (full window width minus notebook padding)
                # Use a callback to update the image when the window is resized
                def update_banner_image(event=None):
                    try:
                        # Get the actual width of the title container
                        actual_width = title_container.winfo_width()
                        if actual_width <= 1:  # Not yet rendered, use default
                            actual_width = 1200 - 30  # Account for notebook padding
                        
                        # Set banner height
                        banner_height = 150
                        
                        # Resize to fill the full width
                        resized_image = pil_bg_image.resize((actual_width, banner_height), Image.Resampling.LANCZOS)
                        
                        # Apply a dark overlay to make text readable
                        overlay = Image.new('RGBA', resized_image.size, (0, 0, 0, 150))  # Semi-transparent black
                        resized_image = resized_image.convert('RGBA')
                        resized_image = Image.alpha_composite(resized_image, overlay)
                        
                        bg_photo = ImageTk.PhotoImage(resized_image)
                        
                        # Update or create background label
                        if hasattr(title_frame, 'bg_label'):
                            title_frame.bg_label.config(image=bg_photo)
                            title_frame.bg_label.image = bg_photo  # Keep reference
                        else:
                            title_frame.bg_label = tk.Label(title_frame, image=bg_photo)
                            title_frame.bg_label.image = bg_photo  # Keep reference
                            title_frame.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                    except Exception as e:
                        print(f"Error updating banner image: {e}")
                
                # Initial image setup
                update_banner_image()
                
                # Bind to configure event to update when window is resized
                title_container.bind('<Configure>', update_banner_image)
                
                # Create title label with dark semi-transparent background
                title_label = tk.Label(title_frame, text="🌞 NASA Solar Image Downloader", 
                                      font=("Arial", 20, "bold"), fg="white", bg="#1a1a1a")
                title_label.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
                
                # Add subtitle
                subtitle_label = tk.Label(title_frame, text="Explore the Sun's Dynamic Activity", 
                                         font=("Arial", 12, "italic"), fg="#f39c12", bg="#1a1a1a")
                subtitle_label.place(relx=0.5, rely=0.65, anchor=tk.CENTER)
                
            else:
                # Fallback to original design if image not found
                title_frame.configure(bg="#3498db")
                title_label = tk.Label(title_frame, text="🌞 NASA Solar Image Downloader", 
                                      font=("Arial", 18, "bold"), fg="white", bg="#3498db")
                title_label.pack(expand=True)
                
        except Exception as e:
            print(f"Error loading banner background: {e}")
            # Fallback to original design
            title_frame.configure(bg="#3498db")
            title_label = tk.Label(title_frame, text="🌞 NASA Solar Image Downloader", 
                                  font=("Arial", 18, "bold"), fg="white", bg="#3498db")
            title_label.pack(expand=True)
        
        # Image filter settings for download tab (moved before date selection)
        download_filter_frame = ttk.LabelFrame(download_frame, text="Image Filters", padding=15)
        download_filter_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Resolution selection
        resolution_frame = ttk.Frame(download_filter_frame)
        resolution_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(resolution_frame, text="Resolution:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        resolution_combo = ttk.Combobox(resolution_frame, textvariable=self.resolution_var, 
                                       values=["1024", "2048", "4096"], state="readonly", width=10)
        resolution_combo.pack(side=tk.LEFT, padx=(0, 20))
        resolution_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Solar filter selection with visual preview
        filter_label = ttk.Label(download_filter_frame, text="Solar Filter:", font=("Arial", 10, "bold"))
        filter_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create the visual filter selection UI
        self.create_filter_selection_ui(download_filter_frame)
        
        # Date selection frame with modern styling (moved after image filters)
        date_frame = ttk.LabelFrame(download_frame, text="Select Date Range", padding=15)
        date_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Quick options with modern buttons
        quick_frame = ttk.Frame(date_frame)
        quick_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(quick_frame, text="Today",
                  command=lambda: self.set_date_range(0)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_frame, text="Last 2 Days",
                  command=lambda: self.set_date_range(1)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_frame, text="Last 3 Days",
                  command=lambda: self.set_date_range(2)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(quick_frame, text="Last Week",
                  command=lambda: self.set_date_range(6)).pack(side=tk.LEFT, padx=(0, 10))
        
        # Custom date selection with better styling
        custom_frame = ttk.Frame(date_frame)
        custom_frame.pack(fill=tk.X)
        
        ttk.Label(custom_frame, text="From:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.start_date_entry = ttk.Entry(custom_frame, textvariable=self.start_date_var, width=12, font=("Arial", 10))
        self.start_date_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(custom_frame, text="To:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.end_date_entry = ttk.Entry(custom_frame, textvariable=self.end_date_var, width=12, font=("Arial", 10))
        self.end_date_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # Download buttons with modern styling
        download_buttons_frame = ttk.Frame(date_frame)
        download_buttons_frame.pack(pady=15)
        
        self.download_btn = ttk.Button(download_buttons_frame, text="🔍 Find & Download Images",
                                      command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.download_all_filters_btn = ttk.Button(download_buttons_frame, text="🌈 Download All Filter Images",
                                                  command=self.start_download_all_filters)
        self.download_all_filters_btn.pack(side=tk.LEFT)
        
        # Progress frame with modern styling
        progress_frame = ttk.LabelFrame(download_frame, text="Download Progress", padding=15)
        progress_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=500)
        self.progress_bar.pack(pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="Ready to download", font=("Arial", 10))
        self.status_label.pack()
        
        # Log frame with modern styling
        log_frame = ttk.LabelFrame(download_frame, text="Download Log", padding=15)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create text widget with scrollbar
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_text_frame, height=10, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_viewer_tab(self):
        """Create the image viewer tab."""
        # Use the pre-created frame
        viewer_frame = self.viewer_frame
        
        # Create a scrollable container for all viewer content
        # Create canvas and scrollbar for scrolling
        viewer_canvas = tk.Canvas(viewer_frame, bg="#f0f0f0")
        viewer_v_scrollbar = ttk.Scrollbar(viewer_frame, orient="vertical", command=viewer_canvas.yview)
        viewer_scrollable_frame = ttk.Frame(viewer_canvas)
        
        # Configure scrolling
        def configure_viewer_scroll_region(event=None):
            viewer_canvas.configure(scrollregion=viewer_canvas.bbox("all"))
        
        viewer_scrollable_frame.bind("<Configure>", configure_viewer_scroll_region)
        
        viewer_canvas.create_window((0, 0), window=viewer_scrollable_frame, anchor="nw")
        viewer_canvas.configure(yscrollcommand=viewer_v_scrollbar.set)
        
        # Make the scrollable frame expand to full canvas width
        def configure_viewer_canvas_width(event):
            # Get the canvas width and set the scrollable frame to match
            canvas_width = event.width
            if viewer_canvas.find_all():
                viewer_canvas.itemconfig(viewer_canvas.find_all()[0], width=canvas_width)
        
        viewer_canvas.bind('<Configure>', configure_viewer_canvas_width)
        
        # Pack canvas and scrollbar to occupy full width
        viewer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        viewer_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def _on_viewer_mousewheel(event):
            viewer_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel events for different platforms
        viewer_canvas.bind("<MouseWheel>", _on_viewer_mousewheel)  # Windows
        viewer_canvas.bind("<Button-4>", lambda e: viewer_canvas.yview_scroll(-1, "units"))  # Linux scroll up
        viewer_canvas.bind("<Button-5>", lambda e: viewer_canvas.yview_scroll(1, "units"))   # Linux scroll down
        
        # Make canvas focusable and bind focus events
        viewer_canvas.focus_set()
        viewer_canvas.bind("<Enter>", lambda e: viewer_canvas.focus_set())
        
        # Also bind to the scrollable frame to catch events
        viewer_scrollable_frame.bind("<MouseWheel>", _on_viewer_mousewheel)
        viewer_scrollable_frame.bind("<Button-4>", lambda e: viewer_canvas.yview_scroll(-1, "units"))
        viewer_scrollable_frame.bind("<Button-5>", lambda e: viewer_canvas.yview_scroll(1, "units"))
        
        # Enable middle button scrolling (same as scroll bar up/down)
        def _on_viewer_middle_button_click(event):
            viewer_canvas.yview_scroll(-3, "units")  # Scroll up like scroll bar
        
        viewer_canvas.bind("<Button-2>", _on_viewer_middle_button_click)
        
        # Now use viewer_scrollable_frame instead of viewer_frame for all content
        
        # Date selection
        date_select_frame = ttk.LabelFrame(viewer_scrollable_frame, text="Select Date Range", padding=10)
        date_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # From date selection
        from_frame = ttk.Frame(date_select_frame)
        from_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(from_frame, text="From:").pack(side=tk.LEFT, padx=(0, 5))
        self.viewer_from_date_var = tk.StringVar()
        self.viewer_from_date_combo = ttk.Combobox(from_frame, textvariable=self.viewer_from_date_var, 
                                                  state="readonly", width=20)
        self.viewer_from_date_combo.pack(side=tk.LEFT)
        
        # To date selection
        to_frame = ttk.Frame(date_select_frame)
        to_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(to_frame, text="To:").pack(side=tk.LEFT, padx=(0, 5))
        self.viewer_to_date_var = tk.StringVar()
        self.viewer_to_date_combo = ttk.Combobox(to_frame, textvariable=self.viewer_to_date_var, 
                                                state="readonly", width=20)
        self.viewer_to_date_combo.pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(date_select_frame)
        button_frame.pack(side=tk.LEFT)
        
        ttk.Button(button_frame, text="Load Images", 
                  command=self.load_images_for_viewer).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Refresh Dates", 
                  command=self.refresh_available_dates).pack(side=tk.LEFT)
        
        # Image filter settings for viewer tab
        viewer_filter_frame = ttk.LabelFrame(viewer_scrollable_frame, text="Image Filters", padding=15)
        viewer_filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Resolution selection
        resolution_frame = ttk.Frame(viewer_filter_frame)
        resolution_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(resolution_frame, text="Resolution:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        resolution_combo = ttk.Combobox(resolution_frame, textvariable=self.resolution_var, 
                                       values=["1024", "2048", "4096"], state="readonly", width=10)
        resolution_combo.pack(side=tk.LEFT, padx=(0, 20))
        resolution_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Solar filter selection with visual preview
        filter_label = ttk.Label(viewer_filter_frame, text="Solar Filter:", font=("Arial", 10, "bold"))
        filter_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create the visual filter selection UI
        self.create_filter_selection_ui(viewer_filter_frame)
        
        # Image display
        image_display_frame = ttk.LabelFrame(viewer_scrollable_frame, text="Solar Image", padding=10)
        image_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.image_display_label = tk.Label(image_display_frame, text="No image loaded", 
                                           background="black", foreground="white",
                                           justify=tk.CENTER, compound=tk.CENTER)
        self.image_display_label.pack(fill=tk.BOTH, expand=True)
        
        # Controls
        controls_frame = ttk.LabelFrame(viewer_scrollable_frame, text="Playback Controls", padding=10)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Playback buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(btn_frame, text="⏮ First", command=self.first_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="⏪ Prev", command=self.prev_image).pack(side=tk.LEFT, padx=(0, 5))
        self.play_btn = ttk.Button(btn_frame, text="▶ Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Next ⏩", command=self.next_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Last ⏭", command=self.last_image).pack(side=tk.LEFT)
        
        # Speed and progress
        control_bottom_frame = ttk.Frame(controls_frame)
        control_bottom_frame.pack(fill=tk.X)
        
        ttk.Label(control_bottom_frame, text="Speed:").pack(side=tk.LEFT, padx=(0, 5))
        self.speed_var = tk.DoubleVar(value=120.0)
        speed_scale = ttk.Scale(control_bottom_frame, from_=0.5, to=240.0, 
                               variable=self.speed_var, orient=tk.HORIZONTAL, length=200,
                               command=self.update_speed_display)
        speed_scale.pack(side=tk.LEFT, padx=(0, 10))
        
        self.speed_display = ttk.Label(control_bottom_frame, text="120.0 FPS")
        self.speed_display.pack(side=tk.LEFT, padx=(0, 20))
        
        # Image info
        self.image_info_label = ttk.Label(control_bottom_frame, text="No images loaded")
        self.image_info_label.pack(side=tk.RIGHT)
        
        # Progress bar for images
        self.image_progress_var = tk.DoubleVar()
        self.image_progress_bar = ttk.Progressbar(controls_frame, variable=self.image_progress_var,
                                                 maximum=100)
        self.image_progress_bar.pack(fill=tk.X, pady=(10, 0))
    
    def create_video_tab(self):
        """Create the video creation and playback tab."""
        # Use the pre-created frame
        video_frame = self.video_frame
        
        # Create a scrollable container for all video content
        # Create canvas and scrollbar for scrolling
        video_canvas = tk.Canvas(video_frame, bg="#f0f0f0")
        video_v_scrollbar = ttk.Scrollbar(video_frame, orient="vertical", command=video_canvas.yview)
        video_scrollable_frame = ttk.Frame(video_canvas)
        
        # Configure scrolling
        def configure_video_scroll_region(event=None):
            video_canvas.configure(scrollregion=video_canvas.bbox("all"))
        
        video_scrollable_frame.bind("<Configure>", configure_video_scroll_region)
        
        video_canvas.create_window((0, 0), window=video_scrollable_frame, anchor="nw")
        video_canvas.configure(yscrollcommand=video_v_scrollbar.set)
        
        # Make the scrollable frame expand to full canvas width
        def configure_video_canvas_width(event):
            # Get the canvas width and set the scrollable frame to match
            canvas_width = event.width
            if video_canvas.find_all():
                video_canvas.itemconfig(video_canvas.find_all()[0], width=canvas_width)
        
        video_canvas.bind('<Configure>', configure_video_canvas_width)
        
        # Pack canvas and scrollbar to occupy full width
        video_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        video_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def _on_video_mousewheel(event):
            video_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel events for different platforms
        video_canvas.bind("<MouseWheel>", _on_video_mousewheel)  # Windows
        video_canvas.bind("<Button-4>", lambda e: video_canvas.yview_scroll(-1, "units"))  # Linux scroll up
        video_canvas.bind("<Button-5>", lambda e: video_canvas.yview_scroll(1, "units"))   # Linux scroll down
        
        # Make canvas focusable and bind focus events
        video_canvas.focus_set()
        video_canvas.bind("<Enter>", lambda e: video_canvas.focus_set())
        
        # Also bind to the scrollable frame to catch events
        video_scrollable_frame.bind("<MouseWheel>", _on_video_mousewheel)
        video_scrollable_frame.bind("<Button-4>", lambda e: video_canvas.yview_scroll(-1, "units"))
        video_scrollable_frame.bind("<Button-5>", lambda e: video_canvas.yview_scroll(1, "units"))
        
        # Enable middle button scrolling (same as scroll bar up/down)
        def _on_video_middle_button_click(event):
            video_canvas.yview_scroll(-3, "units")  # Scroll up like scroll bar
        
        video_canvas.bind("<Button-2>", _on_video_middle_button_click)
        
        # Now use video_scrollable_frame instead of video_frame for all content
        
        # Video creation section
        creation_frame = ttk.LabelFrame(video_scrollable_frame, text="Create MP4 Videos", padding=10)
        creation_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Date selection for video
        video_date_frame = ttk.LabelFrame(creation_frame, text="Select Date Range", padding=10)
        video_date_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Quick options with modern buttons
        video_quick_frame = ttk.Frame(video_date_frame)
        video_quick_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(video_quick_frame, text="Today",
                  command=lambda: self.set_video_date_range(0)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(video_quick_frame, text="Last 3 Days",
                  command=lambda: self.set_video_date_range(2)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(video_quick_frame, text="Last Week",
                  command=lambda: self.set_video_date_range(6)).pack(side=tk.LEFT, padx=(0, 10))
        
        # Custom date selection
        video_custom_frame = ttk.Frame(video_date_frame)
        video_custom_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(video_custom_frame, text="From:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.video_start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.video_start_date_entry = ttk.Entry(video_custom_frame, textvariable=self.video_start_date_var, width=12, font=("Arial", 10))
        self.video_start_date_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(video_custom_frame, text="To:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        self.video_end_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.video_end_date_entry = ttk.Entry(video_custom_frame, textvariable=self.video_end_date_var, width=12, font=("Arial", 10))
        self.video_end_date_entry.pack(side=tk.LEFT, padx=(0, 20))
        
        # FPS setting
        ttk.Label(video_custom_frame, text="FPS:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(10, 5))
        self.video_fps_var = tk.IntVar(value=120)
        fps_spinbox = ttk.Spinbox(video_custom_frame, from_=1, to=240, width=5, 
                                 textvariable=self.video_fps_var)
        fps_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Video creation buttons
        video_btn_frame = ttk.Frame(creation_frame)
        video_btn_frame.pack(fill=tk.X)
        
        ttk.Button(video_btn_frame, text="🎬 Create Video for Date Range", 
                  command=self.create_date_range_video).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(video_btn_frame, text="🎬 Create Combined Video (All Available)", 
                  command=self.create_all_videos).pack(side=tk.LEFT)
        
        # Video creation progress
        video_progress_frame = ttk.LabelFrame(creation_frame, text="Video Creation Progress", padding=10)
        video_progress_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.video_progress_var = tk.DoubleVar()
        self.video_progress_bar = ttk.Progressbar(video_progress_frame, variable=self.video_progress_var, 
                                                 maximum=100, length=500)
        self.video_progress_bar.pack(pady=(0, 10))
        
        self.video_status_label = ttk.Label(video_progress_frame, text="Ready to create video", font=("Arial", 10))
        self.video_status_label.pack()
        
        # Image filter settings for video tab
        video_filter_frame = ttk.LabelFrame(video_scrollable_frame, text="Image Filters", padding=15)
        video_filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Resolution selection
        video_resolution_frame = ttk.Frame(video_filter_frame)
        video_resolution_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(video_resolution_frame, text="Resolution:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        resolution_combo = ttk.Combobox(video_resolution_frame, textvariable=self.resolution_var, 
                                       values=["1024", "2048", "4096"], state="readonly", width=10)
        resolution_combo.pack(side=tk.LEFT, padx=(0, 20))
        resolution_combo.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Solar filter selection with visual preview
        filter_label = ttk.Label(video_filter_frame, text="Solar Filter:", font=("Arial", 10, "bold"))
        filter_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create the visual filter selection UI
        self.create_filter_selection_ui(video_filter_frame)
        
        # Video playback section
        playback_frame = ttk.LabelFrame(video_scrollable_frame, text="Play MP4 Videos", padding=10)
        playback_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Video file selection
        video_select_frame = ttk.Frame(playback_frame)
        video_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(video_select_frame, text="Select MP4 File", 
                  command=self.select_video_file).pack(side=tk.LEFT, padx=(0, 10))
        self.selected_video_label = ttk.Label(video_select_frame, text="No video selected")
        self.selected_video_label.pack(side=tk.LEFT)
        
        # Video display area - Fixed size 1024x1024 pixels
        self.video_display_frame = ttk.Frame(playback_frame, relief=tk.SUNKEN, borderwidth=2)
        self.video_display_frame.pack(pady=(0, 10))
        self.video_display_frame.pack_propagate(False)  # Prevent frame from shrinking
        self.video_display_frame.configure(width=1024, height=1024)  # Fixed size
        
        self.video_display_label = tk.Label(self.video_display_frame, text="Select a video to play", 
                                           background="black", foreground="white", 
                                           justify=tk.CENTER, compound=tk.CENTER)
        self.video_display_label.pack(fill=tk.BOTH, expand=True)
        
        # Video controls
        video_controls_frame = ttk.Frame(playback_frame)
        video_controls_frame.pack(fill=tk.X)
        
        self.video_play_btn = ttk.Button(video_controls_frame, text="▶ Play Video", 
                                        command=self.play_video, state=tk.DISABLED)
        self.video_play_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(video_controls_frame, text="⏹ Stop", 
                  command=self.stop_video).pack(side=tk.LEFT, padx=(0, 5))
        
        self.fullscreen_btn = ttk.Button(video_controls_frame, text="🔳 Fullscreen", 
                                        command=self.toggle_fullscreen, state=tk.DISABLED)
        self.fullscreen_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(video_controls_frame, text="📁 Open Video Folder", 
                  command=self.open_video_folder).pack(side=tk.RIGHT)
    
    def create_rtsw_tab(self):
        """Create the Real Time Solar Wind tab with plots and historical data."""
        # Use the pre-created frame
        rtsw_frame = self.rtsw_frame
        
        # Create a scrollable container for all RTSW content
        # Create canvas and scrollbar for scrolling
        rtsw_canvas = tk.Canvas(rtsw_frame, bg="#f0f0f0")
        rtsw_v_scrollbar = ttk.Scrollbar(rtsw_frame, orient="vertical", command=rtsw_canvas.yview)
        rtsw_scrollable_frame = ttk.Frame(rtsw_canvas)
        
        # Configure scrolling
        def configure_rtsw_scroll_region(event=None):
            rtsw_canvas.configure(scrollregion=rtsw_canvas.bbox("all"))
        
        rtsw_scrollable_frame.bind("<Configure>", configure_rtsw_scroll_region)
        
        rtsw_canvas.create_window((0, 0), window=rtsw_scrollable_frame, anchor="nw")
        rtsw_canvas.configure(yscrollcommand=rtsw_v_scrollbar.set)
        
        # Make the scrollable frame expand to full canvas width
        def configure_rtsw_canvas_width(event):
            canvas_width = event.width
            if rtsw_canvas.find_all():
                rtsw_canvas.itemconfig(rtsw_canvas.find_all()[0], width=canvas_width)
        
        rtsw_canvas.bind('<Configure>', configure_rtsw_canvas_width)
        
        # Pack canvas and scrollbar to occupy full width
        rtsw_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rtsw_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def _on_rtsw_mousewheel(event):
            rtsw_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel events for different platforms
        rtsw_canvas.bind("<MouseWheel>", _on_rtsw_mousewheel)  # Windows
        rtsw_canvas.bind("<Button-4>", lambda e: rtsw_canvas.yview_scroll(-1, "units"))  # Linux scroll up
        rtsw_canvas.bind("<Button-5>", lambda e: rtsw_canvas.yview_scroll(1, "units"))   # Linux scroll down
        
        # Make canvas focusable and bind focus events
        rtsw_canvas.focus_set()
        rtsw_canvas.bind("<Enter>", lambda e: rtsw_canvas.focus_set())
        
        # Also bind to the scrollable frame to catch events
        rtsw_scrollable_frame.bind("<MouseWheel>", _on_rtsw_mousewheel)
        rtsw_scrollable_frame.bind("<Button-4>", lambda e: rtsw_canvas.yview_scroll(-1, "units"))
        rtsw_scrollable_frame.bind("<Button-5>", lambda e: rtsw_canvas.yview_scroll(1, "units"))
        
        # Enable middle button scrolling
        def _on_rtsw_middle_button_click(event):
            rtsw_canvas.yview_scroll(-3, "units")
        
        rtsw_canvas.bind("<Button-2>", _on_rtsw_middle_button_click)
        
        # Now use rtsw_scrollable_frame for all content
        
        # Title section
        title_frame = ttk.LabelFrame(rtsw_scrollable_frame, text="🌬️ Real Time Solar Wind Data", padding=15)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        info_label = ttk.Label(title_frame, 
                              text="Real-time solar wind data from NOAA Space Weather Prediction Center\n"
                                   "Includes historical data, real-time measurements, and visual plots",
                              font=("Arial", 10))
        info_label.pack(anchor=tk.W)
        
        # Control section
        control_frame = ttk.LabelFrame(rtsw_scrollable_frame, text="Data Controls", padding=15)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Refresh button and status
        control_top_frame = ttk.Frame(control_frame)
        control_top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.rtsw_refresh_btn = ttk.Button(control_top_frame, text="🔄 Refresh Data", 
                                          command=self.refresh_rtsw_data)
        self.rtsw_refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.rtsw_auto_refresh_var = tk.BooleanVar(value=False)
        auto_refresh_check = ttk.Checkbutton(control_top_frame, text="Auto-refresh every 5 minutes",
                                           variable=self.rtsw_auto_refresh_var,
                                           command=self.toggle_auto_refresh)
        auto_refresh_check.pack(side=tk.LEFT, padx=(0, 10))
        
        self.rtsw_status_label = ttk.Label(control_top_frame, text="Click 'Refresh Data' to load solar wind data")
        self.rtsw_status_label.pack(side=tk.RIGHT)
        
        # Time range selection
        time_range_frame = ttk.Frame(control_frame)
        time_range_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(time_range_frame, text="Time Range:").pack(side=tk.LEFT, padx=(0, 5))
        self.rtsw_time_range_var = tk.StringVar(value="24 hours")
        time_range_combo = ttk.Combobox(time_range_frame, textvariable=self.rtsw_time_range_var,
                                       values=["6 hours", "12 hours", "24 hours", "3 days", "7 days"],
                                       state="readonly", width=10)
        time_range_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Seaborn Analytics Section
        seaborn_frame = ttk.LabelFrame(control_frame, text="📈 Statistical Analysis with Seaborn", padding=10)
        seaborn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Try to import Seaborn for statistical plotting
        try:
            import seaborn as sns
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            
            # Seaborn controls
            seaborn_controls_frame = ttk.Frame(seaborn_frame)
            seaborn_controls_frame.pack(fill=tk.X, pady=(0, 10))
            
            self.seaborn_generate_btn = ttk.Button(seaborn_controls_frame, text="📊 Generate All Plots", 
                                                  command=self.generate_seaborn_plots)
            self.seaborn_generate_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.seaborn_save_btn = ttk.Button(seaborn_controls_frame, text="💾 Save Analysis", 
                                              command=self.save_seaborn_analysis)
            self.seaborn_save_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # Plot type selection
            ttk.Label(seaborn_controls_frame, text="Analysis Type:").pack(side=tk.LEFT, padx=(10, 5))
            self.seaborn_plot_type_var = tk.StringVar(value="time_series")
            seaborn_type_combo = ttk.Combobox(seaborn_controls_frame, textvariable=self.seaborn_plot_type_var,
                                             values=["correlation", "distribution", "time_series", "regression"],
                                             state="readonly", width=12)
            seaborn_type_combo.pack(side=tk.LEFT, padx=(0, 10))
            
            # Create Seaborn plot container
            self.seaborn_plot_frame = ttk.Frame(seaborn_frame)
            self.seaborn_plot_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create matplotlib figure for Seaborn (larger size for 5 graphs following NOAA format)
            self.seaborn_fig = Figure(figsize=(14, 12), dpi=80, facecolor='white')
            self.seaborn_canvas = FigureCanvasTkAgg(self.seaborn_fig, self.seaborn_plot_frame)
            self.seaborn_canvas.draw()
            self.seaborn_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Status label for Seaborn
            self.seaborn_status_label = ttk.Label(seaborn_frame, 
                                                 text="🎨 Ready to generate beautiful statistical analysis plots!",
                                                 font=("Arial", 10), foreground="#2E86AB")
            self.seaborn_status_label.pack(pady=(10, 0))
            
            # Set Seaborn availability flag
            self.seaborn_available = True
            
            # Generate initial sample plots
            self._create_seaborn_sample_plots()
            
        except ImportError:
            # Seaborn not available, show message
            no_seaborn_label = ttk.Label(seaborn_frame, 
                                        text="📈 Statistical analysis requires Seaborn\n"
                                             "Install with: pip install seaborn\n"
                                             "Beautiful statistical plots for solar wind data analysis",
                                        font=("Arial", 10), justify=tk.CENTER)
            no_seaborn_label.pack(expand=True, pady=20)
            self.seaborn_available = False
        
        # Plot section with Plotly
        plot_frame = ttk.LabelFrame(rtsw_scrollable_frame, text="📊 Solar Wind Plots (Last 24 Hours)", padding=15)
        plot_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Try to import Plotly for interactive plotting
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import plotly.offline as pyo
            import webbrowser
            import tempfile
            import os
            
            # Create container for plot display
            self.plot_container = ttk.Frame(plot_frame)
            self.plot_container.pack(fill=tk.BOTH, expand=True)
            
            # Create a button to open plots in browser
            plot_controls_frame = ttk.Frame(self.plot_container)
            plot_controls_frame.pack(fill=tk.X, pady=(0, 10))
            
            self.open_plots_btn = ttk.Button(plot_controls_frame, text="🚀 Open Interactive Plots in Browser", 
                                           command=self.open_plotly_in_browser)
            self.open_plots_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            self.save_plots_btn = ttk.Button(plot_controls_frame, text="💾 Save Plots as HTML", 
                                           command=self.save_plotly_plots)
            self.save_plots_btn.pack(side=tk.LEFT)
            
            # Create info label for plot status
            self.plot_info_label = ttk.Label(self.plot_container, 
                                           text="🎨 Beautiful interactive plots ready! Click 'Open Interactive Plots' to view in browser.",
                                           font=("Arial", 10), foreground="#2E86AB")
            self.plot_info_label.pack(pady=10)
            
            # Initialize Plotly figure
            self.plotly_fig = None
            self.plot_html_path = None
            
            # Set plotting availability flag BEFORE calling placeholder plots
            self.plotly_available = True
            
            # Add initial placeholder plots
            self._create_placeholder_plots()
            
        except ImportError:
            # Plotly not available, show message
            no_plot_label = ttk.Label(plot_frame, 
                                     text="📊 Interactive plotting requires Plotly\n"
                                          "Install with: pip install plotly\n"
                                          "Beautiful interactive plots will show solar wind parameters over time",
                                     font=("Arial", 10), justify=tk.CENTER)
            no_plot_label.pack(expand=True, pady=20)
            self.plotly_available = False
        
        # Current data section (reduced size since we have plots now)
        data_frame = ttk.LabelFrame(rtsw_scrollable_frame, text="Current Solar Wind Parameters", padding=15)
        data_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create text widget for current data display (smaller)
        data_text_frame = ttk.Frame(data_frame)
        data_text_frame.pack(fill=tk.X)
        
        self.rtsw_data_text = tk.Text(data_text_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        rtsw_data_scrollbar = ttk.Scrollbar(data_text_frame, orient=tk.VERTICAL, command=self.rtsw_data_text.yview)
        self.rtsw_data_text.configure(yscrollcommand=rtsw_data_scrollbar.set)
        
        self.rtsw_data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rtsw_data_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert initial message
        self.rtsw_data_text.insert(tk.END, "Real Time Solar Wind Data\n")
        self.rtsw_data_text.insert(tk.END, "=" * 50 + "\n\n")
        self.rtsw_data_text.insert(tk.END, "Click 'Refresh Data' to load the latest solar wind measurements from NOAA.\n\n")
        self.rtsw_data_text.insert(tk.END, "Data Source: https://www.swpc.noaa.gov/products/real-time-solar-wind\n\n")
        self.rtsw_data_text.insert(tk.END, "Parameters include:\n")
        self.rtsw_data_text.insert(tk.END, "• Magnetic Field Components (Bx, By, Bz) in nT\n")
        self.rtsw_data_text.insert(tk.END, "• Total Magnetic Field (Bt) in nT\n")
        self.rtsw_data_text.insert(tk.END, "• Solar Wind Speed (km/s) - when available\n")
        self.rtsw_data_text.insert(tk.END, "• Proton Density (p/cm³) - when available\n")
        self.rtsw_data_text.configure(state=tk.DISABLED)
        
        # Historical data section
        history_frame = ttk.LabelFrame(rtsw_scrollable_frame, text="📈 Historical Data & Analysis", padding=15)
        history_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Historical data text widget
        history_text_frame = ttk.Frame(history_frame)
        history_text_frame.pack(fill=tk.X)
        
        self.rtsw_history_text = tk.Text(history_text_frame, height=8, wrap=tk.WORD, font=("Consolas", 9))
        history_scrollbar = ttk.Scrollbar(history_text_frame, orient=tk.VERTICAL, command=self.rtsw_history_text.yview)
        self.rtsw_history_text.configure(yscrollcommand=history_scrollbar.set)
        
        self.rtsw_history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert initial historical data message
        self.rtsw_history_text.insert(tk.END, "Historical Solar Wind Analysis\n")
        self.rtsw_history_text.insert(tk.END, "=" * 40 + "\n\n")
        self.rtsw_history_text.insert(tk.END, "Statistical analysis and trends will appear here after data refresh.\n\n")
        self.rtsw_history_text.insert(tk.END, "Analysis includes:\n")
        self.rtsw_history_text.insert(tk.END, "• Average values over selected time period\n")
        self.rtsw_history_text.insert(tk.END, "• Maximum and minimum values\n")
        self.rtsw_history_text.insert(tk.END, "• Geomagnetic storm indicators\n")
        self.rtsw_history_text.insert(tk.END, "• Data quality and coverage statistics\n")
        self.rtsw_history_text.configure(state=tk.DISABLED)
        
        # Links section
        links_frame = ttk.LabelFrame(rtsw_scrollable_frame, text="Related Links", padding=15)
        links_frame.pack(fill=tk.X, padx=10, pady=5)
        
        links_text = "🔗 NOAA Space Weather: https://www.swpc.noaa.gov/\n"
        links_text += "🔗 Real-time Solar Wind: https://www.swpc.noaa.gov/products/real-time-solar-wind\n"
        links_text += "🔗 Space Weather Alerts: https://www.swpc.noaa.gov/products/alerts-watches-and-warnings\n"
        links_text += "🔗 Geomagnetic Activity: https://www.swpc.noaa.gov/products/planetary-k-index"
        
        links_label = ttk.Label(links_frame, text=links_text, font=("Arial", 9))
        links_label.pack(anchor=tk.W)
        
        # Initialize variables
        self.rtsw_auto_refresh_job = None
        self.rtsw_data_cache = []  # Store historical data for plotting
    
    def refresh_rtsw_data(self):
        """Refresh the real-time solar wind data."""
        try:
            self.rtsw_refresh_btn.config(state=tk.DISABLED)
            self.rtsw_status_label.config(text="Loading solar wind data...")
            
            # Start data fetching in background thread
            threading.Thread(target=self._fetch_rtsw_data, daemon=True).start()
            
        except Exception as e:
            self.rtsw_status_label.config(text=f"Error: {str(e)}")
            self.rtsw_refresh_btn.config(state=tk.NORMAL)
    
    def _fetch_rtsw_data(self):
        """Fetch solar wind data in background thread."""
        try:
            import urllib.request
            import json
            from datetime import datetime
            
            # Update status
            self.root.after(0, lambda: self.rtsw_status_label.config(text="Fetching data from NOAA..."))
            
            # NOAA provides JSON data for real-time solar wind
            # This is a simplified example - in practice, you might need to parse specific data formats
            url = "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json"
            
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                
                # Process and format the data
                formatted_data = self._format_rtsw_data(data)
                
                # Update UI in main thread
                self.root.after(0, lambda: self._update_rtsw_display(formatted_data))
                
            except Exception as e:
                # If the JSON endpoint fails, show a placeholder with instructions
                placeholder_data = self._get_rtsw_placeholder_data()
                self.root.after(0, lambda: self._update_rtsw_display(placeholder_data))
                
        except Exception as e:
            error_msg = f"Error fetching data: {str(e)}"
            self.root.after(0, lambda: self.rtsw_status_label.config(text=error_msg))
        
        finally:
            self.root.after(0, lambda: self.rtsw_refresh_btn.config(state=tk.NORMAL))
    
    def _format_rtsw_data(self, data):
        """Format the solar wind data for display."""
        try:
            formatted = "Real Time Solar Wind Data\n"
            formatted += "=" * 50 + "\n"
            formatted += f"Data retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            formatted += f"Source: NOAA Space Weather Prediction Center\n\n"
            
            if isinstance(data, list) and len(data) > 1:
                # Skip header row and get recent data
                recent_entries = data[-10:] if len(data) > 10 else data[1:]
                
                formatted += "Recent Solar Wind Measurements:\n"
                formatted += "-" * 40 + "\n"
                
                for entry in recent_entries:
                    if isinstance(entry, list) and len(entry) >= 7:
                        time_tag = entry[0]
                        bx = entry[1] if entry[1] != '' else 'N/A'
                        by = entry[2] if entry[2] != '' else 'N/A'
                        bz = entry[3] if entry[3] != '' else 'N/A'
                        bt = entry[4] if entry[4] != '' else 'N/A'
                        
                        formatted += f"Time: {time_tag}\n"
                        formatted += f"  Magnetic Field - Bx: {bx} nT, By: {by} nT, Bz: {bz} nT\n"
                        formatted += f"  Total Field (Bt): {bt} nT\n\n"
            else:
                formatted += "No recent data available.\n"
            
            formatted += "\nData Parameters:\n"
            formatted += "• Bx, By, Bz: Magnetic field components in GSM coordinates (nanoTesla)\n"
            formatted += "• Bt: Total magnetic field strength (nanoTesla)\n"
            formatted += "• GSM: Geocentric Solar Magnetospheric coordinate system\n\n"
            
            formatted += "Note: This is real-time data and may contain gaps or anomalies.\n"
            formatted += "For official space weather alerts, visit: https://www.swpc.noaa.gov/\n"
            
            return formatted
            
        except Exception as e:
            return f"Error formatting data: {str(e)}\n\nRaw data preview:\n{str(data)[:500]}..."
    
    def _get_rtsw_placeholder_data(self):
        """Get placeholder data when real data is not available."""
        placeholder = "Real Time Solar Wind Data\n"
        placeholder += "=" * 50 + "\n"
        placeholder += f"Data retrieval attempted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        placeholder += "🌐 NOAA Real-Time Solar Wind Data\n"
        placeholder += "-" * 40 + "\n\n"
        
        placeholder += "This tab displays real-time solar wind data from NOAA's\n"
        placeholder += "Space Weather Prediction Center.\n\n"
        
        placeholder += "Data includes:\n"
        placeholder += "• Solar Wind Speed (km/s)\n"
        placeholder += "• Proton Density (particles/cm³)\n"
        placeholder += "• Temperature (Kelvin)\n"
        placeholder += "• Magnetic Field Components (nanoTesla)\n"
        placeholder += "• Interplanetary Magnetic Field (IMF)\n\n"
        
        placeholder += "🔗 Data Sources:\n"
        placeholder += "• Real-time Solar Wind: https://www.swpc.noaa.gov/products/real-time-solar-wind\n"
        placeholder += "• Space Weather Alerts: https://www.swpc.noaa.gov/products/alerts-watches-and-warnings\n"
        placeholder += "• Solar Wind Speed: https://www.swpc.noaa.gov/products/solar-wind\n\n"
        
        placeholder += "📊 Understanding Solar Wind:\n"
        placeholder += "Solar wind is a stream of charged particles released from the\n"
        placeholder += "upper atmosphere of the Sun. It affects Earth's magnetosphere\n"
        placeholder += "and can cause geomagnetic storms, aurora, and disruptions to\n"
        placeholder += "satellite communications and power grids.\n\n"
        
        placeholder += "🚨 Space Weather Impact:\n"
        placeholder += "• High solar wind speed (>600 km/s): Increased geomagnetic activity\n"
        placeholder += "• Strong southward IMF (Bz < -10 nT): Enhanced aurora activity\n"
        placeholder += "• High proton density (>20 p/cm³): Potential for geomagnetic storms\n\n"
        
        placeholder += "Note: Click 'Refresh Data' to attempt loading real-time measurements.\n"
        placeholder += "Auto-refresh can be enabled to update data every 5 minutes.\n"
        
        return placeholder
    
    def _update_rtsw_display(self, formatted_data):
        """Update the RTSW data display in the main thread."""
        try:
            self.rtsw_data_text.config(state=tk.NORMAL)
            self.rtsw_data_text.delete(1.0, tk.END)
            self.rtsw_data_text.insert(tk.END, formatted_data)
            self.rtsw_data_text.config(state=tk.DISABLED)
            
            self.rtsw_status_label.config(text=f"Data updated: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.rtsw_status_label.config(text=f"Display error: {str(e)}")
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh for RTSW data."""
        if self.rtsw_auto_refresh_var.get():
            # Start auto-refresh
            self.rtsw_status_label.config(text="Auto-refresh enabled (5 min intervals)")
            self._schedule_rtsw_refresh()
        else:
            # Stop auto-refresh
            if self.rtsw_auto_refresh_job:
                self.root.after_cancel(self.rtsw_auto_refresh_job)
                self.rtsw_auto_refresh_job = None
            self.rtsw_status_label.config(text="Auto-refresh disabled")
    
    def _schedule_rtsw_refresh(self):
        """Schedule the next auto-refresh."""
        if self.rtsw_auto_refresh_var.get():
            # Schedule refresh in 5 minutes (300,000 ms)
            self.rtsw_auto_refresh_job = self.root.after(300000, self._auto_refresh_rtsw)
    
    def _auto_refresh_rtsw(self):
        """Perform auto-refresh of RTSW data."""
        if self.rtsw_auto_refresh_var.get():
            self.refresh_rtsw_data()
            self._schedule_rtsw_refresh()  # Schedule next refresh
    
    def _create_placeholder_plots(self):
        """Create beautiful placeholder plots with Plotly when no data is available."""
        if not self.plotly_available:
            return
        
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import numpy as np
            from datetime import datetime, timedelta
            
            # Create sample time series for demonstration
            now = datetime.now()
            times = [now - timedelta(hours=24-i) for i in range(24)]
            
            # Sample data for demonstration with more realistic variations
            bz_data = np.random.normal(-2, 5, 24)  # Bz component
            bt_data = np.abs(np.random.normal(8, 3, 24))  # Total field (always positive)
            speed_data = np.random.normal(450, 100, 24)  # Solar wind speed
            density_data = np.abs(np.random.normal(5, 2, 24))  # Proton density
            
            # Create subplots with beautiful styling
            self.plotly_fig = make_subplots(
                rows=4, cols=1,
                subplot_titles=(
                    '🌌 Interplanetary Magnetic Field - Bz Component (Sample Data)',
                    '🧲 Total Magnetic Field Strength (Sample Data)', 
                    '💨 Solar Wind Speed (Sample Data)',
                    '⚛️ Proton Density (Sample Data)'
                ),
                vertical_spacing=0.08,
                shared_xaxes=True
            )
            
            # Color scheme for visual impact
            colors = {
                'bz': '#00D4FF',      # Bright cyan
                'bt': '#00FF88',      # Bright green
                'speed': '#FF6B35',   # Bright orange
                'density': '#FF3366', # Bright pink
                'threshold_minor': '#FFB800',  # Golden yellow
                'threshold_major': '#FF0040',  # Bright red
                'background': '#0A0A0A'        # Dark background
            }
            
            # Plot 1: Bz Component with storm thresholds
            self.plotly_fig.add_trace(
                go.Scatter(
                    x=times, y=bz_data,
                    mode='lines+markers',
                    name='Bz Component',
                    line=dict(color=colors['bz'], width=3, shape='spline'),
                    marker=dict(size=6, color=colors['bz'], symbol='circle'),
                    hovertemplate='<b>Bz:</b> %{y:.2f} nT<br><b>Time:</b> %{x}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Add threshold lines for Bz
            self.plotly_fig.add_hline(y=0, line_dash="solid", line_color="white", 
                                    annotation_text="Zero Line", row=1, col=1)
            self.plotly_fig.add_hline(y=-5, line_dash="dash", line_color=colors['threshold_minor'], 
                                    annotation_text="Minor Storm (-5 nT)", row=1, col=1)
            self.plotly_fig.add_hline(y=-10, line_dash="dash", line_color=colors['threshold_major'], 
                                    annotation_text="Major Storm (-10 nT)", row=1, col=1)
            
            # Plot 2: Total Magnetic Field
            self.plotly_fig.add_trace(
                go.Scatter(
                    x=times, y=bt_data,
                    mode='lines+markers',
                    name='Total Field (Bt)',
                    line=dict(color=colors['bt'], width=3, shape='spline'),
                    marker=dict(size=6, color=colors['bt'], symbol='diamond'),
                    hovertemplate='<b>Bt:</b> %{y:.2f} nT<br><b>Time:</b> %{x}<extra></extra>'
                ),
                row=2, col=1
            )
            
            # Plot 3: Solar Wind Speed with thresholds
            self.plotly_fig.add_trace(
                go.Scatter(
                    x=times, y=speed_data,
                    mode='lines+markers',
                    name='Solar Wind Speed',
                    line=dict(color=colors['speed'], width=3, shape='spline'),
                    marker=dict(size=6, color=colors['speed'], symbol='triangle-up'),
                    hovertemplate='<b>Speed:</b> %{y:.1f} km/s<br><b>Time:</b> %{x}<extra></extra>'
                ),
                row=3, col=1
            )
            
            # Add speed threshold lines
            self.plotly_fig.add_hline(y=400, line_dash="dash", line_color=colors['threshold_minor'], 
                                    annotation_text="Elevated Speed (400 km/s)", row=3, col=1)
            self.plotly_fig.add_hline(y=600, line_dash="dash", line_color=colors['threshold_major'], 
                                    annotation_text="High Speed (600 km/s)", row=3, col=1)
            
            # Plot 4: Proton Density
            self.plotly_fig.add_trace(
                go.Scatter(
                    x=times, y=density_data,
                    mode='lines+markers',
                    name='Proton Density',
                    line=dict(color=colors['density'], width=3, shape='spline'),
                    marker=dict(size=6, color=colors['density'], symbol='star'),
                    hovertemplate='<b>Density:</b> %{y:.2f} p/cm³<br><b>Time:</b> %{x}<extra></extra>'
                ),
                row=4, col=1
            )
            
            # Update layout for maximum visual impact
            self.plotly_fig.update_layout(
                title=dict(
                    text='🌟 Real-Time Solar Wind Monitoring Dashboard 🌟',
                    x=0.5,
                    font=dict(size=24, color='white', family='Arial Black')
                ),
                plot_bgcolor='rgba(10, 10, 10, 0.9)',
                paper_bgcolor='rgba(5, 5, 5, 0.95)',
                font=dict(color='white', size=12, family='Arial'),
                height=800,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(0, 0, 0, 0.5)',
                    bordercolor='white',
                    borderwidth=1
                ),
                margin=dict(l=60, r=60, t=100, b=60)
            )
            
            # Update axes for all subplots
            for i in range(1, 5):
                self.plotly_fig.update_xaxes(
                    gridcolor='rgba(255, 255, 255, 0.2)',
                    gridwidth=1,
                    showgrid=True,
                    zeroline=False,
                    tickfont=dict(color='white'),
                    row=i, col=1
                )
                self.plotly_fig.update_yaxes(
                    gridcolor='rgba(255, 255, 255, 0.2)',
                    gridwidth=1,
                    showgrid=True,
                    zeroline=False,
                    tickfont=dict(color='white'),
                    row=i, col=1
                )
            
            # Update y-axis labels
            self.plotly_fig.update_yaxes(title_text="Bz (nT)", title_font=dict(color='white'), row=1, col=1)
            self.plotly_fig.update_yaxes(title_text="Bt (nT)", title_font=dict(color='white'), row=2, col=1)
            self.plotly_fig.update_yaxes(title_text="Speed (km/s)", title_font=dict(color='white'), row=3, col=1)
            self.plotly_fig.update_yaxes(title_text="Density (p/cm³)", title_font=dict(color='white'), row=4, col=1)
            self.plotly_fig.update_xaxes(title_text="Time (UTC)", title_font=dict(color='white'), row=4, col=1)
            
            # Save the plot to a temporary HTML file
            self._save_plotly_to_temp()
            
            # Update info label
            self.plot_info_label.config(text="🎨 Beautiful sample data plots created! Click 'Open Interactive Plots' to view.")
            
        except Exception as e:
            print(f"Error creating Plotly placeholder plots: {e}")
            if hasattr(self, 'plot_info_label'):
                self.plot_info_label.config(text=f"❌ Error creating plots: {str(e)}")
    
    def open_plotly_in_browser(self):
        """Open the Plotly plots in the default web browser."""
        if self.plot_html_path and os.path.exists(self.plot_html_path):
            webbrowser.open(f'file://{os.path.abspath(self.plot_html_path)}')
            self.plot_info_label.config(text="🚀 Interactive plots opened in browser!")
        else:
            self.plot_info_label.config(text="❌ No plots available. Please refresh data first.")
    
    def save_plotly_plots(self):
        """Save the current Plotly plots as an HTML file."""
        if self.plotly_fig:
            try:
                from tkinter import filedialog
                filename = filedialog.asksaveasfilename(
                    defaultextension=".html",
                    filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
                    title="Save Solar Wind Plots"
                )
                if filename:
                    import plotly.offline as pyo
                    pyo.plot(self.plotly_fig, filename=filename, auto_open=False)
                    self.plot_info_label.config(text=f"💾 Plots saved to: {os.path.basename(filename)}")
            except Exception as e:
                self.plot_info_label.config(text=f"❌ Error saving plots: {str(e)}")
        else:
            self.plot_info_label.config(text="❌ No plots to save. Please refresh data first.")
    
    def _save_plotly_to_temp(self):
        """Save the current Plotly figure to a temporary HTML file."""
        if self.plotly_fig:
            try:
                import plotly.offline as pyo
                import tempfile
                
                # Create a temporary HTML file
                temp_dir = tempfile.gettempdir()
                self.plot_html_path = os.path.join(temp_dir, 'nasa_solar_wind_plots.html')
                
                pyo.plot(self.plotly_fig, filename=self.plot_html_path, auto_open=False)
                
            except Exception as e:
                print(f"Error saving Plotly to temp file: {e}")
                self.plot_html_path = None
    
    def generate_seaborn_plots(self):
        """Generate beautiful statistical analysis plots using Seaborn and update Plotly interactive plots."""
        if not self.seaborn_available:
            return
        
        try:
            self.seaborn_generate_btn.config(state=tk.DISABLED)
            self.seaborn_status_label.config(text="🎨 Generating statistical plots and updating interactive plots...")
            
            # Start combined plot generation in background thread
            threading.Thread(target=self._generate_combined_plots_worker, daemon=True).start()
            
        except Exception as e:
            self.seaborn_status_label.config(text=f"❌ Error: {str(e)}")
            self.seaborn_generate_btn.config(state=tk.NORMAL)
    
    def _generate_seaborn_worker(self):
        """Generate Seaborn plots in background thread."""
        try:
            import seaborn as sns
            import matplotlib.pyplot as plt
            import pandas as pd
            import numpy as np
            from datetime import datetime, timedelta
            import urllib.request
            import json
            
            # Get plot type
            plot_type = self.seaborn_plot_type_var.get()
            
            self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Fetching real solar wind data for analysis..."))
            
            # Try to fetch real solar wind data first
            df = None
            try:
                # Get time range
                time_range = self.rtsw_time_range_var.get()
                hours_map = {"6 hours": 6, "12 hours": 12, "24 hours": 24, "3 days": 72, "7 days": 168}
                hours = hours_map.get(time_range, 24)
                
                # Fetch magnetic field data
                mag_url = "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json"
                
                with urllib.request.urlopen(mag_url, timeout=15) as response:
                    mag_data = json.loads(response.read().decode())
                
                # Process magnetic field data
                times, bz_values, bt_values = self._process_mag_data(mag_data, hours)
                
                # Try to fetch plasma data
                plasma_url = "https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json"
                speed_values = []
                density_values = []
                
                try:
                    with urllib.request.urlopen(plasma_url, timeout=15) as response:
                        plasma_data = json.loads(response.read().decode())
                    
                    _, speed_values, density_values = self._process_plasma_data(plasma_data, hours)
                    
                except Exception as e:
                    print(f"Plasma data not available: {e}")
                    # Create placeholder data if plasma data is not available
                    speed_values = [400 + np.random.normal(0, 50) for _ in times]
                    density_values = [5 + np.random.normal(0, 1) for _ in times]
                
                # Create DataFrame from real data
                if times and len(times) > 10:  # Need sufficient data points
                    # Ensure all arrays have the same length
                    min_length = min(len(times), len(bz_values), len(bt_values), len(speed_values), len(density_values))
                    
                    # Filter out None values and create clean data
                    clean_data = []
                    for i in range(min_length):
                        if (bz_values[i] is not None and bt_values[i] is not None and 
                            speed_values[i] is not None and density_values[i] is not None):
                            
                            # Calculate time in hours from first timestamp
                            time_hours = (times[i] - times[0]).total_seconds() / 3600
                            
                            # Generate temperature based on speed (realistic correlation)
                            temperature = 50000 + speed_values[i] * 100 + np.random.normal(0, 15000)
                            temperature = max(10000, abs(temperature))  # Ensure realistic temperature
                            
                            # Determine storm level based on Bz
                            if bz_values[i] < -10:
                                storm_level = 'Major'
                            elif bz_values[i] < -5:
                                storm_level = 'Minor'
                            else:
                                storm_level = 'Normal'
                            
                            clean_data.append({
                                'Time_Hours': time_hours,
                                'Bz_nT': bz_values[i],
                                'Bt_nT': bt_values[i],
                                'Speed_kmps': speed_values[i],
                                'Density_pcm3': density_values[i],
                                'Temperature_K': temperature,
                                'Storm_Level': storm_level
                            })
                    
                    if len(clean_data) > 10:  # Need sufficient clean data points
                        df = pd.DataFrame(clean_data)
                        self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Using real solar wind data for analysis..."))
                    
            except Exception as e:
                print(f"Could not fetch real data: {e}")
                df = None
            
            # Fall back to sample data if real data is not available
            if df is None or len(df) < 10:
                self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Using sample data for analysis (real data unavailable)..."))
                
                # Create sample dataset
                np.random.seed(42)  # For reproducible results
                n_points = 100
                
                # Generate correlated solar wind data
                time_hours = np.arange(n_points)
                bz_base = np.sin(time_hours * 0.1) * 5 + np.random.normal(0, 2, n_points)
                bt_base = np.abs(bz_base) + np.random.normal(8, 2, n_points)
                speed_base = 400 + bz_base * 10 + np.random.normal(0, 50, n_points)
                density_base = 5 + np.abs(bz_base) * 0.5 + np.random.normal(0, 1, n_points)
                # Add temperature data (typical proton temperature range: 10,000 - 100,000 K)
                temperature_base = 50000 + speed_base * 100 + np.random.normal(0, 15000, n_points)
                temperature_base = np.abs(temperature_base)  # Ensure positive temperatures
                
                # Create DataFrame
                df = pd.DataFrame({
                    'Time_Hours': time_hours,
                    'Bz_nT': bz_base,
                    'Bt_nT': bt_base,
                    'Speed_kmps': speed_base,
                    'Density_pcm3': density_base,
                    'Temperature_K': temperature_base,
                    'Storm_Level': ['Major' if bz < -10 else 'Minor' if bz < -5 else 'Normal' for bz in bz_base]
                })
            
            # Update UI in main thread
            self.root.after(0, lambda: self._create_seaborn_plots(df, plot_type))
            
        except Exception as e:
            error_msg = f"Error generating Seaborn plots: {str(e)}"
            self.root.after(0, lambda: self.seaborn_status_label.config(text=f"❌ {error_msg}"))
            import traceback
            traceback.print_exc()
        
        finally:
            self.root.after(0, lambda: self.seaborn_generate_btn.config(state=tk.NORMAL))
    
    def _generate_combined_plots_worker(self):
        """Generate both Seaborn and Plotly plots in background thread."""
        try:
            import seaborn as sns
            import matplotlib.pyplot as plt
            import pandas as pd
            import numpy as np
            from datetime import datetime, timedelta
            import urllib.request
            import json
            
            # Get plot type
            plot_type = self.seaborn_plot_type_var.get()
            
            self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Fetching real solar wind data for analysis..."))
            
            # Try to fetch real solar wind data first
            df = None
            times = []
            bz_values = []
            bt_values = []
            speed_values = []
            density_values = []
            
            try:
                # Get time range
                time_range = self.rtsw_time_range_var.get()
                hours_map = {"6 hours": 6, "12 hours": 12, "24 hours": 24, "3 days": 72, "7 days": 168}
                hours = hours_map.get(time_range, 24)
                
                # Fetch magnetic field data
                mag_url = "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json"
                
                with urllib.request.urlopen(mag_url, timeout=15) as response:
                    mag_data = json.loads(response.read().decode())
                
                # Process magnetic field data
                times, bz_values, bt_values = self._process_mag_data(mag_data, hours)
                
                # Try to fetch plasma data
                plasma_url = "https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json"
                
                try:
                    with urllib.request.urlopen(plasma_url, timeout=15) as response:
                        plasma_data = json.loads(response.read().decode())
                    
                    _, speed_values, density_values = self._process_plasma_data(plasma_data, hours)
                    
                except Exception as e:
                    print(f"Plasma data not available: {e}")
                    # Create placeholder data if plasma data is not available
                    speed_values = [400 + np.random.normal(0, 50) for _ in times]
                    density_values = [5 + np.random.normal(0, 1) for _ in times]
                
                # Create DataFrame from real data
                if times and len(times) > 10:  # Need sufficient data points
                    # Ensure all arrays have the same length
                    min_length = min(len(times), len(bz_values), len(bt_values), len(speed_values), len(density_values))
                    
                    # Filter out None values and create clean data
                    clean_data = []
                    for i in range(min_length):
                        if (bz_values[i] is not None and bt_values[i] is not None and 
                            speed_values[i] is not None and density_values[i] is not None):
                            
                            # Calculate time in hours from first timestamp
                            time_hours = (times[i] - times[0]).total_seconds() / 3600
                            
                            # Generate temperature based on speed (realistic correlation)
                            temperature = 50000 + speed_values[i] * 100 + np.random.normal(0, 15000)
                            temperature = max(10000, abs(temperature))  # Ensure realistic temperature
                            
                            # Determine storm level based on Bz
                            if bz_values[i] < -10:
                                storm_level = 'Major'
                            elif bz_values[i] < -5:
                                storm_level = 'Minor'
                            else:
                                storm_level = 'Normal'
                            
                            clean_data.append({
                                'Time_Hours': time_hours,
                                'Bz_nT': bz_values[i],
                                'Bt_nT': bt_values[i],
                                'Speed_kmps': speed_values[i],
                                'Density_pcm3': density_values[i],
                                'Temperature_K': temperature,
                                'Storm_Level': storm_level
                            })
                    
                    if len(clean_data) > 10:  # Need sufficient clean data points
                        df = pd.DataFrame(clean_data)
                        self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Using real solar wind data for analysis..."))
                    
            except Exception as e:
                print(f"Could not fetch real data: {e}")
                df = None
            
            # Fall back to sample data if real data is not available
            if df is None or len(df) < 10:
                self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Using sample data for analysis (real data unavailable)..."))
                
                # Create sample dataset
                np.random.seed(42)  # For reproducible results
                n_points = 100
                
                # Generate correlated solar wind data
                time_hours = np.arange(n_points)
                bz_base = np.sin(time_hours * 0.1) * 5 + np.random.normal(0, 2, n_points)
                bt_base = np.abs(bz_base) + np.random.normal(8, 2, n_points)
                speed_base = 400 + bz_base * 10 + np.random.normal(0, 50, n_points)
                density_base = 5 + np.abs(bz_base) * 0.5 + np.random.normal(0, 1, n_points)
                # Add temperature data (typical proton temperature range: 10,000 - 100,000 K)
                temperature_base = 50000 + speed_base * 100 + np.random.normal(0, 15000, n_points)
                temperature_base = np.abs(temperature_base)  # Ensure positive temperatures
                
                # Create DataFrame
                df = pd.DataFrame({
                    'Time_Hours': time_hours,
                    'Bz_nT': bz_base,
                    'Bt_nT': bt_base,
                    'Speed_kmps': speed_base,
                    'Density_pcm3': density_base,
                    'Temperature_K': temperature_base,
                    'Storm_Level': ['Major' if bz < -10 else 'Minor' if bz < -5 else 'Normal' for bz in bz_base]
                })
                
                # Create corresponding time series data for Plotly
                from datetime import datetime, timedelta
                base_time = datetime.now() - timedelta(hours=24)
                times = [base_time + timedelta(hours=h) for h in time_hours]
                bz_values = bz_base.tolist()
                bt_values = bt_base.tolist()
                speed_values = speed_base.tolist()
                density_values = density_base.tolist()
            
            # Update Seaborn plots in main thread
            self.root.after(0, lambda: self.seaborn_status_label.config(text="🎨 Generating Seaborn statistical plots..."))
            self.root.after(0, lambda: self._create_seaborn_plots(df, plot_type))
            
            # Update Plotly plots if available
            if self.plotly_available and times and bz_values and bt_values:
                self.root.after(0, lambda: self.seaborn_status_label.config(text="📊 Updating interactive Plotly plots..."))
                self.root.after(0, lambda: self._update_plot_display(times, bz_values, bt_values, speed_values, density_values))
            
            # Final status update
            self.root.after(0, lambda: self.seaborn_status_label.config(text="✨ Both statistical and interactive plots updated successfully!"))
            
        except Exception as e:
            error_msg = f"Error generating combined plots: {str(e)}"
            self.root.after(0, lambda: self.seaborn_status_label.config(text=f"❌ {error_msg}"))
            import traceback
            traceback.print_exc()
        
        finally:
            self.root.after(0, lambda: self.seaborn_generate_btn.config(state=tk.NORMAL))
    
    def _create_seaborn_plots(self, df, plot_type):
        """Create beautiful Seaborn plots based on the selected type."""
        try:
            import seaborn as sns
            import matplotlib.pyplot as plt
            
            # Clear the figure completely
            self.seaborn_fig.clear()
            
            # Set Seaborn style for beautiful plots
            sns.set_style("darkgrid")
            sns.set_palette("husl")
            
            if plot_type == "correlation":
                # Correlation heatmap
                ax = self.seaborn_fig.add_subplot(1, 1, 1)
                
                # Select numeric columns for correlation
                numeric_cols = ['Bz_nT', 'Bt_nT', 'Speed_kmps', 'Density_pcm3']
                corr_matrix = df[numeric_cols].corr()
                
                # Create beautiful heatmap
                sns.heatmap(corr_matrix, annot=True, cmap='RdYlBu_r', center=0,
                           square=True, linewidths=0.5, cbar_kws={"shrink": .8},
                           fmt='.2f', ax=ax)
                
                ax.set_title('🌟 Solar Wind Parameters Correlation Matrix 🌟', 
                           fontsize=16, fontweight='bold', pad=20)
                ax.set_xlabel('Solar Wind Parameters', fontsize=12, fontweight='bold')
                ax.set_ylabel('Solar Wind Parameters', fontsize=12, fontweight='bold')
                
            elif plot_type == "distribution":
                # Distribution plots
                self.seaborn_fig.subplots_adjust(hspace=0.4)
                
                # Bz distribution
                ax1 = self.seaborn_fig.add_subplot(2, 2, 1)
                sns.histplot(data=df, x='Bz_nT', hue='Storm_Level', kde=True, ax=ax1)
                ax1.set_title('🌌 Bz Component Distribution', fontweight='bold')
                ax1.axvline(x=-5, color='orange', linestyle='--', alpha=0.7, label='Minor Storm')
                ax1.axvline(x=-10, color='red', linestyle='--', alpha=0.7, label='Major Storm')
                
                # Speed distribution
                ax2 = self.seaborn_fig.add_subplot(2, 2, 2)
                sns.histplot(data=df, x='Speed_kmps', kde=True, ax=ax2, color='coral')
                ax2.set_title('💨 Solar Wind Speed Distribution', fontweight='bold')
                ax2.axvline(x=400, color='yellow', linestyle='--', alpha=0.7)
                ax2.axvline(x=600, color='red', linestyle='--', alpha=0.7)
                
                # Bt vs Density scatter
                ax3 = self.seaborn_fig.add_subplot(2, 2, 3)
                sns.scatterplot(data=df, x='Bt_nT', y='Density_pcm3', hue='Storm_Level', 
                              size='Speed_kmps', sizes=(20, 200), ax=ax3)
                ax3.set_title('🧲 Magnetic Field vs Density', fontweight='bold')
                
                # Box plot by storm level
                ax4 = self.seaborn_fig.add_subplot(2, 2, 4)
                sns.boxplot(data=df, x='Storm_Level', y='Speed_kmps', ax=ax4)
                ax4.set_title('📊 Speed by Storm Level', fontweight='bold')
                
            elif plot_type == "time_series":
                # Time series analysis following NOAA Real Time Solar Wind format (5 graphs)
                self.seaborn_fig.subplots_adjust(hspace=0.4, wspace=0.1)
                
                # Graph 1: Bz Component (GSM) - Top graph
                ax1 = self.seaborn_fig.add_subplot(5, 1, 1)
                ax1.plot(df['Time_Hours'], df['Bz_nT'], linewidth=2, color='#0066CC', label='Bz GSM')
                ax1.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
                ax1.axhline(y=-5, color='orange', linestyle='--', alpha=0.7, linewidth=1, label='Minor Storm')
                ax1.axhline(y=-10, color='red', linestyle='--', alpha=0.7, linewidth=1, label='Major Storm')
                ax1.set_title('Interplanetary Magnetic Field Bz Component (GSM)', fontsize=11, fontweight='bold', pad=10)
                ax1.set_ylabel('Bz (nT)', fontweight='bold', fontsize=10)
                ax1.legend(fontsize=8, loc='upper right')
                ax1.grid(True, alpha=0.3)
                ax1.set_facecolor('#f8f9fa')
                ax1.tick_params(axis='x', labelbottom=False)  # Hide x-axis labels except for bottom graph
                
                # Graph 2: Total Magnetic Field (Bt)
                ax2 = self.seaborn_fig.add_subplot(5, 1, 2)
                ax2.plot(df['Time_Hours'], df['Bt_nT'], linewidth=2, color='#009900', label='Bt Total')
                ax2.set_title('Total Magnetic Field Strength', fontsize=11, fontweight='bold', pad=10)
                ax2.set_ylabel('Bt (nT)', fontweight='bold', fontsize=10)
                ax2.legend(fontsize=8, loc='upper right')
                ax2.grid(True, alpha=0.3)
                ax2.set_facecolor('#f8f9fa')
                ax2.tick_params(axis='x', labelbottom=False)
                
                # Graph 3: Solar Wind Speed
                ax3 = self.seaborn_fig.add_subplot(5, 1, 3)
                ax3.plot(df['Time_Hours'], df['Speed_kmps'], linewidth=2, color='#CC6600', label='Speed')
                ax3.axhline(y=400, color='orange', linestyle='--', alpha=0.7, linewidth=1, label='Elevated')
                ax3.axhline(y=600, color='red', linestyle='--', alpha=0.7, linewidth=1, label='High Speed')
                ax3.set_title('Solar Wind Bulk Speed', fontsize=11, fontweight='bold', pad=10)
                ax3.set_ylabel('Speed (km/s)', fontweight='bold', fontsize=10)
                ax3.legend(fontsize=8, loc='upper right')
                ax3.grid(True, alpha=0.3)
                ax3.set_facecolor('#f8f9fa')
                ax3.tick_params(axis='x', labelbottom=False)
                
                # Graph 4: Proton Density
                ax4 = self.seaborn_fig.add_subplot(5, 1, 4)
                ax4.plot(df['Time_Hours'], df['Density_pcm3'], linewidth=2, color='#9900CC', label='Density')
                ax4.set_title('Proton Density', fontsize=11, fontweight='bold', pad=10)
                ax4.set_ylabel('Density (p/cm³)', fontweight='bold', fontsize=10)
                ax4.legend(fontsize=8, loc='upper right')
                ax4.grid(True, alpha=0.3)
                ax4.set_facecolor('#f8f9fa')
                ax4.tick_params(axis='x', labelbottom=False)
                
                # Graph 5: Temperature (new addition following NOAA format)
                ax5 = self.seaborn_fig.add_subplot(5, 1, 5)
                ax5.plot(df['Time_Hours'], df['Temperature_K'], linewidth=2, color='#CC0066', label='Temperature')
                ax5.set_title('Proton Temperature', fontsize=11, fontweight='bold', pad=10)
                ax5.set_xlabel('Time (Hours)', fontweight='bold', fontsize=10)
                ax5.set_ylabel('Temperature (K)', fontweight='bold', fontsize=10)
                ax5.legend(fontsize=8, loc='upper right')
                ax5.grid(True, alpha=0.3)
                ax5.set_facecolor('#f8f9fa')
                
                # Add overall title following NOAA style
                self.seaborn_fig.suptitle('Real Time Solar Wind - NOAA Format (5 Parameter Dashboard)', 
                                        fontsize=14, fontweight='bold', y=0.98)
                
            elif plot_type == "regression":
                # Regression analysis
                self.seaborn_fig.subplots_adjust(hspace=0.4)
                
                # Bz vs Speed regression
                ax1 = self.seaborn_fig.add_subplot(2, 2, 1)
                sns.regplot(data=df, x='Bz_nT', y='Speed_kmps', ax=ax1, 
                           scatter_kws={'alpha':0.6}, line_kws={'color':'red'})
                ax1.set_title('🌌 Bz vs Speed Regression', fontweight='bold')
                
                # Bt vs Density regression
                ax2 = self.seaborn_fig.add_subplot(2, 2, 2)
                sns.regplot(data=df, x='Bt_nT', y='Density_pcm3', ax=ax2,
                           scatter_kws={'alpha':0.6}, line_kws={'color':'green'})
                ax2.set_title('🧲 Bt vs Density Regression', fontweight='bold')
                
                # Residual plot
                ax3 = self.seaborn_fig.add_subplot(2, 2, 3)
                sns.residplot(data=df, x='Bz_nT', y='Speed_kmps', ax=ax3)
                ax3.set_title('📈 Residual Analysis', fontweight='bold')
                
                # Joint plot in subplot
                ax4 = self.seaborn_fig.add_subplot(2, 2, 4)
                sns.scatterplot(data=df, x='Speed_kmps', y='Density_pcm3', 
                              hue='Storm_Level', ax=ax4)
                ax4.set_title('💫 Speed vs Density by Storm Level', fontweight='bold')
            
            # Update canvas - force a complete redraw
            self.seaborn_canvas.draw()
            self.seaborn_canvas.flush_events()  # Ensure all drawing events are processed
            
            # Force widget update
            self.seaborn_canvas.get_tk_widget().update_idletasks()
            
            # Update status
            self.seaborn_status_label.config(text=f"✨ Beautiful {plot_type} analysis complete! Statistical insights revealed.")
            
        except Exception as e:
            error_msg = f"Error creating plots: {str(e)}"
            self.seaborn_status_label.config(text=f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
    
    def _create_seaborn_sample_plots(self):
        """Create initial sample Seaborn plots showing time series by default."""
        if not self.seaborn_available:
            return
        
        try:
            import pandas as pd
            import numpy as np
            
            # Create sample time series data
            np.random.seed(42)
            n_points = 100
            time_hours = np.arange(n_points)
            
            # Generate realistic solar wind time series data
            bz_base = np.sin(time_hours * 0.1) * 5 + np.random.normal(0, 2, n_points)
            bt_base = np.abs(bz_base) + np.random.normal(8, 2, n_points)
            speed_base = 400 + bz_base * 10 + np.random.normal(0, 50, n_points)
            density_base = 5 + np.abs(bz_base) * 0.5 + np.random.normal(0, 1, n_points)
            # Add temperature data (typical proton temperature range: 10,000 - 100,000 K)
            temperature_base = 50000 + speed_base * 100 + np.random.normal(0, 15000, n_points)
            temperature_base = np.abs(temperature_base)  # Ensure positive temperatures
            
            df = pd.DataFrame({
                'Time_Hours': time_hours,
                'Bz_nT': bz_base,
                'Bt_nT': bt_base,
                'Speed_kmps': speed_base,
                'Density_pcm3': density_base,
                'Temperature_K': temperature_base,
                'Storm_Level': ['Major' if bz < -10 else 'Minor' if bz < -5 else 'Normal' for bz in bz_base]
            })
            
            # Create initial time series plot (5 graphs following NOAA format)
            self._create_seaborn_plots(df, "time_series")
            
        except Exception as e:
            print(f"Error creating Seaborn sample plots: {e}")
    
    def save_seaborn_analysis(self):
        """Save the current Seaborn analysis plots."""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Save Statistical Analysis"
            )
            if filename:
                self.seaborn_fig.savefig(filename, dpi=300, bbox_inches='tight', 
                                       facecolor='white', edgecolor='none')
                self.seaborn_status_label.config(text=f"💾 Analysis saved: {os.path.basename(filename)}")
        except Exception as e:
            self.seaborn_status_label.config(text=f"❌ Error saving: {str(e)}")
    
    def _process_mag_data(self, data, hours):
        """Process magnetic field data for plotting."""
        from datetime import datetime, timedelta
        
        times = []
        bz_values = []
        bt_values = []
        
        if isinstance(data, list) and len(data) > 1:
            # Skip header row
            data_rows = data[1:]
            
            # Filter data for the requested time range
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for row in data_rows:
                if isinstance(row, list) and len(row) >= 7:
                    try:
                        time_str = row[0]
                        time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
                        
                        if time_obj >= cutoff_time:
                            bz = float(row[3]) if row[3] != '' else None
                            bt = float(row[6]) if row[6] != '' else None
                            
                            times.append(time_obj)
                            bz_values.append(bz)
                            bt_values.append(bt)
                            
                    except (ValueError, IndexError):
                        continue
        
        return times, bz_values, bt_values
    
    def _process_plasma_data(self, data, hours):
        """Process plasma data for plotting."""
        from datetime import datetime, timedelta
        
        times = []
        speed_values = []
        density_values = []
        
        if isinstance(data, list) and len(data) > 1:
            # Skip header row
            data_rows = data[1:]
            
            # Filter data for the requested time range
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for row in data_rows:
                if isinstance(row, list) and len(row) >= 3:
                    try:
                        time_str = row[0]
                        time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
                        
                        if time_obj >= cutoff_time:
                            density = float(row[1]) if row[1] != '' else None
                            speed = float(row[2]) if row[2] != '' else None
                            
                            times.append(time_obj)
                            density_values.append(density)
                            speed_values.append(speed)
                            
                    except (ValueError, IndexError):
                        continue
        
        return times, speed_values, density_values
    
    def _update_plot_display(self, times, bz_values, bt_values, speed_values, density_values):
        """Update the plot display with real data using beautiful Plotly visualization."""
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import numpy as np
            
            # Create subplots with beautiful styling
            self.plotly_fig = make_subplots(
                rows=4, cols=1,
                subplot_titles=(
                    '🌌 Interplanetary Magnetic Field - Bz Component (Real-Time Data)',
                    '🧲 Total Magnetic Field Strength (Real-Time Data)', 
                    '💨 Solar Wind Speed (Real-Time Data)',
                    '⚛️ Proton Density (Real-Time Data)'
                ),
                vertical_spacing=0.08,
                shared_xaxes=True
            )
            
            # Enhanced color scheme for visual impact
            colors = {
                'bz': '#00D4FF',      # Bright cyan
                'bt': '#00FF88',      # Bright green  
                'speed': '#FF6B35',   # Bright orange
                'density': '#FF3366', # Bright pink
                'threshold_minor': '#FFB800',  # Golden yellow
                'threshold_major': '#FF0040',  # Bright red
                'background': '#0A0A0A'        # Dark background
            }
            
            # Plot 1: Bz Component with enhanced styling
            if times and bz_values:
                # Filter out None values
                valid_data = [(t, bz) for t, bz in zip(times, bz_values) if bz is not None]
                if valid_data:
                    plot_times, plot_bz = zip(*valid_data)
                    
                    # Create gradient effect for negative values (storm conditions)
                    bz_colors = [colors['threshold_major'] if bz < -10 else 
                               colors['threshold_minor'] if bz < -5 else 
                               colors['bz'] for bz in plot_bz]
                    
                    self.plotly_fig.add_trace(
                        go.Scatter(
                            x=plot_times, y=plot_bz,
                            mode='lines+markers',
                            name='Bz Component',
                            line=dict(color=colors['bz'], width=4, shape='spline'),
                            marker=dict(size=8, color=bz_colors, symbol='circle', 
                                      line=dict(width=2, color='white')),
                            hovertemplate='<b>Bz:</b> %{y:.2f} nT<br><b>Time:</b> %{x}<br><b>Status:</b> %{text}<extra></extra>',
                            text=[f"{'🚨 Major Storm' if bz < -10 else '⚠️ Minor Storm' if bz < -5 else '✅ Normal'}" for bz in plot_bz]
                        ),
                        row=1, col=1
                    )
            
            # Add enhanced threshold lines for Bz
            self.plotly_fig.add_hline(y=0, line_dash="solid", line_color="white", line_width=2,
                                    annotation_text="Zero Line", annotation_position="bottom right", row=1, col=1)
            self.plotly_fig.add_hline(y=-5, line_dash="dash", line_color=colors['threshold_minor'], line_width=3,
                                    annotation_text="⚠️ Minor Storm (-5 nT)", annotation_position="bottom right", row=1, col=1)
            self.plotly_fig.add_hline(y=-10, line_dash="dash", line_color=colors['threshold_major'], line_width=3,
                                    annotation_text="🚨 Major Storm (-10 nT)", annotation_position="bottom right", row=1, col=1)
            
            # Plot 2: Total Magnetic Field with enhanced styling
            if times and bt_values:
                valid_data = [(t, bt) for t, bt in zip(times, bt_values) if bt is not None]
                if valid_data:
                    plot_times, plot_bt = zip(*valid_data)
                    self.plotly_fig.add_trace(
                        go.Scatter(
                            x=plot_times, y=plot_bt,
                            mode='lines+markers',
                            name='Total Field (Bt)',
                            line=dict(color=colors['bt'], width=4, shape='spline'),
                            marker=dict(size=8, color=colors['bt'], symbol='diamond',
                                      line=dict(width=2, color='white')),
                            hovertemplate='<b>Bt:</b> %{y:.2f} nT<br><b>Time:</b> %{x}<extra></extra>',
                            fill='tonexty' if len(self.plotly_fig.data) > 0 else None,
                            fillcolor='rgba(0, 255, 136, 0.1)'
                        ),
                        row=2, col=1
                    )
            
            # Plot 3: Solar Wind Speed with enhanced styling and thresholds
            if times and speed_values:
                valid_data = [(t, s) for t, s in zip(times, speed_values) if s is not None]
                if valid_data:
                    plot_times, plot_speed = zip(*valid_data)
                    
                    # Color code based on speed thresholds
                    speed_colors = [colors['threshold_major'] if s > 600 else 
                                  colors['threshold_minor'] if s > 400 else 
                                  colors['speed'] for s in plot_speed]
                    
                    self.plotly_fig.add_trace(
                        go.Scatter(
                            x=plot_times, y=plot_speed,
                            mode='lines+markers',
                            name='Solar Wind Speed',
                            line=dict(color=colors['speed'], width=4, shape='spline'),
                            marker=dict(size=8, color=speed_colors, symbol='triangle-up',
                                      line=dict(width=2, color='white')),
                            hovertemplate='<b>Speed:</b> %{y:.1f} km/s<br><b>Time:</b> %{x}<br><b>Status:</b> %{text}<extra></extra>',
                            text=[f"🚀 High Speed" if s > 600 else "⚡ Elevated" if s > 400 else "🌊 Normal" for s in plot_speed]
                        ),
                        row=3, col=1
                    )
                    
                    # Add speed threshold lines
                    self.plotly_fig.add_hline(y=400, line_dash="dash", line_color=colors['threshold_minor'], line_width=3,
                                            annotation_text="⚡ Elevated Speed (400 km/s)", annotation_position="bottom right", row=3, col=1)
                    self.plotly_fig.add_hline(y=600, line_dash="dash", line_color=colors['threshold_major'], line_width=3,
                                            annotation_text="🚀 High Speed (600 km/s)", annotation_position="bottom right", row=3, col=1)
                else:
                    # Add "no data" annotation
                    self.plotly_fig.add_annotation(
                        text="📡 Speed data not available",
                        xref="x domain", yref="y domain",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16, color="white"),
                        row=3, col=1
                    )
            else:
                self.plotly_fig.add_annotation(
                    text="📡 Speed data not available",
                    xref="x domain", yref="y domain", 
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="white"),
                    row=3, col=1
                )
            
            # Plot 4: Proton Density with enhanced styling
            if times and density_values:
                valid_data = [(t, d) for t, d in zip(times, density_values) if d is not None]
                if valid_data:
                    plot_times, plot_density = zip(*valid_data)
                    self.plotly_fig.add_trace(
                        go.Scatter(
                            x=plot_times, y=plot_density,
                            mode='lines+markers',
                            name='Proton Density',
                            line=dict(color=colors['density'], width=4, shape='spline'),
                            marker=dict(size=8, color=colors['density'], symbol='star',
                                      line=dict(width=2, color='white')),
                            hovertemplate='<b>Density:</b> %{y:.2f} p/cm³<br><b>Time:</b> %{x}<extra></extra>',
                            fill='tozeroy',
                            fillcolor='rgba(255, 51, 102, 0.1)'
                        ),
                        row=4, col=1
                    )
                else:
                    self.plotly_fig.add_annotation(
                        text="📡 Density data not available",
                        xref="x domain", yref="y domain",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16, color="white"),
                        row=4, col=1
                    )
            else:
                self.plotly_fig.add_annotation(
                    text="📡 Density data not available",
                    xref="x domain", yref="y domain",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="white"),
                    row=4, col=1
                )
            
            # Update layout for maximum visual impact
            time_range = self.rtsw_time_range_var.get()
            self.plotly_fig.update_layout(
                title=dict(
                    text=f'🌟 Real-Time Solar Wind Monitoring Dashboard - {time_range} 🌟',
                    x=0.5,
                    font=dict(size=24, color='white', family='Arial Black')
                ),
                plot_bgcolor='rgba(10, 10, 10, 0.9)',
                paper_bgcolor='rgba(5, 5, 5, 0.95)',
                font=dict(color='white', size=12, family='Arial'),
                height=900,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(0, 0, 0, 0.7)',
                    bordercolor='white',
                    borderwidth=2
                ),
                margin=dict(l=80, r=80, t=120, b=80),
                annotations=[
                    dict(
                        text="🌍 Data from NOAA Space Weather Prediction Center",
                        showarrow=False,
                        xref="paper", yref="paper",
                        x=0.5, y=-0.1, xanchor='center', yanchor='top',
                        font=dict(size=12, color="lightgray")
                    )
                ]
            )
            
            # Update axes for all subplots with enhanced styling
            for i in range(1, 5):
                self.plotly_fig.update_xaxes(
                    gridcolor='rgba(255, 255, 255, 0.3)',
                    gridwidth=1,
                    showgrid=True,
                    zeroline=False,
                    tickfont=dict(color='white', size=11),
                    linecolor='white',
                    linewidth=2,
                    row=i, col=1
                )
                self.plotly_fig.update_yaxes(
                    gridcolor='rgba(255, 255, 255, 0.3)',
                    gridwidth=1,
                    showgrid=True,
                    zeroline=False,
                    tickfont=dict(color='white', size=11),
                    linecolor='white',
                    linewidth=2,
                    row=i, col=1
                )
            
            # Update y-axis labels with enhanced styling
            self.plotly_fig.update_yaxes(title_text="Bz (nT)", title_font=dict(color='white', size=14), row=1, col=1)
            self.plotly_fig.update_yaxes(title_text="Bt (nT)", title_font=dict(color='white', size=14), row=2, col=1)
            self.plotly_fig.update_yaxes(title_text="Speed (km/s)", title_font=dict(color='white', size=14), row=3, col=1)
            self.plotly_fig.update_yaxes(title_text="Density (p/cm³)", title_font=dict(color='white', size=14), row=4, col=1)
            self.plotly_fig.update_xaxes(title_text="Time (UTC)", title_font=dict(color='white', size=14), row=4, col=1)
            
            # Save the updated plot
            self._save_plotly_to_temp()
            
            # Update status
            data_points = len([t for t in times if t is not None])
            self.rtsw_status_label.config(text=f"🎨 Beautiful plots updated: {data_points} data points ({time_range})")
            self.plot_info_label.config(text="🚀 Real-time data plots ready! Click 'Open Interactive Plots' to explore.")
            
            # Update historical analysis
            self._update_historical_analysis(times, bz_values, bt_values, speed_values, density_values)
            
        except Exception as e:
            self.rtsw_status_label.config(text=f"Plot display error: {str(e)}")
            if hasattr(self, 'plot_info_label'):
                self.plot_info_label.config(text=f"❌ Error updating plots: {str(e)}")
    
    def _show_sample_data_with_error(self, error_msg):
        """Show sample data when real data is not available."""
        self._create_placeholder_plots()
        self.rtsw_status_label.config(text=f"Using beautiful sample data - {error_msg}")
        if hasattr(self, 'plot_info_label'):
            self.plot_info_label.config(text=f"🎨 Sample data displayed - {error_msg}")
    
    def _update_historical_analysis(self, times, bz_values, bt_values, speed_values, density_values):
        """Update the historical analysis section."""
        try:
            import numpy as np
            
            analysis = "Historical Solar Wind Analysis\n"
            analysis += "=" * 40 + "\n"
            analysis += f"Analysis updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            analysis += f"Time range: {self.rtsw_time_range_var.get()}\n\n"
            
            if times and len(times) > 0:
                analysis += f"Data Coverage:\n"
                analysis += f"• Total data points: {len(times)}\n"
                analysis += f"• Time span: {times[0].strftime('%Y-%m-%d %H:%M')} to {times[-1].strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                
                # Analyze Bz component
                valid_bz = [bz for bz in bz_values if bz is not None]
                if valid_bz:
                    bz_avg = np.mean(valid_bz)
                    bz_min = np.min(valid_bz)
                    bz_max = np.max(valid_bz)
                    bz_storm_count = len([bz for bz in valid_bz if bz < -5])
                    bz_major_storm_count = len([bz for bz in valid_bz if bz < -10])
                    
                    analysis += f"Magnetic Field Bz Component:\n"
                    analysis += f"• Average: {bz_avg:.2f} nT\n"
                    analysis += f"• Range: {bz_min:.2f} to {bz_max:.2f} nT\n"
                    analysis += f"• Storm conditions (Bz < -5 nT): {bz_storm_count} measurements\n"
                    analysis += f"• Major storm conditions (Bz < -10 nT): {bz_major_storm_count} measurements\n\n"
                
                # Analyze total magnetic field
                valid_bt = [bt for bt in bt_values if bt is not None]
                if valid_bt:
                    bt_avg = np.mean(valid_bt)
                    bt_min = np.min(valid_bt)
                    bt_max = np.max(valid_bt)
                    
                    analysis += f"Total Magnetic Field (Bt):\n"
                    analysis += f"• Average: {bt_avg:.2f} nT\n"
                    analysis += f"• Range: {bt_min:.2f} to {bt_max:.2f} nT\n\n"
                
                # Analyze solar wind speed if available
                valid_speed = [s for s in speed_values if s is not None]
                if valid_speed:
                    speed_avg = np.mean(valid_speed)
                    speed_min = np.min(valid_speed)
                    speed_max = np.max(valid_speed)
                    high_speed_count = len([s for s in valid_speed if s > 600])
                    
                    analysis += f"Solar Wind Speed:\n"
                    analysis += f"• Average: {speed_avg:.1f} km/s\n"
                    analysis += f"• Range: {speed_min:.1f} to {speed_max:.1f} km/s\n"
                    analysis += f"• High speed events (>600 km/s): {high_speed_count} measurements\n\n"
                else:
                    analysis += f"Solar Wind Speed: Data not available\n\n"
                
                # Analyze proton density if available
                valid_density = [d for d in density_values if d is not None]
                if valid_density:
                    density_avg = np.mean(valid_density)
                    density_min = np.min(valid_density)
                    density_max = np.max(valid_density)
                    
                    analysis += f"Proton Density:\n"
                    analysis += f"• Average: {density_avg:.2f} p/cm³\n"
                    analysis += f"• Range: {density_min:.2f} to {density_max:.2f} p/cm³\n\n"
                else:
                    analysis += f"Proton Density: Data not available\n\n"
                
                # Space weather assessment
                analysis += f"Space Weather Assessment:\n"
                if valid_bz:
                    if bz_major_storm_count > 0:
                        analysis += f"• MAJOR geomagnetic storm conditions detected\n"
                    elif bz_storm_count > 0:
                        analysis += f"• MINOR geomagnetic storm conditions detected\n"
                    else:
                        analysis += f"• Quiet geomagnetic conditions\n"
                
                if valid_speed and speed_max > 600:
                    analysis += f"• High-speed solar wind detected (max: {speed_max:.1f} km/s)\n"
                elif valid_speed and speed_max > 400:
                    analysis += f"• Elevated solar wind speed (max: {speed_max:.1f} km/s)\n"
                
            else:
                analysis += "No data available for analysis.\n"
                analysis += "Click 'Refresh Data' and 'Update Plots' to load current measurements.\n"
            
            # Update the historical analysis text widget
            self.rtsw_history_text.config(state=tk.NORMAL)
            self.rtsw_history_text.delete(1.0, tk.END)
            self.rtsw_history_text.insert(tk.END, analysis)
            self.rtsw_history_text.config(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error updating historical analysis: {e}")
    
    def create_settings_tab(self):
        """Create the settings tab."""
        # Use the pre-created frame
        settings_frame = self.settings_frame
        
        # Create a full-width container that ignores notebook padding
        full_width_container = tk.Frame(settings_frame, bg="#f0f0f0")
        full_width_container.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        
        # Create a scrollable container for all settings content
        # Create canvas and scrollbar for scrolling
        settings_canvas = tk.Canvas(full_width_container, bg="#f0f0f0")
        settings_v_scrollbar = ttk.Scrollbar(full_width_container, orient="vertical", command=settings_canvas.yview)
        settings_scrollable_frame = ttk.Frame(settings_canvas)
        
        # Configure scrolling
        def configure_scroll_region(event=None):
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
        
        settings_scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        settings_canvas.create_window((0, 0), window=settings_scrollable_frame, anchor="nw")
        settings_canvas.configure(yscrollcommand=settings_v_scrollbar.set)
        
        # Make the scrollable frame expand to full canvas width
        def configure_canvas_width(event):
            # Get the canvas width and set the scrollable frame to match
            canvas_width = event.width
            if settings_canvas.find_all():
                settings_canvas.itemconfig(settings_canvas.find_all()[0], width=canvas_width)
        
        settings_canvas.bind('<Configure>', configure_canvas_width)
        
        # Pack canvas and scrollbar to occupy full width
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            settings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel events for different platforms
        settings_canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        settings_canvas.bind("<Button-4>", lambda e: settings_canvas.yview_scroll(-1, "units"))  # Linux scroll up
        settings_canvas.bind("<Button-5>", lambda e: settings_canvas.yview_scroll(1, "units"))   # Linux scroll down
        
        # Make canvas focusable and bind focus events
        settings_canvas.focus_set()
        settings_canvas.bind("<Enter>", lambda e: settings_canvas.focus_set())
        
        # Also bind to the scrollable frame to catch events
        settings_scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        settings_scrollable_frame.bind("<Button-4>", lambda e: settings_canvas.yview_scroll(-1, "units"))
        settings_scrollable_frame.bind("<Button-5>", lambda e: settings_canvas.yview_scroll(1, "units"))
        
        # Enable middle button scrolling (same as scroll bar up/down)
        def _on_settings_middle_button_click(event):
            settings_canvas.yview_scroll(-3, "units")  # Scroll up like scroll bar
        
        settings_canvas.bind("<Button-2>", _on_settings_middle_button_click)
        
        # Now use settings_scrollable_frame instead of settings_frame for all content
        
        # Download settings
        download_settings_frame = ttk.LabelFrame(settings_scrollable_frame, text="Download Settings", padding=10)
        download_settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(download_settings_frame, text="Rate Limit Delay (seconds):").pack(anchor=tk.W)
        self.rate_limit_var = tk.DoubleVar(value=1.0)
        rate_limit_scale = ttk.Scale(download_settings_frame, from_=0.5, to=5.0, 
                                    variable=self.rate_limit_var, orient=tk.HORIZONTAL)
        rate_limit_scale.pack(fill=tk.X, pady=(0, 10))
        
        # Custom keyword search settings
        keyword_settings_frame = ttk.LabelFrame(settings_scrollable_frame, text="Custom Keyword Search", padding=10)
        keyword_settings_frame.pack(fill=tk.X, pady=10)
        
        # Description
        desc_label = ttk.Label(keyword_settings_frame, 
                              text="Customize search keywords for each solar filter. Leave empty to use default filter numbers.",
                              font=("Arial", 9), foreground="gray")
        desc_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Initialize custom keywords dictionary if not exists
        if not hasattr(self, 'custom_keywords'):
            self.custom_keywords = {}
            for filter_num in self.filter_data.keys():
                self.custom_keywords[filter_num] = tk.StringVar(value=filter_num)  # Default to filter number
        
        # Create keyword input fields for each filter with thumbnails
        keyword_grid_frame = ttk.Frame(keyword_settings_frame)
        keyword_grid_frame.pack(fill=tk.BOTH, expand=True)  # Changed to fill both and expand
        
        # Create a scrollable frame for keyword inputs
        keyword_canvas = tk.Canvas(keyword_grid_frame, height=300, bg="#f8f9fa")  # Increased height for thumbnails
        keyword_v_scrollbar = ttk.Scrollbar(keyword_grid_frame, orient="vertical", command=keyword_canvas.yview)
        keyword_scroll_frame = ttk.Frame(keyword_canvas)
        
        keyword_scroll_frame.bind(
            "<Configure>",
            lambda e: keyword_canvas.configure(scrollregion=keyword_canvas.bbox("all"))
        )
        
        keyword_canvas.create_window((0, 0), window=keyword_scroll_frame, anchor="nw")
        keyword_canvas.configure(yscrollcommand=keyword_v_scrollbar.set)
        
        # Make canvas expand to fill width
        def configure_keyword_canvas_width(event):
            canvas_width = event.width
            if keyword_canvas.find_all():
                keyword_canvas.itemconfig(keyword_canvas.find_all()[0], width=canvas_width)
        
        keyword_canvas.bind('<Configure>', configure_keyword_canvas_width)
        
        keyword_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        keyword_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Calculate number of columns based on available space (dynamic layout)
        # We'll use 4 columns for better space utilization
        num_columns = 4
        
        # Create input fields for each filter with thumbnails
        for i, (filter_num, data) in enumerate(self.filter_data.items()):
            row = i // num_columns
            col = i % num_columns
            
            filter_frame = ttk.Frame(keyword_scroll_frame, relief=tk.RIDGE, borderwidth=1)
            filter_frame.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")  # Changed to nsew for full expansion
            
            # Try to load thumbnail image
            thumbnail_image = None
            ui_img_path = Path("src/ui_img")
            for img_file in ui_img_path.glob(f"*_{filter_num}.jpg"):
                try:
                    pil_img = Image.open(img_file)
                    pil_img.thumbnail((50, 50), Image.Resampling.LANCZOS)  # Slightly smaller for 4 columns
                    thumbnail_image = ImageTk.PhotoImage(pil_img)
                    break
                except Exception as e:
                    print(f"Could not load thumbnail for {filter_num}: {e}")
                    continue
            
            # Create thumbnail display
            if thumbnail_image:
                thumbnail_label = tk.Label(filter_frame, image=thumbnail_image, 
                                         bg=data["color"], relief=tk.RAISED, bd=2)
                thumbnail_label.image = thumbnail_image  # Keep reference
                thumbnail_label.pack(pady=(3, 2))
            else:
                # Fallback to colored box if no image
                placeholder_label = tk.Label(filter_frame, text=filter_num, 
                                           bg=data["color"], fg="white", 
                                           font=("Arial", 9, "bold"),
                                           width=6, height=2, relief=tk.RAISED, bd=2)  # Smaller for 4 columns
                placeholder_label.pack(pady=(3, 2))
            
            # Filter label with color
            filter_label = tk.Label(filter_frame, text=f"{data['name']}", 
                                   font=("Arial", 8, "bold"), fg="white", bg=data["color"],
                                   padx=3, pady=1)  # Reduced padding for compact layout
            filter_label.pack(fill=tk.X, pady=(0, 2))
            
            # Filter description
            desc_label = tk.Label(filter_frame, text=data["desc"], 
                                 font=("Arial", 7), fg="gray", wraplength=100,  # Reduced wrap length
                                 justify=tk.CENTER)
            desc_label.pack(pady=(0, 3))
            
            # Keyword input label
            keyword_label = ttk.Label(filter_frame, text=f"Keyword:", 
                                     font=("Arial", 7))  # Shortened label
            keyword_label.pack(anchor=tk.W, padx=3)
            
            # Keyword input
            keyword_entry = ttk.Entry(filter_frame, textvariable=self.custom_keywords[filter_num], 
                                     font=("Arial", 8))  # Removed fixed width to allow expansion
            keyword_entry.pack(fill=tk.X, padx=3, pady=(1, 3))
            
            # Bind change event
            self.custom_keywords[filter_num].trace('w', self.on_keyword_change)
        
        # Configure grid weights for proper spacing and full width utilization
        for col in range(num_columns):
            keyword_scroll_frame.grid_columnconfigure(col, weight=1, uniform="column")  # Added uniform for equal spacing
        
        # Configure row weights to allow vertical expansion if needed
        total_rows = (len(self.filter_data) + num_columns - 1) // num_columns
        for row in range(total_rows):
            keyword_scroll_frame.grid_rowconfigure(row, weight=1)
        
        # Reset and Apply buttons
        keyword_btn_frame = ttk.Frame(keyword_settings_frame)
        keyword_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(keyword_btn_frame, text="🔄 Reset to Defaults", 
                  command=self.reset_keywords_to_default).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(keyword_btn_frame, text="✅ Apply Keywords", 
                  command=self.apply_custom_keywords).pack(side=tk.LEFT)
        
        # Data directory settings
        data_settings_frame = ttk.LabelFrame(settings_scrollable_frame, text="Data Directory", padding=10)
        data_settings_frame.pack(fill=tk.X, pady=5)
        
        current_dir_frame = ttk.Frame(data_settings_frame)
        current_dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(current_dir_frame, text="Current data directory:").pack(anchor=tk.W)
        self.data_dir_label = ttk.Label(current_dir_frame, text=str(self.storage.base_data_dir.absolute()), 
                                       foreground="blue")
        self.data_dir_label.pack(anchor=tk.W, pady=(5, 0))
        
        ttk.Button(data_settings_frame, text="📁 Open Data Folder", 
                  command=self.open_data_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(data_settings_frame, text="🧹 Clean Up Corrupted Files", 
                  command=self.cleanup_files).pack(side=tk.LEFT)
        
        # Credit text
        credit_frame = ttk.Frame(settings_scrollable_frame)
        credit_frame.pack(fill=tk.X, pady=(20, 10))
        
        credit_label = ttk.Label(credit_frame, 
                                text="Created by Andy Kong", 
                                font=("Arial", 9, "italic"), 
                                foreground="gray")
        credit_label.pack(anchor=tk.CENTER)
    
    def create_filter_selection_ui(self, parent_frame):
        """Create the visual filter selection UI that can be reused in multiple tabs."""
        # Create scrollable frame for filter selection
        filter_canvas = tk.Canvas(parent_frame, height=120, bg="#f0f0f0")
        filter_scrollbar = ttk.Scrollbar(parent_frame, orient="horizontal", command=filter_canvas.xview)
        filter_scroll_frame = ttk.Frame(filter_canvas)
        
        filter_scroll_frame.bind(
            "<Configure>",
            lambda e: filter_canvas.configure(scrollregion=filter_canvas.bbox("all"))
        )
        
        filter_canvas.create_window((0, 0), window=filter_scroll_frame, anchor="nw")
        filter_canvas.configure(xscrollcommand=filter_scrollbar.set)
        
        filter_canvas.pack(fill=tk.X, pady=(0, 5))
        filter_scrollbar.pack(fill=tk.X)
        
        # Create visual filter selection buttons
        for i, (filter_num, data) in enumerate(self.filter_data.items()):
            filter_btn_frame = ttk.Frame(filter_scroll_frame)
            filter_btn_frame.grid(row=0, column=i, padx=5, pady=5)
            
            # Try to load preview image
            preview_image = None
            ui_img_path = Path("src/ui_img")
            for img_file in ui_img_path.glob(f"*_{filter_num}.jpg"):
                try:
                    pil_img = Image.open(img_file)
                    pil_img.thumbnail((80, 80), Image.Resampling.LANCZOS)
                    preview_image = ImageTk.PhotoImage(pil_img)
                    break
                except:
                    continue
            
            # Create filter button
            if preview_image:
                filter_btn = tk.Button(filter_btn_frame, image=preview_image, 
                                     command=lambda f=filter_num: self.select_filter(f),
                                     relief=tk.RAISED, bd=2, bg=data["color"], 
                                     activebackground=data["color"])
                filter_btn.image = preview_image  # Keep reference
            else:
                filter_btn = tk.Button(filter_btn_frame, text=filter_num,
                                     command=lambda f=filter_num: self.select_filter(f),
                                     relief=tk.RAISED, bd=2, bg=data["color"],
                                     activebackground=data["color"], width=8, height=4)
            
            filter_btn.pack()
            
            # Filter info
            info_label = ttk.Label(filter_btn_frame, text=data["name"], 
                                 font=("Arial", 8, "bold"), anchor=tk.CENTER)
            info_label.pack()
            
            desc_label = ttk.Label(filter_btn_frame, text=data["desc"], 
                                 font=("Arial", 7), anchor=tk.CENTER, foreground="gray")
            desc_label.pack()
            
            self.filter_buttons[filter_num] = filter_btn
        
        # Update initial selection if not already done
        if not self._filter_initialized:
            # Set the filter without triggering refresh during initialization
            self.solar_filter_var.set("0211")
            
            # Update button appearances
            for fnum, btn in self.filter_buttons.items():
                if fnum == "0211":
                    btn.config(relief=tk.SUNKEN, bd=3)
                else:
                    btn.config(relief=tk.RAISED, bd=2)
            
            self._filter_initialized = True

    def select_filter(self, filter_num):
        """Select a solar filter and update the UI."""
        self.solar_filter_var.set(filter_num)
        
        # Update button appearances
        for fnum, btn in self.filter_buttons.items():
            if fnum == filter_num:
                btn.config(relief=tk.SUNKEN, bd=3)
            else:
                btn.config(relief=tk.RAISED, bd=2)
        
        # Trigger filter change
        self.on_filter_change()
    
    def on_filter_change(self, event=None):
        """Handle changes to resolution or solar filter settings."""
        resolution = self.resolution_var.get()
        solar_filter = self.solar_filter_var.get()
        
        # Get custom keyword if available
        search_keyword = self.get_current_search_keyword()
        
        # Update scraper with new settings (using custom keyword)
        self.scraper.update_filters(resolution, search_keyword)
        
        # Update storage organizer with new pattern (using custom keyword)
        self.storage.update_file_pattern(resolution, search_keyword)
        
        # Refresh available dates to reflect new filter (only if UI is fully initialized)
        if hasattr(self, 'viewer_from_date_combo'):
            self.refresh_available_dates()
    
    def on_keyword_change(self, *args):
        """Handle changes to custom keyword settings."""
        # This method is called when any keyword is modified
        # We don't need to do anything immediately, changes are applied when user clicks Apply
        pass
    
    def reset_keywords_to_default(self):
        """Reset all custom keywords to their default filter numbers."""
        for filter_num in self.filter_data.keys():
            self.custom_keywords[filter_num].set(filter_num)
        
        messagebox.showinfo("Keywords Reset", "All keywords have been reset to default filter numbers.")
    
    def apply_custom_keywords(self):
        """Apply the custom keywords to the search system."""
        try:
            # Get current settings
            resolution = self.resolution_var.get()
            
            # Update the scraper and storage with custom keywords
            # For now, we'll use the currently selected filter's custom keyword
            current_filter = self.solar_filter_var.get()
            custom_keyword = self.custom_keywords[current_filter].get().strip()
            
            if not custom_keyword:
                custom_keyword = current_filter  # Fallback to default
            
            # Update components with custom keyword
            self.scraper.update_filters(resolution, custom_keyword)
            self.storage.update_file_pattern(resolution, custom_keyword)
            
            # Refresh available dates
            if hasattr(self, 'viewer_from_date_combo'):
                self.refresh_available_dates()
            
            messagebox.showinfo("Keywords Applied", 
                              f"Custom keywords applied successfully!\n"
                              f"Current search keyword: '{custom_keyword}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply custom keywords: {str(e)}")
    
    def get_current_search_keyword(self):
        """Get the current search keyword for the selected filter."""
        current_filter = self.solar_filter_var.get()
        if hasattr(self, 'custom_keywords') and current_filter in self.custom_keywords:
            custom_keyword = self.custom_keywords[current_filter].get().strip()
            return custom_keyword if custom_keyword else current_filter
        return current_filter
    
    def check_system_requirements(self, parent_frame):
        """Check and display system requirements."""
        # Check FFmpeg with detailed information
        ffmpeg_status, ffmpeg_details = self._check_ffmpeg_detailed()
        
        ffmpeg_frame = ttk.Frame(parent_frame)
        ffmpeg_frame.pack(fill=tk.X, anchor=tk.W, pady=(0, 5))
        
        ttk.Label(ffmpeg_frame, text=f"FFmpeg: {ffmpeg_status}").pack(anchor=tk.W)
        if ffmpeg_details:
            details_label = ttk.Label(ffmpeg_frame, text=ffmpeg_details, 
                                     font=("Arial", 8), foreground="gray")
            details_label.pack(anchor=tk.W, padx=(20, 0))
        
        # Add FFmpeg installation help if not found
        if "❌" in ffmpeg_status:
            help_frame = ttk.Frame(ffmpeg_frame)
            help_frame.pack(fill=tk.X, anchor=tk.W, padx=(20, 0), pady=(2, 0))
            
            ttk.Button(help_frame, text="📥 Download FFmpeg", 
                      command=self.open_ffmpeg_download).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(help_frame, text="ℹ️ Installation Guide", 
                      command=self.show_ffmpeg_help).pack(side=tk.LEFT)
        
        # Check OpenCV
        try:
            import cv2
            opencv_status = f"✅ Available (v{cv2.__version__})"
        except:
            opencv_status = "❌ Not found"
        
        ttk.Label(parent_frame, text=f"OpenCV: {opencv_status}").pack(anchor=tk.W)
        
        # Check PIL
        try:
            from PIL import Image
            pil_status = f"✅ Available (v{Image.__version__})"
        except:
            pil_status = "❌ Not found"
        
        ttk.Label(parent_frame, text=f"Pillow: {pil_status}").pack(anchor=tk.W)
        
        # Add system information
        import platform
        system_info_frame = ttk.Frame(parent_frame)
        system_info_frame.pack(fill=tk.X, anchor=tk.W, pady=(10, 0))
        
        ttk.Label(system_info_frame, text="System Information:", 
                 font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(system_info_frame, text=f"OS: {platform.system()} {platform.release()}", 
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=(10, 0))
        ttk.Label(system_info_frame, text=f"Python: {platform.python_version()}", 
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=(10, 0))
    
    def _check_ffmpeg_available(self):
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
    
    def _check_ffmpeg_detailed(self):
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
    
    def open_ffmpeg_download(self):
        """Open FFmpeg download page."""
        import webbrowser
        webbrowser.open("https://ffmpeg.org/download.html")
    
    def show_ffmpeg_help(self):
        """Show FFmpeg installation help."""
        help_text = """FFmpeg Installation Guide:

Windows:
1. Download FFmpeg from: https://ffmpeg.org/download.html
2. Extract the files to a folder (e.g., C:\\ffmpeg)
3. Add the bin folder to your system PATH:
   - Open System Properties → Advanced → Environment Variables
   - Edit the PATH variable and add: C:\\ffmpeg\\bin
   - Restart your computer

Alternative (Windows):
- Use Chocolatey: choco install ffmpeg
- Use Scoop: scoop install ffmpeg

macOS:
- Use Homebrew: brew install ffmpeg

Linux:
- Ubuntu/Debian: sudo apt install ffmpeg
- CentOS/RHEL: sudo yum install ffmpeg

After installation, restart this application to detect FFmpeg.

Note: FFmpeg is used for high-quality video creation. 
Without it, the application will use OpenCV as a fallback."""
        
        messagebox.showinfo("FFmpeg Installation Guide", help_text)
    
    def _create_video_with_ffmpeg(self, image_paths, output_path, fps, progress_callback=None, status_callback=None):
        """Create video using FFmpeg."""
        temp_dir = Path("temp_video_frames")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Create sequential frame files
            total_images = len(image_paths)
            for i, src_path in enumerate(image_paths):
                if progress_callback:
                    progress = 20 + (i / total_images) * 50
                    progress_callback(progress)
                if status_callback:
                    status_callback(f"Preparing frame {i+1}/{total_images}...")
                
                temp_path = temp_dir / f"frame_{i:06d}.jpg"
                if temp_path.exists():
                    temp_path.unlink()
                
                try:
                    temp_path.symlink_to(src_path.absolute())
                except OSError:
                    shutil.copy2(src_path, temp_path)
            
            if status_callback:
                status_callback("Running FFmpeg to create video...")
            if progress_callback:
                progress_callback(70)
            
            # Run ffmpeg with web-optimized settings
            input_pattern = str(temp_dir / "frame_%06d.jpg")
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-framerate', str(fps),
                '-i', input_pattern, 
                '-c:v', 'libx264',           # H.264 codec
                '-pix_fmt', 'yuv420p',       # Compatible pixel format
                '-profile:v', 'baseline',    # Baseline profile for maximum compatibility
                '-level', '3.0',             # Level 3.0 for web compatibility
                '-crf', '23',                # Good quality/size balance
                '-preset', 'medium',         # Encoding speed vs compression
                '-movflags', '+faststart',   # Optimize for web streaming
                str(output_path)
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if progress_callback:
                progress_callback(100)
            
            if result.returncode == 0:
                return True, "FFmpeg"
            else:
                return False, f"FFmpeg error: {result.stderr}"
        
        except Exception as e:
            return False, f"FFmpeg exception: {str(e)}"
        
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _create_video_with_opencv(self, image_paths, output_path, fps, progress_callback=None, status_callback=None):
        """Create video using OpenCV as fallback."""
        try:
            import cv2
            
            if status_callback:
                status_callback("Using OpenCV to create video...")
            
            # Read first image to get dimensions
            first_image = cv2.imread(str(image_paths[0]))
            if first_image is None:
                return False, "Could not read first image"
            
            height, width, layers = first_image.shape
            
            # Try different codecs for better compatibility
            codecs_to_try = [
                ('avc1', 'H264/AVC1'),  # Best compatibility
                ('mp4v', 'MP4V'),       # Good compatibility
                ('MJPG', 'MJPEG'),      # Fallback option
            ]
            
            video_writer = None
            used_codec = None
            
            for fourcc_str, codec_name in codecs_to_try:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                    video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
                    
                    if video_writer.isOpened():
                        used_codec = codec_name
                        break
                    else:
                        video_writer.release()
                        video_writer = None
                except:
                    if video_writer:
                        video_writer.release()
                        video_writer = None
                    continue
            
            if video_writer is None or not video_writer.isOpened():
                return False, "Could not open video writer with any codec"
            
            # Add frames to video
            total_images = len(image_paths)
            for i, image_path in enumerate(image_paths):
                if progress_callback:
                    progress = 30 + (i / total_images) * 60
                    progress_callback(progress)
                if status_callback:
                    status_callback(f"Adding frame {i+1}/{total_images} to video")
                
                frame = cv2.imread(str(image_path))
                if frame is not None:
                    # Ensure frame has the correct dimensions
                    if frame.shape[:2] != (height, width):
                        frame = cv2.resize(frame, (width, height))
                    video_writer.write(frame)
                else:
                    print(f"Warning: Could not read image {image_path}")
            
            # Release everything
            video_writer.release()
            cv2.destroyAllWindows()
            
            if progress_callback:
                progress_callback(100)
            
            # Check if file was created successfully
            if output_path.exists() and output_path.stat().st_size > 0:
                return True, f"OpenCV ({used_codec})"
            else:
                return False, "Video file was not created or is empty"
        
        except ImportError:
            return False, "OpenCV not available"
        except Exception as e:
            return False, f"OpenCV error: {str(e)}"
    
    def log_message(self, message):
        """Add message to download log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def set_date_range(self, days_back):
        """Set date range for quick selection."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))
    
    def set_video_date_range(self, days_back):
        """Set video date range for quick selection."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        self.video_start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.video_end_date_var.set(end_date.strftime("%Y-%m-%d"))
    
    def start_download(self):
        """Start the download process in a background thread."""
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Download in Progress", "A download is already in progress!")
            return
        
        # First, check how many images will be downloaded
        try:
            # Parse dates
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format")
            return
        
        # Show scanning message
        self.status_label.config(text="Scanning for available images...")
        self.root.update()
        
        try:
            # Get available images
            available_images = self.scraper.get_available_images_for_date_range(start_date, end_date)
            
            if not available_images:
                messagebox.showinfo("No Images Found", 
                                  f"No images found for date range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n"
                                  f"Resolution: {self.resolution_var.get()}px\n"
                                  f"Filter: {self.solar_filter_var.get()}")
                self.status_label.config(text="No images found")
                return
            
            # Filter new images
            new_images = self.scraper.filter_new_images(available_images, self.storage)
            
            if not new_images:
                messagebox.showinfo("All Images Downloaded", 
                                  f"All {len(available_images)} images are already downloaded!\n\n"
                                  f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
                                  f"Resolution: {self.resolution_var.get()}px\n"
                                  f"Filter: {self.solar_filter_var.get()}")
                self.status_label.config(text="All images up to date")
                return
            
            # Show confirmation dialog with download details
            filter_name = self.filter_data.get(self.solar_filter_var.get(), {}).get('name', self.solar_filter_var.get())
            filter_desc = self.filter_data.get(self.solar_filter_var.get(), {}).get('desc', '')
            
            confirmation_message = f"Download Images Confirmation\n\n"
            confirmation_message += f"📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
            confirmation_message += f"🔍 Resolution: {self.resolution_var.get()} pixels\n"
            confirmation_message += f"🌞 Filter: {filter_name}"
            if filter_desc:
                confirmation_message += f" - {filter_desc}"
            confirmation_message += f"\n\n"
            confirmation_message += f"📊 Total available: {len(available_images)} images\n"
            confirmation_message += f"📥 New to download: {len(new_images)} images\n"
            confirmation_message += f"✅ Already downloaded: {len(available_images) - len(new_images)} images\n\n"
            confirmation_message += f"Do you want to proceed with downloading {len(new_images)} new images?"
            
            result = messagebox.askyesno("Confirm Download", confirmation_message)
            
            if not result:
                self.status_label.config(text="Download cancelled")
                return
            
            # User confirmed, proceed with download
            self.download_btn.config(state=tk.DISABLED)
            self.log_text.delete(1.0, tk.END)
            
            self.download_thread = threading.Thread(target=self._download_worker, daemon=True)
            self.download_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error checking images: {str(e)}")
            self.status_label.config(text="Error occurred")
            return
    
    def _download_worker(self):
        """Download worker running in background thread."""
        try:
            # Parse dates
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
            
            self.root.after(0, lambda: self.log_message(f"Starting download for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"))
            self.root.after(0, lambda: self.status_label.config(text="Preparing download..."))
            
            # Get available images (re-scan to ensure consistency)
            available_images = self.scraper.get_available_images_for_date_range(start_date, end_date)
            
            # Filter new images
            new_images = self.scraper.filter_new_images(available_images, self.storage)
            
            self.root.after(0, lambda: self.log_message(f"Downloading {len(new_images)} new images"))
            
            # Create download tasks
            tasks = self.scraper.create_download_tasks(new_images, self.storage)
            
            # Download images
            successful = 0
            failed = 0
            
            for i, task in enumerate(tasks):
                progress = (i / len(tasks)) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                filename = task.target_path.name
                self.root.after(0, lambda f=filename, idx=i+1, total=len(tasks): 
                               self.status_label.config(text=f"Downloading {idx}/{total}: {f}"))
                
                success = self.download_manager.download_and_save(task)
                
                if success:
                    successful += 1
                    self.root.after(0, lambda f=filename: self.log_message(f"✅ Downloaded: {f}"))
                else:
                    failed += 1
                    self.root.after(0, lambda f=filename, err=task.error_message: 
                                   self.log_message(f"❌ Failed: {f} - {err}"))
            
            # Final status
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.log_message(f"Download complete: {successful} successful, {failed} failed"))
            self.root.after(0, lambda: self.status_label.config(text=f"Complete: {successful}/{len(tasks)} downloaded"))
            self.root.after(0, self.refresh_available_dates)
        
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Error: {str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="Download failed"))
        
        finally:
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.download_all_filters_btn.config(state=tk.NORMAL))
    
    def start_download_all_filters(self):
        """Start downloading images for all 12 solar filters."""
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Download in Progress", "A download is already in progress!")
            return
        
        # Confirm with user since this will download a lot of images
        result = messagebox.askyesno(
            "Download All Filters", 
            "This will download images for all 12 solar filters for the selected date range.\n"
            "This may take a long time and download many images.\n\n"
            "Do you want to continue?"
        )
        
        if not result:
            return
        
        self.download_btn.config(state=tk.DISABLED)
        self.download_all_filters_btn.config(state=tk.DISABLED)
        self.log_text.delete(1.0, tk.END)
        
        self.download_thread = threading.Thread(target=self._download_all_filters_worker, daemon=True)
        self.download_thread.start()
    
    def _download_all_filters_worker(self):
        """Download worker for all filters running in background thread."""
        try:
            # Parse dates
            start_date = datetime.strptime(self.start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_var.get(), "%Y-%m-%d")
            
            self.root.after(0, lambda: self.log_message(f"Starting download for ALL FILTERS from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"))
            
            # Get all filter keys
            all_filters = list(self.filter_data.keys())
            total_filters = len(all_filters)
            
            self.root.after(0, lambda: self.log_message(f"Will download images for {total_filters} filters: {', '.join(all_filters)}"))
            
            # Store original filter setting
            original_filter = self.solar_filter_var.get()
            
            total_successful = 0
            total_failed = 0
            
            for filter_index, filter_key in enumerate(all_filters):
                filter_name = self.filter_data[filter_key]['name']
                self.root.after(0, lambda f=filter_name, idx=filter_index+1, total=total_filters: 
                               self.log_message(f"\n🔄 Processing filter {idx}/{total}: {f} ({filter_key})"))
                
                # Update filter setting
                self.solar_filter_var.set(filter_key)
                
                # Update components with new filter
                self.scraper.update_filters(self.resolution_var.get(), filter_key)
                self.storage.update_file_pattern(self.resolution_var.get(), filter_key)
                
                # Get available images for this filter
                available_images = self.scraper.get_available_images_for_date_range(start_date, end_date)
                
                if not available_images:
                    self.root.after(0, lambda f=filter_name: self.log_message(f"  ⚠️  No images found for {f}"))
                    continue
                
                # Filter new images
                new_images = self.scraper.filter_new_images(available_images, self.storage)
                
                if not new_images:
                    self.root.after(0, lambda f=filter_name: self.log_message(f"  ✅ All {f} images already downloaded"))
                    continue
                
                self.root.after(0, lambda f=filter_name, count=len(new_images): 
                               self.log_message(f"  📥 Downloading {count} new {f} images"))
                
                # Create download tasks
                tasks = self.scraper.create_download_tasks(new_images, self.storage)
                
                # Download images for this filter
                filter_successful = 0
                filter_failed = 0
                
                for i, task in enumerate(tasks):
                    # Calculate overall progress
                    filter_progress = (i / len(tasks)) * (1 / total_filters)
                    overall_progress = (filter_index / total_filters) * 100 + filter_progress * 100
                    self.root.after(0, lambda p=overall_progress: self.progress_var.set(p))
                    
                    filename = task.target_path.name
                    self.root.after(0, lambda f=filename, idx=i+1, total=len(tasks), fname=filter_name: 
                                   self.status_label.config(text=f"{fname}: Downloading {idx}/{total}: {f}"))
                    
                    success = self.download_manager.download_and_save(task)
                    
                    if success:
                        filter_successful += 1
                        total_successful += 1
                    else:
                        filter_failed += 1
                        total_failed += 1
                        self.root.after(0, lambda f=filename, err=task.error_message: 
                                       self.log_message(f"    ❌ Failed: {f} - {err}"))
                
                # Filter summary
                self.root.after(0, lambda f=filter_name, s=filter_successful, fail=filter_failed: 
                               self.log_message(f"  📊 {f} complete: {s} successful, {fail} failed"))
            
            # Restore original filter setting
            self.solar_filter_var.set(original_filter)
            self.scraper.update_filters(self.resolution_var.get(), original_filter)
            self.storage.update_file_pattern(self.resolution_var.get(), original_filter)
            
            # Final status
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.log_message(f"\n🎉 ALL FILTERS DOWNLOAD COMPLETE!"))
            self.root.after(0, lambda: self.log_message(f"📊 Total: {total_successful} successful, {total_failed} failed"))
            self.root.after(0, lambda: self.status_label.config(text=f"All filters complete: {total_successful} downloaded, {total_failed} failed"))
            self.root.after(0, self.refresh_available_dates)
        
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Error in all filters download: {str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="All filters download failed"))
        
        finally:
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.download_all_filters_btn.config(state=tk.NORMAL))
    
    def refresh_available_dates(self):
        """Refresh the list of available dates."""
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
                        
                        images = list(day_dir.glob(f"*_{self.resolution_var.get()}_{self.solar_filter_var.get()}.jpg"))
                        if images:
                            try:
                                date = datetime(int(year_dir.name), int(month_dir.name), int(day_dir.name))
                                date_str = f"{date.strftime('%Y-%m-%d')} ({len(images)} images)"
                                dates.append((date, date_str))
                            except ValueError:
                                continue
        
        if dates:
            dates.sort(reverse=True)  # Most recent first
            date_strings = [date_str for _, date_str in dates]
            
            # Update all date combo boxes (only viewer tab now has combo boxes)
            if hasattr(self, 'viewer_from_date_combo'):
                self.viewer_from_date_combo['values'] = date_strings
                self.viewer_to_date_combo['values'] = date_strings
                
                if date_strings:
                    self.viewer_from_date_combo.current(len(date_strings) - 1)  # Set to earliest date (last in reverse-sorted list)
                    self.viewer_to_date_combo.current(0)  # Set to latest date (first in reverse-sorted list)
            
            self.available_dates = {date_str: date for date, date_str in dates}
        else:
            if hasattr(self, 'viewer_from_date_combo'):
                self.viewer_from_date_combo['values'] = []
                self.viewer_to_date_combo['values'] = []
            self.available_dates = {}
    
    def load_images_for_viewer(self):
        """Load images for the viewer tab."""
        from_selected = self.viewer_from_date_var.get()
        to_selected = self.viewer_to_date_var.get()
        
        if not from_selected or from_selected not in self.available_dates:
            messagebox.showerror("Error", "Please select a valid 'From' date")
            return
        
        if not to_selected or to_selected not in self.available_dates:
            messagebox.showerror("Error", "Please select a valid 'To' date")
            return
        
        from_date = self.available_dates[from_selected]
        to_date = self.available_dates[to_selected]
        
        # Ensure from_date is not after to_date
        if from_date > to_date:
            from_date, to_date = to_date, from_date
        
        # Load images from all dates in the range
        self.current_images = []
        total_images = 0
        
        # Get all dates in range
        current_date = from_date
        while current_date <= to_date:
            image_files = self.storage.list_local_images(current_date)
            
            if image_files:
                date_path = self.storage.get_date_path(current_date)
                
                for filename in sorted(image_files):
                    image_path = date_path / filename
                    self.current_images.append((image_path, filename, current_date))
                    total_images += 1
            
            current_date += timedelta(days=1)
        
        if not self.current_images:
            messagebox.showerror("Error", f"No images found for date range {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
            return
        
        # Sort all images by filename (which includes timestamp)
        self.current_images.sort(key=lambda x: x[1])
        
        self.current_image_index = 0
        self.update_image_display()
        
        date_range_text = f"{from_date.strftime('%Y-%m-%d')}" if from_date == to_date else f"{from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}"
        self.image_info_label.config(text=f"Loaded {total_images} images for {date_range_text}")
    
    def update_image_display(self):
        """Update the image display in viewer tab."""
        if not self.current_images:
            return
        
        # Handle both old format (path, filename) and new format (path, filename, date)
        current_item = self.current_images[self.current_image_index]
        if len(current_item) == 3:
            image_path, filename, image_date = current_item
        else:
            image_path, filename = current_item
            image_date = None
        
        try:
            # Load and resize image
            pil_image = Image.open(image_path)
            
            # Calculate size to fit in display area
            display_size = (600, 600)
            pil_image.thumbnail(display_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update display
            self.image_display_label.config(image=photo, text="")
            self.image_display_label.image = photo  # Keep reference
            
            # Update progress and info
            progress = (self.current_image_index + 1) / len(self.current_images) * 100
            self.image_progress_var.set(progress)
            
            # Extract timestamp
            timestamp = filename.split('_')[1] if '_' in filename else "Unknown"
            if len(timestamp) == 6:
                formatted_time = f"{timestamp[:2]}:{timestamp[2:4]}:{timestamp[4:6]}"
            else:
                formatted_time = timestamp
            
            # Include date in info if available
            if image_date:
                info_text = f"Image {self.current_image_index + 1}/{len(self.current_images)} - {image_date.strftime('%Y-%m-%d')} Time: {formatted_time}"
            else:
                info_text = f"Image {self.current_image_index + 1}/{len(self.current_images)} - Time: {formatted_time}"
            self.image_info_label.config(text=info_text)
            
            # Update speed display
            speed = self.speed_var.get()
            self.speed_display.config(text=f"{speed:.1f} FPS")
        
        except Exception as e:
            self.image_display_label.config(text=f"Error loading image: {e}")
    
    def update_speed_display(self, value=None):
        """Update the speed display when slider changes."""
        speed = self.speed_var.get()
        self.speed_display.config(text=f"{speed:.1f} FPS")
    
    def first_image(self):
        """Go to first image."""
        if self.current_images:
            self.current_image_index = 0
            self.update_image_display()
    
    def prev_image(self):
        """Go to previous image."""
        if self.current_images and self.current_image_index > 0:
            self.current_image_index -= 1
            self.update_image_display()
    
    def next_image(self):
        """Go to next image."""
        if self.current_images and self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.update_image_display()
    
    def last_image(self):
        """Go to last image."""
        if self.current_images:
            self.current_image_index = len(self.current_images) - 1
            self.update_image_display()
    
    def toggle_play(self):
        """Toggle play/pause for image sequence."""
        if self.is_playing:
            self.stop_play()
        else:
            self.start_play()
    
    def start_play(self):
        """Start playing image sequence."""
        if not self.current_images:
            messagebox.showwarning("No Images", "Please load images first")
            return
        
        self.is_playing = True
        self.play_btn.config(text="⏸ Pause")
        
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
    
    def stop_play(self):
        """Stop playing image sequence."""
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
    
    def _play_loop(self):
        """Play loop for image sequence."""
        while self.is_playing and self.current_images:
            if self.current_image_index >= len(self.current_images) - 1:
                self.current_image_index = 0  # Loop back
            else:
                self.current_image_index += 1
            
            self.root.after(0, self.update_image_display)
            
            # Wait based on FPS
            fps = self.speed_var.get()
            delay = 1.0 / fps
            
            import time
            time.sleep(delay)
    
    def create_date_range_video(self):
        """Create video for selected date range."""
        try:
            # Parse dates
            start_date = datetime.strptime(self.video_start_date_var.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.video_end_date_var.get(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format")
            return
        
        if start_date > end_date:
            messagebox.showerror("Invalid Date Range", "Start date must be before or equal to end date")
            return
        
        fps = self.video_fps_var.get()
        
        # Clear video player before creating new video to avoid file conflicts
        self.clear_video_player()
        
        # Create video in background thread (FFmpeg check moved to worker)
        threading.Thread(target=self._create_date_range_video_worker, args=(start_date, end_date, fps), daemon=True).start()
    
    def _create_date_range_video_worker(self, start_date, end_date, fps):
        """Create video for date range in background thread."""
        try:
            # Reset progress bar
            self.root.after(0, lambda: self.video_progress_var.set(0))
            self.root.after(0, lambda: self.video_status_label.config(text="Initializing video creation..."))
            
            # Create video directory if it doesn't exist
            video_dir = Path("video")
            video_dir.mkdir(exist_ok=True)
            
            # Generate output filename with date range, resolution, and solar filter
            current_filter = self.solar_filter_var.get()
            current_resolution = self.resolution_var.get()
            filter_name = current_filter.replace('+', '_')  # Replace + with _ for filename compatibility
            
            if start_date == end_date:
                output_file = f"nasa_solar_{start_date.strftime('%Y%m%d')}_{current_resolution}_{filter_name}.mp4"
            else:
                output_file = f"nasa_solar_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_{current_resolution}_{filter_name}.mp4"
            
            output_path = video_dir / output_file
            
            date_range_text = f"{start_date.strftime('%Y-%m-%d')}" if start_date == end_date else f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            
            # Update progress: 10%
            self.root.after(0, lambda: self.video_progress_var.set(10))
            self.root.after(0, lambda: self.video_status_label.config(text="Collecting images..."))
            
            # Collect all images from the date range
            all_image_paths = []
            current_date = start_date
            
            while current_date <= end_date:
                images = self.storage.list_local_images(current_date)
                if images:
                    date_path = self.storage.get_date_path(current_date)
                    
                    # Add all images from this date
                    for filename in sorted(images):
                        image_path = date_path / filename
                        if image_path.exists():
                            all_image_paths.append(image_path)
                
                current_date += timedelta(days=1)
            
            if not all_image_paths:
                self.root.after(0, lambda: self.video_status_label.config(text="No images found"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"No images found for date range {date_range_text}"))
                return
            
            # Update progress: 20%
            self.root.after(0, lambda: self.video_progress_var.set(20))
            self.root.after(0, lambda: self.video_status_label.config(text=f"Found {len(all_image_paths)} images. Creating video..."))
            
            # Try FFmpeg first, then fall back to OpenCV
            success = False
            message = ""
            
            # Method 1: Try FFmpeg
            if self._check_ffmpeg_available():
                success, message = self._create_video_with_ffmpeg(
                    all_image_paths, output_path, fps,
                    progress_callback=lambda p: self.root.after(0, lambda: self.video_progress_var.set(p)),
                    status_callback=lambda s: self.root.after(0, lambda: self.video_status_label.config(text=s))
                )
            
            # Method 2: Fall back to OpenCV if FFmpeg failed
            if not success:
                self.root.after(0, lambda: self.video_status_label.config(text="FFmpeg not available, using OpenCV..."))
                success, message = self._create_video_with_opencv(
                    all_image_paths, output_path, fps,
                    progress_callback=lambda p: self.root.after(0, lambda: self.video_progress_var.set(p)),
                    status_callback=lambda s: self.root.after(0, lambda: self.video_status_label.config(text=s))
                )
            
            if success:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                duration = len(all_image_paths) / fps
                
                final_message = f"Video created successfully!\n\n"
                final_message += f"File: {output_path.name}\n"
                final_message += f"Size: {size_mb:.1f} MB\n"
                final_message += f"Total frames: {len(all_image_paths)}\n"
                final_message += f"Duration: {duration:.1f} seconds\n"
                final_message += f"Date range: {date_range_text}\n"
                final_message += f"Method: {message}"
                
                # Auto-load the newly created video in the player
                self.root.after(0, lambda: self.auto_load_created_video(str(output_path)))
                self.root.after(0, lambda: self.video_status_label.config(text="Video created successfully!"))
                self.root.after(0, lambda: messagebox.showinfo("Success", final_message))
            else:
                self.root.after(0, lambda: self.video_status_label.config(text="Video creation failed"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Video creation failed: {message}"))
        
        except Exception as e:
            self.root.after(0, lambda: self.video_status_label.config(text="Video creation failed"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Video creation failed: {str(e)}"))

    def create_single_video(self):
        """Create video for selected date."""
        selected = self.video_date_var.get()
        if not selected or selected not in self.available_dates:
            messagebox.showerror("Error", "Please select a valid date")
            return
        
        date = self.available_dates[selected]
        fps = self.video_fps_var.get()
        
        # Clear video player before creating new video to avoid file conflicts
        self.clear_video_player()
        
        # Create video in background thread (FFmpeg check moved to worker)
        threading.Thread(target=self._create_video_worker, args=(date, fps), daemon=True).start()
    
    def _create_video_worker(self, date, fps):
        """Create video in background thread."""
        try:
            # Create video directory if it doesn't exist
            video_dir = Path("video")
            video_dir.mkdir(exist_ok=True)
            
            # Generate output filename with date, resolution, and solar filter
            current_filter = self.solar_filter_var.get()
            current_resolution = self.resolution_var.get()
            filter_name = current_filter.replace('+', '_')  # Replace + with _ for filename compatibility
            
            output_file = f"nasa_solar_{date.strftime('%Y%m%d')}_{current_resolution}_{filter_name}.mp4"
            output_path = video_dir / output_file
            
            # Get images
            images = self.storage.list_local_images(date)
            if not images:
                self.root.after(0, lambda: messagebox.showerror("Error", "No images found for selected date"))
                return
            
            date_path = self.storage.get_date_path(date)
            
            # Collect all image paths
            all_image_paths = []
            for image in sorted(images):
                image_path = date_path / image
                if image_path.exists():
                    all_image_paths.append(image_path)
            
            if not all_image_paths:
                self.root.after(0, lambda: messagebox.showerror("Error", "No valid images found for selected date"))
                return
            
            # Try FFmpeg first, then fall back to OpenCV
            success = False
            message = ""
            
            # Method 1: Try FFmpeg
            if self._check_ffmpeg_available():
                success, message = self._create_video_with_ffmpeg(all_image_paths, output_path, fps)
            
            # Method 2: Fall back to OpenCV if FFmpeg failed
            if not success:
                success, message = self._create_video_with_opencv(all_image_paths, output_path, fps)
            
            if success:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                duration = len(all_image_paths) / fps
                
                final_message = f"Video created successfully!\n\n"
                final_message += f"File: {output_path.name}\n"
                final_message += f"Size: {size_mb:.1f} MB\n"
                final_message += f"Total frames: {len(all_image_paths)}\n"
                final_message += f"Duration: {duration:.1f} seconds\n"
                final_message += f"Date: {date.strftime('%Y-%m-%d')}\n"
                final_message += f"Method: {message}"
                
                # Auto-load the newly created video in the player
                self.root.after(0, lambda: self.auto_load_created_video(str(output_path)))
                self.root.after(0, lambda: messagebox.showinfo("Success", final_message))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Video creation failed: {message}"))
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Video creation failed: {str(e)}"))
    
    def create_all_videos(self):
        """Create one combined video with all images from all dates."""
        if not self.available_dates:
            messagebox.showwarning("No Data", "No downloaded images found")
            return
        
        fps = self.video_fps_var.get()
        
        # Count total images
        total_images = 0
        for date_str, date in self.available_dates.items():
            images = self.storage.list_local_images(date)
            total_images += len(images)
        
        result = messagebox.askyesno("Create Combined Video", 
                                   f"Create one combined video with images from all {len(self.available_dates)} dates?\n"
                                   f"Total images: {total_images}\n"
                                   f"Estimated duration: ~{total_images/fps:.1f} seconds\n"
                                   f"This may take a long time.")
        if not result:
            return
        
        # Clear video player before creating new video to avoid file conflicts
        self.clear_video_player()
        
        threading.Thread(target=self._create_combined_video_worker, args=(fps,), daemon=True).start()
    
    def _create_combined_video_worker(self, fps):
        """Create combined video in background thread."""
        try:
            # Reset progress bar
            self.root.after(0, lambda: self.video_progress_var.set(0))
            self.root.after(0, lambda: self.video_status_label.config(text="Initializing combined video creation..."))
            
            # Create video directory if it doesn't exist
            video_dir = Path("video")
            video_dir.mkdir(exist_ok=True)
            
            # Generate output filename with date range, resolution, and solar filter
            dates = sorted(self.available_dates.values())
            start_date = dates[0]
            end_date = dates[-1]
            
            # Get current solar filter and resolution for filename
            current_filter = self.solar_filter_var.get()
            current_resolution = self.resolution_var.get()
            filter_name = current_filter.replace('+', '_')  # Replace + with _ for filename compatibility
            
            if start_date == end_date:
                output_file = f"nasa_solar_combined_{start_date.strftime('%Y%m%d')}_{current_resolution}_{filter_name}.mp4"
            else:
                output_file = f"nasa_solar_combined_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_{current_resolution}_{filter_name}.mp4"
            
            output_path = video_dir / output_file
            
            # Update progress: 10%
            self.root.after(0, lambda: self.video_progress_var.set(10))
            self.root.after(0, lambda: self.video_status_label.config(text="Collecting images from all dates..."))
            
            # Collect all images from all dates
            all_image_paths = []
            
            for date in sorted(self.available_dates.values()):
                images = self.storage.list_local_images(date)
                if images:
                    date_path = self.storage.get_date_path(date)
                    
                    # Add all images from this date
                    for filename in sorted(images):
                        image_path = date_path / filename
                        if image_path.exists():
                            all_image_paths.append(image_path)
            
            if not all_image_paths:
                self.root.after(0, lambda: self.video_status_label.config(text="No images found"))
                self.root.after(0, lambda: messagebox.showerror("Error", "No images found"))
                return
            
            # Update progress: 20%
            self.root.after(0, lambda: self.video_progress_var.set(20))
            self.root.after(0, lambda: self.video_status_label.config(text=f"Found {len(all_image_paths)} images. Creating video..."))
            
            # Try FFmpeg first, then fall back to OpenCV
            success = False
            message = ""
            
            # Method 1: Try FFmpeg
            if self._check_ffmpeg_available():
                success, message = self._create_video_with_ffmpeg(
                    all_image_paths, output_path, fps,
                    progress_callback=lambda p: self.root.after(0, lambda: self.video_progress_var.set(p)),
                    status_callback=lambda s: self.root.after(0, lambda: self.video_status_label.config(text=s))
                )
            
            # Method 2: Fall back to OpenCV if FFmpeg failed
            if not success:
                self.root.after(0, lambda: self.video_status_label.config(text="FFmpeg not available, using OpenCV..."))
                success, message = self._create_video_with_opencv(
                    all_image_paths, output_path, fps,
                    progress_callback=lambda p: self.root.after(0, lambda: self.video_progress_var.set(p)),
                    status_callback=lambda s: self.root.after(0, lambda: self.video_status_label.config(text=s))
                )
            
            if success:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                duration = len(all_image_paths) / fps
                
                final_message = f"Combined video created successfully!\n\n"
                final_message += f"File: {output_path.name}\n"
                final_message += f"Size: {size_mb:.1f} MB\n"
                final_message += f"Total frames: {len(all_image_paths)}\n"
                final_message += f"Duration: {duration:.1f} seconds\n"
                final_message += f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
                final_message += f"Method: {message}"
                
                # Auto-load the newly created video in the player
                self.root.after(0, lambda: self.auto_load_created_video(str(output_path)))
                self.root.after(0, lambda: self.video_status_label.config(text="Combined video created successfully!"))
                self.root.after(0, lambda: messagebox.showinfo("Success", final_message))
            else:
                self.root.after(0, lambda: self.video_status_label.config(text="Combined video creation failed"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Combined video creation failed: {message}"))
        
        except Exception as e:
            self.root.after(0, lambda: self.video_status_label.config(text="Combined video creation failed"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Combined video creation failed: {str(e)}"))
    
    def select_video_file(self):
        """Select MP4 file for playback."""
        video_dir = Path("video")
        initial_dir = str(video_dir) if video_dir.exists() else str(Path.cwd())
        
        file_path = filedialog.askopenfilename(
            title="Select MP4 Video",
            initialdir=initial_dir,
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        
        if file_path:
            # Stop any current video playback
            if self.video_playing:
                self.stop_video()
            
            self.selected_video_path = file_path
            filename = Path(file_path).name
            self.selected_video_label.config(text=f"Selected: {filename}")
            self.video_play_btn.config(state=tk.NORMAL)
            self.fullscreen_btn.config(state=tk.NORMAL)
            
            # Show video info and preview frame
            try:
                cap = cv2.VideoCapture(file_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else 0
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    info_text = f"Selected: {filename}\nDuration: {duration:.1f}s, Size: {width}x{height}, FPS: {fps:.1f}"
                    self.selected_video_label.config(text=info_text)
                    
                    # Get first frame for preview with 1024x1024 display size
                    ret, frame = cap.read()
                    if ret:
                        # Convert BGR to RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        
                        # Use fixed display size of 1024x1024 pixels
                        display_width = 1024
                        display_height = 1024
                        
                        # Calculate the best fit size while maintaining aspect ratio
                        original_width, original_height = pil_image.size
                        aspect_ratio = original_width / original_height
                        
                        # Calculate scaled dimensions to fit within 1024x1024 display area
                        if aspect_ratio > 1.0:
                            # Video is wider - fit to width
                            new_width = display_width
                            new_height = int(display_width / aspect_ratio)
                        else:
                            # Video is taller or square - fit to height
                            new_height = display_height
                            new_width = int(display_height * aspect_ratio)
                        
                        # Resize the preview image maintaining aspect ratio
                        preview_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        preview_photo = ImageTk.PhotoImage(preview_image)
                        
                        # Show preview frame
                        self.video_display_label.config(image=preview_photo, text="")
                        self.video_display_label.image = preview_photo  # Keep reference
                    
                    cap.release()
                else:
                    self.selected_video_label.config(text=f"Selected: {filename} (Could not read video info)")
                    self.video_display_label.config(image="", text="Could not load video preview")
            except Exception as e:
                self.selected_video_label.config(text=f"Selected: {filename}")
                self.video_display_label.config(image="", text=f"Error loading preview: {str(e)}")
    
    def play_video(self):
        """Play the selected MP4 video embedded in the GUI."""
        if not self.selected_video_path:
            messagebox.showwarning("No Video", "Please select a video file first")
            return
        
        if self.video_playing:
            self.stop_video()
            return
        
        try:
            # Open video file with OpenCV
            self.video_cap = cv2.VideoCapture(self.selected_video_path)
            
            if not self.video_cap.isOpened():
                messagebox.showerror("Error", "Could not open video file")
                return
            
            # Get video properties
            fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            self.video_playing = True
            self.video_play_btn.config(text="⏸ Pause")
            
            # Start video playback thread
            self.video_thread = threading.Thread(target=self._video_playback_loop, 
                                                args=(fps,), daemon=True)
            self.video_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not play video: {str(e)}")
    
    def stop_video(self):
        """Stop video playback."""
        self.video_playing = False
        self.video_play_btn.config(text="▶ Play Video")
        
        # Exit fullscreen if active
        if self.fullscreen_mode:
            self.exit_fullscreen()
        
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        
        # Keep the last frame displayed instead of clearing
        # The last frame is already shown in self.video_display_label at 1024x1024
        # So we don't need to clear it - just leave it as is to maintain the size
    
    def clear_video_player(self):
        """Clear/unmount the current video from the player to avoid file conflicts."""
        # Stop any current video playback
        if self.video_playing:
            self.stop_video()
        
        # Clear the selected video
        self.selected_video_path = None
        self.selected_video_label.config(text="No video selected")
        
        # Clear the video display
        self.video_display_label.config(image="", text="Select a video to play")
        self.video_display_label.image = None  # Clear image reference
        
        # Disable video controls
        self.video_play_btn.config(state=tk.DISABLED)
        self.fullscreen_btn.config(state=tk.DISABLED)
        
        # Release video capture if still open
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
    
    def auto_load_created_video(self, video_path):
        """Auto-load a newly created video in the player."""
        try:
            if not Path(video_path).exists():
                return
            
            # Set the video path
            self.selected_video_path = video_path
            filename = Path(video_path).name
            
            # Enable video controls
            self.video_play_btn.config(state=tk.NORMAL)
            self.fullscreen_btn.config(state=tk.NORMAL)
            
            # Show video info and preview frame
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                info_text = f"Auto-loaded: {filename}\nDuration: {duration:.1f}s, Size: {width}x{height}, FPS: {fps:.1f}"
                self.selected_video_label.config(text=info_text)
                
                # Get first frame for preview with 1024x1024 display size
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # Use fixed display size of 1024x1024 pixels
                    display_width = 1024
                    display_height = 1024
                    
                    # Calculate the best fit size while maintaining aspect ratio
                    original_width, original_height = pil_image.size
                    aspect_ratio = original_width / original_height
                    
                    # Calculate scaled dimensions to fit within 1024x1024 display area
                    if aspect_ratio > 1.0:
                        # Video is wider - fit to width
                        new_width = display_width
                        new_height = int(display_width / aspect_ratio)
                    else:
                        # Video is taller or square - fit to height
                        new_height = display_height
                        new_width = int(display_height * aspect_ratio)
                    
                    # Resize the preview image maintaining aspect ratio
                    preview_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    preview_photo = ImageTk.PhotoImage(preview_image)
                    
                    # Show preview frame
                    self.video_display_label.config(image=preview_photo, text="")
                    self.video_display_label.image = preview_photo  # Keep reference
                
                cap.release()
            else:
                self.selected_video_label.config(text=f"Auto-loaded: {filename} (Could not read video info)")
                self.video_display_label.config(image="", text="Could not load video preview")
                
        except Exception as e:
            print(f"Error auto-loading video: {e}")
            self.selected_video_label.config(text=f"Auto-loaded: {Path(video_path).name}")
            self.video_display_label.config(image="", text="Error loading preview")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode for video playback."""
        if not self.selected_video_path:
            messagebox.showwarning("No Video", "Please select a video file first")
            return
        
        if self.fullscreen_mode:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()
    
    def enter_fullscreen(self):
        """Enter fullscreen mode."""
        if self.fullscreen_mode:
            return
        
        self.fullscreen_mode = True
        self.fullscreen_btn.config(text="🔲 Exit Fullscreen")
        
        # Create fullscreen window
        self.fullscreen_window = tk.Toplevel(self.root)
        self.fullscreen_window.title("NASA Solar Video - Fullscreen")
        self.fullscreen_window.configure(bg='black')
        
        # Make it fullscreen
        self.fullscreen_window.attributes('-fullscreen', True)
        self.fullscreen_window.attributes('-topmost', True)
        
        # Create fullscreen video label
        self.fullscreen_video_label = tk.Label(self.fullscreen_window, 
                                             text="Loading video...", 
                                             background="black", foreground="white",
                                             font=("Arial", 24))
        self.fullscreen_video_label.pack(fill=tk.BOTH, expand=True)
        
        # Bind escape key to exit fullscreen
        self.fullscreen_window.bind('<Escape>', lambda e: self.exit_fullscreen())
        self.fullscreen_window.bind('<KeyPress>', lambda e: self.exit_fullscreen() if e.keysym == 'Escape' else None)
        self.fullscreen_window.focus_set()
        
        # Handle window close
        self.fullscreen_window.protocol("WM_DELETE_WINDOW", self.exit_fullscreen)
        
        # Start video if not already playing
        if not self.video_playing:
            self.play_video()
    
    def exit_fullscreen(self):
        """Exit fullscreen mode."""
        if not self.fullscreen_mode:
            return
        
        self.fullscreen_mode = False
        self.fullscreen_btn.config(text="🔳 Fullscreen")
        
        if self.fullscreen_window:
            self.fullscreen_window.destroy()
            self.fullscreen_window = None
            self.fullscreen_video_label = None
    
    def _video_playback_loop(self, fps):
        """Video playback loop running in background thread."""
        frame_delay = 1.0 / fps if fps > 0 else 1.0 / 30  # Default to 30 FPS if unknown
        
        while self.video_playing and self.video_cap:
            ret, frame = self.video_cap.read()
            
            if not ret:
                # End of video, loop back to beginning
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            try:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                pil_image = Image.fromarray(frame_rgb)
                
                # Create different sized images for regular and fullscreen display
                if self.fullscreen_mode and self.fullscreen_window:
                    # Get screen size for fullscreen
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    fullscreen_size = (screen_width, screen_height)
                    
                    # Create fullscreen image
                    fullscreen_image = pil_image.copy()
                    fullscreen_image.thumbnail(fullscreen_size, Image.Resampling.LANCZOS)
                    fullscreen_photo = ImageTk.PhotoImage(fullscreen_image)
                    
                    # Update both displays
                    self.root.after(0, self._update_video_frame, pil_image, fullscreen_photo)
                else:
                    # Regular display only
                    self.root.after(0, self._update_video_frame, pil_image, None)
                
                # Wait for next frame
                import time
                time.sleep(frame_delay)
                
            except Exception as e:
                print(f"Error displaying video frame: {e}")
                break
        
        # Cleanup when done
        self.root.after(0, self._video_playback_finished)
    
    def _update_video_frame(self, pil_image, fullscreen_photo=None):
        """Update video frame in the GUI (called from main thread)."""
        if self.video_playing:
            # Use fixed display size of 1024x1024 pixels
            display_width = 1024
            display_height = 1024
            
            # Calculate the best fit size while maintaining aspect ratio
            original_width, original_height = pil_image.size
            aspect_ratio = original_width / original_height
            
            # Calculate scaled dimensions to fit within 1024x1024 display area
            if aspect_ratio > 1.0:
                # Video is wider - fit to width
                new_width = display_width
                new_height = int(display_width / aspect_ratio)
            else:
                # Video is taller or square - fit to height
                new_height = display_height
                new_width = int(display_height * aspect_ratio)
            
            # Resize the image maintaining aspect ratio
            regular_image = pil_image.copy()
            regular_image = regular_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            regular_photo = ImageTk.PhotoImage(regular_image)
            
            self.video_display_label.config(image=regular_photo, text="")
            self.video_display_label.image = regular_photo  # Keep reference
            
            # Update fullscreen display if active
            if self.fullscreen_mode and self.fullscreen_window and fullscreen_photo:
                try:
                    self.fullscreen_video_label.config(image=fullscreen_photo, text="")
                    self.fullscreen_video_label.image = fullscreen_photo  # Keep reference
                except:
                    pass  # Fullscreen window might have been closed
    
    def _video_playback_finished(self):
        """Called when video playback finishes."""
        self.video_playing = False
        self.video_play_btn.config(text="▶ Play Video")
        
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
    
    def open_video_folder(self):
        """Open the folder containing videos."""
        try:
            video_dir = Path("video")
            video_dir.mkdir(exist_ok=True)  # Create if it doesn't exist
            
            if sys.platform.startswith('win'):
                os.startfile(video_dir)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', str(video_dir)])
            else:
                subprocess.run(['xdg-open', str(video_dir)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open video folder: {str(e)}")
    
    def open_data_folder(self):
        """Open the data folder."""
        try:
            data_dir = self.storage.base_data_dir
            if sys.platform.startswith('win'):
                os.startfile(data_dir)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', str(data_dir)])
            else:
                subprocess.run(['xdg-open', str(data_dir)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open data folder: {str(e)}")
    
    def cleanup_files(self):
        """Clean up corrupted files."""
        result = messagebox.askyesno("Clean Up Files", 
                                   "This will remove corrupted (zero-size) image files.\n"
                                   "Continue?")
        if not result:
            return
        
        total_removed = 0
        data_dir = self.storage.base_data_dir
        
        if data_dir.exists():
            for year_dir in data_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir():
                            continue
                        
                        try:
                            date = datetime(int(year_dir.name), int(month_dir.name), int(day_dir.name))
                            removed = self.storage.cleanup_corrupted_files(date)
                            total_removed += removed
                        except:
                            continue
        
        messagebox.showinfo("Cleanup Complete", f"Removed {total_removed} corrupted files")
        self.refresh_available_dates()
    
    def run(self):
        """Run the GUI application."""
        # Set up cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
    
    def _on_closing(self):
        """Handle application closing."""
        # Exit fullscreen mode
        if self.fullscreen_mode:
            self.exit_fullscreen()
        
        # Stop video playback
        if self.video_playing:
            self.stop_video()
        
        # Stop image playback
        if self.is_playing:
            self.stop_play()
        
        # Close the application
        self.root.destroy()


def main():
    """Main application entry point."""
    if not HAS_GUI:
        return
    
    try:
        # Install required packages if missing
        try:
            import cv2
        except ImportError:
            print("Installing opencv-python...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'opencv-python'])
        
        app = NASADownloaderGUI()
        app.run()
    
    except Exception as e:
        print(f"❌ Error starting GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()