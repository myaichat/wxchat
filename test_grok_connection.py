import json
import requests
from g_ask_grok import ask_grok

def test_grok_tab_connection():
    """Test if we can connect to the Grok tab and get basic info."""
    try:
        # Check if Chrome debugging is available
        response = requests.get("http://localhost:9222/json")
        tabs = response.json()
        
        print("Available Chrome tabs:")
        for i, tab in enumerate(tabs):
            print(f"{i+1}. {tab.get('title', 'No title')} - {tab.get('url', 'No URL')}")
            if "grok.com" in tab.get("url", ""):
                print(f"   ✓ Found Grok tab: {tab['webSocketDebuggerUrl']}")
        
        # Test the ask_grok function
        print("\n" + "="*50)
        print("Testing Grok chat functionality...")
        
        test_question = "Hello! Can you respond with just 'Test successful' to confirm this works?"
        print(f"Sending test question: {test_question}")
        
        response = ask_grok(test_question)
        
        if response:
            print(f"\n✓ SUCCESS! Grok responded:")
            print(f"Response: {response}")
        else:
            print("\n✗ FAILED: No response received")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_grok_tab_connection()
