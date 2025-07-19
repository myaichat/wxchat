@echo off
echo Starting Streamlit Gem PyChrome Chat Interface...
echo.
echo Make sure Chrome is running with debug port:
echo chrome --remote-debugging-port=9222
echo.
echo Starting Streamlit app...
streamlit run streamlit_gem_pychrome_app.py
pause
