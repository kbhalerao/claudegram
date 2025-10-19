#!/usr/bin/env python3
"""Debug script to test Telegram polling and response recognition."""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

from src.telegram_io_mcp.telegram_client import TelegramClient

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def test_polling():
    """Test the polling mechanism."""
    client = TelegramClient(BOT_TOKEN, CHAT_ID)

    print("=" * 70)
    print("ClaudeGram - Polling Debug Tool")
    print("=" * 70)
    print()

    # Generate a request ID
    request_id = f"req_debug_{int(datetime.now().timestamp())}"
    message = f"{request_id}: Please reply 'test response' to this message"

    # Send the test message
    print(f"Sending test message...")
    print(f"Request ID: {request_id}")
    print(f"Message: {message}")
    print()

    success = await client.send_message(message)

    if not success:
        print("❌ Failed to send message!")
        return

    print("✓ Message sent successfully!")
    print()
    print("=" * 70)
    print("INSTRUCTIONS:")
    print("=" * 70)
    print(f"1. Check your Telegram chat for the message")
    print(f"2. Reply EXACTLY in this format:")
    print(f"   {request_id}: test response")
    print(f"3. This script will poll for 30 seconds")
    print("=" * 70)
    print()

    # Get initial updates to mark as read
    print("Getting initial updates...")
    updates = await client.bot.get_updates()
    if updates:
        last_update_id = updates[-1].update_id
        print(f"✓ Caught up to update ID: {last_update_id}")
    else:
        last_update_id = None
        print("✓ No previous updates")

    print()
    print("Starting polling (30 seconds)...")
    print("-" * 70)

    # Poll for response
    start_time = asyncio.get_event_loop().time()
    poll_interval = 2
    timeout = 30
    attempts = 0

    while True:
        attempts += 1
        elapsed = asyncio.get_event_loop().time() - start_time

        if elapsed >= timeout:
            print()
            print("⏱️  Timeout reached (30 seconds)")
            print(f"Made {attempts} polling attempts")
            break

        # Get updates
        try:
            updates = await client.bot.get_updates(
                offset=last_update_id + 1 if last_update_id else None, timeout=2
            )

            print(f"[{elapsed:5.1f}s] Poll #{attempts}: ", end="")

            if updates:
                print(f"Got {len(updates)} update(s)")

                for update in updates:
                    last_update_id = update.update_id

                    if update.message:
                        msg = update.message
                        print(f"  Update ID: {update.update_id}")
                        print(f"  From: {msg.from_user.first_name} (ID: {msg.chat_id})")
                        print(f"  Text: {msg.text}")

                        # Check if it's from the correct chat
                        if str(msg.chat_id) == CHAT_ID:
                            print(f"  ✓ Chat ID matches!")

                            # Try to extract response
                            response = client._extract_response(msg.text, request_id)
                            if response:
                                print()
                                print("=" * 70)
                                print("✅ SUCCESS! Response recognized!")
                                print("=" * 70)
                                print(f"Request ID: {request_id}")
                                print(f"Response: {response}")
                                print(f"Time taken: {elapsed:.1f} seconds")
                                print("=" * 70)
                                return
                            else:
                                print(f"  ✗ Response pattern didn't match")
                                print(
                                    f"     Expected format: {request_id}: <your response>"
                                )
                        else:
                            print(
                                f"  ✗ Wrong chat (expected {CHAT_ID}, got {msg.chat_id})"
                            )
                        print()
            else:
                print("No new updates")

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(poll_interval)

    print()
    print("=" * 70)
    print("❌ No matching response received")
    print("=" * 70)
    print()
    print("Debugging tips:")
    print(f"1. Make sure you replied in the exact format: {request_id}: test response")
    print(f"2. Check that TELEGRAM_CHAT_ID in .env matches your actual chat ID")
    print(f"3. The bot must have received your message (check with @userinfobot)")


async def main():
    """Main entry point."""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        return

    await test_polling()


if __name__ == "__main__":
    asyncio.run(main())
