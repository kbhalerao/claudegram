#!/bin/bash

# ClaudeGram Cloud Deployment Setup Script
# This script helps you configure ClaudeGram for cloud deployment

set -e

echo "========================================"
echo "ClaudeGram Cloud Deployment Setup"
echo "========================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the claudegram directory
if [ ! -f "pyproject.toml" ] || [ ! -d "cloudflare" ]; then
    echo -e "${RED}Error: Please run this script from the claudegram root directory${NC}"
    exit 1
fi

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
echo ""

# Check for wrangler
if ! command -v wrangler &> /dev/null; then
    echo -e "${YELLOW}Wrangler CLI not found. Installing...${NC}"
    npm install -g wrangler
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed. Please install uv first:${NC}"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check complete${NC}"
echo ""

# Step 2: Get configuration from user
echo "Step 2: Collecting configuration..."
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Do you want to overwrite it? (y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "Using existing .env file"
        source .env
    else
        rm .env
    fi
fi

if [ ! -f ".env" ]; then
    # Telegram Bot Token
    echo "Please enter your Telegram Bot Token (from @BotFather):"
    read -p "TELEGRAM_BOT_TOKEN: " bot_token

    # Telegram Chat ID
    echo ""
    echo "Please enter your Telegram Chat ID (from @userinfobot):"
    read -p "TELEGRAM_CHAT_ID: " chat_id

    # User ID
    echo ""
    echo "Please enter your User ID (e.g., user-yourname@example.com):"
    read -p "USER_ID: " user_id

    # API Key
    echo ""
    echo "Generating secure API key..."
    api_key=$(openssl rand -hex 32)
    echo -e "${GREEN}Generated API key: $api_key${NC}"

    # Create .env file
    cat > .env <<EOF
# ClaudeGram Cloud Configuration
DEPLOYMENT_MODE=cloud

# Cloudflare Worker URL (will be updated after deployment)
CLOUDFLARE_WORKER_URL=https://claudegram.YOUR-SUBDOMAIN.workers.dev

# API Key for Worker authentication
CLOUDFLARE_API_KEY=$api_key

# User ID (unique identifier)
USER_ID=$user_id

# Telegram credentials
TELEGRAM_BOT_TOKEN=$bot_token
TELEGRAM_CHAT_ID=$chat_id

# Local mode settings (not used in cloud mode)
REQUEST_TIMEOUT_DEFAULT=300
DATABASE_PATH=./telegram_io_cache.db
EOF

    echo -e "${GREEN}✓ Configuration saved to .env${NC}"
    source .env
fi

echo ""

# Step 3: Login to Cloudflare
echo "Step 3: Logging into Cloudflare..."
echo ""

wrangler login

echo -e "${GREEN}✓ Cloudflare login complete${NC}"
echo ""

# Step 4: Create D1 Database
echo "Step 4: Creating D1 Database..."
echo ""

cd cloudflare

# Check if database already exists
db_output=$(wrangler d1 list 2>&1 || true)

if echo "$db_output" | grep -q "claudegram-db"; then
    echo -e "${YELLOW}Database 'claudegram-db' already exists${NC}"
    # Extract database ID
    db_id=$(wrangler d1 list | grep "claudegram-db" | awk '{print $2}')
else
    # Create new database
    db_result=$(wrangler d1 create claudegram-db)
    db_id=$(echo "$db_result" | grep "database_id" | cut -d'"' -f2)

    # Update wrangler.toml with database ID
    if [ ! -z "$db_id" ]; then
        sed -i.bak "s/database_id = \"\"/database_id = \"$db_id\"/" wrangler.toml
        rm wrangler.toml.bak
        echo -e "${GREEN}✓ Database created with ID: $db_id${NC}"
    fi
fi

echo ""

# Step 5: Run migrations
echo "Step 5: Running database migrations..."
echo ""

wrangler d1 execute claudegram-db --file=migrations/0001_initial.sql

echo -e "${GREEN}✓ Migrations complete${NC}"
echo ""

# Step 6: Set secrets
echo "Step 6: Setting Worker secrets..."
echo ""

echo "$TELEGRAM_BOT_TOKEN" | wrangler secret put TELEGRAM_BOT_TOKEN
echo "$TELEGRAM_CHAT_ID" | wrangler secret put TELEGRAM_CHAT_ID
echo "$CLOUDFLARE_API_KEY" | wrangler secret put API_KEY

echo -e "${GREEN}✓ Secrets configured${NC}"
echo ""

# Step 7: Deploy Worker
echo "Step 7: Deploying Cloudflare Worker..."
echo ""

deploy_output=$(wrangler deploy 2>&1)
echo "$deploy_output"

# Extract worker URL
worker_url=$(echo "$deploy_output" | grep -oE "https://[a-zA-Z0-9-]+\.workers\.dev" | head -1)

if [ ! -z "$worker_url" ]; then
    echo -e "${GREEN}✓ Worker deployed to: $worker_url${NC}"

    # Update .env with actual Worker URL
    cd ..
    sed -i.bak "s|CLOUDFLARE_WORKER_URL=.*|CLOUDFLARE_WORKER_URL=$worker_url|" .env
    rm .env.bak

    echo -e "${GREEN}✓ Updated .env with Worker URL${NC}"
else
    echo -e "${YELLOW}Warning: Could not extract Worker URL. Please update .env manually.${NC}"
    cd ..
fi

echo ""

# Step 8: Set Telegram Webhook
echo "Step 8: Configuring Telegram webhook..."
echo ""

if [ ! -z "$worker_url" ]; then
    webhook_url="$worker_url/telegram/webhook"
    curl_output=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -d "url=$webhook_url")

    if echo "$curl_output" | grep -q '"ok":true'; then
        echo -e "${GREEN}✓ Webhook configured successfully${NC}"

        # Verify webhook
        webhook_info=$(curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo")
        echo "Webhook info: $webhook_info"
    else
        echo -e "${RED}Error: Failed to set webhook${NC}"
        echo "$curl_output"
    fi
fi

echo ""

# Step 9: Install MCP server dependencies
echo "Step 9: Installing MCP server dependencies..."
echo ""

uv sync

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 10: Test deployment
echo "Step 10: Testing deployment..."
echo ""

if [ ! -z "$worker_url" ]; then
    health_check=$(curl -s "$worker_url/health")

    if echo "$health_check" | grep -q "ok"; then
        echo -e "${GREEN}✓ Health check passed${NC}"
        echo "Response: $health_check"
    else
        echo -e "${YELLOW}Warning: Health check failed${NC}"
        echo "Response: $health_check"
    fi
fi

echo ""
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Configure Claude Desktop to use this MCP server"
echo "2. Add the following to your Claude Desktop config:"
echo ""
echo '{
  "mcpServers": {
    "claudegram": {
      "command": "uv",
      "args": [
        "--directory",
        "'$(pwd)'",
        "run",
        "python",
        "-m",
        "telegram_io_mcp.server"
      ]
    }
  }
}'
echo ""
echo "3. Restart Claude Desktop"
echo ""
echo "For more information, see:"
echo "  - README.md"
echo "  - cloudflare/DEPLOYMENT.md"
echo ""
