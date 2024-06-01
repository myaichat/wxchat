import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp 
from include.fmt import fmt
import time, threading
from os.path import join
import openai
import os, subprocess
import wx.stc as stc
from wx.stc import StyledTextCtrl

import include.config.init_config as init_config 

init_config.init(**{})
apc = init_config.apc
apc.pause_output = {}
apc.stop_output = {}

from dotenv import load_dotenv
load_dotenv()

SYSTEM = "You are a chatbot that assists with Python interview questions. numerate options in answer."
MODEL  = 'gpt-4o'
PYTHON_QUESTION = "What is the difference between a deep copy and a shallow copy?"
#record with 2 values 'Chat'  or 'Copilot'

chatHistory = {}

questionHistory = {}
currentQuestion = {}
currentModel   = {}

openai.api_key = os.getenv("OPENAI_API_KEY")
from enum import Enum

class AttrDict(object):
    def __init__(self, adict):
        self.__dict__.update(adict)


class dict2(dict):                                                              

    def __init__(self, **kwargs):                                               
        super(dict2, self).__init__(kwargs)                                     

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


vendors    =  d2d2({'Gpt4' : d2d2(dict(chat='Chat', copilot='Copilot'))})

panels     = AttrDict(dict(vendor='VendorDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))

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
class ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        

        # Initialize the client
        self.client = openai.OpenAI()

    def stream_response(self, prompt, chatHistory, receiveing_tab_id, model):
        # Create a chat completion request with streaming enabled
        #pp(chatHistory)

        response = self.client.chat.completions.create(
            model=model,
            messages=chatHistory,
            stream=True
        )
        out = []
        # Print each response chunk as it arrives
        stop_output=apc.stop_output[receiveing_tab_id]
        pause_output=apc.pause_output[receiveing_tab_id]
        for chunk in response:
            if stop_output[0] or pause_output[0] :
                
                if stop_output[0] :
                    print('\n-->Stopped\n')
                    pub.sendMessage("stopped")
                    break
                    #pub.sendMessage("append_text", text='\n-->Stopped\n')
                else:
                    while pause_output[0] :
                        time.sleep(0.1)
                        if stop_output[0]:
                            print('\n-->Stopped\n')
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
    def __init__(self, *args, **kwargs):
        super(NewChatDialog, self).__init__(*args, **kwargs)
        self.vendor = wx.RadioBox(self, label="Vendor:", choices=list(vendors.keys()), majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.chat_type = wx.RadioBox(self, label="Gpt:", choices=list(vendors.Gpt4.values()), majorDimension=1, style=wx.RA_SPECIFY_ROWS)

        self.name = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.name.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        self.system = wx.TextCtrl(self,style=wx.TE_MULTILINE, size=(400, 75))
        self.system.SetValue(SYSTEM )
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
            pp(chat.__dict__)
            
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

class StyledTextDisplay(stc.StyledTextCtrl, GetClassName, NewChat):
    def __init__(self, parent):
        super(StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        NewChat.__init__(self)
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
            self.GotoPos(self.GetTextLength())

class Gpt4_Chat_DisplayPanel(StyledTextDisplay):
    def __init__(self, parent, tab_id):
        StyledTextDisplay.__init__(self,parent)
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
        self.tab_id=tab_id

        pub.subscribe(self.AddChatOutput, 'chat_output')
        #pub.subscribe(lambda message, tab_id: self.AddOutput(message, tab_id), 'chat_output')
        pub.subscribe(self.OnShowTabId, 'show_tab_id') 
    def AddChatOutput(self, message, tab_id):
        #print(1111, self.tab_id,tab_id, self.tab_id==tab_id, message)
        if self.tab_id==tab_id:
            #start_pos = self.GetLastPosition()
            if 1: #for line in message.splitlines():

                wx.CallAfter(self.AddOutput, message)
                
                #end_pos = self.chatDisplay.GetLastPosition()
                #self.chatDisplay.SetStyle(start_pos, end_pos, wx.TextAttr(wx.BLACK))        
    def OnShowTabId(self):
        print('show_tab_id', self.tab_id)

             

class Gpt4_Copilot_DisplayPanel(StyledTextDisplay):
    def __init__(self, parent, tab_id):
        StyledTextDisplay.__init__(self,parent)
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.SetFont(font) 
     
        self.tab_id=tab_id
        pub.subscribe(self.AddChatOutput, 'chat_output')
        #pub.subscribe(lambda message, tab_id: self.AddOutput(message, tab_id), 'chat_output')
        pub.subscribe(self.OnShowTabId, 'show_tab_id') 
    def AddChatOutput(self, message, tab_id):
        #print(1111, self.tab_id,tab_id, self.tab_id==tab_id, message)
        if self.tab_id==tab_id:
            #start_pos = self.GetLastPosition()
            if 1: #for line in message.splitlines():

                wx.CallAfter(self.AddOutput, message)
                
                #end_pos = self.chatDisplay.GetLastPosition()
                #self.chatDisplay.SetStyle(start_pos, end_pos, wx.TextAttr(wx.BLACK))        
    def OnShowTabId(self):
        print('show_tab_id', self.tab_id)

          

                                         

class Gpt4_VendorDisplayNotebookPanel(wx.Panel):
    def __init__(self, parent, vendor_tab_id):
        super(Gpt4_VendorDisplayNotebookPanel, self).__init__(parent)
       
        self.chat_notebook = wx.Notebook(self)
        self.vendor_tab_id=vendor_tab_id
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chat_notebook, 1, wx.EXPAND)
        #self.chat_notebook.SetActiveTabColour(wx.RED)
        #self.chat_notebook.SetNonActiveTabTextColour(wx.BLUE)
        self.SetSizer(sizer)        
    def AddTab(self, chat):
        chat_notebook=self.chat_notebook
        title=f'{chat.chat_type}: {chat.name}'
        chatDisplay=None
        tab_id=(self.vendor_tab_id, chat_notebook.GetPageCount())
        if 1:
            #pp(panels.__dict__)
            #pp(chat.__dict__)
            display_panel = f'Gpt4_{chat.chat_type}_{panels.chat}'
            print('display_panel', display_panel)
            try:
                assert display_panel in globals()
                print(f'Adding "{chat.chat_type}" panel:', display_panel)
                cls= globals()[display_panel]
                
                chatDisplay = cls (chat_notebook, tab_id=tab_id)

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
        chatDisplay.tab_id=tab_id=(self.vendor_tab_id, chat_tab_id)
        apc.chats[tab_id]=chat
        pub.sendMessage('set_chat_defaults', tab_id=tab_id)
        self.chat_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.chat_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
    def OnPageChanging(self, event):
        # Code to execute when the notebook page is about to be changed
        print("Notebook page is about to be changed")
        # Get the index of the new tab that is about to be selected
        oldTabIndex = event.GetSelection()

        # Print the index
        print(f"Old tab index: {oldTabIndex}")
        #preserve the question
        
        pub.sendMessage('save_question_for_tab_id', message=(self.vendor_tab_id, oldTabIndex))
        

        # Continue processing the event
        
        event.Skip()

    
    def OnPageChanged(self, event):
        # Code to execute when the notebook page has been changed
        nb=event.GetEventObject()
        newtabIndex = nb.GetSelection()

        # Print the index
        print(f"Selected tab index: {newtabIndex}")
        tab_id=(self.vendor_tab_id, newtabIndex)
        pub.sendMessage('restore_question_for_tab_id', message=tab_id)
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
        self.pause_button = wx.Button(self, label="Pause")
        self.stop_button = wx.Button(self, label="Stop")
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

class Gpt4_Chat_InputPanel(wx.Panel, NewChat,GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Gpt4_Chat_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id

        chatHistory[self.tab_id]=[]
        chatHistory[self.tab_id]= [{"role": "system", "content": SYSTEM}]
        self.askLabel = wx.StaticText(self, label=f'Ask chatgpt {tab_id}:')
        model_names = [MODEL, 'gpt-4-turbo', 'gpt-4']  # Add more model names as needed
        self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
        self.model_dropdown.SetValue(MODEL)
        
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
            q=PYTHON_QUESTION
            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=MODEL


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
        pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask copilot {tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            
            system=apc.chats[self.tab_id].system
            self.tabs[self.tab_id]=dict(q="Replace this with your question")
            chatHistory[self.tab_id]= [{"role": "system", "content": system}]
            questionHistory[self.tab_id]=[]
            currentModel[self.tab_id]=MODEL


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
        self.inputCtrl.SetValue(self.tabs[message]['q'])
        
        self.model_dropdown.SetValue(currentModel[message])
        self.tab_id=message
        #self.q_tab_id=message
        #self.inputCtrl.SetSelection(0, -1)
        self.inputCtrl.SetFocus()
    def SaveQuestionForTabId(self, message):
        global currentModel
        q=self.inputCtrl.GetValue()
        self.tabs[message]=dict(q=q)
        currentModel[message]=self.model_dropdown.GetValue()
        if 0:
            d={"role": "user", "content":q}
            if self.tab_id in chatHistory:
                if d not in chatHistory[self.tab_id]:
                    chatHistory[self.tab_id] += [{"role": "user", "content":q}]
    def SetQuestionTabId(self, new_tab_id):
        global chatHistory
        self.tab_id=new_tab_id
        system=apc.chats[self.tab_id].system
        self.tabs[self.tab_id]=dict(q="Replace this with your question")
        chatHistory[self.tab_id]= [{"role": "system", "content": system}]
        questionHistory[self.tab_id]=[]
        currentModel[self.tab_id]=MODEL
        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        self.inputCtrl.SetFocus()
        self.inputCtrl.SetSelection(0, -1) 

    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        print('Ask button clicked')

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
            prompt = self.inputCtrl.GetValue()
            self.log(f'Asking: {prompt}')
            pub.sendMessage('start_progress')
            
            
            chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.tab_id].append(question)
            currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
            currentModel[self.tab_id]=self.model_dropdown.GetValue()


            header=fmt([[prompt]], ['User Question'])
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

        
class Gpt4_Copilot_InputPanel(wx.Panel, NewChat, GetClassName, Base_InputPanel):
    def __init__(self, parent, tab_id):
        global chatHistory,  currentQuestion, currentModel
        super(Gpt4_Copilot_InputPanel, self).__init__(parent)
        NewChat.__init__(self)
        GetClassName.__init__(self)
        self.tabs={}
        self.tab_id=tab_id

        chatHistory[self.tab_id]=[]
        chatHistory[self.tab_id]= [{"role": "system", "content": SYSTEM}]
        self.askLabel = wx.StaticText(self, label=f'Ask copilot {tab_id}:')
        model_names = [MODEL, 'gpt-4-turbo', 'gpt-4']  # Add more model names as needed
        self.model_dropdown = wx.ComboBox(self, choices=model_names, style=wx.CB_READONLY)
        self.model_dropdown.SetValue(MODEL)
        
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
            q="Hey,  what is the fastest way to sort in python?"
            self.tabs[self.tab_id]=dict(q=q)
            questionHistory[self.tab_id]=[q]
            currentQuestion[self.tab_id]=0
            currentModel[self.tab_id]=MODEL


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
        pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
        wx.CallAfter(self.inputCtrl.SetFocus)
    def SetTabId(self, tab_id):
        self.tab_id=tab_id
        self.askLabel.SetLabel(f'Ask copilot {tab_id}:')
    def SetChatDefaults(self, tab_id):
        global chatHistory, questionHistory, currentModel
        if tab_id ==self.tab_id:
            
            system=apc.chats[self.tab_id].system
            self.tabs[self.tab_id]=dict(q="Replace this with your question")
            chatHistory[self.tab_id]= [{"role": "system", "content": system}]
            questionHistory[self.tab_id]=[]
            currentModel[self.tab_id]=MODEL        
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
        tab_id=message
        if tab_id in self.tabs:
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            self.model_dropdown.SetValue(currentModel[message])
            self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
    def SaveQuestionForTabId(self, message):
        global currentModel
        q=self.inputCtrl.GetValue()
        self.tabs[message]=dict(q=q)
        currentModel[message]=self.model_dropdown.GetValue()
        if 0:
            d={"role": "user", "content":q}
            if self.tab_id in chatHistory:
                if d not in chatHistory[self.tab_id]:
                    chatHistory[self.tab_id] += [{"role": "user", "content":q}]
    def SetQuestionTabId(self, new_tab_id):
        global chatHistory
        self.tab_id=new_tab_id
        system=apc.chats[self.tab_id].system
        self.tabs[self.tab_id]=dict(q="Replace this with your question")
        chatHistory[self.tab_id]= [{"role": "system", "content": system}]
        questionHistory[self.tab_id]=[]
        currentModel[self.tab_id]=MODEL
        self.inputCtrl.SetValue(self.tabs[self.tab_id]['q'])
        self.inputCtrl.SetFocus()
        self.inputCtrl.SetSelection(0, -1) 

    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        print('Ask button clicked')
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
            prompt = self.inputCtrl.GetValue()
            self.log(f'Asking: {prompt}')
            pub.sendMessage('start_progress')
            
            
            chatHistory[self.tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.tab_id].append(question)
            currentQuestion[self.tab_id]=len(questionHistory[self.tab_id])-1
            currentModel[self.tab_id]=self.model_dropdown.GetValue()


            header=fmt([[prompt]], ['User Question'])
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


class VendorNotebook(wx.Notebook):
    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.NB_LEFT, name=wx.NotebookNameStr):
        super().__init__(parent, id, pos, size, style, name)      
        

    
        pub.subscribe(self.AddTab, 'add_chat')
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
 
        pub.subscribe(self.AddDefaultTabs, 'add_default_tabs')
    def AddDefaultTabs(self):
        if 1:
            chat=apc.default_chat 
            self.AddTab(chat)
        
        if 1:
            chat=default_copilot=AttrDict(dict(vendor='Gpt4', chat_type='Copilot', name='Py DEV', system=SYSTEM)) 
            #chat=apc.default_copilot
            self.AddTab(default_copilot)                             
    def OnPageChanging(self, event):
        # Code to execute when the notebook page is about to be changed
        print("Notebook page is about to be changed")
        # Get the index of the new tab that is about to be selected
        oldTabIndex = event.GetSelection()

        # Print the index
        print(f"Old tab index: {oldTabIndex}")
        #preserve the question
        
        pub.sendMessage('vendor_tab_changing', message=oldTabIndex)
        # Continue processing the event
        
        event.Skip()


    def OnPageChanged(self, event):
        # Code to execute when the notebook page has been changed
        tabIndex = self.GetSelection()

        # Print the index
        print(f"Selected tab index: {tabIndex}")
        pub.sendMessage('vendor_tab_changed', message=tabIndex)

        # Continue processing the event
        event.Skip()       


    def PageExists(self, title):
        for index in range(self.GetPageCount()):
            if self.GetPageText(index) == title:
                return index
        return -1
    def AddTab(self,  chat):
        
        title=f'{chat.vendor}'

        existing_page_index = self.PageExists(title)
        if existing_page_index != -1:
            print(f"Vendor Page '{title}' already exists")
            self.SetSelection(existing_page_index)
            page=self.GetPage(existing_page_index)
            print(f'EXISTING: "{title}" tab [{self.GetPageCount()}] Adding chat tab to existing vendor', page.__class__.__name__)
            page.AddTab(chat)
        else:

            print(f"New Vendor Page '{title}'")
            display_panel = f'{chat.vendor}_{panels.vendor}'
            print('display_panel', display_panel)
            try:
                assert display_panel in globals().keys()
                cls= globals()[display_panel]
                self.chatDisplay = cls (self, self.GetPageCount())
                print(f'NEW: "{title}" Adding tab [{self.GetPageCount()}] vendor tab to ', self.chatDisplay.__class__.__name__)
                self.chatDisplay.AddTab(chat)  
                            
            except AssertionError:
                pp(globals().keys())
                #raise AssertionError(f"Display class '{display_panel}' does not exist.")
                raise

            # Add the chat display to the panel
            #chatDisplaySizer = wx.BoxSizer(wx.VERTICAL)
            #chatDisplaySizer.Add(self.chatDisplay, 1, wx.EXPAND)
            #chatDisplayPanel.SetSizer(chatDisplaySizer)

            # Add the panel to the notebook
            self.AddPage(self.chatDisplay, title)
            self.SetSelection(self.GetPageCount() - 1)  
            vendor_tab_id=self.GetPageCount() - 1

        
class WorkspacePanel(wx.Panel,NewChat):
    def __init__(self, parent):
        super(WorkspacePanel, self).__init__(parent)
        self.h_splitter = h_splitter=wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.v_splitter = v_splitter= wx.SplitterWindow(h_splitter, style=wx.SP_LIVE_UPDATE)
        #self.splitter.SetMinimumPaneSize(20)        
        apc.default_chat=chat=AttrDict(dict(vendor='Gpt4', chat_type='Chat', name='Python', system=SYSTEM))  
        
        self.vendor_notebook = VendorNotebook(h_splitter)
        #self.askButton.Disable()
        self.chatInputs={} 
        self.SwapInputPanel(chat, (0,0), resplit=False)
        
        if 0:
            self.chatInput = Gpt4_Chat_InputPanel(v_splitter, tab_id=(0,0))
            
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
        print('SwapInputPanel', chat.chat_type)
        v_splitter = self.v_splitter
        if resplit:
            
            #old_chat_input = self.chatInput
            v_splitter.Unsplit(self.chatInput)
        input_id=(chat.vendor, chat.chat_type)
        
            
        if input_id in self.chatInputs:
            self.chatInput=self.chatInputs[input_id]
           
            self.chatInput.SetTabId(tab_id)
        else:
            if chat.chat_type == 'Chat':
                print(f'NEW Gpt4_Chat_InputPanel [{self.vendor_notebook.GetPageCount()}]', tab_id)
                self.chatInput = Gpt4_Chat_InputPanel(v_splitter,tab_id=tab_id)
            else:
                print(f'NEW Gpt4_Copilot_InputPanel [{self.vendor_notebook.GetPageCount()}]', tab_id)
                self.chatInput = Gpt4_Copilot_InputPanel(v_splitter,tab_id=tab_id)
            self.chatInputs[input_id]=self.chatInput
        print('SwapInputPanel', self.chatInputs.keys())
        if resplit:
            v_splitter.SplitVertically(self.chatInput, self.logPanel)
            self.chatInput.SetFocus()
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



class MyFrame(wx.Frame, NewChat):
    def __init__(self, title):
        global apc
        super(MyFrame, self).__init__(None, title=title, size=(800, 800))
        apc.chats={}
        
        self.workspace = apc.workspace = WorkspacePanel(self)
        
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
        image = wx.Image(join('Art','ChatGPT_Desktop_Art_1.png'), wx.BITMAP_TYPE_PNG)
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
        image = wx.Image(join('Art','ChatGPT_Desktop_Art_1.png'), wx.BITMAP_TYPE_PNG)

        # Resize and display the image
        self.ResizeAndDisplayImage(static_bitmap, image)

    def OnButton2(self, static_bitmap):
        # Load the second image
        image = wx.Image(join('Art','ChatGPT_Desktop_Art_2.png'), wx.BITMAP_TYPE_PNG)

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
        self.frame = MyFrame('Poor Man\'s Desktop ChatGPT')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()