import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp 
from include.fmt import fmt
import time, glob,threading, traceback
from os.path import join
from datetime import datetime
import os, subprocess, yaml, sys
import wx.stc as stc


import include.config.init_config as init_config 

init_config.init(**{})
apc = init_config.apc
apc.pause_output = {}
apc.stop_output = {}
DEFAULT_MODEL  = "microsoft/Phi-3-vision-128k-instruct"


apc.chatHistory = chatHistory={}

apc.questionHistory = questionHistory={}
apc.currentQuestion = currentQuestion={}
apc.currentModel   = currentModel={}



e=sys.exit
from dotenv import load_dotenv
load_dotenv()

from include.Common import *

apc.all_templates=all_templates=dict2()
apc.all_chats=all_chats=dict2()
apc.all_system_templates= all_system_templates=dict2()

from include.Gpt4_Python import Gpt4_Chat_InputPanel, Gpt4_Chat_DisplayPanel, Gpt4_Copilot_DisplayPanel, Gpt4_Copilot_InputPanel




#templates = d2d2(dict(Chat={}, Copilot={}))
default_chat_template='SYSTEM'
default_copilot_template='SYSTEM_CHATTY'

dir_path = 'template'

# list all files in the directory
# list all .yaml files in the directory
yaml_files = glob.glob(f'{dir_path}\\*\\*.yaml')

#pp(yaml_files)



class CustomDict(dict):
    def __setitem__(self, key, value):
        super(CustomDict, self).__setitem__(key, value)
        #print(f"Set {key} to {value}")

class MyLoader(yaml.SafeLoader):
    pass

def construct_mapping(loader, node):
    loader.flatten_mapping(node)  # Optional: Handle merged mappings properly
    return dict2(loader.construct_pairs(node))

# Add the constructor to the custom loader
MyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping
)



# Load the YAML using the custom loader
for yfn in yaml_files:
    #print(f'Loading template {yfn}...')
    bn=os.path.basename(yfn)
    if '__' in yfn:
        continue
    with open(yfn, 'r') as file:
        print(f'Processing template {yfn}...')
        data = yaml.load(file, Loader=MyLoader)

        all_templates[data.templates.workspace.name]=data
        all_chats[data.templates.workspace.name]=[]
        for tab in data.templates.tabs:
            all_chats[data.templates.workspace.name] +=data.templates.tabs[tab]
        for ch in all_chats[data.templates.workspace.name]:
            ch.workspace=data.templates.workspace.name
        all_system_templates[data.templates.workspace.name]=data.templates.System
        #break

#pp(all_templates.keys())
#e()
#all_templates=all_templates.Oracle
apc.default_workspace = list(all_templates.values())[0].templates.workspace



#dws=apc.default_workspace.name










from enum import Enum


#fn='_wx_test.py'
#fn=__file__ 
#fn='docs\\demo.plsql'


#vendor_api    =  all_templates.templates.vendor_api
#workspaces    = all_templates.templates.workspace 

panels     = AttrDict(dict(workspace='WorkspacePanel', vendor='ChatDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))

def get_current_conda_env():
    try:
        result = subprocess.run(
            ["conda", "info", "--envs"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True, shell=True
        )
        envs_output = result.stdout
        for line in envs_output.splitlines():
            if '*' in line:
                return line.split()[0]
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return None
    
def log(message, color=None):
    pub.sendMessage('log', message=message, color=color)
def set_status(message):
    pub.sendMessage('set_status', message=message)
def format_stacktrace():
    parts = ["Traceback (most recent call last):\n"]
    parts.extend(traceback.format_stack(limit=25))
    parts.extend(traceback.format_exception(*sys.exc_info())[1:])
    return "".join(parts)

class VisionResponseStreamer:
    def __init__(self, model_id):
        # Set your OpenAI API key here
        from transformers import AutoModelForCausalLM 
        from transformers import AutoProcessor 

        # Initialize the client
        self.model = AutoModelForCausalLM.from_pretrained(model_id, device_map="cuda", trust_remote_code=True, torch_dtype="auto", _attn_implementation='flash_attention_2') # use _attn_implementation='eager' to disable flash attention

        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True) 

    def stream_response(self, prompt, chatHistory, receiveing_tab_id, max_new_tokens, image_path):
        # Create a chat completion request with streaming enabled
        #pp(chatHistory)
        from PIL import Image 
        import requests 

        from os.path import isfile
        chat=apc.chats[receiveing_tab_id]

        #model_id = chat.model_id
    
        model, processor = self.model, self.processor

        messages = [{"role": "user", "content": prompt}]
        fn = image_path
        

        #prompt = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        #chat history
        prompt = processor.tokenizer.apply_chat_template(chatHistory, tokenize=False, add_generation_prompt=True)
        
        out = []
        try:
            
            assert isfile(fn)
            image = Image.open(fn)
            inputs = processor(prompt, [image], return_tensors="pt").to("cuda:0") 

            generation_args = { 
                "max_new_tokens": max_new_tokens , 
                "temperature": 1, 
                "do_sample": False, 
            } 

            generate_ids = model.generate(**inputs, eos_token_id=processor.tokenizer.eos_token_id, **generation_args) 

            # remove input tokens 
            generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
            response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0] 
            stop_output=apc.stop_output[receiveing_tab_id]
            pause_output=apc.pause_output[receiveing_tab_id]

            
            
            out.append(response)
            from os.path import basename
            bn=basename(image_path)            
            header=fmt([[f'System Answer']],[])
            print(f'\nFile: {bn}\n')
            print(header)
            print(response)
            #print(content, receiveing_tab_id)
            pub.sendMessage('chat_output', message=f'{header}\nFile: {bn}\n\n{response}', tab_id=receiveing_tab_id)
            
        except Exception as e:
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            return ''
        if 0:

            self.client = openai.OpenAI()
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=chatHistory,
                    stream=True,
		    max_tokens=4096 
                )
            except Exception as e:
                log(f'Error in stream_response', 'red')
                log(str(e), 'red')
                return ''
            
            # Print each response chunk as it arrives
            #pp(apc.stop_output)
            stop_output=apc.stop_output[receiveing_tab_id]
            pause_output=apc.pause_output[receiveing_tab_id]
            for chunk in response:
                if stop_output[0] or pause_output[0] :
                    
                    if stop_output[0] :
                        #print('\n-->Stopped\n')
                        pub.sendMessage("stopped")
                        break
                        #pub.sendMessage("append_text", text='\n-->Stopped\n')
                    else:
                        while pause_output[0] :
                            time.sleep(0.1)
                            if stop_output[0]:
                                #print('\n-->Stopped\n')
                                pub.sendMessage("stopped")
                                break
                                #pub.sendMessage("append_text", text='\n-->Stopped\n')
                                                
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    #print(content, end='', flush=True)
                    #pp(content)
                    if content:
                        out.append(content)
                        #print(content, receiveing_tab_id)
                        pub.sendMessage('chat_output', message=f'{content}', tab_id=receiveing_tab_id)

        if out:
            pub.sendMessage('chat_output', message=f'\n', tab_id=receiveing_tab_id)

        return ''.join(out)

