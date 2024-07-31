


import argparse
import time, random
from datetime import datetime
import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
import time, glob,threading, traceback
import os, sys  
from os.path import join, isfile
from include.Portrait.Base.Base_InputPanel_Portrait_SD import Base_InputPanel_Portrait_SD
import torch

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
#from include.Portrait.Copilot_Text import Copilot_DisplayPanel
#from include.Portrait.Copilot_Vision import Copilot_DisplayPanel 
from include.Portrait.Copilot_Vision import  MyNotebookImagePanel
DEFAULT_MODEL  = r'microsoft/Promptist'
model_list=[DEFAULT_MODEL]

dir_path = 'template'

chatHistory,  currentQuestion, currentModel = apc.chatHistory,  apc.currentQuestion, apc.currentModel
questionHistory= apc.questionHistory
all_templates, all_chats, all_system_templates = apc.all_templates, apc.all_chats, apc.all_system_templates
panels     = AttrDict(dict(workspace='WorkspacePanel', vendor='ChatDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))



class Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id):
        super(Copilot_DisplayPanel, self).__init__(parent)
        #apc.chats[tab_id]=chat
        # Create a splitter window
        self.copilot_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)
        self.tab_id=tab_id

        # Initialize the notebook_panel and logPanel
        self.notebook_panel=notebook_panel = MyNotebookImagePanel(self.copilot_splitter, tab_id)
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
    def _GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.canvasCtrl
        for canvas in  self.notebook_panel.canvasCtrl:
            out.append(canvas.image_path)
        
    def GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        
        out=[]
        notebook= self.notebook_panel.notebook
       
        page_count = notebook.GetPageCount()

        for page_index in range(page_count):
            # Get the panel (page) at the current index
            page = notebook.GetPage(page_index)
            
            out.append(page.image_path)
        return out
    
    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip()        



#import vertexai
#from vertexai.language_models import TextGenerationModel
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
class CustomTextStreamer(TextIteratorStreamer):
    def __init__(self, tokenizer,tab_id, skip_special_tokens=True):
        super().__init__(tokenizer, skip_special_tokens)
        self.generated_text = ""
        self.tab_id=tab_id
        print("CustomTextStreamer initialized")

    def on_finalized_text(self, text: str, stream_end: bool = False):
        #print("CustomTextStreamer on_finalized_text invoked")
        # Remove special tokens from the end of the text
        #text = text.replace("<end_of_turn>", "").replace("<eos>", "").strip()
        if 1:
            self.generated_text += text
            pub.sendMessage('chat_output', message=text, tab_id=self.tab_id)
            print(text, end='', flush=True)  # Print each chunk of text
class Chat_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if model_id not in self.model:
            
            
            self.model[model_id] =  AutoModelForCausalLM.from_pretrained(model_id,
                                                                cache_dir="cache").to(device)
            
        else:
            print("Model already loaded")
        return self.model[model_id] , device
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  tokenizer= AutoTokenizer.from_pretrained("gpt2", cache_dir="cache")
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.padding_side = "left"

        else:
            print("Tokenizer already loaded")
        return self.tokenizer[model_id]
    def generate_response(self, input_ids, chat, receiveing_tab_id,attention_mask, model , tokenizer):
        
        eos_id = tokenizer.eos_token_id
        # Stream generation
        
        assert type(chat.top_p) is tuple, type(chat.top_p)
        assert type(chat.top_p) is tuple, type(chat.top_p)
        for top_p in range(*[int(x*10) for x in chat.top_p]):
            top_p=top_p/10
            for top_k in range(*[int(x) for x in chat.top_k], 30):
                for temp in range(*[int(x*10) for x in chat.temperature], 3):
                    temp=temp/10
                    for length_penalty in range(*[int(x) for x in chat.length_penalty]):
                        #print (f'top_p = {top_p}, top_k = {top_k}, temp = {temp}')
                        for repetition_penalty in range(*[int(x*10) for x in chat.repetition_penalty], 3):
                            repetition_penalty=repetition_penalty/10
                            header = fmt([[f'top_p = {top_p}, top_k = {top_k}, len_pnlt = {length_penalty}, rept_pnlt = {repetition_penalty}, temp = {temp}']],[])
                            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
                            gen_start = time.time()
                            outputs = model.generate(input_ids, 
                                                            attention_mask=attention_mask,
                                                            do_sample=chat.do_sample,
                                                            temperature=temp, 
                                                            max_new_tokens=chat.max_length, 
                                                            min_new_tokens=chat.min_length, 
                                                            num_beams=8, 
                                                            top_k=top_k,
                                                            top_p=top_p,
                                                            num_return_sequences=1, 
                                                            eos_token_id=eos_id, 
                                                            pad_token_id=eos_id,
                                                            
                                                            length_penalty=float(length_penalty),
                                                            repetition_penalty=float(repetition_penalty),
                                                            return_dict_in_generate=True,
                                                            output_scores=True)

                            generated_tokens = outputs.sequences[:, input_ids.shape[-1]:]


                            text = tokenizer.decode(generated_tokens[0], skip_special_tokens=True).strip()
                            

                            pub.sendMessage('chat_output', message=text, tab_id=receiveing_tab_id)
                            pub.sendMessage('chat_output', message='\n', tab_id=receiveing_tab_id)
                            print(f"{top_p}: Generate:", time.time() - gen_start)

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id, model):
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
        start = time.time()
        try:

            start = time.time()
            
            tokenizer=self.get_tokenizer(chat.model)
            model, device = self.get_model(chat.model)
            inputs = tokenizer(text_prompt.strip() + " Rephrase:", return_tensors="pt", padding=True)
            input_ids = inputs.input_ids.to(device)
            attention_mask = inputs.attention_mask.to(device)
            #eos_id = tokenizer.eos_token_id
            gen_start = time.time()
            self.generate_response( input_ids, chat, receiveing_tab_id,attention_mask, model , tokenizer)

            
            print("\nTotal:", time.time() - start)
            print("\Generate:", time.time() - gen_start)
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


