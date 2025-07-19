@echo off
echo Testing Grok API implementation...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the test
python test_grok_api.py %*

REM Keep window open to see results
echo.
echo Press any key to exit...
pause >nul
