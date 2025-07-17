# Streaming Server and Client Logging

This document describes the logging functionality added to both the streaming server and ask_chatgpt.py client that creates individual timestamped JSON files for each request/response pair.

## Overview

Both the streaming server and the ask_chatgpt.py client now automatically log every question/answer interaction to individual JSON files in the `logs/` directory. Each conversation is saved with a unique timestamp-based filename to distinguish between different sources.

## Features

- **Individual Log Files**: Each request creates a separate JSON file
- **Source-Specific Filenames**: 
  - Server logs: `server_chat_session_YYYYMMDD_HHMMSS.json`
  - Client logs: `ask_chatgpt_chat_session_YYYYMMDD_HHMMSS.json`
- **Complete Response Logging**: Captures the full response after streaming is complete
- **Error Logging**: Also logs error responses for debugging
- **Automatic Directory Creation**: Creates `logs/` directory if it doesn't exist

## Log File Format

Each log file contains a JSON object with the following structure:

```json
{
  "timestamp": "2025-07-16T21:52:55.026619",
  "question": "What is Python?",
  "answer": "Python is a high-level programming language...",
  "model": "gpt-4o"
}
```

### Fields:
- `timestamp`: ISO format timestamp when the log was created
- `question`: The user's input message
- `answer`: The complete response from the AI model
- `model`: The AI model used (defaults to "gpt-4o")

## Usage

### Starting the Server

```bash
python streaming_server.py
```

The server will start on `http://127.0.0.1:8002` and display:
```
Starting ChatGPT DevTools Proxy server on http://127.0.0.1:8002
Logs will be saved to the 'logs/' directory
```

### Making Requests

#### Via API
```bash
curl -X POST "http://localhost:8002/ask-chatgpt" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello, how are you?"}'
```

#### Via CLI Test
```bash
python streaming_server.py "What is machine learning?"
```

#### Via Test Script
```bash
python test_logging.py
```

## Log File Examples

### Successful Response
```json
{
  "timestamp": "2025-07-16T21:52:55.026619",
  "question": "Tell me about Python programming",
  "answer": "Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991...",
  "model": "gpt-4o"
}
```

### Error Response
```json
{
  "timestamp": "2025-07-16T21:55:12.123456",
  "question": "Invalid request",
  "answer": "Error: WebSocket connection failed",
  "model": "gpt-4o"
}
```

## File Naming Convention

Log files are named using the following pattern:
- `server_chat_session_YYYYMMDD_HHMMSS.json`
- Example: `server_chat_session_20250716_215255.json`

This ensures:
- Chronological ordering when sorted by filename
- No filename conflicts (assuming requests don't occur in the same second)
- Easy identification of when conversations occurred

## Implementation Details

### Logging Function
```python
def save_chat_log(question: str, answer: str, model: str = "gpt-4o"):
    """Save individual chat session to timestamped JSON file"""
    # Creates logs/ directory if needed
    # Generates timestamp-based filename
    # Saves JSON with UTF-8 encoding
```

### Integration Points
- **Streaming Response**: Logs are created when streaming completes
- **Error Handling**: Errors are caught and logged with error messages
- **CLI Testing**: Command-line tests also generate logs
- **API Endpoint**: All `/ask-chatgpt` requests are logged

## Testing

Use the provided test script to verify logging functionality:

```bash
python test_logging.py
```

This script will:
1. Send a test message to the server
2. Monitor the streaming response
3. Check for new log files
4. Display log file contents
5. Show response statistics

## Directory Structure

```
project/
├── streaming_server.py      # Main server with logging
├── streaming_chat_fixed.py  # Streaming implementation
├── test_logging.py          # Test script
├── logs/                    # Log files directory
│   ├── server_chat_session_20250716_215255.json
│   ├── server_chat_session_20250716_215301.json
│   └── ...
└── LOGGING_README.md        # This file
```

## Benefits

1. **Audit Trail**: Complete record of all interactions
2. **Debugging**: Easy to trace issues with specific requests
3. **Analytics**: Can analyze conversation patterns and response quality
4. **Backup**: Persistent storage of all conversations
5. **Individual Files**: Easy to process, share, or archive specific conversations

## Notes

- Log files are created with UTF-8 encoding to handle international characters
- The `logs/` directory is automatically created if it doesn't exist
- Each request gets its own file to avoid concurrency issues
- Timestamps use the server's local timezone
- Error responses are also logged for debugging purposes
