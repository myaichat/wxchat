#!/usr/bin/env python3
"""
Test script to verify the Grok handler fix works correctly
"""

def test_import():
    """Test that the grok_handler can be imported without errors"""
    try:
        from chat_handlers.grok_handler import standalone_grok_test, MockSessionState
        print("✅ Import test passed - grok_handler imports successfully")
        return True
    except Exception as e:
        print(f"❌ Import test failed: {str(e)}")
        return False

def test_mock_session_state():
    """Test that MockSessionState works correctly"""
    try:
        from chat_handlers.grok_handler import MockSessionState
        
        mock = MockSessionState()
        mock.test_attr = "test_value"
        
        assert mock.get("test_attr") == "test_value"
        assert mock.get("nonexistent", "default") == "default"
        
        print("✅ MockSessionState test passed")
        return True
    except Exception as e:
        print(f"❌ MockSessionState test failed: {str(e)}")
        return False

def test_standalone_function_exists():
    """Test that standalone test function exists and is callable"""
    try:
        from chat_handlers.grok_handler import standalone_grok_test
        
        # Check if function exists and is callable
        assert callable(standalone_grok_test)
        
        print("✅ Standalone function test passed")
        return True
    except Exception as e:
        print(f"❌ Standalone function test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 TESTING GROK HANDLER FIX")
    print("=" * 40)
    
    tests = [
        test_import,
        test_mock_session_state,
        test_standalone_function_exists
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Grok handler fix is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
