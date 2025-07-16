import os
import streamlit as st

def test_openai_connection():
    """Test OpenAI API connection and configuration"""
    print("=== OpenAI API Debug Test ===")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API Key found: {'Yes' if api_key else 'No'}")
    if api_key:
        print(f"API Key starts with: {api_key[:10]}...")
    
    # Try to import OpenAI
    try:
        from openai import OpenAI
        print("✅ OpenAI library imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OpenAI: {e}")
        return False
    
    # Try to create client
    if not api_key:
        print("❌ No API key found - cannot test connection")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client created successfully")
    except Exception as e:
        print(f"❌ Failed to create OpenAI client: {e}")
        return False
    
    # Try a simple API call
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'Hello, this is a test!'"}],
            max_tokens=50
        )
        print("✅ API call successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

if __name__ == "__main__":
    test_openai_connection()
