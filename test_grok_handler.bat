@echo off
echo Testing Grok Handler CLI...
echo.

if "%1"=="" (
    echo Usage: test_grok_handler.bat "Your question here" [timeout_seconds]
    echo Example: test_grok_handler.bat "What is AI?" 60
    echo.
    pause
    exit /b 1
)

set QUESTION=%1
set TIMEOUT=%2
if "%TIMEOUT%"=="" set TIMEOUT=120

echo Question: %QUESTION%
echo Timeout: %TIMEOUT% seconds
echo.

python chat_handlers/grok_handler.py %QUESTION% %TIMEOUT%

echo.
pause
