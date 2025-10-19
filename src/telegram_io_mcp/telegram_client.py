"""Telegram API wrapper for sending and polling messages."""

import asyncio
import re
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError


class TelegramClient:
    """Wrapper for Telegram Bot API operations."""

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram bot client."""
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, text: str) -> bool:
        """Send a message to the configured chat.

        Args:
            text: The message text to send

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
            return True
        except TelegramError as e:
            print(f"Failed to send message to Telegram: {e}")
            return False

    async def poll_for_response(
        self, request_id: str, timeout: int = 300, poll_interval: int = 2
    ) -> Optional[str]:
        """Poll Telegram chat for a response matching the request_id.

        Args:
            request_id: The unique request ID to match
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between polling attempts

        Returns:
            The response text if found, None if timeout exceeded
        """
        start_time = asyncio.get_event_loop().time()
        last_update_id = None

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                return None

            try:
                # Get updates from Telegram
                updates = await self.bot.get_updates(
                    offset=last_update_id + 1 if last_update_id else None,
                    timeout=poll_interval,
                )

                for update in updates:
                    last_update_id = update.update_id

                    # Check if update has a message from the correct chat
                    if (
                        update.message
                        and update.message.chat_id == int(self.chat_id)
                        and update.message.text
                    ):
                        # Try to extract response matching pattern: "request_id: <response>"
                        response = self._extract_response(
                            update.message.text, request_id
                        )
                        if response:
                            return response

            except TelegramError as e:
                print(f"Error polling Telegram: {e}")
                # Wait before retrying
                await asyncio.sleep(poll_interval)
                continue

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    @staticmethod
    def _extract_response(message_text: str, request_id: str) -> Optional[str]:
        """Extract response from a message matching the request_id pattern.

        Expected format: "request_id: <response text>"

        Args:
            message_text: The full message text
            request_id: The request ID to match

        Returns:
            The response text if pattern matches, None otherwise
        """
        # Pattern: request_id followed by colon and space, then capture everything after
        pattern = rf"^{re.escape(request_id)}:\s*(.+)$"
        match = re.match(pattern, message_text.strip(), re.DOTALL)

        if match:
            return match.group(1).strip()
        return None

    async def close(self):
        """Close the bot connection."""
        # python-telegram-bot v20+ handles cleanup automatically
        pass
