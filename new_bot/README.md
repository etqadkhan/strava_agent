# 🏃‍♂️ Strava Agent - AI-Powered Running Coach

An intelligent, multi-agent AI system that provides personalized running coaching by analyzing your Strava data through a sophisticated Telegram bot interface. Built with LangGraph, Google Gemini AI, and ChromaDB for advanced data processing and insights.

## ✨ Features

- **🤖 AI-Powered Coaching**: Uses Google Gemini AI to analyze your running data and provide personalized insights
- **📱 Telegram Bot Interface**: Easy-to-use chat interface for asking questions about your runs
- **🏃 Strava Integration**: Automatically syncs your running activities from Strava with intelligent deduplication
- **📊 Advanced Analytics**: Generates plots and visualizations of your running performance
- **👥 Multi-User Support**: Each user can have their own Strava account and data
- **🧠 LangGraph Workflow**: Sophisticated 9-agent workflow for intelligent data processing
- **🔒 Secure & Private**: User data isolation and secure API key management

## 🏗️ System Architecture

### Multi-Agent Workflow System

The system implements a sophisticated 9-agent workflow using LangGraph:

1. **Personal Info Checker Agent**: Validates user information completeness
2. **Strava Agent**: Fetches and processes running activities with intelligent deduplication
3. **Document Creator Agent**: Converts data to natural language summaries using LLM
4. **Document Storage Agent**: Stores processed documents in ChromaDB vector database
5. **Query Interpreter Agent**: Converts natural language to structured queries
6. **Document Retriever Agent**: Performs semantic search and retrieves relevant data
7. **Coach Agent**: Generates personalized coaching insights
8. **Plotting Agent**: Creates AI-powered visualizations with fallback mechanisms
9. **Response Formatter Agent**: Formats final responses for Telegram delivery

### Core Components

- **Telegram Bot** (`telegram_bot/`): Handles user interactions and message routing
- **AI Workflow** (`agents/`): LangGraph-powered workflow for intelligent data processing
- **Strava Client** (`strava/`): API client for fetching running data with OAuth2
- **LLM Integration** (`llm/`): Google Gemini AI integration with rate limiting
- **Data Storage** (`utils/`): ChromaDB vector database and chat context management

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Strava API access
- Google Gemini API key
- Telegram bot token

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/strava-agent.git
   cd strava-agent
   ```

2. **Install dependencies using uv**
   ```bash
   cd new_bot
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your actual API keys and tokens
   ```

4. **Run the bot**
   ```bash
   uv run python main.py
   ```

## ⚙️ Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```env
# Strava Configuration
STRAVA_CLIENT_ID=your_strava_client_id_here
STRAVA_CLIENT_SECRET=your_strava_client_secret_here
STRAVA_REFRESH_TOKEN=your_strava_refresh_token_here

# Google Gemini Configuration
GOOGLE_API_KEY=your_google_api_key_here
MODEL_NAME=gemini-2.0-flash
EMBED_MODEL=models/text-embedding-004

# Telegram Configuration
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Database Configuration
CHROMA_DB_DIR=./chroma_stores

# User Configuration (JSON string)
USERS={"user1": {"chat_id": 123456789, "strava_refresh_token": "token1"}}
```

### API Setup Instructions

#### Strava API Setup
1. Go to https://www.strava.com/settings/api
2. Create a new application
3. Note down your `Client ID` and `Client Secret`
4. Set the Authorization Callback Domain to `localhost`
5. Visit the authorization URL to get your refresh token:
   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&response_type=code&scope=activity:read_all
   ```

#### Google Gemini API Setup
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Enable the Gemini API in your Google Cloud Console

#### Telegram Bot Setup
1. Message @BotFather on Telegram
2. Use the `/newbot` command
3. Follow the instructions to create your bot
4. Note down the bot token

### User Configuration

The `USERS` variable supports multiple users with different Strava accounts:

```json
{
  "etqad": {
    "chat_id": "123456789",
    "strava_refresh_token": "your_token"
  },
  "wife": {
    "chat_id": "987654321", 
    "strava_refresh_token": "her_token",
    "strava_client_id": "her_client_id",
    "strava_client_secret": "her_client_secret"
  }
}
```

## 📱 Usage

### Bot Commands

- `/start` - Initialize the bot and set up personal information
- `/sync` - Sync your latest Strava running activities
- `/info` - View or update your personal information
- `/clear` - Clear chat history
- `/reset` - Reset your personal information
- `/help` - Show available commands

### Example Queries

- "Analyze my easy run from yesterday"
- "Compare my last two long runs"
- "How did my pace improve over the last month?"
- "Show me my heart rate trends for tempo runs"
- "What's my best 10K time?"
- "Compare Tempo Run 1 and 2"
- "How did my easy runs perform in August?"

## 🔍 Advanced Features

### Intelligent Data Processing

- **Automatic Deduplication**: Only fetches new runs from Strava
- **Stream Data Extraction**: Per-kilometer breakdowns with metrics
- **Fallback Handling**: Graceful degradation for manual runs
- **Rich Metadata**: Comprehensive indexing for efficient search

### Natural Language Understanding

- **Complex Queries**: Support for date ranges, run types, metrics
- **Temporal Expressions**: "last 30 days", "August", specific dates
- **Specific Run Requests**: "Tempo Run 1 and 2"
- **Comparative Analysis**: Run-to-run comparisons
- **Metric Filtering**: Heart rate ranges, pace thresholds

### Personalized Coaching

- **Context-Aware Responses**: Consider user preferences and history
- **Actionable Insights**: Specific recommendations based on data
- **Progress Tracking**: Trend analysis and goal alignment
- **Training Load Analysis**: Volume and intensity assessment

### Advanced Visualizations

