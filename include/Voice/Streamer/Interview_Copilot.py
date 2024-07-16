import os,sys, time
sys.stdout = open(os.devnull, 'w') #disable pygame prints
import openai
from include.fmt import pfmt
import keyboard
from pubsub import pub
from include.Common import split_text_into_chunks, fmt
from pprint import pprint as pp 
from dotenv import load_dotenv
load_dotenv()
e=sys.exit
import include.config.init_config as init_config 
apc = init_config.apc
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
exit_loop = False
# Define a function to toggle the pause flag when the space key is hit\
import wx
def log( message, color=wx.BLUE):
    
    pub.sendMessage('log', message=f'{message}', color=color)
def toggle_pause(e):
    global pause_stream
    pause_stream = not pause_stream
def ctrl_set_exit_flag():
    global exit_loop
    exit_loop = True
def set_exit_flag(e):
    global exit_loop
    exit_loop = True    
# Register the space key to call the toggle_pause function
if 0:
    keyboard.on_press_key('space', toggle_pause)
    keyboard.on_press_key('e', set_exit_flag, suppress=True)
#keyboard.add_hotkey('ctrl+e', set_exit_flag)
from colorama import Fore, Style

_conversation_history = [
    {"role": "system", "content": """You are a chatbot that assists with Technical interview for Python developer. 
     numerate answert options globally with one sequence. 
     Answer in english. do not add extra new lines. output your answer as markdown text  """}
]
#print(111, apc.chatHistory)
#e()
def listen():
    
    file_path = transcriber.record_audio()
    print(f"Audio recorded and saved to {file_path}")

    # Transcribe audio
    transcript_result = transcriber.transcribe_audio(file_path)
    #print(f"Transcription Result: {transcript_result}")
    return transcript_result
def echo_output(content):
    inside_stars = False
    inside_backticks = False
    inside_hash = False 
    new_content = ''
    i = 0
    if not content:
        return
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
    if inside_backticks:  # If we're still inside a code block, add the reset code
        print(Style.RESET_ALL)

def stream_response(tab_id):
    global exit_loop, pause_stream
    conversation_history=apc.chatHistory[tab_id]
    if not conversation_history:
        conversation_history.append({"role": "system", "content": """You are a chatbot that assists with Technical interview for Python developer.  
        numerate answert options globally with one sequence.
        Answer in english. do not add extra new lines. output your answer as markdown text """})
        
    model_voice.delete_mp3_files()  # delete all the model response audio files
    transcriber.delete_wav_audio_files()    # delete all the user recorded speech       
    if 1:
        log('listening...')
        
        user_input = listen()
        #print('User input:', user_input)
        if user_input is None:
            print('No input')
            user_input = listen()
    prompt= user_input
    chat=apc.chats[tab_id]
    txt='\n'.join(split_text_into_chunks(prompt,80))
    header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
    pub.sendMessage('chat_output', message=f'{header}\n', tab_id=tab_id)
    
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
        if exit_loop:
            print(f"{Style.RESET_ALL}")
            print("\nExiting loop")
            
            break        
        while pause_stream:
            time.sleep(0.1) 
            if exit_loop:
                print(f"{Style.RESET_ALL}")
                #pause_stream=False
                print("\nExiting loop")
                break                   
        if hasattr(chunk.choices[0].delta, 'content'):
            content = chunk.choices[0].delta.content
            if content:
                out.append(content)
                pub.sendMessage('chat_output', message=content, tab_id=tab_id)
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
           

    if inside_backticks:  # If we're still inside a code block, add the reset code
        print(Style.RESET_ALL)
    if out:
        pub.sendMessage('chat_output', message='\n', tab_id=tab_id)
    conversation_history.append({"role": "assistant", "content": ''.join(out)})
 
    print(f"{Style.RESET_ALL}")
    return ''.join(out), exit_loop



def conversation(tab_id):
    global exit_loop, pause_stream
    #prompt="Hey,  what is the fastest way to sort in python?"
    user_input = ""
    
    while True:
        log('listening...')
        pub.sendMessage('chat_output', message='listening...', tab_id=tab_id)
        user_input = listen()
        #print('User input:', user_input)
        if user_input is None:
            print('No input')
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
            model_response, tell_me_more =stream_response(user_input, tab_id)
            if not tell_me_more:
                print()
                inp = input('Continue?')
            else:
                exit_loop=False
                pause_stream=False
            #print(model_response)



if __name__ == "__main__":

    conversation()
    #stream_response("Hey,  what is the fastes way to sort in python?")
    



