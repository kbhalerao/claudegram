"""Helper script to get your chat ID from Telegram bot updates."""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def get_chat_id():
    """Get chat ID from recent bot messages."""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is not set in .env")
        return

    bot = Bot(token=BOT_TOKEN)
    me = await bot.get_me()

    print("=" * 60)
    print(f"Getting chat ID for bot: @{me.username}")
    print("=" * 60)
    print()
    print("If you haven't already:")
    print(f"1. Open Telegram and search for @{me.username}")
    print("2. Click 'Start' or send /start")
    print("3. Send any message to the bot")
    print()
    print("Checking for messages...")
    print()

    updates = await bot.get_updates()

    if not updates:
        print("❌ No messages found yet!")
        print()
        print("Please send a message to the bot first, then run this script again.")
        return

    print(f"✓ Found {len(updates)} update(s)!")
    print()
    print("Recent chats:")
    print("-" * 60)

    seen_chats = {}
    for update in reversed(updates[-10:]):  # Show last 10 updates
        if update.message:
            chat_id = update.message.chat_id
            from_user = update.message.from_user

            if chat_id not in seen_chats:
                seen_chats[chat_id] = {
                    "name": from_user.first_name,
                    "username": from_user.username,
                    "message": update.message.text or "(media)",
                }

    for chat_id, info in seen_chats.items():
        print(f"Chat ID: {chat_id}")
        print(f"  Name: {info['name']}")
        if info["username"]:
            print(f"  Username: @{info['username']}")
        print(f"  Last message: {info['message']}")
        print()

    if len(seen_chats) == 1:
        chat_id = list(seen_chats.keys())[0]
        print("=" * 60)
        print("Add this to your .env file:")
        print("=" * 60)
        print(f"TELEGRAM_CHAT_ID={chat_id}")
        print("=" * 60)
    else:
        print("Multiple chats found. Use the Chat ID for your personal chat.")


if __name__ == "__main__":
    asyncio.run(get_chat_id())
