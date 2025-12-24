#!/usr/bin/env python3
"""
Test script to verify Seaborn integration for NASA Solar Wind analysis
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import seaborn as sns
    import matplotlib.pyplot as plt
    print("✅ Seaborn and matplotlib imported successfully!")
    
    # Create sample solar wind time series data
    np.random.seed(42)
    n_points = 100
    time_hours = np.arange(n_points)
    
    # Generate realistic solar wind time series data
    bz_base = np.sin(time_hours * 0.1) * 5 + np.random.normal(0, 2, n_points)
    bt_base = np.abs(bz_base) + np.random.normal(8, 2, n_points)
    speed_base = 400 + bz_base * 10 + np.random.normal(0, 50, n_points)
    density_base = 5 + np.abs(bz_base) * 0.5 + np.random.normal(0, 1, n_points)
    
    df = pd.DataFrame({
        'Time_Hours': time_hours,
        'Bz_nT': bz_base,
        'Bt_nT': bt_base,
        'Speed_kmps': speed_base,
        'Density_pcm3': density_base,
        'Storm_Level': ['Major' if bz < -10 else 'Minor' if bz < -5 else 'Normal' for bz in bz_base]
    })
    
    print(f"✅ Created sample dataset with {len(df)} data points")
    print(f"📊 Data columns: {list(df.columns)}")
    
    # Create the 4-graph time series plot
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('🌟 Solar Wind Time Series Analysis - 4 Parameter Dashboard 🌟', 
                fontsize=16, fontweight='bold')
    
    # Graph 1: Bz Component
    ax1.plot(df['Time_Hours'], df['Bz_nT'], linewidth=3, color='#00D4FF', label='Bz Component')
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.7, linewidth=1)
    ax1.axhline(y=-5, color='orange', linestyle='--', alpha=0.8, linewidth=2, label='Minor Storm (-5 nT)')
    ax1.axhline(y=-10, color='red', linestyle='--', alpha=0.8, linewidth=2, label='Major Storm (-10 nT)')
    ax1.set_title('Interplanetary Magnetic Field - Bz Component', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Bz (nT)', fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Graph 2: Total Magnetic Field (Bt)
    ax2.plot(df['Time_Hours'], df['Bt_nT'], linewidth=3, color='#00FF88', label='Total Field (Bt)')
    ax2.fill_between(df['Time_Hours'], df['Bt_nT'], alpha=0.3, color='#00FF88')
    ax2.set_title('Total Magnetic Field Strength', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Bt (nT)', fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Graph 3: Solar Wind Speed
    ax3.plot(df['Time_Hours'], df['Speed_kmps'], linewidth=3, color='#FF6B35', label='Solar Wind Speed')
    ax3.axhline(y=400, color='yellow', linestyle='--', alpha=0.8, linewidth=2, label='Elevated (400 km/s)')
    ax3.axhline(y=600, color='red', linestyle='--', alpha=0.8, linewidth=2, label='High Speed (600 km/s)')
    ax3.set_title('Solar Wind Speed', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Time (Hours)', fontweight='bold')
    ax3.set_ylabel('Speed (km/s)', fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Graph 4: Proton Density
    ax4.plot(df['Time_Hours'], df['Density_pcm3'], linewidth=3, color='#FF3366', label='Proton Density')
    ax4.fill_between(df['Time_Hours'], df['Density_pcm3'], alpha=0.3, color='#FF3366')
    ax4.set_title('Proton Density', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Time (Hours)', fontweight='bold')
    ax4.set_ylabel('Density (p/cm³)', fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the test plot
    output_file = "test_seaborn_time_series.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Test time series plot saved: {output_file}")
    
    # Show statistics
    print("\n📈 Sample Data Statistics:")
    print(f"Bz range: {df['Bz_nT'].min():.2f} to {df['Bz_nT'].max():.2f} nT")
    print(f"Bt range: {df['Bt_nT'].min():.2f} to {df['Bt_nT'].max():.2f} nT")
    print(f"Speed range: {df['Speed_kmps'].min():.1f} to {df['Speed_kmps'].max():.1f} km/s")
    print(f"Density range: {df['Density_pcm3'].min():.2f} to {df['Density_pcm3'].max():.2f} p/cm³")
    
    storm_counts = df['Storm_Level'].value_counts()
    print(f"\n🌩️ Storm Level Distribution:")
    for level, count in storm_counts.items():
        print(f"  {level}: {count} data points ({count/len(df)*100:.1f}%)")
    
    plt.show()
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("💡 Install with: pip install seaborn pandas matplotlib")
except Exception as e:
    print(f"❌ Error creating test plot: {e}")