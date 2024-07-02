

import argparse
import time, random
from datetime import datetime
import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
import time, glob,threading, traceback
import os, sys  
from os.path import join, isfile
from include.Prompt.Base.Base_InputPanel_Anthropic_Claude import Base_InputPanel_Anthropic_Claude

import base64
import requests
#import openai

from pubsub import pub
from pprint import pprint as pp 
from include.Common import *
#from include.Common_MiniCPM import Base_InputPanel
from include.fmt import fmt, pfmt, pfmtd, fmtd

e=sys.exit
import include.config.init_config as init_config 
apc = init_config.apc
default_chat_template='SYSTEM'
default_copilot_template='SYSTEM_CHATTY'


DEFAULT_MODEL='claude-3-haiku-20240307'

model_list=['claude-3-5-sonnet-20240620','claude-3-opus-20240229',
            'claude-3-sonnet-20240229','claude-3-haiku-20240307']

dir_path = 'template'

chatHistory,  currentQuestion, currentModel = apc.chatHistory,  apc.currentQuestion, apc.currentModel
questionHistory= apc.questionHistory
all_templates, all_chats, all_system_templates = apc.all_templates, apc.all_chats, apc.all_system_templates
panels     = AttrDict(dict(workspace='WorkspacePanel', vendor='ChatDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))

class NoHist_ResponseStreamer:
    
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id,  prompt_path):
        # Create a chat completion request with streaming enabled
       
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

            from PIL import Image
            import io
            import base64

            def get_base64_encoded_image(image_path):
                # Open the image and convert it to JPEG
                with Image.open(image_path) as image:
                    with io.BytesIO() as buffer:
                        image.convert('RGB').save(buffer, format="JPEG")
                        binary_data = buffer.getvalue()
                
                # Encode the JPEG binary data to base64
                base_64_encoded_data = base64.b64encode(binary_data)
                base64_string = base_64_encoded_data.decode('utf-8')
                return base64_string

            #b_data=get_base64_encoded_image("test.jpeg")
            ifn=image_path[0]
            b_data=get_base64_encoded_image(ifn)

            prompt=text_prompt
            message_list = [
                {
                    "role": 'user',
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b_data}},
                        {"type": "text", "text": prompt}
                    ]
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

        
            for chunk in stream:
                #pp(chunk)
                if chunk.type == 'content_block_delta':
                    text = chunk.delta.text
                    print(text, end='', flush=True)
                    out.append(text)
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



class Hist_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}
        #pub.subscribe(self.load_random_images, 'load_random_images')
        if  not pHist_ResponseStreamer.subscribed:
                
            pub.subscribe(self.load_random_prompts, 'load_random_prompts')
            pHist_ResponseStreamer.subscribed=True    
    def load_random_prompts(self, tab_id):
        
        if tab_id in     self.chat_history:
            print(  'Clearing history load_random_prompts', tab_id)
            del self.chat_history[tab_id]    
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id,  prompt_path):
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

            from PIL import Image
            import io
            import base64

            def get_base64_encoded_image(ifn):
                # Open the image and convert it to JPEG
                with Image.open(ifn) as image:
                    with io.BytesIO() as buffer:
                        image.convert('RGB').save(buffer, format="JPEG")
                        binary_data = buffer.getvalue()
                
                # Encode the JPEG binary data to base64
                base_64_encoded_data = base64.b64encode(binary_data)
                base64_string = base_64_encoded_data.decode('utf-8')
                return base64_string

            #b_data=get_base64_encoded_image("test.jpeg")
            
            content = []
            if not chat_history:
                for ifn in image_path:
                    b_data = get_base64_encoded_image(ifn)
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b_data
                        }
                    })

            
            if 0:
                prompt=f"""You have perfect artistic sence and pay great attention to detail which makes you an expert at describing images.
                {text_prompt} Before providing the answer in <answer> 
                tags, think step by step in <thinking> tags and analyze every part of the image."""
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

