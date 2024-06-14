import wx
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc

class dict2(dict):                                                              
    def __setitem__(self, key, value):
        super(dict2, self).__setitem__(key, value)
        #print(f"Set {key} to {value}")
    def __init__(self, *args, **kwargs):                                               
        super(dict2, self).__init__(*args,  **kwargs)                                     

    def __setattr__(self, key, value):                                          
        self[key] = value                                                       

    def __dir__(self):                                                          
        return self.keys()                                                      

    def __getattr__(self, key):                                                 
        try:                                                                    
            return self[key]                                                    
        except KeyError:                                                        
            raise AttributeError(key)                                           

    def __setstate__(self, state):                                              
        pass 

def d2d2(d):
    out=dict2()
    for k, v in d.items():
        if type(v) in [dict]:
            out[k]= d2d2(v)
        else:
            out[k]=v
    return out

class AttrDict(object):
    def __init__(self, adict):
        self.__dict__.update(adict)

def log(message, color=None):
    pub.sendMessage('log', message=message, color=color)
def set_status(message):
    pub.sendMessage('set_status', message=message)
def format_stacktrace():
    parts = ["Traceback (most recent call last):\n"]
    parts.extend(traceback.format_stack(limit=25))
    parts.extend(traceback.format_exception(*sys.exc_info())[1:])
    return "".join(parts)

class NewChat(object):
    def __init__(self):
        if 1:
            accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('N'), wx.ID_NEW)])

            # Set the accelerator table for chatInput
            self.SetAcceleratorTable(accel_tbl)

            # Bind the event to the handler
            self.Bind(wx.EVT_MENU, self.OnNewChat, id=wx.ID_NEW)
        #pub.subscribe(self.OnDefaultChat, 'adddefault_chat')
    def OnNewChat(self, event):
        dialog = NewChatDialog(self, title="New Chat")
        if dialog.ShowModal() == wx.ID_OK:
            vendor=dialog.vendor.GetStringSelection()
            chat_type_str = dialog.chat_type.GetStringSelection()
            chat_type =chat_type_str
            name = dialog.name.GetValue()
            system = dialog.system.GetValue()
            chatName = name
            chat=AttrDict(dict(vendor=vendor, chat_type=chat_type, name=name, system=system))
            #pp(chat.__dict__)
            
            print(fmt([[f"New chat: {name}"]], ['New Chat']))
            pub.sendMessage('log', message=f'New chat name: {name}')
            pub.sendMessage('add_chat', chat=chat)
        dialog.Destroy()        
class GetClassName:
    def __init__(self):
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClick)
    def OnRightClick(self, event):
        # Create a popup menu
        menu = wx.Menu()
        
        # Add a menu item to the popup menu
        current_class_name=self.__class__.__name__
        item = menu.Append(wx.ID_ANY, current_class_name)

        pname=self.GetParent().__class__.__name__
        parent_item = menu.Append(wx.ID_ANY, pname)
        
        # Bind the menu item to an event handler
        self.Bind(wx.EVT_MENU, lambda event, name=current_class_name: self.OnCopyName(event, name), item)
        self.Bind(wx.EVT_MENU, lambda event, name=pname: self.OnCopyName(event, name), parent_item)

        
        # Show the popup menu
        self.PopupMenu(menu)
        
        # Destroy the menu after it's used
        menu.Destroy()

    def OnCopyName(self, event, name):
        # Create a data object for the clipboard
        data_object = wx.TextDataObject()

        # Set the class name into the data object
        
        data_object.SetText(name)

        # Copy the text to the clipboard
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(data_object)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox('Unable to open the clipboard', 'Error', wx.OK | wx.ICON_ERROR)

