"""SQLite database manager for request tracking."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .models import Request


class DatabaseManager:
    """Manages SQLite database for request persistence."""

    def __init__(self, db_path: str = "./telegram_io_cache.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    metadata TEXT,
                    sent_at TIMESTAMP NOT NULL,
                    timeout_seconds INTEGER DEFAULT 300,
                    response TEXT,
                    response_at TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    telegram_message_id INTEGER
                )
            """)

            # Migration: Add telegram_message_id column if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(requests)")
            columns = [row[1] for row in cursor.fetchall()]
            if "telegram_message_id" not in columns:
                conn.execute("ALTER TABLE requests ADD COLUMN telegram_message_id INTEGER")

            conn.commit()

    def create_request(self, request: Request) -> None:
        """Store a new request in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO requests (id, message, metadata, sent_at, timeout_seconds, status, created_at, telegram_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.id,
                    request.message,
                    request.metadata,
                    request.sent_at.isoformat(),
                    request.timeout_seconds,
                    request.status,
                    datetime.now().isoformat(),
                    request.telegram_message_id,
                ),
            )
            conn.commit()

    def get_request(self, request_id: str) -> Optional[Request]:
        """Retrieve a request by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM requests WHERE id = ?", (request_id,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_request(row)
            return None

    def update_response(
        self, request_id: str, response: str, response_at: datetime
    ) -> None:
        """Update a request with the received response."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE requests
                SET response = ?, response_at = ?, status = 'completed'
                WHERE id = ?
                """,
                (response, response_at.isoformat(), request_id),
            )
            conn.commit()

    def get_recent_requests(
        self, limit: int = 10, completed_only: bool = False
    ) -> List[Request]:
        """Retrieve recent requests, optionally filtering by completion status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM requests"
            if completed_only:
                query += " WHERE status = 'completed'"
            query += " ORDER BY created_at DESC LIMIT ?"

            cursor = conn.execute(query, (limit,))
            rows = cursor.fetchall()

            return [self._row_to_request(row) for row in rows]

    def delete_old_requests(self, older_than_days: int = 7) -> tuple[int, int]:
        """Delete requests older than specified days. Returns (count, estimated_bytes)."""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        with sqlite3.connect(self.db_path) as conn:
            # Get count before deletion
            cursor = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE created_at < ?",
                (cutoff_date.isoformat(),),
            )
            count = cursor.fetchone()[0]

            # Estimate freed space (rough calculation)
            estimated_bytes = count * 512  # Rough estimate per row

            # Delete old requests
            conn.execute(
                "DELETE FROM requests WHERE created_at < ?",
                (cutoff_date.isoformat(),),
            )
            conn.commit()

            # Vacuum to reclaim space
            conn.execute("VACUUM")

            return count, estimated_bytes

    def get_request_by_telegram_message_id(self, telegram_message_id: int) -> Optional[Request]:
        """Retrieve a request by Telegram message ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM requests WHERE telegram_message_id = ?", (telegram_message_id,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_request(row)
            return None

    def update_telegram_message_id(self, request_id: str, telegram_message_id: int) -> None:
        """Update a request with its Telegram message ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE requests SET telegram_message_id = ? WHERE id = ?",
                (telegram_message_id, request_id),
            )
            conn.commit()

    @staticmethod
    def _row_to_request(row: sqlite3.Row) -> Request:
        """Convert a database row to a Request object."""
        return Request(
            id=row["id"],
            message=row["message"],
            metadata=row["metadata"],
            sent_at=datetime.fromisoformat(row["sent_at"]),
            timeout_seconds=row["timeout_seconds"],
            response=row["response"],
            response_at=datetime.fromisoformat(row["response_at"])
            if row["response_at"]
            else None,
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            telegram_message_id=row["telegram_message_id"] if "telegram_message_id" in row.keys() else None,
        )
