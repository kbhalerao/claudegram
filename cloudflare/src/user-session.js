/**
 * Durable Object for managing user sessions
 * One instance per user - handles all their requests/responses
 */
export class UserSession {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.userId = null;
  }

  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Extract user ID from request
    this.userId = request.headers.get('X-User-ID');
    if (!this.userId) {
      return jsonResponse({ error: 'X-User-ID header required' }, 401);
    }

    // Verify API key
    const apiKey = request.headers.get('X-API-Key');
    if (!this.verifyApiKey(apiKey)) {
      return jsonResponse({ error: 'Invalid API key' }, 403);
    }

    // Route requests
    if (path.includes('/requests') && request.method === 'POST') {
      return this.createRequest(request);
    }

    if (path.includes('/requests/') && request.method === 'GET') {
      const requestId = path.split('/').pop();
      return this.getRequest(requestId);
    }

    if (path.includes('/response') && request.method === 'POST') {
      return this.submitResponse(request);
    }

    if (path.includes('/history')) {
      return this.getHistory(request);
    }

    if (path.includes('/cleanup') && request.method === 'DELETE') {
      return this.cleanup(request);
    }

    return jsonResponse({ error: 'Not found' }, 404);
  }

  /**
   * Create a new request and send to Telegram
   */
  async createRequest(request) {
    const body = await request.json();
    const { message, timeout = 300, metadata } = body;

    // Generate unique request ID
    const requestId = `req_${crypto.randomUUID().substring(0, 12)}`;
    const sentAt = new Date().toISOString();

    // Send to Telegram
    const telegramMessageId = await this.sendTelegramMessage(message);
    if (!telegramMessageId) {
      return jsonResponse({ error: 'Failed to send to Telegram' }, 500);
    }

    // Store in D1
    await this.env.DB.prepare(
      `INSERT INTO requests
       (id, user_id, message, metadata, sent_at, timeout_seconds, status, created_at, telegram_message_id)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      requestId,
      this.userId,
      message,
      metadata || null,
      sentAt,
      timeout,
      'pending',
      sentAt,
      telegramMessageId
    ).run();

    return jsonResponse({
      request_id: requestId,
      sent_at: sentAt,
      telegram_message: message,
      telegram_message_id: telegramMessageId
    });
  }

  /**
   * Get request status
   */
  async getRequest(requestId) {
    const result = await this.env.DB.prepare(
      'SELECT * FROM requests WHERE id = ? AND user_id = ?'
    ).bind(requestId, this.userId).first();

    if (!result) {
      return jsonResponse({ error: 'Request not found' }, 404);
    }

    return jsonResponse({
      request_id: result.id,
      status: result.status,
      message: result.message,
      sent_at: result.sent_at,
      response: result.response,
      response_at: result.response_at,
      response_time_seconds: result.response_at
        ? Math.floor((new Date(result.response_at) - new Date(result.sent_at)) / 1000)
        : null
    });
  }

  /**
   * Submit response (from chat or Telegram)
   */
  async submitResponse(request) {
    const body = await request.json();
    const { request_id, response } = body;

    // Check if request exists and is pending
    const existing = await this.env.DB.prepare(
      'SELECT * FROM requests WHERE id = ? AND user_id = ?'
    ).bind(request_id, this.userId).first();

    if (!existing) {
      return jsonResponse({ error: 'Request not found' }, 404);
    }

    if (existing.status === 'completed') {
      return jsonResponse({
        error: 'Request already completed',
        existing_response: existing.response
      }, 400);
    }

    // Update with response
    const responseAt = new Date().toISOString();
    await this.env.DB.prepare(
      `UPDATE requests
       SET response = ?, response_at = ?, status = 'completed'
       WHERE id = ? AND user_id = ?`
    ).bind(response, responseAt, request_id, this.userId).run();

    const responseTime = Math.floor((new Date(responseAt) - new Date(existing.sent_at)) / 1000);

    return jsonResponse({
      request_id: request_id,
      response: response,
      received_at: responseAt,
      response_time_seconds: responseTime
    });
  }

  /**
   * Get request history
   */
  async getHistory(request) {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const completedOnly = url.searchParams.get('completed_only') === 'true';

    let query = 'SELECT * FROM requests WHERE user_id = ?';
    let params = [this.userId];

    if (completedOnly) {
      query += ' AND status = ?';
      params.push('completed');
    }

    query += ' ORDER BY created_at DESC LIMIT ?';
    params.push(limit);

    const { results } = await this.env.DB.prepare(query).bind(...params).all();

    const requests = results.map(r => ({
      request_id: r.id,
      message: r.message,
      status: r.status,
      sent_at: r.sent_at,
      response: r.response,
      response_at: r.response_at,
      response_time_seconds: r.response_at
        ? Math.floor((new Date(r.response_at) - new Date(r.sent_at)) / 1000)
        : null
    }));

    return jsonResponse({ requests });
  }

  /**
   * Cleanup old requests
   */
  async cleanup(request) {
    const url = new URL(request.url);
    const olderThanDays = parseInt(url.searchParams.get('older_than_days') || '7');

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

    const result = await this.env.DB.prepare(
      'DELETE FROM requests WHERE user_id = ? AND created_at < ? RETURNING id'
    ).bind(this.userId, cutoffDate.toISOString()).all();

    return jsonResponse({
      deleted_count: result.results.length,
      freed_space_bytes: result.results.length * 512 // estimate
    });
  }

  /**
   * Send message to Telegram
   */
  async sendTelegramMessage(text) {
    const botToken = await this.env.TELEGRAM_BOT_TOKEN;
    const chatId = await this.env.TELEGRAM_CHAT_ID;

    const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: text
      })
    });

    const data = await response.json();
    return data.ok ? data.result.message_id : null;
  }

  /**
   * Verify API key (simple check, use better auth in production)
   */
  verifyApiKey(apiKey) {
    // In production, check against stored keys in env or KV
    const validKey = this.env.API_KEY;
    return apiKey === validKey;
  }
}

/**
 * Helper to create JSON responses
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}
