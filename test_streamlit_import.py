#!/usr/bin/env python3
"""
Test script to verify that dual_model_chat_app.py can be imported without errors
"""

import sys
import os

def test_import():
    """Test importing the main Streamlit app"""
    try:
        print("🧪 Testing import of dual_model_chat_app.py...")
        
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Try to import the main app module
        import dual_model_chat_app
        
        print("✅ Successfully imported dual_model_chat_app.py")
        print("✅ No startup errors detected")
        return True
        
    except Exception as e:
        print(f"❌ Failed to import dual_model_chat_app.py: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🎯 Streamlit App Import Test")
    print("=" * 50)
    
    success = test_import()
    
    if success:
        print("\n🎉 Test passed! The app should start without errors.")
    else:
        print("\n💥 Test failed! There are import/startup issues.")
        sys.exit(1)
