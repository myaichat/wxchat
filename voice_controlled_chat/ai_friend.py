import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from include.voice import Voice
from include.transcribe import Transcribe
from pprint import pprint as pp

# load the environment variables
load_dotenv()

# Initialise the Large Language Model
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=1, 
    model_name='gpt-4o'
    )

# Create a prompt template
template = """You are a chatbot that assists with technical interview on:

Must Have Skills

Oracle DB - SQL/PLSQL expertise
Data Analysis & Prod Support experience
Unix shell scripting
CI/CD tools: GIT

Good to have skills:

Informatica ETL development/Support experience
BI Tools - Tableau/ PowerBl
Basic Python
Snowflake, DBT
Azure Cloud knowledge
Liquibase

If question is not about interview tech stack do not refuse answer and do your best answering it.



Previous conversation:
{chat_history}

New human question: {question}
Response:"""

# Create a prompt template
prompt = PromptTemplate.from_template(template)

# Create some memory for the agent
memory = ConversationBufferMemory(memory_key="chat_history")

# Initialise the conversation chain
conversation_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True, 
    memory=memory
)

# initialize the voice instance
model_voice = Voice()

# initialise the voice transcriber
transcriber = Transcribe()

def listen():
    
    file_path = transcriber.record_audio()
    print(f"Audio recorded and saved to {file_path}")

    # Transcribe audio
    transcript_result = transcriber.transcribe_audio(file_path)
    print(f"Transcription Result: {transcript_result}")
    return transcript_result

def prompt_model(text):
    # Prompt the LLM chain
    response = conversation_chain.run({"question": text})
    return response

def respond(model_response):
    # Run the speech synthesis
    response_id = model_voice.generate_voice(model_response)
    #model_voice.play_voice(response_id)   
    transcriber = Transcribe()
    

def conversation():
    user_input = ""
    
    while True:
        print('listen...')
        user_input = listen()
        print('User input:', user_input)
        if user_input is None:
            user_input = listen()
            print('User input 2:', user_input)

        elif "bye" in user_input.lower():
            respond(conversation_chain.run({"question": "Send a friendly goodbye question and give a nice short sweet compliment based on the conversation."}))
            model_voice.delete_mp3_files()  # delete all the model response audio files
            transcriber.delete_wav_audio_files()    # delete all the user recorded speech
            return
        
        else:
            model_response = prompt_model(user_input)
            print('Responce...')
            print('#'*60)
            print(model_response)
            print('#'*60)
            
            inp = input('Continue?')
            #print('Memory:')
            #print(memory)
            
            print(prompt)
            #respond(model_response)
        

if __name__ == "__main__":
    #respond(conversation_chain.run({"question": "Greet me in a friendly way."}))
    conversation()