class NewChatDialog(wx.Dialog):
    def __init__(self,ws_name, *args, **kwargs):
        super(NewChatDialog, self).__init__(*args, **kwargs)
        self.ws_name=ws_name
        self.vendor = wx.RadioBox(self, label="Vendor:", choices=list(vendor_api.keys()), majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.chat_type = wx.RadioBox(self, label="Gpt:", choices=list(vendor_api.Gpt4.values()), majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.chat_type.Bind(wx.EVT_RADIOBOX, self.OnRadioBox)
        #self.chat_type.SetStringSelection(default_chat_template)
        self.name = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.name.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        self.system = wx.TextCtrl(self,style=wx.TE_MULTILINE, size=(400, 75))
        self.system.SetValue(all_system_templates[ws_name].Chat [default_chat_template] )
        self.system.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.vendor, flag=wx.EXPAND|wx.ALL, border=5)         
        
        h_sizer.Add(self.chat_type, flag=wx.EXPAND|wx.ALL, border=5) 
        sizer.Add(h_sizer, flag=wx.EXPAND|wx.ALL, border=5)
        sizer.Add(wx.StaticText(self, label="Name:"), flag=wx.EXPAND|wx.ALL, border=5)
        sizer.Add(self.name, flag=wx.EXPAND|wx.ALL, border=5)
        sizer.Add(wx.StaticText(self, label="System:"), flag=wx.EXPAND|wx.ALL, border=5)
        sizer.Add(self.system, flag=wx.EXPAND|wx.ALL, border=5)

        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.AddButton(wx.Button(self, wx.ID_OK))
        button_sizer.AddButton(wx.Button(self, wx.ID_CANCEL))
        button_sizer.Realize()

        sizer.Add(button_sizer, flag=wx.EXPAND|wx.ALL, border=5)

        self.SetSizerAndFit(sizer)
        self.Center()
    def OnRadioBox(self, event):
        # This method will be called when the selection changes
        selected_string = self.chat_type.GetStringSelection()
        #print(f"The selected GPT type is {selected_string}")
        self.system.SetValue(all_system_templates[self.ws_name][selected_string]['SYSTEM'])

    def on_key_down(self, event):
        if event.ControlDown() and event.GetKeyCode() == wx.WXK_RETURN:
            self.EndModal(wx.ID_OK)
        else:
            event.Skip()

    def on_enter(self, event):
        self.EndModal(wx.ID_OK)

class StyledTextDisplay(stc.StyledTextCtrl, GetClassName, NewChat, Scroll_Handlet):
    def __init__(self, parent):
        super(StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        NewChat.__init__(self)
        Scroll_Handlet.__init__(self)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.SetWrapMode(stc.STC_WRAP_WORD)

        self.SetLexer(stc.STC_LEX_PYTHON)
        text_keywords = 'picture model image file artist artistic artistically color light scene question answer description mood texture emotion feeling sense impression atmosphere tone style technique brushstroke composition perspective'
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

        
class Microsoft_Chat_DisplayPanel(StyledTextDisplay):
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

             



class MyNotebookImagePanel(wx.Panel):
    def __init__(self, parent, tab_id):
        super(MyNotebookImagePanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        
        self.notebook = notebook
        
        self.canvasCtrl = wx.Panel(notebook)

        apc.canvas = self.canvasCtrl
        self.static_bitmap = None
        #self.Bind(wx.EVT_SIZE, self.OnResize)
        self.image_path = None
        chat = apc.chats[tab_id]

        if 'default_file' in chat:
            self.image_path = chat.default_file
            print(self.image_path)
            self.DisplayImageOnCanvas(self.image_path)
            notebook.AddPage(self.canvasCtrl, self.image_path)
        else:
            notebook.AddPage(self.canvasCtrl, 'Canvas')
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Layout()
        pub.subscribe(self.load_image_file, 'open_image_file')
        # Bind paste event
        #self.Bind(wx.EVT_TEXT_PASTE, self.OnPaste)
        
        # Bind key down event to handle Ctrl+V
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('V'), wx.ID_PASTE)
        ])
        #self.SetAcceleratorTable(accel_tbl)
        #self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.canvasCtrl.SetAcceleratorTable(accel_tbl)
        self.canvasCtrl.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
           
    def OnPaste(self, event):
        print('Pasting...')
        clipboard = wx.Clipboard.Get()
        if clipboard.Open():
            if clipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                data_object = wx.BitmapDataObject()
                if clipboard.GetData(data_object):
                    bitmap = data_object.GetBitmap()
                    image = wx.Image(bitmap.ConvertToImage())
                    
                    # Save the image to a temporary file or set it directly to the canvas
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    temp_image_path = join('image_log',f'temp_pasted_image_{timestamp}.png' )                  
                    
                    image.SaveFile(temp_image_path, wx.BITMAP_TYPE_PNG)
                    self.load_image_file(temp_image_path)
                else:
                    print("Clipboard data retrieve failed")
            else:
                print("Clipboard does not contain image data")
            clipboard.Close()
            log('Paste done.')
            set_status('Paste done.') 
        else:
            print("Unable to open clipboard")        
    def load_image_file(self, file_path):
        # This method will be used to load and display an image on the canvas
        self.image_path = file_path
        self.DisplayImageOnCanvas(file_path)
        self.update_notebook_tab_label(file_path)
    def update_notebook_tab_label(self, file_path):
        # Update the notebook tab label to the new file name
        file_name = os.path.basename(file_path)
        notebook = self.notebook
        
        # Find the tab with the canvas and update its label
        for i in range(notebook.GetPageCount()):
            if notebook.GetPage(i) == self.canvasCtrl:
                notebook.SetPageText(i, file_name)
                break
        
    def DisplayImageOnCanvas(self, image_path):
        # Load the image
        if hasattr(self, 'static_bitmap') and self.static_bitmap:
            self.static_bitmap.Destroy()      
        image = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
        
        # Get the top-level window size
        top_level_window = self.GetTopLevelParent()
        canvas_width, canvas_height = top_level_window.GetSize()
        canvas_width=canvas_width/2
        canvas_height -=200
        # Get the image size
        image_width = image.GetWidth()
        image_height = image.GetHeight()
        
        # Calculate the new size maintaining aspect ratio
        if image_width > image_height:
            new_width = canvas_width
            new_height = canvas_width * image_height / image_width
        else:
            new_height = canvas_height
            new_width = canvas_height * image_width / image_height
        
        # Resize the image
        image = image.Scale(int(new_width), int(new_height), wx.IMAGE_QUALITY_HIGH)
        
        # Convert it to a bitmap
        bitmap = wx.Bitmap(image)
        
        # Create a StaticBitmap widget to display the image
        self.static_bitmap = wx.StaticBitmap(self.canvasCtrl, -1, bitmap)
        self.static_bitmap.Bind(wx.EVT_LEFT_DOWN, self.OnBitmapClick)
        # Optionally, resize the panel to fit the image
        self.canvasCtrl.SetSize(bitmap.GetWidth(), bitmap.GetHeight()) 
    def OnBitmapClick(self, event):
        # Set focus to the notebook tab containing the static bitmap (canvasCtrl)
        for i in range(self.notebook.GetPageCount()):
            if self.notebook.GetPage(i) == self.canvasCtrl:
                self.notebook.SetSelection(i)
                self.canvasCtrl.SetFocus()
                break
    def OnResize(self, event):
        if self.image_path:
            self.DisplayImageOnCanvas(self.image_path)
        event.Skip()


    def ScaleImage(self, image, max_width, max_height):
        image_width = image.GetWidth()
        image_height = image.GetHeight()

        # Calculate the new size maintaining the aspect ratio
        if image_width > image_height:
            new_width = max_width
            new_height = max_width * image_height / image_width
            if new_height > max_height:
                new_height = max_height
                new_width = max_height * image_width / image_height
        else:
            new_height = max_height
            new_width = max_height * image_width / image_height
            if new_width > max_width:
                new_width = max_width
                new_height = max_width * image_height / image_width

        # Resize the image
        return image.Scale(int(new_width), int(new_height), wx.IMAGE_QUALITY_HIGH)
            




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



