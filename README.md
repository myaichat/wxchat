Next artwork: [Yet another MoA fork](https://medium.com/p/23f4fd43e72d)<br>
[Portrait Fuser](https://medium.com/p/b7735d3460fa)<br>

[Microsoft Promptist](https://medium.com/p/e0ef47ea192b)<br>
[ GrypheMythoMax Prompt fuser](https://medium.com/p/fc3918f756de)<br>
[Groq Llama3 function calling](https://medium.com/p/dd9d33af6ad6) <br>
[AI Inteview Assistant Streamlit UI with voice](https://medium.com/p/56c2cd360a8b) <br>
[AI Inteview Assistant xwPython UI](https://medium.com/p/55b1852b9541)<br>
[AI Inteview Assistant CLI](https://medium.com/@alexbuzunov/starting-with-ai-interview-assistant-cli-on-windows-d2d8e0f4edb1)<br>

Florence 2 config:  https://medium.com/p/722f035caba1 
<br>Qwen 2 Prompt Fuser: [Source](https://github.com/myaichat/wxchat/blob/qwen2_prompt_fuser/include/Prompt/Qwen_Qwen2_Prompt.py), [Model](https://huggingface.co/collections/Qwen/qwen2-6659360b33528ced941e557f)
<br>Nvidia  nemotron-4-340b Prompt Fuser (runs on Nvidia NIM): [Source](https://github.com/myaichat/wxchat/blob/nvidia_nemotron_prompt_fuser/include/Prompt/Nvidia_Nemotron_Prompt.py), [Model](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemo/models/nemotron-4-340b-instruct)
<br>
Meta llama3 70b prompt fuser : [Source](https://github.com/myaichat/wxchat/blob/meta_llama3_prompt_fuser/include/Prompt/Meta_Llama3_Prompt.py) [API](https://build.nvidia.com/meta/llama3-70b) [HF](https://huggingface.co/blog/llama3#inference-integrations)

# Finction Calling/Tools
wxPython UI for function calling  API demo
| Vendor   | API | Model   | Tool | Config | Usage|Info | 
|------------|------------|------------|------------|------------|------------|------------|
|Groq|Transformers| Llama3| [Source](https://github.com/myaichat/wxchat/blob/groq_function_calling/parallel.py)| []()| [Medium](https://medium.com/p/dd9d33af6ad6)|[]()|

# Chat/Copilot
wxPython UI for inference API demo
| Vendor   | API | Model   | Chat/Copilot | Config | Usage|Info | 
|------------|------------|------------|------------|------------|------------|------------|
| Google AI|vertexai| PaLM 2| [Source](https://github.com/myaichat/wxchat/blob/google_palm_copilot/include/Copilot/Google_PaLM.py)| [Medium](https://medium.com/p/ec1b62354bfa)| [Medium](https://medium.com/@alexbuzunov/introducing-palm-2-copilot-your-google-ai-powered-coding-assistant-1dddbf4fc1d0)|[]()|
| Microsoft|onnxruntime_genai | Phi-3 ONNX | [Source](https://github.com/myaichat/wxchat/blob/phy3_copilot/include/Phy3_Python.py)| []()| [Medium](https://github.com/microsoft/Phi-3CookBook?WT.mc_id=aiml-138114-kinfeylo)|[CookBook](https://github.com/microsoft/Phi-3CookBook?WT.mc_id=aiml-138114-kinfeylo)|
| Open AI|openai| gpt-4o| [Source](https://github.com/myaichat/wxchat/blob/feature/poor_mans_copilot/poor_mans/copilot/7d_copilot.py)| [Medium](https://medium.com/p/ec1b62354bfa)| [Medium](https://medium.com/p/6f03ca3b5569), [YouTube](https://www.youtube.com/watch?v=Yh1_YGSjTVQ&t=14s)|[]()|
| Google Vertex AI|vertexai| gemini-pro-*| [Source](https://github.com/myaichat/wxchat/blob/google_vertexai_copilot/include/Copilot/Google_VertexAI.py)| [Medium](https://medium.com/p/aa05cb233f2f)| [Medium](https://medium.com/p/4b06f4f19937)|[]()|
| Anthropic|anthropic | claude-3.x*| [Source](https://github.com/myaichat/wxchat/blob/claude_copilot/include/Copilot/Anthropic_Claude.py)| []()| [Medium](https://medium.com/p/6d295d10e357)|[]()|
| Google Gemma 2|transformers | gemma-2-*| [Source](https://github.com/myaichat/wxchat/blob/google_gemma/include/Copilot/Google_Gemma.py)| [Medium](https://medium.com/p/0d7dc430b72c)| [Medium](https://medium.com/p/4bd85eb997ec)|[]()|
| Qwen|transformers| Qwen2-***-Instruct| [](https://github.com/myaichat/wxchat/blob/qwen2_prompt_fuser/include/Prompt/Qwen_Qwen2_Prompt.py)| []()| []()|[Model](https://huggingface.co/collections/Qwen/qwen2-6659360b33528ced941e557f),[Gihub](https://github.com/QwenLM/Qwen)|


# Vision/Image Fusion
wxPython UI for Vision API demo

| Vendor   | API| Model   | Vision | Config | Usage|Info | 
|------------|------------|------------|------------|------------|------------|------------|
| Open AI|openai| gpt-4o | [Source](https://github.com/myaichat/wxchat/blob/gpt4_vision/include/Gpt4_Vision.py)| []()| [Medium](https://medium.com/p/2031397e3ceb), []()|
| Microsoft|onnxruntime_genai| Phi-3 ONNX | [Source](https://github.com/myaichat/wxchat/blob/phy3_vision/phy3_vision.py)| [Medium](https://medium.com/p/affb8f129332)| [Medium](https://medium.com/p/2d5dd6c0de2d), [YouTube](https://www.youtube.com/watch?v=dQM7_tNfkjs&t=1s)|[]()|
| OpenBMB|transformers  |MiniCPM-Llama3-V-2_5 (int4) | [Source](https://github.com/myaichat/wxchat/blob/minicpm_vision/include/MiniCPM_Vision.py)| []()| [Medium](https://medium.com/p/42bf91aa1c86), []()|[]()|
| Google Gen AI| generativeai |gemini-pro-vision | [Source](https://github.com/myaichat/wxchat/blob/google_vision/include/Google_Vision.py)| [Medium](https://medium.com/p/aa05cb233f2f)| [Medium](https://medium.com/p/c75adecb16eb), []()|[]()|
| Google Vertex AI|vertexai |gemini-pro-* | [Source](https://github.com/myaichat/wxchat/blob/google_vertexai_vision/google_vertexai_vision.py)| [Medium](https://medium.com/p/aa05cb233f2f)| [Medium](https://medium.com/p/0d3e1c0e1fb1), []()|[]()|
| Anthropic |anthropic |claude-3.x* | [Source](https://github.com/myaichat/wxchat/blob/claude_vision/claude_vision.py)| []()| [Medium](https://medium.com/p/1e0f89300754), []()|[]()|
| Microsoft |transformers |Florence-2-large | [](https://github.com/myaichat/wxchat/blob/claude_vision/claude_vision.py)| []()| [](https://medium.com/p/1e0f89300754) []()|[Model](https://huggingface.co/microsoft/Florence-2-large)|




# Prompt Fusion
wxPython UI for Prompt Fusion demo

| Vendor   | API| Model   | Vision | Config | Ueage|Info | 
|------------|------------|------------|------------|------------|------------|------------|
| Anthropic |anthropic| claude-3.x* | [Source](https://github.com/myaichat/wxchat/blob/claude_prompt_fusion/claude_prompt_fusion.py)| []()| [Medium](https://medium.com/p/4bd85eb997ec), []()|[]()|
| Google Gemma 2| transformers|gemma-2-* | [Source](https://github.com/myaichat/wxchat/blob/gemma_prompt_fusion/include/Prompt/Google_Gemma_Prompt.py)| [Medium](https://medium.com/p/0d7dc430b72c)| [Medium](https://medium.com/p/40e30431d9ac), []()|[]()|
|  Open AI|openai| gpt-4o | [Source](https://github.com/myaichat/wxchat/blob/gpt4_prompt_infuser/gpt4_prompt_infuser.py)| []()| [Medium](https://medium.com/me/stats/post/d8b41ec9e482), []()|[]()|
|  Google Vertex AI|vertexai| gemini-pro-* | [Source](https://github.com/myaichat/wxchat/blob/gemini_prompt_fuser/gemini_prompt_fuser.py)| [Medium](https://medium.com/p/aa05cb233f2f)| [Medium](), []()|[]()|
|  Google AI|vertexai |PaLM 2 | [Source](https://github.com/myaichat/wxchat/blob/palm_prompt_fuser/palm_prompt_fuser.py)| [Medium]( https://medium.com/p/ec1b62354bfa)| [Medium](https://medium.com/p/3d3d3f42895d), []()|[]()|
| Microsoft|onnxruntime_genai| Phi-3 ONNX | [Source](https://github.com/myaichat/wxchat/blob/phi3_prompt_fuser/phi3_prompt_fuser.py)| []()| [Medium]()|[]()|
| Qwen|transformers| Qwen2-***-Instruct| [Source](https://github.com/myaichat/wxchat/blob/qwen2_prompt_fuser/include/Prompt/Qwen_Qwen2_Prompt.py)| []()| [Medium]()|[Model](https://huggingface.co/collections/Qwen/qwen2-6659360b33528ced941e557f)|
| Nvidia<br>(runs on Nvidia NIM) |openai| nemotron-4-340b| [Source](https://github.com/myaichat/wxchat/blob/nvidia_nemotron_prompt_fuser/include/Prompt/Nvidia_Nemotron_Prompt.py)| []()| [Medium](https://medium.com/p/f9d55677d01a)|[Model](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemo/models/nemotron-4-340b-instruct)|
| Qwen|transformers| Qwen2-***-Instruct,[72B deepinfra](https://deepinfra.com/Qwen/Qwen2-72B-Instruct/api?example=openai-python)| [](https://github.com/myaichat/wxchat/blob/qwen2_prompt_fuser/include/Prompt/Qwen_Qwen2_Prompt.py)| []()| [Medium](https://medium.com/p/1ee0e47bfaf2)|[Model](https://huggingface.co/collections/Qwen/qwen2-6659360b33528ced941e557f),[Gihub](https://github.com/QwenLM/Qwen)|
| Meta|openai|  llama3 70b,[70B](https://build.nvidia.com/meta/llama3-70b),[HF](https://huggingface.co/blog/llama3#inference-integrations)| [Source](https://github.com/myaichat/wxchat/blob/meta_llama3_prompt_fuser/include/Prompt/Meta_Llama3_Prompt.py)| []()| [Medium](https://medium.com/p/a29c396f73c1)|[]()|
|  Gryphe| MythoMax | [Source](https://github.com/myaichat/wxchat/blob/mythomax_prompt_fuser/include/Prompt/Gryphe_MythoMax_Prompt.py)| []()| [Medium](https://medium.com/p/fc3918f756de), []()|[]()|
|  Microsoft | Promptist | [Source](https://github.com/myaichat/wxchat/blob/microsoft_promptist/include/Prompt/Promptist_Microsoft_Prompt.py)| []()| [Medium](https://medium.com/p/e0ef47ea192b), []()|[]()|





# Image Generation
Image Generation demo UI using wxpython

| Vendor   | Model   | Image Generation | Config | Usage|Info | 
|------------|------------|------------|------------|------------|------------|
| OpenAI| dall-e-3 | [Source](https://github.com/myaichat/wxchat/blob/create_dalee_image/image/create_dalee_image/7awx_any.py)| []()| [Medium](https://medium.com/p/70f457c2e851), [YouTube](https://www.youtube.com/watch?v=QlUF6PXgLOo&t=36s)|[]()|



## Youtube

ChatGPT Chat/Copilot: [All-In_One DB Copilot](https://www.youtube.com/watch?v=DdMXzxL0VBo&t=2s),  [Oracle PL/SQL Copilot](https://www.youtube.com/watch?v=v0Pnl-bAm9c),  [Python Copilot](https://www.youtube.com/watch?v=Yh1_YGSjTVQ&t=14s)

ChatGPT Desktop Client: [Multi Chat](https://www.youtube.com/watch?v=iTnSehOSrg8&t=209s)

Voice: [Interview Voice Assistant](https://www.youtube.com/watch?v=tgAFRJ-jb3s&t=4s)


DALEE-3: [Image Generator](https://www.youtube.com/watch?v=QlUF6PXgLOo&t=36s)

ChatGPT streaming chat: [wxPython chat](https://www.youtube.com/watch?v=Jb886h3kZGE&t=643s)


wxPython: [Rudimentary terminal](https://www.youtube.com/watch?v=odpbWfRmvDU), [Create gist](https://www.youtube.com/watch?v=FFqcDB1Yytw),  [Diagrammer](https://www.youtube.com/watch?v=TdXTu1l2Rz0&t=18s)

[Stabiliti.ai](https://platform.stability.ai/docs/legacy/grpc-api/features/image-to-image#Python)
[img-2-img](https://huggingface.co/docs/diffusers/en/using-diffusers/img2img)



### Google: 
[Sample browser](https://cloud.google.com/docs/samples)  [Gemma2 Config](https://medium.com/p/0d7dc430b72c)    [GPrompt Gallery](https://console.cloud.google.com/vertex-ai/generative/prompt-gallery?_ga=2.197961389.362164277.1719958699-521879258.1717807561&project=spatial-flag-427113-n0) 



#### Dedicated infer
https://docs.api.nvidia.com/nim/reference/google-gemma7b-infer

https://huggingface.co/docs/inference-endpoints/guides/create_endpoint

### Huggingface Creating endpoint
https://huggingface.co/learn/cookbook/enterprise_dedicated_endpoints 
[Tasks](https://huggingface.co/docs/inference-endpoints/supported_tasks )
[Control Space programmatically](https://huggingface.co/docs/huggingface_hub/en/guides/manage-spaces )
[Custom handler](https://huggingface.co/docs/inference-endpoints/guides/custom_handler)
[Deploy Llama3](https://huggingface.co/blog/llama3#inference-integrations) 
[Use via API](https://www.gradio.app/guides/getting-started-with-the-python-client#the-view-api-page)
[OpenAI  Inference API](https://huggingface.co/blog/tgi-messages-api#using-inference-endpoints-with-openai-client-libraries)
[Serverless Inference API](https://huggingface.co/docs/api-inference/en/index)
[HF Chat](https://huggingface.co/chat/)


### Deepseek
https://huggingface.co/deepseek-ai/DeepSeek-V2-Chat
https://deepseekcoder.github.io/


### Api-gen
https://apigen-pipeline.github.io/

Openchat: https://github.com/imoneoi/openchat#installation

#### Salesforce
https://github.com/SalesforceAIResearch/xLAM
[stablediffusionap img2img](https://stablediffusionapi.com/docs/community-models-api-v4/dreamboothimg2img/)

People to follow:
| #  | Name                        | LinkedIn                                                   | Twitter                   | Newsletter/Blog                                       | Website/YouTube/Podcast                                 | Top Audience                         | Why Follow                              | Usual Location         |
|----|-----------------------------|------------------------------------------------------------|---------------------------|-------------------------------------------------------|----------------------------------------------------------|-------------------------------------|----------------------------------------|------------------------|
| 1  | Andrej Karpathy             | NA                                                         | [@karpathy](https://twitter.com/karpathy) | [Blog](https://karpathy.github.io/)                     | [YouTube](https://www.youtube.com/@andrejkarpathy)      | Software Engineers                    | Mostly his time at Tesla, YouTube tutorials | Stanford, California  |
| 2  | Dwarkesh Patel              | NA                                                         | [@dwarkesh_sp](https://twitter.com/dwarkesh_sp) | [Podcast](https://dwarkesh.substack.com)                | [YouTube](https://www.youtube.com/c/DwarkeshPatel)      | YouTubers, General AI Enthusiasts     | Strictly AI related interviews            | San Francisco, California |
| 3  | Philipp Schmid              | [LinkedIn](https://www.linkedin.com/in/philipp-schmid-a6a2bb196/) | [@_philschmid](https://twitter.com/_philschmid) | [Blog](https://www.philschmid.de/)                      | [Hugging Face Posts](https://huggingface.co/posts)     | ML Researchers                        | For open-source LLM news ONLY             | Germany               |
| 4  | Linxi ‘Jim’ Fan             | [LinkedIn](https://www.linkedin.com/in/drjimfan/)          | [@DrJimFan](https://twitter.com/DrJimFan)   | NA                                                    | [Ted Talk](https://www.ted.com/talks/linxi_jim_fan_the_next_grand_challenge_in_ai) | AI Enthusiasts                        | Insights on Robotics & Agentic AI, Videos | Stanford, California  |
| 5  | Sahar Mor                   | [LinkedIn](https://www.linkedin.com/in/sahar-mor/)          | [@theaievangelist](https://twitter.com/theaievangelist) | [AI Tidbits](https://substack.com/)                       | [Substack](https://substack.com/)                        | Software Engineers                    | Breaking News on recent launches          | San Francisco, California |
| 6  | Jeremy Caplan               | [LinkedIn](https://www.linkedin.com/in/jeremycaplan/)       | [@jeremycaplan](https://twitter.com/jeremycaplan)  | [Wonder Tools](https://jeremycaplan.substack.com)      | [Website](https://jeremycaplan.com/)                    | General AI Enthusiasts                | Mostly for AI tool insights               | New York, New York     |
| 7  | Benedict Evans              | [LinkedIn](https://www.linkedin.com/in/benedictevans/)      | (closed)                  | [Newsletter](https://www.ben-evans.com/newsletter)    | [Website](https://www.ben-evans.com/contact)            | General AI Enthusiast                 | Insights into historical macro context of BigTech | New York              |
| 8  | Paris Marx                  | [LinkedIn](https://www.linkedin.com/in/parismarx/)          | [@techwontsaveus](https://twitter.com/techwontsaveus) | [Disconnect](https://disconnect.blog/)                   | [YouTube](https://www.youtube.com/@techwontsaveus)       | General AI Enthusiasts, skeptics      | The BigTech backlash content              | Montreal, Canada       |
| 9  | Yann LeCun                  | [LinkedIn](https://www.linkedin.com/in/yann-lecun/)         | [@ylecun](https://twitter.com/ylecun)      | NA                                                    | [Website](https://yann.lecun.com/)                      | AI Researchers                        | Contributions to deep learning and AI advancements | New York              |
| 10 | Andrew Ng                   | [LinkedIn](https://www.linkedin.com/in/andrewyng/)          | [@AndrewYNg](https://twitter.com/AndrewYNg) | NA                                                    | [Website](https://www.andrewng.org/)                    | AI Researchers, Educators             | AI research and education influence       | Stanford, California  |
| 11 | Fei-Fei Li                  | [LinkedIn](https://www.linkedin.com/in/feifeili/)           | [@drfeifei](https://twitter.com/drfeifei)   | NA                                                    | [Website](https://profiles.stanford.edu/fei-fei-li)     | AI Researchers                        | Computer vision and AI for social good    | Stanford, California  |
| 12 | Geoffrey Hinton             | [LinkedIn](https://www.linkedin.com/in/geoffreyhinton/)     | [@geoffreyhinton](https://twitter.com/geoffreyhinton) | NA                                                    | [Website](https://www.cs.toronto.edu/~hinton/)          | AI Researchers                        | Foundational work in neural networks       | Toronto, Canada       |
| 13 | Richard Socher              | [LinkedIn](https://www.linkedin.com/in/richardsocher/)      | [@RichardSocher](https://twitter.com/RichardSocher) | NA                                                    | [Website](https://www.socher.org/)                      | AI Researchers, Industry Leaders      | Natural language processing and AI applications | San Francisco, California |
| 14 | Nathan Benaich              | [LinkedIn](https://www.linkedin.com/in/nathanbenaich/)      | [@nathanbenaich](https://twitter.com/nathanbenaich) | [Guide to AI](https://www.nathanbenaich.com/)            | [Website](https://www.nathanbenaich.com/)               | Investors, General AI Enthusiasts     | VC insights, State of AI report            | London, UK            |
| 15 | Linus Ekenstam              | [LinkedIn](https://www.linkedin.com/in/linusekenstam/)      | [@LinusEkenstam](https://twitter.com/LinusEkenstam) | [Inside My Head](https://linusekenstam.substack.com)   | [Bento](https://bento.me/linusekenstam)                  | AI General Audience, Tinkerers        | AI design and innovative thinking         | Barcelona, Spain      |
| 16 | Tobias Zwingmann            | [LinkedIn](https://www.linkedin.com/in/tobias-zwingmann/)   | [@ztobi](https://twitter.com/ztobi)        | [The Augmented Advantage](https://newsletter.tobiaszwingmann.com/) | [Book](https://www.amazon.com/AI-Powered-Business-Intelligence-Tobias-Zwingmann-ebook/dp/B0B3SGQJC1?ref_=ast_author_mpb) | B2B professionals, Founders, CEOs      | B2B insights on AI                         | Hannover, Germany     |
| 17 | Sinead Bovell               | [LinkedIn](https://www.linkedin.com/in/sinead-bovell-89072a34/) | [@sineadbovell](https://twitter.com/sineadbovell) | TBA                                                   | [Instagram](https://www.instagram.com/sineadbovell/)    | General AI Enthusiasts                | Influencer content and videos              | New York, USA          |
| 18 | Jeong-Bae Son              | [LinkedIn](https://www.linkedin.com/in/jeong-bae-son/)      | NA                        | NA                                                    | [Personal Website](https://www.usq.edu.au/about-us/our-people/academic-staff/jeong-bae-son) | Applied Linguistics, TESOL            | Computer-assisted language learning       | Australia             |
| 19 | Natasha Kathleen Ruži      | [LinkedIn](https://www.linkedin.com/in/natasha-kathleen-ruži/) | NA                        | NA                                                    | [Institute Website](https://www.imes.hr/)               | Computer-mediated communication       | Educational outcomes for migrants          | Zagreb, Croatia        |
| 20 | Garimella                  | NA                                                         | NA                        | NA                                                    | NA                                                       | PhD Students, Early Career Researchers | Rising Star in AI, Machine Learning and Systems | NA                    |


<br>
<br>
<br>
<br>

### Each demo starts as an orphan branch

git checkout --orphan branchname

git rm -rf .
 

add files

 

git add .

git commit -m "init"

git push -u origin branchname
