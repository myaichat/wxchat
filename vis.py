import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp 
from include.fmt import fmt
import time, glob,threading, traceback
from os.path import join
import openai
import os, subprocess, yaml, sys
import wx.stc as stc
from wx.stc import StyledTextCtrl

import include.config.init_config as init_config 

init_config.init(**{})
apc = init_config.apc
apc.pause_output = {}
apc.stop_output = {}
e=sys.exit
from dotenv import load_dotenv
load_dotenv()

class dict2(dict):                                                              
    def __setitem__(self, key, value):
        super(dict2, self).__setitem__(key, value)
        #print(f"Set {key} to {value}")
    def __init__(self, *args, **kwargs):                                               
        super(dict2, self).__init__(*args,  **kwargs)                                     

    def __setattr__(self, key, value):                                          
        self[key] = value                                                       

    def __dir__(self):                                                          
        return self.keys()                                                      

    def __getattr__(self, key):                                                 
        try:                                                                    
            return self[key]                                                    
        except KeyError:                                                        
            raise AttributeError(key)                                           

    def __setstate__(self, state):                                              
        pass 

def d2d2(d):
    out=dict2()
    for k, v in d.items():
        if type(v) in [dict]:
            out[k]= d2d2(v)
        else:
            out[k]=v
    return out

class AttrDict(object):
    def __init__(self, adict):
        self.__dict__.update(adict)




#templates = d2d2(dict(Chat={}, Copilot={}))
default_chat_template='SYSTEM'
default_copilot_template='SYSTEM_CHATTY'

dir_path = 'template\\Gpt4'

# list all files in the directory
# list all .yaml files in the directory
yaml_files = glob.glob(f'{dir_path}\\*.yaml')

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


all_templates=dict2()
all_chats=dict2()
all_system_templates=dict2()
# Load the YAML using the custom loader
for yfn in yaml_files:
    bn=os.path.basename(yfn)
    if bn.startswith('_'):
        continue
    with open(yfn, 'r') as file:
        print(f'Loading template {yfn}...')
        data = yaml.load(file, Loader=MyLoader)

        all_templates[data.templates.workspace.name]=data
        all_chats[data.templates.workspace.name] =data.templates.tabs.Chat + data.templates.tabs.Copilot
        for ch in all_chats[data.templates.workspace.name]:
            ch.workspace=data.templates.workspace.name
        all_system_templates[data.templates.workspace.name]=data.templates.System
        #break

#pp(all_templates.keys())
#e()
#all_templates=all_templates.Oracle
apc.default_workspace = list(all_templates.values())[0].templates.workspace



#dws=apc.default_workspace.name







DEFAULT_MODEL  = 'gpt-4o'


chatHistory = {}

questionHistory = {}
currentQuestion = {}
currentModel   = {}

openai.api_key = os.getenv("OPENAI_API_KEY")
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

class ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        

        # Initialize the client
        self.client = openai.OpenAI()

    def stream_response(self, prompt, chatHistory, receiveing_tab_id, model):
        # Create a chat completion request with streaming enabled
        #pp(chatHistory)
        try:
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
            out = []
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
        except Exception as e:
            log(f'Error in stream_response', 'red')
            log(format_stacktrace(), 'red')
            return ''
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
class NewChat(object):
    def __init__(self):
        if 1:
            accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('N'), wx.ID_NEW)])

            # Set the accelerator table for chatInput
            self.SetAcceleratorTable(accel_tbl)

            # Bind the event to the handler
            self.Bind(wx.EVT_MENU, self.OnNewChat, id=wx.ID_NEW)
        #pub.subscribe(self.OnDefaultChat, 'adddefault_chat')
    def OnNewChat(self, event):
        dialog = NewChatDialog(self, title="New Chat")
        if dialog.ShowModal() == wx.ID_OK:
            vendor=dialog.vendor.GetStringSelection()
            chat_type_str = dialog.chat_type.GetStringSelection()
            chat_type =chat_type_str
            name = dialog.name.GetValue()
            system = dialog.system.GetValue()
            chatName = name
            chat=AttrDict(dict(vendor=vendor, chat_type=chat_type, name=name, system=system))
            #pp(chat.__dict__)
            
            print(fmt([[f"New chat: {name}"]], ['New Chat']))
            pub.sendMessage('log', message=f'New chat name: {name}')
            pub.sendMessage('add_chat', chat=chat)
        dialog.Destroy()        
