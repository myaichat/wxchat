import wx
import wx.grid as gridlib

class MyFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, wx.ID_ANY, "wx.Grid Example", size=(400, 300))

        self.grid = gridlib.Grid(self)
        self.grid.CreateGrid(5, 2)  # Creating a grid with 5 rows and 2 columns

        for i in range(5):
            self.grid.SetCellValue(i, 0, "Short text")
            self.grid.SetCellValue(i, 1, "This is a longer piece of text that should expand the row \nheight significantly to fit all content.")

        self.grid.AutoSizeColumns()  # Automatically adjust the width of columns to fit content
        self.grid.AutoSizeRows()     # Automatically adjust the height of rows to fit content

app = wx.App(False)
frame = MyFrame(None)
frame.Show(True)
app.MainLoop()