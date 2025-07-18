@echo off
echo Claude Streaming CDP Runner
echo ========================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Check if the streaming script exists
if not exist "claude_simple_cdp_streaming.py" (
    echo Error: claude_simple_cdp_streaming.py not found
    echo Please make sure the file is in the current directory
    pause
    exit /b 1
)

echo Python found: 
python --version
echo.

REM Check if Chrome debug port is accessible
echo Checking Chrome debug port...
curl -s http://localhost:9222/json >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Chrome debug port not accessible
    echo.
    echo Setup required:
    echo 1. Close all Chrome instances
    echo 2. Start Chrome with: chrome --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome-debug
    echo 3. Open https://claude.ai and login
    echo 4. Start a new conversation
    echo.
    echo Press any key to continue anyway, or Ctrl+C to exit
    pause >nul
) else (
    echo Chrome debug port accessible!
)

echo.
echo Usage examples:
echo   %~nx0 "Hello, how are you?"
echo   %~nx0 "Tell me about Python programming"
echo   %~nx0 "Write a short story"
echo.

REM Check if question was provided as argument
if "%~1"=="" (
    echo No question provided. Please enter your question:
    set /p question="Question: "
) else (
    set question=%~1
)

if "%question%"=="" (
    echo Error: No question provided
    pause
    exit /b 1
)

echo.
echo Running streaming Claude with question: "%question%"
echo ================================================
echo.

REM Run the streaming script
python claude_simple_cdp_streaming.py "%question%"

echo.
echo ================================================
echo Script completed. Press any key to exit...
pause >nul
