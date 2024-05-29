import wx
import tempfile
import subprocess
import wx.stc as stc
import wx.lib.agw.aui as aui
from pubsub import pub
from pprint import pprint as pp
import include.config.init_config as init_config 

init_config.init(**{})
apc = init_config.apc

import openai
import os
from dotenv import load_dotenv
load_dotenv()


fn=__file__
class CodeException(object):
    def __init__(self, message):
        super(CodeException, self).__init__()
        self.message = message
    def GetFixPrompt(self):
        return f'''Code to fix: {self.message}      '''


SYSTEM = """You are a chatbot that assists with adding new features 
and debugging scripts written using wxPython. Return only the code required for change. 
Present changes in form:
#Change From:
[OLD CODE LINES]
#Change To:
[NEW CODE LINES]
And line number or lines range if possible.
."""

openai.api_key = os.getenv("OPENAI_API_KEY")
class ResponseStreamer:
    def __init__(self):
        # Set your OpenAI API key here
        

        # Initialize the client
        self.client = openai.OpenAI()

    def stream_response(self, prompt):
        # Create a chat completion request with streaming enabled
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )

        # Print each response chunk as it arrives
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                #print(content, end='', flush=True)
                #pp(content)
                if content:
                    
                    pub.sendMessage('chat_output', message=f'{content}')



class _GetClassName:
    def __init__(self):
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClick)
    def OnRightClick(self, event):
        # Create a popup menu
        menu = wx.Menu()
        
        # Add a root menu item with a submenu
        pname=self.GetParent().__class__.__name__
        root_item = wx.MenuItem(menu, wx.ID_ANY, pname)
        submenu = wx.Menu()
        current_class_name = self.__class__.__name__
        submenu_item = submenu.Append(wx.ID_ANY, current_class_name)
        #menu.Append(root_item)
        menu.AppendSubMenu(submenu, pname)
        
        # Add a menu item to the popup menu
        
        #test_item = menu.Append(wx.ID_ANY, current_class_name)
        
        # Bind the menu item to an event handler
        self.Bind(wx.EVT_MENU, self.OnCopyName, submenu_item)
        
        # Show the popup menu
        self.PopupMenu(menu)
        
        # Destroy the menu after it's used
        menu.Destroy()


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


class StyledTextDisplay(stc.StyledTextCtrl, GetClassName):
    def __init__(self, parent):
        super(StyledTextDisplay, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP)
        GetClassName.__init__(self)
        #self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.SetLexer(stc.STC_LEX_PYTHON)
        python_keywords = 'self and as assert break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield'

        self.SetKeyWords(0, python_keywords)
        # Set Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, 'fore:#000000')
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, 'fore:#008000')
        self.StyleSetSpec(stc.STC_P_NUMBER, 'fore:#008080')
        self.StyleSetSpec(stc.STC_P_STRING, 'fore:#008000')
        self.StyleSetSpec(stc.STC_P_CHARACTER, 'fore:#008000')
        self.StyleSetSpec(stc.STC_P_WORD, 'fore:#000080,bold')
        self.StyleSetSpec(stc.STC_P_TRIPLE, 'fore:#008000')
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, 'fore:#008000')
        self.StyleSetSpec(stc.STC_P_CLASSNAME, 'fore:#0000FF,,weight:bold')
        self.StyleSetSpec(stc.STC_P_DEFNAME, 'fore:#008080,,weight:bold')
        self.StyleSetSpec(stc.STC_P_OPERATOR, 'fore:#000000')
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#0000FF')  # Change color for variable names to blue
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, 'fore:#008000')
        self.StyleSetSpec(stc.STC_P_STRINGEOL, 'fore:#008000,back:#E0C0E0,eol')
        self.StyleSetSpec(stc.STC_P_DECORATOR, 'fore:#805000')
        self.StyleSetSpec(stc.STC_P_WORD2, 'fore:#800080,bold')
        # Set Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")  # Default
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#008000,back:#FFFFFF")  # Comment
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")  # Number
        self.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")  # String
        self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")  # Character
        self.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")  # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")  # Triple double quotes
        self.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#00008B,back:#FFFFFF")  # Class name
        self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#00008B,back:#FFFFFF")  # Function or method name
        self.StyleSetSpec(stc.STC_P_OPERATOR, "fore:#000000,back:#FFFFFF")  # Operators
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,back:#FFFFFF")  # Identifiers

        # Set face
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')
        pub.subscribe(self.AddOutput, 'chat_output')

    def _OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            self.AskQuestion()
        else:
            event.Skip()

    def AskQuestion(self):
        pass  # Implement if needed

    def AddOutput(self, message):
        if 1: 
            self.AppendText(message)

        


class CopilotDisplayPanel(wx.Panel):
    def __init__(self, parent):
        super(CopilotDisplayPanel, self).__init__(parent)

        #self.chatDisplay = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.chatDisplay = StyledTextDisplay(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.chatDisplay, 1, wx.EXPAND)
        self.SetSizer(sizer) 

