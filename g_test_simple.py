import websocket
import json
import time
import re

# WebSocket URL from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/26F411DF5B6CF6C6EA8CB688C5E84F5F"

# Initialize WebSocket connection
ws = websocket.create_connection(ws_url)

def send_cdp_command(method, params, command_id):
    command = {"id": command_id, "method": method, "params": params}
    ws.send(json.dumps(command))
    
    while True:
        response = json.loads(ws.recv())
        if 'id' in response and response['id'] == command_id:
            return response
        elif 'method' in response:
            continue

def extract_grok_responses():
    """Extract all text content and find Grok's responses"""
    print("🔍 Extracting all page content to find Grok's responses...")
    
    # Get the entire page HTML
    html_response = send_cdp_command("DOM.getOuterHTML", {"nodeId": 1}, 999)
    
    if 'result' in html_response and 'outerHTML' in html_response['result']:
        html_content = html_response['result']['outerHTML']
        
        # Extract all text content
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        text_content = ' '.join(text_content.split())
        
        print(f"📄 Total page text length: {len(text_content)} characters")
        
        # Look for our message first
        if "Hello, Grok! Please respond with a simple greeting" in text_content:
            print("✅ Found our sent message in the page!")
            
            # Find the position of our message
            our_message_pos = text_content.find("Hello, Grok! Please respond with a simple greeting")
            
            # Get text after our message (potential responses)
            text_after = text_content[our_message_pos + 50:]
            
            print(f"📝 Text after our message (first 500 chars):")
            print(f"'{text_after[:500]}...'")
            
            # Look for response patterns
            response_patterns = [
                r'Hi[^.!?]*[.!?]',
                r'Hello[^.!?]*[.!?]', 
                r'Nice to[^.!?]*[.!?]',
                r'Greetings[^.!?]*[.!?]',
                r'Hey[^.!?]*[.!?]'
            ]
            
            print("\n🎯 SEARCHING FOR GROK RESPONSES:")
            found_responses = []
            
            for pattern in response_patterns:
                matches = re.findall(pattern, text_after[:1000], re.IGNORECASE)
                for match in matches:
                    clean_match = match.strip()
                    if (len(clean_match) > 5 and 
                        "Hello, Grok!" not in clean_match and
                        "How can Grok help" not in clean_match and
                        "DeepSearch" not in clean_match):
                        found_responses.append(clean_match)
            
            if found_responses:
                print(f"\n🎉 FOUND {len(found_responses)} GROK RESPONSE(S):")
                for i, response in enumerate(found_responses, 1):
                    print(f"   Response {i}: '{response}'")
            else:
                print("❌ No clear responses found with patterns")
                
                # Try a broader search
                print("\n🔍 Trying broader search...")
                sentences = re.split(r'[.!?]+', text_after[:2000])
                for sentence in sentences[:10]:
                    sentence = sentence.strip()
                    if (len(sentence) > 10 and 
                        sentence.lower() not in ['how can grok help', 'deepsearch', 'think', 'grok 3'] and
                        "Hello, Grok!" not in sentence):
                        print(f"   Potential response: '{sentence}'")
        else:
            print("❌ Could not find our sent message in the page")
            
            # Search for any greeting-like responses anyway
            print("\n🔍 Searching entire page for greeting responses...")
            greeting_patterns = [
                r'Hi[^.!?]*[.!?]',
                r'Hello[^.!?]*[.!?]',
                r'Nice to[^.!?]*[.!?]'
            ]
            
            for pattern in greeting_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches[:5]:  # Show first 5 matches
                    clean_match = match.strip()
                    if len(clean_match) > 5:
                        print(f"   Found: '{clean_match}'")

# Main execution
print("🚀 SIMPLE GROK RESPONSE EXTRACTOR")
print("=" * 50)

try:
    # Enable DOM
    send_cdp_command("DOM.enable", {}, 1)
    send_cdp_command("DOM.getDocument", {}, 2)
    
    # Extract responses
    extract_grok_responses()
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    ws.close()
    print("\n✅ Script completed!")
