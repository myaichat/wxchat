import wx
import os
from pubsub import pub

from wx.py.shell import Shell

import subprocess

class CLIEmulator(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="CLI Emulator", size=(600,400))
        panel = wx.Panel(self)

        self.output = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.input.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.output, 1, wx.EXPAND)
        sizer.Add(self.input, 0, wx.EXPAND)
        panel.SetSizer(sizer)

    def OnEnter(self, event):
        command = self.input.GetValue()
        self.input.Clear()

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        self.output.AppendText(f'> {command}\n')
        self.output.AppendText(stdout.decode() + stderr.decode())

app = wx.App(False)
frame = CLIEmulator()
frame.Show()
app.MainLoop()

class RightPanel(wx.Panel):
    def __init__(self, parent):
        super(RightPanel, self).__init__(parent)

        self.control = wx.TextCtrl(self, style = wx.TE_MULTILINE)
        self.shell = Shell(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.control, 1, wx.EXPAND)
        sizer.Add(self.shell, 1, wx.EXPAND)
        self.SetSizer(sizer)
        pub.subscribe(self.open_file, "open_file") 
    def open_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                self.control.SetValue(file.read())
        except FileNotFoundError:
            print("File not found. Please make sure the file path is correct.")
        except Exception as e:
            print(f"An error occurred while reading the file: {e}")
    

class Mywin(wx.Frame): 
    def __init__(self, parent, title): 
        super(Mywin, self).__init__(parent, title = title, size = (500,300)) 

        self.rightPanel = RightPanel(self)
        self.CreateStatusBar() 

        filemenu= wx.Menu() 
        menuOpen = filemenu.Append(wx.ID_OPEN, "Open"," Open text file") 
        menuExit = filemenu.Append(wx.ID_EXIT,"Exit"," Terminate the program") 

        menuBar = wx.MenuBar() 
        menuBar.Append(filemenu,"&File") 
        self.SetMenuBar(menuBar) 

        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen) 
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit) 

        self.Show(True) 

        # Load problem.py into editor upon start
        self.dirname = os.getcwd()  # get current working directory
        self.filename = 'problem.py'

        
        self.SetSize((600, 700))
        self.Centre()
        pub.sendMessage("open_file", file_path=os.path.join(self.dirname, self.filename))
    def OnOpen(self,e): 
        """ Open a file""" 
        self.dirname = os.getcwd()  # get current working directory
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.FD_OPEN) 
        if dlg.ShowModal() == wx.ID_OK: 
            self.filename = dlg.GetFilename() 
            self.dirname = dlg.GetDirectory() 
            pub.sendMessage("open_file", file_path=os.path.join(self.dirname, self.filename))
        dlg.Destroy() 

    def OnExit(self,e): 
        self.Close(True) 

app = wx.App() 
Mywin(None, 'Code Editor') 
app.MainLoop()