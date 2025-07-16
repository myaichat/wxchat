import streamlit as st
import os
from openai import OpenAI

def simple_get_chatgpt_response(prompt):
    """Simplified ChatGPT response function for debugging"""
    st.write(f"🔍 DEBUG: Starting ChatGPT request with prompt: '{prompt}'")
    
    if not prompt or not prompt.strip():
        st.error("⚠️ Prompt is empty — nothing to send.")
        return None

    try:
        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("❌ OPENAI_API_KEY environment variable not found!")
            return None
        
        st.write("🔍 DEBUG: API key found")
        
        client = OpenAI(api_key=api_key)
        st.write("🔍 DEBUG: OpenAI client created")
        
        # Simple non-streaming request first
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        
        st.write("🔍 DEBUG: API call completed")
        
        result = response.choices[0].message.content
        st.write(f"🔍 DEBUG: Response received: '{result}'")
        
        return result
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Simple Streamlit app for testing
st.title("🧪 ChatGPT Debug Test")

if "test_response" not in st.session_state:
    st.session_state.test_response = None

test_prompt = st.text_input("Enter test prompt:", value="Say hello!")

if st.button("Test ChatGPT"):
    st.session_state.test_response = simple_get_chatgpt_response(test_prompt)

if st.session_state.test_response:
    st.success("✅ Response received!")
    st.write("**Response:**")
    st.write(st.session_state.test_response)
