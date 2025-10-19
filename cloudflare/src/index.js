/**
 * ClaudeGram Cloudflare Worker
 * Routes requests to user-specific Durable Objects
 * Handles Telegram webhooks
 */

import { UserSession } from './user-session.js';
export { UserSession };

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Handle Telegram webhook
    if (url.pathname === '/telegram/webhook') {
      return handleTelegramWebhook(request, env);
    }

    // Handle health check
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok', service: 'claudegram' }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // All other requests go to user's Durable Object
    return routeToUserSession(request, env);
  }
};

/**
 * Route request to user's Durable Object
 */
async function routeToUserSession(request, env) {
  // Get user ID from header
  const userId = request.headers.get('X-User-ID');
  if (!userId) {
    return new Response(JSON.stringify({ error: 'X-User-ID header required' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Get or create Durable Object for this user
  const id = env.USER_SESSIONS.idFromName(userId);
  const stub = env.USER_SESSIONS.get(id);

  // Forward request to Durable Object
  return stub.fetch(request);
}

/**
 * Handle Telegram webhook
 * Receives updates from Telegram and routes to appropriate user session
 */
async function handleTelegramWebhook(request, env) {
  try {
    const update = await request.json();

    // Extract message info
    if (!update.message || !update.message.text) {
      return new Response('OK', { status: 200 });
    }

    const message = update.message;
    const chatId = message.chat.id.toString();
    const text = message.text;
    const messageId = message.message_id;

    console.log(`Telegram webhook: chatId=${chatId}, text=${text}`);

    // Find which user this chat belongs to
    // First, we need to find pending requests for this chat
    const { results } = await env.DB.prepare(
      `SELECT DISTINCT user_id FROM requests
       WHERE status = 'pending'
       ORDER BY created_at DESC
       LIMIT 10`
    ).all();

    // For each user with pending requests, check if this chat belongs to them
    for (const row of results) {
      const userId = row.user_id;

      // Get user's Durable Object
      const id = env.USER_SESSIONS.idFromName(userId);
      const stub = env.USER_SESSIONS.get(id);

      // Try to match this message to a pending request
      const matched = await matchMessageToRequest(stub, env, userId, chatId, text, messageId, message);
      if (matched) {
        break; // Stop after first match
      }
    }

    return new Response('OK', { status: 200 });
  } catch (error) {
    console.error('Telegram webhook error:', error);
    return new Response('Error', { status: 500 });
  }
}

/**
 * Try to match incoming Telegram message to a pending request
 */
async function matchMessageToRequest(stub, env, userId, chatId, text, messageId, fullMessage) {
  // Get pending requests for this user
  const { results } = await env.DB.prepare(
    `SELECT * FROM requests
     WHERE user_id = ? AND status = 'pending'
     ORDER BY sent_at DESC
     LIMIT 5`
  ).bind(userId).all();

  if (results.length === 0) {
    return false;
  }

  for (const request of results) {
    let response = null;

    // Method 1: Check if this is a reply to our message
    if (fullMessage.reply_to_message && request.telegram_message_id) {
      if (fullMessage.reply_to_message.message_id === request.telegram_message_id) {
        response = text;
        console.log(`Matched via reply: request=${request.id}`);
      }
    }

    // Method 2: Check for request_id prefix pattern
    if (!response) {
      const prefixPattern = new RegExp(`^${request.id}:\\s*(.+)$`, 's');
      const match = text.match(prefixPattern);
      if (match) {
        response = match[1].trim();
        console.log(`Matched via prefix: request=${request.id}`);
      }
    }

    // Method 3: Accept any message (most recent pending request)
    if (!response && results[0].id === request.id) {
      response = text;
      console.log(`Matched via any-message: request=${request.id}`);
    }

    // If we found a match, update the request
    if (response) {
      const responseAt = new Date().toISOString();
      await env.DB.prepare(
        `UPDATE requests
         SET response = ?, response_at = ?, status = 'completed'
         WHERE id = ?`
      ).bind(response, responseAt, request.id).run();

      console.log(`Updated request ${request.id} with response`);
      return true;
    }
  }

  return false;
}
