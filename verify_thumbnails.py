#!/usr/bin/env python3
"""
Verify that all solar filter thumbnails are available, including the new composite filters.
"""

from pathlib import Path
from PIL import Image

print("🖼️  Verifying Solar Filter Thumbnails...")

# Define all filters including the new composite ones
all_filters = {
    "0193": "193 Å - Coronal loops",
    "0304": "304 Å - Chromosphere", 
    "0171": "171 Å - Quiet corona",
    "0211": "211 Å - Active regions",
    "0131": "131 Å - Flaring regions",
    "0335": "335 Å - Active cores",
    "0094": "94 Å - Hot plasma",
    "1600": "1600 Å - Transition region",
    "1700": "1700 Å - Temperature min",
    "094335193": "094+335+193 - Composite: Hot plasma + Active cores + Coronal loops",
    "304211171": "304+211+171 - Composite: Chromosphere + Active regions + Quiet corona", 
    "211193171": "211+193+171 - Composite: Active regions + Coronal loops + Quiet corona"
}

ui_img_path = Path("src/ui_img")
found_thumbnails = 0
missing_thumbnails = 0

print("\n📋 Thumbnail Status:")

for filter_num, description in all_filters.items():
    # Look for thumbnail image
    thumbnail_files = list(ui_img_path.glob(f"*_{filter_num}.jpg"))
    
    if thumbnail_files:
        thumbnail_file = thumbnail_files[0]
        try:
            # Try to open the image to verify it's valid
            with Image.open(thumbnail_file) as img:
                width, height = img.size
                print(f"✅ {filter_num}: {thumbnail_file.name} ({width}x{height})")
                found_thumbnails += 1
        except Exception as e:
            print(f"❌ {filter_num}: {thumbnail_file.name} (corrupted: {e})")
            missing_thumbnails += 1
    else:
        print(f"❌ {filter_num}: No thumbnail found")
        missing_thumbnails += 1

print(f"\n📊 Summary:")
print(f"✅ Found: {found_thumbnails} thumbnails")
print(f"❌ Missing: {missing_thumbnails} thumbnails")
print(f"📈 Total: {len(all_filters)} filters")

if missing_thumbnails == 0:
    print("\n🎉 All solar filter thumbnails are available!")
    print("The GUI will display visual previews for all filters including the new composite ones.")
else:
    print(f"\n⚠️  {missing_thumbnails} thumbnails are missing.")
    print("Missing filters will display as text buttons instead of image previews.")

print("\n🚀 Thumbnail verification completed!")