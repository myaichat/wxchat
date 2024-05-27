import wx
import tempfile
import subprocess
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp

import openai
import os
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
class ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        

        # Initialize the client
        self.client = openai.OpenAI()

    def stream_response(self, prompt):
        # Create a chat completion request with streaming enabled
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a chatbot that assists questions."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        has_content = []
        # Print each response chunk as it arrives
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                #print(content, end='', flush=True)
                #pp(content)
                if content:
                    has_content = True
                    pub.sendMessage('chat_output', message=f'{content}')
        if has_content:
            pub.sendMessage('chat_output', message=f'\n')



class ChatDisplayPanel(wx.Panel):
    def __init__(self, parent):
        super(ChatDisplayPanel, self).__init__(parent)

        self.chatDisplay = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chatDisplay, 1, wx.EXPAND)
        self.SetSizer(sizer) 
        pub.subscribe(self.AddOutput, 'chat_output')

        if 1:
            accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('N'), wx.ID_NEW)])

            # Set the accelerator table for chatInput
            self.chatDisplay.SetAcceleratorTable(accel_tbl)

            # Bind the event to the handler
            self.chatDisplay.Bind(wx.EVT_MENU, self.OnNewChat, id=wx.ID_NEW)

    def OnNewChat(self, event):
        # Code to execute when the "New" item is selected
        dialog = wx.TextEntryDialog(self, "Enter new chat name", "New Chat")

        # Show the dialog and get the result
        if dialog.ShowModal() == wx.ID_OK:
            chatName = dialog.GetValue()
            print(f"New chat name: {chatName}")
            pub.sendMessage('log', message=f'New chat name: {chatName}')
            pub.sendMessage('add_chat', message=chatName)

        # Destroy the dialog
        dialog.Destroy()

    def AddOutput(self, message):
        start_pos = self.chatDisplay.GetLastPosition()
        if 1: #for line in message.splitlines():
            self.chatDisplay.AppendText(message)
            end_pos = self.chatDisplay.GetLastPosition()
            self.chatDisplay.SetStyle(start_pos, end_pos, wx.TextAttr(wx.BLACK))



class LogPanel(wx.Panel):
    def __init__(self, parent):
        super(LogPanel, self).__init__(parent, size=(800, 200))
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
            print(111, line)
            end_pos = self.logCtrl.GetLastPosition()
            self.logCtrl.SetStyle(start_pos, end_pos, wx.TextAttr(color))
    def AddException(self, message, color=wx.RED):
        #normal_font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        #self.logCtrl.SetFont(normal_font)
        start_pos = self.logCtrl.GetLastPosition()
        for line in message.splitlines():
            print(222, line)
            self.logCtrl.AppendText('EXCEPTION: '+ line + '\n')
            
            end_pos = self.logCtrl.GetLastPosition()
            self.logCtrl.SetStyle(start_pos, end_pos, wx.TextAttr(color))
    
class MyChatInput(wx.Panel):
    def __init__(self, parent):
        super(MyChatInput, self).__init__(parent)
        self.tabs={}
        self.askLabel = wx.StaticText(self, label='Ask chatgpt:')
        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)



        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add((1,1), 1, wx.ALIGN_CENTER|wx.ALL)
  
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.tabs[0]=dict(q="Hey,  what is the fastest way to sort in python?")
        self.inputCtrl.SetValue(self.tabs[0]['q'])
        self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None

        pub.subscribe(self.SetException, 'fix_exception')
        pub.subscribe(self.SetQuestionTabId  , 'set_question_tab_id')
        pub.subscribe(self.SaveQuestionForTabId  ,  'save_question_for_tab_id')
        pub.subscribe(self.RestoreQuestionForTabId  ,  'restore_question_for_tab_id')
    def RestoreQuestionForTabId(self, message):
        self.inputCtrl.SetValue(self.tabs[message]['q'])
        self.inputCtrl.SetFocus()
        #self.inputCtrl.SetSelection(0, -1)
    def SaveQuestionForTabId(self, message):
        self.tabs[message]=dict(q=self.inputCtrl.GetValue())
    def  SetQuestionTabId(self, message):
        self.q_tab_id=message
        self.tabs[self.q_tab_id]=dict(q="Replace this with your question")
        self.inputCtrl.SetValue(self.tabs[self.q_tab_id]['q'])
        self.inputCtrl.SetFocus()
        self.inputCtrl.SetSelection(0, -1) 

    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        print('Ask button clicked')
        self.AskQuestion()
    def AskQuestion(self):
        # Get the content of the StyledTextCtrl
        question = self.inputCtrl.GetValue()
        if not question:
            self.log('There is no question!', color=wx.RED)
        else:
            prompt = self.inputCtrl.GetValue()
            self.log(f'Asking: {prompt}')
            rs=ResponseStreamer()
            
            
            rs.stream_response(prompt)  
            self.log('Done')

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            self.AskQuestion()
        else:
            event.Skip()


    def log(self, message, color=wx.BLUE):
        
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}', color=color)


