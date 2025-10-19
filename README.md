# ClaudeGram - Telegram I/O MCP Server

A lightweight MCP server that enables Claude Code to send prompts to Telegram and await responses, facilitating remote decision-making and input gathering while working on long-running tasks.

## Overview

When Claude Code runs long-running development tasks, you may need to step away from your desktop. ClaudeGram bridges that gap by allowing Claude Code to send questions to your Telegram chat and wait for your responses on mobile.

## Features

- **Send prompts to Telegram**: Claude Code can send questions/prompts to your Telegram chat
- **Await responses**: Block until you respond or timeout is exceeded
- **Request tracking**: SQLite database persists all requests and responses
- **Non-blocking status checks**: Query request status without blocking
- **Request history**: Retrieve past requests for debugging and audit
- **Automatic cleanup**: Remove old requests from the database

## Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and chat with [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions to create a new bot
3. Copy the bot token (you'll need this for configuration)
4. Get your user ID by chatting with [@userinfobot](https://t.me/userinfobot)
5. Start a chat with your new bot by searching for it in Telegram

### 2. Install ClaudeGram

```bash
git clone https://github.com/kbhalerao/claudegram.git
cd claudegram
uv sync
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your bot token and chat ID
```

Your `.env` file should look like:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### 4. Configure Claude Code

Add this MCP server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "telegram-io": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/claudegram",
        "run",
        "python",
        "-m",
        "telegram_io_mcp.server"
      ],
      "env": {
        "TELEGRAM_BOT_TOKEN": "your_bot_token_here",
        "TELEGRAM_CHAT_ID": "your_chat_id_here"
      }
    }
  }
}
```

Replace `/absolute/path/to/claudegram` with the actual path to your cloned repository.

### 5. Restart Claude Desktop

After updating the configuration, restart Claude Desktop for the changes to take effect.

## Usage

### Basic Example

In Claude Code, you can now use the Telegram I/O tools:

```python
# During a long-running task, send a question to your phone
result = mcp.send_request(
    "Should we refactor authentication into a separate service? (yes/no)"
)
request_id = result["request_id"]

# Wait for your response (up to 5 minutes)
response_data = mcp.await_response(request_id, timeout=300)
decision = response_data["response"]

# Continue based on your response
if decision.lower() == "yes":
    # proceed with refactoring
    ...
```

### Responding on Telegram

ClaudeGram supports three ways to respond (from easiest to most explicit):

**Method 1: Just send your answer** (Recommended)
When you receive a question like:
```
Should we refactor authentication into a separate service? (yes/no)
```

Just reply with:
```
yes
```

That's it! The system automatically associates your message with the pending request.

**Method 2: Use Telegram's reply feature**
Tap/click "Reply" on the bot's message and type your answer:
```
yes
```

This explicitly links your response to the specific question (useful if you have multiple pending requests).

**Method 3: Prefix format** (Legacy)
Include the request ID in your response:
```
req_abc123xyz: yes
```

This format is still supported for backward compatibility.

**Multi-message responses:**
You can send multiple messages! The system waits for 3 seconds of silence before finalizing your response. For example:
```
Message 1: Here are the pros
Message 2: And here are the cons
Message 3: I recommend option A
```
(wait 3 seconds → all messages combined and sent to Claude)

## MCP Tools

### `send_request`

Send a prompt/question to Telegram and get a unique request ID.

**Parameters**:
- `message` (required): The prompt/question to send
- `timeout` (optional): How long to wait for response in seconds (default: 300)
- `metadata` (optional): Additional context to store in database

**Returns**:
```json
{
  "request_id": "req_abc123xyz",
  "sent_at": "2025-10-19T14:32:15Z",
  "telegram_message": "req_abc123xyz: Need API design decision"
}
```

### `await_response`

Block until a response is received or timeout is exceeded.

**Parameters**:
- `request_id` (required): The request_id from send_request
- `timeout` (optional): Override timeout in seconds
- `poll_interval` (optional): Poll frequency in seconds (default: 2)

**Returns**:
```json
{
  "request_id": "req_abc123xyz",
  "response": "GraphQL",
  "received_at": "2025-10-19T14:35:42Z",
  "response_time_seconds": 187
}
```

### `get_request_status`

Check status of a request without blocking.

**Parameters**:
- `request_id` (required): The request_id to check

**Returns**:
```json
{
  "request_id": "req_abc123xyz",
  "status": "pending|completed",
  "sent_at": "2025-10-19T14:32:15Z",
  "response": "GraphQL",
  "response_at": "2025-10-19T14:35:42Z"
}
```

### `get_request_history`

Retrieve past requests for debugging/audit.

**Parameters**:
- `limit` (optional): Number of recent requests (default: 10)
- `completed_only` (optional): Filter by completion status (default: false)

**Returns**:
```json
{
  "requests": [...]
}
```

### `clear_expired_requests`

Cleanup old requests from database.

**Parameters**:
- `older_than_days` (optional): Delete requests older than N days (default: 7)

**Returns**:
```json
{
  "deleted_count": 5,
  "freed_space_bytes": 2048
}
```

## Development

### Running Tests

```bash
uv run pytest
```

### Running the Server Standalone

```bash
uv run python -m telegram_io_mcp.server
```

## Architecture

```
Claude Code
    ↓
Telegram I/O MCP Server
    ├── Telegram API (via python-telegram-bot)
    ├── SQLite Database (request tracking)
    └── Polling Loop (response retrieval)
    ↓
Telegram Bot/Chat
    ↓
Mobile Device (user)
```

## Security Considerations

- Bot token stored in environment variable only (never hardcoded)
- Chat ID restriction: only accept messages from configured TELEGRAM_CHAT_ID
- SQLite database stored locally (no remote data)
- Request IDs are cryptographically random (UUID4)

## Troubleshooting

### "Request not found" error
- Make sure you're using the correct request_id returned from `send_request`

### "Timeout waiting for response" error
- Check that you're replying in the correct format: `request_id: your response`
- Increase the timeout value if you need more time

### "Failed to send message to Telegram" error
- Verify your `TELEGRAM_BOT_TOKEN` is correct
- Verify your `TELEGRAM_CHAT_ID` is correct
- Make sure you've started a chat with your bot on Telegram

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
