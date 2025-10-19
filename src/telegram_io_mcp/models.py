"""Data models for Telegram I/O MCP server."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Request:
    """Represents a request sent to Telegram."""

    id: str
    message: str
    sent_at: datetime
    timeout_seconds: int = 300
    metadata: Optional[str] = None
    response: Optional[str] = None
    response_at: Optional[datetime] = None
    status: str = "pending"
    created_at: Optional[datetime] = None
    telegram_message_id: Optional[int] = None  # Telegram's message ID for reply matching

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.id,
            "message": self.message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "response": self.response,
            "response_at": self.response_at.isoformat() if self.response_at else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def response_time_seconds(self) -> Optional[int]:
        """Calculate response time in seconds."""
        if self.response_at and self.sent_at:
            return int((self.response_at - self.sent_at).total_seconds())
        return None


@dataclass
class SendRequestResult:
    """Result of sending a request to Telegram."""

    request_id: str
    sent_at: datetime
    telegram_message: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "sent_at": self.sent_at.isoformat(),
            "telegram_message": self.telegram_message,
        }


@dataclass
class AwaitResponseResult:
    """Result of awaiting a response from Telegram."""

    request_id: str
    response: str
    received_at: datetime
    response_time_seconds: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "response": self.response,
            "received_at": self.received_at.isoformat(),
            "response_time_seconds": self.response_time_seconds,
        }
