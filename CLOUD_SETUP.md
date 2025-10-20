# ClaudeGram Cloud Deployment - Quick Start Guide

This guide will help you deploy ClaudeGram to Cloudflare Workers for multi-device synchronization.

## Why Cloud Mode?

Cloud mode enables:
- **Multi-device sync**: Use ClaudeGram across laptop, desktop, and mobile seamlessly
- **Real-time updates**: Telegram webhooks (no polling lag)
- **Persistent storage**: Cloud database accessible from all devices
- **Always available**: No need to keep one device running

## Prerequisites

1. **Cloudflare Account** (free tier works fine)
   - Sign up at https://dash.cloudflare.com/sign-up

2. **Telegram Bot**
   - Chat with [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Save your bot token

3. **Telegram Chat ID**
   - Chat with [@userinfobot](https://t.me/userinfobot)
   - Save your chat ID (numeric value)
   - Start a chat with your new bot

4. **Node.js & npm** (for Wrangler CLI)
   - Download from https://nodejs.org/

5. **uv** (Python package manager)
   - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Automated Setup (Recommended)

We've created an automated setup script that handles everything:

```bash
# Clone the repository
git clone https://github.com/kbhalerao/claudegram.git
cd claudegram

# Run the setup script
./setup_cloud.sh
```

The script will:
1. ✅ Check prerequisites
2. ✅ Collect your configuration (bot token, chat ID, etc.)
3. ✅ Login to Cloudflare
4. ✅ Create D1 database
5. ✅ Run migrations
6. ✅ Set Worker secrets
7. ✅ Deploy Worker
8. ✅ Configure Telegram webhook
9. ✅ Install dependencies
10. ✅ Test deployment

## Manual Setup

If you prefer manual setup, follow these steps:

### 1. Install Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values:
# - DEPLOYMENT_MODE=cloud
# - TELEGRAM_BOT_TOKEN=your_token
# - TELEGRAM_CHAT_ID=your_chat_id
# - USER_ID=user-yourname@example.com
# - CLOUDFLARE_API_KEY=generate_random_string
```

### 3. Login to Cloudflare

```bash
wrangler login
```

### 4. Deploy Cloudflare Backend

```bash
cd cloudflare

# Create D1 database
wrangler d1 create claudegram-db

# Copy the database_id from output and update wrangler.toml
# Update the line: database_id = "YOUR_DATABASE_ID_HERE"

# Run migrations
wrangler d1 execute claudegram-db --file=migrations/0001_initial.sql

# Set secrets
wrangler secret put TELEGRAM_BOT_TOKEN  # Paste your bot token
wrangler secret put TELEGRAM_CHAT_ID    # Paste your chat ID
wrangler secret put API_KEY             # Paste your API key

# Deploy Worker
wrangler deploy
```

### 5. Configure Telegram Webhook

```bash
# Replace with your actual Worker URL and bot token
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://claudegram.<your-subdomain>.workers.dev/telegram/webhook"

# Verify webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

### 6. Install MCP Server

```bash
cd ..
uv sync
```

### 7. Update .env with Worker URL

```bash
# Edit .env and update:
CLOUDFLARE_WORKER_URL=https://claudegram.<your-subdomain>.workers.dev
```

## Configure Claude Desktop

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "claudegram": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/claudegram",
        "run",
        "python",
        "-m",
        "telegram_io_mcp.server"
      ]
    }
  }
}
```

Replace `/absolute/path/to/claudegram` with the actual path on your system.

## Multi-Device Setup

To use ClaudeGram across multiple devices:

1. **Deploy once** (from any device) - this creates the cloud infrastructure
2. **On each device**:
   - Clone the repository
   - Copy the `.env` file from your first device (contains shared credentials)
   - Run `uv sync`
   - Configure Claude Desktop with the path on that device

All devices will now share the same cloud state!

## Testing Your Setup

1. **Test the Worker health endpoint**:
   ```bash
   curl https://claudegram.<your-subdomain>.workers.dev/health
   # Should return: {"status":"ok","service":"claudegram"}
   ```

2. **Test in Claude Desktop**:
   - Open Claude Desktop
   - Ask: "Use ClaudeGram to ask me what I want for dinner"
   - Check your Telegram - you should receive the message
   - Reply on Telegram or in Claude chat

3. **Test multi-device** (if you have multiple devices):
   - Send a request from Device A
   - Check status from Device B
   - Respond from mobile Telegram
   - Both devices see the response

## Monitoring & Maintenance

### View Worker Logs
```bash
cd cloudflare
wrangler tail
```

### View Database Contents
```bash
wrangler d1 execute claudegram-db --command="SELECT * FROM requests ORDER BY created_at DESC LIMIT 10"
```

### Update Worker Code
```bash
git pull
cd cloudflare
wrangler deploy
```

### Clean Up Old Requests
Use the `clear_expired_requests` MCP tool in Claude Desktop, or:
```bash
wrangler d1 execute claudegram-db --command="DELETE FROM requests WHERE created_at < datetime('now', '-7 days')"
```

## Troubleshooting

### "Cloud mode requires CLOUDFLARE_WORKER_URL..." error
- Ensure `.env` file exists and contains all required variables
- Verify `DEPLOYMENT_MODE=cloud` is set
- Check that `CLOUDFLARE_WORKER_URL`, `CLOUDFLARE_API_KEY`, and `USER_ID` are set

### Webhook not receiving messages
```bash
# Check webhook status
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Reset webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://claudegram.<your-subdomain>.workers.dev/telegram/webhook"
```

### "Request not found" errors
- Check Worker logs: `wrangler tail`
- Verify D1 database is accessible: `wrangler d1 execute claudegram-db --command="SELECT COUNT(*) FROM requests"`
- Ensure all devices are using the same `USER_ID` in `.env`

### Worker deployment fails
- Verify you're logged in: `wrangler whoami`
- Check D1 database exists: `wrangler d1 list`
- Ensure `wrangler.toml` has correct `database_id`

## Cost Breakdown

Cloudflare's **free tier** includes:
- ✅ 100,000 Worker requests/day
- ✅ 1 million Durable Objects requests/day
- ✅ 5 GB D1 storage
- ✅ 5 million D1 rows read/day

**Typical ClaudeGram usage**: ~100-500 requests/day = **$0/month** 🎉

## Architecture Overview

```
┌─────────────────┐
│ Claude Desktop  │ ──┐
│  (Device 1)     │   │
└─────────────────┘   │
                      │
┌─────────────────┐   │    ┌──────────────────┐
│ Claude Desktop  │ ──┼───▶│ Cloudflare Worker│
│  (Device 2)     │   │    │  + Durable Object│
└─────────────────┘   │    └─────────┬────────┘
                      │              │
┌─────────────────┐   │              ├─▶ D1 Database
│ Claude Code     │ ──┘              │
│  (Mobile SSH)   │                  └─▶ Telegram Bot
└─────────────────┘
```

## Next Steps

- Read [cloudflare/DEPLOYMENT.md](cloudflare/DEPLOYMENT.md) for advanced configuration
- Check [README.md](README.md) for usage examples
- See [CLAUDE.md](CLAUDE.md) for development guidelines

## Getting Help

- File issues: https://github.com/kbhalerao/claudegram/issues
- Check logs: `wrangler tail`
- Review Cloudflare docs: https://developers.cloudflare.com/workers/

---

**Happy cloud deploying! 🚀**
