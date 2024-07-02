#https://aistudio.google.com/app/prompts/new_chat?model=gemma-2-27b-it
import wx
import wx.stc as stc
import wx.adv
import wx.lib.agw.aui as aui
import time, glob,threading, traceback
import os
from pubsub import pub
from pprint import pprint as pp 
from include.Common import *
from include.fmt import fmt
from include.Copilot.Base.Base_InputPanel_Google_Gemma import Base_InputPanel_Google_Gemma
import include.config.init_config as init_config 
apc = init_config.apc
default_chat_template='SYSTEM'
default_copilot_template='SYSTEM_CHATTY'
#DEFAULT_MODEL  = 'gpt-4o'


DEFAULT_MODEL='google/gemma-2-9b-it'

model_list=['google/gemma-2-9b', DEFAULT_MODEL,'google/gemma-2-27b-it']
dir_path = 'template'

chatHistory,  currentQuestion, currentModel = apc.chatHistory,  apc.currentQuestion, apc.currentModel
questionHistory= apc.questionHistory
all_templates, all_chats, all_system_templates = apc.all_templates, apc.all_chats, apc.all_system_templates
panels     = AttrDict(dict(workspace='WorkspacePanel', vendor='ChatDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))

from transformers import AutoTokenizer, AutoModelForCausalLM, LogitsProcessorList, LogitsProcessor
import torch
import time
from transformers import TextStreamer
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TextStreamer
import torch
import time

class StreamProcessor(LogitsProcessor):
    def __init__(self, tokenizer, model,tab_id):
        self.tokenizer = tokenizer
        self.model = model
        self.generated_text = ""
        print("\nStart:", time.time() - apc.stream_start)
        self.start= time.time()
        self.tab_id = tab_id
    
    def __call__(self, input_ids, scores):
        generated_token_id = torch.argmax(scores, dim=-1)
        generated_token = self.tokenizer.decode(generated_token_id)
        self.generated_text += generated_token
        #print(generated_token, end='', flush=True)
        pub.sendMessage('chat_output', message=f'{generated_token}', tab_id=self.tab_id)
        return scores

class FlashAttn_CustomTextStreamer(TextStreamer):
    def __init__(self, tokenizer, tab_id,skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens)
        self.generated_text = ""
        print("CustomTextStreamer initialized")
        self.tab_id=tab_id
        self.start= time.time()

    def __call__(self, token_ids, **kwargs):
        #print("CustomTextStreamer __call__ invoked")
        # Decode the token ids and append to the generated text
        text = self.tokenizer.decode(token_ids, skip_special_tokens=self.skip_special_tokens)
        self.generated_text += text
        #print(123)
        print(text, end='', flush=True)  # Print each chunk of text
        pub.sendMessage('chat_output', message=f'{text}', tab_id=self.tab_id)

class CustomTextStreamer(TextStreamer):
    def __init__(self, tokenizer, tab_id, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens)
        self.generated_text = ""
        self.skip_special_tokens = skip_special_tokens
        print("\nStart 111:", time.time() - apc.stream_start)
        self.start= time.time()  
        self.tab_id = tab_id      

    def __call__(self, token_ids, scores):
        # Decode the token ids and append to the generated text
        text = self.tokenizer.decode(token_ids, skip_special_tokens=self.skip_special_tokens)
        self.generated_text += text
        pub.sendMessage('chat_output', message=f'{text}', tab_id=self.tab_id)
        print(123)
        #print(text, end='', flush=True)  # Print each chunk of text

class ManualStreamer:
    def __init__(self, tokenizer, tab_id, skip_special_tokens=True):
        self.tokenizer = tokenizer
        self.skip_special_tokens = skip_special_tokens
        self.generated_text = ""
        self.tab_id = tab_id
        self.start= time.time()

    def stream(self, input_ids, model, max_new_tokens=600, temperature=1.0, top_p=0.95, top_k=50):
        generated_ids = input_ids
        for _ in range(max_new_tokens):
            outputs = model.generate(
                generated_ids,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_new_tokens=1,
                pad_token_id=self.tokenizer.eos_token_id  # Ensure padding token id is set
            )
            next_token_id = outputs[:, -1:]
            generated_ids = torch.cat((generated_ids, next_token_id), dim=1)
            next_token = self.tokenizer.decode(next_token_id.squeeze(), skip_special_tokens=self.skip_special_tokens)
            self.generated_text += next_token
            #print(123)
            pub.sendMessage('chat_output', message=f'{next_token}', tab_id=self.tab_id)
            print(next_token, end='', flush=True)  # Print each chunk of text as it is generated

class FlashAttn_ManualStreamer:
    def __init__(self, tokenizer, tab_id, skip_special_tokens=True):
        self.tokenizer = tokenizer
        self.skip_special_tokens = skip_special_tokens
        self.generated_text = ""
        self.tab_id = tab_id
        self.start= time.time()

    def stream(self, input_ids, attention_mask, model, max_new_tokens=100, temperature=1.0, top_p=0.95, top_k=50):
        generated_ids = input_ids
        generated_attention_mask = attention_mask
        for _ in range(max_new_tokens):
            outputs = model.generate(
                input_ids=generated_ids,
                attention_mask=generated_attention_mask,
                do_sample=True,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_new_tokens=1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            next_token_id = outputs[:, -1:]
            generated_ids = torch.cat((generated_ids, next_token_id), dim=1)
            next_token = self.tokenizer.decode(next_token_id.squeeze(), skip_special_tokens=self.skip_special_tokens)
            self.generated_text += next_token
            print(next_token, end='', flush=True)  # Print each chunk of text as it is generated

            # Update the attention mask to include the new token
            new_attention_mask = torch.ones((attention_mask.size(0), 1), device=attention_mask.device)
            generated_attention_mask = torch.cat((generated_attention_mask, new_attention_mask), dim=1)
class Chat_CustomStreamer(TextStreamer):
    def __init__(self, tokenizer, tab_id, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens=skip_special_tokens)
        self.generated_text = ""
        self.skip_special_tokens = skip_special_tokens
        self.tab_id = tab_id

    def put(self, token_ids):
        # Ensure we process each token ID individually
        if token_ids.dim() == 1:  # Case for batch size 1
            for token_id in token_ids:
                token = self.tokenizer.decode([token_id.item()], skip_special_tokens=self.skip_special_tokens)
                self.generated_text += token
                # Here you can process the token as it is generated
                pub.sendMessage('chat_output', message=f'{token}', tab_id=self.tab_id)
                print(token, end='', flush=True)
        else:  # Case for batch size > 1
            for batch in token_ids:
                for token_id in batch:
                    token = self.tokenizer.decode([token_id.item()], skip_special_tokens=self.skip_special_tokens)
                    self.generated_text += token
                    # Here you can process the token as it is generated
                    if 1: #suppressing
                        print(token, end='', flush=True)
class Chat_4bit_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]

            prompt = tokenizer.apply_chat_template(uchat, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=chat.max_tokens, 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)  

class History_4bit_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')
            
            achat = [
                {"role": "assistant", "content": streamer.generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out) 
class Chat_History_FlashAttn_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')
            
            achat = [
                {"role": "assistant", "content": streamer.generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out) 
class Copilot_History_4bit_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}


    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]= [
            {"role": "user", "content": """Can you as chatbot that assists with anwering questions about 
        code included or adding new features 
        and debugging scripts written using wxPython. 
        Give short description for each change the code required for change.
        Numerate each change by index 
        Present changes in form:
        #Description
        [CHANGE DESCRIPTION]
        #Change To:
        [NEW CODE LINES]"""},
            {"role": "assistant", "content": """Okay, I'm ready to help with your wxPython code!  I'll understand the context of each change.

Provide me with the code snippet and tell me what you want to change.

I'll number the changes and make a numbered list to keep track of what is updated. 



Let's get coding!"""},
            ]        
            

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')
            
            achat = [
                {"role": "assistant", "content": streamer.generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)  

class Copilot_History_FlashAttn_Sys_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}


    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]= [
            {"role": "user", "content": """Can you as chatbot that assists with anwering questions about 
        code included or adding new features 
        and debugging scripts written using wxPython. 
        Give short description for each change the code required for change.
        Numerate each change by index 
        Present changes in form:
        #Description
        [CHANGE DESCRIPTION]
        #Change To:
        [NEW CODE LINES]"""},
            {"role": "assistant", "content": """Okay, I'm ready to help with your wxPython code!  I'll understand the context of each change.

Provide me with the code snippet and tell me what you want to change.

I'll number the changes and make a numbered list to keep track of what is updated. 



Let's get coding!"""},
            ]        
            

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')
            
            achat = [
                {"role": "assistant", "content": streamer.generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)  
           
class Chat_History_4bit_Batch_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]= []
              
            

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
    
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)
            gen_start = time.time()
            outputs = model.generate(input_ids=inputs, 
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                )
            generated_text=tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(generated_text)
            
            pub.sendMessage('chat_output', message=f'{generated_text}\n', tab_id=receiveing_tab_id)
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')            
            achat = [
                {"role": "assistant", "content": generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)
class Copilot_History_4bit_Batch_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]= []
              
            

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
    
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)
            gen_start = time.time()
            outputs = model.generate(input_ids=inputs, 
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                )
            generated_text=tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(generated_text)
            
            pub.sendMessage('chat_output', message=f'{generated_text}\n', tab_id=receiveing_tab_id)
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')            
            achat = [
                {"role": "assistant", "content": generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)


class Copilot_History_FlashAttn_Batch_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]= []
              
            

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
    
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)
            gen_start = time.time()
            outputs = model.generate(input_ids=inputs, 
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                )
            generated_text=tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(generated_text)
            
            pub.sendMessage('chat_output', message=f'{generated_text}\n', tab_id=receiveing_tab_id)
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')            
            achat = [
                {"role": "assistant", "content": generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)
class Copilot_History_Full_Batch_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                #torch_dtype=dtype,
                #attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Enable synchronous error reporting
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]= []
              
            

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]
            chat_history +=uchat
            pp(chat_history)
    
            prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)
            gen_start = time.time()
            outputs = model.generate(input_ids=inputs, 
                max_new_tokens=int(chat.max_tokens), 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                )
            generated_text=tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(generated_text)
            
            pub.sendMessage('chat_output', message=f'{generated_text}\n', tab_id=receiveing_tab_id)
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')            
            achat = [
                {"role": "assistant", "content": generated_text},
            ]
            chat_history +=achat
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)
        