class GetClassName:
    def __init__(self):
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClick)
    def OnRightClick(self, event):
        # Create a popup menu
        menu = wx.Menu()
        
        # Add a menu item to the popup menu
        current_class_name=self.__class__.__name__
        item = menu.Append(wx.ID_ANY, current_class_name)

        pname=self.GetParent().__class__.__name__
        parent_item = menu.Append(wx.ID_ANY, pname)
        
        # Bind the menu item to an event handler
        self.Bind(wx.EVT_MENU, lambda event, name=current_class_name: self.OnCopyName(event, name), item)
        self.Bind(wx.EVT_MENU, lambda event, name=pname: self.OnCopyName(event, name), parent_item)

        
        # Show the popup menu
        self.PopupMenu(menu)
        
        # Destroy the menu after it's used
        menu.Destroy()

    def OnCopyName(self, event, name):
        # Create a data object for the clipboard
        data_object = wx.TextDataObject()

        # Set the class name into the data object
        
        data_object.SetText(name)

        # Copy the text to the clipboard
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(data_object)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox('Unable to open the clipboard', 'Error', wx.OK | wx.ICON_ERROR)

class Scroll_Handlet:
    def __init__(self):
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)

        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scrolled=False
        self.previous_scroll_pos=self.GetScrollPos(wx.VERTICAL)        
        #self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

    def on_scroll(self, event):
        current_scroll_pos = self.GetScrollPos(wx.VERTICAL)

        # If the current scroll position is greater than the previous scroll position,
        # you've scrolled down
        if current_scroll_pos > self.previous_scroll_pos:
            self.scrolled = True
        # If the current scroll position is less than the previous scroll position,
        # you've scrolled up
        elif current_scroll_pos < self.previous_scroll_pos:
            self.scrolled = False

        # Update the previous scroll position
        self.previous_scroll_pos = current_scroll_pos
        event.Skip()

    def on_key_down(self, event):
        if event.GetKeyCode() in [ wx.WXK_PAGEDOWN]:
            self.scrolled = True
        if event.GetKeyCode() in [wx.WXK_PAGEUP]:
            self.scrolled = False    
        if event.ControlDown() and event.GetKeyCode() == ord('P'):
            if self.pause_output:
                self.resume_answer(self.pause_button)
            else:
                self.pause_output = True
                #print('Paused')    
                self.statusbar.SetStatusText('Paused')            
        event.Skip()    

class StyledTextDisplay(stc.StyledTextCtrl, GetClassName, NewChat, Scroll_Handlet):
    def __init__(self, parent):
        super(StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        NewChat.__init__(self)
        Scroll_Handlet.__init__(self)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.SetLexer(stc.STC_LEX_PYTHON)
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

        
class Gpt4_Chat_DisplayPanel(StyledTextDisplay):
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

             



class MyNotebookCodePanel(wx.Panel):
    def __init__(self, parent, tab_id):
        super(MyNotebookCodePanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        
        self.notebook = notebook
        
        self.codeCtrl = stc.StyledTextCtrl(notebook)
        self.codeCtrl.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        self.codeCtrl.SetMarginWidth(0, self.codeCtrl.TextWidth(stc.STC_STYLE_LINENUMBER, '9999'))
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
        pub.subscribe(self.ExecuteFile, 'execute')
        pub.subscribe(self.OnSaveFile, 'save_file')

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


class _Gpt4_Copilot_DisplayPanel(StyledTextDisplay):
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

          


class Gpt4_Copilot_DisplayPanel(wx.Panel):
    def __init__(self, parent, tab_id, chat):
        super(Gpt4_Copilot_DisplayPanel, self).__init__(parent)
        apc.chats[tab_id]=chat
        # Create a splitter window
        self.copilot_splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)
        self.tab_id=tab_id

        # Initialize the notebook_panel and logPanel
        self.notebook_panel=notebook_panel = MyNotebookCodePanel(self.copilot_splitter, tab_id)
        notebook_panel.SetMinSize((-1, 50))
        #notebook_panel.SetMinSize((800, -1))
        self.chatPanel = _Gpt4_Copilot_DisplayPanel(self.copilot_splitter, tab_id)
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

class PauseHandlet:
    def __init__(self,tab_id):
        self.tab_id=tab_id

        #print('-------------setting PauseHandlet', self.tab_id)
        apc.pause_output[self.tab_id]=[False]
        apc.stop_output[self.tab_id]=[False]
        pub.subscribe(self.SetPause, 'pause_output')
        pub.subscribe(self.SetStop, 'stop_output')
    def pause_output(self,on_off=None):
        if on_off is not None:
            apc.pause_output[self.tab_id][0]=on_off
        else:
            return apc.pause_output[self.tab_id][0]

    def stop_output(self,on_off=None):
        if on_off is not None:
            apc.stop_output[self.tab_id][0]=on_off
            if on_off:
                self.stop_button.Disable()
            else:
                self.stop_button.Enable()
                self.pause_button.Enable()
        else:
            return apc.stop_output[self.tab_id][0]
    
    def on_pause(self, event):
        print('\nPause\n')
        if not self.stop_output():
            self.pause_output(not self.pause_output())

            if  self.pause_output():
                #self.statusBar.SetStatusText('Paused')
                pub.sendMessage('set_status', message='Paused')
                event.GetEventObject().SetLabel('Resume')
            else:
                #self.statusBar.SetStatusText('Resumed')
                pub.sendMessage('set_status', message='Resumed')
                event.GetEventObject().SetLabel('Pause')
                #self.resume_answer(event.GetEventObject())  
    def on_stop(self, event):
        print('\nStop\n')
        #self.stop_output(not self.stop_output())
        self.stop_output(True)
        if  1: #self.stop_output():
            #self.statusBar.SetStatusText('Stopped')
            pub.sendMessage('set_status', message='Stopped')
            #event.GetEventObject().SetLabel('Start')
            self.pause_button.Disable()
            self.stop_button.Disable()
        if 0:
            #self.statusBar.SetStatusText('Started')

            pub.sendMessage('set_status', message='Started')
            event.GetEventObject().SetLabel('Stop')
            self.pause_button.Enable()
            self.pause_button.SetLabel('Pause')
    def SetPause(self, message):
        self.pause_output = message
    def SetStop(self, message):
        self.stop_output = message

class PausePanel(wx.Panel,PauseHandlet):
    def __init__(self, parent, tab_id):
        super(PausePanel, self).__init__(parent)
        PauseHandlet.__init__(self, tab_id)
        self.pause_button = wx.Button(self, label="Pause", size=(40, -1))
        self.stop_button = wx.Button(self, label="Stop", size=(40, -1))
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.pause_button, 0, wx.ALL)
        sizer.Add(self.stop_button, 0, wx.ALL)
        self.SetSizer(sizer)
        self.stop_button.Disable()
        self.pause_button.Disable()
        
        
