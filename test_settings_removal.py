#!/usr/bin/env python3
"""
Test script to verify that the System Information box has been removed from Settings tab.
"""

import sys
from pathlib import Path

def test_settings_tab_structure():
    """Test that Settings tab structure is correct after removal."""
    try:
        # Read the nasa_gui.py file to verify the changes
        gui_file = Path("nasa_gui.py")
        if not gui_file.exists():
            print("❌ nasa_gui.py file not found")
            return False
        
        content = gui_file.read_text(encoding='utf-8')
        
        # Check that System Information box is removed
        system_info_patterns = [
            'text="System Information"',
            'ttk.LabelFrame(settings_scrollable_frame, text="System Information"',
            'self.check_system_requirements(info_frame)'
        ]
        
        found_patterns = []
        for pattern in system_info_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        if found_patterns:
            print("❌ System Information box still found in code:")
            for pattern in found_patterns:
                print(f"   - {pattern}")
            return False
        else:
            print("✅ System Information box successfully removed")
        
        # Check that other Settings tab components are still present
        required_components = [
            'text="Download Settings"',
            'text="Custom Keyword Search"',
            'text="Data Directory"',
            'text="Created by Andy Kong"'
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print("❌ Some required Settings tab components are missing:")
            for component in missing_components:
                print(f"   - {component}")
            return False
        else:
            print("✅ All other Settings tab components are present")
        
        # Check that the check_system_requirements method still exists (might be used elsewhere)
        if 'def check_system_requirements(' in content:
            print("✅ check_system_requirements method still exists (for potential future use)")
        else:
            print("ℹ️  check_system_requirements method removed (not needed)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing System Information box removal from Settings tab...")
    print("=" * 70)
    
    success = test_settings_tab_structure()
    
    print("=" * 70)
    if success:
        print("✅ All tests passed! System Information box successfully removed.")
        print("\n📋 Settings Tab Structure (After Removal):")
        print("   ✅ Download Settings")
        print("   ✅ Custom Keyword Search (with thumbnails)")
        print("   ✅ Data Directory")
        print("   ❌ System Information (REMOVED)")
        print("   ✅ Credit text")
        print("\n💡 Benefits:")
        print("   • Cleaner, more focused Settings interface")
        print("   • Reduced clutter in Settings tab")
        print("   • Better user experience")
    else:
        print("❌ Tests failed! Please check the implementation.")
    
    return success

if __name__ == "__main__":
    main()