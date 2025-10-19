# ClaudeGram Cloudflare Deployment Guide

Complete guide for deploying ClaudeGram to Cloudflare Workers with Durable Objects and D1.

## Prerequisites

- Cloudflare account (free tier works)
- Node.js installed
- Telegram bot created (@BotFather)

## Step 1: Install Wrangler

```bash
npm install -g wrangler
```

## Step 2: Login to Cloudflare

```bash
wrangler login
```

## Step 3: Create D1 Database

```bash
cd cloudflare
wrangler d1 create claudegram-db
```

This outputs something like:
```
[[d1_databases]]
binding = "DB"
database_name = "claudegram-db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Copy the `database_id`** and update `wrangler.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "claudegram-db"
database_id = "YOUR_DATABASE_ID_HERE"  # <- Paste here
```

## Step 4: Run Migrations

```bash
wrangler d1 execute claudegram-db --file=migrations/0001_initial.sql
```

## Step 5: Set Secrets

```bash
# Telegram bot token
wrangler secret put TELEGRAM_BOT_TOKEN
# Paste your bot token when prompted

# Telegram chat ID
wrangler secret put TELEGRAM_CHAT_ID
# Paste your chat ID when prompted

# API key for MCP server authentication
wrangler secret put API_KEY
# Generate a secure random string (e.g., openssl rand -hex 32)
```

## Step 6: Deploy Worker

```bash
wrangler deploy
```

This deploys to: `https://claudegram.<your-subdomain>.workers.dev`

## Step 7: Set Telegram Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://claudegram.<your-subdomain>.workers.dev/telegram/webhook"
```

Verify webhook:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## Step 8: Test the API

```bash
# Health check
curl https://claudegram.<your-subdomain>.workers.dev/health

# Create a test request
curl -X POST https://claudegram.<your-subdomain>.workers.dev/requests \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "X-User-ID: user-test@example.com" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test question", "timeout": 300}'
```

## Step 9: Configure MCP Server

On each device, update `.env`:
```
DEPLOYMENT_MODE=cloud
CLOUDFLARE_WORKER_URL=https://claudegram.<your-subdomain>.workers.dev
CLOUDFLARE_API_KEY=<your-api-key>
USER_ID=user-your-email@example.com
```

## Monitoring

View logs:
```bash
wrangler tail
```

View D1 data:
```bash
wrangler d1 execute claudegram-db --command="SELECT * FROM requests LIMIT 10"
```

## Troubleshooting

### Webhook not receiving messages
```bash
# Check webhook status
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Delete and reset webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://claudegram.<your-subdomain>.workers.dev/telegram/webhook"
```

### Check Worker logs
```bash
wrangler tail --format pretty
```

### Test D1 connection
```bash
wrangler d1 execute claudegram-db --command="SELECT COUNT(*) FROM requests"
```

## Updating

```bash
# Pull latest code
git pull

# Deploy new version
wrangler deploy
```

## Costs

- **Free tier includes:**
  - 100,000 Worker requests/day
  - 1 million Durable Objects requests/day
  - 5 GB D1 storage
  - 5 million D1 rows read/day

ClaudeGram usage typically stays well within free tier limits!