class LogTextControl(wx.TextCtrl, GetClassName):
    def __init__(self, parent, **kwargs):
        super(LogTextControl, self).__init__(parent, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
        GetClassName.__init__(self) 
        self.default_font = self.GetFont()

    def AppendFormattedText(self, message, color):
        start_pos = self.GetLastPosition()
        self.AppendText(message + '\n')
        end_pos = self.GetLastPosition()
        self.SetStyle(start_pos, end_pos, wx.TextAttr(color))



class LogPanel(wx.Panel):
    def __init__(self, parent):
        super(LogPanel, self).__init__(parent)
        self.logCtrl = LogTextControl(self)
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

class MyTextInputCtrl(wx.TextCtrl, GetClassName):
    def __init__(self, parent):
        super(MyTextInputCtrl, self).__init__(parent, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        GetClassName.__init__(self)


class MyChatInput(wx.Panel):
    def __init__(self, parent):
        super(MyChatInput, self).__init__(parent)

        self.askLabel = wx.StaticText(self, label='Ask chatgpt:')
        self.askButton = wx.Button(self, label='Ask')
        self.askButton.Bind(wx.EVT_BUTTON, self.onAskButton)
        if 1:
            self.fixButton = wx.Button(self, label='Fix')
            self.fixButton.Bind(wx.EVT_BUTTON, self.onFixButton)
            self.fixButton.Disable()


        askSizer = wx.BoxSizer(wx.HORIZONTAL)
        askSizer.Add(self.askLabel, 0, wx.ALIGN_CENTER)
        askSizer.Add((1,1), 1, wx.ALIGN_CENTER|wx.ALL)
        askSizer.Add(self.fixButton, 0, wx.ALIGN_CENTER)
        askSizer.Add(self.askButton, 0, wx.ALIGN_CENTER)

        self.inputCtrl = MyTextInputCtrl(self)
        #self.inputCtrl.SetValue("Hey, how do i add menubar ?")
        self.inputCtrl.SetMinSize((-1, 120))  
        self.inputCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(askSizer, 0, wx.EXPAND)
        sizer.Add(self.inputCtrl, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.ex=None
        pub.subscribe(self.SetException, 'fix_exception')
    def SetException(self, message):
        self.ex=message
    def onAskButton(self, event):
        # Code to execute when the Ask button is clicked
        print('Ask button clicked')
        self.ask_question()
    def ask_question(self):
        code=apc.editor.GetValue()
        if not code.strip():
            self.log('The code is empty!', color=wx.RED)
            return        
        input = self.inputCtrl.GetValue()
        if not input.strip():
            self.log('The question is empty!', color=wx.RED)
            return        
        prompt=f'''
Code to fix: {code}
Question: "{input}"
Answer:
'''        
        pp(prompt)
        if 1:
            rs=ResponseStreamer()

            rs.stream_response(prompt) 
    def onFixButton(self, event):
        if not self.ex:
            wx.MessageBox('No exception to fix', 'Error', wx.OK | wx.ICON_ERROR)
        else:
            # Code to execute when the Ask button is clicked
            print('Fix button clicked')
            rs=ResponseStreamer()
            prompt = self.ex.GetFixPrompt()
            rs.stream_response(prompt) 

    def OnCharHook(self, event):
        if event.ControlDown() and event.GetKeyCode() == wx.WXK_RETURN:
            print('Executing Ctrl+Enter...')
            self.ask_question()
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



class MyCopilotChatPanel(wx.Panel):
    def __init__(self, parent):
        super(MyCopilotChatPanel, self).__init__(parent)
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.chatDisplay = CopilotDisplayPanel (self.splitter)


        #self.askButton.Disable() 
        self.chatInput = MyChatInput(self.splitter)

        
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Add CopilotDisplayPanel and MyChatInput to the splitter window
        self.splitter.SplitHorizontally(self.chatDisplay, self.chatInput)
        self.splitter.SetSashPosition(300)  # Set initial sash position as per your need

        sizer.Add(self.splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)


class MyNotebookCodePanel(wx.Panel):
    def __init__(self, parent):
        super(MyNotebookCodePanel, self).__init__(parent)
        
        notebook = aui.AuiNotebook(self)
        
        self.notebook = notebook
        
        self.codeCtrl = stc.StyledTextCtrl(notebook)
        self.codeCtrl.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        self.codeCtrl.SetMarginWidth(0, self.codeCtrl.TextWidth(stc.STC_STYLE_LINENUMBER, '9999'))
        self.codeCtrl.StyleSetForeground(stc.STC_STYLE_LINENUMBER, wx.Colour(75, 75, 75))
                
        self.codeCtrl.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.codeCtrl.SetLexer(stc.STC_LEX_PYTHON)
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
        self.codeCtrl.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#0000FF')
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTBLOCK, 'fore:#008000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRINGEOL, 'fore:#008000,back:#E0C0E0,eol')
        self.codeCtrl.StyleSetSpec(stc.STC_P_DECORATOR, 'fore:#805000')
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD2, 'fore:#800080,bold')
        # Set Python styles
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#008000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_NUMBER, "fore:#FF8C00,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_STRING, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_WORD, "fore:#0000FF,back:#FFFFFF,weight:bold")
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#FF0000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#00008B,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#00008B,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_OPERATOR, "fore:#000000,back:#FFFFFF")
        self.codeCtrl.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,back:#FFFFFF")
        
        self.codeCtrl.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'face:Courier New')
        apc.editor = self.codeCtrl
        
        self.load_file(fn)
        notebook.AddPage(self.codeCtrl, fn)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.Layout()
        pub.subscribe(self.ExecuteFile, 'execute')
        pub.subscribe(self.OnSaveFile, 'save_file')

    def OnSaveFile(self):
        print('Saving file...')
        with open(fn, 'w') as file:
            data = self.codeCtrl.GetValue().replace('\r\n', '\n')
            file.write(data)

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('A') or event.GetKeyCode() == wx.WXK_RETURN):
            print('Executing Ctrl+A...')
        else:
            event.Skip()

    def load_file(self, file_path):
        with open(file_path, 'r') as file:
            data = file.read()
        data = data.replace('\r\n', '\n')
        self.codeCtrl.SetValue(data)

    def OnCharHook(self, event):
        if event.ControlDown() and (event.GetKeyCode() == ord('E') or event.GetKeyCode() == wx.WXK_RETURN):
            self.log('Executing...')
            self.ExecuteFile()
            self.log('Done.')
        else:
            event.Skip()

    def log(self, message):
        pub.sendMessage('log', message=f'{self.__class__.__name__}: {message}')

    def output(self, message):
        pub.sendMessage('output', message=f'{message}')

    def exception(self, message):
        pub.sendMessage('exception', message=f'{message}')

    def ExecuteFile(self):
        code = self.codeCtrl.GetText()
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(code.encode())
            temp_file_name = f.name
        process = subprocess.Popen(['python', temp_file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.output(stdout.decode())
            self.exception(stderr.decode())
            ex = CodeException(stderr.decode())
            #self.fixButton.Enable()
            pub.sendMessage('fix_exception', message=ex)
        else:
            self.output(stdout.decode())

class MyCodePanel(wx.Panel):
    def __init__(self, parent):
        super(MyCodePanel, self).__init__(parent)
        
        # Create a splitter window
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        #splitter = wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)


        # Initialize the notebook_panel and logPanel
        notebook_panel = MyNotebookCodePanel(self.splitter)
        notebook_panel.SetMinSize((-1, 50))
        #notebook_panel.SetMinSize((800, -1))
        self.logPanel = LogPanel(self.splitter)
        self.logPanel.SetMinSize((-1, 50))

        # Add notebook panel and log panel to the splitter window
        #self.splitter.AppendWindow(notebook_panel)
        #self.splitter.AppendWindow(self.logPanel)
        self.splitter.SplitHorizontally(notebook_panel, self.logPanel) 
        print(111, self.GetSize().GetHeight() // 2)
        self.splitter.SetSashPosition(500)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

        # Set initial sash positions
        #
        



import wx.lib.splitter as splitter 

# Add new class MySplitterPanel to organize copilot and code panels
class MySplitterPanel(wx.Panel):
    def __init__(self, parent):
        super(MySplitterPanel, self).__init__(parent)

        self.splitter = splitter.MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        self.mychat = MyCopilotChatPanel(self.splitter)
      
        #self.mychat.SetMinSize((300, -1))
        self.panel = MyCodePanel(self.splitter)
        self.mychat.SetMinSize((-1, 50))
        self.panel.SetMinSize((-1, 50))  
        self.splitter.AppendWindow(self.mychat)
        self.splitter.AppendWindow(self.panel)

        #print(self.GetSize().GetWidth() // 2)
        self.splitter.SetSashPosition(0, self.GetParent().GetSize().GetWidth() // 2)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.splitter, 1, wx.EXPAND|wx.ALL)
        self.SetSizer(sizer)  # Add this line to set the sizer for MySplitterPanel class



class MyFrame(wx.Frame):
    def __init__(self, title):
        super(MyFrame, self).__init__(None, title=title, size=(800, 800))

        self.splitterPanel = MySplitterPanel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.splitterPanel, 1, wx.EXPAND|wx.ALL)  
        
        self.SetSizer(sizer)


        self.AddMenuBar()
        self.Centre()

        self.Show()
    def AddMenuBar(self):
        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        saveItem = wx.MenuItem(fileMenu, wx.ID_SAVE, "&Save\tCtrl+S")
        fileMenu.Append(saveItem)
        self.Bind(wx.EVT_MENU, self.onSave, saveItem)
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)
    def onSave(self, event):
        print('Save menu item clicked')
        pub.sendMessage('save_file')
                
class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame('Poor Man\'s Copilot')
        return True

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()