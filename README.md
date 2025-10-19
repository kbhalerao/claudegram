# ClaudeGram - Telegram I/O MCP Server

A cloud-native MCP server that enables Claude Code to send prompts to Telegram and await responses across multiple devices, facilitating remote decision-making and input gathering while working on long-running tasks.

## Overview

When Claude Code runs long-running development tasks, you may need to step away from your desktop or switch devices. ClaudeGram bridges that gap by:
- Sending questions to your Telegram chat (respond on mobile)
- OR responding directly in Claude chat (respond at desk)
- Syncing state across all your devices via Cloudflare

## Features

- **Multi-device sync**: Use ClaudeGram across laptop, desktop, and mobile seamlessly
- **Cloud-native**: Powered by Cloudflare Workers + Durable Objects + D1
- **Dual-response**: Respond via Telegram OR Claude chat - whichever is convenient
- **Real-time**: Instant updates via webhooks (no polling lag)
- **Multi-message support**: Send multiple messages, system waits for silence
- **Request tracking**: D1 database persists all requests and responses
- **Automatic cleanup**: Remove old requests from the database

## Architecture

```
Claude Code (Laptop) ──┐
Claude Code (Desktop) ─┼──> Cloudflare Worker ──> Durable Object (per user)
Claude Desktop        ─┘          │                     │
                                  │                     ├─> D1 Database
                                  │                     └─> Telegram Webhook
                                  │
                            Telegram Bot
```

**Key Components:**
- **Local MCP Server** (on each device): Thin API client, communicates via stdio
- **Cloudflare Worker**: Routes requests to user's Durable Object
- **Durable Object**: One instance per user, manages all state and coordination
- **D1 Database**: Cloud SQLite database for persistent storage
- **Telegram Webhook**: Real-time message delivery (no polling!)

## Deployment Modes

ClaudeGram supports two deployment modes:

### Local Mode (Simple, Single Device)
- Local SQLite database
- Direct Telegram polling
- Good for: Single device, testing, offline use

### Cloud Mode (Recommended, Multi-Device)
- Cloudflare Workers + Durable Objects + D1
- Telegram webhooks (real-time)
- Good for: Multiple devices, production use, team collaboration

This guide covers **Cloud Mode** deployment. For local mode, see [LOCAL_SETUP.md](./LOCAL_SETUP.md).

## Cloud Deployment Guide

### 1. Create a Telegram Bot

1. Open Telegram and chat with [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions to create a new bot
3. Copy the bot token (you'll need this for configuration)
4. Get your user ID by chatting with [@userinfobot](https://t.me/userinfobot)
5. Start a chat with your new bot by searching for it in Telegram

### 2. Deploy Cloudflare Backend

```bash
git clone https://github.com/kbhalerao/claudegram.git
cd claudegram/cloudflare

# Install Wrangler (Cloudflare CLI)
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create D1 database
wrangler d1 create claudegram-db

# Deploy Worker + Durable Object
wrangler deploy
```

This creates:
- Cloudflare Worker at `https://claudegram.<your-subdomain>.workers.dev`
- D1 database for persistent storage
- Durable Object class for user sessions

### 3. Configure Telegram Webhook

```bash
# Set webhook to point to your Worker
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://claudegram.<your-subdomain>.workers.dev/telegram/webhook"
```

### 4. Install MCP Server (on each device)

```bash
cd claudegram
uv sync --extra dev
```

### 5. Configure Environment (on each device)

```bash
cp .env.example .env
# Edit .env with your settings
```

Your `.env` file should contain:
```
# Cloudflare Worker URL
CLOUDFLARE_WORKER_URL=https://claudegram.<your-subdomain>.workers.dev

# API Key (get from Cloudflare dashboard or generate)
CLOUDFLARE_API_KEY=your-secret-api-key

# User ID (unique identifier for you)
USER_ID=user-your-email@example.com

# Telegram credentials (for Worker)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

### 6. Configure Claude Code (on each device)

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

### Dual-Response Workflow (Recommended)

ClaudeGram supports responding from **either Telegram OR the Claude chat** - whichever is more convenient:

**In Claude Chat:**
```
You: Use ClaudeGram to ask me which API style to use

Claude: I've sent "Which API style should we use: REST or GraphQL?" to your
        Telegram (@kdb_claudegram_bot). You can respond there, or just tell
        me your answer here.

You: Use GraphQL

Claude: [calls submit_response] Got it! Proceeding with GraphQL...
```

**Or in Telegram:**
```
Telegram Bot: Which API style should we use: REST or GraphQL?
You: GraphQL
Claude: [polling detects response] Got it! Proceeding with GraphQL...
```

### Example Integration

```python
# Claude sends the question
result = send_request("Which API style should we use: REST or GraphQL?")
request_id = result["request_id"]

# Claude tells you about both response options
print(f"Question sent to Telegram. You can respond there, or tell me here.")

# If you respond in chat:
# Claude detects your message and calls: submit_response(request_id, "GraphQL")

# If you respond in Telegram:
# Claude calls: await_response(request_id)
# which polls Telegram and returns your response
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

### `submit_response`

Submit a response directly when the user responds in the Claude chat instead of Telegram.

**Parameters**:
- `request_id` (required): The request_id to respond to
- `response` (required): The user's response text

**Returns**:
```json
{
  "request_id": "req_abc123xyz",
  "response": "GraphQL",
  "received_at": "2025-10-19T14:33:27Z",
  "response_time_seconds": 72
}
```

**Usage**:
This tool allows Claude to submit responses on behalf of the user when they respond directly in the chat window instead of going to Telegram. This provides flexibility - respond from wherever is convenient!

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
