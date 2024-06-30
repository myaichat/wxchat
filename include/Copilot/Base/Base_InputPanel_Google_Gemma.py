import wx
import sys, traceback
from pubsub import pub
from include.fmt import fmt
from pprint import pprint as pp 
import include.config.init_config as init_config 
apc = init_config.apc
import wx.html
from include.Common import HtmlDialog, Base_InputPanel, ChatHistoryDialog, dict2, evaluate



class Base_InputPanel_Google_Gemma(Base_InputPanel):
    def get_chat_streamer(self, tab_id, glbs):

        chat=apc.chats[tab_id]
        pp(chat)
      
        streamer_name = f'{chat.streamer_name}_ResponseStreamer'
        if streamer_name not in self.rs:

            assert streamer_name in glbs, streamer_name
            #print(f'\t\Creating streamer:', streamer_name)
            cls= glbs[streamer_name]
            # Gpt4_Chat_DisplayPanel/ Gpt4_Copilot_DisplayPanel
            self.rs[streamer_name] = cls ()
            print(f'\t\Created streamer:', streamer_name)
        else:
            print(f'\t\Reusing streamer:', streamer_name)
        return self.rs[streamer_name]  
            
    def AddButtons_Level_1(self, h_sizer):
        if 1: #second row



            #h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 


            self.historyButton = wx.Button(self, label='Hist', size=(40, 25))
            self.historyButton.Bind(wx.EVT_BUTTON, self.onHistoryButton)
            h_sizer.Add(self.historyButton, 0, wx.ALIGN_CENTER) 
            self.sysButton = wx.Button(self, label='Sys', size=(40, 25))
            self.sysButton.Bind(wx.EVT_BUTTON, self.onSysButton)
            h_sizer.Add(self.sysButton, 0, wx.ALIGN_CENTER) 

            if 0:
                self.min_tokens_dropdown = wx.ComboBox(self, choices=['1','256', '512', '768','1024','1536', '2048'], style=wx.CB_READONLY)
                self.min_tokens_dropdown.SetValue('1')  # Default value
                self.min_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxTokensChange)
                chat.min_tokens = int(self.min_tokens_dropdown.GetValue())
                h_sizer.Add(self.min_tokens_dropdown, 0, wx.ALIGN_CENTER) 
    def onHistoryButton(self, event):
        
        dialog = ChatHistoryDialog(self, self.tab_id, apc.chatHistory)
        dialog.ShowModal()
        dialog.Destroy()

    def onSysButton(self, event):
        
        dialog = ShowSystemPrompts_Chat(self, self.tab_id, apc.chatHistory)
        dialog.ShowModal()
        dialog.Destroy() 

            #v_sizer.Add(h_sizer_1, 0, wx.ALIGN_CENTER) 






    def split_text_into_chunks(self, text, chunk_length=80):
        # Split the text into chunks of specified length
        chunks = [text[i:i+chunk_length] for i in range(0, len(text), chunk_length)]
        return chunks


    def AddButtons_Level_2(self, h_sizer_1):
        if 1: #second row


            #h_sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
            chat=apc.chats[self.tab_id] 
            self.max_tokens_dropdown = wx.ComboBox(self, choices=['100', '150','300','450', '600', '750', '1000', '2000', '2048', '4096', '8192'], style=wx.CB_READONLY)
            self.max_tokens_dropdown.SetValue('300')  # Default value
            self.max_tokens_dropdown.Bind(wx.EVT_COMBOBOX, self.OnMaxTokensChange)
            chat.max_tokens = int(self.max_tokens_dropdown.GetValue())

            self.do_sample_dropdown = wx.ComboBox(self, choices=['True', 'False'], style=wx.CB_READONLY)
            self.do_sample_dropdown.SetValue('False')  # Default value
            self.do_sample_dropdown.Bind(wx.EVT_COMBOBOX, self.OnDoSampleChange)
            chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')

            self.temp_dropdown = wx.ComboBox(self, choices=['-1.0','0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9','0.95',  '1.0', '1.2', '2', '3'], style=wx.CB_READONLY)
            self.temp_dropdown.SetValue('0.8')  # Default value
            self.temp_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTempChange)
            chat.temperature = float(self.temp_dropdown.GetValue()  )                         
            if 1:
                self.top_p_dropdown = wx.ComboBox(self, choices=['-1.0','0.0',  '0.1',  '0.2',  '0.3',  '0.4',  '0.5',  '0.6',  '0.7',  '0.8',  '0.9', '0.95',  '1.0',  '1.1',], style=wx.CB_READONLY)
                self.top_p_dropdown.SetValue('0.95')  # Default value
                self.top_p_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopPChange)
                chat.top_p = float(self.top_p_dropdown.GetValue()  )
                #top_k
                self.top_k_dropdown = wx.ComboBox(self, choices=['1',  '2',  '3',  '4',  '5',  '10',  '20',  '40',  '41'], style=wx.CB_READONLY)
                self.top_k_dropdown.SetValue('40')  # Default value
                self.top_k_dropdown.Bind(wx.EVT_COMBOBOX, self.OnTopKChange)
                chat.top_k = int(self.top_k_dropdown.GetValue()  )     

            self.use_cache_dropdown = wx.ComboBox(self, choices=['True', 'False'], style=wx.CB_READONLY)
            self.use_cache_dropdown.SetValue('True')  # Default value
            self.use_cache_dropdown.Bind(wx.EVT_COMBOBOX, self.OnUseCacheChange)
            chat.use_cache = (self.use_cache_dropdown.GetValue() == 'True')

        
            sizer_0 = wx.BoxSizer(wx.VERTICAL)
            dos = wx.StaticText(self, label="max_tokens")
            dos.html_content ="""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Max Tokens Explained</title>
            </head>
            <body>
                
            <h1>Max Tokens Definition</h1>
            <h3>Default: 1024, Range: 1–2048</h3>
                <ul>
            </li><li>Maximum number of tokens that can be generated in the response. A token is approximately four characters. 100 tokens correspond to roughly 60-80 words.
            
            <li>Specify a lower value for shorter responses and a higher value for potentially longer responses.
            </li>    

            </body>
            </html>
            """    
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))          
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.max_tokens_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)


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
            dos = wx.StaticText(self, label="temp-re")
            dos.html_content ="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temperature Ranges Explained</title>
