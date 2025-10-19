# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClaudeGram is a lightweight MCP (Model Context Protocol) server that enables Claude Code to send prompts to Telegram and await responses, facilitating remote decision-making during long-running tasks. This allows developers to step away from their desktop while Claude Code waits for mobile input via Telegram.

## Technology Stack

- **Language**: Python 3.13+
- **Package Manager**: uv
- **MCP Framework**: mcp (v1.0+)
- **Telegram**: python-telegram-bot (v20+)
- **Database**: SQLite3 (built-in)

## Environment Configuration

Required environment variables:
```
TELEGRAM_BOT_TOKEN=<bot_token_from_botfather>
TELEGRAM_CHAT_ID=<your_user_id_or_group_chat_id>
REQUEST_TIMEOUT_DEFAULT=300  # seconds
DATABASE_PATH=./telegram_io_cache.db  # optional
```

## Project Structure

Per REQUIREMENTS.md, the expected structure is:
```
src/
└── telegram_io_mcp/
    ├── __init__.py
    ├── server.py           # Main MCP server
    ├── telegram_client.py  # Telegram API wrapper
    ├── database.py         # SQLite manager
    └── models.py           # Data classes
```

## Architecture

### Core Components

1. **MCP Server** (`server.py`): Implements 5 MCP tools for request/response management
2. **Telegram Client** (`telegram_client.py`): Wraps python-telegram-bot for sending/polling
3. **Database Manager** (`database.py`): SQLite persistence for request tracking
4. **Data Models** (`models.py`): Request/response data structures

### Data Flow Pattern

1. Claude Code → `send_request()` → Generate UUID request_id → Send to Telegram
2. Store in SQLite: `{id, message, metadata, sent_at, status: 'pending'}`
3. Claude Code → `await_response(request_id)` → Poll Telegram every 2s
4. User replies on mobile: `request_id: <answer>`
5. Extract response → Update SQLite → Return to Claude Code

## MCP Tools to Implement

1. **send_request**: Send prompt to Telegram, returns request_id
2. **await_response**: Block until response received (polls Telegram)
3. **get_request_status**: Non-blocking status check
4. **get_request_history**: Retrieve past requests for audit
5. **clear_expired_requests**: Cleanup old database entries

See REQUIREMENTS.md lines 104-227 for detailed tool specifications.

## Database Schema

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

## Key Implementation Details

### Request ID Format
- Generate using UUID4: `req_<uuid>`
- Prepend to all Telegram messages for response matching
- Example: `req_abc123xyz: Should we use GraphQL or REST?`

### Response Parsing
- Poll Telegram chat for messages containing request_id
- Extract pattern: `request_id: <response_text>`
- Response text is everything after the colon and space

### Timeout Handling
- Default: 300 seconds (5 minutes)
- Poll interval: 2 seconds (configurable)
- On timeout: Return error without blocking indefinitely

### Security
- Only accept messages from configured `TELEGRAM_CHAT_ID`
- Never hardcode bot token (environment only)
- SQLite database stored locally (no remote sync)

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Run MCP server
uv run python -m telegram_io_mcp.server
```

### Testing
```bash
# Run tests (when implemented)
uv run pytest
```

## Common Development Tasks

When implementing new features:
- All Telegram interactions go through `telegram_client.py`
- All database operations go through `database.py`
- MCP tool handlers live in `server.py`
- Use async/await for Telegram API calls (python-telegram-bot v20 is async)

## Constraints and Scope

**In Scope (MVP)**:
- Text-only messages
- Single chat support
- Blocking await with polling
- SQLite persistence

**Out of Scope**:
- Media/file support
- Multi-chat support
- Message editing/deletion
- Telegram bot commands
- Rich formatting
- Webhooks (polling only)
