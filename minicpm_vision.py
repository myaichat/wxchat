#
#try: https://ai.azure.com/explore/models/Phi-3-vision-128k-instruct/version/1/registry/azureml
# https://inference.readthedocs.io/en/latest/models/model_abilities/vision.html
#import onnxruntime_genai as og

import argparse
import time

import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp 
from include.fmt import fmt,pfmtd,pfmtv,pfmt, pfmtdv, fmtv
import time, random, glob,threading, traceback
from os.path import join
from datetime import datetime
import os, subprocess, yaml, sys
import wx.stc as stc
from PIL import Image as PILImage





import include.config.init_config as init_config 

init_config.init(**{})
apc = init_config.apc
apc.pause_output = {}
apc.stop_output = {}
DEFAULT_MODEL  = "microsoft/Phi-3-vision-128k-instruct"



apc.chatHistory = chatHistory={}

apc.questionHistory = questionHistory={}
apc.currentQuestion = currentQuestion={}
apc.currentModel   = {}



e=sys.exit
from dotenv import load_dotenv
load_dotenv()

from include.Common import *

apc.all_templates=all_templates=dict2()
apc.all_chats=all_chats=dict2()
apc.all_system_templates= all_system_templates=dict2()
if 0:
    from include.Phy3_Python import Microsoft_Chat_InputPanel, \
        Microsoft_ChatDisplayNotebookPanel, Microsoft_Copilot_InputPanel
if 1:
    from include.Gpt4_Python import Gpt4_Chat_InputPanel, Gpt4_ChatDisplayNotebookPanel, \
        Gpt4_Chat_DisplayPanel, Gpt4_Copilot_DisplayPanel, Gpt4_Copilot_InputPanel

from include.MiniCPM_Vision import  OpenBNB_ChatDisplayNotebookPanel, OpenBNB_Copilot_InputPanel

#print('Microsoft_ChatDisplayNotebookPanel' in globals())
#e()

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

pp(all_templates.keys())
#e()
#all_templates=all_templates.Oracle
apc.default_workspace = list(all_templates.values())[0].templates.workspace






from enum import Enum



panels     = AttrDict(dict(workspace='WorkspacePanel', vendor='ChatDisplayNotebookPanel',chat='DisplayPanel', input='InputPanel'))


    
def log(message, color=None):
    pub.sendMessage('log', message=message, color=color)
def set_status(message):
    pub.sendMessage('set_status', message=message)
def format_stacktrace():
    parts = ["Traceback (most recent call last):\n"]
    parts.extend(traceback.format_stack(limit=25))
    parts.extend(traceback.format_exception(*sys.exc_info())[1:])
    return "".join(parts)



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



class LogPanel(wx.Panel):
    subscribed = False
    def __init__(self, parent):
        super(LogPanel, self).__init__(parent)
        self.logCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        self.default_font = self.logCtrl.GetFont()
        monospaced_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.logCtrl.SetFont(monospaced_font)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.logCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        if not LogPanel.subscribed:
       
            pub.subscribe(self.AddLog, 'log')
            pub.subscribe(self.AddOutput, 'output')
            pub.subscribe(self.AddException, 'exception')
            LogPanel.subscribed = True

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


#GPT4 Vendor Display Panel
class VendorNotebook(wx.Notebook):
    subscribed = False
    def __init__(self, parent,ws_name, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.NB_LEFT, name=wx.NotebookNameStr):
        super().__init__(parent, id, pos, size, style, name)      
        
        self.ws_name = ws_name
        
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        if not VendorNotebook.subscribed:
            pub.subscribe(self.AddDefaultTabs, 'add_default_tabs')
            pub.subscribe(self.AddTab, 'add_chat')
            VendorNotebook.subscribed = True

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
                #assert display_panel in globals()
                cls = globals()[display_panel]
                self.chatDisplay_notebook = cls(self, self.GetPageCount(), self.ws_name)
                #print(f'Adding {chat.vendor}_ChatDisplayNotebookPanel panel:', display_panel)
                self.chatDisplay_notebook.AddTab(chat)
                #self.chatDisplay_notebook.SetFocus()
            except :
                print('Microsoft_ChatDisplayNotebookPanel' in globals())
                raise
                #raise AssertionError(f"Display class '{display_panel}' does not exist.")
            self.AddPage(self.chatDisplay_notebook, title)
            self.SetSelection(self.GetPageCount() - 1)



class WorkspacePanel(wx.Panel,NewChat):
    subscribed = False
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
            tab_id=(chat.workspace,chat.chat_type, chat.vendor,0,0)
            apc.chats[tab_id]=chat
            self.SwapInputPanel(tab_id , resplit=False)
        
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
        if not WorkspacePanel.subscribed:
            pub.subscribe(self.SwapInputPanel, 'swap_input_panel')
            WorkspacePanel.subscribed = True

    def SwapInputPanel(self,  tab_id, resplit=True):
        print('SwapInputPanel 111', tab_id)
        #parent = self.GetParent()
        #apc.chats[tab_id]=chat
        chat=apc.chats[tab_id]
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
            #self.chatInput.SetTabId(tab_id)
            self.chatInput.tab_id=tab_id
            self.chatInput.RestoreQuestionForTabId(tab_id)
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
                
                print(f'\t\tWorkspace|resplit[{resplit}]: Adding {chat.workspace} "{chat.chat_type}" panel:', chatInput_panel)
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
            #self.chatInput.tab_id=tab_id
            
            self.chatInput.RestoreQuestionForTabId(tab_id)
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
        super(MyFrame, self).__init__(None, title=title, size=(1400, 1000))
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
        self.statusBar = self.CreateStatusBar(3)
        self.statusBar.SetStatusText('Ready')
        self.statusBar.SetStatusText('System', 1)
        #pub.subscribe(self.SetStatusText, 'set_status')
        #pub.subscribe(self.SetStatusText, 'log')
        self.progressBar = wx.Gauge(self.statusBar, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.statusBar.SetStatusWidths([50, -1,200])
        
        rect = self.statusBar.GetFieldRect(2)
        self.progressBar.SetPosition((rect.x, rect.y))
        self.progressBar.SetSize((rect.width, rect.height))  
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)   
        pub.subscribe(self.StartProgress, 'start_progress')  
        pub.subscribe(self.StopProgress, 'stop_progress') 
        pub.subscribe(self.SetSystemPrompt, 'set_system_prompt')
        self.system_prompt={} 
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
    def SetSystemPrompt(self, message,tab_id):
        self.system_prompt[tab_id]=message
        self.statusBar.SetStatusText(message, 1)    
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
        self.frame = MyFrame(f'MiniCPM Vision')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()