import streamlit as st
import streamlit.components.v1 as components
import time

def push_to_talk_button_improved():
    """Create an improved push-to-talk button using JavaScript and session state"""
    
    # Initialize session state for button tracking
    if 'ptt_recording' not in st.session_state:
        st.session_state.ptt_recording = False
    if 'ptt_start_time' not in st.session_state:
        st.session_state.ptt_start_time = None
    if 'ptt_action' not in st.session_state:
        st.session_state.ptt_action = None
    
    # JavaScript code for push-to-talk functionality
    js_code = f"""
    <div id="push-to-talk-container">
        <button 
            id="push-to-talk-btn" 
            onmousedown="startRecording()" 
            onmouseup="stopRecording()"
            onmouseleave="stopRecording()"
            style="
                background-color: {'#28a745' if st.session_state.ptt_recording else '#ff4b4b'};
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
                transition: background-color 0.2s;
            "
        >
            {'🔴 Recording...' if st.session_state.ptt_recording else '🎤 Hold to Record'}
        </button>
        <div id="status" style="margin-top: 10px; font-weight: bold; color: #333;">
            {'🔴 Recording in progress...' if st.session_state.ptt_recording else ''}
        </div>
    </div>

    <script>
        let isRecording = {str(st.session_state.ptt_recording).lower()};
        let recordingStartTime = null;
        
        function startRecording() {{
            if (!isRecording) {{
                isRecording = true;
                recordingStartTime = Date.now();
                
                // Update button appearance
                document.getElementById('push-to-talk-btn').style.backgroundColor = '#28a745';
                document.getElementById('push-to-talk-btn').innerHTML = '🔴 Recording...';
                document.getElementById('status').innerHTML = '🔴 Recording in progress...';
                
                // Send start signal to Streamlit
                fetch('/start_recording', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{action: 'start', timestamp: recordingStartTime}})
                }}).catch(e => console.log('Start recording signal sent'));
            }}
        }}
        
        function stopRecording() {{
            if (isRecording) {{
                isRecording = false;
                const recordingDuration = Date.now() - recordingStartTime;
                
                // Update button appearance
                document.getElementById('push-to-talk-btn').style.backgroundColor = '#ff4b4b';
                document.getElementById('push-to-talk-btn').innerHTML = '🎤 Hold to Record';
                document.getElementById('status').innerHTML = 'Processing audio...';
                
                // Send stop signal to Streamlit
                fetch('/stop_recording', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{action: 'stop', duration: recordingDuration, timestamp: Date.now()}})
                }}).catch(e => console.log('Stop recording signal sent'));
                
                setTimeout(() => {{
                    document.getElementById('status').innerHTML = '';
                }}, 3000);
            }}
        }}
        
        // Prevent context menu and drag
        document.getElementById('push-to-talk-btn').addEventListener('contextmenu', e => e.preventDefault());
        document.getElementById('push-to-talk-btn').addEventListener('dragstart', e => e.preventDefault());
        
        // Touch support for mobile
        document.getElementById('push-to-talk-btn').addEventListener('touchstart', e => {{
            e.preventDefault();
            startRecording();
        }});
        
        document.getElementById('push-to-talk-btn').addEventListener('touchend', e => {{
            e.preventDefault();
            stopRecording();
        }});
    </script>
    """
    
    # Create the component
    components.html(js_code, height=100)
    
    # Return current state
    return {
        'recording': st.session_state.ptt_recording,
        'action': st.session_state.ptt_action
    }

def handle_ptt_action(action):
    """Handle push-to-talk actions"""
    if action == 'start':
        st.session_state.ptt_recording = True
        st.session_state.ptt_start_time = time.time()
        st.session_state.ptt_action = 'start'
    elif action == 'stop':
        st.session_state.ptt_recording = False
        st.session_state.ptt_action = 'stop'
    else:
        st.session_state.ptt_action = None