</head>
<body>

            <h1>Temperature Definition</h1>
            <h3> Range: 0.0–1.0, Default: 0.0</h3>
                <ul>
            </li><li>The temperature is used for sampling during response generation, which occurs when topP and topK are applied. Temperature controls the degree of randomness in token selection. Lower temperatures are good for prompts that require a less open-ended or creative response, while higher temperatures can lead to more diverse or creative results. A temperature of 0 means that the highest probability tokens are always selected. In this case, responses for a given prompt are mostly deterministic, but a small amount of variation is still possible.
            
            <li>If the model returns a response that's too generic, too short, or the model gives a fallback response, try increasing the temperature.
            </li>   

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



            if 1:
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
    
<h1>Top-k Definition</h1>
<h3>Default: 40, Range:1-40</h3>
    <ul>
</li><li>Top-K changes how the model selects tokens for output. A top-K of 1 means the next selected token is the most probable among all tokens in the model's vocabulary (also called greedy decoding), while a top-K of 3 means that the next token is selected from among the three most probable tokens by using temperature.
<li>For each token selection step, the top-K tokens with the highest probabilities are sampled. Then tokens are further filtered based on top-P with the final token selected using temperature sampling.
</li>    
<li>Specify a lower value for less random responses and a higher value for more random responses.</li>
    </ul>


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

            if 1:
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

            <h1>Top-p Definition</h1>
            <h3> Range: 0.0–1.0, Default: 0.95</h3>
                <ul>
            </li><li>Top-P changes how the model selects tokens for output. Tokens are selected from the most (see top-K) to least probable until the sum of their probabilities equals the top-P value. For example, if tokens A, B, and C have a probability of 0.3, 0.2, and 0.1 and the top-P value is 0.5, then the model will select either A or B as the next token by using temperature and excludes C as a candidate.
            
            <li>Specify a lower value for less random responses and a higher value for more random responses.
            </li>   

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
            dos = wx.StaticText(self, label="use_cache")
            dos.html_content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meaning of use_cache</title>
</head>
<body>
    <h1>use_cache=True</h1>

<ul>
<li><strong>1:</strong> The <code>use_cache</code> parameter in the <code>generate()</code> method controls whether the model should use the past key/value states (cache) for faster generation.

</li><li><strong>2:</strong> When <code>use_cache</code> is set to <code>True</code>, the model will cache the key/value states generated during the decoding process. This means that at each generation step, the model doesn't need to recompute the attention scores for the previous tokens, as they are already stored in the cache. Instead, it can simply retrieve the cached states and use them for the current step, leading to faster generation.

</li><li><strong>3:</strong> On the other hand, when <code>use_cache</code> is set to <code>False</code>, the model will not store the past key/value states and will recompute the attention scores at each generation step. This can be slower, especially for longer sequences, as the model needs to process the entire input sequence at each step.

