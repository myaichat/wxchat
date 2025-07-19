#!/usr/bin/env python3
"""
Test script for Grok API implementation
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

def test_grok_api():
    """Test the Grok API connection and streaming"""
    print("🤖 GROK API TEST")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("XAI_API_KEY")
    if not api_key or api_key == "your_xai_api_key_here":
        print("❌ XAI_API_KEY not found or not set in .env file")
        print("📝 Please add your xAI API key to the .env file:")
        print("   XAI_API_KEY=your_actual_api_key_here")
        print("🔗 Get your API key from: https://console.x.ai/")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test question
    question = "What is artificial intelligence?"
    if len(sys.argv) > 1:
        question = sys.argv[1]
    
    print(f"❓ Question: {question}")
    print("=" * 50)
    
    try:
        # Initialize OpenAI client for xAI Grok API
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        
        # Prepare messages for API call
        messages = [
            {"role": "system", "content": "You are Grok, a helpful AI assistant created by xAI. Provide clear, informative, and engaging responses."},
            {"role": "user", "content": question}
        ]
        
        print("🔄 Making API call to Grok...")
        
        # Make streaming API call
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="grok-beta",  # Use the available Grok model
                messages=messages,
                stream=True,
                max_tokens=4000,
                temperature=0.7
            )
            
            print("📤 Streaming response:")
            print("-" * 50)
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    print(content, end='', flush=True)
                    
        except Exception as api_error:
            error_msg = str(api_error)
            print(f"\n❌ Grok API Error: {error_msg}")
            
            if "401" in error_msg or "authentication" in error_msg.lower():
                print("💡 This looks like an authentication error. Please check your XAI_API_KEY.")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                print("💡 Rate limit exceeded. Please try again later.")
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                print("💡 API quota exceeded or billing issue. Please check your xAI account.")
            
            return False
        
        print("\n" + "=" * 50)
        if full_response:
            print(f"✅ SUCCESS! Response length: {len(full_response)} characters")
            return True
        else:
            print("❌ No response received from Grok API")
            return False
            
    except ImportError:
        print("❌ OpenAI library not found. Please install it:")
        print("   pip install openai")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    success = test_grok_api()
    
    if success:
        print("\n🎉 Grok API test completed successfully!")
        print("✅ The API integration is working correctly.")
    else:
        print("\n💥 Grok API test failed!")
        print("❌ Please check your API key and network connection.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