class Chat_8bit_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.float16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]

            prompt = tokenizer.apply_chat_template(uchat, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=chat.max_tokens, 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)     
class Chat_NoHist_FlashAttn_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            #quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                torch_dtype=dtype,
                attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]

            prompt = tokenizer.apply_chat_template(uchat, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=chat.max_tokens, 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)  
    
class Chat_Full_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        #dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
            #quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                cache_dir="./cache",
                #torch_dtype=dtype,
                #attn_implementation="flash_attention_2"
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()
            model_id = chat.model
            

            tokenizer = self.get_tokenizer(model_id)
            telapsed=time.time() - start
            print("tokenizer:",telapsed )

            #quantization_config = BitsAndBytesConfig(load_in_4bit=True)
            model_start = time.time()
            model = self.get_model(model_id)
            print("model:", time.time() - start)
            log(f'Tokenizer {telapsed}, Model {time.time() - model_start}')

            uchat = [
                {"role": "user", "content": text_prompt},
            ]

            prompt = tokenizer.apply_chat_template(uchat, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")

            # Ensure the inputs are moved to the same device as the model
            inputs = inputs.to(model.device)

            # Use the custom streamer
            streamer = Chat_CustomStreamer(tokenizer, receiveing_tab_id, skip_special_tokens=True)

            # Adjust the call to generate
            #pp(chat)
            gen_start = time.time()
            model.generate(input_ids=inputs, streamer=streamer,
                max_new_tokens=chat.max_tokens, 
                do_sample=chat.do_sample,
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),      # Nucleus sampling
                top_k=int(chat.top_k), 
                num_return_sequences=1,
                use_cache=chat.use_cache,
                #return_dict_in_generate=False,
                #output_scores=False,                
            )

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)      
class NoHist_4bit_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}

 
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:




            start = time.time()
            apc.stream_start = time.time()
           
            model_id=DEFAULT_MODEL


            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

            
            quantization_config = BitsAndBytesConfig(load_in_4bit=True)


            quantization_config_2 = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )


            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True #,
                #low_cpu_mem_usage=True
            )

            input_text = text_prompt
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiveing_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,  # limit the number of new tokens to generate
                do_sample=True,  # disable sampling to get deterministic output
                temperature=1.0,
                top_p=0.95,      # Nucleus sampling
                top_k=50         # Limiting to top_k choices
            )
            #print(outputs)
            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)




        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)   

class Hist_4bit_ResponseStreamer:
    subscribed = False
    def __init__(self):
        # Set your OpenAI API key here
        self.model = {}
        self.chat_history = {}
        self.tokenizer = {}
    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

            quantization_config = BitsAndBytesConfig(load_in_4bit=True)

            quantization_config_2 = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )

            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True
            )
           
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]
    def stream_response(self, text_prompt, chatHistory, receiving_tab_id):
        # Create a chat completion request with streaming enabled
        if receiving_tab_id not in self.chat_history:
            self.chat_history[receiving_tab_id] = []
        chat_history = self.chat_history[receiving_tab_id]
        out = []
        from os.path import isfile
        chat = apc.chats[receiving_tab_id]
        txt = '\n'.join(split_text_into_chunks(text_prompt, 80))
        
        try:
            start = time.time()
            apc.stream_start = time.time()
           
            model_id = DEFAULT_MODEL

            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            tokenizer = self.get_tokenizer(model_id)
            model = self.get_model(model_id)

            # Prepare input with chat history
            input_text = self.prepare_input_with_history(text_prompt, chat_history)
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiving_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=50
            )

            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)

            # Update chat history
            self.update_chat_history(receiving_tab_id, text_prompt, outputs)

        except Exception as e:    
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            print(f"An error occurred: {e}")
            raise

        if logits_processor[0].generated_text:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiving_tab_id)

        return ''.join(out)

    def prepare_input_with_history(self, text_prompt, chat_history):
        # Prepare input text with chat history
        history_text = ""
        for entry in chat_history:
            history_text += f"Human: {entry['human']}\nAI: {entry['ai']}\n\n"
        return f"{history_text}Human: {text_prompt}\nAI:"

    def update_chat_history(self, tab_id, human_message, ai_response):
        # Update chat history for the given tab
        chat=apc.chats[tab_id]
        tokenizer=self.tokenizer[chat.model]
        decoded_response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
        self.chat_history[tab_id].append({
            "human": human_message,
            "ai": decoded_response
        })