class pHist_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}
        #pub.subscribe(self.load_random_images, 'load_random_images')
        if  not pHist_ResponseStreamer.subscribed:
                
            pub.subscribe(self.load_random_prompts, 'load_random_prompts')
            pHist_ResponseStreamer.subscribed=True    
    def load_random_prompts(self, tab_id):
        
        if tab_id in     self.chat_history:
            print(  'Clearing history load_random_prompts', tab_id)
            del self.chat_history[tab_id]  

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id,  prompt_path):
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

           
            content = []
            
        

            image_descriptions=[]
            for pfn in prompt_path:
                with open(pfn, 'r') as f:
                    image_descriptions.append(f.read()) 

            descriptions_text = "\n\n".join([f"Image {i+1}: {desc}" for i, desc in enumerate(image_descriptions)])
            


            prompt = f"""I want you to imagine and describe in detail a single image that fuses elements from multiple image descriptions. 
            Here are the descriptions of the input images:

            {descriptions_text}

            Please create a vivid, detailed description of a single imaginary image that combines elements from all of these descriptions. 
            Focus on how the elements from each description interact and blend together. 
            Be specific about colors, shapes, textures, and composition. 
            Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

            Before Providing the final description in <fused_image> tag, list weights of each emage use used in description and short info about it in <weights> tags. .
            do not start with "The resulting image is" in <fused_image>
            {text_prompt}"""


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
    
    
class Chat_ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history={}
   
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id,  image_path):
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

class One_pChat_ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history=[]
   
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id,  prompt_path):
        # Create a chat completion request with streaming enabled

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

           
            content = []
            
        

            image_descriptions=[]
            for pfn in prompt_path:
                with open(pfn, 'r') as f:
                    image_descriptions.append(f.read()) 

            descriptions_text = "\n\n".join([f"Image {i+1}: {desc}" for i, desc in enumerate(image_descriptions)])
            


            prompt = f"""I want you to imagine and describe in detail a single image that fuses elements 
            from image descriptions and user image modification request.
            Here are the descriptions of the input image:
            '{descriptions_text}'
            Here user request for input image modification:
            '{text_prompt}'

            Please create a vivid, detailed description of a single imaginary taking into account user request.
            
            Be specific about colors, shapes, textures, and composition. 
            Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

            Provide the final description in <modified_image> tag.
            """


            content.append({"type": "text", "text": prompt})
            message_list =  [
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
class pChat_ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.chat_history=[]
   
        


    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id,  prompt_path):
        # Create a chat completion request with streaming enabled

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

           
            content = []
            
        

            image_descriptions=[]
            for pfn in prompt_path:
                with open(pfn, 'r') as f:
                    image_descriptions.append(f.read()) 

            descriptions_text = "\n\n".join([f"Image {i+1}: {desc}" for i, desc in enumerate(image_descriptions)])
            


            prompt = f"""I want you to imagine and describe in detail a single image that fuses elements from multiple image descriptions. 
            Here are the descriptions of the input images:

            {descriptions_text}

            Please create a vivid, detailed description of a single imaginary image that combines elements from all of these descriptions. 
            Focus on how the elements from each description interact and blend together. 
            Be specific about colors, shapes, textures, and composition. 
            Your description should be cohesive, as if describing a real painting or photograph that fuses these elements.

            Before Providing the final description in <fused_image> tag, list weights of each emage use used in description and short info about it in <weights> tags. .
            {text_prompt}"""


            content.append({"type": "text", "text": prompt})
            message_list =  [
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
class StyledTextDisplay(stc.StyledTextCtrl, GetClassName, NewChat, Scroll_Handlet):
    def __init__(self, parent):
        super(StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        NewChat.__init__(self)
        Scroll_Handlet.__init__(self)
        self.SetWrapMode(stc.STC_WRAP_WORD)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.SetLexer(stc.STC_LEX_PYTHON)
        python_keywords = 'woman tryzub pinup pin-up nude Ukraine Ukrainian Tryzub flag blue yellow picture model image file artist artistic artistically color light scene question answer description mood texture emotion feeling sense impression atmosphere tone style technique brushstroke composition perspective'


        self.SetKeyWords(0, python_keywords)
        # Set Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")  # Default
        #self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#008000,back:#FFFFFF")  # Comment
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")  # Number
        #self.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")  # String
        #self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")  # Character
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        #self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  # Triple quotes
        #self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")  # Triple double quotes
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
            #print('Scrolling to the end')
            if self.scrolled:
            #self.answer_output.MakeCellVisible(i, 0)
        
                self.GotoPos(self.GetTextLength())
        else:
            if 1: #self.scrolled:
            # print('Not scrolling to the end')
                self.GotoPos(self.GetTextLength())


class PromptCtrl(StyledTextDisplay):
    subscribed=False
    def __init__(self, parent,chat):
        super().__init__(parent)
        self.chat=chat
        self.prompt_path=None
        if 'default_file' in chat:
            self.prompt_path = chat.default_file
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('V'), wx.ID_PASTE)
        ])
        #self.SetAcceleratorTable(accel_tbl)
        #self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        
        if not PromptCtrl.subscribed:
                
            pub.subscribe(self.OnOpenPromptFile, 'open_prompt_file')
            PromptCtrl.subscribed=True
    def OnOpenPromptFile(self, file_path):

        if self.IsTabVisible():
            print('Opening prompt file...')
            self.load_prompt_file(file_path)
        else:
            print('Not visible')
    def IsTabVisible(self):
        parent_notebook = self.GetParent()  # Assuming direct parent is the notebook
        current_page = parent_notebook.GetCurrentPage()
        return current_page == self            
    def OnPaste(self, event):
        print('Pasting...')
        clipboard = wx.Clipboard.Get()
        if clipboard.Open():
            #get text from clipboard
            if clipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                data_object = wx.TextDataObject()
                if clipboard.GetData(data_object):
                    text = data_object.GetText()
                                        
                    # Save the image to a temporary file or set it directly to the canvas
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    temp_prompt_path = join('image_log',f'temp_pasted_image_{timestamp}.png' )                  
                    
                    with open(temp_prompt_path, 'wb') as f:
                        f.write(data_object.GetData(text))
                    self.load_prompt_file(temp_prompt_path)

                else:
                    print("Clipboard data retrieve failed")
            

            else:
                print("Clipboard does not contain text data")
            clipboard.Close()
            log('Paste done.')
            set_status('Paste done.') 
        else:
            print("Unable to open clipboard")

    def load_prompt(self, prompt_path):
        text = None
        
        assert isfile(prompt_path), prompt_path
        with open(prompt_path, 'r') as f:
            text = f.read()
            
        return text
    
    def load_prompt_file(self, file_path):
        # This method will be used to load and display an image on the canvas
        self.prompt_path = file_path
        self.DisplayPrompt(file_path)
        #self.update_notebook_tab_label(file_path)

    def OnPromptClick(self, event):
        # Set focus to the notebook tab containing the static bitmap (canvasCtrl)
        self.SetFocus()


    def DisplayPrompt(self, prompt_path):
        # Load the image
     
        txt = self.load_prompt(prompt_path)
        if txt is None:
            print("Failed to load prompt.")
            return
        
        self.AppendText(txt)

class MyNotebookPromptPanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, tab_id):
        super(MyNotebookPromptPanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        self.tab_id=tab_id
        self.notebook = notebook
        self.promptCtrl=[]
        chat = apc.chats[tab_id]
        promptCtrl=PromptCtrl(notebook, chat)
        self.promptCtrl.append(promptCtrl)

        apc.prompts = self.promptCtrl
        
        #self.Bind(wx.EVT_SIZE, self.OnResize)
        
        
        chat.num_of_prompts=    chat.get('num_of_prompts',    1)
        if promptCtrl.prompt_path:
            
            print(promptCtrl.prompt_path)
            promptCtrl.DisplayPrompt(promptCtrl.prompt_path)
            notebook.AddPage(promptCtrl, promptCtrl.prompt_path)
        else:
            notebook.AddPage(promptCtrl, f'Prompt_1')
            
            
            for i in range(2,chat.num_of_prompts+1):
                promptCtrl = PromptCtrl(notebook, chat)
                self.promptCtrl.append(promptCtrl)                
                notebook.AddPage(promptCtrl, f'Prompt_{i}')
                
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Layout()
        
        # Bind paste event
        #self.Bind(wx.EVT_TEXT_PASTE, self.OnPaste)
        
        # Bind key down event to handle Ctrl+V

        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        pub.subscribe(self.load_random_prompts, 'load_random_prompts')
        self.prompt_pool=self.get_prompt_list()
        if 0 and not MyNotebookPromptPanel.subscribed:
                
            pub.subscribe(self.load_random_prompts, 'load_random_prompts')
            MyNotebookPromptPanel.subscribed=True  
        self.notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.onTabClose)
    def onTabClose(self, event):
        # Check if the panel being closed is MyNotebookImagePanel
        page_index = event.GetSelection()
        #print(page_index, self.notebook.GetPageCount(), isinstance(self, MyNotebookImagePanel))
        page = self.notebook.GetPage(page_index)
        if isinstance(self, MyNotebookPromptPanel):
            # Prevent the tab from closing
            #dialog asking if want to close
            dialog=wx.MessageDialog(self, 'Are you sure you want to close this tab?', 'Close Tab', wx.YES_NO | wx.ICON_QUESTION)
            response = dialog.ShowModal()
            if response == wx.ID_YES:
                # Close the tab
                event.Skip()    
            else:       

                event.Veto()              
    def get_prompt_list(self):
        from pathlib import Path

        prompt_path = Path(apc.home)/'prompts'
        #image_path= Path(__file__).parent / 'test'
        #print(apc.home)
        #print(prompt_path)
        #e()
        txt_files = list(prompt_path.glob('*.txt')) 

        return  txt_files
    def load_random_prompts(self, tab_id):
        print(tab_id == self.tab_id , tab_id, self.tab_id)
        if tab_id == self.tab_id:
            
            chat = apc.chats[self.tab_id]
            print('Loading random prompts...', chat.num_of_prompts)
            
            print(len(self.prompt_pool))
            random_subset = random.sample(self.prompt_pool, chat.num_of_prompts)
            pp(random_subset)
            if 1:
                for i, fn in enumerate(random_subset):
                    print(i, fn)
                    self.promptCtrl[i].load_prompt_file(str(fn))
        else:
            pass
            #print('Not for me', self.tab_id)
    def update_notebook_tab_label(self, file_path):
        # Update the notebook tab label to the new file name
        file_name = os.path.basename(file_path)
        notebook = self.notebook
        
        # Find the tab with the canvas and update its label
        for i in range(notebook.GetPageCount()):
            if notebook.GetPage(i) == self.promptCtrl:
                notebook.SetPageText(i, file_name)
                break
        







    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('V') or event.GetKeyCode() == wx.WXK_RETURN):
            self.log('Loading...')
            self.OnPaste(event)
            self.log('Done.')
        else:
            event.Skip()

    def log(self, message):
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}')

    def output(self, message):
        pub.sendMessage('output', message=f'{message}')

    def exception(self, message):
        pub.sendMessage('exception', message=f'{message}')



