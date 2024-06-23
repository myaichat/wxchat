import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc
import wx.html
from include.Common import Base_InputPanel, HtmlDialog
class Base_InputPanel_Phi3(Base_InputPanel):
    def AddButtons(self, v_sizer):
        if 1: #second row



            h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 
            self.do_sample_dropdown = wx.ComboBox(self, choices=['True', 'False'], style=wx.CB_READONLY)
            self.do_sample_dropdown.SetValue('False')  # Default value
            self.do_sample_dropdown.Bind(wx.EVT_COMBOBOX, self.OnDoSampleChange)
            chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
        
            self.max_length_dropdown = wx.ComboBox(self, choices=['512', '768','1024','1536', '2048', '4096', str(1024* 10), str(1024* 20), str(1024* 40)], style=wx.CB_READONLY)
            self.max_length_dropdown.SetValue('2048')  # Default value
            self.max_length_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxLengthChange)
            chat.max_length = int(self.max_length_dropdown.GetValue())

            self.min_length_dropdown = wx.ComboBox(self, choices=['1', '512', '1024', '2048', '4096'], style=wx.CB_READONLY)
            self.min_length_dropdown.SetValue('1')  # Default value
            self.min_length_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMinLengthChange)
            chat.min_length = int(self.min_length_dropdown.GetValue()  )

            self.top_p_dropdown = wx.ComboBox(self, choices=['0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9',  '1.0',  '1.1',], style=wx.CB_READONLY)
            self.top_p_dropdown.SetValue('0.9')  # Default value
            self.top_p_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopPChange)
            chat.top_p = float(self.top_p_dropdown.GetValue()  )
            #top_k
            self.top_k_dropdown = wx.ComboBox(self, choices=['1',  '2',  '3',  '4',  '5',  '10',  '20',  '50',  '75',  '100',  '150', '200','300',], style=wx.CB_READONLY)
            self.top_k_dropdown.SetValue('50')  # Default value
            self.top_k_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopKChange)
            chat.top_k = int(self.top_k_dropdown.GetValue()  )     

            self.temp_dropdown = wx.ComboBox(self, choices=['0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9',  '1.0', '1.2', '1.4', '1.7',  '2.0', '5.0', '10.0', '50.0'], style=wx.CB_READONLY)
            self.temp_dropdown.SetValue('1.2')  # Default value
            self.temp_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTempChange)
            chat.temperature = float(self.temp_dropdown.GetValue()  )  
            #repetition_penalty
            self.repetition_penalty_dropdown = wx.ComboBox(self, choices=['1.0',  '1.1',  '1.2',  '1.3',  '1.4',  '1.5',  '1.6',  '1.7',  '1.8',  '1.9',  '2.0',  '2.1','2.5','3.0','5.0','10.0',], style=wx.CB_READONLY)
            self.repetition_penalty_dropdown.SetValue('1.1')  # Default value
            self.repetition_penalty_dropdown.Bind(wx.EVT_COMBOBOX, self.OnRepetitionPenaltyChange)
            chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue()  )             

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="do_sample")
            dos.html_content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Increasing Artfulness with do_sample=True</title>
