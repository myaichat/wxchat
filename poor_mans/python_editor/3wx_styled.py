import wx
import os
import wx.lib.agw.aui as aui
import wx
from wx.richtext import RichTextCtrl
import wx.stc as stc

MINIMUM_LOGPANEL_HEIGHT=200
class MyTabPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.codeCtrl = stc.StyledTextCtrl(self)
        self.codeCtrl.SetLexer(stc.STC_LEX_PYTHON)
        # Set Python styles
        # Set Python styles
        self.codeCtrl.SetStyleBits(5)
        python_keywords = 'self and as assert break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield'
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
        self.codeCtrl.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#0000FF')  # Change color for variable names to blue
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTBLOCK, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRINGEOL, 'fore:#008000,back:#E0C0E0,eol')
        self.codeCtrl.StyleSetSpec(stc.STC_P_DECORATOR, 'fore:#805000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD2, 'fore:#800080,bold')
        # Set Python styles
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")  # Default
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#008000,back:#FFFFFF")  # Comment
        self.codeCtrl.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")  # Number
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")  # String
        self.codeCtrl.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")  # Character
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  # Triple quotes
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")  # Triple double quotes
        self.codeCtrl.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#00008B,back:#FFFFFF")  # Class name
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#00008B,back:#FFFFFF")  # Function or method name
        self.codeCtrl.StyleSetSpec(stc.STC_P_OPERATOR, "fore:#000000,back:#FFFFFF")  # Operators
        self.codeCtrl.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,back:#FFFFFF")  # Identifiers
        #self.codeCtrl.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#0000FF,back:#FFFFFF,bold")  # Class name
        
        # Set face
        self.codeCtrl.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.codeCtrl, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(sizer)
class MyLogPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.logCtrl = wx.richtext.RichTextCtrl(self, style=wx.VSCROLL|wx.HSCROLL|wx.NO_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.logCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
class MyNotebook(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        

        self.splitter = wx.SplitterWindow(self)
        self.notebook = aui.AuiNotebook(self.splitter)
        self.logPanel = MyLogPanel(self.splitter)
        self.splitter.SplitHorizontally(self.notebook, self.logPanel)
        self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSashPosChanged)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.splitter.SetSashPosition(self.GetSize().height - MINIMUM_LOGPANEL_HEIGHT)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPageClose, self.notebook)
        #SashPosition = self.GetSize().height / 2
        self.Bind(wx.EVT_SIZE, self.OnSize)        
    def OnSize(self, event):
        newSashPosition = self.GetSize().height - MINIMUM_LOGPANEL_HEIGHT
        self.splitter.SetSashPosition(newSashPosition)
        event.Skip() 
    def OnSashPosChanged(self, event):
        global MINIMUM_LOGPANEL_HEIGHT
        MINIMUM_LOGPANEL_HEIGHT = self.GetSize().height - event.GetSashPosition() 
    def OnPageClose(self, event):
            idx = event.GetSelection()
            page = self.notebook.GetPage(idx)
            if page.textCtrl.IsModified():
                dlg = wx.MessageDialog(self, "Do you want to save changes?", 
                                    "Confirm Exit", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
                result = dlg.ShowModal()
                dlg.Destroy()
                if result == wx.ID_OK:
                    with open(page.filePath, 'w') as f:
                        f.write(page.textCtrl.GetValue())
                else:
                    event.Veto()               
class MyFrame(wx.Frame):
    def __init__(self, parent, id=wx.ID_ANY, title="", 
                 pos=wx.DefaultPosition, size=wx.DefaultSize, 
                 style=wx.DEFAULT_FRAME_STYLE, name="myframe"):
        super(MyFrame, self).__init__(parent, id, title, 
                                      pos, size, style, name)


        sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = MyNotebook(self)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Show()

        self.CreateMenuBar()
        self.Center()



    def CreateMenuBar(self):
        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        openItem = fileMenu.Append(wx.ID_OPEN, "&Open", "Open a file")
        saveItem = fileMenu.Append(wx.ID_SAVE, "&Save", "Save the file")
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)

        self.Bind(wx.EVT_MENU, self.OnOpen, openItem)
        self.Bind(wx.EVT_MENU, self.OnSave, saveItem)

        accelTable = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('S'), saveItem.GetId())])
        self.SetAcceleratorTable(accelTable)

    def OnOpen(self, event):
        current_dir = os.getcwd()
        openFileDialog = wx.FileDialog(self, "Open", "", 
                                    current_dir, 
                                    "Python files (*.py)|*.py", 
                                    wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            return     # the user changed their mind

        # Proceed loading the file chosen by the user
        filePath = openFileDialog.GetPath()
        self.OpenFile(filePath)

    def OnSave(self, event):
        idx = self.notebook.GetSelection()
        page = self.notebook.GetPage(idx)
        if page.textCtrl.IsModified():
            fileName = os.path.basename(page.filePath)
            saveFileDialog = wx.FileDialog(self, "Save", "", fileName, 
                                        "Python files (*.py)|*.py", 
                                        wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

            if saveFileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Save the file
            filePath = saveFileDialog.GetPath()
            with open(filePath, 'w') as f:
                f.write(page.textCtrl.GetValue())


    def OpenFile(self, filePath):
        with open(filePath, 'r') as f:
            fileContent = f.read()

        newTab = MyTabPanel(self.notebook)
        newTab.filePath = filePath
        newTab.codeCtrl.SetValue(fileContent)

        fileName = os.path.basename(filePath)
        self.notebook.notebook.AddPage(newTab, fileName)
        self.notebook.notebook.SetSelection(self.notebook.notebook.GetPageCount() - 1)


app = wx.App(False)
frame = MyFrame(None, wx.ID_ANY, "Multi-Tab Python Editor", wx.DefaultPosition, 
                (800, 1000), wx.DEFAULT_FRAME_STYLE)
frame.OpenFile(__file__)
app.MainLoop()