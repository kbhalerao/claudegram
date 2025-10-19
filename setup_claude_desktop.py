#!/usr/bin/env python3
"""Helper script to generate Claude Desktop configuration for ClaudeGram."""

import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def find_uv():
    """Find the uv executable."""
    uv_path = shutil.which("uv")
    if not uv_path:
        print("❌ Error: 'uv' command not found in PATH")
        print("Please install uv first: https://github.com/astral-sh/uv")
        sys.exit(1)
    return uv_path


def get_config_path():
    """Get the Claude Desktop config file path based on OS."""
    if sys.platform == "darwin":  # macOS
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif sys.platform == "win32":  # Windows
        return Path(os.getenv("APPDATA")) / "Claude/claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config/Claude/claude_desktop_config.json"


def generate_config():
    """Generate the MCP server configuration."""
    uv_path = find_uv()
    project_path = Path(__file__).parent.absolute()

    print("=" * 70)
    print("ClaudeGram - Claude Desktop MCP Configuration Generator")
    print("=" * 70)
    print()

    # Check environment variables
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  Warning: Environment variables not configured!")
        print("Please make sure your .env file contains:")
        print("  - TELEGRAM_BOT_TOKEN")
        print("  - TELEGRAM_CHAT_ID")
        print()
        print("You can still generate the config, but you'll need to add these manually.")
        print()

    config = {
        "claudegram": {
            "command": str(uv_path),
            "args": [
                "--directory",
                str(project_path),
                "run",
                "python",
                "-m",
                "telegram_io_mcp.server",
            ],
        }
    }

    # Add environment variables if available
    if BOT_TOKEN and CHAT_ID:
        config["claudegram"]["env"] = {
            "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
            "TELEGRAM_CHAT_ID": CHAT_ID,
        }

    print(f"✓ Found uv at: {uv_path}")
    print(f"✓ Project path: {project_path}")
    print()

    # Display configuration
    print("Generated MCP Server Configuration:")
    print("=" * 70)
    print(json.dumps({"mcpServers": config}, indent=2))
    print("=" * 70)
    print()

    # Get config file path
    config_path = get_config_path()
    print(f"Claude Desktop config location: {config_path}")
    print()

    # Check if config file exists
    if config_path.exists():
        print("⚠️  Configuration file already exists!")
        print()
        response = input("Do you want to merge this configuration? (y/n): ")
        if response.lower() != "y":
            print("Cancelled. Configuration not saved.")
            print()
            print("To manually add this configuration, copy the JSON above and add it")
            print("to the 'mcpServers' section of your Claude Desktop config file.")
            return

        # Load existing config
        with open(config_path) as f:
            existing_config = json.load(f)

        # Merge configurations
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}

        existing_config["mcpServers"].update(config)

        # Backup existing config
        backup_path = config_path.with_suffix(".json.backup")
        shutil.copy(config_path, backup_path)
        print(f"✓ Backed up existing config to: {backup_path}")

        # Write merged config
        with open(config_path, "w") as f:
            json.dump(existing_config, f, indent=2)

        print(f"✓ Updated configuration file: {config_path}")

    else:
        # Create new config file
        config_path.parent.mkdir(parents=True, exist_ok=True)

        full_config = {"mcpServers": config}

        with open(config_path, "w") as f:
            json.dump(full_config, f, indent=2)

        print(f"✓ Created new configuration file: {config_path}")

    print()
    print("=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart Claude Desktop")
    print("2. The 'telegram-io' MCP server should now be available")
    print("3. You can test it by asking Claude to use the Telegram tools")
    print()


if __name__ == "__main__":
    try:
        generate_config()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
