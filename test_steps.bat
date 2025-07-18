@echo off
echo Quick Test Steps for Claude Streaming
echo =====================================
echo.

echo Step 1: Start Chrome with debug port
echo Command: chrome --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome-debug
echo.

echo Step 2: Open claude.ai and login
echo.

echo Step 3: Run one of these tests:
echo.

echo Basic streaming test:
echo python claude_simple_cdp_streaming.py "Hello, how are you?"
echo.

echo Async generator test:
echo python quick_test.py
echo.

echo Demo with examples:
echo python demo_async_streaming.py "Tell me about Python"
echo.

echo Multiple examples:
echo python example_async_usage.py
echo.

pause
