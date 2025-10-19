#!/usr/bin/env python3
"""Check bot configuration and webhook status."""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def check_config():
    """Check bot configuration."""
    print("=" * 70)
    print("ClaudeGram - Bot Configuration Check")
    print("=" * 70)
    print()

    bot = Bot(token=BOT_TOKEN)

    # Get bot info
    me = await bot.get_me()
    print(f"Bot: @{me.username}")
    print()

    # Check webhook
    print("Checking webhook configuration...")
    webhook_info = await bot.get_webhook_info()

    if webhook_info.url:
        print(f"⚠️  Webhook is SET: {webhook_info.url}")
        print(f"   Pending updates: {webhook_info.pending_update_count}")
        print()
        print("This prevents polling from working!")
        print("To fix, run: await bot.delete_webhook()")
        print()

        response = input("Delete webhook now? (y/n): ")
        if response.lower() == "y":
            await bot.delete_webhook(drop_pending_updates=False)
            print("✓ Webhook deleted")
            print()
    else:
        print("✓ No webhook set (polling mode)")
        print()

    # Get pending updates
    print("Checking for pending updates...")
    updates = await bot.get_updates(limit=10)

    if updates:
        print(f"✓ Found {len(updates)} pending update(s):")
        print()
        for i, update in enumerate(updates[-5:], 1):
            if update.message:
                msg = update.message
                print(f"{i}. Update ID: {update.update_id}")
                print(f"   From: {msg.from_user.first_name} ({msg.chat_id})")
                print(f"   Text: {msg.text[:100]}")
                print()
    else:
        print("ℹ️  No pending updates")
        print()
        print("This could mean:")
        print("1. No messages have been sent to the bot")
        print("2. Another process has already consumed the updates")
        print("3. Updates were cleared")
        print()

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(check_config())