class _Copilot_DisplayPanel(StyledTextDisplay):
    subscribed=False
    def __init__(self, parent, tab_id):
        StyledTextDisplay.__init__(self,parent)
        
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
     
        self.tab_id=tab_id

        if 1: #not Copilot_DisplayPanel.subscribed:
                
            pub.subscribe(self.AddChatOutput, 'chat_output')
            #print('#' * 20, self.tab_id, 'subscribing to chat_output')
            Copilot_DisplayPanel.subscribed=True 
        else:
            pass
            #print('-' * 20, 'Already subscribed', self.tab_id)
            #print('Copilot_DisplayPanel passing on subscription', self.tab_id)       
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

          


class Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id, chat):
        super(Copilot_DisplayPanel, self).__init__(parent)
        apc.chats[tab_id]=chat
        # Create a splitter window
        self.copilot_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)
        self.tab_id=tab_id

        # Initialize the notebook_panel and logPanel
        self.notebook_panel=notebook_panel = MyNotebookPromptPanel(self.copilot_splitter, tab_id)
        notebook_panel.SetMinSize((-1, 50))
        #notebook_panel.SetMinSize((800, -1))
        self.chatPanel = _Copilot_DisplayPanel(self.copilot_splitter, tab_id)
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
    def _GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.promptCtrl
        for prompt in  self.notebook_panel.promptCtrl:
            out.append(prompt.prompt_path)
        
    def GetPromptPath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.notebook
       
        page_count = notebook.GetPageCount()

        for page_index in range(page_count):
            # Get the panel (page) at the current index
            page = notebook.GetPage(page_index)
            
            out.append(page.prompt_path)
        return out
    
    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip()        

