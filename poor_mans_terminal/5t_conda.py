import wx
import os, sys
import subprocess
import wx.richtext as rt
from pprint import pprint as pp
class MyFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.main_panel = wx.Panel(self)
        self.prompt = "user@stackOvervlow:~ "

        if 1:
            self.textctrl = rt.RichTextCtrl(self.main_panel, -1, '', style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_RICH2|wx.TE_WORDWRAP)
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
            self.textctrl.AppendText('conda env list')
        if 0:
            # Panel for the button, ensuring it is above the text control
            self.button_panel = wx.Panel(self.main_panel)
            self.button_panel.SetWindowStyle(wx.STAY_ON_TOP) 
            self.button = wx.Button(self.button_panel, -1, 'Activate', pos=(0, 0))
            self.button.SetBackgroundColour(wx.Colour(200, 200, 200))
            self.button.Bind(wx.EVT_BUTTON, self.on_button_click)
            
            # Positioning panels and controls manually
            self.main_panel.SetSize((800, 600))
            self.textctrl.SetSize((800, 580))
            self.button_panel.SetPosition((10, 10))
            self.button_panel.SetSize((200, 40))  # Size enough for the button

            # Ensure the button is visible and functional
            self.button_panel.Raise()
            self.button_panel.Show()
            self.button.Refresh()
            self.button.Update()
        

        self.SetSize((800, 600))
        self.Centre() 
        #wx.CallLater(1, self.simulate_hover, self.button)  # Simulate a hover effect
    def simulate_hover(self,button):
        # Create an instance of wx.UIActionSimulator
        simulator = wx.UIActionSimulator()
        
        # Get the position of the button relative to the screen
        button_pos = button.ClientToScreen(wx.Point(0, 0))
        
        # Move the mouse to the center of the button
        button_center_x = button_pos.x + button.GetSize().GetWidth() // 2
        button_center_y = button_pos.y + button.GetSize().GetHeight() // 2
        simulator.MouseMove(button_center_x, button_center_y)
        
        # Optionally, you can add a small delay to simulate a realistic hover
        #wx.MilliSleep(100)  # Delay of 100 milliseconds    
    def on_button_click(self, event):
        print("Button clicked!")                 
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
        sizer_1.Add(self.textctrl, 1, wx.EXPAND|wx.ALL, 0)
        self.main_panel.SetSizer(sizer_1)
        self.main_panel.Layout()

    def add_env_buttons(self, output):
        # Get the output from `conda env list`
        
        # Parse the output to get the environment names
        lines = output.split('\n')[2:]  # Skip the first two lines
        envs = [line.split()[0] for line in lines if line and line.split() and len(line.split())>1]
        pp([line for line in lines if line and line.split()])
        if 1:
            button_panel = wx.ScrolledWindow(self, -1)
            button_panel.SetScrollRate(10, 10)
            button_panel.SetWindowStyle(wx.STAY_ON_TOP)
            button_panel.SetBackgroundColour('white')
            frame_height = self.GetSize().height
            panel_height = button_panel.GetSize().height

            y = (frame_height - panel_height) // 2

            button_panel.SetPosition((500, y-300+60))

            button_panel.SetSize((200, 300))            

            sizer_1 = wx.BoxSizer(wx.VERTICAL)
        for i, env in enumerate(envs):
            print(777, env)

            button = wx.Button(button_panel, -1, f'Activate "{env}"', pos=(400,30*i), size=(-1,22))
            button.Bind(wx.EVT_BUTTON, lambda event, env=env: self.on_activate(event, env))
            button.SetBackgroundColour(wx.Colour(200, 200, 200))
            sizer_1.Add(button, 0, 0, 1)
            button.Refresh()
            button.Update()            
            wx.CallLater(1, self.simulate_hover, button)
        button_panel.SetSizer(sizer_1)
        button_panel.Layout()             
        button_panel.Raise()
        button_panel.FitInside()
        #button_panel.Show()

    
    

    def on_activate(self, event, env):
        print(f'Activating environment: {env}')
        command = 'start cmd /k "C:\\tmp\\M\\miniconda3\\condabin\\conda.bat deactivate && C:\\tmp\\M\\miniconda3\\condabin\\conda.bat activate ' + env + '"'
        #remove existing conda env variables from shell initialization
        new_env = {k: v for k, v in os.environ.items() if not k.startswith('CONDA') and not k.startswith('VIRTUAL') and not k.startswith('PROMPT')}
        subprocess.Popen(command, shell=True, env=new_env)

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
        
        if command.strip() == 'conda env list':
            print(777, command.strip())
            self.add_env_buttons(retvalue.decode())

if __name__ == "__main__":
    app = wx.App(0)
    wx.InitAllImageHandlers()
    frame_1 = MyFrame(None, -1, "")
    app.SetTopWindow(frame_1)
    frame_1.Show()
    app.MainLoop()