</li><li><strong>4:</strong> In general, setting <code>use_cache=True</code> can provide a significant speed-up during generation, especially for models with a large number of layers or when generating long sequences. However, it does come with a trade-off in terms of memory usage, as the cached states need to be stored in memory.

</li></li><li><strong>5:</strong> In your code, <code>use_cache=True</code> is used to enable caching during the generation process, which can help speed up the generation of tokens using the custom streamer.

<li><strong>6:</strong> It's worth noting that the <code>use_cache</code> parameter is only applicable to models that support caching, such as the <code>AutoModelForCausalLM</code> used in your code. Some models may not have this capability, in which case setting <code>use_cache=True</code> would have no effect.
</li></ul>
    
</body>
</html>

"""        
            dos.Bind(wx.EVT_LEFT_DOWN, lambda event: self.OnClickDos(event))
            sizer_0.Add(dos, 0, wx.ALIGN_CENTER)
            sizer_0.Add(self.use_cache_dropdown, 0, wx.ALIGN_CENTER)
            h_sizer_1.Add(sizer_0, 0, wx.ALIGN_CENTER)


    
            
            #v_sizer.Add(h_sizer_1, 0, wx.ALIGN_CENTER) 
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

    def OnMaxTokensChange(self, event):
        # Get the selected do_sample value
        selected_value = self.max_tokens_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.max_tokens = selected_value
        print('OnMaxTokensChange',selected_value, self.tab_id)
        # Continue processing the event
        event.Skip()  

    def OnDoSampleChange(self, event):
        # Get the selected do_sample value
        selected_do_sample = self.do_sample_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.do_sample = (selected_do_sample == 'True')
        print('OnDoSampleChange',selected_do_sample, self.tab_id)
        # Continue processing the event
        event.Skip()
    def OnUseCacheChange(self, event):
        # Get the selected do_sample value
        selected_use_cache = self.use_cache_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.use_cache = (selected_use_cache == 'True')
        print('OnUseCacheChange',selected_use_cache, self.tab_id)
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
        print('OnTempChange')
        pp(self.tab_id)
        # Get the selected do_sample value
        selected_temp = self.temp_dropdown.GetValue()

        # Print the selected model
        chat = apc.chats[self.tab_id]
        chat.temperature = float(selected_temp )


        # Continue processing the event
        event.Skip()    



    def RestoreQuestionForTabId(self, tab_id):
        self.tab_id=tab_id
        message=tab_id
        chat=apc.chats[message]

        if message in self.tabs:
            assert self.chat_type==message[1]
            #print('Chat restoring', message)
            #pp(self.tabs[message])
            self.inputCtrl.SetValue(self.tabs[message]['q'])
            
            self.model_dropdown.SetValue(apc.currentModel[message])
            chat.model = self.model_dropdown.GetValue()
            #self.tab_id=message
            #self.q_tab_id=message
            #self.inputCtrl.SetSelection(0, -1)
            self.inputCtrl.SetFocus()
            
            #print(message, self.tab_id)
            #pp(self.tabs)
        
            if chat.get('max_tokens', None):
                self.max_tokens_dropdown.SetValue(str(chat.max_tokens)) 
            else:
                chat.max_tokens = int(self.max_tokens_dropdown.GetValue())  
            if 1:

                if chat.get('top_p', None):
                    #self.top_p_dropdown.Enable()
                
                    self.top_p_dropdown.SetValue(str(chat.top_p))
                    
                    #wx.MessageBox(f"top_p {chat.top_p} {self.top_p_dropdown.GetValue()}", "top_p"   )
                else:
                    chat.top_p= float(self.top_p_dropdown.GetValue())

            if 1:    
                if chat.get('top_k', None):
                    #self.top_k_dropdown.Enable()
                    self.top_k_dropdown.SetValue(str(chat.top_k))
                else:
                    chat.top_k = int(self.top_k_dropdown.GetValue())


            if chat.get('temperature', None):
                self.temp_dropdown.SetValue(str(chat.temperature))
            else:
                chat.temperature = float(self.temp_dropdown.GetValue())

            if chat.get('do_sample', None) is not None:
                
                val = 'True' if chat.do_sample else 'False'
                self.do_sample_dropdown.SetValue(val)
            else:
                chat.do_sample = (self.do_sample_dropdown.GetValue() == 'True')

            if chat.get('use_cache', None) is not None:
                
                val = 'True' if chat.use_cache else 'False'
                self.use_cache_dropdown.SetValue(val)
            else:
                chat.use_cache = (self.use_cache_dropdown.GetValue() == 'True')