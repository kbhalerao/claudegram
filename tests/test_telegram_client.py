"""Tests for Telegram client operations."""

import os
import asyncio
from datetime import datetime

import pytest
from dotenv import load_dotenv

from telegram_io_mcp.telegram_client import TelegramClient

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Skip tests if credentials are not configured
pytestmark = pytest.mark.skipif(
    not BOT_TOKEN or not CHAT_ID,
    reason="TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
)


@pytest.fixture
def telegram_client():
    """Create a Telegram client for testing."""
    return TelegramClient(BOT_TOKEN, CHAT_ID)


async def test_send_message(telegram_client):
    """Test sending a message to Telegram."""
    message = f"Test message from ClaudeGram - {datetime.now().isoformat()}"
    success = await telegram_client.send_message(message)

    assert success is True
    print(f"\n✓ Message sent successfully: {message}")
    print("  Check your Telegram chat to verify!")


async def test_send_request_with_id(telegram_client):
    """Test sending a message with a request ID prefix."""
    request_id = f"req_test_{datetime.now().timestamp()}"
    message = f"{request_id}: This is a test question"

    success = await telegram_client.send_message(message)

    assert success is True
    print(f"\n✓ Request sent with ID: {request_id}")
    print("  Check your Telegram chat to verify!")


async def test_extract_response():
    """Test extracting response from message text."""
    request_id = "req_abc123"

    # Valid response format
    message = f"{request_id}: This is my answer"
    response = TelegramClient._extract_response(message, request_id)
    assert response == "This is my answer"

    # Response with extra whitespace
    message = f"{request_id}:   Answer with spaces   "
    response = TelegramClient._extract_response(message, request_id)
    assert response == "Answer with spaces"

    # Multi-line response
    message = f"{request_id}: Line 1\nLine 2\nLine 3"
    response = TelegramClient._extract_response(message, request_id)
    assert response == "Line 1\nLine 2\nLine 3"

    # Wrong request ID
    message = "req_different: Some answer"
    response = TelegramClient._extract_response(message, request_id)
    assert response is None

    # Missing colon
    message = f"{request_id} No colon here"
    response = TelegramClient._extract_response(message, request_id)
    assert response is None


async def test_poll_for_response_with_manual_reply(telegram_client):
    """Test polling for a response (requires manual reply in Telegram).

    This is an interactive test - it will send a message and wait for you to reply.
    """
    request_id = f"req_interactive_{int(datetime.now().timestamp())}"
    question = f"{request_id}: Please reply 'yes' to this message within 60 seconds"

    # Send the question
    success = await telegram_client.send_message(question)
    assert success is True

    print(f"\n{'='*60}")
    print(f"INTERACTIVE TEST: Please reply to the message in Telegram!")
    print(f"{'='*60}")
    print(f"Request ID: {request_id}")
    print(f"Expected format: {request_id}: yes")
    print(f"Waiting for up to 60 seconds...")
    print(f"{'='*60}\n")

    # Poll for response with 60 second timeout
    response = await telegram_client.poll_for_response(
        request_id=request_id, timeout=60, poll_interval=2
    )

    if response:
        print(f"\n✓ Response received: {response}")
        assert response is not None
    else:
        print("\n✗ No response received within timeout")
        pytest.fail("No response received - did you reply in Telegram?")


async def test_poll_for_response_timeout(telegram_client):
    """Test that polling times out correctly when no response is received."""
    request_id = f"req_timeout_{int(datetime.now().timestamp())}"

    # Poll for a response that will never come (short timeout)
    response = await telegram_client.poll_for_response(
        request_id=request_id, timeout=5, poll_interval=1
    )

    assert response is None
    print(f"\n✓ Timeout handled correctly (no response in 5 seconds)")
