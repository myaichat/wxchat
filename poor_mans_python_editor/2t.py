import wx
import tempfile
import subprocess
import wx.stc as stc
import wx.lib.agw.aui as aui

class LogPanel(wx.Panel):
    def __init__(self, parent):
        super(LogPanel, self).__init__(parent, size=(800, 200))
        self.logCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.logCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def AddLog(self, message, color=wx.BLACK):
        start_pos = self.logCtrl.GetLastPosition()
        self.logCtrl.AppendText(message + '\n')
        end_pos = self.logCtrl.GetLastPosition()
        self.logCtrl.SetStyle(start_pos, end_pos, wx.TextAttr(color))

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

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('E') or event.GetKeyCode() == wx.WXK_RETURN):
            self.ExecuteFile()
        else:
            event.Skip()

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
            self.logPanel.AddLog(stderr.decode(), color=wx.RED)
        else:
            self.logPanel.AddLog(stdout.decode())

class MyFrame(wx.Frame):
    def __init__(self, title):
        super(MyFrame, self).__init__(None, title=title, size=(800, 600))
        self.panel = MyTabPanel(self)
        self.Show()

class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame('My App')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()