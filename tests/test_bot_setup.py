"""Helper script to verify Telegram bot setup and get chat information."""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def verify_bot_setup():
    """Verify bot configuration and get information."""
    print("=" * 60)
    print("ClaudeGram Bot Setup Verification")
    print("=" * 60)

    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is not set in .env")
        return

    if not CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID is not set in .env")
        return

    print(f"✓ Bot token found: {BOT_TOKEN[:10]}...")
    print(f"✓ Chat ID configured: {CHAT_ID}")
    print()

    try:
        bot = Bot(token=BOT_TOKEN)

        # Get bot information
        print("Getting bot information...")
        me = await bot.get_me()
        print(f"✓ Bot connected successfully!")
        print(f"  Bot username: @{me.username}")
        print(f"  Bot name: {me.first_name}")
        print(f"  Bot ID: {me.id}")
        print()

        # Try to get chat information
        print(f"Checking chat {CHAT_ID}...")
        try:
            chat = await bot.get_chat(chat_id=CHAT_ID)
            print(f"✓ Chat found!")
            print(f"  Chat type: {chat.type}")
            if chat.username:
                print(f"  Chat username: @{chat.username}")
            if chat.first_name:
                print(f"  Chat name: {chat.first_name}")
            print()

            # Try to send a test message
            print("Sending test message...")
            message = await bot.send_message(
                chat_id=CHAT_ID, text="✓ ClaudeGram bot setup verified successfully!"
            )
            print(f"✓ Test message sent! Message ID: {message.message_id}")
            print()
            print("=" * 60)
            print("SUCCESS! Your bot is configured correctly.")
            print("=" * 60)

        except TelegramError as e:
            print(f"❌ Error accessing chat: {e}")
            print()
            print("Troubleshooting steps:")
            print("1. Make sure you've started a chat with your bot")
            print(f"   - Open Telegram and search for @{me.username}")
            print("   - Send /start to the bot")
            print()
            print("2. Get your correct chat ID:")
            print("   - Chat with @userinfobot on Telegram")
            print("   - Copy the ID it gives you")
            print("   - Update TELEGRAM_CHAT_ID in your .env file")
            print()
            print("3. Alternative: Get chat ID from updates")
            print("   Run this and then send a message to your bot:")

            # Try to get recent updates
            print("\n   Checking recent messages to the bot...")
            updates = await bot.get_updates()
            if updates:
                print(f"\n   Found {len(updates)} recent update(s):")
                for update in updates[-5:]:  # Show last 5 updates
                    if update.message:
                        print(
                            f"   - Chat ID: {update.message.chat_id} "
                            f"(from: {update.message.from_user.first_name})"
                        )
            else:
                print("   No recent messages found. Send a message to the bot first!")

    except TelegramError as e:
        print(f"❌ Error connecting to bot: {e}")
        print("\nPlease check that your TELEGRAM_BOT_TOKEN is correct.")

    print()


if __name__ == "__main__":
    asyncio.run(verify_bot_setup())
