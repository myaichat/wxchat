import wx
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp
from include.fmt import fmt


import openai
import os
from dotenv import load_dotenv
load_dotenv()

SYSTEM ="You are a chatbot that assists with questions. numerate options in answer."
chatHistory = {}

questionHistory = {}
currentQuestion = {}


openai.api_key = os.getenv("OPENAI_API_KEY")

def log(message, color=None):
    pub.sendMessage('log', message=message, color=color)
def set_status(message):
    pub.sendMessage('set_status', message=message)
class ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        

        # Initialize the client
        self.client = openai.OpenAI()

    def stream_response(self, prompt, chatHistory=chatHistory):
        # Create a chat completion request with streaming enabled
        #pp(chatHistory)

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=chatHistory,
            stream=True
        )
        out = []
        # Print each response chunk as it arrives
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                #print(content, end='', flush=True)
                #pp(content)
                if content:
                    out.append(content)
                    pub.sendMessage('chat_output', message=f'{content}')
        if out:
            pub.sendMessage('chat_output', message=f'\n')

        return ''.join(out)


class ChatDisplayPanel(wx.Panel):
    def __init__(self, parent):
        super(ChatDisplayPanel, self).__init__(parent)

        self.chatDisplay = chatDisplay =  wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        # Set the font of chatDisplay
        chatDisplay.SetFont(font)        

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
        global chatHistory, chatHistory, currentQuestion
        super(MyChatInput, self).__init__(parent)
        self.tabs={}
        self.q_tab_id=0

        chatHistory[self.q_tab_id]=[]
        chatHistory[self.q_tab_id]= [{"role": "system", "content": SYSTEM}]
        self.askLabel = wx.StaticText(self, label='Ask chatgpt:')
        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)



        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add((1,1), 1, wx.ALIGN_CENTER|wx.ALL)
  
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        if 1:
            q="Hey,  what is the fastest way to sort in python?"
            self.tabs[0]=dict(q=q)
            questionHistory[0]=[q]
            currentQuestion[0]=0


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

        q=self.inputCtrl.GetValue()
        self.tabs[message]=dict(q=q)
        if 0:
            d={"role": "user", "content":q}
            if self.q_tab_id in chatHistory:
                if d not in chatHistory[self.q_tab_id]:
                    chatHistory[self.q_tab_id] += [{"role": "user", "content":q}]
    def SetQuestionTabId(self, message):
        global chatHistory
        self.q_tab_id=message
        self.tabs[self.q_tab_id]=dict(q="Replace this with your question")
        chatHistory[self.q_tab_id]= [{"role": "system", "content": SYSTEM}]
        questionHistory[self.q_tab_id]=[]
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
        global chatHistory, questionHistory, currentQuestion
        # Get the content of the StyledTextCtrl
        question = self.inputCtrl.GetValue()
        if not question:
            self.log('There is no question!', color=wx.RED)
        else:
            prompt = self.inputCtrl.GetValue()
            self.log(f'Asking: {prompt}')
            pub.sendMessage('start_progress')
            rs=ResponseStreamer()
            
            chatHistory[self.q_tab_id] += [{"role": "user", "content": prompt}]

            questionHistory[self.q_tab_id].append(question)
            currentQuestion[self.q_tab_id]=len(questionHistory[self.q_tab_id])-1


            header=fmt([[prompt]], ['User Question'])
            print(header)
            pub.sendMessage('chat_output', message=f'{header}\n')
            #pub.sendMessage('chat_output', message=f'{prompt}\n')
            
            out=rs.stream_response(prompt, chatHistory[self.q_tab_id])  
            if out:
                chatHistory[self.q_tab_id].append({"role": "assistant", "content": out}) 
            pub.sendMessage('stop_progress')
            log('Done.')
            set_status('Done.')
    def PrevQuestion(self):
        qid=currentQuestion[self.q_tab_id]
        if qid:
            q=questionHistory[self.q_tab_id][qid-1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.q_tab_id]=qid-1
        else:
            self.log('No previous question.', color=wx.RED)
    def NextQuestion(self):
        qid=currentQuestion[self.q_tab_id]
        if len(questionHistory[self.q_tab_id])>qid+1:
            q=questionHistory[self.q_tab_id][qid+1]
            self.inputCtrl.SetValue(q)
            self.inputCtrl.SetFocus()
            currentQuestion[self.q_tab_id]=qid+1
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
        self.statusBar = self.CreateStatusBar(2)
        pub.subscribe(self.SetStatusText, 'set_status')
        #pub.subscribe(self.SetStatusText, 'log')
        self.progressBar = wx.Gauge(self.statusBar, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.statusBar.SetStatusWidths([-1, 200])
        self.statusBar.SetStatusText("Field 1", 0)
        rect = self.statusBar.GetFieldRect(1)
        self.progressBar.SetPosition((rect.x, rect.y))
        self.progressBar.SetSize((rect.width, rect.height))  
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)   
        pub.subscribe(self.StartProgress, 'start_progress')  
        pub.subscribe(self.StopProgress, 'stop_progress') 
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
        self.frame = MyFrame('Poor Man\'s Desktop ChatGPT')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()