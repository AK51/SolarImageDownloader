#!/usr/bin/env python3
"""
Test script to verify Plotly integration for NASA Solar Wind plots
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    print("✅ Plotly imported successfully!")
    
    # Create sample data
    now = datetime.now()
    times = [now - timedelta(hours=24-i) for i in range(24)]
    
    # Sample data for demonstration
    bz_data = np.random.normal(-2, 5, 24)  # Bz component
    bt_data = np.abs(np.random.normal(8, 3, 24))  # Total field (always positive)
    speed_data = np.random.normal(450, 100, 24)  # Solar wind speed
    density_data = np.abs(np.random.normal(5, 2, 24))  # Proton density
    
    # Create beautiful subplots
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=(
            '🌌 Interplanetary Magnetic Field - Bz Component (Test Data)',
            '🧲 Total Magnetic Field Strength (Test Data)', 
            '💨 Solar Wind Speed (Test Data)',
            '⚛️ Proton Density (Test Data)'
        ),
        vertical_spacing=0.08,
        shared_xaxes=True
    )
    
    # Enhanced color scheme
    colors = {
        'bz': '#00D4FF',      # Bright cyan
        'bt': '#00FF88',      # Bright green
        'speed': '#FF6B35',   # Bright orange
        'density': '#FF3366', # Bright pink
        'threshold_minor': '#FFB800',  # Golden yellow
        'threshold_major': '#FF0040',  # Bright red
    }
    
    # Add traces
    fig.add_trace(
        go.Scatter(
            x=times, y=bz_data,
            mode='lines+markers',
            name='Bz Component',
            line=dict(color=colors['bz'], width=4, shape='spline'),
            marker=dict(size=8, color=colors['bz'], symbol='circle'),
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=times, y=bt_data,
            mode='lines+markers',
            name='Total Field (Bt)',
            line=dict(color=colors['bt'], width=4, shape='spline'),
            marker=dict(size=8, color=colors['bt'], symbol='diamond'),
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=times, y=speed_data,
            mode='lines+markers',
            name='Solar Wind Speed',
            line=dict(color=colors['speed'], width=4, shape='spline'),
            marker=dict(size=8, color=colors['speed'], symbol='triangle-up'),
        ),
        row=3, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=times, y=density_data,
            mode='lines+markers',
            name='Proton Density',
            line=dict(color=colors['density'], width=4, shape='spline'),
            marker=dict(size=8, color=colors['density'], symbol='star'),
        ),
        row=4, col=1
    )
    
    # Update layout for visual impact
    fig.update_layout(
        title=dict(
            text='🌟 NASA Solar Wind Test Dashboard 🌟',
            x=0.5,
            font=dict(size=24, color='white', family='Arial Black')
        ),
        plot_bgcolor='rgba(10, 10, 10, 0.9)',
        paper_bgcolor='rgba(5, 5, 5, 0.95)',
        font=dict(color='white', size=12, family='Arial'),
        height=800,
        showlegend=True,
    )
    
    # Update axes
    for i in range(1, 5):
        fig.update_xaxes(
            gridcolor='rgba(255, 255, 255, 0.3)',
            gridwidth=1,
            showgrid=True,
            tickfont=dict(color='white'),
            row=i, col=1
        )
        fig.update_yaxes(
            gridcolor='rgba(255, 255, 255, 0.3)',
            gridwidth=1,
            showgrid=True,
            tickfont=dict(color='white'),
            row=i, col=1
        )
    
    # Save test plot
    output_file = "test_solar_wind_plots.html"
    pyo.plot(fig, filename=output_file, auto_open=True)
    print(f"✅ Test plot created: {output_file}")
    print("🚀 Opening in browser...")
    
except ImportError as e:
    print(f"❌ Plotly import failed: {e}")
    print("💡 Install with: pip install plotly")
except Exception as e:
    print(f"❌ Error creating test plot: {e}")