class Hist_4bit_Sys_ResponseStreamer:
    subscribed = False
    def __init__(self):
        # Set your OpenAI API key here
        self.model = {}
        self.chat_history = {}
        self.tokenizer = {}
    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

            quantization_config = BitsAndBytesConfig(load_in_4bit=True)

            quantization_config_2 = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )

            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True
            )
           
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]
    def stream_response(self, text_prompt, chatHistory, receiving_tab_id):
        # Create a chat completion request with streaming enabled
        if receiving_tab_id not in self.chat_history:
            self.chat_history[receiving_tab_id] = [
            { "human": """Can you as chatbot that assists with anwering questions about 
        code included or adding new features 
        and debugging scripts written using wxPython. 
        Give short description for each change the code required for change.
        Numerate each change by index 
        Present changes in form:
        #Description
        [CHANGE DESCRIPTION]
        #Change To:
        [NEW CODE LINES]""","ai": """Okay, I'm ready to help with your wxPython code!  I'll understand the context of each change.

Provide me with the code snippet and tell me what you want to change.

I'll number the changes and make a numbered list to keep track of what is updated. 



Let's get coding!"""},
            ] 
            self.chat_history[receiving_tab_id] = [
            { "human": """Can you as chatbot that assists with anwering questions about 
        code given or adding new features 
        and debugging scripts written using wxPython. 
        Give short description for each change the code required for change.
        Numerate each change by index. 
        Present changes in form:
        Line number:
        [NEW CODE LINES]""","ai": """Okay, I'm ready to help with your wxPython code!  I'll understand the context of each change.

Provide me with the code snippet and tell me what you want to change.

I'll number the changes and make a numbered list to keep track of what is updated. 



Let's get coding!"""},
            ]             
        chat_history = self.chat_history[receiving_tab_id]
        out = []
        from os.path import isfile
        chat = apc.chats[receiving_tab_id]
        txt = '\n'.join(split_text_into_chunks(text_prompt, 80))
        
        try:
            start = time.time()
            apc.stream_start = time.time()
           
            model_id = DEFAULT_MODEL

            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            tokenizer = self.get_tokenizer(model_id)
            model = self.get_model(model_id)

            # Prepare input with chat history
            input_text = self.prepare_input_with_history(text_prompt, chat_history)
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiving_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=50
            )

            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)

            # Update chat history
            self.update_chat_history(receiving_tab_id, text_prompt, outputs)

        except Exception as e:    
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            print(f"An error occurred: {e}")
            raise

        if logits_processor[0].generated_text:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiving_tab_id)

        return ''.join(out)

    def prepare_input_with_history(self, text_prompt, chat_history):
        # Prepare input text with chat history
        history_text = ""
        for entry in chat_history:
            history_text += f"Human: {entry['human']}\nAI: {entry['ai']}\n\n"
        return f"{history_text}Human: {text_prompt}\nAI:"

    def update_chat_history(self, tab_id, human_message, ai_response):
        # Update chat history for the given tab
        chat=apc.chats[tab_id]
        tokenizer=self.tokenizer[chat.model]
        decoded_response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
        self.chat_history[tab_id].append({
            "human": human_message,
            "ai": decoded_response
        })

class Hist_Flash_ResponseStreamer:
    subscribed = False
    def __init__(self):
        # Set your OpenAI API key here
        self.model = {}
        self.chat_history = {}
        self.tokenizer = {}
    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True,
                #low_cpu_mem_usage=True,
                attn_implementation="flash_attention_2"
            )
           
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]
    def stream_response(self, text_prompt, chatHistory, receiving_tab_id):
        # Create a chat completion request with streaming enabled
        if receiving_tab_id not in self.chat_history:
            self.chat_history[receiving_tab_id] = []
        chat_history = self.chat_history[receiving_tab_id]
        out = []
        from os.path import isfile
        chat = apc.chats[receiving_tab_id]
        txt = '\n'.join(split_text_into_chunks(text_prompt, 80))
        
        try:
            start = time.time()
            apc.stream_start = time.time()
           
            model_id = DEFAULT_MODEL

            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            tokenizer = self.get_tokenizer(model_id)
            model = self.get_model(model_id)

            # Prepare input with chat history
            input_text = self.prepare_input_with_history(text_prompt, chat_history)
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiving_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=50
            )

            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)

            # Update chat history
            self.update_chat_history(receiving_tab_id, text_prompt, outputs)

        except Exception as e:    
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            print(f"An error occurred: {e}")
            raise

        if logits_processor[0].generated_text:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiving_tab_id)

        return ''.join(out)

    def prepare_input_with_history(self, text_prompt, chat_history):
        # Prepare input text with chat history
        history_text = ""
        for entry in chat_history:
            history_text += f"Human: {entry['human']}\nAI: {entry['ai']}\n\n"
        return f"{history_text}Human: {text_prompt}\nAI:"

    def update_chat_history(self, tab_id, human_message, ai_response):
        # Update chat history for the given tab
        chat=apc.chats[tab_id]
        tokenizer=self.tokenizer[chat.model]
        decoded_response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
        self.chat_history[tab_id].append({
            "human": human_message,
            "ai": decoded_response
        })

class Hist_Full_ResponseStreamer:
    subscribed = False
    def __init__(self):
        # Set your OpenAI API key here
        self.model = {}
        self.chat_history = {}
        self.tokenizer = {}
    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                #torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True,
                #low_cpu_mem_usage=True,
                #attn_implementation="flash_attention_2"
            )
           
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]
    def stream_response(self, text_prompt, chatHistory, receiving_tab_id):
        # Create a chat completion request with streaming enabled
        if receiving_tab_id not in self.chat_history:
            self.chat_history[receiving_tab_id] = []
        chat_history = self.chat_history[receiving_tab_id]
        out = []
        from os.path import isfile
        chat = apc.chats[receiving_tab_id]
        txt = '\n'.join(split_text_into_chunks(text_prompt, 80))
        
        try:
            start = time.time()
            apc.stream_start = time.time()
           
            model_id = DEFAULT_MODEL

            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            tokenizer = self.get_tokenizer(model_id)
            model = self.get_model(model_id)

            # Prepare input with chat history
            input_text = self.prepare_input_with_history(text_prompt, chat_history)
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiving_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=50
            )

            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)

            # Update chat history
            self.update_chat_history(receiving_tab_id, text_prompt, outputs)

        except Exception as e:    
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            print(f"An error occurred: {e}")
            raise

        if logits_processor[0].generated_text:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiving_tab_id)

        return ''.join(out)

    def prepare_input_with_history(self, text_prompt, chat_history):
        # Prepare input text with chat history
        history_text = ""
        for entry in chat_history:
            history_text += f"Human: {entry['human']}\nAI: {entry['ai']}\n\n"
        return f"{history_text}Human: {text_prompt}\nAI:"

    def update_chat_history(self, tab_id, human_message, ai_response):
        # Update chat history for the given tab
        chat=apc.chats[tab_id]
        tokenizer=self.tokenizer[chat.model]
        decoded_response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
        self.chat_history[tab_id].append({
            "human": human_message,
            "ai": decoded_response
        })

class NoHist_Full_ResponseStreamer:
    subscribed = False
    def __init__(self):
        # Set your OpenAI API key here
        self.model = {}
        self.chat_history = {}
        self.tokenizer = {}
    def get_model(self, model_id):
        dtype = torch.bfloat16
        if model_id not in self.model:
            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                #torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True,
                #low_cpu_mem_usage=True,
                #attn_implementation="flash_attention_2"
            )
           
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Model already loaded")
        return self.tokenizer[model_id]
    def stream_response(self, text_prompt, chatHistory, receiving_tab_id):
        # Create a chat completion request with streaming enabled
        if receiving_tab_id not in self.chat_history:
            self.chat_history[receiving_tab_id] = []
        chat_history = self.chat_history[receiving_tab_id]
        out = []
        from os.path import isfile
        chat = apc.chats[receiving_tab_id]
        txt = '\n'.join(split_text_into_chunks(text_prompt, 80))
        
        try:
            start = time.time()
            apc.stream_start = time.time()
           
            model_id = DEFAULT_MODEL

            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig



            tokenizer = self.get_tokenizer(model_id)
            model = self.get_model(model_id)

            # Prepare input with chat history
            input_text = self.prepare_input_with_history(text_prompt, chat_history)
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiving_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,
                do_sample=True,
                temperature=1.0,
                top_p=0.95,
                top_k=50
            )

            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)

            # Update chat history
            self.update_chat_history(receiving_tab_id, text_prompt, outputs)

        except Exception as e:    
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            print(f"An error occurred: {e}")
            raise

        if logits_processor[0].generated_text:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiving_tab_id)

        return ''.join(out)

    def prepare_input_with_history(self, text_prompt, chat_history):
        # Prepare input text with chat history
        history_text = ""
        for entry in chat_history:
            history_text += f"Human: {entry['human']}\nAI: {entry['ai']}\n\n"
        return f"{history_text}Human: {text_prompt}\nAI:"

    def update_chat_history(self, tab_id, human_message, ai_response):
        # Update chat history for the given tab
        chat=apc.chats[tab_id]
        tokenizer=self.tokenizer[chat.model]
        decoded_response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
        self.chat_history[tab_id]=[]
        

