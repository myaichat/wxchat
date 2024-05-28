import wx
import subprocess
import wx.richtext as rt

class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        
        # Creating a panel that contains all other controls ensures proper focus and rendering
        self.main_panel = wx.Panel(self)
        
        self.prompt = "user@stackOvervlow:~ "
        
        # Panel for the text control
        self.textctrl_panel = wx.Panel(self.main_panel)
        self.textctrl_panel.SetBackgroundColour(wx.WHITE)
        
        # Rich text control
        self.textctrl = rt.RichTextCtrl(self.textctrl_panel, -1, '', style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_RICH2|wx.TE_WORDWRAP)
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName='Lucida Console')
        self.textctrl.SetFont(font)
        self.default_txt = wx.TextAttr(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        self.textctrl.AppendText(self.prompt + 'conda env list')
        
        # Panel for the button, positioned on top of the text control panel
        self.button_panel = wx.Panel(self.main_panel)
        self.button_panel.SetBackgroundColour(wx.LIGHT_GREY)
        self.button = wx.Button(self.button_panel, -1, 'Activate', pos=(0, 0))
        self.button.SetBackgroundColour(wx.Colour(200, 200, 200))
        
        # Positioning panels and controls manually
        self.main_panel.SetSize((800, 600))
        self.textctrl_panel.SetSize((800, 580))
        self.textctrl.SetSize(self.textctrl_panel.GetSize())
        self.button_panel.SetSize((200, 40))  # Size enough for the button
        self.button_panel.SetPosition((10, 10))
        self.textctrl.SetEvtHandlerEnabled(False)
        # Enable event handling for the button panel
        self.button_panel.SetEvtHandlerEnabled(True)
        # Set the frame's properties and layout
        self.__set_properties()
        self.__bind_events()
        
        self.command_history = []
        self.command_index = 0
        
        self.SetSize((800, 600))
        self.Centre()
        
    # Additional methods...
    
    def __set_properties(self):
        self.SetTitle("Poor Man's Terminal")
    
    def __bind_events(self):
        self.Bind(wx.EVT_TEXT_ENTER, self.__enter)
        self.button.Bind(wx.EVT_BUTTON, self.on_button_click)
    
    def __enter(self, e):
        # Process command when Enter is pressed
        self.eval_last_line()
    
    def eval_last_line(self):
        command = self.textctrl.GetValue().strip()
        if command == 'conda env list':
            # Execute command
            pass
    
    def on_button_click(self, event):
        print("Button clicked!")

if __name__ == "__main__":
    app = wx.App(False)
    frame = MyFrame(None, wx.ID_ANY)
    frame.Show()
    app.MainLoop()