import wx
import wxasync
import asyncio
from pprint import pprint as pp

from pubsub import pub

import textwrap

import wx.grid as gridlib


import openai
import os, re, time
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key here
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("API key is not loaded!")
else:
    print("API key loaded successfully.")
openai.api_key = api_key

class MainFrame(wx.Frame):
    def __init__(self, size=(1000, 600)):
        super().__init__(None, title="OpenAI Question Asker", size=size)

        # Creating the main panel and sizer
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)  # Main sizer for the panel

        # Setup for question input
        question_label = wx.StaticText(panel, label="Question:")
        self.question_input = wx.TextCtrl(panel, value='Hey, what are new features of Apache Spark?', style=wx.TE_PROCESS_ENTER|wx.TE_MULTILINE)
        self.question_input.SetMaxSize(wx.Size(-1, 200))
        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.question_input.SetFont(font)

        input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer.Add(question_label, 0, wx.ALL | wx.CENTER, 5)
        input_sizer.Add(self.question_input, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 5)  # Add to main sizer with expand flag
        
        
        self.stop_output = False
        self.response_stream = None
        self.client=None
        copy_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_copy, id=copy_id)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('Q'), copy_id)])
        pause_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_pause, id=pause_id)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('P'), pause_id)])

        self.SetAcceleratorTable(accel_tbl)
        # Setup for output grid
        self.setup_output_grid(panel)
        main_sizer.Add(self.answer_output, 1, wx.EXPAND | wx.ALL, 5)  # Ensure grid expands
        #self.answer_output.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self.on_cell_click)
        # Setup for buttons
        self.setup_buttons(panel, main_sizer)

        panel.SetSizer(main_sizer)  # Set the main sizer to the panel
        #self.Bind(wx.EVT_SIZE, self.on_resize)
        self.Centre()  # Center the frame on screen
        self.Show()
        self.Bind(wx.EVT_SIZE, self.on_resize)
        self.question_input.SetInsertionPoint(0)
        self.question_input.SetSelection(-1, -1)
        self.question_input.SetFocus()
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText('Ready')
        self.answer_output.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
        self.question_input.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.answer_output.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.scrolled=False
        self.previous_scroll_pos=self.answer_output.GetScrollPos(wx.VERTICAL)
        #self.answer_output.GetGridWindow().Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    def on_scroll(self, event):
        current_scroll_pos = self.answer_output.GetScrollPos(wx.VERTICAL)

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
                print('Paused')    
                self.statusbar.SetStatusText('Paused')            
        event.Skip()
    def _on_key_down(self, event):
        # Check if Ctrl-Q was pressed
        if event.ControlDown() and event.GetKeyCode() == ord('Q'):
            # Get the current cell
            row, col = self.answer_output.GetGridCursorRow(), self.answer_output.GetGridCursorCol()

            # Get the highlighted text
            start, end = self.answer_output.GetCellEditor(row, col).GetControl().GetSelection()
            text = self.answer_output.GetCellValue(row, col)[start:end]

            # Set the highlighted text to question_input
            self.question_input.SetValue(text)
        else:
            # Skip the event
            event.Skip()

    def on_cell_click(self, event):
        row, col = event.GetRow(), event.GetCol()

        # Set the renderer of the cell to a GridCellAutoWrapStringRenderer
        self.answer_output.SetCellRenderer(row, col, gridlib.GridCellAutoWrapStringRenderer())

        # Force the grid to recalculate the row heights
        self.answer_output.AutoSizeRows()

        # Skip the event
        event.Skip()   

    def on_copy(self, event):
        # Check if Ctrl-Q was pressed
        if 1:
            # Get the current cell
            row, col = self.answer_output.GetGridCursorRow(), self.answer_output.GetGridCursorCol()
            #print(row, col, self.answer_output.IsCellEditControlEnabled())
            
           
        if self.answer_output.IsCellEditControlEnabled():
            # Get the highlighted text
            start, end = self.answer_output.GetCellEditor(row, col).GetControl().GetSelection()
            text = self.answer_output.GetCellValue(row, col)[start:end]
        else:
            text = self.answer_output.GetCellValue(row, col)
        
        #print(text)
        self.question_input.SetValue(text.strip())

        # Set the focus to the question input
        self.question_input.SetFocus()

        # Reset the client
        self.client = None

            
    def _on_copy(self, event):
        # Get the selected cells
        selected_cells = self.answer_output.GetSelectedCells()
        pp(selected_cells)
        top_lefts = self.answer_output.GetSelectionBlockTopLeft()
        pp(top_lefts)
        # Initialize an empty string to hold the selected text
        selected_text = ''

        # Loop through the selected cells
        for cell in selected_cells:
            # Get the row and column of the cell
            row = cell[0]
            col = cell[1]

            # Get the value of the cell and append it to the selected text
            value = self.answer_output.GetCellValue(row, col)
            selected_text += value + '\n'

        # Set the selected text to the question input
        self.question_input.SetValue(selected_text.strip())

        # Set the focus to the question input
        self.question_input.SetFocus()

        # Reset the client
        self.client = None

        # Skip the event
        event.Skip()
    def on_resize(self, event):
        # Resize the last column to take up the remaining space
        self.answer_output.AutoSizeColumn(self.answer_output.GetNumberCols() - 1)
        self.answer_output.SetColSize(self.answer_output.GetNumberCols() - 1, 
                                    self.answer_output.GetSize().width - 
                                    sum([self.answer_output.GetColSize(i) for i in range(self.answer_output.GetNumberCols() - 1)]))

        # Skip the event
        event.Skip()       
    async def get_chat_completion_client(self, prompt):
        if not self.client:
            self.client = openai.ChatCompletion.create(
                model=self.model_selector.GetValue(),
                messages=[
                    {"role": "system", "content": "You are a chatbot that assists with Apache Spark queries."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
        return self.client        
    def add_row(self, text, is_bold=False):
        #print(123, text)
        #print('Adding row')
        self.start_time = time.time()
        i = self.answer_output.GetNumberRows()
        if i:
            self.answer_output.AutoSizeRows()
            #self.answer_output.AutoSizeColumns()
        elapsed_time = round(time.time() - self.start_time, 2)
        
        self.answer_output.AppendRows(1)
        print('Adding row', i, text)
        self.answer_output.SetCellValue(i, 0, str(round(time.time() - self.g_start_time, 2)))
        self.answer_output.SetCellValue(i, 1, str(elapsed_time))  # Convert elapsed_time to string
        self.answer_output.SetCellValue(i, 2, self.model_selector.GetValue())
        self.answer_output.SetCellValue(i, 3, text)
        #self.answer_output.AutoSizeColumns()  # Automatically adjust the width of columns to fit content
        self.answer_output.AutoSizeRows() 
        #print(1111)
        #pp( text)
        #if text.strip():
        #print('Resetting time -------------------')
        #pp(text)
        #self.start_time = time.time()
        if 1:
            if is_bold:

                font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            else:
                font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            # Create a cell attribute with the bold font
            attr = wx.grid.GridCellAttr()
            attr.SetFont(font)
            #last_index = self.answer_output.GetNumberRows() - 1
            # Set the row attribute
            self.answer_output.SetRowAttr(i, attr)
        #self.answer_output.MakeCellVisible(i, 0)
        if self.scrolled:
            self.answer_output.MakeCellVisible(i, 0)

        #print(i,last_visible_row)
    def append_text(self, text):
        if '\n' in text:
            text = re.sub('\n+', '\n', text)
            lines = text.split('\n')
            #pp(lines)
            self.append_to_row(lines[0])
            #self.add_row('')
            if 1:
                for line in lines[1:]:
                    if line:
                        self.add_row(line)
            self.add_row('')
        else:
            #row_count = self.answer_output.GetNumberRows()
            last_index = self.answer_output.GetNumberRows() - 1
            if last_index >= 0:
                self.append_to_row(text)
            else:
                self.add_row(text)
        i = self.answer_output.GetNumberRows()-1
        #print(111, i)
        self.answer_output.SetCellValue(i, 0, str(round(time.time() - self.g_start_time, 2)))
        self.answer_output.SetCellValue(i, 1, str(round(time.time() - self.start_time, 2)))  # Convert elapsed_time to string
    def append_to_row(self, text):
        # Append the text to the row
        last_index = self.answer_output.GetNumberRows() - 1
        current_text = self.answer_output.GetCellValue(last_index, 3)
        new_text = current_text + text
        #print(last_index, new_text)
        # Wrap the new text
        wrapped_text = textwrap.fill(new_text, width=75)  # Adjust the width as needed

        # Set the cell value to the wrapped text
        self.answer_output.SetCellValue(last_index, 3, wrapped_text)

    async def stream_response(self, prompt, output_ctrl, frame):
        # Create a chat completion request with streaming enabled
        #out=[]
        try:

            #self.add_row(f'\n-->Start ({self.model_selector.GetValue()}).\n')
            #pub.sendMessage("append_text", text=f'\n-->Start ({self.model_selector.GetValue()}).\n')
            for chunk in await self.get_chat_completion_client(prompt):
                if frame.stop_output or frame.pause_output:
                    break            
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    #out.append(content)
                    #output_ctrl.AppendText(content)
                    #pub.sendMessage("append_text", text=content)
                    self.append_text(content)
                    await asyncio.sleep(0)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:

            if not frame.pause_output:
                self.client = None
                #print('--> Stopped')
                #self.answer_output.AppendText('\n-->Done.\n\n\n')
                if not frame.stop_output:
                    print('\n-->Done.\n\n\n')
                    #pub.sendMessage("append_text", text='\n-->Done.\n\n\n')
                else:
                    print('\n-->Done(Stop).\n\n\n')
                    #pub.sendMessage("append_text", text='\n-->Done(Stop).\n\n\n')
                
            else:

                print('--> Paused')
            
            if 1:
                self.answer_output.AutoSizeRows()
                #self.answer_output.AutoSizeColumns()

    async def on_ask(self):
        #self.statusbar.SetStatusText('Asking...')
        
        self.stop_output = False
        self.pause_output = False 
        
        self.g_start_time= time.time()
        question = self.question_input.GetValue()
        if not self.statusbar.GetStatusText()=='Resumed':
            self.add_row(question, True)


        self.add_row('')
        self.response_stream =  await self.stream_response(question, self.answer_output, self)
        #self.answer_output.AppendText('\n'*3)
        #self.client=None
                
    def on_stop(self, event):

        self.stop_output = True 
        self.pause_output = False
        
        #pp(self.response_stream) 
        if self.response_stream :
            self.response_stream.cancel()
            self.response_stream = None
        self.client=None
        #pub.sendMessage("append_text", text='\n-->Done.\n\n\n')
        #self.statusbar.SetStatusText('Stopped')        
    def on_ask_wrapper(self, event):
        asyncio.create_task(self.on_ask())
    def setup_output_grid(self, panel):
        # Create and configure the grid for output
        self.answer_output = gridlib.Grid(panel)
        self.answer_output.CreateGrid(0, 4)  # Pre-creating some rows and columns
        col_labels = ["Elapsed", "Delta", "Model", "Text"]
        for col, label in enumerate(col_labels):
            self.answer_output.SetColLabelValue(col, label)
        #self.answer_output.SetColSize(0, 100)  # Set initial size for the 'Elapsed' column
        self.answer_output.SetColSize(3, 400)  # Set initial size for the 'Text' column
        if 0:
            font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
            attr = gridlib.GridCellAttr()
            attr.SetFont(font)
            self.answer_output.SetColAttr(3, attr)
        #self.answer_output.AutoSizeColumns()  # Optional: auto-size columns based on content
        self.answer_output.SetDefaultEditor(gridlib.GridCellAutoWrapStringEditor())
        if 0:
            i=0
            text='''I'm an artificial intelligence designed to help
you with Apache Spark queries. I do not possess
emotions but I'm here and ready to assist you. How
can I help you today?'''
            self.answer_output.AppendRows(1)
            self.answer_output.SetCellValue(i, 0, str(round(time.time() - self.g_start_time, 2)))
            self.answer_output.SetCellValue(i, 1, str(0))  # Convert elapsed_time to string
            self.answer_output.SetCellValue(i, 2, 'test')
            self.answer_output.SetCellValue(i, 3, text)
            self.answer_output.AutoSizeRows() 

            
    def setup_buttons(self, panel, sizer):
        # Create button sizer
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_names = ["gpt-3", "gpt-4", "gpt-4-turbo", "gpt-4-turbo-2024-04-09",
                       'gpt-4-turbo-preview', 'gpt-4-0125-preview', 'gpt-4-1106-preview',
                       'gpt-4-32k-0613', 'gpt-4-32k']
        self.model_selector = wx.ComboBox(panel, choices=model_names, style=wx.CB_READONLY)
        self.model_selector.SetValue("gpt-4")
        ask_button = wx.Button(panel, label="Ask Question")
        stop_button = wx.Button(panel, label="Stop")

        if 1:
            self.pause_output = False
            self.pause_button=pause_button = wx.Button(panel, label="Pause")
            
            pause_button.Bind(wx.EVT_BUTTON, self.on_pause)

        button_sizer.Add(self.model_selector, 0, wx.EXPAND | wx.ALL, 5)
        button_sizer.Add(ask_button, 1, wx.EXPAND | wx.ALL, 5)
        button_sizer.Add(pause_button, 0, wx.ALL, 5)
        button_sizer.Add(stop_button, 0, wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Bind button events
        ask_button.Bind(wx.EVT_BUTTON, self.on_ask_wrapper)
        stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self.question_input.Bind(wx.EVT_TEXT_ENTER, self.on_ask_wrapper)
    def on_pause(self, event):
        if event.GetEventObject().GetLabel() == 'Pause':
            print('Pausing')
            self.pause_output = True 
            if self.response_stream :
                self.response_stream.cancel()
                self.response_stream = None   
            if self.pause_output:
                self.statusbar.SetStatusText('Paused')
                event.GetEventObject().SetLabel('Resume')

        else:    
            print('Resuming')
            self.resume_answer(event.GetEventObject())
    def resume_answer(self, btn):
        
        self.statusbar.SetStatusText('Resumed')
        btn.SetLabel('Pause')
        print('resume_answer' , self.pause_output )
        if not self.stop_output and self.pause_output:
            self.pause_output = False
            asyncio.create_task(self.on_ask())
if __name__ == "__main__":
    app = wxasync.WxAsyncApp()
    frame = MainFrame()
    frame.SetSize(1000, 600)
    frame.Show()
    asyncio.get_event_loop().run_until_complete(app.MainLoop())