class NoHist_8bit_ResponseStreamer:

    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}

 
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:





            apc.stream_start = time.time()
           
            model_id=DEFAULT_MODEL


            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

            
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)


            quantization_config_2 = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )


            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True #,
                #low_cpu_mem_usage=True
            )

            input_text = text_prompt
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiveing_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,  # limit the number of new tokens to generate
                do_sample=True,  # disable sampling to get deterministic output
                temperature=1.0,
                top_p=0.95,      # Nucleus sampling
                top_k=50         # Limiting to top_k choices
            )
            #print(outputs)
            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)



            if 0:
                msg=[]
                for chunk in outputs:
                    #pp(chunk)
                    if chunk.type == 'content_block_delta':
                        text = chunk.delta.text
                        print(text, end='', flush=True)
                        out.append(text)
                        msg.append(text)
                        pub.sendMessage('chat_output', message=f'{text}', tab_id=receiveing_tab_id)

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out) 

class NoHist_BFloat16_ResponseStreamer:

    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}

 
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:



            start = time.time()

            apc.stream_start = time.time()
           
            model_id=DEFAULT_MODEL


            from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

            
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)


            quantization_config_2 = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )


            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                #quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True ,
                low_cpu_mem_usage=True
            )

            input_text = text_prompt
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            logits_processor = LogitsProcessorList()
            logits_processor.append(StreamProcessor(tokenizer, model, receiveing_tab_id))

            outputs = model.generate(
                **input_ids,
                logits_processor=logits_processor,
                max_new_tokens=300,  # limit the number of new tokens to generate
                do_sample=True,  # disable sampling to get deterministic output
                temperature=1.0,
                top_p=0.95,      # Nucleus sampling
                top_k=50         # Limiting to top_k choices
            )
            #print(outputs)
            print("\nStreaming:", time.time() - logits_processor[0].start)
            print("\nTotal:", time.time() - start)



            if 0:
                msg=[]
                for chunk in outputs:
                    #pp(chunk)
                    if chunk.type == 'content_block_delta':
                        text = chunk.delta.text
                        print(text, end='', flush=True)
                        out.append(text)
                        msg.append(text)
                        pub.sendMessage('chat_output', message=f'{text}', tab_id=receiveing_tab_id)

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out) 

class NoHist_BFloat16_FlashAttn_ResponseStreamer:

    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}

 
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        #header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:




            
            apc.stream_start = time.time()
           
            model_id=DEFAULT_MODEL
            from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer


            start = time.time()
            model_id="google/gemma-2-27b-it"
            model_id="google/gemma-2-9b-it"
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                cache_dir="./cache",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                attn_implementation="flash_attention_2"
            )
            print("Model load:", time.time() - start)
            input_text = text_prompt
            input_ids = tokenizer(input_text, return_tensors="pt").to("cuda")

            # Set up the streamer
            streamer = TextIteratorStreamer(tokenizer)

            # Generate the text with streaming
            outputs = model.generate(
                **input_ids,
                streamer=streamer,
                max_new_tokens=300,  # Adjust as needed
                do_sample=True  # Disable sampling to get deterministic output
            )
            print("Generated:", time.time() - start)
            # Print the streamed output
            for new_text in streamer:
                #print(123)
                time.sleep(.01)
                
                print(new_text, end='', flush=True)
                pub.sendMessage('chat_output', message=f'{new_text}', tab_id=receiveing_tab_id)

            print("\nTime:", time.time() - start)

            if 0:
                msg=[]
                for chunk in outputs:
                    #pp(chunk)
                    if chunk.type == 'content_block_delta':
                        text = chunk.delta.text
                        print(text, end='', flush=True)
                        out.append(text)
                        msg.append(text)
                        pub.sendMessage('chat_output', message=f'{text}', tab_id=receiveing_tab_id)

        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out) 
            
class _History_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}

 
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        try:

            import base64
            from anthropic import Anthropic


            client = Anthropic()


            #b_data=get_base64_encoded_image("test.jpeg")
            
            content = []

            prompt=text_prompt
            content.append({"type": "text", "text": prompt})
            message_list = chat_history + [
                {
                    "role": 'user',
                    "content": content
                }
            ]
            pp(chat)
            stream = client.messages.create(
                model=chat.model,
                max_tokens=int(chat.max_tokens),
                temperature=float(chat.temperature),
                top_p=float(chat.top_p),
                stop_sequences=["Human:", "User:", "Assistant:", "AI:"],
                
                #system="You have perfect artistic sense and pay great attention to detail which makes you an expert at describing images.",
                system=chat.system_prompt,
                messages=message_list,
                
                stream=True
                
            )
            #print(response.content[0].text)

            msg=[]
            for chunk in stream:
                #pp(chunk)
                if chunk.type == 'content_block_delta':
                    text = chunk.delta.text
                    print(text, end='', flush=True)
                    out.append(text)
                    msg.append(text)
                    pub.sendMessage('chat_output', message=f'{text}', tab_id=receiveing_tab_id)

            assistant_message = {
                "role": "assistant",
                "content": ''.join(msg)
            }
            
            chat_history.append(message_list[-1])  # Add user's message to history
            chat_history.append(assistant_message)  # Add assistant's response to history
            
            #prompt2 = "Now, can you tell me about the color palette used in this artwork?"
        
        except Exception as e:    


            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')

            print(f"An error occurred: {e}")
            raise
            #return ''
        

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)   