class Chat_DisplayPanel(StyledTextDisplay):
    def __init__(self, parent, tab_id, chat):
        StyledTextDisplay.__init__(self,parent)
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
        self.tab_id=tab_id

        pub.subscribe(self.AddChatOutput, 'chat_output')
        #pub.subscribe(lambda message, tab_id: self.AddOutput(message, tab_id), 'chat_output')
        pub.subscribe(self.OnShowTabId, 'show_tab_id') 
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

class ChatDisplayNotebookPanel(wx.Panel):
    subscribed=False
    def __init__(self, parent, vendor_tab_id, ws_name):
        super(ChatDisplayNotebookPanel, self).__init__(parent)
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
        if not ChatDisplayNotebookPanel.subscribed:
            
            pub.subscribe(self.OnWorkspaceTabChanging, 'workspace_tab_changing')
            pub.subscribe(self.OnWorkspaceTabChanged, 'workspace_tab_changed')
            pub.subscribe(self.OnVendorspaceTabChanging, 'vendor_tab_changing')   
            pub.subscribe(self.OnVendorspaceTabChanged, 'vendor_tab_changed')
            ChatDisplayNotebookPanel.subscribed=True
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
            display_panel = f'{chat.chat_type}_{panels.chat}'
            #print('display_panel', display_panel)
            try:
                assert display_panel in globals(), display_panel
                print(f'\t\tAddTab: Adding {chat.workspace} "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                # Microsoft_Chat_DisplayPanel/ Microsoft_Copilot_DisplayPanel
                chatDisplay = cls (chat_notebook, tab_id=tab_id, chat=chat)
                #chatDisplay.SetFocus()
                if 1:
                    apc.chats[tab_id]=chat
                    pub.sendMessage('swap_input_panel',  tab_id=tab_id)
            except AssertionError:
                print(f"Display class '{display_panel}' does not exist.")
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
        #print(tab_id, tab_id in apc.chats)
        if tab_id in apc.chats:
            chat=apc.chats[tab_id]
            pub.sendMessage('swap_input_panel', tab_id=tab_id)
        # Continue processing the event
        event.Skip()          



    def get_latest_chat_tab_id(self):
        return self.GetPageCount() - 1
#old
class Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel_Anthropic_Claude):
    subscribed=False
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Copilot_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.image_id=1
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        self.chat_type=chat.chat_type
        chatHistory[self.tab_id]=[]
        #chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Copilot[default_copilot_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask Claude AI {tab_id}:')
        if 1:
            model_names = model_list  # Add more model names as needed
            self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
            self.model_dropdown.SetValue(DEFAULT_MODEL)
            
            self.model_dropdown.Bind(wx.EVT_COMBOBOX, self.OnModelChange)
            chat.model = self.model_dropdown.GetValue()

        if 0:       
            max_new_tokens_values = ["256", "512", "1024", "2048", "4096", "8192", "16384", "32768"]
            # Create a ComboBox for max_new_tokens
            self.max_tokens_dropdown = wx.ComboBox(self, choices=max_new_tokens_values, style=wx.CB_READONLY)
            self.max_tokens_dropdown.SetValue("2048")  # Default value
            chat.max_new_tokens = "2048"
            self.max_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxNewTokensChange)
        if 0:       
            temp_vals = ["0", "0.2", "0.4", "0.6", "0.8", "1", "2", "5"]
            # Create a ComboBox for max_new_tokens
            self.temp_dropdown = wx.ComboBox(self, choices=temp_vals, style=wx.CB_READONLY)
            self.temp_dropdown.SetValue("1")  # Default value
            chat.temperature =  "1"
            self.temp_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTempChange)

        self.askButton = wx.Button(self, label='Ask', size=(40, 25))
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)

        self.randomButton = wx.Button(self, label='Rand', size=(40, 25))
        self.randomButton.Bind(wx.EVT_BUTTON, self.onRandomButton)   
        if 0:
            self.historyButton = wx.Button(self, label='Hist', size=(40, 25))
            self.historyButton.Bind(wx.EVT_BUTTON, self.onHistoryButton)
            # New Random button
 

            self.sysButton = wx.Button(self, label='Sys', size=(40, 25))
            self.sysButton.Bind(wx.EVT_BUTTON, self.onSysButton)

        if 0:
            self.numOfTabsCtrl = wx.TextCtrl(self, value="1", size=(40, 25))
            self.tabsButton = wx.Button(self, label='Tabs', size=(40, 25))
            self.tabsButton.Bind(wx.EVT_BUTTON, self.onTabsButton)
        
        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_LEFT)
        askSizer.Add(self.model_dropdown, 0, wx.ALIGN_LEFT)
        #askSizer.Add(self.max_new_tokens_dropdown, 0, wx.ALIGN_CENTER)
        #askSizer.Add(self.temp_dropdown, 0, wx.ALIGN_CENTER)
        if 0:
            self.pause_panel=pause_panel=PausePanel(self, self.tab_id)
            askSizer.Add(pause_panel, 0, wx.ALL)
        #h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        Base_InputPanel_Anthropic_Claude.AddButtons_Level_1(self, askSizer)
        #askSizer.Add(h_sizer, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.randomButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)
        #askSizer.Add(self.historyButton, 0, wx.ALIGN_CENTER)
        #
        #askSizer.Add(self.sysButton, 0, wx.ALIGN_CENTER)
        #askSizer.Add(self.numOfTabsCtrl, 0, wx.ALIGN_CENTER)
        #askSizer.Add(self.tabsButton, 0, wx.ALIGN_CENTER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        Base_InputPanel_Anthropic_Claude.AddButtons_Level_2(self, h_sizer)

        sizer.Add(askSizer, 0, wx.ALIGN_LEFT)
        sizer.Add(h_sizer, 0, wx.ALIGN_LEFT)



        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)

        #self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        #sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0

        #pub.subscribe(self.SetException, 'fix_exception')
        #pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
        #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        #pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)

        self.rs={}

        if not Copilot_InputPanel.subscribed:
                
            #pub.subscribe(self.SetException, 'fix_exception')
            pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
            #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
            #pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
            Copilot_InputPanel.subscribed=True
    def get_rs(self, tab_id):
        chat=apc.chats[tab_id]
        streamer_name = f'{chat.streamer_name}_ResponseStreamer'
        if streamer_name not in self.rs:
            
            print(f'\t\Creating streamer:', streamer_name)
            cls= globals()[streamer_name]
            # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
            self.rs[streamer_name] = cls ()
        return self.rs [streamer_name]             
    def onTabsButton(self, event):
        try:
            num_of_tabs = int(self.numOfTabsCtrl.GetValue())
            pub.sendMessage('set_num_of_tabs', num=num_of_tabs, tab_id=self.tab_id)
        except ValueError:
            self.log("Invalid number of tabs.", color=wx.RED)

    def onRandomButton(self, event):
        # Implement the random function logic here
        self.log('Random button clicked 11')
        pub.sendMessage('load_random_prompts', tab_id=self.tab_id)
    def onHistoryButton(self, event):
        global chatHistory
        dialog = ChatHistoryDialog(self, self.tab_id, chatHistory)
        dialog.ShowModal()
        dialog.Destroy()
    def onSysButton(self, event):
        global chatHistory
        dialog = ShowSystemPrompts(self, self.tab_id, chatHistory)
        dialog.ShowModal()
        dialog.Destroy()        
    def OnMaxNewTokensChange(self, event):
        # This method will be called when the selection changes
        selected_value = self.max_new_tokens_dropdown.GetValue()
        print(f"Selected max_new_tokens: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.max_new_tokens = selected_value
    def OnTempChange(self, event):

        # This method will be called when the selection changes
        selected_value = self.temp_dropdown.GetValue()
        print(f"Selected temp: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.temperature = selected_value            
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask Claude{tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            #print('@'*30, 'Setting chat defaults', tab_id)
            assert self.chat_type==tab_id[1]
            chat=apc.chats[tab_id]
            if 0:

                self.tabs[self.tab_id]=dict(q=chat.question)
                #chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]
                questionHistory[self.tab_id]=[]
                currentModel[self.tab_id]=self.model_dropdown.GetValue() 
                chatHistory[self.tab_id]=[]    
            if 1:
                q= apc.chats[self.tab_id].question
                self.tabs[self.tab_id]=dict(q=q)
                questionHistory[self.tab_id]=[q]
                currentQuestion[self.tab_id]=0
                currentModel[self.tab_id]=self.model_dropdown.GetValue()
                chatHistory[self.tab_id]=[]  
                #chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]
            self.RestoreQuestionForTabId(tab_id)
            self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])


    def OnModelChange(self, event):
        # Get the selected model
        selected_model = self.model_dropdown.GetValue()

        chat=apc.chats[self.tab_id]
        chat.model = selected_model
        # Continue processing the event
        event.Skip()

    def _RestoreQuestionForTabId(self, message):
        global currentModel
        tab_id=message
        if tab_id in self.tabs:
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            #self.model_dropdown.SetValue(currentModel[message])
            self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
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
        try:
            #self.Base_OnAskQuestion()
            question = self.inputCtrl.GetValue()
            if not question:
                self.log('There is no question!', color=wx.RED)
            else:
                question = self.inputCtrl.GetValue()
                self.log(f'Asking question: {question}')
                pub.sendMessage('start_progress')
                #code=???
                chatDisplay=apc.chat_panels[self.tab_id]
                prompt_path=chatDisplay.GetPromptPath(self.tab_id)
                #pp(image_path)
                #return
                assert prompt_path,chatDisplay
                #print(888, chatDisplay.__class__.__name__)
                #code='print(1223)'
                chat=apc.chats[self.tab_id]
                

                #question=question.replace('\n', ' ')
                user_prompt= 'DESCRIBE_IMAGE'
                prompt=evaluate(all_system_templates[chat.workspace].Copilot[user_prompt], dict2( input=question))
                #pp(prompt)
                payload =[{"role": "user", "content": prompt}] 


                questionHistory[self.tab_id].append(question)
                currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
                currentModel[self.tab_id]=self.model_dropdown.GetValue()


                

                # DO NOT REMOVE THIS LINE
                chat.temperature = chat.get('temperature',"1")
                #header=fmt([[f'User Question|Hist:{chat.history}|{ self.max_new_tokens_dropdown.GetValue()}|{system}|{chat.temp_val}']],[])
                
                #print(header)
                #print(question)
                #pub.sendMessage('chat_output', message=f'{header}\nFiles: {len(image_path)}\n\n{question}\n', tab_id=self.tab_id)
                #pub.sendMessage('chat_output', message=f'{prompt}\n')
                #pp(image_path)
                #out=rs.stream_response(prompt, chatHistory[self.q_tab_id])  
                for i, fn in enumerate(prompt_path):
                    if not fn:
                        log(f'Image {i} is not set', color=wx.RED)
                        pub.sendMessage('stop_progress')
                        return
                    log(fn)
                import random  
                #pp(image_path)
                if 1:
                    random.shuffle(prompt_path)
                #pp(image_path)
                if 'system_prompt' not in chat:
                    system= chat.get('system', 'SYSTEM')
                    num_op=str(chat.num_of_prompts)
                    chat.system_prompt=evaluate(all_system_templates[chat.workspace].Copilot[system], dict2(num_of_prompts=num_op))
                    pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id)
                    #print(system_prompt)

                threading.Thread(target=self.stream_response, args=(prompt, payload, self.tab_id, prompt_path)).start()
        except Exception as e:
            print(format_stacktrace())
            self.log(f'Error: {format_stacktrace()}', color=wx.RED)
            pub.sendMessage('stop_progress')
    def stream_response(self, prompt, payload, tab_id,  prompt_path):
        # Call stream_response and store the result in out
        global chatHistory, questionHistory, currentQuestion,currentModel
        self.receiveing_tab_id=tab_id
        
        #print(1111, keep_history)
       
        payload=chatHistory[self.tab_id]
        vrs=self.get_rs(tab_id)
        out = vrs.stream_response(prompt, payload, self.receiveing_tab_id, prompt_path)
        if out:
            chatHistory[tab_id].append({"role": "assistant", "content": out}) 
            self.image_id +=1
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
        python_keywords = 'bool python str int self False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with both yield'

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
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  # Single triple quotes (''' ''')
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
 