class Fuser_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if model_id not in self.model:
            
            
            self.model[model_id] =  AutoModelForCausalLM.from_pretrained(model_id,
                                                                cache_dir="cache").to(device)
            
        else:
            print("Model already loaded")
        return self.model[model_id] , device
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  tokenizer= AutoTokenizer.from_pretrained("gpt2", cache_dir="cache")
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.padding_side = "left"

        else:
            print("Tokenizer already loaded")
        return self.tokenizer[model_id]
    def get_prompts(self)  :
        # get prompt text from all prompt panels
        prompts = []
        for promptCtrl in apc.prompts:
            prompts.append(promptCtrl.GetText())
        return prompts
    def generate_response(self, input_ids, chat, receiveing_tab_id,attention_mask, model , tokenizer):
        
        eos_id = tokenizer.eos_token_id
        # Stream generation
        
        assert type(chat.top_p) is tuple, type(chat.top_p)
        assert type(chat.top_k) is tuple, type(chat.top_k)
        assert type(chat.temperature) is tuple, type(chat.temperature)
        assert type(chat.temperature) is tuple, type(chat.temperature)
        assert type(chat.repetition_penalty) is tuple, type(chat.repetition_penalty)
        for top_p in range(*[int(x*10) for x in chat.top_p]):
            top_p=top_p/10
            for top_k in range(*[int(x) for x in chat.top_k], 30):
                for temp in range(*[int(x*10) for x in chat.temperature], 3):
                    temp=temp/10
                    for length_penalty in range(*[int(x) for x in chat.temperature]):
                        #print (f'top_p = {top_p}, top_k = {top_k}, temp = {temp}')
                        for repetition_penalty in range(*[int(x*10) for x in chat.repetition_penalty], 3):
                            repetition_penalty=repetition_penalty/10
                            header = fmt([[f'top_p = {top_p}, top_k = {top_k}, len_pnlt = {length_penalty}, rept_pnlt = {repetition_penalty}, temp = {temp}']],[])
                            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
                            gen_start = time.time()
                            outputs = model.generate(input_ids, 
                                                            attention_mask=attention_mask,
                                                            do_sample=chat.do_sample,
                                                            temperature=temp, 
                                                            max_new_tokens=chat.max_length, 
                                                            min_new_tokens=chat.min_length, 
                                                            num_beams=8, 
                                                            top_k=top_k,
                                                            top_p=top_p,
                                                            num_return_sequences=1, 
                                                            eos_token_id=eos_id, 
                                                            pad_token_id=eos_id,
                                                            
                                                            length_penalty=float(length_penalty),
                                                            repetition_penalty=float(repetition_penalty),
                                                            return_dict_in_generate=True,
                                                            output_scores=True)

                            generated_tokens = outputs.sequences[:, input_ids.shape[-1]:]


                            text = tokenizer.decode(generated_tokens[0], skip_special_tokens=True).strip()
                            

                            pub.sendMessage('chat_output', message=text, tab_id=receiveing_tab_id)
                            pub.sendMessage('chat_output', message='\n', tab_id=receiveing_tab_id)
                            print(f"{top_p}: Generate:", time.time() - gen_start)    
    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id, prompt_path):
        # Create a chat completion request with streaming enabled
        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[]
        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]
        #txt='\n'.join(split_text_into_chunks(text_prompt,80))
        # header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        #pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        start = time.time()
        try:

            start = time.time()
            
   

            

            prompts=self.get_prompts()
            descriptions_text=prompts[0]
            txt='\n'.join(split_text_into_chunks(descriptions_text,80))
            header = fmt([[f'{txt}\nAnswer:\n']],['Prompt | '+chat.model])
            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)            

            tokenizer=self.get_tokenizer(chat.model)
            model, device = self.get_model(chat.model)
            inputs = tokenizer(descriptions_text.strip() + " Rephrase:", return_tensors="pt", padding=True)
            input_ids = inputs.input_ids.to(device)
            attention_mask = inputs.attention_mask.to(device)
            eos_id = tokenizer.eos_token_id
            
            # Stream generation
            gen_start = time.time()
            self.generate_response( input_ids, chat, receiveing_tab_id,attention_mask, model , tokenizer)

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

 

