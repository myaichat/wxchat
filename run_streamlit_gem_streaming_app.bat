@echo off
echo Starting Streamlit Gem PyChrome Streaming Chat Interface...
echo.
echo Make sure Chrome is running with debug port:
echo chrome --remote-debugging-port=9222
echo.
echo Starting Streamlit streaming app...
streamlit run streamlit_gem_pychrome_streaming_app.py
pause