class Gemma_Google_Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id, chat):
        super(Gemma_Google_Copilot_DisplayPanel, self).__init__(parent)
        apc.chats[tab_id]=chat
        # Create a splitter window
        self.copilot_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)
        self.tab_id=tab_id

        # Initialize the notebook_panel and logPanel
        self.notebook_panel=notebook_panel = MyNotebookCodePanel(self.copilot_splitter, tab_id)
        notebook_panel.SetMinSize((-1, 50))
        #notebook_panel.SetMinSize((800, -1))
        self.chatPanel = Copilot_DisplayPanel(self.copilot_splitter, tab_id)
        self.chatPanel.SetMinSize((-1, 50))

        # Add notebook panel and log panel to the splitter window
        #self.splitter.AppendWindow(notebook_panel)
        #self.splitter.AppendWindow(self.logPanel)
        self.copilot_splitter.SplitVertically( self.chatPanel, notebook_panel) 
        #print(111, self.GetSize().GetWidth() // 2)
        self.copilot_splitter.SetSashPosition(500)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.copilot_splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Set initial sash positions
        #
        self.Bind(wx.EVT_SIZE, self.OnResize)
    def GetCode(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        return self.notebook_panel.codeCtrl.GetText()
    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip()        

                         
class StyledTextDisplay(stc.StyledTextCtrl, GetClassName, NewChat, Scroll_Handlet):
    def __init__(self, parent):
        super(StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        NewChat.__init__(self)
        Scroll_Handlet.__init__(self)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.SetWrapMode(stc.STC_WRAP_WORD)
        
        self.SetLexer(stc.STC_LEX_PYTHON)
        text_keywords = 'nude Ukraine Ukrainian Tryzub flag blue yellow picture model image file artist artistic artistically color light scene question answer description mood texture emotion feeling sense impression atmosphere tone style technique brushstroke composition perspective'
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")  # Default
        
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")  # Number
        #self.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")  # String
        #self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")  # Character
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")  # Triple double quotes
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,back:#FFFFFF")  # Identifiers
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')

        self.SetKeyWords(0, text_keywords)

        # Set face
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')
        #pub.subscribe(self.AddOutput, 'chat_output')
        self.Bind(wx.EVT_SIZE, self.OnResize)

    def OnResize(self, event):
        self.Refresh()
        event.Skip()

    def _OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            self.AskQuestion()
        else:
            event.Skip()

    def AskQuestion(self):
        pass  # Implement if needed
    def IsTextInvisible(self):
        last_position = self.GetTextLength()
        line_number = self.LineFromPosition(last_position)
        first_visible_line = self.GetFirstVisibleLine()
        lines_on_screen = self.LinesOnScreen()
        return not (first_visible_line <= line_number < first_visible_line + lines_on_screen)

    def AddOutput(self, message):
        wx.CallAfter(self._AddOutput, message)
    def _AddOutput(self, message):
        self.AppendText(message)
        if self.IsTextInvisible():

            if self.scrolled:
            #self.answer_output.MakeCellVisible(i, 0)
        
                self.GotoPos(self.GetTextLength())
class code_StyledTextDisplay(stc.StyledTextCtrl, GetClassName, NewChat, Scroll_Handlet):
    def __init__(self, parent):
        super(code_StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        NewChat.__init__(self)
        Scroll_Handlet.__init__(self)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.SetLexer(stc.STC_LEX_PYTHON)
        self.SetWrapMode(stc.STC_WRAP_WORD)
        python_keywords = 'self False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with both yield'


        self.SetKeyWords(0, python_keywords)
        # Set Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")  # Default
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#008000,back:#FFFFFF")  # Comment
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")  # Number
        self.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")  # String
        self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")  # Character
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")  # Triple double quotes
        self.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#00008B,back:#FFFFFF")  # Class name
        self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#00008B,back:#FFFFFF")  # Function or method name
        self.StyleSetSpec(stc.STC_P_OPERATOR, "fore:#000000,back:#FFFFFF")  # Operators
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,back:#FFFFFF")  # Identifiers
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')
        # Set face
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')
        #pub.subscribe(self.AddOutput, 'chat_output')
        self.Bind(wx.EVT_SIZE, self.OnResize)

    def OnResize(self, event):
        self.Refresh()
        event.Skip()

    def _OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            self.AskQuestion()
        else:
            event.Skip()

    def AskQuestion(self):
        pass  # Implement if needed
    def IsTextInvisible(self):
        last_position = self.GetTextLength()
        line_number = self.LineFromPosition(last_position)
        first_visible_line = self.GetFirstVisibleLine()
        lines_on_screen = self.LinesOnScreen()
        return not (first_visible_line <= line_number < first_visible_line + lines_on_screen)

    def AddOutput(self, message):
        wx.CallAfter(self._AddOutput, message)
    def _AddOutput(self, message):
        self.AppendText(message)
        if self.IsTextInvisible():

            if self.scrolled:
            #self.answer_output.MakeCellVisible(i, 0)
        
                self.GotoPos(self.GetTextLength())      

class Gemma_Google_Chat_DisplayPanel(code_StyledTextDisplay):
    def __init__(self, parent, tab_id, chat):
        code_StyledTextDisplay.__init__(self,parent)
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
        self.tab_id=tab_id

        pub.subscribe(self.AddChatOutput, 'chat_output')
        #pub.subscribe(lambda message, tab_id: self.AddOutput(message, tab_id), 'chat_output')
        #pub.subscribe(self.OnShowTabId, 'show_tab_id') 
    def IsTabVisible(self):
        # Get the parent notebook
        parent_notebook = self.GetParent()

        # Check if the current page is the selected page in the parent notebook
        return parent_notebook.GetPage(parent_notebook.GetSelection()) == self
            
    def AddChatOutput(self, message, tab_id):
        #print(1111, self.tab_id,tab_id, self.tab_id==tab_id, message)
        #print('Chat', tab_id, self.IsTabVisible())
        if self.tab_id==tab_id:
            #start_pos = self.GetLastPosition()
            if 1: #for line in message.splitlines():

                wx.CallAfter(self.AddOutput, message)
                
                #end_pos = self.chatDisplay.GetLastPosition()
                #self.chatDisplay.SetStyle(start_pos, end_pos, wx.TextAttr(wx.BLACK))        
    def OnShowTabId(self):
        print('show_tab_id', self.tab_id)

             
class Gemma_Google_ChatDisplayNotebookPanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, vendor_tab_id, ws_name):
        super(Gemma_Google_ChatDisplayNotebookPanel, self).__init__(parent)
        self.tabs={}
        self.ws_name=ws_name
        self.chat_notebook = wx.Notebook(self, style=wx.NB_BOTTOM)
        self.vendor_tab_id=vendor_tab_id
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chat_notebook, 1, wx.EXPAND)
        #self.chat_notebook.SetActiveTabColour(wx.RED)
        #self.chat_notebook.SetNonActiveTabTextColour(wx.BLUE)
        self.SetSizer(sizer)    
        self.chat_notebook.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.chat_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.chat_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        if not Gemma_Google_ChatDisplayNotebookPanel.subscribed:
            pub.subscribe(self.OnWorkspaceTabChanging, 'workspace_tab_changing')
            pub.subscribe(self.OnWorkspaceTabChanged, 'workspace_tab_changed')
            pub.subscribe(self.OnVendorspaceTabChanging, 'vendor_tab_changing')   
            pub.subscribe(self.OnVendorspaceTabChanged, 'vendor_tab_changed')
            Gemma_Google_ChatDisplayNotebookPanel.subscribed=True
    def get_active_chat_panel(self):
        active_chat_tab_index = self.chat_notebook.GetSelection()
        if active_chat_tab_index == wx.NOT_FOUND:
            return None
        return self.chat_notebook.GetPage(active_chat_tab_index)
            
    def OnWorkspaceTabChanging(self, message):
        print(self.__class__.__name__)
        print('OnWorkspaceTabChanging', message, self.ws_name)        
        if message==self.ws_name:
            active_chat_panel = self.get_active_chat_panel()
            if active_chat_panel is not None:
                active_tab_id = active_chat_panel.tab_id
                #print('OnWorkspaceTabChanging dd', message, self.vendor_tab_id, self.ws_name, active_tab_id)
                pub.sendMessage('save_question_for_tab_id', message=active_tab_id)
            else:
                print('No active chat panel found')
        
    def OnWorkspaceTabChanged(self, message):
        if message==self.ws_name:
            active_chat_panel = self.get_active_chat_panel()
            if active_chat_panel is not None:
                active_tab_id = active_chat_panel.tab_id
                #print('OnWorkspaceTabChanged', message, self.vendor_tab_id, self.ws_name, active_tab_id)
            if 1:
                #pub.sendMessage('restore_question_for_tab_id', tab_id=active_tab_id)

                assert active_tab_id in apc.chats
                chat=apc.chats[active_tab_id]
                print('swapping', active_tab_id )
                pub.sendMessage('swap_input_panel', tab_id=active_tab_id)
                            

    def OnVendorspaceTabChanging(self, message):
        #print('TODO OnVendorspaceTabChanging', message)
        #raise NotImplementedError
        pass
    def OnVendorspaceTabChanged(self, message):
       
        #print('TODO OnVendorspaceTabChanged', message)
        
        #raise NotImplementedError
        pass
    def OnMouseMotion(self, event):
        # Get the mouse position
        position = event.GetPosition()
        # Get the tab index under the mouse position
        #print(self.notebook.HitTest(position))
        tab_index, _= self.chat_notebook.HitTest(position)

        #print(tab_index)
        # If the mouse is over a tab
        if tab_index >= 0:
            # Get the tab text
            tab_text = self.chat_notebook.GetPageText(tab_index)
            # Set the tab tooltip
            tt=self.GetToolTipText()
            self.chat_notebook.SetToolTip(f'{tt}/{tab_text}')
        else:
            self.chat_notebook.SetToolTip(None)
        event.Skip()
    def GetToolTipText(self):
        tab_id=self.tabs[self.chat_notebook.GetSelection()]
        return f'{apc.default_workspace.name}/{apc.default_workspace.vendor} {apc.chats[tab_id].chat_type}'
        

    def AddTab(self, chat):
        chat_notebook=self.chat_notebook
        title=f'{chat.chat_type}: {chat.name}'
        title=f'{chat.name} | {chat.streamer_name}'
        chatDisplay=None
        tab_id=(chat.workspace, chat.chat_type, chat.vendor,self.vendor_tab_id, chat_notebook.GetPageCount())
        self.tabs[chat_notebook.GetPageCount()]=tab_id
        if 1:
            #pp(panels.__dict__)
            #pp(chat.__dict__)
            display_panel = f'{chat.vendor}_{chat.workspace}_{chat.chat_type}_{panels.chat}'
            #print('display_panel', display_panel)
            try:
                assert display_panel in globals(), display_panel
                print(f'\t\tAdding {chat.workspace} "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
                chatDisplay = cls (chat_notebook, tab_id=tab_id, chat=chat)
                #chatDisplay.SetFocus()
                if 1:
                    apc.chats[tab_id]=chat
                    pub.sendMessage('swap_input_panel',  tab_id=tab_id)
            except AssertionError:
                #raise AssertionError(f"Display class '{display_panel}' does not exist.")
                raise
        assert chatDisplay   
        chat_notebook.AddPage(chatDisplay, title)
        chat_notebook.SetSelection(chat_notebook.GetPageCount() - 1)  
        
        chat_tab_id = chat_notebook.GetPageCount() - 1
        #self.SetTabLabelColor(chat_tab_id, wx.Colour(255, 0, 0))
        chatDisplay.tab_id=self.tab_id=tab_id=(chat.workspace,chat.chat_type, chat.vendor, self.vendor_tab_id, chat_tab_id)
        apc.chats[tab_id]=chat
        apc.chat_panels[tab_id]=chatDisplay
        
        pub.sendMessage('set_chat_defaults', tab_id=tab_id)

    def OnPageChanging(self, event):
        # Code to execute when the notebook page is about to be changed
        #print("Notebook page is about to be changed")
        # Get the index of the new tab that is about to be selected
        nb=event.GetEventObject()
        oldTabIndex = event.GetSelection()
        current_chatDisplay = nb.GetPage(oldTabIndex)
        #print('OnPageChanging 111', current_chatDisplay.tab_id)
        pub.sendMessage('save_question_for_tab_id', message=current_chatDisplay.tab_id)
  
        event.Skip()

    
    def OnPageChanged(self, event):
        # Code to execute when the notebook page has been changed
        nb=event.GetEventObject()
        newtabIndex = nb.GetSelection()
        current_chatDisplay = nb.GetPage(newtabIndex)
        tab_id=current_chatDisplay.tab_id
        #print('OnPageChanged 222', tab_id)
        #pub.sendMessage('restore_question_for_tab_id', tab_id=tab_id)
        current_chatDisplay = nb.GetPage(newtabIndex)
        #pp(current_chatDisplay.tab_id)
        #e()
        if tab_id in apc.chats:
            chat=apc.chats[tab_id]
            pub.sendMessage('swap_input_panel', tab_id=tab_id)
        # Continue processing the event
        event.Skip()          



    def get_latest_chat_tab_id(self):
        return self.GetPageCount() - 1

class Gemma_Google_Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel_Google_Gemma):
    subscribed=False
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Gemma_Google_Copilot_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        self.chat_type=chat.chat_type
        chatHistory[self.tab_id]=[]
        chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Copilot[default_copilot_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask copilot {tab_id}:')
       
        self.model_dropdown = wx.ComboBox(self, choices=model_list, style=wx.CB_READONLY)
        self.model_dropdown.SetValue(chat.model)
        
        self.model_dropdown.Bind(wx.EVT_COMBOBOX, self.OnModelChange)

        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)

        # Create a HyperlinkCtrl
        
        self.hyperlink = wx.adv.HyperlinkCtrl(self, id=wx.ID_ANY, label="AiStudio", url="https://aistudio.google.com/app/prompts/new_chat?model=gemma-2-27b-it")
        
        # Bind the EVT_HYPERLINK event to an event handler
        self.hyperlink.Bind(wx.adv.EVT_HYPERLINK, self.onHyperlinkClick)
        

        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.model_dropdown, 0, wx.ALIGN_CENTER)
        self.pause_panel=pause_panel=PausePanel(self, self.tab_id)
        askSizer.Add(pause_panel, 0, wx.ALL)
        Base_InputPanel_Google_Gemma.AddButtons_Level_1(self, askSizer)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.hyperlink, 0, wx.ALIGN_CENTER)
        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)
        if 1:
            q= apc.chats[self.tab_id].question
            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=chat.model
            chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]

        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        #self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        Base_InputPanel_Google_Gemma.AddButtons_Level_2(self, h_sizer)

        sizer.Add(askSizer, 0, wx.ALIGN_CENTER)
        sizer.Add(h_sizer, 0, wx.ALIGN_LEFT)


        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0
        if not Gemma_Google_Copilot_InputPanel.subscribed:
            #pub.subscribe(self.SetException, 'fix_exception')
            pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
            #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
            #pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
            Gemma_Google_Copilot_InputPanel.subscribed=True
        wx.CallAfter(self.inputCtrl.SetFocus)
        self.rs={}
    def onHyperlinkClick(self, event):
        # Custom action when the hyperlink is clicked
        # For example, open the URL in a web browser
        import webbrowser
        webbrowser.open(self.hyperlink.GetURL())        
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask copilot {tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            assert self.chat_type==tab_id[1]
            chat=apc.chats[tab_id]
  

            self.tabs[self.tab_id]=dict(q=chat.question)
            chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]
            questionHistory[self.tab_id]=[]
            currentModel[self.tab_id]=chat.model        
    def OnModelChange(self, event):
        # Get the selected model
        selected_model = self.model_dropdown.GetValue()
        chat=apc.chats[self.tab_id]
        chat.model=selected_model
        # Print the selected model
        #print(f"Selected model: {selected_model}")

        # You can add more code here to do something with the selected model

        # Continue processing the event
        event.Skip()

    def _SaveQuestionForTabId(self, message):
        global currentModel
        q=self.inputCtrl.GetValue()
        self.tabs[message]=dict(q=q)
        currentModel[message]=self.model_dropdown.GetValue()
        if 0:
            d={"role": "user", "content":q}
            if self.tab_id in chatHistory:
                if d not in chatHistory[self.tab_id]:
                    chatHistory[self.tab_id] += [{"role": "user", "content":q}]


    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        #print('Ask button clicked')
        self.AskQuestion()
    def AskQuestion(self):
        global chatHistory, questionHistory, currentQuestion,currentModel
        # Get the content of the StyledTextCtrl
        #print('current tab_id', self.q_tab_id)
        #pub.sendMessage('show_tab_id')
        self.Base_OnAskQuestion()
        question = self.inputCtrl.GetValue()
        if not question:
            self.log('There is no question!', color=wx.RED)
        else:
            question = self.inputCtrl.GetValue()
            self.log(f'Asking question: {question}')
            pub.sendMessage('start_progress')
            #code=???
            chatDisplay=apc.chat_panels[self.tab_id]
            code=chatDisplay.GetCode(self.tab_id)
            #print(888, chatDisplay.__class__.__name__)
            #code='print(1223)'
            chat=apc.chats[self.tab_id]
            prompt=evaluate(all_system_templates[chat.workspace].Copilot.FIX_CODE, AttrDict(dict(code=code, input=question)))
            chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.tab_id].append(question)
            currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
            currentModel[self.tab_id]=self.model_dropdown.GetValue()




            header=fmt([['\n'.join(self.split_text_into_chunks(question, 80))+'\nAnswer:']], [f'User Question | {chat.model}'])

            # DO NOT REMOVE THIS LINE
            print(header)
            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=self.tab_id)
            #pub.sendMessage('chat_output', message=f'{prompt}\n')
            
            #out=rs.stream_response(prompt, chatHistory[self.q_tab_id])  
            chat.question=question
            if 'system_prompt' not in chat:
                system= chat.get('system', 'SYSTEM')
                chat.question=question
                chat.system_prompt=evaluate(all_system_templates[chat.workspace].Copilot[system], dict2(question=chat.question))
                pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id)        
            else:
                pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id) 

            threading.Thread(target=self.stream_response, args=(prompt, chatHistory, self.tab_id, self.model_dropdown.GetValue())).start()

    def stream_response(self, prompt, chatHistory, tab_id, model):
        # Call stream_response and store the result in out
        self.receiveing_tab_id=tab_id
        chat=apc.chats[tab_id]
        rs = self.get_chat_streamer(tab_id,globals())

        #rs=ResponseStreamer()
        out = rs.stream_response(prompt, chatHistory[tab_id], self.receiveing_tab_id)
        if out:
            chatHistory[tab_id].append({"role": "assistant", "content": out}) 
        pub.sendMessage('stop_progress')
        log('Done.')
        set_status('Done.')        

    def PrevQuestion(self):
        qid=currentQuestion[self.tab_id]
        if qid:
            q=questionHistory[self.tab_id][qid-1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.tab_id]=qid-1
        else:
            self.log('No previous question.', color=wx.RED)
    def NextQuestion(self):
        qid=currentQuestion[self.tab_id]
        if len(questionHistory[self.tab_id])>qid+1:
            q=questionHistory[self.tab_id][qid+1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.tab_id]=qid+1
        else:
            self.log('No next question.', color=wx.RED)
    def OnCharHook(self, event):
        if event.ControlDown() and  event.GetKeyCode() == wx.WXK_RETURN:
            self.AskQuestion()
        elif event.ControlDown() and event.GetKeyCode() == wx.WXK_RIGHT:
            log("Ctrl+-> pressed")
            set_status("Ctrl+-> pressed")
            self.NextQuestion()
        elif event.ControlDown() and event.GetKeyCode() == wx.WXK_LEFT:
            self.log("Ctrl+<- pressed")
            set_status("Ctrl+<- pressed")
            self.PrevQuestion()
                       
        else:
            event.Skip()


    def log(self, message, color=wx.BLUE):
        
        pub.sendMessage('log', message=f'{message}', color=color)

   
class MyNotebookCodePanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, tab_id):
        super(MyNotebookCodePanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        
        self.notebook = notebook
        
        self.codeCtrl = stc.StyledTextCtrl(notebook)
        self.codeCtrl.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        self.codeCtrl.SetMarginWidth(0, self.codeCtrl.TextWidth(stc.STC_STYLE_LINENUMBER, '100'))
        self.codeCtrl.StyleSetForeground(stc.STC_STYLE_LINENUMBER, wx.Colour(75, 75, 75))
        
        self.codeCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.codeCtrl.SetLexer(stc.STC_LEX_PYTHON)
        python_keywords = 'self False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with both yield'

        self.codeCtrl.SetKeyWords(0, python_keywords)
        # Set Python styles
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFAULT, 'fore:#000000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTLINE, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_NUMBER, 'fore:#008080')
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRING, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_CHARACTER, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD, 'fore:#000080,bold')
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLE, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_CLASSNAME, 'fore:#0000FF,,weight:bold')
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFNAME, 'fore:#008080,,weight:bold')
        self.codeCtrl.StyleSetSpec(stc.STC_P_OPERATOR, 'fore:#000000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#0000FF')
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTBLOCK, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRINGEOL, 'fore:#008000,back:#E0C0E0,eol')
        self.codeCtrl.StyleSetSpec(stc.STC_P_DECORATOR, 'fore:#805000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD2, 'fore:#800080,bold')
        # Set Python styles
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#008000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#00008B,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#00008B,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_OPERATOR, "fore:#000000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')
        apc.editor = self.codeCtrl 
        
        #
        #pp(apc.chats)
        chat=apc.chats[tab_id] 
        #pp(chat) 
        if 'default_file' in chat:
            fn=chat.default_file
            print(fn)
            #e()
        else:
            fn=__file__
        self.load_file(fn)
        notebook.AddPage(self.codeCtrl, fn)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.Layout()
        if not MyNotebookCodePanel.subscribed:

            pub.subscribe(self.ExecuteFile, 'execute')
            pub.subscribe(self.OnSaveFile, 'save_file')
            MyNotebookCodePanel.subscribed=True

    def OnSaveFile(self):
        #print('Saving file...')
        with open(fn, 'w') as file:
            data = self.codeCtrl.GetValue().replace('\r\n', '\n')
            file.write(data)

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            print('Executing Ctrl+A...')
        else:
            event.Skip()

    def load_file(self, file_path):
        with open(file_path, 'r') as file:
            data = file.read()
        data = data.replace('\r\n', '\n')
        self.codeCtrl.SetValue(data)

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('E') or event.GetKeyCode() == wx.WXK_RETURN):
            self.log('Executing...')
            self.ExecuteFile()
            self.log('Done.')
        else:
            event.Skip()

    def log(self, message):
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}')

    def output(self, message):
        pub.sendMessage('output', message=f'{message}')

    def exception(self, message):
        pub.sendMessage('exception', message=f'{message}')

    def ExecuteFile(self):
        code = self.codeCtrl.GetText()
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(code.encode())
            temp_file_name = f.name
        
        local_dir = os.getcwd()
        command = f'start cmd /k "python {fn} "'
        #remove existing conda env variables from shell initialization
        #new_env = {k: v for k, v in os.environ.items() if not k.startswith('CONDA') and not k.startswith('VIRTUAL') and not k.startswith('PROMPT')}
        apc.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        cwd=local_dir, creationflags=subprocess.CREATE_NO_WINDOW)


        if 0:
            stdout, stderr = process.communicate()
            if stderr:
                self.output(stdout.decode())
                self.exception(stderr.decode())
                ex = CodeException(stderr.decode())
                #self.fixButton.Enable()
                pub.sendMessage('fix_exception', message=ex)
            else:
                self.output(stdout.decode())

    def _ExecuteFile(self):
        code = self.codeCtrl.GetText()
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(code.encode())
            temp_file_name = f.name
        predefined_dir = 'path/to/your/directory'
        local_dir = os.getcwd()
        process = subprocess.Popen(['python', fn], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   cwd=local_dir)
        stdout, stderr = process.communicate()
        if stderr:
            self.output(stdout.decode())
            self.exception(stderr.decode())
            ex = CodeException(stderr.decode())
            #self.fixButton.Enable()
            pub.sendMessage('fix_exception', message=ex)
        else:
            self.output(stdout.decode())

