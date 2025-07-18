# Claude Alternatives for Streamlit Compatibility

This document provides alternative solutions to replace the Playwright-based `claude_streaming_chat.py` that doesn't work in Streamlit environments.

## Problem

The original command:
```bash
python '.\chat_handlers\claude_streaming_chat.py' 'how ry?'
```

Uses Playwright to automate a Chrome browser and interact with Claude.ai. This doesn't work in Streamlit because:
- Playwright requires a display/GUI environment
- Streamlit runs in a web server context
- Browser automation conflicts with Streamlit's architecture

## Solutions

### 1. Direct API Client (Recommended)

**File:** `claude_api_alternative.py`

Uses Anthropic's official Claude API directly. This is the most reliable solution.

#### Setup:
1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Set environment variable: `ANTHROPIC_API_KEY=your_key_here`
3. Install required packages: `pip install requests`

#### Usage:
```python
# Simple usage
from claude_api_alternative import ask_claude_simple

response = ask_claude_simple("how ry?", method="api")
print(response)

# Streaming usage
from claude_api_alternative import ask_claude_streaming_simple

for chunk in ask_claude_streaming_simple("how ry?"):
    print(chunk, end='', flush=True)
```

#### Command line usage:
```bash
python claude_api_alternative.py "how ry?"
```

### 2. Streamlit-Compatible Handler

**File:** `streamlit_claude_handler.py`

Provides the same interface as the original but works in Streamlit.

#### Usage in Streamlit:
```python
import streamlit as st
from streamlit_claude_handler import StreamlitClaudeHandler

# Initialize handler
handler = StreamlitClaudeHandler()

# Get user input
question = st.text_input("Ask Claude:")

if st.button("Send"):
    # Streaming response
    response_container = st.empty()
    full_response = ""
    
    for chunk in handler.ask_claude_streaming(question):
        if not chunk.startswith("Error:"):
            full_response += chunk
            response_container.write(full_response)
        else:
            st.error(chunk)
            break
```

#### Drop-in replacement:
```python
# Replace this:
from chat_handlers.claude_streaming_chat import ask_claude

# With this:
from streamlit_claude_handler import ask_claude

# Same API works
response = ask_claude("how ry?")
```

#### Run as Streamlit app:
```bash
streamlit run streamlit_claude_handler.py
```

### 3. Proxy Server Solution

**File:** `claude_proxy_server.py`

Runs a separate Flask server that handles Playwright interactions and exposes HTTP API.

#### Setup:
1. Install Flask: `pip install flask`
2. Start Chrome with debug mode:
   ```bash
   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```

3. Start the proxy server:
   ```bash
   python claude_proxy_server.py --port 8080 --debug-port 9222
   ```

4. Use from Streamlit:
   ```python
   import requests
   
   def ask_claude_proxy(question):
       response = requests.post(
           "http://localhost:8080/ask",
           json={"question": question}
       )
       return response.json().get("response")
   
   # Usage
   answer = ask_claude_proxy("how ry?")
   ```

## Comparison of Solutions

| Solution | Pros | Cons | Best For |
|----------|------|------|----------|
| **API Client** | ✅ Most reliable<br>✅ No browser needed<br>✅ Official API<br>✅ Streaming support | ❌ Requires API key<br>❌ Usage costs | Production apps, reliable service |
| **Streamlit Handler** | ✅ Drop-in replacement<br>✅ Streamlit optimized<br>✅ Same interface | ❌ Requires API key<br>❌ Usage costs | Streamlit apps, easy migration |
| **Proxy Server** | ✅ Uses existing browser<br>✅ No API costs<br>✅ Maintains sessions | ❌ Complex setup<br>❌ Requires Chrome debug<br>❌ Less reliable | Development, testing |

## Quick Start Examples

### Replace Original Command

Instead of:
```bash
python '.\chat_handlers\claude_streaming_chat.py' 'how ry?'
```

Use:
```bash
# Option 1: API Client (requires ANTHROPIC_API_KEY)
python claude_api_alternative.py "how ry?"

# Option 2: Streamlit Handler (requires ANTHROPIC_API_KEY)
python streamlit_claude_handler.py "how ry?"

# Option 3: Proxy Server (requires Chrome debug + proxy server running)
curl -X POST http://localhost:8080/ask -H "Content-Type: application/json" -d '{"question":"how ry?"}'
```

### Streamlit Integration

```python
import streamlit as st

# Option 1: Direct API (recommended)
from claude_api_alternative import ClaudeAPIClient

client = ClaudeAPIClient()
if st.button("Ask Claude"):
    response = client.ask_claude("how ry?")
    st.write(response)

# Option 2: Streamlit Handler
from streamlit_claude_handler import ask_claude

if st.button("Ask Claude"):
    response = ask_claude("how ry?")
    st.write(response)

# Option 3: Proxy Client
import requests

def ask_via_proxy(question):
    try:
        response = requests.post(
            "http://localhost:8080/ask",
            json={"question": question},
            timeout=30
        )
        return response.json().get("response")
    except:
        return "Proxy server not available"

if st.button("Ask Claude"):
    response = ask_via_proxy("how ry?")
    st.write(response)
```

## Environment Setup

### For API Solutions (Options 1 & 2):
```bash
# Install dependencies
pip install requests streamlit

# Set API key
export ANTHROPIC_API_KEY="your_api_key_here"
# Or on Windows:
set ANTHROPIC_API_KEY=your_api_key_here
```

### For Proxy Solution (Option 3):
```bash
# Install dependencies
pip install flask requests playwright

# Start Chrome with debug
chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

# Start proxy server
python claude_proxy_server.py
```

## Troubleshooting

### API Client Issues:
- **"API key not found"**: Set `ANTHROPIC_API_KEY` environment variable
- **"API Error 401"**: Check your API key is valid
- **"API Error 429"**: Rate limit exceeded, wait and retry

### Streamlit Handler Issues:
- **Import errors**: Make sure `streamlit` is installed
- **API errors**: Same as API client issues above

### Proxy Server Issues:
- **"Failed to connect to Chrome"**: Ensure Chrome is running with `--remote-debugging-port=9222`
- **"Connection refused"**: Check if proxy server is running on correct port
- **"Playwright errors"**: Install playwright: `pip install playwright && playwright install`

## Migration Guide

To migrate from the original Playwright solution:

1. **Choose your preferred solution** (API recommended for production)
2. **Update imports**:
   ```python
   # Old
   from chat_handlers.claude_streaming_chat import ask_claude
   
   # New (Option 1)
   from claude_api_alternative import ask_claude_simple as ask_claude
   
   # New (Option 2)
   from streamlit_claude_handler import ask_claude
   ```
3. **Set up authentication** (for API solutions)
4. **Test functionality** with your existing code
5. **Update deployment** to include new dependencies

The new solutions provide the same functionality but are compatible with Streamlit and more reliable than browser automation.
