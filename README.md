# SpeakStream AI 🎙️

**Simultaneous Voice Chat with ChatGPT, Claude, Grok, Perplexity & Gemini**

A thread-safe Streamlit application that records your voice and streams responses from all 5 major AI models simultaneously for instant comparison.

![SpeakStream AI Multi-Model Interface](screenshot.png)

## ✨ Features

- 🎤 **Voice Recording**: High-quality 16kHz audio capture with background threading
- 🤖 **Auto-Transcription**: OpenAI Whisper API integration with manual editing support
- 🚀 **Multi-Model Streaming**: Simultaneous responses from ChatGPT, Claude, Grok, Perplexity & Gemini
- 📊 **Real-Time Comparison**: Side-by-side response streaming in tabbed interface
- 💾 **Conversation Logging**: JSON logs for each model with timestamps
- 🔧 **Thread-Safe Design**: Non-blocking UI with proper concurrency handling
- 🎛️ **Flexible Configuration**: WebUI + API support for each model
- ⚡ **Smart Auto-Mode**: Automatic transcription and response triggering

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/myaichat/speakstream-ai.git
cd speakstream-ai

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.template .env
# Edit .env with your API keys

# Optional: Start Chrome for WebUI features
chrome --remote-debugging-port=9222

# Run the application
streamlit run gemini_model_chat_app.py
```

## 📋 Requirements

- Python 3.8+
- Streamlit
- OpenAI API key (for Whisper transcription)
- API keys for desired AI models (ChatGPT, Claude, Grok, Perplexity, Gemini)
- Chrome browser (for WebUI features)
- Microphone access

## 🏗️ Architecture

### Modular Handler Pattern
Each AI model has its own dedicated handler module:

```
📁 chat_handlers/
├── chatgpt_handler.py      # ChatGPT WebUI + API
├── claude_handler.py       # Claude WebUI + API  
├── grok_handler.py         # Grok WebUI + API
├── perplexity_handler.py   # Perplexity WebUI + API
└── gemini_handler.py       # Gemini WebUI + API
```

### Key Components
- **Audio Recording**: Background thread captures voice without blocking UI
- **Transcription**: OpenAI Whisper converts speech to text
- **Concurrent Streaming**: All enabled models process simultaneously
- **Centralized State**: 200+ session variables manage everything
- **Thread Safety**: `add_script_run_ctx` enables safe UI updates from background threads

## 🎯 Usage

### Basic Workflow
1. **Enable Models**: Check WebUI/API boxes for models you want to use
2. **Set Auto-Mode**: Enable auto-transcribe and auto-response for seamless experience
3. **Record**: Press ▶️ Start → speak → press ⏹️ Stop
4. **Compare**: Watch responses stream into separate tabs
5. **Refine**: Edit transcription and press Ctrl+Enter to re-query

### Advanced Features
- **Smart Auto-Triggering**: Some models start immediately when enabled
- **Emergency Stop**: Stop all streaming with one button
- **Manual Transcription Editing**: Refine voice-to-text before querying
- **Conversation History**: JSON logs for each model and session

## ⚙️ Configuration

### Environment Variables
Create a `.env` file with your API keys:

```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
XAI_API_KEY=your_grok_key
PERPLEXITY_API_KEY=your_perplexity_key
GOOGLE_API_KEY=your_gemini_key
```

### Audio Settings
```python
RATE, CH = 16_000, 1  # 16kHz mono for optimal voice recognition
OUT_DIR = "recordings"  # Timestamped WAV files
TIMEOUT_SEC = 60  # Max recording length
```

## 📁 Project Structure

```
📁 speakstream-ai/
├── gemini_model_chat_app.py          # Main multi-model app
├── simple_chat_app.py                # Simplified single-model version
├── .env.template                     # API key template
├── requirements.txt                  # Python dependencies
├── 📁 chat_handlers/                 # AI model handlers
│   ├── chatgpt_handler.py
│   ├── claude_handler.py
│   ├── grok_handler.py
│   ├── perplexity_handler.py
│   └── gemini_handler.py
├── 📁 include/                       # Core utilities
│   └── transcribe.py                 # Whisper integration
├── 📁 logs/                          # Conversation logs (auto-created)
├── 📁 recordings/                    # Audio files (auto-created)
└── 📁 docs/                          # Documentation
```

## 🔧 Adding New AI Models

Want to add a sixth model? Follow this pattern:

### 1. Create Handler Module
```python
# chat_handlers/your_model_handler.py
def start_concurrent_streaming(question):
    """Start WebUI and/or API streams"""
    # Implementation here

def render_your_model_responses():
    """Display responses in two columns"""
    # UI rendering here

def handle_concurrent_streaming(question, stream_type):
    """Background streaming logic"""
    # Streaming implementation here

def handle_stopped_streaming():
    """Cleanup on stop"""
    # Cleanup logic here
```

### 2. Add Session State Variables
```python
# Add to main app initialization
if "your_model_concurrent_streaming_active" not in st.session_state:
    st.session_state.your_model_concurrent_streaming_active = False
# ... add all necessary state variables
```

### 3. Wire UI Components
```python
# Add to model selection, tabs, and streaming handler
# Follow existing patterns for ChatGPT, Claude, etc.
```

## 🚀 Performance Tips

- **Batch Token Updates**: Update UI every ~20 tokens instead of per-token
- **Selective Model Enabling**: Only enable models you're actively comparing
- **Local Whisper**: Use local whisper-tiny model for heavy transcription workloads
- **Chrome Debugging**: Use `--remote-debugging-port=9222` for free WebUI response scraping

## 🐛 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `RuntimeError: Cannot call st.* from a thread` | Ensure `add_script_run_ctx(thread)` is called before starting threads |
| Streaming text doesn't appear | Check that `st.rerun()` is called in the central streaming loop |
| No audio captured | Check microphone permissions and `sounddevice` installation |
| Model not responding | Verify API keys in `.env` and check handler implementation |

## 🛣️ Roadmap

- 🔄 **Streaming Audio Upload**: Direct S3 upload for long conversations
- 🖼️ **Multimodal Support**: Screenshot-to-prompt for visual questions
- 🔬 **Response Scoring**: A/B testing widget with CSV export
- 📈 **Analytics Dashboard**: Latency and token-per-second metrics
- 🎯 **Local LLM Support**: Ollama, LM Studio integration
- 🔊 **Text-to-Speech**: Hear responses back with voice synthesis

## 🤝 Contributing

We welcome contributions! Here's how you can help:

- 🌟 **Star the repository** to show your support
- 🐛 **Report issues** if you encounter problems
- 💡 **Suggest features** for new AI models or capabilities
- 🤝 **Submit pull requests** for improvements
- 📖 **Improve documentation** and tutorials

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with a clear description

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- OpenAI for Whisper API
- Streamlit for the amazing web framework
- All AI model providers for their APIs
- The open source community for inspiration and feedback

## 📞 Support

- 📚 **Documentation**: Check the `/docs` folder for detailed guides
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💬 **Discussions**: Join conversations in GitHub Discussions
- 📧 **Contact**: Reach out for collaboration opportunities

---

**SpeakStream AI** - Transforming voice into insights across multiple AI models simultaneously. Whether you're researching AI model differences, building comparison tools, or exploring multi-model conversations, this solution provides a solid foundation that's both powerful and extensible.

**Ready to start?** Clone the repo, configure your API keys, and begin exploring the fascinating world of multi-model AI conversations! 🚀

---

**Tags:** `streamlit` `voice-ai` `chatgpt` `claude` `grok` `perplexity` `gemini` `python` `threading` `concurrent` `whisper` `ai-comparison`
