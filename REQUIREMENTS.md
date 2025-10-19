# Telegram I/O MCP Server - Product Requirements Document

## Overview

A lightweight MCP server that enables Claude Code to send prompts to Telegram and await responses, facilitating remote decision-making and input gathering while working on long-running tasks.

## Problem Statement

When Claude Code runs long-running development tasks, the developer may need to step away from their desktop. Currently, there's no built-in way to:
1. Notify the developer on their mobile device that a decision is needed
2. Receive the response back into Claude Code
3. Resume execution with that response

This MCP server bridges that gap using Telegram as a secure, real-time communication channel.

## Goals

- Enable Claude Code to send prompts/questions to Telegram and receive responses
- Support both synchronous (await) and asynchronous message patterns
- Provide timeout handling and graceful degradation
- Maintain a request history for debugging and audit purposes
- Require minimal setup (just a Telegram bot token)

## Scope

### In Scope
- Send text messages to Telegram with unique request IDs
- Poll for and retrieve responses from a Telegram chat
- Blocking `await_response` function with timeout support
- SQLite database for request tracking
- Environment variable configuration
- Error handling and logging

### Out of Scope
- Media/file support (text only for MVP)
- Multi-chat support (single designated chat per server instance)
- Message editing or deletion
- Telegram bot commands or handlers
- Rich formatting beyond basic text

## Architecture

### Components

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

### Data Flow

1. Claude Code calls MCP tool: `send_request("Need API design decision", timeout=300)`
2. MCP server generates unique `request_id`, sends to Telegram with prefix
3. MCP server stores request in SQLite with timestamp
4. Claude Code calls: `response = await_response(request_id, timeout=300)`
5. MCP server polls Telegram chat for messages containing `request_id`
6. User replies on phone: `request_id: GraphQL`
7. MCP server extracts response, updates database, returns to Claude Code
8. Claude Code resumes with the response

## Technical Requirements

### Technology Stack
- **Language**: Python 3.10+
- **MCP Framework**: mcp (v1.0+)
- **Telegram**: python-telegram-bot (v20+)
- **Database**: SQLite3 (built-in)
- **Package Manager**: uv

### Environment Variables
```
TELEGRAM_BOT_TOKEN=<bot_token_from_botfather>
TELEGRAM_CHAT_ID=<your_user_id_or_group_chat_id>
REQUEST_TIMEOUT_DEFAULT=300  # seconds
DATABASE_PATH=./telegram_io_cache.db  # optional
```

### Project Structure
```
telegram-io-mcp/
├── src/
│   └── telegram_io_mcp/
│       ├── __init__.py
│       ├── server.py              # Main MCP server
│       ├── telegram_client.py      # Telegram API wrapper
│       ├── database.py             # SQLite manager
│       └── models.py               # Data classes
├── pyproject.toml
├── README.md
├── .env.example
└── setup.md
```

## MCP Tools Specification

### Tool 1: `send_request`

**Purpose**: Send a prompt/question to Telegram and get a unique request ID

**Input Parameters**:
- `message` (string, required): The prompt/question to send
- `timeout` (integer, optional, default=300): How long to wait for response in seconds
- `metadata` (string, optional): Additional context to store in database

**Returns**:
```json
{
  "request_id": "req_abc123xyz",
  "sent_at": "2025-10-19T14:32:15Z",
  "telegram_message": "req_abc123xyz: Need API design decision"
}
```

**Behavior**:
- Generate UUID-based request_id
- Prepend request_id to message before sending to Telegram
- Store request in database with timestamp and metadata
- Return request_id for later polling

**Example Message Sent to Telegram**:
```
req_abc123xyz: Need API design decision - REST or GraphQL?
```

---

### Tool 2: `await_response`

**Purpose**: Block until a response is received or timeout is exceeded

**Input Parameters**:
- `request_id` (string, required): The request_id from send_request
- `timeout` (integer, optional, default=300): Override timeout in seconds
- `poll_interval` (integer, optional, default=2): Poll frequency in seconds

**Returns**:
```json
{
  "request_id": "req_abc123xyz",
  "response": "GraphQL",
  "received_at": "2025-10-19T14:35:42Z",
  "response_time_seconds": 187
}
```

**Error Handling**:
- If request_id not found: return error "Request not found"
- If timeout exceeded: return error "Timeout waiting for response"
- If Telegram API fails: return error "Failed to fetch messages" with retry suggestion

**Behavior**:
- Poll Telegram chat every `poll_interval` seconds for new messages
- Extract responses with pattern: `request_id: <response_text>`
- Mark request as completed in database
- Return response immediately upon match or raise timeout error

