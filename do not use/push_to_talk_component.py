import streamlit as st
import streamlit.components.v1 as components

def push_to_talk_button():
    """Create a push-to-talk button using JavaScript"""
    
    # JavaScript code for push-to-talk functionality
    js_code = """
    <div id="push-to-talk-container">
        <button 
            id="push-to-talk-btn" 
            onmousedown="startRecording(event)" 
            onmouseup="stopRecording(event)"
            onmouseleave="stopRecording(event)"
            style="
                background-color: #ff4b4b;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
            "
        >
            🎤 Hold to Record
        </button>
        <div id="status" style="margin-top: 10px; font-weight: bold;"></div>
    </div>

    <script>
        let isRecording = false;
        let recordingStartTime = null;
        let componentValue = null;
        
        function startRecording(event) {
            event.preventDefault();
            if (!isRecording) {
                isRecording = true;
                recordingStartTime = Date.now();
                document.getElementById('push-to-talk-btn').style.backgroundColor = '#28a745';
                document.getElementById('push-to-talk-btn').innerHTML = '🔴 Recording...';
                document.getElementById('status').innerHTML = '🔴 Recording in progress...';
                
                // Set component value for Streamlit
                componentValue = {action: 'start_recording', timestamp: recordingStartTime};
                
                // Trigger Streamlit rerun
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: componentValue
                }, '*');
            }
        }
        
        function stopRecording(event) {
            event.preventDefault();
            if (isRecording) {
                isRecording = false;
                const recordingDuration = Date.now() - recordingStartTime;
                document.getElementById('push-to-talk-btn').style.backgroundColor = '#ff4b4b';
                document.getElementById('push-to-talk-btn').innerHTML = '🎤 Hold to Record';
                document.getElementById('status').innerHTML = 'Processing audio...';
                
                // Set component value for Streamlit
                componentValue = {action: 'stop_recording', duration: recordingDuration, timestamp: Date.now()};
                
                // Trigger Streamlit rerun
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: componentValue
                }, '*');
                
                setTimeout(() => {
                    document.getElementById('status').innerHTML = '';
                }, 3000);
            }
        }
        
        // Prevent context menu on right click
        document.getElementById('push-to-talk-btn').addEventListener('contextmenu', function(e) {
            e.preventDefault();
        });
        
        // Handle touch events for mobile
        document.getElementById('push-to-talk-btn').addEventListener('touchstart', function(e) {
            e.preventDefault();
            startRecording(e);
        });
        
        document.getElementById('push-to-talk-btn').addEventListener('touchend', function(e) {
            e.preventDefault();
            stopRecording(e);
        });
        
        // Prevent default drag behavior
        document.getElementById('push-to-talk-btn').addEventListener('dragstart', function(e) {
            e.preventDefault();
        });
    </script>
    """
    
    # Create the component
    component_value = components.html(js_code, height=100)
    return component_value