class Copilot_DisplayPanel(code_StyledTextDisplay):
    def __init__(self, parent, tab_id):
        code_StyledTextDisplay.__init__(self,parent)
        
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
     
        self.tab_id=tab_id
        pub.subscribe(self.AddChatOutput, 'chat_output')
        #pub.subscribe(lambda message, tab_id: self.AddOutput(message, tab_id), 'chat_output')
        #pub.subscribe(self.OnShowTabId, 'show_tab_id') 
    def IsTabVisible(self):
        # Get the parent notebook
        parent_notebook = self.GetParent().GetParent().GetParent()
        #print ('Copilot', self.tab_id, parent_notebook, parent_notebook.GetSelection())
        # Check if the current page is the selected page in the parent notebook
        return parent_notebook.GetPage(parent_notebook.GetSelection())       
    def AddChatOutput(self, message, tab_id):
        #print(1111, self.tab_id,tab_id, self.tab_id==tab_id, message)
        #print('Copilot',  self.IsTabVisible(), self.tab_id)
        if self.tab_id==tab_id:
            #start_pos = self.GetLastPosition()
            if 1: #for line in message.splitlines():

                wx.CallAfter(self.AddOutput, message)
                
                #end_pos = self.chatDisplay.GetLastPosition()
                #self.chatDisplay.SetStyle(start_pos, end_pos, wx.TextAttr(wx.BLACK))        
    def OnShowTabId(self):
        print('show_tab_id', self.tab_id)

          




