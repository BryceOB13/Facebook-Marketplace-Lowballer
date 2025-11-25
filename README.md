# Marketplace Deal Scout

A production-ready browser automation system that navigates Facebook Marketplace, extracts product listings, and tracks deals across sessions.

## Features

- Automated Facebook Marketplace browsing
- Deal discovery and tracking with persistent memory
- Chrome DevTools Protocol integration
- Rate limiting and anti-detection measures
- Session persistence across executions
- Property-based testing for correctness

## Prerequisites

- Python 3.9 or higher
- Google Chrome browser
- Node.js (for chrome-devtools-mcp)
- uv/uvx (for strands-agents-mcp-server)

## Installation

1. Clone the repository and navigate to the project directory

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the package in development mode:
```bash
pip install -e .
```

## Chrome Setup

Launch Chrome with remote debugging enabled:

### macOS
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/.chrome-marketplace-profile \
  --disable-blink-features=AutomationControlled
```

### Linux
```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=$HOME/.chrome-marketplace-profile \
  --disable-blink-features=AutomationControlled
```

### Windows
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir=%USERPROFILE%\.chrome-marketplace-profile ^
  --disable-blink-features=AutomationControlled
```

## MCP Server Configuration

The MCP servers are configured in `.kiro/mcp.json`. The default configuration includes:

- **chrome-devtools**: Browser automation via Chrome DevTools Protocol
  - Connects to Chrome remote debugging port (default: 9222)
  - Auto-approves navigation, page load waiting, and script evaluation tools
  - Startup timeout: 20 seconds

- **strands-agents**: Memory persistence and multi-agent coordination
  - Provides memory storage and retrieval capabilities
  - Auto-approves memory operations
  - Log level: INFO

### Starting the MCP Servers

The MCP servers are automatically started by the Claude Agent SDK when the agent initializes. Ensure:

1. Chrome is running with remote debugging enabled (see Chrome Setup section)
2. Node.js is installed (for chrome-devtools-mcp)
3. uv/uvx is installed (for strands-agents-mcp-server)

## API Key Setup

The bot requires an Anthropic API key to function. 

1. Get an API key from: https://console.anthropic.com/
2. Set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Configuration

Configuration can be customized via environment variables:

- `CHROME_DEBUG_PORT`: Chrome remote debugging port (default: 9222)
- `SESSION_ID`: Agent session identifier (default: marketplace_scout_v1)
- `MAX_TURNS`: Maximum agent turns per execution (default: 50)
- `MIN_DELAY_SECONDS`: Minimum delay between actions (default: 3)
- `MAX_DELAY_SECONDS`: Maximum delay between actions (default: 7)
- `MAX_PAGES_PER_HOUR`: Hourly page request limit (default: 10)
- `SCROLL_ITERATIONS`: Number of scroll cycles (default: 3)
- `SESSION_BASE_DIR`: Session storage directory (default: ./agent_sessions)

## Usage

```python
from src.config import get_agent_settings

# Get configuration
settings = get_agent_settings()

# Use in your agent implementation
# (Implementation coming in subsequent tasks)
```

## Testing

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run property-based tests:
```bash
pytest tests/property/ -v
```

## Project Structure

```
marketplace-deal-scout/
├── .kiro/
│   ├── mcp.json              # MCP server configuration
│   └── specs/                # Feature specifications
├── src/
│   ├── config/               # Configuration module
│   │   ├── __init__.py
│   │   └── agent_config.py
│   └── __init__.py
├── tests/                    # Test suite
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
└── README.md                 # This file
```

## Legal Considerations

This tool is intended for **personal use only**. Facebook's Terms of Service prohibit commercial scraping and automated access. Users are responsible for:

- Complying with Facebook's Terms of Service
- Respecting rate limits and robots.txt
- Using the tool ethically and legally
- Not using the tool for commercial purposes

## License

This project is for educational and personal use only.
