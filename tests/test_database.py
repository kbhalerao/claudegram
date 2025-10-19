"""Tests for database operations."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from telegram_io_mcp.database import DatabaseManager
from telegram_io_mcp.models import Request


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield DatabaseManager(str(db_path))


def test_database_initialization(db):
    """Test that database is initialized correctly."""
    assert db.db_path.exists()


def test_create_request(db):
    """Test creating a request in the database."""
    request = Request(
        id="req_test123",
        message="Test message",
        sent_at=datetime.now(),
        timeout_seconds=300,
        metadata="test metadata",
    )

    db.create_request(request)

    # Verify request was created
    retrieved = db.get_request("req_test123")
    assert retrieved is not None
    assert retrieved.id == "req_test123"
    assert retrieved.message == "Test message"
    assert retrieved.metadata == "test metadata"
    assert retrieved.status == "pending"


def test_get_nonexistent_request(db):
    """Test retrieving a request that doesn't exist."""
    result = db.get_request("req_nonexistent")
    assert result is None


def test_update_response(db):
    """Test updating a request with a response."""
    request = Request(
        id="req_test456",
        message="Test question",
        sent_at=datetime.now(),
    )

    db.create_request(request)

    # Update with response
    response_time = datetime.now()
    db.update_response("req_test456", "Test answer", response_time)

    # Verify update
    retrieved = db.get_request("req_test456")
    assert retrieved is not None
    assert retrieved.response == "Test answer"
    assert retrieved.status == "completed"
    assert retrieved.response_at is not None


def test_get_recent_requests(db):
    """Test retrieving recent requests."""
    # Create multiple requests
    for i in range(5):
        request = Request(
            id=f"req_test{i}",
            message=f"Test message {i}",
            sent_at=datetime.now(),
        )
        db.create_request(request)

    # Get recent requests
    requests = db.get_recent_requests(limit=3)
    assert len(requests) == 3


def test_get_recent_requests_completed_only(db):
    """Test filtering requests by completion status."""
    # Create pending and completed requests
    for i in range(3):
        request = Request(
            id=f"req_pending{i}",
            message=f"Pending {i}",
            sent_at=datetime.now(),
        )
        db.create_request(request)

    for i in range(2):
        request = Request(
            id=f"req_completed{i}",
            message=f"Completed {i}",
            sent_at=datetime.now(),
        )
        db.create_request(request)
        db.update_response(f"req_completed{i}", "Answer", datetime.now())

    # Get only completed requests
    completed = db.get_recent_requests(limit=10, completed_only=True)
    assert len(completed) == 2
    assert all(req.status == "completed" for req in completed)


def test_delete_old_requests(db):
    """Test deleting old requests."""
    # Create old requests
    old_time = datetime.now() - timedelta(days=10)
    for i in range(3):
        request = Request(
            id=f"req_old{i}",
            message=f"Old message {i}",
            sent_at=old_time,
        )
        db.create_request(request)

        # Manually update created_at to be old
        with db.db_path.open() as _:
            import sqlite3

            conn = sqlite3.connect(db.db_path)
            conn.execute(
                "UPDATE requests SET created_at = ? WHERE id = ?",
                (old_time.isoformat(), f"req_old{i}"),
            )
            conn.commit()
            conn.close()

    # Create recent request
    request = Request(
        id="req_recent",
        message="Recent message",
        sent_at=datetime.now(),
    )
    db.create_request(request)

    # Delete old requests (older than 7 days)
    deleted_count, freed_space = db.delete_old_requests(older_than_days=7)

    assert deleted_count == 3
    assert freed_space > 0

    # Verify recent request still exists
    recent = db.get_request("req_recent")
    assert recent is not None

    # Verify old requests are gone
    old = db.get_request("req_old0")
    assert old is None


def test_request_response_time(db):
    """Test that response time is calculated correctly."""
    sent_time = datetime.now()
    request = Request(
        id="req_timing",
        message="Timing test",
        sent_at=sent_time,
    )
    db.create_request(request)

    # Wait a moment and update with response
    import time

    time.sleep(1)
    response_time = datetime.now()
    db.update_response("req_timing", "Answer", response_time)

    # Retrieve and check response time
    retrieved = db.get_request("req_timing")
    assert retrieved.response_time_seconds is not None
    assert retrieved.response_time_seconds >= 1