---

### Tool 3: `get_request_status`

**Purpose**: Check status of a request without blocking

**Input Parameters**:
- `request_id` (string, required): The request_id

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

---

### Tool 4: `get_request_history`

**Purpose**: Retrieve past requests for debugging/audit

**Input Parameters**:
- `limit` (integer, optional, default=10): Number of recent requests
- `completed_only` (boolean, optional, default=false): Filter by completion status

**Returns**:
```json
{
  "requests": [
    {
      "request_id": "req_abc123xyz",
      "message": "Need API design decision",
      "status": "completed",
      "sent_at": "2025-10-19T14:32:15Z",
      "response": "GraphQL",
      "response_at": "2025-10-19T14:35:42Z",
      "response_time_seconds": 187
    }
  ]
}
```

---

### Tool 5: `clear_expired_requests`

**Purpose**: Cleanup old requests from database

**Input Parameters**:
- `older_than_days` (integer, optional, default=7): Delete requests older than N days

**Returns**:
```json
{
  "deleted_count": 5,
  "freed_space_bytes": 2048
}
```

## Database Schema

### requests table
```sql
CREATE TABLE requests (
  id TEXT PRIMARY KEY,
  message TEXT NOT NULL,
  metadata TEXT,
  sent_at TIMESTAMP NOT NULL,
  timeout_seconds INTEGER DEFAULT 300,
  response TEXT,
  response_at TIMESTAMP,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Example in Claude Code

```python
# During a long-running task, need user input
print("Analyzing code structure...")

# Send request to user's phone via Telegram
result = mcp.send_request(
    "Should we refactor authentication into a separate service? (yes/no)"
)
request_id = result["request_id"]

# Continue with other work while waiting
print("Processing remaining files...")

# Wait for response (up to 5 minutes)
response_data = mcp.await_response(
    request_id,
    timeout=300
)

decision = response_data["response"]
print(f"User decision: {decision}")

# Resume main task with user's input
if decision.lower() == "yes":
    refactor_auth_service()
else:
    continue_with_current_structure()
```

## Error Handling

### Client-Side (Claude Code Perspective)
```
TimeoutError: "Waited 300s for response to req_abc123xyz, no reply received"
RequestNotFound: "Request req_invalid does not exist"
TelegramError: "Failed to fetch messages from Telegram (check token/chat_id)"
```

### Server-Side Logging
- All requests/responses logged to file with timestamps
- Failed requests logged with retry suggestions
- Telegram API errors logged with codes

## Performance Considerations

- Poll interval: 2 seconds (default, configurable)
- Database cleanup: Manual via tool
- Max request lifetime: 24 hours (can be configured)
- Single-threaded, blocking await (intentional for Claude Code)

## Security Considerations

- Bot token stored in environment variable only (never hardcoded)
- Chat ID restriction: only accept messages from configured TELEGRAM_CHAT_ID
- SQLite database stored locally (no remote data)
- No message history sent to external services
- Request IDs are cryptographically random (UUID4)

## Setup Instructions (for README)

1. **Create Telegram Bot**
   - Chat with @BotFather on Telegram
   - Create new bot, copy token
   - Get your user ID: Chat @userinfobot

2. **Install MCP Server**
   ```bash
   git clone https://github.com/your-org/telegram-io-mcp.git
   cd telegram-io-mcp
   uv sync
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and chat ID
   ```

4. **Configure Claude Code**
   - Add to Claude Desktop config or Claude Code environment
   - MCP server starts automatically

5. **Test**
   ```bash
   uv run python -m telegram_io_mcp.server
   ```

## Success Criteria

- ✅ Can send a request via MCP tool in under 1 second
- ✅ Can receive response via await_response within network latency
- ✅ Handles timeouts gracefully without hanging Claude Code
- ✅ Database persists state across server restarts
- ✅ Setup requires only 2 environment variables
- ✅ Clear error messages guide user troubleshooting
- ✅ No external dependencies beyond python-telegram-bot and mcp

## Future Enhancements (Out of Scope for MVP)

- Multiple chat support
- Message buttons/quick replies for structured responses
- Media attachments
- Request expiration policies
- Webhook-based message delivery instead of polling
- Integration with other messaging platforms (Signal, Discord, etc.)
- Request priority levels
- Analytics dashboard

## Deliverables

1. Complete Python MCP server implementation
2. SQLite schema and migrations
3. Comprehensive README with examples
4. Setup guide (.env.example, setup.md)
5. Integration guide for Claude Code users
6. Error handling and logging framework
7. Test suite (basic unit tests)
8. GitHub repository with CI/CD ready structure