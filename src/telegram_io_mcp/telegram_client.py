"""Telegram API wrapper for sending and polling messages."""

import asyncio
import logging
import re
import sys
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

# Set up logging to stderr so it appears in MCP logs
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class TelegramClient:
    """Wrapper for Telegram Bot API operations."""

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram bot client."""
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, text: str) -> Optional[int]:
        """Send a message to the configured chat.

        Args:
            text: The message text to send

        Returns:
            The Telegram message ID if successful, None otherwise
        """
        try:
            message = await self.bot.send_message(chat_id=self.chat_id, text=text)
            logger.info(f"Message sent successfully. Message ID: {message.message_id}")
            return message.message_id
        except TelegramError as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return None

    async def poll_for_response(
        self, request_id: str, timeout: int = 300, poll_interval: int = 2,
        telegram_message_id: Optional[int] = None,
        collection_window: int = 3
    ) -> Optional[str]:
        """Poll Telegram chat for a response.

        Supports three methods for matching responses (in priority order):
        1. Reply feature: User replies to the bot's message
        2. Prefix pattern: Message starting with "request_id: <response>"
        3. Any message: Any message sent after the request (most natural)

        Multi-message support: After receiving the first message, continues
        collecting messages until there's a silence (no new messages) for
        `collection_window` seconds. This allows you to send multiple messages
        and the system waits until you're done typing.

        Args:
            request_id: The unique request ID to match
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between polling attempts
            telegram_message_id: Optional Telegram message ID to match replies against
            collection_window: Seconds of silence required to finalize multi-message response

        Returns:
            The response text (combined if multiple messages), None if timeout exceeded
        """
        start_time = asyncio.get_event_loop().time()
        last_update_id = None
        poll_count = 0

        collected_messages = []
        last_message_time = None  # Time of the most recent message

        logger.info(f"Starting to poll for response to request_id: {request_id}")
        if telegram_message_id:
            logger.info(f"Watching for: 1) Replies to message {telegram_message_id}, 2) Prefix pattern, 3) Any message")
        else:
            logger.info(f"Watching for: 1) Prefix pattern, 2) Any message")
        logger.info(f"Timeout: {timeout}s, Poll interval: {poll_interval}s")
        logger.info(f"Multi-message: Will collect until {collection_window}s of silence")
        logger.info(f"Expecting messages from chat_id: {self.chat_id}")

        while True:
            # Check global timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                logger.warning(f"Timeout reached after {elapsed:.1f}s, no response found")
                return None

            # Check silence window - if we've received messages and there's been silence, return
            if last_message_time:
                silence_duration = asyncio.get_event_loop().time() - last_message_time
                if silence_duration >= collection_window:
                    combined_response = "\n".join(collected_messages)
                    logger.info(f"✓ Silence detected ({silence_duration:.1f}s). Returning {len(collected_messages)} message(s)")
                    return combined_response

            poll_count += 1

            try:
                # Get updates from Telegram
                updates = await self.bot.get_updates(
                    offset=last_update_id + 1 if last_update_id else None,
                    timeout=poll_interval,
                )

                if updates:
                    logger.debug(f"Poll #{poll_count}: Received {len(updates)} update(s)")
                else:
                    logger.debug(f"Poll #{poll_count}: No new updates")

                for update in updates:
                    last_update_id = update.update_id

                    # Check if update has a message from the correct chat
                    if update.message and update.message.text:
                        msg = update.message
                        msg_chat_id = str(msg.chat_id)
                        msg_text = msg.text

                        logger.debug(f"Update {update.update_id}: chat_id={msg_chat_id}, text='{msg_text[:100]}'")

                        if msg_chat_id == str(self.chat_id):
                            logger.info(f"Message from correct chat! Text: '{msg_text}'")

                            # Method 1 (Highest Priority): Check if this is a reply to our message
                            if telegram_message_id and msg.reply_to_message:
                                if msg.reply_to_message.message_id == telegram_message_id:
                                    logger.info(f"✓ Method 1: Found reply to our message!")
                                    last_message_time = asyncio.get_event_loop().time()
                                    if len(collected_messages) == 0:
                                        logger.info(f"First message received. Will wait for {collection_window}s of silence before returning")
                                    else:
                                        logger.info(f"Additional message received. Resetting silence timer")
                                    collected_messages.append(msg_text)
                                    logger.debug(f"Collected {len(collected_messages)} message(s) so far")
                                    continue
                                else:
                                    logger.debug(f"Reply to different message (expected {telegram_message_id}, got {msg.reply_to_message.message_id})")

                            # Method 2: Try to extract response with request_id prefix
                            response = self._extract_response(msg_text, request_id)
                            if response:
                                logger.info(f"✓ Method 2: Response extracted via prefix pattern: '{response}'")
                                # For prefix pattern, return immediately (explicit format = single message expected)
                                return response

                            # Method 3 (Fallback): Accept any message from the correct chat
                            # This is the most natural UX - just send your answer
                            logger.info(f"✓ Method 3: Accepting message as response (no reply/prefix needed)")
                            last_message_time = asyncio.get_event_loop().time()
                            if len(collected_messages) == 0:
                                logger.info(f"First message received. Will wait for {collection_window}s of silence before returning")
                            else:
                                logger.info(f"Additional message received. Resetting silence timer")
                            collected_messages.append(msg_text)
                            logger.debug(f"Collected {len(collected_messages)} message(s) so far")
                        else:
                            logger.debug(f"Message from different chat (expected {self.chat_id}, got {msg_chat_id})")

            except TelegramError as e:
                logger.error(f"Error polling Telegram: {e}")
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
