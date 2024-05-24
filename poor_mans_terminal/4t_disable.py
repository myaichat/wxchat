import wx
import subprocess
import wx.richtext as rt
from pprint import pprint as pp
class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.prompt = "user@stackOvervlow:~ "
        self.textctrl = rt.RichTextCtrl(self, -1, '', style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_RICH2|wx.TE_WORDWRAP)
        #'Consolas' 'Lucida Console' 'Courier' 'Monaco'
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName='Lucida Console')
        self.textctrl.SetFont(font)
        self.default_txt = wx.TextAttr(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
      
        #self.textctrl.BeginTextColour(wx.Colour(239, 177, 177))
        self.textctrl.AppendText(self.prompt)

        self.__set_properties()
        self.__do_layout()
        self.__bind_events()
        self.command_history = []
        self.command_index = 0
        self.textctrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)    
        self.textctrl.SetFocus() 
        self.Centre()   
    def on_resize(self, event):
        #self.textctrl.Refresh()
        event.Skip()
    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_UP:
            if self.command_index > 0:
                self.command_index -= 1
                self.set_current_line(self.command_history[self.command_index])
        elif keycode == wx.WXK_DOWN:
            if self.command_index < len(self.command_history) - 1:
                self.command_index += 1
                self.set_current_line(self.command_history[self.command_index])
        else:
            event.Skip() 
    def set_current_line(self, text):
        nl = self.textctrl.GetNumberOfLines()
        self.textctrl.Remove(self.textctrl.XYToPosition(len(self.prompt), nl - 1), self.textctrl.GetLastPosition())
        self.textctrl.AppendText(text)


    def __bind_events(self):
        self.Bind(wx.EVT_TEXT_ENTER, self.__enter)


    def __enter(self, e):
        #print('__enter')
        self.value = (self.textctrl.GetValue())
        self.eval_last_line()
        #e.Skip()


    def __set_properties(self):
        self.SetTitle("Poor Man's Terminal")
        self.SetSize((800, 600))
        self.textctrl.SetFocus()

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.textctrl, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def eval_last_line(self):
        nl = self.textctrl.GetNumberOfLines()
        last_line = self.textctrl.GetLineText(nl - 2)
        command = last_line[len(self.prompt):].strip()
        if not command:  # If the command is empty, return early


            start = self.textctrl.GetLastPosition()
            
            self.textctrl.AppendText(self.prompt)  # Remove the '\n' before the prompt
            end = self.textctrl.GetLastPosition() 
            self.textctrl.SetInsertionPointEnd()
            self.textctrl.ShowPosition(self.textctrl.GetLastPosition())  # Scroll to the bottom

            return
        if not(self.command_history and self.command_history[-1]) == command:
            self.command_history.append(command)
        self.command_index = len(self.command_history)
        
        args = command.split()
        self.textctrl.Disable()
        proc = subprocess.Popen(['cmd', '/C']+args, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with wx.BusyInfo("Processing..."):
            retvalue = proc.communicate()[0]
        self.textctrl.Enable()
        self.textctrl.SetFocus()
        if proc.returncode != 0:
            c = wx.Colour(255, 0, 0)  # Red color for error
        else:
            c = self.default_txt  # black  color for success
        start = self.textctrl.GetLastPosition()  # Get the position of the last character
        self.textctrl.AppendText(retvalue.decode())  # Remove the '\n' before the output
        end = self.textctrl.GetLastPosition()  # Get the position of the new last character

        self.textctrl.SetStyle(start, end, wx.TextAttr(c))  # Set the style of the appended text
        start = self.textctrl.GetLastPosition()
        
        self.textctrl.AppendText(self.prompt)  # Remove the '\n' before the prompt
        end = self.textctrl.GetLastPosition() 
        self.textctrl.SetInsertionPointEnd()
        self.textctrl.ShowPosition(self.textctrl.GetLastPosition())  # Scroll to the bottom

if __name__ == "__main__":
    app = wx.App(0)
    wx.InitAllImageHandlers()
    frame_1 = MyFrame(None, -1, "")
    app.SetTopWindow(frame_1)
    frame_1.Show()
    app.MainLoop()