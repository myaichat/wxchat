import wx
import tempfile
import subprocess
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub

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

        self.inputCtrl = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.inputCtrl.SetValue('Fix that exception')
        self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
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
class MyChat(wx.Panel):
    def __init__(self, parent):
        super(MyChat, self).__init__(parent)

        self.chatDisplay = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.askLabel = wx.StaticText(self, label='Ask chatgpt:')
        self.chatInput = MyChatInput(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chatDisplay, 1, wx.EXPAND)
        sizer.Add(self.askLabel, 0, wx.ALIGN_LEFT|wx.ALL, 2)
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
        else:
            self.output(stdout.decode())

class MyFrame(wx.Frame):
    def __init__(self, title):
        super(MyFrame, self).__init__(None, title=title, size=(800, 800))

        self.panel = MyTabPanel(self)
        self.mychat = MyChat(self)
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
        self.frame = MyFrame('My App')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()