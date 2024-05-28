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
                {"role": "system", "content": "You are a chatbot that assists with Python interview ."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        # Print each response chunk as it arrives
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                #print(content, end='', flush=True)
                #pp(content)

                pub.sendMessage('chat_output', message=f'{content}')


class ChatDisplayPanel(wx.Panel):
    def __init__(self, parent):
        super(ChatDisplayPanel, self).__init__(parent)

        self.chatDisplay = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chatDisplay, 1, wx.EXPAND)
        self.SetSizer(sizer) 
        pub.subscribe(self.AddOutput, 'chat_output')
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

        self.askLabel = wx.StaticText(self, label='Ask chatgpt:')
        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)
        if 1:
            self.fixButton = wx.Button(self, label='Fix')
            self.fixButton.Bind(wx.EVT_BUTTON, self.onFixButton)
            self.fixButton.Disable()


        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add((1,1), 1, wx.ALIGN_CENTER|wx.ALL)
        askSizer.Add(self.fixButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.inputCtrl.SetValue("Hey,  what is the fastest way to sort in python?")
        self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        pub.subscribe(self.SetException, 'fix_exception')
    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        print('Ask button clicked')
        rs=ResponseStreamer()
        prompt = self.inputCtrl.GetValue()
        rs.stream_response(prompt)  
    def onFixButton(self, event):
        if not self.ex:
            wx.MessageBox('No exception to fix', 'Error', wx.OK | wx.ICON_ERROR)
        else:
            # Code to execute when the Ask button is clicked
            print('Fix button clicked')
            rs=ResponseStreamer()
            prompt = self.ex.GetFixPrompt()
            rs.stream_response(prompt) 

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            self.AskQuestion()
        else:
            event.Skip()
    def AskQuestion(self):
        # Get the content of the StyledTextCtrl
        question = self.inputCtrl.GetValue()
        if not question:
            self.log('There is no question!', color=wx.RED)
        else:
            #self.log('Question: ' + question)
            self.log(question)

    def log(self, message, color=wx.BLUE):
        
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}', color=color)



class MyChatPanel(wx.Panel):
    def __init__(self, parent):
        super(MyChatPanel, self).__init__(parent)

        self.chatDisplay = ChatDisplayPanel (self)


        #self.askButton.Disable() 
        self.chatInput = MyChatInput(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chatDisplay, 1, wx.EXPAND)



        sizer.Add(self.chatInput, 0, wx.EXPAND)
        self.SetSizer(sizer)

               
    
class MyTabPanel(wx.Panel):
    def __init__(self, parent):
        super(MyTabPanel, self).__init__(parent)
        notebook = aui.AuiNotebook(self)
        logPanel = LogPanel(self)
        self.notebook = notebook
        self.logPanel = logPanel
        self.textCtrl = stc.StyledTextCtrl(notebook)
        self.textCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.textCtrl.SetLexer(stc.STC_LEX_PYTHON)
        self.textCtrl.SetValue("print('Hello, World!');\na=1/0")
        notebook.AddPage(self.textCtrl, "Tab 1")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        sizer.Add(self.logPanel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Layout()
        pub.subscribe(self.ExecuteFile, 'execute')

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('E') or event.GetKeyCode() == wx.WXK_RETURN):
            self.log('Executing...')
            #pub.sendMessage('execute')
            self.ExecuteFile()
            self.log('Done.')
            #self.ExecuteFile()
        else:
            event.Skip()
    def log(self, message):
        
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}')
    def output(self, message):
        
        pub.sendMessage('output', message=f'{message}') 
    def exception(self, message):
        
        pub.sendMessage('exception', message=f'{message}')  

    def ExecuteFile(self):
        # Get the content of the StyledTextCtrl
        code = self.textCtrl.GetText()

        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(code.encode())
            temp_file_name = f.name

        # Execute the temporary Python file
        process = subprocess.Popen(['python', temp_file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # If there's an exception, make the text red in the log
        if stderr:
            self.output(stdout.decode())
            self.exception(stderr.decode())
            
            ex=CodeException(stderr.decode())
            self.fixButton.Enable()
            pub.sendMessage('fix_exception', message=ex)
        else:
            self.output(stdout.decode())

class CodeException(object):
    def __init__(self, message):
        super(CodeException, self).__init__(message)
        self.message = message
        
class MyFrame(wx.Frame):
    def __init__(self, title):
        super(MyFrame, self).__init__(None, title=title, size=(800, 800))

        self.panel = MyTabPanel(self)
        self.mychat = MyChatPanel(self)
        self.mychat.SetMinSize((300, -1))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.mychat, 1, wx.EXPAND)
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.mychat.SetSize(wx.Size(300, -1))

        self.Centre()

        self.Show()

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame('Poor Man\'s Copilot')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()