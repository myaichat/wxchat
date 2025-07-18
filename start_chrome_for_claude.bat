@echo off
echo Starting Chrome with debug mode for Claude Web UI...
echo.
echo This will:
echo 1. Start Chrome with remote debugging enabled on port 9222
echo 2. Use a separate user data directory to avoid conflicts
echo 3. Open Claude.ai automatically
echo.

REM Kill any existing Chrome processes to avoid conflicts
taskkill /f /im chrome.exe 2>nul

REM Wait a moment for processes to close
timeout /t 2 /nobreak >nul

REM Create temp directory for Chrome user data
set CHROME_USER_DIR=%TEMP%\chrome-debug-claude
if not exist "%CHROME_USER_DIR%" mkdir "%CHROME_USER_DIR%"

echo Starting Chrome with debug mode...
echo User data directory: %CHROME_USER_DIR%
echo Debug port: 9222
echo.

REM Start Chrome with debug mode and open Claude.ai
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%CHROME_USER_DIR%" ^
  --disable-web-security ^
  --disable-features=VizDisplayCompositor ^
  "https://claude.ai"

echo.
echo Chrome started! Please:
echo 1. Wait for Chrome to fully load
echo 2. Log into Claude.ai if needed
echo 3. Start the Streamlit app: streamlit run claude_webui_app.py
echo.
echo Press any key to exit this window...
pause >nul
