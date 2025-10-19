-- Initial schema for ClaudeGram D1 database
-- Same schema as local SQLite for easy migration

CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata TEXT,
    sent_at TIMESTAMP NOT NULL,
    timeout_seconds INTEGER DEFAULT 300,
    response TEXT,
    response_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    telegram_message_id INTEGER
);

-- Index for efficient user queries
CREATE INDEX idx_requests_user_id ON requests(user_id);

-- Index for status queries
CREATE INDEX idx_requests_status ON requests(status);

-- Index for cleanup queries
CREATE INDEX idx_requests_created_at ON requests(created_at);

-- Index for telegram message lookups
CREATE INDEX idx_requests_telegram_message_id ON requests(telegram_message_id);