</head>
<body>
    <h1>Increasing Artfulness with do_sample=True</h1>
    
    <p>When <code>do_sample=true</code>, the model uses stochastic decoding methods such as sampling with temperature, top-p, or top-k sampling. Here are several strategies to increase the artfulness of the output:</p>
    
    <h2>Strategies:</h2>
    
    <h3>1. Adjust Temperature:</h3>
    <ul>
        <li><strong>Description:</strong> Increasing the temperature value increases the randomness of the predictions, leading to more creative and diverse outputs.</li>
        <li><strong>Example:</strong> Set <code>temperature=1.2</code> for more creativity.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "temperature": 1.2
}
    </pre>

    <h3>2. Adjust Top-p (Nucleus Sampling):</h3>
    <ul>
        <li><strong>Description:</strong> Top-p sampling considers the smallest set of tokens whose cumulative probability exceeds the threshold p. Lowering top-p can make the output more focused, while increasing it can make it more diverse.</li>
        <li><strong>Example:</strong> Set <code>top_p=0.9</code> to balance creativity and coherence.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "top_p": 0.9
}
    </pre>

    <h3>3. Adjust Top-k:</h3>
    <ul>
        <li><strong>Description:</strong> Top-k sampling considers only the top k tokens. Increasing the value of k allows the model to consider a broader range of tokens, increasing diversity.</li>
        <li><strong>Example:</strong> Set <code>top_k=100</code> for more diverse outputs.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "top_k": 100
}
    </pre>

    <h3>4. Combine Strategies:</h3>
    <ul>
        <li><strong>Description:</strong> Combining temperature, top-p, and top-k adjustments can amplify their effects, leading to even more artful and creative outputs.</li>
        <li><strong>Example:</strong> Use a combination of these parameters for maximum creativity.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "temperature": 1.2,
  "top_p": 0.9,
  "top_k": 100
}
    </pre>

    <h3>5. Apply Repetition Penalty:</h3>
    <ul>
        <li><strong>Description:</strong> Using a repetition penalty discourages the model from repeating the same phrases or words, promoting more varied and interesting outputs.</li>
        <li><strong>Example:</strong> Set <code>repetition_penalty=1.2</code>.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "repetition_penalty": 1.2
}
    </pre>

    <h3>6. Adjust Length Penalty:</h3>
    <ul>
        <li><strong>Description:</strong> Tuning the length penalty can influence the length of the output, which can indirectly affect its creativity. A lower length penalty encourages longer outputs, while a higher penalty favors shorter ones.</li>
        <li><strong>Example:</strong> Set <code>length_penalty=0.8</code> for longer, potentially more creative outputs.
        </li>
    </ul>
    <pre>
{
  "do_sample": true,
  "length_penalty": 0.8
}
    </pre>

    <h2>Example Configuration Combining Multiple Strategies:</h2>
    <pre>
{
  "do_sample": true,
  "temperature": 1.2,
  "top_p": 0.9,
  "top_k": 100,
  "repetition_penalty": 1.2,
  "length_penalty": 0.8
}
    </pre>
    
</body>
</html>

