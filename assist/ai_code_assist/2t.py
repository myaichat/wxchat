"""The script is a simple text generation model using LSTM in TensorFlow/Keras. 
The script tokenizes a list of Python code snippets and trains an LSTM model to predict the next token in the code.
The script then uses the trained model to predict the next token given an input code snippet.
"""
import os
from dotenv import load_dotenv
#from langchain_openai import ChatOpenAI
import openai
# load the environment variables
load_dotenv()

# Initialise the Large Language Model


# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the client
client = openai.OpenAI()


import openai

def query_openai_for_fix(description, file_name, code, error_message):


    # Building a prompt that focuses on a specific file and includes the error message
    prompt = f"Problem description: {description}\nError message: {error_message}\n\nFile: {file_name}\nCode:\n{code}\n\nSuggest a fix:"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a chatbot that assists with fixing bugs Python in code."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    # Print each response chunk as it arrives
    for chunk in response:
        if hasattr(chunk.choices[0].delta, 'content'):
            content = chunk.choices[0].delta.content
            print(content, end='', flush=True)
    return None

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print("File not found. Please make sure the file path is correct.")
        exit()
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        exit()

def main():
    print("Describe your coding problem:")
    problem_description = """Python 3.9 script running in windows shell fails.
    Environment:
    OS:Windows 12 cli/shell
    Miniconda Python version: 3.9
    Package                 Version
----------------------- --------
absl-py                 2.1.0
aiohttp                 3.9.5
aiosignal               1.2.0
astunparse              1.6.3
async-timeout           4.0.3
attrs                   23.1.0
blinker                 1.6.2
Brotli                  1.0.9
cachetools              5.3.3
certifi                 2024.2.2
cffi                    1.16.0
charset-normalizer      2.0.4
click                   8.1.7
colorama                0.4.6
cryptography            41.0.3
flatbuffers             2.0
frozenlist              1.4.0
gast                    0.4.0
google-auth             2.29.0
google-auth-oauthlib    0.4.4
google-pasta            0.2.0
grpcio                  1.48.2
h5py                    3.11.0
idna                    3.7
importlib-metadata      7.0.1
keras                   2.10.0
Keras-Preprocessing     1.1.2
Markdown                3.4.1
MarkupSafe              2.1.3
mkl-fft                 1.3.8
mkl-random              1.2.4
mkl-service             2.4.0
multidict               6.0.4
numpy                   1.26.4
oauthlib                3.2.2
opt-einsum              3.3.0
packaging               23.2
pip                     24.0
protobuf                3.20.3
pyasn1                  0.4.8
pyasn1-modules          0.2.8
pycparser               2.21
PyJWT                   2.8.0
pyOpenSSL               23.2.0
PySocks                 1.7.1
requests                2.31.0
requests-oauthlib       1.3.0
rsa                     4.7.2
scipy                   1.13.0
setuptools              69.5.1
six                     1.16.0
tensorboard             2.10.0
tensorboard-data-server 0.6.1
tensorboard-plugin-wit  1.8.1
tensorflow              2.10.0
tensorflow-estimator    2.10.0
termcolor               2.1.0
typing_extensions       4.11.0
urllib3                 2.2.1
Werkzeug                2.3.8
wheel                   0.43.0
win-inet-pton           1.1.0
wrapt                   1.14.1
yarl                    1.9.3
zipp                    3.17.0

Script purpose: The script is a simple text generation model using LSTM in TensorFlow/Keras. The script tokenizes a list of Python code snippets and trains an LSTM model to predict the next token in the code. The script then uses the trained model to predict the next token given an input code snippet.
"""
    file_name = "problem.py"
    code_snippet = read_file(file_name)
    print("Enter the error message (if any):")
    error_message = r'''Traceback (most recent call last):
  File "C:\Users\alex_\aichat\wxchat\ai_code_assist\problem.py", line 22, in <module>
    tokenizer.fit_on_text(data)
AttributeError: 'Tokenizer' object has no attribute 'fit_on_text'
'''

    fix_suggestion = query_openai_for_fix(problem_description, file_name, code_snippet, error_message)
    print("\nSuggested Fix:\n", fix_suggestion)

if __name__ == "__main__":
    main()
