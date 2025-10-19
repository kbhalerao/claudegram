"""Cloud API client for ClaudeGram Cloudflare Worker."""

import os
from datetime import datetime
from typing import List, Optional
import httpx

from .models import Request, SendRequestResult, AwaitResponseResult


class CloudClient:
    """API client for ClaudeGram Cloudflare Worker backend."""

    def __init__(
        self,
        worker_url: str,
        api_key: str,
        user_id: str,
    ):
        """Initialize cloud client.

        Args:
            worker_url: Cloudflare Worker URL (e.g., https://claudegram.workers.dev)
            api_key: API key for authentication
            user_id: User identifier
        """
        self.worker_url = worker_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.client = httpx.AsyncClient(timeout=30.0)

    def _headers(self):
        """Get common headers for API requests."""
        return {
            'X-API-Key': self.api_key,
            'X-User-ID': self.user_id,
            'Content-Type': 'application/json',
        }

    async def create_request(
        self,
        message: str,
        timeout_seconds: int = 300,
        metadata: Optional[str] = None,
    ) -> SendRequestResult:
        """Create a new request via API."""
        response = await self.client.post(
            f"{self.worker_url}/requests",
            headers=self._headers(),
            json={
                'message': message,
                'timeout': timeout_seconds,
                'metadata': metadata,
            }
        )
        response.raise_for_status()
        data = response.json()

        return SendRequestResult(
            request_id=data['request_id'],
            sent_at=datetime.fromisoformat(data['sent_at']),
            telegram_message=data['telegram_message'],
        )

    async def get_request(self, request_id: str) -> Optional[Request]:
        """Get request status via API."""
        response = await self.client.get(
            f"{self.worker_url}/requests/{request_id}",
            headers=self._headers(),
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        return Request(
            id=data['request_id'],
            message=data['message'],
            sent_at=datetime.fromisoformat(data['sent_at']),
            status=data['status'],
            response=data.get('response'),
            response_at=datetime.fromisoformat(data['response_at'])
            if data.get('response_at')
            else None,
        )

    async def submit_response(
        self, request_id: str, response_text: str
    ) -> AwaitResponseResult:
        """Submit response via API."""
        response = await self.client.post(
            f"{self.worker_url}/response",
            headers=self._headers(),
            json={
                'request_id': request_id,
                'response': response_text,
            }
        )
        response.raise_for_status()
        data = response.json()

        return AwaitResponseResult(
            request_id=data['request_id'],
            response=data['response'],
            received_at=datetime.fromisoformat(data['received_at']),
            response_time_seconds=data['response_time_seconds'],
        )

    async def get_recent_requests(
        self, limit: int = 10, completed_only: bool = False
    ) -> List[Request]:
        """Get recent requests via API."""
        params = {'limit': limit}
        if completed_only:
            params['completed_only'] = 'true'

        response = await self.client.get(
            f"{self.worker_url}/history",
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        requests = []
        for item in data['requests']:
            requests.append(Request(
                id=item['request_id'],
                message=item['message'],
                sent_at=datetime.fromisoformat(item['sent_at']),
                status=item['status'],
                response=item.get('response'),
                response_at=datetime.fromisoformat(item['response_at'])
                if item.get('response_at')
                else None,
            ))

        return requests

    async def delete_old_requests(self, older_than_days: int = 7) -> tuple[int, int]:
        """Delete old requests via API."""
        response = await self.client.delete(
            f"{self.worker_url}/cleanup",
            headers=self._headers(),
            params={'older_than_days': older_than_days},
        )
        response.raise_for_status()
        data = response.json()

        return data['deleted_count'], data['freed_space_bytes']

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


def get_cloud_client() -> Optional[CloudClient]:
    """Get cloud client if configured, otherwise None."""
    worker_url = os.getenv('CLOUDFLARE_WORKER_URL')
    api_key = os.getenv('CLOUDFLARE_API_KEY')
    user_id = os.getenv('USER_ID')

    if worker_url and api_key and user_id:
        return CloudClient(worker_url, api_key, user_id)

    return None