"""        
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.do_sample_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="max_len")
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.max_length_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)


            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="min_len")
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.min_length_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)
                   
            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="top_k")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top-k Ranges Explained</title>
</head>
<body>
    <h1>Top-k Ranges Explained</h1>
    
    <h2>Top-k Range Effects:</h2>
    
    <h3>Low Top-k (1 to 50):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers only a small number of the most likely tokens.</li>
        <li><strong>Output:</strong> The text will be more coherent and focused, with less randomness and creativity.</li>
        <li><strong>Use Case:</strong> Ideal for generating concise, coherent text where maintaining context is crucial.</li>
    </ul>
    
    <h3>Moderate Top-k (51 to 100):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a wider range of tokens, increasing diversity while maintaining coherence.</li>
        <li><strong>Output:</strong> The text is generally well-structured with a moderate amount of creativity and variation.</li>
        <li><strong>Use Case:</strong> Suitable for most applications where a balance between creativity and coherence is desired.</li>
    </ul>
    
    <h3>High Top-k (101 to 200):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model has a larger pool of tokens to choose from, enhancing creativity and diversity.</li>
        <li><strong>Output:</strong> The text becomes more varied and creative, with an increased likelihood of unexpected or novel phrases.</li>
        <li><strong>Use Case:</strong> Good for creative writing, brainstorming, and when you want more innovative or out-of-the-box content.</li>
    </ul>
    
    <h3>Very High Top-k (201 and above):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a very large number of tokens, greatly increasing the diversity of the output.</li>
        <li><strong>Output:</strong> The text can become very varied and potentially less coherent, with a higher chance of novel and surprising elements.</li>
        <li><strong>Use Case:</strong> Best for generating highly creative, experimental, or whimsical content where innovation is prioritized over coherence.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Top-k:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.8,
  "top_p": 0.9,
  "top_k": 20
}
    </pre>
    <p><strong>Output:</strong> Highly coherent and focused text.</p>
    
    <h3>Moderate Top-k:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 75
}
    </pre>
    <p><strong>Output:</strong> Balanced text with coherence and creativity.</p>
    
    <h3>High Top-k:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.0,
  "top_p": 0.9,
  "top_k": 150
}
    </pre>
    <p><strong>Output:</strong> More creative and diverse text with a good balance of coherence.</p>
    
    <h3>Very High Top-k (Maximum Diversity):</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.2,
  "top_p": 0.9,
  "top_k": 300
}
    </pre>
    <p><strong>Output:</strong> Highly creative and varied text, with a higher chance of unexpected or novel content.</p>
    
</body>
</html>
"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))            
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.top_k_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)


            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="top_p")
            
            # Assuming "some_text" is the text you want to pass as a parameter
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top-p Ranges Explained</title>
</head>
<body>
    <h1>Top-p Ranges Explained</h1>
    
    <h2>Top-p Range Effects:</h2>
    
    <h3>Low Top-p (0.1 to 0.3):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model focuses on a very small set of highly probable tokens.</li>
        <li><strong>Output:</strong> The text will be highly coherent and predictable, with less creativity and diversity.</li>
        <li><strong>Use Case:</strong> Suitable for generating formal, factual, or highly structured content where precision and coherence are paramount.</li>
    </ul>
    
    <h3>Moderate Top-p (0.4 to 0.7):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a broader set of probable tokens, balancing coherence and creativity.</li>
        <li><strong>Output:</strong> The text will have a good balance of coherence and creativity, with more diverse and interesting outputs than a low top-p.</li>
        <li><strong>Use Case:</strong> Suitable for general-purpose text generation where a balance between creativity and coherence is desired.</li>
    </ul>
    
    <h3>High Top-p (0.8 to 1.0):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model considers a wide range of tokens, including less probable ones.</li>
        <li><strong>Output:</strong> The text will be more creative, diverse, and potentially surprising, but with a higher risk of incoherence.</li>
        <li><strong>Use Case:</strong> Suitable for creative writing, brainstorming, and generating artistic or unconventional content.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Top-p:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.8,
  "top_p": 0.2,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly coherent, predictable text.</p>
    
    <h3>Moderate Top-p:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.9,
  "top_p": 0.5,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Balanced text with both coherence and creativity.</p>
    
    <h3>High Top-p:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.0,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Creative and diverse text with a higher chance of surprises.</p>
    
    <h3>Very High Top-p (Maximum Creativity):</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.2,
  "top_p": 1.0,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly creative and diverse, with a significant chance of incoherence.</p>
    
</body>
</html>"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))

            #dos.Bind(wx.EVT_ENTER_WINDOW, self.onHover)
            #dos.Bind(wx.EVT_LEAVE_WINDOW, self.onLeave)
    
   
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.top_p_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)




            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="temp-re")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temperature Ranges Explained</title>
</head>
<body>
    <h1>Temperature Ranges Explained</h1>
    
    <h2>Temperature Range Effects:</h2>
    
    <h3>Low Temperature (0.2 to 0.5):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model produces highly deterministic and predictable text, focusing on the most probable tokens.</li>
        <li><strong>Output:</strong> The text will be very coherent and structured, with little randomness or creativity.</li>
        <li><strong>Use Case:</strong> Ideal for tasks requiring precision and accuracy, such as technical writing, factual content, and formal documentation.</li>
    </ul>
    
    <h3>Moderate Temperature (0.6 to 0.8):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model introduces some randomness while maintaining a balance between coherence and creativity.</li>
        <li><strong>Output:</strong> The text will be well-structured with moderate creativity, suitable for general-purpose applications.</li>
        <li><strong>Use Case:</strong> Suitable for generating conversational, narrative, and informative text where a balance of creativity and coherence is needed.</li>
    </ul>
    
    <h3>High Temperature (0.9 to 1.2):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model generates more random and creative text, considering a wider range of possible tokens.</li>
        <li><strong>Output:</strong> The text will be diverse, creative, and less predictable, but with a higher risk of incoherence.</li>
        <li><strong>Use Case:</strong> Good for creative writing, brainstorming, and scenarios where innovation and originality are prioritized.</li>
    </ul>
    
    <h3>Very High Temperature (>1.2):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model produces highly random and varied text, often prioritizing creativity over coherence.</li>
        <li><strong>Output:</strong> The text will be highly diverse and potentially novel, but with a significant risk of being incoherent or nonsensical.</li>
        <li><strong>Use Case:</strong> Best for experimental and highly creative tasks where unconventional and surprising outputs are desired.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Temperature:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.4,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly coherent and structured text.</p>
    
    <h3>Moderate Temperature:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Balanced text with coherence and creativity.</p>
    
    <h3>High Temperature:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.0,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Creative and diverse text with a higher risk of surprises.</p>
    
    <h3>Very High Temperature (Maximum Creativity):</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 1.5,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly creative and varied text, with a significant risk of incoherence.</p>
    
</body>
</html>
"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.temp_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="repeti")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repetition Penalty Ranges Explained</title>
</head>
<body>
    <h1>Repetition Penalty Ranges Explained</h1>
    
    <h2>Repetition Penalty Range Effects:</h2>
    
    <h3>Low Repetition Penalty (1.0 to 1.1):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model slightly penalizes repeated phrases or words, encouraging some variation while maintaining coherence.</li>
        <li><strong>Output:</strong> The text will have minor diversity with high coherence, producing natural-sounding and fluent sentences.</li>
        <li><strong>Use Case:</strong> Suitable for general-purpose text generation where maintaining coherence is important, such as dialogue or narrative writing.</li>
    </ul>
    
    <h3>Moderate Repetition Penalty (1.2 to 1.5):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model moderately penalizes repeated phrases or words, encouraging more variation and creativity.</li>
        <li><strong>Output:</strong> The text will be more diverse and creative, with less repetition and potentially more interesting language.</li>
        <li><strong>Use Case:</strong> Suitable for creative writing, brainstorming, and content that benefits from a higher level of creativity and variation.</li>
    </ul>
    
    <h3>High Repetition Penalty (1.6 to 2.0):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model heavily penalizes repeated phrases or words, promoting maximum variation and creativity.</li>
        <li><strong>Output:</strong> The text will be highly diverse and creative, with minimal repetition, but may risk losing some coherence.</li>
        <li><strong>Use Case:</strong> Ideal for generating highly creative and experimental content where uniqueness and novelty are prioritized over coherence.</li>
    </ul>
    
    <h3>Very High Repetition Penalty (>2.0):</h3>
    <ul>
        <li><strong>Behavior:</strong> The model severely penalizes repeated phrases or words, pushing for extreme variation and novelty.</li>
        <li><strong>Output:</strong> The text will be extremely varied and creative, with very low repetition, but may become difficult to follow or understand.</li>
        <li><strong>Use Case:</strong> Best for experimental writing, artistic projects, or situations where extreme creativity and novelty are desired, even at the cost of coherence.</li>
    </ul>
    
    <h2>Example Configurations:</h2>
    
    <h3>Low Repetition Penalty:</h3>
    <pre>
{
  "repetition_penalty": 1.1,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Text with minor diversity and high coherence.</p>
    
    <h3>Moderate Repetition Penalty:</h3>
    <pre>
{
  "repetition_penalty": 1.3,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> More diverse and creative text with less repetition.</p>
    
    <h3>High Repetition Penalty:</h3>
    <pre>
{
  "repetition_penalty": 1.7,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Highly diverse and creative text with minimal repetition.</p>
    
    <h3>Very High Repetition Penalty (Maximum Creativity):</h3>
    <pre>
{
  "repetition_penalty": 2.1,
  "temperature": 0.9,
  "top_p": 0.9,
  "top_k": 50
}
    </pre>
    <p><strong>Output:</strong> Extremely varied and creative text with very low repetition.</p>
    
</body>
</html>
>"""   

            # Modify the event binding to use a lambda function
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
                        
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.repetition_penalty_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)

           
            
            v_sizer.Add(h_sizer_1, 0, wx.ALIGN_CENTER) 
    def OnClickDos(self, event):
        # Define your HTML content here. It could also be loaded from a file or a webpage.
        html_content = event.GetEventObject().html_content
        dialog = HtmlDialog(self, "HTML Content", html_content)
        dialog.ShowModal()
        dialog.Destroy()

    def onHover(self, event):
        # Fetch the webpage content. For demonstration, we're just using static HTML.
        html_content ="""<html><body><h3>top_p</h3><p>top_p is a parameter used in text generation that controls the nucleus sampling method, also known as top-p sampling. 
This sampling strategy is designed to focus the model's attention on the most probable next words or tokens, 
enhancing the quality and coherence of the generated text.
</p></body></html>"""
        # In a real application, you might fetch the content like so:
        # response = requests.get("http://example.com")
        # html_content = response.text
        self.tooltip = HtmlToolTip(None, html_content)  # Use self.tooltip to store the window
        pos = wx.GetMousePosition()
        self.tooltip.SetPosition(pos)
        self.tooltip.Show()
    def onLeave(self, event):
        # Destroy the tooltip window when the mouse leaves the widget
        if self.tooltip:
            self.tooltip.Destroy()
            self.tooltip = None  # Reset the tooltip attribute to None
    def OnDoSampleChange(self, event):
        # Get the selected do_sample value
        selected_do_sample = self.do_sample_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.do_sample = (selected_do_sample == 'True')
        print('OnDoSampleChange',selected_do_sample, self.tab_id)
        # Continue processing the event
        event.Skip()
    def OnMaxLengthChange(self, event):
        # Get the selected do_sample value
        selected_max_length = self.max_length_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.max_length = int(selected_max_length )
        print('OnMaxLengthChange',selected_max_length, self.tab_id)
        # Continue processing the event
        event.Skip()
    def OnMinLengthChange(self, event):
        # Get the selected do_sample value
        selected_min_length = self.min_length_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.min_length = int(selected_min_length )

        # Continue processing the event
        event.Skip()     
    def OnTopPChange(self, event):
        # Get the selected do_sample value
        selected_top_p = self.top_p_dropdown.GetValue()
        print('OnTopPChange',selected_top_p, self.tab_id)
        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.top_p = float(selected_top_p )

        # Continue processing the event
        pp(chat)
        print(apc.chats)
        event.Skip()        
    def OnTopKChange(self, event):
        # Get the selected do_sample value
        selected_top_k = self.top_k_dropdown.GetValue()
        print('OnTopKChange',selected_top_k, self.tab_id)
        # Print the selected model
        chat = apc.chats[self.tab_id]
        
        chat.top_k = int(selected_top_k )

        # Continue processing the event
        event.Skip()

    def OnTempChange(self, event):
        # Get the selected do_sample value
        selected_temp = self.temp_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.temperature = float(selected_temp )


        # Continue processing the event
        event.Skip()    
    def OnRepetitionPenaltyChange(self, event):
        # Get the selected do_sample value
        selected_repetition_penalty = self.repetition_penalty_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.repetition_penalty = float(selected_repetition_penalty )

        # Continue processing the event
        event.Skip()


    def RestoreQuestionForTabId(self, tab_id):
        self.tab_id=tab_id
        message=tab_id
        chat=apc.chats[message]
        pp(chat)
        print('RestoreQuestionForTabId', chat)
        if message in self.tabs:
            assert self.chat_type==message[1]
            #print('Chat restoring', message)
            #pp(self.tabs[message])
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            print(self.__class__.__name__, 'RestoreQuestionForTabId', message)
            self.model_dropdown.SetValue(apc.currentModel[message])
            #self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
            #print('Restored', message)
            
            #chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
            #chat.max_length = int(self.max_length_dropdown.GetValue() )
            
            #chat.min_length = int(self.min_length_dropdown.GetValue() )
            #chat.top_p = float(self.top_p_dropdown.GetValue() )
            #chat.top_k = float(self.top_k_dropdown.GetValue() )
            #chat.temperature = float(self.temp_dropdown.GetValue() )
            #chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue() )
            
            print(message, self.tab_id)
            #pp(self.tabs)
        
            if chat.get('max_length', None):
                self.max_length_dropdown.SetValue(str(chat.max_length)) 
            else:
                chat.max_length = int(self.max_length_dropdown.GetValue())  


            if chat.get('min_length', None):
                self.min_length_dropdown.SetValue(str(chat.min_length))
            else:
                chat.min_length = int(self.min_length_dropdown.GetValue())


            if chat.get('top_p', None):
                
                self.top_p_dropdown.SetValue(str(chat.top_p))
                
                #wx.MessageBox(f"top_p {chat.top_p} {self.top_p_dropdown.GetValue()}", "top_p"   )
            else:
                chat.top_p= float(self.top_p_dropdown.GetValue())

            
            if chat.get('top_k', None):
                self.top_k_dropdown.SetValue(str(chat.top_k))
            else:
                chat.top_k = int(self.top_k_dropdown.GetValue())


            if chat.get('temperature', None):
                self.temp_dropdown.SetValue(str(chat.temperature))
            else:
                chat.temperature = float(self.temp_dropdown.GetValue())



            if chat.get('repetition_penalty', None):
                self.repetition_penalty_dropdown.SetValue(str(chat.repetition_penalty))
            else:
                chat.repetition_penalty = float(self.repetition_penalty_dropdown.GetValue())

            if chat.get('do_sample', None) is not None:
                
                val = 'True' if chat.do_sample else 'False'
                self.do_sample_dropdown.SetValue(val)
            else:
                chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')
    

            #self.max_length_dropdown.SetValue(str(chat.get('max_length', 2048)))    