"""
Pytest configuration and shared fixtures
"""

import contextlib
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_env_credentials():
    """Mock environment with valid Datadog credentials"""
    with patch.dict(os.environ, {"DD_API_KEY": "test_key", "DD_APP_KEY": "test_app"}):
        yield


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for API calls"""
    with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
        # Setup default successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None

        # `get`/`post` are awaited by the client, so they need AsyncMock
        client = mock_client.return_value.__aenter__.return_value
        client.get = AsyncMock(return_value=mock_response)
        client.post = AsyncMock(return_value=mock_response)

        yield mock_client


@pytest.fixture
def httpx_json():
    """Factory patching the async httpx client so requests return a JSON payload."""

    @contextlib.contextmanager
    def _patch(payload, status_error=None):
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            response = MagicMock()
            response.json.return_value = payload
            if status_error is None:
                response.raise_for_status.return_value = None
            else:
                response.raise_for_status.side_effect = status_error

            client = mock_client.return_value.__aenter__.return_value
            client.get = AsyncMock(return_value=response)
            client.post = AsyncMock(return_value=response)
            yield mock_client

    return _patch


@pytest.fixture
def mock_logs_api():
    """Factory patching the Datadog SDK logs API behind fetch_logs."""

    @contextlib.contextmanager
    def _patch(log_dicts=(), meta=None):
        with patch('datadog_mcp.utils.datadog_client.ApiClient'), \
             patch('datadog_mcp.utils.datadog_client.LogsApi') as mock_api:
            response = MagicMock()
            response.data = [
                MagicMock(**{"to_dict.return_value": d}) for d in log_dicts
            ]
            response.meta = MagicMock(**{"to_dict.return_value": meta or {}})
            response.links = None
            mock_api.return_value.list_logs.return_value = response
            yield mock_api.return_value

    return _patch


@pytest.fixture
def sample_request():
    """Create a sample request object"""
    request = MagicMock()
    request.arguments = {}
    return request


@pytest.fixture
def sample_logs_data():
    """Sample response in the shape `fetch_logs` returns"""
    return {
        "data": [
            {
                "attributes": {
                    "timestamp": "2023-01-01T12:00:00Z",
                    "message": "Test log message",
                    "service": "test-service",
                    "status": "info",
                    "host": "test-host",
                }
            },
            {
                "attributes": {
                    "timestamp": "2023-01-01T12:01:00Z",
                    "message": "Error occurred",
                    "service": "test-service",
                    "status": "error",
                    "host": "test-host",
                }
            },
        ],
        "meta": {"page": {"after": "next-cursor"}},
    }


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing"""
    return {
        "data": {
            "attributes": {
                "series": [
                    {
                        "metric": "system.cpu.user",
                        "points": [
                            [1640995200000, 25.5],
                            [1640995260000, 30.2]
                        ],
                        "tags": ["host:web-01", "env:prod"]
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_teams_data():
    """Sample response in the shape `fetch_teams` returns"""
    return {
        "data": [
            {
                "id": "team-123",
                "type": "team",
                "attributes": {
                    "name": "Backend Team",
                    "handle": "backend-team",
                    "description": "Backend development team",
                    "created_at": "2024-01-01T00:00:00Z",
                },
            }
        ],
        "meta": {"pagination": {"total_count": 1, "total_pages": 1}},
    }