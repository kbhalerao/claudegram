"""Main MCP server for Telegram I/O."""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool, TextContent

from .database import DatabaseManager
from .models import Request, SendRequestResult, AwaitResponseResult
from .telegram_client import TelegramClient
from .cloud_client import CloudClient, get_cloud_client

# Load environment variables
load_dotenv()

# Configuration
DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "local").lower()
DEFAULT_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_DEFAULT", "300"))

# Initialize components based on deployment mode
db: Optional[DatabaseManager] = None
telegram: Optional[TelegramClient] = None
cloud: Optional[CloudClient] = None

if DEPLOYMENT_MODE == "cloud":
    # Cloud mode: use Cloudflare Worker backend
    cloud = get_cloud_client()
    if not cloud:
        raise ValueError(
            "Cloud mode requires CLOUDFLARE_WORKER_URL, CLOUDFLARE_API_KEY, and USER_ID environment variables"
        )
else:
    # Local mode: use local database and Telegram client
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./telegram_io_cache.db")

    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required for local mode")
    if not CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID environment variable is required for local mode")

    db = DatabaseManager(DATABASE_PATH)
    telegram = TelegramClient(BOT_TOKEN, CHAT_ID)

app = Server("telegram-io-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="send_request",
            description="Send a prompt/question to Telegram and get a unique request ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The prompt/question to send to Telegram",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "How long to wait for response in seconds (default: 300)",
                        "default": DEFAULT_TIMEOUT,
                    },
                    "metadata": {
                        "type": "string",
                        "description": "Additional context to store in database (optional)",
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="await_response",
            description="Block until a response is received for a request or timeout is exceeded",
            inputSchema={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "The request_id from send_request",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Override timeout in seconds (default: from original request)",
                    },
                    "poll_interval": {
                        "type": "integer",
                        "description": "Poll frequency in seconds (default: 2)",
                        "default": 2,
                    },
                },
                "required": ["request_id"],
            },
        ),
        Tool(
            name="submit_response",
            description="Submit a response directly (for when user responds in chat instead of Telegram)",
            inputSchema={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "The request_id to respond to",
                    },
                    "response": {
                        "type": "string",
                        "description": "The user's response text",
                    },
                },
                "required": ["request_id", "response"],
            },
        ),
        Tool(
            name="get_request_status",
            description="Check status of a request without blocking",
            inputSchema={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "The request_id to check",
                    },
                },
                "required": ["request_id"],
            },
        ),
        Tool(
            name="get_request_history",
            description="Retrieve past requests for debugging/audit",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent requests (default: 10)",
                        "default": 10,
                    },
                    "completed_only": {
                        "type": "boolean",
                        "description": "Filter by completion status (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="clear_expired_requests",
            description="Cleanup old requests from database",
            inputSchema={
                "type": "object",
                "properties": {
                    "older_than_days": {
                        "type": "integer",
                        "description": "Delete requests older than N days (default: 7)",
                        "default": 7,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "send_request":
            result = await handle_send_request(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "await_response":
            result = await handle_await_response(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "submit_response":
            result = await handle_submit_response(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_request_status":
            result = await handle_get_request_status(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_request_history":
            result = await handle_get_request_history(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "clear_expired_requests":
            result = await handle_clear_expired_requests(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_response = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def handle_send_request(arguments: dict) -> dict:
    """Handle send_request tool call."""
    message = arguments["message"]
    timeout = arguments.get("timeout", DEFAULT_TIMEOUT)
    metadata = arguments.get("metadata")

    if DEPLOYMENT_MODE == "cloud":
        # Cloud mode: use Cloudflare Worker API
        result = await cloud.create_request(message, timeout, metadata)
        return result.to_dict()
    else:
        # Local mode: use local database and Telegram client
        # Generate unique request ID
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        # Create request object
        request = Request(
            id=request_id,
            message=message,
            sent_at=datetime.now(),
            timeout_seconds=timeout,
            metadata=metadata,
            status="pending",
        )

        # Store in database
        db.create_request(request)

        # Send to Telegram (just the message, no prefix needed!)
        telegram_message_id = await telegram.send_message(message)

        if not telegram_message_id:
            raise Exception("Failed to send message to Telegram")

        # Update request with Telegram message ID
        db.update_telegram_message_id(request_id, telegram_message_id)

        # Return result
        result = SendRequestResult(
            request_id=request_id,
            sent_at=request.sent_at,
            telegram_message=message,
        )

        return result.to_dict()


async def handle_await_response(arguments: dict) -> dict:
    """Handle await_response tool call."""
    request_id = arguments["request_id"]
    poll_interval = arguments.get("poll_interval", 2)

    if DEPLOYMENT_MODE == "cloud":
        # Cloud mode: poll via Cloudflare Worker API
        timeout = arguments.get("timeout", DEFAULT_TIMEOUT)

        # Poll for response
        start_time = datetime.now()
        while True:
            # Check request status
            request = await cloud.get_request(request_id)
            if not request:
                raise ValueError(f"Request not found: {request_id}")

            # Check if completed
            if request.status == "completed" and request.response:
                response_time = int((request.response_at - request.sent_at).total_seconds())
                result = AwaitResponseResult(
                    request_id=request_id,
                    response=request.response,
                    received_at=request.response_at,
                    response_time_seconds=response_time,
                )
                return result.to_dict()

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Waited {timeout}s for response to {request_id}, no reply received"
                )

            # Wait before next poll
            await asyncio.sleep(poll_interval)
    else:
        # Local mode: use local database and Telegram client
        # Get request from database
        request = db.get_request(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        # Check if already completed (user may have submitted via chat)
        if request.status == "completed" and request.response:
            response_time = int((request.response_at - request.sent_at).total_seconds())
            result = AwaitResponseResult(
                request_id=request_id,
                response=request.response,
                received_at=request.response_at,
                response_time_seconds=response_time,
            )
            return result.to_dict()

        # Use override timeout if provided, otherwise use original timeout
        timeout = arguments.get("timeout", request.timeout_seconds)

        # Poll for response (pass telegram_message_id for reply detection)
        # This also checks database on each iteration for submit_response
        response_text = await telegram.poll_for_response(
            request_id=request_id,
            timeout=timeout,
            poll_interval=poll_interval,
            telegram_message_id=request.telegram_message_id
        )

        if response_text is None:
            raise TimeoutError(
                f"Waited {timeout}s for response to {request_id}, no reply received"
            )

        # Update database with response (if not already updated by submit_response)
        request_updated = db.get_request(request_id)
        if request_updated.status != "completed":
            response_at = datetime.now()
            db.update_response(request_id, response_text, response_at)
        else:
            response_at = request_updated.response_at
            response_text = request_updated.response

        # Calculate response time
        response_time = int((response_at - request.sent_at).total_seconds())

        # Return result
        result = AwaitResponseResult(
            request_id=request_id,
            response=response_text,
            received_at=response_at,
            response_time_seconds=response_time,
        )

        return result.to_dict()


async def handle_submit_response(arguments: dict) -> dict:
    """Handle submit_response tool call - user responds directly in chat."""
    request_id = arguments["request_id"]
    response_text = arguments["response"]

    if DEPLOYMENT_MODE == "cloud":
        # Cloud mode: submit via Cloudflare Worker API
        result = await cloud.submit_response(request_id, response_text)
        return result.to_dict()
    else:
        # Local mode: use local database
        # Get request from database
        request = db.get_request(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        # Check if already completed
        if request.status == "completed":
            raise ValueError(f"Request {request_id} already has a response: {request.response}")

        # Update database with response
        response_at = datetime.now()
        db.update_response(request_id, response_text, response_at)

        # Calculate response time
        response_time = int((response_at - request.sent_at).total_seconds())

        # Return result
        result = AwaitResponseResult(
            request_id=request_id,
            response=response_text,
            received_at=response_at,
            response_time_seconds=response_time,
        )

        return result.to_dict()


async def handle_get_request_status(arguments: dict) -> dict:
    """Handle get_request_status tool call."""
    request_id = arguments["request_id"]

    if DEPLOYMENT_MODE == "cloud":
        # Cloud mode: get via Cloudflare Worker API
        request = await cloud.get_request(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")
    else:
        # Local mode: get from local database
        request = db.get_request(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

    # Return status
    return {
        "request_id": request.id,
        "status": request.status,
        "sent_at": request.sent_at.isoformat(),
        "response": request.response,
        "response_at": request.response_at.isoformat() if request.response_at else None,
    }


async def handle_get_request_history(arguments: dict) -> dict:
    """Handle get_request_history tool call."""
    limit = arguments.get("limit", 10)
    completed_only = arguments.get("completed_only", False)

    if DEPLOYMENT_MODE == "cloud":
        # Cloud mode: get via Cloudflare Worker API
        requests = await cloud.get_recent_requests(limit=limit, completed_only=completed_only)
    else:
        # Local mode: get from local database
        requests = db.get_recent_requests(limit=limit, completed_only=completed_only)

    # Convert to dict format
    requests_data = []
    for req in requests:
        req_dict = req.to_dict()
        # Add response_time_seconds if available
        if req.response_time_seconds is not None:
            req_dict["response_time_seconds"] = req.response_time_seconds
        requests_data.append(req_dict)

    return {"requests": requests_data}


async def handle_clear_expired_requests(arguments: dict) -> dict:
    """Handle clear_expired_requests tool call."""
    older_than_days = arguments.get("older_than_days", 7)

    if DEPLOYMENT_MODE == "cloud":
        # Cloud mode: delete via Cloudflare Worker API
        deleted_count, freed_space = await cloud.delete_old_requests(older_than_days)
    else:
        # Local mode: delete from local database
        deleted_count, freed_space = db.delete_old_requests(older_than_days)

    return {"deleted_count": deleted_count, "freed_space_bytes": freed_space}


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
