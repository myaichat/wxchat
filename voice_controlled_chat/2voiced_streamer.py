import os,sys, time
sys.stdout = open(os.devnull, 'w') #disable pygame prints
import openai
from include.fmt import pfmt
import keyboard
from pprint import pprint as pp
from dotenv import load_dotenv
load_dotenv()

from include.voice import Voice
from include.transcribe import Transcribe
from colorama import Fore, Style
sys.stdout = sys.__stdout__
# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client
client = openai.OpenAI()

# initialize the voice instance
model_voice = Voice()

# initialise the voice transcriber
transcriber = Transcribe()

# Initialize a flag for pausing the stream
pause_stream = False

# Define a function to toggle the pause flag when the space key is hit
def toggle_pause(e):
    global pause_stream
    pause_stream = not pause_stream

# Register the space key to call the toggle_pause function
keyboard.on_press_key('space', toggle_pause)

from colorama import Fore, Style

conversation_history = [
    {"role": "system", "content": "You are a chatbot that assists with Python interview ."}
]

def stream_response(prompt):
    conversation_history.append({"role": "user", "content": prompt})
    # Create a chat completion request with streaming enabled
    #pp(conversation_history)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation_history, 

        stream=True
    )

    # Print each response chunk as it arrives
    out=[]
    inside_stars = False
    inside_backticks = False
    inside_hash = False
    for chunk in response:
        while pause_stream:
            time.sleep(0.1)        
        if hasattr(chunk.choices[0].delta, 'content'):
            content = chunk.choices[0].delta.content
            new_content = ''
            i = 0
            if not content:
                continue
            while i < len(content):
                if content[i:i+2] == '**':
                    if inside_stars:
                        new_content += f"{Style.RESET_ALL}"
                        inside_stars = False
                    else:
                        new_content += f"{Fore.GREEN}{Style.BRIGHT}"
                        inside_stars = True
                    i += 2  # Skip the next character
                elif content[i:i+3] == '```':
                    if inside_backticks:
                        new_content += f"{Style.RESET_ALL}"
                        inside_backticks = False
                        i += 3 
                    else:
                        new_content += f"{Fore.RED}{Style.BRIGHT}"
                        inside_backticks = True
                        i += 3
                     # Skip the next two characters
                elif content[i] == '#' and (i == 0 or content[i-1] == '\n'):  # If the line starts with '#'
                    new_content += f"{Fore.BLUE}{Style.BRIGHT}" + content[i]
                    inside_hash = True
                    i += 1
                elif content[i] == '\n' and inside_hash:  # If the line ends and we're inside a hash line
                    new_content += f"{Style.RESET_ALL}" + content[i]
                    inside_hash = False
                    i += 1
                else:
                    new_content += content[i]
                    i += 1
            print(new_content, end='', flush=True)
            if new_content:
                out.append(new_content)
    if inside_backticks:  # If we're still inside a code block, add the reset code
        out.append(Style.RESET_ALL)
    conversation_history.append({"role": "assistant", "content": ''.join(out)})
    return ''.join(out)

def listen():
    
    file_path = transcriber.record_audio()
    print(f"Audio recorded and saved to {file_path}")

    # Transcribe audio
    transcript_result = transcriber.transcribe_audio(file_path)
    #print(f"Transcription Result: {transcript_result}")
    return transcript_result

def conversation():
    #prompt="Hey,  what is the fastest way to sort in python?"
    user_input = ""
    
    while True:
        print('listen...')
        user_input = listen()
        #print('User input:', user_input)
        if user_input is None:
            user_input = listen()
            #print('User input 2:', user_input)

        elif "bye" in user_input.lower():
            #respond(conversation_chain.run({"question": "Send a friendly goodbye question and give a nice short sweet compliment based on the conversation."}))
            model_voice.delete_mp3_files()  # delete all the model response audio files
            transcriber.delete_wav_audio_files()    # delete all the user recorded speech
            return
        
        else:
            assert user_input
            
            pfmt([[ user_input]], ['User Input'])          
            model_response =stream_response(user_input)

            inp = input('Continue?')
            #print('Memory:')
            #print(memory)
            
            print(prompt)
            #respond(model_response)



if __name__ == "__main__":

    conversation()
    #stream_response("Hey,  what is the fastes way to sort in python?")
    



