import openai
import os
from dotenv import load_dotenv
load_dotenv()

from include.voice import Voice
from include.transcribe import Transcribe
from colorama import Fore, Style
# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client
client = openai.OpenAI()

# initialize the voice instance
model_voice = Voice()

# initialise the voice transcriber
transcriber = Transcribe()

from colorama import Fore, Style

def stream_response(prompt):
    # Create a chat completion request with streaming enabled
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a chatbot that assists with Python interview ."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    # Print each response chunk as it arrives
    out=[]
    inside_stars = False
    inside_backticks = False
    inside_hash = False
    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content'):
            content = chunk.choices[0].delta.content
            new_content = ''
            i = 0
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
                    else:
                        new_content += f"{Fore.RED}{Style.BRIGHT}"
                        inside_backticks = True
                    i += 3  # Skip the next two characters
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
    return ''.join(out)

def listen():
    
    file_path = transcriber.record_audio()
    print(f"Audio recorded and saved to {file_path}")

    # Transcribe audio
    transcript_result = transcriber.transcribe_audio(file_path)
    print(f"Transcription Result: {transcript_result}")
    return transcript_result

def conversation():
    prompt="Hey,  what is the fastes was to sort in python?"
    user_input = ""
    
    while True:
        print('listen...')
        user_input = listen()
        print('User input:', user_input)
        if user_input is None:
            user_input = listen()
            print('User input 2:', user_input)

        elif "bye" in user_input.lower():
            #respond(conversation_chain.run({"question": "Send a friendly goodbye question and give a nice short sweet compliment based on the conversation."}))
            model_voice.delete_mp3_files()  # delete all the model response audio files
            transcriber.delete_wav_audio_files()    # delete all the user recorded speech
            return
        
        else:
            assert user_input
            
            print('#'*60)            
            model_response =stream_response(user_input)
            print('#'*60)
            if 0:
                print('Responce...')
                print('#'*80)
                print(model_response)
                print('#'*80)
            
            inp = input('Continue?')
            #print('Memory:')
            #print(memory)
            
            print(prompt)
            #respond(model_response)
if __name__ == "__main__":
    conversation()
    #stream_response("Hey,  what is the fastes was to sort in python?")