class ChatNotebook(wx.Notebook):
    def __init__(self, parent):
        super().__init__(parent)        
        self.AddTab('Python Sort')
        pub.subscribe(self.AddTab, 'add_chat')
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
    def OnPageChanging(self, event):
        # Code to execute when the notebook page is about to be changed
        print("Notebook page is about to be changed")
        # Get the index of the new tab that is about to be selected
        oldTabIndex = event.GetSelection()

        # Print the index
        print(f"Old tab index: {oldTabIndex}")
        #preserve the question
        
        pub.sendMessage('save_question_for_tab_id', message=oldTabIndex)
        # Continue processing the event
        event.Skip()


    def OnPageChanged(self, event):
        # Code to execute when the notebook page has been changed
        tabIndex = self.GetSelection()

        # Print the index
        print(f"Selected tab index: {tabIndex}")
        pub.sendMessage('restore_question_for_tab_id', message=tabIndex)

        # Continue processing the event
        event.Skip()       


    def AddTab(self, message):
        title=message
        chatDisplayPanel = wx.Panel(self)
        self.chatDisplay = ChatDisplayPanel (chatDisplayPanel)
        # Add the chat display to the panel
        chatDisplaySizer = wx.BoxSizer(wx.VERTICAL)
        chatDisplaySizer.Add(self.chatDisplay, 1, wx.EXPAND)
        chatDisplayPanel.SetSizer(chatDisplaySizer)

        # Add the panel to the notebook
        self.AddPage(chatDisplayPanel, title)
        self.SetSelection(self.GetPageCount() - 1)
        tab_id=self.GetPageCount() - 1
        pub.sendMessage('set_question_tab_id', message=tab_id)
        
class MyChatPanel(wx.Panel):
    def __init__(self, parent):
        super(MyChatPanel, self).__init__(parent)

        

        self.notebook = ChatNotebook(self)
        #self.askButton.Disable() 
        self.chatInput = MyChatInput(self)
        self.chatInput.SetMinSize((300, -1)) 
        
        self.logPanel = LogPanel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND|wx.ALL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.chatInput, 0, wx.EXPAND|wx.ALL)
        h_sizer.Add(self.logPanel, 0, wx.EXPAND|wx.ALL)
        sizer.Add(h_sizer, 0, wx.EXPAND|wx.ALL)
        self.SetSizer(sizer)
        if 1:
            accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('N'), wx.ID_NEW)])

            # Set the accelerator table for chatInput
            self.chatInput.SetAcceleratorTable(accel_tbl)

            # Bind the event to the handler
            self.chatInput.Bind(wx.EVT_MENU, self.OnNewChat, id=wx.ID_NEW)
        self.chatInput.SetFocus()
    def OnNewChat(self, event):
        # Code to execute when the "New" item is selected
        dialog = wx.TextEntryDialog(self, "Enter new chat name", "New Chat")

        # Show the dialog and get the result
        if dialog.ShowModal() == wx.ID_OK:
            chatName = dialog.GetValue()
            print(f"New chat name: {chatName}")
            pub.sendMessage('log', message=f'New chat name: {chatName}')
            pub.sendMessage('add_chat', message=chatName)

        # Destroy the dialog
        dialog.Destroy()
    def SetInputFocus(self):
        self.chatInput.SetFocus()
class MyFrame(wx.Frame):
    def __init__(self, title):
        super(MyFrame, self).__init__(None, title=title, size=(800, 800))

        
        self.mychat = MyChatPanel(self)
        #self.mychat.SetMinSize((300, -1))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.mychat, 1, wx.EXPAND|wx.ALL)
       
        self.SetSizer(sizer)

        #self.mychat.SetSize(wx.Size(300, -1))

        self.Centre()

        self.Show()
        self.AddMenuBar()
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

        # Set the menu bar on the parent window
        self.SetMenuBar(menuBar)
    def OnNewChat(self, event):
        # Code to execute when the "New" item is selected
        dialog = wx.TextEntryDialog(self, "Enter new chat name", "New Chat")

        # Show the dialog and get the result
        if dialog.ShowModal() == wx.ID_OK:
            chatName = dialog.GetValue()
            print(f"New chat name: {chatName}")
            pub.sendMessage('log', message=f'New chat name: {chatName}')
            pub.sendMessage('add_chat', message=chatName)

        # Destroy the dialog
        dialog.Destroy()


class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame('Poor Man\'s  ChatGPT')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()