class Gemma_Google_Chat_InputPanel(wx.Panel, NewChat,GetClassName, Base_InputPanel_Google_Gemma):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Gemma_Google_Chat_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        chatHistory[self.tab_id]=[]
        #pp(chat)
        chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask chatgpt {tab_id}:')
        
        self.chat_type=chat.chat_type
        self.model_dropdown = wx.ComboBox(self, choices=model_list, style=wx.CB_READONLY)
        self.model_dropdown.SetValue(chat.model)
        
        self.model_dropdown.Bind(wx.EVT_COMBOBOX, self.OnModelChange)

        

        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)



        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.model_dropdown, 0, wx.ALIGN_CENTER)
        self.pause_panel=pause_panel=PausePanel(self, self.tab_id)
        askSizer.Add(pause_panel, 0, wx.ALL)
   
        askSizer.Add((1,1), 1, wx.ALIGN_CENTER|wx.ALL)
        Base_InputPanel_Google_Gemma.AddButtons_Level_1(self, askSizer)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)
        if 1:
            q=apc.chats[tab_id].question

            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=chat.model

            chat=apc.chats[tab_id]
            chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
         


        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        #self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        Base_InputPanel_Google_Gemma.AddButtons_Level_2(self, h_sizer)

        sizer.Add(askSizer, 0, wx.ALIGN_CENTER)
        sizer.Add(h_sizer, 0, wx.ALIGN_LEFT)

        
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0

        pub.subscribe(self.SetException, 'fix_exception')
        pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
        #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        #pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)
        self.rs={}
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask chatgpt {tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            assert self.chat_type==tab_id[1]
            
            #pp(apc.chats[tab_id])
            #e()
            self.tabs[self.tab_id]=dict(q=apc.chats[tab_id].question)
            chat=apc.chats[tab_id]
            chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
            questionHistory[self.tab_id]=[]
            currentModel[self.tab_id]=chat.model


    def _SetTabId(self, tab_id):
        global chatHistory, questionHistory, currentModel
        self.tab_id=tab_id
      
        return self

                      
    def OnModelChange(self, event):
        # Get the selected model
        selected_model = self.model_dropdown.GetValue()

        # Print the selected model
        print(f"Selected model 111: {selected_model}")
        chat=apc.chats[self.tab_id]
        chat.model=selected_model        

        # You can add more code here to do something with the selected model

        # Continue processing the event
        event.Skip()


        
    def _SaveQuestionForTabId(self, message):
        global currentModel
        q=self.inputCtrl.GetValue()
        self.tabs[message]=dict(q=q)
        currentModel[message]=self.model_dropdown.GetValue()
        if 0:
            d={"role": "user", "content":q}
            if self.tab_id in chatHistory:
                if d not in chatHistory[self.tab_id]:
                    chatHistory[self.tab_id] += [{"role": "user", "content":q}]


    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        #print('Ask button clicked')
        self.AskQuestion()
    def AskQuestion(self):
        global chatHistory, questionHistory, currentQuestion,currentModel
        # Get the content of the StyledTextCtrl
        #print('current tab_id', self.q_tab_id)
        
        #pub.sendMessage('show_tab_id')
        #pp(chatHistory)
        self.Base_OnAskQuestion()           
        question = self.inputCtrl.GetValue()
        if not question:
            self.log('There is no question!', color=wx.RED)
        else:
            question = self.inputCtrl.GetValue()
            self.log(f'Asking question: {question}')
            pub.sendMessage('start_progress')
            chat=apc.chats[self.tab_id]
            prompt=evaluate(all_system_templates[chat.workspace].Chat.PROMPT, AttrDict(dict(question=question)))
            chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.tab_id].append(question)
            currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
            currentModel[self.tab_id]=self.model_dropdown.GetValue()


            header=fmt([['\n'.join(self.split_text_into_chunks(question, 80))+'\nAnswer:']], [f'User Question | {chat.model}'])
            # DO NOT REMOVE THIS LINE
            print(header)
            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=self.tab_id)
            #pub.sendMessage('chat_output', message=f'{prompt}\n')
            if 'system_prompt' not in chat:
                system= chat.get('system', 'SYSTEM')
                chat.question=question
                chat.system_prompt=evaluate(all_system_templates[chat.workspace].Chat[system], dict2(question=chat.question))
                pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id)        
            else:
                pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id) 
            self.askButton.Disable()
            threading.Thread(target=self.stream_response, args=(prompt, chatHistory, self.tab_id, self.model_dropdown.GetValue())).start()


    def stream_response(self, prompt, chatHistory, tab_id, model):
        # Call stream_response and store the result in out
        self.receiveing_tab_id=tab_id
        chat=apc.chats[tab_id]


        # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
        rs = self.get_chat_streamer(tab_id, globals())
        out = rs.stream_response(prompt, chatHistory[tab_id], self.receiveing_tab_id)
        if out:
            chatHistory[tab_id].append({"role": "assistant", "content": out}) 
        pub.sendMessage('stop_progress')
        log('Done.')
        set_status('Done.')  
        wx.CallAfter(self.askButton.Enable)      

    def PrevQuestion(self):
        qid=currentQuestion[self.tab_id]
        if qid:
            q=questionHistory[self.tab_id][qid-1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.tab_id]=qid-1
        else:
            self.log('No previous question.', color=wx.RED)
    def NextQuestion(self):
        qid=currentQuestion[self.tab_id]
        if len(questionHistory[self.tab_id])>qid+1:
            q=questionHistory[self.tab_id][qid+1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.tab_id]=qid+1
        else:
            self.log('No next question.', color=wx.RED)
    def OnCharHook(self, event):
        if event.ControlDown() and  event.GetKeyCode() == wx.WXK_RETURN:
            self.AskQuestion()
        elif event.ControlDown() and event.GetKeyCode() == wx.WXK_RIGHT:
            log("Ctrl+-> pressed")
            set_status("Ctrl+-> pressed")
            self.NextQuestion()
        elif event.ControlDown() and event.GetKeyCode() == wx.WXK_LEFT:
            self.log("Ctrl+<- pressed")
            set_status("Ctrl+<- pressed")
            self.PrevQuestion()
                       
        else:
            event.Skip()


    def log(self, message, color=wx.BLUE):
        
        pub.sendMessage('log', message=f'{message}', color=color)
