# 🚀 Chat → LinkedIn Post Generator

Transform your ChatGPT conversations into professional LinkedIn posts with just a few clicks! This tool automatically extracts, summarizes, and formats your ChatGPT discussions into engaging LinkedIn content, helping you grow your professional brand effortlessly.

## ✨ Features

- 🔗 **Easy Input**: Simply paste your ChatGPT shared URL
- 🤖 **Multi-Model AI**: Choose from OpenAI, Claude, and Mistral models
- 🔑 **Flexible API Keys**: Support for multiple AI providers
- 📝 **Professional Formatting**: Generates LinkedIn-ready posts in various styles
- 🔄 **Auto-Posting**: Option to directly post to your LinkedIn profile
- 🎨 **Customizable**: Choose your post style and tone
- 🔒 **Privacy Control**: Select post visibility (Public/Connections)
- 💬 **Copy-Paste Ready**: Get formatted content ready to share
- 🔐 **Secure Credentials**: Temporary credential storage with easy clearing
- ⏱️ **Session Management**: Automatic session timeout and rate limiting
- 🚀 **One-Click Deployment**: Easy deployment to Streamlit Cloud

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/linkedin-chatgpt.git
cd linkedin-chatgpt
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (optional):
   - Copy `.env.example` to `.env`
   - Add your API keys (OpenAI, Claude, OpenRouter)
   - Note: API keys can also be entered directly in the UI

## 🚀 Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Configure your AI settings:
   - Enter your preferred API keys (OpenAI, Claude, OpenRouter)
   - Select your AI provider and model
   - All keys are stored securely in your session

3. Input your ChatGPT shared URL

4. Choose your post style and tone

5. (Optional) Enable auto-posting to LinkedIn:
   - Enter your LinkedIn credentials in the secure UI
   - Credentials are stored temporarily in your session
   - Use the "Clear Credentials" button to remove stored credentials

6. Click "Generate LinkedIn Post"

7. Copy the generated post or let it auto-post to LinkedIn

## 🔒 Security Features

- **Temporary Credential Storage**: All credentials are stored only in your browser session
- **Easy Clearing**: One-click credential clearing with the "Clear Credentials" button
- **Secure Input**: Password fields are properly masked
- **No Permanent Storage**: Credentials are never stored on the server
- **Environment Variables**: Optional for local development only
- **Session Timeout**: Automatic session expiration after 30 minutes
- **Rate Limiting**: Prevents spam with 60-second cooldown between posts
- **Session Timer**: Visual indicator of remaining session time

## 🚀 One-Click Deployment

### Option 1: Streamlit Cloud (Recommended)
1. Fork this repository
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New App"
4. Select your forked repository
5. Set `app.py` as the entry point
6. Add your API keys in the secrets tab (optional)
7. Click "Deploy"

### Option 2: GitHub Actions (Automatic)
1. Fork this repository
2. Add your secrets in GitHub:
   - `STREAMLIT_TOKEN`: Your Streamlit Cloud token
   - `OPENAI_API_KEY`: Your OpenAI API key (optional)
   - `CLAUDE_API_KEY`: Your Claude API key (optional)
   - `OPENROUTER_API_KEY`: Your OpenRouter API key (optional)
3. Push to main branch to trigger automatic deployment

## 📁 Project Structure

```
linkedin_postgen/
├── app.py             # Streamlit frontend and app logic
├── extractor.py       # Extracts plain text from ChatGPT shared URLs
├── summarizer.py      # Summarizes content using multiple AI models
├── postgen.py         # Generates final LinkedIn-ready post
├── linkedin_poster.py # Handles LinkedIn auto-posting
├── requirements.txt   # Required packages
├── .env               # Environment variables (optional)
├── streamlit_app.yaml # Streamlit deployment configuration
└── .github/workflows/ # GitHub Actions deployment workflow
    └── deploy.yml     # Automatic deployment configuration
```

## 💡 Use Cases

- Convert technical problem-solving into thought leadership posts
- Share your developer journey and project updates
- Create engaging content from your ChatGPT learning sessions
- Build your professional brand with consistent posting
- Document and share your technical discoveries

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI, Anthropic, and Mistral for their powerful language models
- Streamlit for the amazing web framework
- LinkedIn API for enabling direct posting