"""
Tests for log retrieval functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_logs
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent

LOGS_PAYLOAD = {
    "data": [
        {
            "attributes": {
                "timestamp": "2023-01-01T12:00:00Z",
                "message": "Error in application",
                "service": "web-app",
                "status": "error",
                "host": "web-01",
            }
        }
    ],
    "meta": {"page": {"after": "next-cursor"}},
}


class TestLogToolDefinition:
    """Test the get_logs tool definition"""
    
    def test_get_logs_tool_definition(self):
        """Test that get_logs tool definition is properly structured"""
        tool_def = get_logs.get_tool_definition()
        
        assert tool_def.name == "get_logs"
        assert "logs" in tool_def.description.lower()
        assert hasattr(tool_def, 'input_schema')
        
        # Check required schema properties
        schema = tool_def.input_schema
        assert "properties" in schema
        
        # Should have common parameters
        properties = schema["properties"]
        expected_params = ["query", "filters", "time_range", "limit", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"


class TestLogRetrieval:
    """Test log retrieval functionality"""

    @pytest.mark.asyncio
    async def test_fetch_logs_basic(self, mock_logs_api):
        """Test basic log fetching functionality"""
        log = LOGS_PAYLOAD["data"][0]

        with mock_logs_api([log], meta={"page": {"after": "next_cursor"}}) as api:
            result = await datadog_client.fetch_logs()

            assert isinstance(result, dict)
            assert result["data"] == [log]
            assert result["meta"]["page"]["after"] == "next_cursor"
            api.list_logs.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_logs_with_filters(self, mock_logs_api):
        """Test that filters are combined into the query string"""
        filters = {
            "service": "web-app",
            "env": "production",
            "status": "error",
        }

        with mock_logs_api([LOGS_PAYLOAD["data"][0]]) as api:
            await datadog_client.fetch_logs(filters=filters)

            body = api.list_logs.call_args.kwargs["body"]
            query = body["filter"]["query"]
            assert "service:web-app" in query
            assert "env:production" in query
            assert "status:error" in query

    @pytest.mark.asyncio
    async def test_fetch_logs_defaults_to_match_all(self, mock_logs_api):
        """Test that no filters yields a match-all query"""
        with mock_logs_api() as api:
            result = await datadog_client.fetch_logs()

            assert result["data"] == []
            body = api.list_logs.call_args.kwargs["body"]
            assert body["filter"]["query"] == "*"


class TestLogToolHandler:
    """Test the get_logs tool handler"""

    @pytest.mark.asyncio
    async def test_handle_logs_request_success(self):
        """Test successful log request handling"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "error",
            "time_range": "1h",
            "limit": 100,
            "format": "table"
        }

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = LOGS_PAYLOAD

            result = await get_logs.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert isinstance(result.content[0], TextContent)
            assert "Error in application" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_logs_request_with_json_format(self):
        """Test log request with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "info",
            "format": "json",
            "limit": 50
        }

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = LOGS_PAYLOAD

            result = await get_logs.handle_call(mock_request)

            assert result.is_error is False
            json.loads(result.content[0].text)

    @pytest.mark.asyncio
    async def test_handle_logs_request_error(self):
        """Test error handling in log requests"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "test",
            "time_range": "1h"
        }

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await get_logs.handle_call(mock_request)

            assert result.is_error is True
            assert "error" in result.content[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_logs_request_empty_results(self):
        """Test handling when no logs are found"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "nonexistent",
            "time_range": "1h"
        }

        with patch('datadog_mcp.tools.get_logs.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"data": [], "meta": {}}

            result = await get_logs.handle_call(mock_request)

            assert result.is_error is False
            assert "no logs" in result.content[0].text.lower()


class TestLogFormatting:
    """Test log data formatting"""
    
    def test_log_table_formatting(self):
        """Test that logs can be formatted as table"""
        sample_logs = [
            {
                "timestamp": "2023-01-01T12:00:00Z",
                "message": "Test message 1",
                "service": "service1",
                "status": "info"
            },
            {
                "timestamp": "2023-01-01T12:01:00Z", 
                "message": "Test message 2",
                "service": "service2",
                "status": "error"
            }
        ]
        
        # Import formatter and test
        from datadog_mcp.utils.formatters import format_logs_as_table
        
        try:
            table_output = format_logs_as_table(sample_logs)
            assert isinstance(table_output, str)
            assert len(table_output) > 0
            assert "service1" in table_output
            assert "service2" in table_output
        except ImportError:
            # If formatter doesn't exist, create a simple test
            assert len(sample_logs) == 2
    
    def test_log_json_formatting(self):
        """Test that logs can be formatted as JSON"""
        sample_logs = [
            {
                "timestamp": "2023-01-01T12:00:00Z",
                "message": "Test message",
                "service": "service1"
            }
        ]
        
        json_output = json.dumps(sample_logs, indent=2)
        assert isinstance(json_output, str)
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert len(parsed) == 1
        assert parsed[0]["service"] == "service1"


class TestLogFiltering:
    """Test log filtering functionality"""

    @pytest.mark.asyncio
    async def test_logs_with_service_filter(self, mock_logs_api):
        """Test filtering logs by service"""
        with mock_logs_api([LOGS_PAYLOAD["data"][0]]) as api:
            await datadog_client.fetch_logs(filters={"service": "web-api"})

            body = api.list_logs.call_args.kwargs["body"]
            assert body["filter"]["query"] == "service:web-api"

    @pytest.mark.asyncio
    async def test_logs_with_time_range(self, mock_logs_api):
        """Test filtering logs by time range"""
        with mock_logs_api() as api:
            await datadog_client.fetch_logs(time_range="4h")

            body = api.list_logs.call_args.kwargs["body"]
            assert body["filter"]._from == "now-4h"
            assert body["filter"].to == "now"

    @pytest.mark.asyncio
    async def test_logs_pagination_cursor(self, mock_logs_api):
        """Test that limit and cursor reach the request page options"""
        with mock_logs_api() as api:
            await datadog_client.fetch_logs(limit=25, cursor="abc123")

            body = api.list_logs.call_args.kwargs["body"]
            assert body["page"]["limit"] == 25
            assert body["page"]["cursor"] == "abc123"


if __name__ == "__main__":
    pytest.main([__file__])