class Scroll_Handlet:
    def __init__(self):
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)

        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scrolled=False
        self.previous_scroll_pos=self.GetScrollPos(wx.VERTICAL)        
        #self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        pub.subscribe(self.OnScroll, 'scroll_output')
    def OnScroll(self, message):
        self.scrolled=True
    def on_scroll(self, event):
        current_scroll_pos = self.GetScrollPos(wx.VERTICAL)

        # If the current scroll position is greater than the previous scroll position,
        # you've scrolled down
        if current_scroll_pos > self.previous_scroll_pos:
            self.scrolled = True
        # If the current scroll position is less than the previous scroll position,
        # you've scrolled up
        elif current_scroll_pos < self.previous_scroll_pos:
            self.scrolled = False

        # Update the previous scroll position
        self.previous_scroll_pos = current_scroll_pos
        event.Skip()

    def on_key_down(self, event):
        if event.GetKeyCode() in [ wx.WXK_PAGEDOWN]:
            self.scrolled = True
        if event.GetKeyCode() in [wx.WXK_PAGEUP]:
            self.scrolled = False    
        if event.ControlDown() and event.GetKeyCode() == ord('P'):
            if self.pause_output:
                self.resume_answer(self.pause_button)
            else:
                self.pause_output = True
                #print('Paused')    
                self.statusbar.SetStatusText('Paused')            
        event.Skip()    
class PauseHandlet:
    def __init__(self,tab_id):
        self.tab_id=tab_id

        #print('-------------setting PauseHandlet', self.tab_id)
        apc.pause_output[self.tab_id]=[False]
        apc.stop_output[self.tab_id]=[False]
        pub.subscribe(self.SetPause, 'pause_output')
        pub.subscribe(self.SetStop, 'stop_output')
    def pause_output(self,on_off=None):
        if on_off is not None:
            apc.pause_output[self.tab_id][0]=on_off
        else:
            return apc.pause_output[self.tab_id][0]

    def stop_output(self,on_off=None):
        if on_off is not None:
            apc.stop_output[self.tab_id][0]=on_off
            if on_off:
                self.stop_button.Disable()
            else:
                self.stop_button.Enable()
                self.pause_button.Enable()
        else:
            return apc.stop_output[self.tab_id][0]
    
    def on_pause(self, event):
        print('\nPause\n')
        if not self.stop_output():
            self.pause_output(not self.pause_output())

            if  self.pause_output():
                #self.statusBar.SetStatusText('Paused')
                pub.sendMessage('set_status', message='Paused')
                event.GetEventObject().SetLabel('Resume')
            else:
                #self.statusBar.SetStatusText('Resumed')
                pub.sendMessage('set_status', message='Resumed')
                event.GetEventObject().SetLabel('Pause')
                #self.resume_answer(event.GetEventObject())  
    def on_stop(self, event):
        print('\nStop\n')
        #self.stop_output(not self.stop_output())
        self.stop_output(True)
        if  1: #self.stop_output():
            #self.statusBar.SetStatusText('Stopped')
            pub.sendMessage('set_status', message='Stopped')
            #event.GetEventObject().SetLabel('Start')
            self.pause_button.Disable()
            self.stop_button.Disable()
        if 0:
            #self.statusBar.SetStatusText('Started')

            pub.sendMessage('set_status', message='Started')
            event.GetEventObject().SetLabel('Stop')
            self.pause_button.Enable()
            self.pause_button.SetLabel('Pause')
    def SetPause(self, message):
        self.pause_output = message
    def SetStop(self, message):
        self.stop_output = message

class PausePanel(wx.Panel,PauseHandlet):
    def __init__(self, parent, tab_id):
        super(PausePanel, self).__init__(parent)
        PauseHandlet.__init__(self, tab_id)
        self.pause_button = wx.Button(self, label="Pause", size=(40, -1))
        self.stop_button = wx.Button(self, label="Stop", size=(40, -1))
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.pause_button, 0, wx.ALL)
        sizer.Add(self.stop_button, 0, wx.ALL)
        self.SetSizer(sizer)
        self.stop_button.Disable()
        self.pause_button.Disable()
        
        
class Base_InputPanel:
    def Base_OnAskQuestion(self):
        self.pause_panel.pause_output(False)
        self.pause_panel.stop_output(False)   
    def evaluate(self,ss, params):
        #a = f"{ss}"
        a=eval('f"""'+ss+'"""')
        return a 