class Chat_InputPanel(wx.Panel, NewChat,GetClassName, Base_InputPanel_Anthropic_Claude):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Chat_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        chatHistory[self.tab_id]=[]
        #pp(chat)
        chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask chatgpt {tab_id}:')
        model_names = [DEFAULT_MODEL, 'gpt-4-turbo', 'gpt-4']  # Add more model names as needed
        self.chat_type=chat.chat_type
        self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
        self.model_dropdown.SetValue(DEFAULT_MODEL)
        
        self.model_dropdown.Bind(wx.EVT_COMBOBOX, self.OnModelChange)

        

        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)



        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.model_dropdown, 0, wx.ALIGN_CENTER)
        self.pause_panel=pause_panel=PausePanel(self, self.tab_id)
        askSizer.Add(pause_panel, 0, wx.ALL)
   
        askSizer.Add((1,1), 1, wx.ALIGN_CENTER|wx.ALL)
        Base_InputPanel_Anthropic_Claude.AddButtons_Level_1(self, askSizer)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        Base_InputPanel_Anthropic_Claude.AddButtons_Level_2(self, h_sizer)

        sizer.Add(askSizer, 0, wx.ALIGN_LEFT)
        sizer.Add(h_sizer, 0, wx.ALIGN_LEFT)        

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)
        if 1:
            q=apc.chats[tab_id].question

            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=DEFAULT_MODEL

            chat=apc.chats[tab_id]
            chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
         


        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        #self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        #sizer = wx.BoxSizer(wx.VERTICAL)
        #sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0

        pub.subscribe(self.SetException, 'fix_exception')
        pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
        #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        #pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)
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
            currentModel[self.tab_id]=DEFAULT_MODEL
        self.RestoreQuestionForTabId(tab_id)

    def _SetTabId(self, tab_id):
        global chatHistory, questionHistory, currentModel
        self.tab_id=tab_id
      
        return self

                      
    def OnModelChange(self, event):
        # Get the selected model
        selected_model = self.model_dropdown.GetValue()

        # Print the selected model
        print(f"Selected model: {selected_model}")

        # You can add more code here to do something with the selected model

        # Continue processing the event
        event.Skip()

    def _RestoreQuestionForTabId(self, tab_id):
        message=tab_id
        
        global currentModel
        if message  in self.tabs:
            print(self.__class__.__name__, 'RestoreQuestionForTabId', message)
            assert self.chat_type==message[1]
            print('Chat restoring', message)
            pp(self.tabs[message])
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            self.model_dropdown.SetValue(currentModel[message])
            self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
        
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

            if 0:
                header=fmt([['\n'.join(self.split_text_into_chunks(question, 80))]], ['User Question'])
                # DO NOT REMOVE THIS LINE
                print(header)
                pub.sendMessage('chat_output', message=f'{header}\n', tab_id=self.tab_id)
            #pub.sendMessage('chat_output', message=f'{prompt}\n')
            if 'system_prompt' not in chat:
                system= chat.get('system', 'SYSTEM')
               
                chat.system_prompt=evaluate(all_system_templates[chat.workspace].Chat[system], dict2())
                pub.sendMessage('set_system_prompt', message=chat.system_prompt, tab_id=self.tab_id)        
            
            self.askButton.Disable()
            threading.Thread(target=self.stream_response, args=(prompt, chatHistory, self.tab_id, self.model_dropdown.GetValue())).start()

    def stream_response(self, prompt, chatHistory, tab_id, model):
        # Call stream_response and store the result in out
        self.receiveing_tab_id=tab_id
        chat=apc.chats[tab_id]
        streamer_name = f'{chat.streamer_name}_ResponseStreamer'

        assert streamer_name in globals(), streamer_name
        print(f'\t\Creating streamer:', streamer_name)
        cls= globals()[streamer_name]
        # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
        rs = cls ()
        out = rs.stream_response(prompt, chatHistory[tab_id], self.receiveing_tab_id, model)
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
          