class Deepinfra_Prompt_Fuser_ResponseStreamer:
    subscribed=False
    def __init__(self):
        # Set your OpenAI API key here
        self.model={}
        self.tokenizer={}
        self.chat_history={}

    def get_model(self, model_id):
        
        if model_id not in self.model:
            
            
            self.model[model_id] = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype="auto",
                device_map="auto",
                cache_dir="./cache",
                attn_implementation="flash_attention_2",
            )
        else:
            print("Model already loaded")
        return self.model[model_id]
        
    def get_tokenizer(self, model_id):
        if model_id not in self.tokenizer:

            self.tokenizer[model_id] =  AutoTokenizer.from_pretrained(model_id)
        
        else:
            print("Tokenizer already loaded")
        return self.tokenizer[model_id]

    def stream_response(self, text_prompt, chatHistory, receiveing_tab_id, prompt_path):
        # Create a chat completion request with streaming enabled
        chat=apc.chats[receiveing_tab_id]

        if receiveing_tab_id not in self.chat_history:
            self.chat_history[receiveing_tab_id]=[{"role": "system", "content": chat.system_prompt},]

        chat_history=self.chat_history[receiveing_tab_id]    
        out=[]
        from os.path import isfile
        gen_start=time.time()
        txt='\n'.join(split_text_into_chunks(text_prompt,80))
        header = fmt([[f'{txt}Answer:\n']],['Question | '+chat.model])
        pub.sendMessage('chat_output', message=f'{header}\n', tab_id=receiveing_tab_id)
        start = time.time()
        try:
            import os
            from openai import OpenAI

            # Create an OpenAI client with your deepinfra token and endpoint
            openai = OpenAI(
                api_key=os.getenv("DEEPINFRA_API_KEY"),
                base_url="https://api.deepinfra.com/v1/openai",
            )

            


            #prompt = "Give me a short introduction to large language model."

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

            Before Providing the final description in <fused_prompt> tag, list weights of each emage use used in description and short info about it in <weights> tags. .
            Do not mention weights in fused_prompt.
            {text_prompt}"""


            if chat.history:
                if len(chat_history)==1:
                    messages = [
                        {"role": "user", "content": prompt}
                    ]
                else:
                    messages = [
                        {"role": "user", "content": text_prompt}
                    ]
            else:
                messages = [
                    {"role": "user", "content": prompt}
                ]                            
            chat_history += messages
            #pp(chat_history)
            #return ''
            #pp(chat)
            # e()
            chat_completion = openai.chat.completions.create(
                model=chat.model,
                messages=messages,
                stream =True,
                temperature=chat.temperature,
                max_tokens=chat.max_length,
                top_p=chat.top_p,
                n=1,
                stop=None,
                #length_penalty=chat.length_penalty, 
                presence_penalty=chat.presence_penalty, #Positive values penalize new tokens based on whether they appear in the text so far,
                # increasing the model's likelihood to talk about new topics.
                #-2 ≤ presence_penalty ≤ 2
                frequency_penalty=chat.frequency_penalty, #Positive values penalize new tokens based on how many times they appear in the text so far, 
                # increasing the model's likelihood to talk about new topics.
                #-2 ≤ frequency_penalty ≤ 2
                #repetition_penalty=1.0, #(> 1 penalize, < 1 encourage)

            )
          
            for chunk in chat_completion:

                if chunk.choices[0].finish_reason:
                    log(chunk.choices[0].finish_reason, 'red' ) #+ chunk.usage["prompt_tokens"] + chunk.usage["completion_tokens"], 'red')
                    print(chunk.choices[0].finish_reason) #, chunk.usage["prompt_tokens"], chunk.usage["completion_tokens"])
                else:
                
                    text=chunk.choices[0].delta.content
                    if text is not None:
                        out.append(text)
                        pub.sendMessage('chat_output', message=f'{text}', tab_id=receiveing_tab_id)
                        print(text, end="")

            # After generation, print the total time and the full generated text
            print("\Generate:", time.time() - gen_start)
            print("\nTotal:", time.time() - start)
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)
            log(f'\nElapsed {time.time() - gen_start}, Total: {time.time() - start}')

            if chat.history:
                assistant = [{"role": "assistant", "content": ''.join(out)}]
                #pp(assistant)
                chat_history += assistant
            else:
                del self.chat_history[receiveing_tab_id]
        
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


class Chat_DisplayPanel(StyledTextDisplay):
    def __init__(self, parent, tab_id):
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
                print(111, display_panel, display_panel in globals())
                assert display_panel in globals(), display_panel
                print(f'\t\tAddTab: Adding {chat.workspace} "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                # Microsoft_Chat_DisplayPanel/ Microsoft_Copilot_DisplayPanel
                chatDisplay = cls (chat_notebook, tab_id=tab_id)
                #chatDisplay.SetFocus()
                if 1:
                    apc.chats[tab_id]=chat
                    pub.sendMessage('swap_input_panel',  tab_id=tab_id)
            except Exception as ex:
                print('#'*80)
                print(f"{str(ex)}")
                print('#'*80)
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
class Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel_Portrait_SD):
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
        chatHistory[self.tab_id]= [] #[{"role": "system", "content": all_system_templates[chat.workspace].Copilot[default_copilot_template]}]
        self.askLabel = wx.StaticText(self, label=f'{tab_id}:')
        if 1:
            model_names = model_list  # Add more model names as needed
            self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
            self.model_dropdown.SetValue(chat.model)
            
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
        Base_InputPanel_Portrait_SD.AddButtons_Level_1(self, askSizer)
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
        Base_InputPanel_Portrait_SD.AddButtons_Level_2(self, h_sizer)

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

                threading.Thread(target=self.stream_response, args=(prompt, chatHistory, self.tab_id, prompt_path)).start()
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
        out = vrs.stream_response(prompt, chatHistory, self.receiveing_tab_id, prompt_path)
        if out:
            #chatHistory[tab_id].append({"role": "assistant", "content": out}) 
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
 

class Chat_InputPanel(wx.Panel, NewChat,GetClassName, Base_InputPanel_Portrait_SD):
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
        #chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
        self.askLabel = wx.StaticText(self, label=f'{tab_id}:')
        model_names = model_list  # Add more model names as needed
        self.chat_type=chat.chat_type
        self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
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
        Base_InputPanel_Portrait_SD.AddButtons_Level_1(self, askSizer)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        Base_InputPanel_Portrait_SD.AddButtons_Level_2(self, h_sizer)

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
            #chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
         


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
        self.rs={}
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'{tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            assert self.chat_type==tab_id[1]
            
            #pp(apc.chats[tab_id])
            #e()
            self.tabs[self.tab_id]=dict(q=apc.chats[tab_id].question)
            chat=apc.chats[tab_id]
            chatHistory[self.tab_id]= [] #[{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
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
        chat=apc.chats[self.tab_id]
        chat.model=selected_model
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
            #chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

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
    def get_rs(self, tab_id):
        chat=apc.chats[tab_id]
        streamer_name = f'{chat.streamer_name}_ResponseStreamer'
        if streamer_name not in self.rs:
            
            print(f'\t\Creating streamer:', streamer_name)
            cls= globals()[streamer_name]
            # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
            self.rs[streamer_name] = cls ()
        return self.rs [streamer_name] 
    def stream_response(self, prompt, chatHistory, tab_id, model):
        # Call stream_response and store the result in out
        self.receiveing_tab_id=tab_id
        chat=apc.chats[tab_id]
        rs=self.get_rs(tab_id)
        out = rs.stream_response(prompt, chatHistory, self.receiveing_tab_id, model)
        if out:
            #chatHistory[tab_id].append({"role": "assistant", "content": out}) 
            pass
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
          
