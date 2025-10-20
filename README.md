# ClaudeGram - Telegram I/O MCP Server

A cloud-native MCP server that enables Claude Code to send prompts to Telegram and await responses across multiple devices, facilitating remote decision-making and input gathering while working on long-running tasks.

## 🚀 Quickstart (5 minutes)

**Want to respond to Claude from your phone while away from your desk?**

```bash
# 1. Clone and setup
git clone https://github.com/kbhalerao/claudegram.git
cd claudegram
uv sync

# 2. Create Telegram bot (get token from @BotFather)
# 3. Configure environment
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 4. Install system-wide (works for both CLI and Desktop!)
uv run python setup_claude_desktop.py

# 5. Restart Claude Code/Desktop
# Done! Use /away when you step away, /back when you return
```

**That's it!** Now when you use `/away`, Claude will send questions to your Telegram. Answer from your phone, and Claude continues working!

---

## 📚 Table of Contents

- [🚀 Quickstart](#-quickstart-5-minutes) ← Start here!
- [Overview](#overview)
- [Features](#features)
- [Cloud Deployment Guide](#cloud-deployment-guide) (optional, for multi-device)
- [Usage](#usage)
  - [Slash Commands](#slash-commands-quick-setup)
  - [Dual-Response Workflow](#dual-response-workflow-recommended)
- [MCP Tools](#mcp-tools)
- [Troubleshooting](#troubleshooting) ← Common issues solved!
- [Architecture](#architecture)
- [Development](#development)

---

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

### 1. Create a Telegram Bot (2 minutes)

**Step-by-step with screenshots:**

1. **Open Telegram** and search for `@BotFather` (official bot for creating bots)

2. **Send this command:** `/newbot`

3. **Follow the prompts:**
   - Choose a name (e.g., "My ClaudeGram Bot")
   - Choose a username ending in "bot" (e.g., "my_claudegram_bot")

4. **Copy your bot token** - It looks like this:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
   ⚠️ **Keep this secret!** Don't share it publicly.

5. **Get your Chat ID:**
   - Search for `@userinfobot` in Telegram
   - Send it any message
   - It will reply with your user ID (e.g., `987654321`)

6. **Start your bot:**
   - Search for your bot in Telegram (the username you chose)
   - Click "Start" or send `/start`

✅ **You're done!** Save the bot token and chat ID for the next step.

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

**Create your configuration file:**

```bash
cp .env.example .env
```

**Edit `.env` with your values:**

```bash
# Required: Your Telegram bot credentials from Step 1
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Optional: For cloud mode (multi-device sync)
CLOUDFLARE_WORKER_URL=https://claudegram.<your-subdomain>.workers.dev
CLOUDFLARE_API_KEY=your-secret-api-key
USER_ID=user-your-email@example.com
```

💡 **Tip:** You can use local mode first (just bot token + chat ID) and add cloud sync later!

### 6. Install System-Wide (One Command!)

**This is the magic step that makes `/away` and `/back` work everywhere:**

```bash
uv run python setup_claude_desktop.py
```

**What this does automatically:**

✅ Installs `/away` and `/back` slash commands
✅ Configures permissions (no permission prompts!)
✅ Updates Claude Code CLI config (`~/.claude.json`)
✅ Updates Claude Desktop config (platform-specific)
✅ Creates backups of existing configs

**You'll see output like:**
```
✓ Installed slash commands: away.md, back.md, README.md
✓ Configured permissions: .claude/settings.local.json
✓ Updated configuration file: ~/.claude.json
Setup Complete!
```

**Now restart Claude Code/Desktop** and you're ready to go!

**Manual Setup:**
Add this MCP server to your configuration file:

**Claude Desktop:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Claude Code (CLI):**
- **All platforms**: `~/.claude.json`

```json
{
  "mcpServers": {
    "claudegram": {
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

**Note:** For Claude Code (CLI), you'll need to restart your Claude Code session for changes to take effect. For Claude Desktop, restart the application.

## Usage

### Slash Commands (Quick Setup)

ClaudeGram includes two convenient slash commands for toggling Telegram relay mode:

**`/away` - Enable Telegram Relay**
Use when stepping away from your desk. Claude will:
- Send ALL questions to Telegram automatically
- Wait for your mobile responses
- Send progress updates to your phone

**`/back` - Disable Telegram Relay**
Use when returning to your desk. Claude will:
- Resume normal CLI interaction
- Stop using Telegram relay
- Display full output in the terminal

**Example workflow:**
```bash
# Stepping away from desk
/away
> Build the entire frontend and run all tests. Ask me about any decisions.

# [You respond to questions from your phone via Telegram while away]

# Back at desk
/back
> Show me the build output and test results
```

The slash commands are automatically installed when you run the setup script (`setup_claude_desktop.py`). All ClaudeGram MCP tools are pre-approved, so there are no permission prompts.

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

### 🔧 Setup Issues

**Slash commands `/away` and `/back` not working?**

1. **Check commands are installed:**
   ```bash
   ls .claude/commands/
   # Should show: away.md, back.md, README.md
   ```

2. **Re-run setup if missing:**
   ```bash
   uv run python setup_claude_desktop.py
   ```

3. **Restart Claude:**
   - Claude Code CLI: Exit and restart terminal session
   - Claude Desktop: Quit app completely and reopen

4. **Check config files exist:**
   - CLI: `cat ~/.claude.json` (should have `mcpServers.claudegram`)
   - Desktop: Check platform-specific config location

**Permission prompts appearing?**

Check `.claude/settings.local.json` has:
```json
{
  "permissions": {
    "allow": [
      "mcp__claudegram__send_request",
      "mcp__claudegram__await_response",
      ...
    ]
  }
}
```

If missing, re-run: `uv run python setup_claude_desktop.py`

**MCP server not starting?**

1. **Check environment variables:**
   ```bash
   source .env  # or 'set -a; source .env; set +a' on Linux
   echo $TELEGRAM_BOT_TOKEN  # Should show your token
   ```

2. **Test MCP server manually:**
   ```bash
   uv run python -m telegram_io_mcp.server
   # Should start without errors
   ```

3. **Check logs:**
   - Claude Code: Look for errors in terminal output
   - Claude Desktop: Check Developer Tools console (Help → Toggle Developer Tools)

### 📱 Telegram Issues

**"Failed to send message to Telegram" error**

1. **Verify credentials:**
   ```bash
   # Test bot token
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   # Should return bot info
   ```

2. **Verify chat started:**
   - Search for your bot in Telegram
   - Make sure you sent `/start` to the bot

3. **Check .env file:**
   - `TELEGRAM_BOT_TOKEN` format: `123456789:ABCdef...`
   - `TELEGRAM_CHAT_ID` format: `987654321` (just numbers)

**Messages not being received?**

- Check bot is online (search for it in Telegram)
- Verify you're using the correct bot username
- Try sending `/start` to the bot again

**Can't find Chat ID?**

Use `@userinfobot`:
1. Search `@userinfobot` in Telegram
2. Send any message
3. Copy the ID it gives you

### 🔄 Runtime Issues

**"Request not found" error**

- Make sure you're using the correct `request_id` returned from `send_request`
- Check request hasn't expired (default 10 minutes)

**"Timeout waiting for response" error**

- Increase timeout: `send_request(message, timeout=600)`
- Check you responded in Telegram (any message works!)
- Try the request again

**Responses not detected?**

- Just send your answer as a normal message (no special format needed!)
- Or use Telegram's "Reply" feature on the bot's message
- Legacy format still works: `request_id: your answer`

### 💻 Platform-Specific

**macOS:** Config at `~/Library/Application Support/Claude/`
**Windows:** Config at `%APPDATA%\Claude\`
**Linux:** Config at `~/.config/Claude/`

**Still having issues?**

1. Check existing issues: https://github.com/kbhalerao/claudegram/issues
2. Enable debug logging: Set `LOG_LEVEL=DEBUG` in `.env`
3. Open a new issue with:
   - Your OS and Claude version
   - Output of `uv run python setup_claude_desktop.py`
   - Any error messages from logs

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