class Base_InputPanel:
    def Base_OnAskQuestion(self):
        self.pause_panel.pause_output(False)
        self.pause_panel.stop_output(False)   
    def evaluate(self,ss, params):
        #a = f"{ss}"
        a=eval('f"""'+ss+'"""')
        return a 
class Gpt4_Chat_InputPanel(wx.Panel, NewChat,GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Gpt4_Chat_InputPanel, self).__init__(parent)
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

        
class Gpt4_Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Gpt4_Copilot_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id
        chat=   apc.chats[tab_id]
        self.chat_type=chat.chat_type
        chatHistory[self.tab_id]=[]
        chatHistory[self.tab_id]= [{"role": "system", "content": all_system_templates[chat.workspace].Copilot[default_copilot_template]}]
        self.askLabel = wx.StaticText(self, label=f'Ask copilot {tab_id}:')
        model_names = [DEFAULT_MODEL, 'gpt-4-turbo', 'gpt-4']  # Add more model names as needed
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
  
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE)
        if 1:
            q= apc.chats[self.tab_id].question
            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=DEFAULT_MODEL
            chatHistory[self.tab_id]= [{"role": "system", "content": chat.system}]

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
            currentModel[self.tab_id]=DEFAULT_MODEL        
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
            prompt=self.evaluate(all_system_templates[chat.workspace].Copilot.FIX_CODE, AttrDict(dict(code=code, input=question)))
            chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.tab_id].append(question)
            currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
            currentModel[self.tab_id]=self.model_dropdown.GetValue()


            header=fmt([[question]], ['User Question'])

            # DO NOT REMOVE THIS LINE
            print(header)
            pub.sendMessage('chat_output', message=f'{header}\n', tab_id=self.tab_id)
            #pub.sendMessage('chat_output', message=f'{prompt}\n')
            
            #out=rs.stream_response(prompt, chatHistory[self.q_tab_id])  
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

            if chat.chat_type == 'Chat':
                #print(f'NEW Gpt4_Chat_InputPanel [{self.vendor_notebook.GetPageCount()}]', tab_id)
                self.chatInput = Gpt4_Chat_InputPanel(v_splitter,tab_id=tab_id)
            else:
                #print(f'NEW Gpt4_Copilot_InputPanel [{self.vendor_notebook.GetPageCount()}]', tab_id)
                self.chatInput = Gpt4_Copilot_InputPanel(v_splitter,tab_id=tab_id)
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
        self.frame = MyFrame(f'All-In-One Copilot')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()