class Copilot_DisplayPanel(StyledTextDisplay):
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

          


class Microsoft_Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id, chat):
        super(Microsoft_Copilot_DisplayPanel, self).__init__(parent)
        apc.chats[tab_id]=chat
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
    def GetImagePath(self, tab_id):
        assert tab_id==self.tab_id, self.__class__.__name__
        return self.notebook_panel.image_path
    def OnResize(self, event):
        # Adjust the sash position to keep the vertical splitter size constant
        width, height = self.GetSize()
        self.copilot_splitter.SetSashPosition(width // 2)
        event.Skip()        

                                         

class Microsoft_ChatDisplayNotebookPanel(wx.Panel):
    def __init__(self, parent, vendor_tab_id, ws_name):
        super(Microsoft_ChatDisplayNotebookPanel, self).__init__(parent)
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
        pub.subscribe(self.OnWorkspaceTabChanging, 'workspace_tab_changing')
        pub.subscribe(self.OnWorkspaceTabChanged, 'workspace_tab_changed')
        pub.subscribe(self.OnVendorspaceTabChanging, 'vendor_tab_changing')   
        pub.subscribe(self.OnVendorspaceTabChanged, 'vendor_tab_changed')
    def get_active_chat_panel(self):
        active_chat_tab_index = self.chat_notebook.GetSelection()
        if active_chat_tab_index == wx.NOT_FOUND:
            return None
        return self.chat_notebook.GetPage(active_chat_tab_index)
            
    def OnWorkspaceTabChanging(self, message):
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
                pub.sendMessage('restore_question_for_tab_id', message=active_tab_id)

                assert active_tab_id in apc.chats
                chat=apc.chats[active_tab_id]
                print('swapping', active_tab_id )
                pub.sendMessage('swap_input_panel', chat=chat,tab_id=active_tab_id)
                            

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
        title=f'{chat.name}'
        chatDisplay=None
        tab_id=(chat.workspace, chat.chat_type, chat.vendor,self.vendor_tab_id, chat_notebook.GetPageCount())
        self.tabs[chat_notebook.GetPageCount()]=tab_id
        if 1:
            #pp(panels.__dict__)
            #pp(chat.__dict__)
            display_panel = f'{chat.vendor}_{chat.chat_type}_{panels.chat}'
            #print('display_panel', display_panel)
            try:
                assert display_panel in globals(), display_panel
                print(f'\t\tAdding {chat.workspace} "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
                try:
                    chatDisplay = cls (chat_notebook, tab_id=tab_id, chat=chat)
                    #chatDisplay.SetFocus()
                except:
                    print(format_stacktrace())
                    print(f'Error in {display_panel} class')
                    e(1)
                if 1:
                    pub.sendMessage('swap_input_panel', chat=chat, tab_id=tab_id)
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
        pub.sendMessage('restore_question_for_tab_id', message=tab_id)
        current_chatDisplay = nb.GetPage(newtabIndex)
        #pp(current_chatDisplay.tab_id)
        #e()
        if tab_id in apc.chats:
            chat=apc.chats[tab_id]
            pub.sendMessage('swap_input_panel', chat=chat,tab_id=tab_id)
        # Continue processing the event
        event.Skip()          



    def get_latest_chat_tab_id(self):
        return self.GetPageCount() - 1



class LogPanel(wx.Panel):
    def __init__(self, parent):
        super(LogPanel, self).__init__(parent)
        self.logCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        self.default_font = self.logCtrl.GetFont()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.logCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        pub.subscribe(self.AddLog, 'log')
        pub.subscribe(self.AddOutput, 'output')
        pub.subscribe(self.AddException, 'exception')

    def AddLog(self, message, color=None):
        if not color:
            color=wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        if 0:
            italic_font = wx.Font(10, wx.DEFAULT, wx.ITALIC, wx.NORMAL)
            normal_font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)            
            for line in message:
                if 'specific condition':  # Replace with your specific condition
                    self.logCtrl.BeginFont(italic_font)
                    self.logCtrl.WriteText(line + '\n')
                    self.logCtrl.EndFont()
                else:
                    self.logCtrl.BeginFont(normal_font)
                    self.logCtrl.WriteText(line + '\n')
                    self.logCtrl.EndFont()

        if 1:
            #self.logCtrl.SetFont(italic_font)
            start_pos = self.logCtrl.GetLastPosition()
            
            self.logCtrl.AppendText(message + '\n')
            
            end_pos = self.logCtrl.GetLastPosition()
            self.logCtrl.SetStyle(start_pos, end_pos, wx.TextAttr(color))
        
    def AddOutput(self, message, color=wx.BLACK):
        start_pos = self.logCtrl.GetLastPosition()
        for line in message.splitlines():
            self.logCtrl.AppendText('OUTPUT: '+line + '\n')
            #print(111, line)
            end_pos = self.logCtrl.GetLastPosition()
            self.logCtrl.SetStyle(start_pos, end_pos, wx.TextAttr(color))
    def AddException(self, message, color=wx.RED):
        #normal_font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        #self.logCtrl.SetFont(normal_font)
        start_pos = self.logCtrl.GetLastPosition()
        for line in message.splitlines():
            #print(222, line)
            self.logCtrl.AppendText('EXCEPTION: '+ line + '\n')
            
            end_pos = self.logCtrl.GetLastPosition()
            self.logCtrl.SetStyle(start_pos, end_pos, wx.TextAttr(color))


class Microsoft_Chat_InputPanel(wx.Panel, NewChat,GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Microsoft_Chat_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        chatHistory[self.tab_id]=[]
        #pp(chat)
        pp(all_system_templates[chat.workspace])
        chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Chat[default_chat_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask chatgpt {tab_id}:')
        if 1:
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
  
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

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
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0

        pub.subscribe(self.SetException, 'fix_exception')
        pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
        #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
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

    def RestoreQuestionForTabId(self, message):
        global currentModel
        if message in self.tabs:
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
            prompt=self.evaluate(all_system_templates[chat.workspace].Chat.PROMPT, AttrDict(dict(question=question)))
            chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.tab_id].append(question)
            currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
            currentModel[self.tab_id]=self.model_dropdown.GetValue()


            header=fmt([[prompt]], ['User Question'])
            # DO NOT REMOVE THIS LINE
            print(header)
            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=self.tab_id)
            #pub.sendMessage('chat_output', message=f'{prompt}\n')
            
            
            self.askButton.Disable()
            threading.Thread(target=self.stream_response, args=(prompt, chatHistory, self.tab_id, self.model_dropdown.GetValue())).start()

    def stream_response(self, prompt, chatHistory, tab_id, model):
        # Call stream_response and store the result in out
        self.receiveing_tab_id=tab_id
        rs=ResponseStreamer()
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

class ChatHistoryDialog(wx.Dialog):
    def __init__(self, parent, tab_id, chat_history):
        super(ChatHistoryDialog, self).__init__(parent, title="Chat History", size=(600, 400))
        self.tab_id = tab_id
        self.chat_history = chat_history
        
        # Create the ListCtrl
        self.listCtrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        
        # Add columns
        self.listCtrl.InsertColumn(0, 'Role', width=100)
        self.listCtrl.InsertColumn(1, 'Content', width=450)
        
        # Populate the ListCtrl with chat history
        self.populate_list_ctrl()
        
        # Create a close button
        closeButton = wx.Button(self, label="Close")
        closeButton.Bind(wx.EVT_BUTTON, self.on_close)
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.listCtrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(closeButton, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(sizer)
        
    def populate_list_ctrl(self):
        for entry in self.chat_history[self.tab_id]:
            index = self.listCtrl.InsertItem(self.listCtrl.GetItemCount(), entry['role'])
            self.listCtrl.SetItem(index, 1, entry['content'])
    
    def on_close(self, event):
        self.Close()        
class Microsoft_Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Microsoft_Copilot_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.image_id=1
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        self.chat_type=chat.chat_type
        chatHistory[self.tab_id]=[]
        #chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Copilot[default_copilot_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask Phy-3 {tab_id}:')
        if 0:
            model_names = [DEFAULT_MODEL, 'gpt-4-turbo', 'gpt-4']  # Add more model names as needed
            self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
            self.model_dropdown.SetValue(DEFAULT_MODEL)
            
            self.model_dropdown.Bind(wx.EVT_COMBOBOX, self.OnModelChange)

        if 1:       
            max_new_tokens_values = ["256", "512", "1024", "2048", "4096", "8192", "16384", "32768"]
            # Create a ComboBox for max_new_tokens
            self.max_new_tokens_dropdown = wx.ComboBox(self, choices=max_new_tokens_values, style=wx.CB_READONLY)
            self.max_new_tokens_dropdown.SetValue("2048")  # Default value
            chat.max_new_tokens = "2048"
            self.max_new_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxNewTokensChange)


        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)

        self.historyButton = wx.Button(self, label='History')
        self.historyButton.Bind(wx.EVT_BUTTON, self.onHistoryButton)

        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.max_new_tokens_dropdown, 0, wx.ALIGN_CENTER)
        if 0:
            self.pause_panel=pause_panel=PausePanel(self, self.tab_id)
            askSizer.Add(pause_panel, 0, wx.ALL)
  
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.historyButton, 0, wx.ALIGN_CENTER)
        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)
        if 1:
            q= apc.chats[self.tab_id].question
            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=DEFAULT_MODEL

            #chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]

        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        #self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        self.receiveing_tab_id=0

        #pub.subscribe(self.SetException, 'fix_exception')
        pub.subscribe(self.SetChatDefaults  , 'set_chat_defaults')
        #pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)
        if  not  hasattr(apc, 'vrs'):
            apc.vrs=VisionResponseStreamer(DEFAULT_MODEL)

    def onHistoryButton(self, event):
        global chatHistory
        dialog = ChatHistoryDialog(self, self.tab_id, chatHistory)
        dialog.ShowModal()
        dialog.Destroy()
        
    def OnMaxNewTokensChange(self, event):
        # This method will be called when the selection changes
        selected_value = self.max_new_tokens_dropdown.GetValue()
        print(f"Selected max_new_tokens: {selected_value}")
        chat = apc.chats[self.tab_id]
        chat.max_new_tokens = selected_value
                
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask Phy-3 {tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            assert self.chat_type==tab_id[1]
            chat=apc.chats[tab_id]
  

            self.tabs[self.tab_id]=dict(q=chat.question)
            #chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]
            questionHistory[self.tab_id]=[]
            currentModel[self.tab_id]=DEFAULT_MODEL 
            chatHistory[self.tab_id]=[]       
    def OnModelChange(self, event):
        # Get the selected model
        selected_model = self.model_dropdown.GetValue()

        # Print the selected model
        #print(f"Selected model: {selected_model}")

        # You can add more code here to do something with the selected model

        # Continue processing the event
        event.Skip()

    def RestoreQuestionForTabId(self, message):
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
                image_path=chatDisplay.GetImagePath(self.tab_id)
                assert image_path,chatDisplay
                #print(888, chatDisplay.__class__.__name__)
                #code='print(1223)'
                chat=apc.chats[self.tab_id]
                chat=apc.chats[self.tab_id]

                #question=question.replace('\n', ' ')
                prompt=self.evaluate(all_system_templates[chat.workspace].Copilot.DESCRIBE_IMAGE, dict2(image_id=1, input=question))
                pp(prompt)
                payload =[{"role": "user", "content": prompt}] 


                questionHistory[self.tab_id].append(question)
                currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
                currentModel[self.tab_id]=chat.model_id


                

                # DO NOT REMOVE THIS LINE
                from os.path import basename
                bn=basename(image_path)
                header=fmt([[f'User Question|Hist:{chat.history}|{ self.max_new_tokens_dropdown.GetValue()}']],[])
                print(f'\nFile: {bn}\n')
                print(header)
                print(question)
                pub.sendMessage('chat_output', message=f'{header}\nFile: {bn}\n\n{question}\n', tab_id=self.tab_id)
                #pub.sendMessage('chat_output', message=f'{prompt}\n')
                
                #out=rs.stream_response(prompt, chatHistory[self.q_tab_id])  
                threading.Thread(target=self.stream_response, args=(prompt, payload, self.tab_id, image_path, chat.history)).start()
        except Exception as e:
            print(format_stacktrace())
            self.log(f'Error: {format_stacktrace()}', color=wx.RED)
            pub.sendMessage('stop_progress')
    def stream_response(self, prompt, payload, tab_id,  image_path, keep_history):
        # Call stream_response and store the result in out
        global chatHistory, questionHistory, currentQuestion,currentModel
        self.receiveing_tab_id=tab_id
        
        print(1111, keep_history)
        chatHistory[self.tab_id] += payload
        if keep_history:
            payload=chatHistory[self.tab_id]

        out = apc.vrs.stream_response(prompt, payload, self.receiveing_tab_id, int(self.max_new_tokens_dropdown.GetValue()) ,image_path)
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


class Gpt4_ChatDisplayNotebookPanel(wx.Panel):
    def __init__(self, parent, vendor_tab_id, ws_name):
        super(Gpt4_ChatDisplayNotebookPanel, self).__init__(parent)
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
        pub.subscribe(self.OnWorkspaceTabChanging, 'workspace_tab_changing')
        pub.subscribe(self.OnWorkspaceTabChanged, 'workspace_tab_changed')
        pub.subscribe(self.OnVendorspaceTabChanging, 'vendor_tab_changing')   
        pub.subscribe(self.OnVendorspaceTabChanged, 'vendor_tab_changed')
    def get_active_chat_panel(self):
        active_chat_tab_index = self.chat_notebook.GetSelection()
        if active_chat_tab_index == wx.NOT_FOUND:
            return None
        return self.chat_notebook.GetPage(active_chat_tab_index)
            
    def OnWorkspaceTabChanging(self, message):
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
                pub.sendMessage('restore_question_for_tab_id', message=active_tab_id)

                assert active_tab_id in apc.chats
                chat=apc.chats[active_tab_id]
                print('swapping', active_tab_id )
                pub.sendMessage('swap_input_panel', chat=chat,tab_id=active_tab_id)
                            

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
        title=f'{chat.name}'
        chatDisplay=None
        tab_id=(chat.workspace, chat.chat_type, chat.vendor,self.vendor_tab_id, chat_notebook.GetPageCount())
        self.tabs[chat_notebook.GetPageCount()]=tab_id
        if 1:
            #pp(panels.__dict__)
            #pp(chat.__dict__)
            display_panel = f'Gpt4_{chat.chat_type}_{panels.chat}'
            #print('display_panel', display_panel)
            try:
                assert display_panel in globals()
                print(f'\t\tAdding {chat.workspace} "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
                chatDisplay = cls (chat_notebook, tab_id=tab_id, chat=chat)
                #chatDisplay.SetFocus()
                if 1:
                    pub.sendMessage('swap_input_panel', chat=chat, tab_id=tab_id)
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
        pub.sendMessage('restore_question_for_tab_id', message=tab_id)
        current_chatDisplay = nb.GetPage(newtabIndex)
        #pp(current_chatDisplay.tab_id)
        #e()
        if tab_id in apc.chats:
            chat=apc.chats[tab_id]
            pub.sendMessage('swap_input_panel', chat=chat,tab_id=tab_id)
        # Continue processing the event
        event.Skip()          



    def get_latest_chat_tab_id(self):
        return self.GetPageCount() - 1



#GPT4 Vendor Display Panel
class VendorNotebook(wx.Notebook):
    def __init__(self, parent,ws_name, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.NB_LEFT, name=wx.NotebookNameStr):
        super().__init__(parent, id, pos, size, style, name)      
        
        self.ws_name = ws_name
        pub.subscribe(self.AddTab, 'add_chat')
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        pub.subscribe(self.AddDefaultTabs, 'add_default_tabs')

    def OnMouseMotion(self, event):
        position = event.GetPosition()
        tab_index, _ = self.HitTest(position)
        if tab_index >= 0:
            tab_text = self.GetPageText(tab_index)
            tt = self.GetToolTipText()
            self.SetToolTip(f'{tt}/{tab_text}')
        else:
            self.SetToolTip(None)
        event.Skip()
    def set_focus_on_last_tab(self):
        """ Set focus to the last tab. """
        last_tab_index = self.GetPageCount() - 1
        if last_tab_index >= 0:
            self.SetSelection(last_tab_index)

    def GetToolTipText(self):
        return f'{self.ws_name}'
    def AddDefaultTabs(self):
        for ch in all_chats[self.ws_name]:
            self.AddTab(ch)
        #print('Added default tabs')  
        #set focus on tab 1
        self.set_focus_on_last_tab()

    def OnPageChanging(self, event):
        nb = event.GetEventObject()
        oldTabIndex = event.GetSelection()
        panel = nb.GetPage(oldTabIndex)
        #print(f'VendorNotebook: OnPageChanging FROM {panel.tab_id}, {panel}')   
        pub.sendMessage('vendor_tab_changing', message=panel.tab_id)
        event.Skip()

    def OnPageChanged(self, event):
        nb = event.GetEventObject()
        tabIndex = event.GetSelection()
        panel = nb.GetPage(tabIndex)
        #print(f'VendorNotebook: OnPageChanged TO {panel.tab_id}, {panel}')
        pub.sendMessage('vendor_tab_changed', message=panel.tab_id)
        event.Skip()
     


    def PageExists(self, title):
        for index in range(self.GetPageCount()):
            if self.GetPageText(index) == title:
                return index
        return -1

    def AddTab(self, chat):
        title = f'{chat.vendor}'
        existing_page_index = self.PageExists(title)
        if existing_page_index != -1:
            self.SetSelection(existing_page_index)
            page = self.GetPage(existing_page_index)
            #print(f'EXISTING: "{title}" tab [{self.GetPageCount()}] Adding chat tab to existing vendor', page.__class__.__name__)
            page.AddTab(chat)
        else:
            display_panel = f'{chat.vendor}_ChatDisplayNotebookPanel'
            try:
                assert display_panel in globals().keys()
                cls = globals()[display_panel]
                self.chatDisplay_notebook = cls(self, self.GetPageCount(), self.ws_name)
                #print(f'Adding {chat.vendor}_ChatDisplayNotebookPanel panel:', display_panel)
                self.chatDisplay_notebook.AddTab(chat)
                #self.chatDisplay_notebook.SetFocus()
            except AssertionError:
                raise AssertionError(f"Display class '{display_panel}' does not exist.")
            self.AddPage(self.chatDisplay_notebook, title)
            self.SetSelection(self.GetPageCount() - 1)



class WorkspacePanel(wx.Panel,NewChat):
    def __init__(self, parent, ws_name):
        super(WorkspacePanel, self).__init__(parent)
        self.h_splitter = h_splitter=wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.v_splitter = v_splitter= wx.SplitterWindow(h_splitter, style=wx.SP_LIVE_UPDATE)
        #self.splitter.SetMinimumPaneSize(20)        
         
        self.ws_name=ws_name
        self.vendor_notebook = VendorNotebook(h_splitter, ws_name)
        #self.askButton.Disable()
        self.chatInputs={} 
        if 1: 
            #DUMMY chatInput - 
            # SwapInputPanel will replace this with the actual chatInput
            chat=all_chats[self.ws_name][0]
            self.SwapInputPanel(chat, (chat.workspace,chat.chat_type, chat.vendor,0,0), resplit=False)
        
        if 0:
            self.chatInput = Gpt4_Chat_InputPanel(v_splitter, tab_id=(self.ws_name,0,0))
            
            self.chatInputs[(chat.vendor, chat.chat_type)]=self.chatInput

                
        self.chatInput.SetMinSize((300, 200)) 
        
        self.logPanel = LogPanel(v_splitter)
        self.v_splitter.SplitVertically(self.chatInput, self.logPanel)
        self.h_splitter.SplitHorizontally(self.vendor_notebook, v_splitter)
        #self.h_splitter.SetSashPosition(500)
        sizer = wx.BoxSizer(wx.VERTICAL)
        #sizer.Add(self.notebook, 1, wx.EXPAND|wx.ALL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.h_splitter, 1, wx.EXPAND|wx.ALL)        
        sizer.Add(h_sizer, 1, wx.EXPAND|wx.ALL)
        self.SetSizer(sizer)
        self.v_splitter.SetMinimumPaneSize(200)

        self.chatInput.SetFocus()
        self.Bind(wx.EVT_SIZE, self.OnResize)
        if 1:
            pub.subscribe(self.SwapInputPanel, 'swap_input_panel')

    def SwapInputPanel(self, chat, tab_id, resplit=True):
        #parent = self.GetParent()
        apc.chats[tab_id]=chat
        #print('SwapInputPanel', chat.chat_type)
        v_splitter = self.v_splitter
        if resplit:
            
            #old_chat_input = self.chatInput
            v_splitter.Unsplit(self.chatInput)
        input_id=(chat.vendor, chat.chat_type)
        if tab_id not in apc.pause_output:
            apc.pause_output[tab_id]=[False]
        if tab_id not in apc.stop_output:
            apc.stop_output[tab_id]=[False]
            
        if input_id in self.chatInputs:
            self.chatInput=self.chatInputs[input_id]
            #print(self.chatInput, tab_id)
            self.chatInput.SetTabId(tab_id)
        else:
            if 0:
                if chat.chat_type == 'Chat':
                    #print(f'NEW Gpt4_Chat_InputPanel [{self.vendor_notebook.GetPageCount()}]', tab_id)
                    self.chatInput = Gpt4_Chat_InputPanel(v_splitter,tab_id=tab_id)
                else:
                    #print(f'NEW Gpt4_Copilot_InputPanel [{self.vendor_notebook.GetPageCount()}]', tab_id)
                    self.chatInput = Gpt4_Copilot_InputPanel(v_splitter,tab_id=tab_id)


            chatInput_panel = f'{chat.vendor}_{chat.chat_type}_{panels.input}'
            #print('display_panel', display_panel)
            try:
                
                print(f'\t\tAdding {chat.workspace} "{chat.chat_type}" panel:', chatInput_panel)
                assert chatInput_panel in globals(), f"Display class '{chatInput_panel}' does not exist."
                cls= globals()[chatInput_panel]
                # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
                try:
                    self.chatInput = cls (v_splitter, tab_id=tab_id)
                except:
                    print(format_stacktrace())
                    print(f'Error creating {chatInput_panel}')
                    e(1)
                    

            except AssertionError:
                #raise AssertionError(f"Display class '{display_panel}' does not exist.")
                raise

            self.chatInputs[input_id]=self.chatInput
        #print('SwapInputPanel', self.chatInputs.keys())
        if resplit:
            v_splitter.SplitVertically(self.chatInput, self.logPanel)
            #self.chatInput.SetFocus()
        #old_chat_input.Destroy()

    def OnResize(self, event):
        #print('OnResize')
        # Adjust the sash position to keep the vertical splitter size constant
        width, height=self.GetParent().GetSize()
        self.h_splitter.SetSashPosition(height-self.v_splitter.GetMinimumPaneSize())
        #self.h_splitter.SetSashPosition(self.v_splitter.GetSize().GetHeight())
        event.Skip()
    def SetInputFocus(self):
        self.chatInput.SetFocus()

class Workspace(wx.Panel):
    def __init__(self, parent):
        super(Workspace, self).__init__(parent)
        # Create a notebook
        self.workspace_notebook = wx.Notebook(self)

        # Add vendor panel to the notebook
        for ws_name in all_templates.keys():
            workspace_panel = WorkspacePanel(self.workspace_notebook, ws_name)
            print(f'Adding workspace panel:', ws_name)
            self.workspace_notebook.AddPage(workspace_panel, ws_name)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.workspace_notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)   

        self.workspace_notebook.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.workspace_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.workspace_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
    def set_focus_on_last_tab(self):
        """ Set focus to the last tab. """
        last_tab_index = self.workspace_notebook.GetPageCount() - 1
        if last_tab_index >= 0:
            self.workspace_notebook.SetSelection(last_tab_index)

    def OnPageChanging(self, event):
        nb=event.GetEventObject()
        oldTabIndex = event.GetSelection()
        panel = nb.GetPage(oldTabIndex)
        if type(panel) is WorkspacePanel:
            # Send a message that the tab is changing
            print('OnPageChanging 111', panel)
            pub.sendMessage('workspace_tab_changing', message=panel.ws_name)

        
        event.Skip()

    def OnPageChanged(self, event):
        nb=event.GetEventObject()
        newtabIndex = nb.GetSelection()
        panel = nb.GetPage(newtabIndex)
        
        if type(panel) is WorkspacePanel:
            # Send a message that the tab has changed
            #print('OnPageChanged 222', panel)
            pub.sendMessage('workspace_tab_changed', message=panel.ws_name)
        
        event.Skip()


    def OnMouseMotion(self, event):
        # Get the mouse position
        position = event.GetPosition()
        # Get the tab index under the mouse position
        #print(self.notebook.HitTest(position))
        tab_index, _= self.workspace_notebook.HitTest(position)

        #print(tab_index)
        # If the mouse is over a tab
        if tab_index >= 0:
            # Get the tab text
            tab_text = self.workspace_notebook.GetPageText(tab_index)
            # Set the tab tooltip
            
            self.workspace_notebook.SetToolTip(f'{tab_text} Workspace')
        else:
            self.workspace_notebook.SetToolTip(None)
        event.Skip()
    def GetToolTipText(self):
        #return f'{apc.default_workspace.workspace}'
        pass
    
class MyFrame(wx.Frame, NewChat):
    def __init__(self, title):
        global apc
        super(MyFrame, self).__init__(None, title=title, size=(800, 800))
        apc.chats={}
        apc.chat_panels={}
        self.workspace = apc.workspace = Workspace(self)
        
        #self.mychat.SetMinSize((300, -1))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.workspace, 1, wx.EXPAND|wx.ALL)
       
        self.SetSizer(sizer)

        #self.mychat.SetSize(wx.Size(300, -1))

        self.Centre()

        self.Show()
        self.AddMenuBar()
        self.statusBar = self.CreateStatusBar(2)
        self.statusBar.SetStatusText('Ready')
        #pub.subscribe(self.SetStatusText, 'set_status')
        #pub.subscribe(self.SetStatusText, 'log')
        self.progressBar = wx.Gauge(self.statusBar, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.statusBar.SetStatusWidths([-1, 200])
        
        rect = self.statusBar.GetFieldRect(1)
        self.progressBar.SetPosition((rect.x, rect.y))
        self.progressBar.SetSize((rect.width, rect.height))  
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)   
        pub.subscribe(self.StartProgress, 'start_progress')  
        pub.subscribe(self.StopProgress, 'stop_progress') 
        if 0:
            apc.conda_env=get_current_conda_env()
            print(apc.conda_env)
            if apc.conda_env.endswith('test'):
                
                x, y = self.GetPosition() 
                self.SetPosition((x+100, y+100))

        

        pub.sendMessage('add_default_tabs')
        pub.subscribe(self.SetStatus, 'set_status')
        #self.workspace.set_focus_on_last_tab()
        #self.workspace.workspace_notebook.SetSelection(0)
        #self.workspace.workspace_notebook.SetSelection(1)
    def SetStatus(self, message):
        self.statusBar.SetStatusText(message, 0)
    def StartProgress(self):
        # ...
        # Start the timer
        self.timer.Start(100)
    def OnTimer(self, event):
        # Get the current value of the progress bar
        value = self.progressBar.GetValue()

        # Update the progress bar
        if value < 100:
            self.progressBar.SetValue(value + 1)
        else:
            # Stop the timer when the progress bar reaches 100
            #self.timer.Stop()
            self.progressBar.SetValue(0)  
    def StopProgress(self):
        # ...
        self.timer.Stop()
        self.progressBar.SetValue(100)  

    def SetStatusText(self, message):
        self.statusBar.SetStatusText(message, 0)

    def AddMenuBar(self):
        # Create a menu bar
        menuBar = wx.MenuBar()
        if 1:
            fileMenu = wx.Menu()
            openItem = fileMenu.Append(wx.ID_OPEN, "&Open", "Open a file")
            exitItem = fileMenu.Append(wx.ID_EXIT, "&Exit", "Exit application")

            # Bind file menu items
            self.Bind(wx.EVT_MENU, self.OnOpen, openItem)
            self.Bind(wx.EVT_MENU, self.OnExit, exitItem)

            menuBar.Append(fileMenu, "&File")


        # Create a menu
        chatMenu = wx.Menu()

        # Create a menu item
        newItem = chatMenu.Append(wx.ID_NEW, "New")


        # Bind the event to the handler
        self.Bind(wx.EVT_MENU, self.OnNewChat, newItem)

        # Add the menu to the menu bar
        menuBar.Append(chatMenu, "Chat")
        art_item = chatMenu.Append(wx.ID_ANY, 'Art', 'Open Art')
        # Set the menu bar on the parent window
        self.SetMenuBar(menuBar)


        self.Bind(wx.EVT_MENU, self.OnOpenArt, art_item)
    def OnOpen(self, event):
        #current dir
        default_dir = os.getcwd()
        with wx.FileDialog(self, "Open file", default_dir, wildcard="Image files (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = dialog.GetPath()
            try:
                with open(pathname, 'r') as file:
                    # Read file content here
                    pub.sendMessage('open_image_file', file_path=pathname)
            except IOError:
                wx.LogError("Cannot open file '%s'." % pathname)

    def OnExit(self, event):
        self.Close(True)

    # Step 2: Bind a method to the wx.EVT_MENU event for the "Art" item
    def OnOpenArt(self, event):
        # Create a new dialog
        dialog = wx.Dialog(self, title="Art", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dialog.SetSize((800, 600))  # Set a size for the dialog

        # Create a static bitmap widget to display the image
        static_bitmap = wx.StaticBitmap(dialog)

        # Create buttons
        button1 = wx.Button(dialog, label="1")
        button1.Bind(wx.EVT_BUTTON, lambda event: self.OnButton1(static_bitmap))
        button2 = wx.Button(dialog, label="2")
        button2.Bind(wx.EVT_BUTTON, lambda event: self.OnButton2(static_bitmap))

        # Create a close button
        close_button = wx.Button(dialog, label="Close")
        close_button.Bind(wx.EVT_BUTTON, lambda event: dialog.Close())

        # Create a sizer to layout the widgets
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(static_bitmap, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(button1,0, flag=wx.ALIGN_CENTER)
        h_sizer.Add(button2, 0, flag=wx.ALIGN_CENTER)
        h_sizer.Add((0,0), 1, flag=wx.ALIGN_CENTER)
        h_sizer.Add(close_button,0, flag=wx.ALIGN_CENTER , border=10)
        sizer.Add(h_sizer, 1, flag=wx.EXPAND)
        # Set the sizer to the dialog
        dialog.SetSizer(sizer)
        image = wx.Image(join('Art',f'{apc.default_workspace.name}Copilot_Art_1.jpg'), wx.BITMAP_TYPE_JPEG)
        image_width = image.GetWidth()
        image_height = image.GetHeight()
        dialog_width, dialog_height = dialog.GetSize()
        if image_width > image_height:
            new_width = dialog_width
            new_height = dialog_width * image_height / image_width
        else:
            new_height = dialog_height
            new_width = dialog_height * image_width / image_height
        image = image.Scale(int(new_width), int(new_height), wx.IMAGE_QUALITY_HIGH)
        bitmap = wx.Bitmap(image)
        static_bitmap.SetBitmap(bitmap)
        # Center the dialog
        dialog.Centre()

        # Show the dialog
        dialog.ShowModal()

        # Load the first image


        # Destroy the dialog when it's closed
        dialog.Destroy()

    def OnButton1(self, static_bitmap):
        # Load the second image
        image = wx.Image(join('Art',f'{apc.default_workspace.name}Copilot_Art_1.jpg'), wx.BITMAP_TYPE_JPEG)

        # Resize and display the image
        self.ResizeAndDisplayImage(static_bitmap, image)

    def OnButton2(self, static_bitmap):
        # Load the second image
        image = wx.Image(join('Art',f'{apc.default_workspace.name}Copilot_Art_2.jpg'), wx.BITMAP_TYPE_JPEG)

        # Resize and display the image
        self.ResizeAndDisplayImage(static_bitmap, image)

    def ResizeAndDisplayImage(self, static_bitmap, image):
        # Resize the image to fit the dialog, maintaining aspect ratio
        image_width = image.GetWidth()
        image_height = image.GetHeight()
        dialog_width, dialog_height = static_bitmap.GetSize()
        if image_width > image_height:
            new_width = dialog_width
            new_height = dialog_width * image_height / image_width
        else:
            new_height = dialog_height
            new_width = dialog_height * image_width / image_height
        image = image.Scale(int(new_width), int(new_height), wx.IMAGE_QUALITY_HIGH)
        bitmap = wx.Bitmap(image)
        static_bitmap.SetBitmap(bitmap)

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame(f'Phy-3 Vision')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()