- **AI-Powered Charts**: Context-aware visualization selection
- **Multiple Chart Types**: Line plots, bar charts, scatter plots
- **Performance Trends**: Pace, heart rate, power over time
- **Comparative Analysis**: Side-by-side run comparisons
- **Fallback Mechanisms**: Graceful degradation to simple plots

## 🛠️ Development

### Code Quality

- **Black**: Code formatting (88 character line length)
- **Flake8**: Linting and style checking
- **Pre-commit hooks**: Automatic code quality checks

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black .
```

### Adding Dependencies

```bash
uv add package_name
uv add --dev package_name  # For development dependencies
```

## 📁 Project Structure

```
strava-agent/
├── new_bot/                    # Main application directory
│   ├── agents/                 # AI workflow agents
│   │   ├── simple_agent.py     # Basic agent implementation
│   │   └── workflow.py         # LangGraph workflow orchestration
│   ├── llm/                    # Google Gemini integration
│   │   └── client.py           # LLM client with rate limiting
│   ├── strava/                 # Strava API client
│   │   └── client.py           # OAuth2 client with token refresh
│   ├── telegram_bot/           # Telegram bot implementation
│   │   └── bot.py              # Bot interface and command handling
│   ├── utils/                  # Utility modules
│   │   ├── chat_context.py     # User conversation management
│   │   ├── chroma_manager.py   # Vector database operations
│   │   ├── plotting_agent.py   # Visualization generation
│   │   ├── token_manager.py    # Secure token handling
│   │   └── user_mapper.py      # User configuration management
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── pyproject.toml          # Project configuration
│   └── env.example             # Environment template
├── src/                        # Alternative source structure
├── pyproject.toml              # Root project configuration
└── README.md                   # This file
```

## 🔒 Security & Privacy

### Data Protection

- **Environment Variables**: All secrets stored securely in `.env` files
- **User Isolation**: Separate databases per user with ChromaDB
- **Local Storage**: User data stored locally, not in the cloud
- **Minimal Collection**: Only necessary information is collected
- **Secure Token Management**: OAuth2 implementation with automatic refresh

### API Security

- **OAuth2 Implementation**: Secure Strava authentication
- **Rate Limiting**: Respectful API usage with exponential backoff
- **Token Management**: Automatic refresh handling
- **Input Validation**: Sanitized user inputs

### What's Protected

- **API Keys**: Never committed to version control
- **User Tokens**: Stored securely in environment variables
- **Personal Data**: Isolated per user in separate databases
- **Chat History**: Stored locally with user isolation

## 🚨 Important Security Notes

- **Never commit `.env` files** - they contain sensitive API keys
- **Keep API keys secure** - rotate them periodically
- **User data isolation** - each user's data is stored separately
- **Local storage only** - no data is sent to external services

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run code quality checks: `uv run black . && uv run flake8`
5. Submit a pull request

### Development Guidelines

- **Agent Development**: Add new specialized agents to the workflow
- **Integration**: Support additional data sources and platforms
- **Visualization**: Enhance plotting capabilities and chart types
- **Documentation**: Improve guides and API documentation

## 📊 Performance & Scalability

### System Characteristics

- **User Isolation**: Independent databases per user
- **Modular Architecture**: Easy component replacement and extension
- **Efficient Caching**: Intelligent data reuse and embedding cache
- **Rate Limit Respect**: Sustainable API usage with automatic retry

### Reliability Features

- **Error Recovery**: Graceful handling of failures and edge cases
- **Fallback Mechanisms**: Multiple recovery strategies for robustness
- **Data Validation**: Comprehensive input checking and validation
- **Monitoring**: Detailed logging and debugging capabilities

## 🔧 Troubleshooting

### Common Issues

1. **API Rate Limits**: Automatic retry with exponential backoff
2. **Token Expiration**: Automatic refresh handling
3. **Missing Data**: Graceful degradation for incomplete data
4. **Configuration Errors**: Clear error messages and setup guides

### Debug Mode

Enable detailed logging by modifying the logging configuration in `main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

### Support

If you encounter issues:

1. Check the logs in `bot.log`
2. Verify your API keys are correct
3. Ensure all dependencies are installed
4. Check that your Strava account has running activities
5. Review the [Issues](https://github.com/yourusername/strava-agent/issues) page

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](new_bot/LICENSE) file for details.

## 🙏 Acknowledgments

- [Strava API](https://developers.strava.com/) for running data
- [Google Gemini](https://ai.google.dev/) for AI capabilities
- [LangGraph](https://langchain-ai.github.io/langgraph/) for workflow orchestration
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [LangChain](https://python.langchain.com/) for LLM integration framework

## 🚀 Future Enhancements

### Planned Features

1. **Advanced Analytics**: Machine learning-based insights and predictions
2. **Enhanced Visualization**: Interactive charts and dashboards
3. **Social Features**: Group challenges and performance sharing
4. **Integration Expansion**: Additional fitness platforms and wearables
5. **Mobile Integration**: Native app support and notifications

### Extensibility Points

- **New Agents**: Easy to add specialized agents for specific tasks
- **Additional Data Sources**: Support for other fitness and health platforms
- **Enhanced Analytics**: ML models and predictive insights
- **Custom Workflows**: User-defined analysis workflows

## 📞 Getting Help

If you need assistance:

1. **Documentation**: This README contains comprehensive setup and usage information
2. **Issues**: Check existing issues or create new ones on GitHub
3. **Discussions**: Use GitHub Discussions for questions and ideas
4. **Contributing**: Submit pull requests for improvements

---

**Happy Running! 🏃‍♂️💨**

*This Strava Agent represents a sophisticated implementation of modern AI architecture, combining multi-agent systems, LLM integration, vector databases, and intelligent data processing to provide personalized running coaching through an intuitive Telegram interface.*
