import wx
import os
import wx.lib.agw.aui as aui

class MyTabPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.textCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.textCtrl, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(sizer)
class MyLogPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.logCtrl = wx.richtext.RichTextCtrl(self, style=wx.VSCROLL|wx.HSCROLL|wx.NO_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.logCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
class MyFrame(wx.Frame):
    def __init__(self, parent, id=wx.ID_ANY, title="", 
                 pos=wx.DefaultPosition, size=wx.DefaultSize, 
                 style=wx.DEFAULT_FRAME_STYLE, name="myframe"):
        super(MyFrame, self).__init__(parent, id, title, 
                                      pos, size, style, name)
        self._mgr = aui.AuiManager(self)

        self.notebook = aui.AuiNotebook(self)
        self._mgr.AddPane(self.notebook, aui.AuiPaneInfo().CenterPane().Name("Notebook"))

        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPageClose, self.notebook)

        self._mgr.Update()
        self.Show()
        self.CreateMenuBar()

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
        openFileDialog = wx.FileDialog(self, "Open", "", "", 
                                    "Text files (*.txt)|*.txt", 
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
                                        "Text files (*.txt)|*.txt", 
                                        wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

            if saveFileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Save the file
            filePath = saveFileDialog.GetPath()
            with open(filePath, 'w') as f:
                f.write(page.textCtrl.GetValue())
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

    def OpenFile(self, filePath):
        with open(filePath, 'r') as f:
            fileContent = f.read()

        newTab = MyTabPanel(self.notebook)
        newTab.filePath = filePath
        newTab.textCtrl.SetValue(fileContent)

        fileName = os.path.basename(filePath)
        self.notebook.AddPage(newTab, fileName)
        self.notebook.SetSelection(self.notebook.GetPageCount() - 1)


app = wx.App(False)
frame = MyFrame(None, wx.ID_ANY, "Multi-Tab Editor", wx.DefaultPosition, 
                (800, 600), wx.DEFAULT_FRAME_STYLE)
frame.OpenFile('test.txt')
app.MainLoop()