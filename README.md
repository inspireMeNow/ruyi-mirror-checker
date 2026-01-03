# Ruyi Mirror Checker

A monitoring service for checking the availability of mirror URLs and board images in the Ruyi package.  The service provides both a FastAPI and a Telegram Bot interface for querying mirror status.

## Architecture

The project consists of several components:

- **checker/api.py**: FastAPI web server and Telegram bot integration
- **checker/checker.py**: Core URL checking logic with support for mirror:// URLs
- **checker/config.py**: Configuration loader for TOML manifests
- **checker/generate.py**: Status JSON generator script

## Installation

### Prerequisites

- Python 3.11+
- uv package manager

### Install Dependencies

```bash
uv sync
```

Required packages:
- fastapi
- uvicorn
- python-telegram-bot
- httpx
- requests

## Usage

### 1. FastAPI Server

Start the FastAPI server to provide REST API endpoints:

```bash
uv run uvicorn checker.api:app --host 0.0.0.0 --port 8000
```

#### Environment Variables

- `RESULTS_URL`: URL to fetch pre-generated status JSON (default: [GitHub raw URL](https://raw.githubusercontent.com/inspireMeNow/ruyi-mirror-checker/refs/heads/hidden/status.json))
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required for bot functionality)

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service information |
| `/board-images` | GET | List all available boards |
| `/board-images/{board_name}` | GET | Get detailed status for a specific board |
| `/health` | GET | Health check endpoint |
| `/api/webhook` | POST | Telegram webhook endpoint |

#### Example API Usage

```bash
# List all boards
curl http://localhost:8000/board-images

# Get specific board details
curl http://localhost:8000/board-images/arduino-milkv-duo-sd

# Health check
curl http://localhost:8000/health
```

### 2. Telegram Bot

The Telegram bot provides an interactive interface for querying board availability. 

#### Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Set the token as an environment variable: 

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token-here"
```

4. Configure webhook (for production):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/api/webhook"}'
```

#### Bot Commands

- `/start` or `/help` - Show available commands and help information
- `/boards` - List all available boards
- `/board <name>` - Check availability status for a specific board


### 3. Generate Status JSON

Run the generator script to create a status. json file:

```bash
export REPO_ROOT=/path/to/ruyi-packages
uv run python -m checker.generate
```

This will: 
1. Load board configurations from `packages-index/manifests/board-image/`
2. Check all distfile URLs
3. Generate `status.json` with availability results


## Links

- Live API: https://ruyi-checker.inspiremenow.top
