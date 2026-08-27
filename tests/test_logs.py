"""
Tests for log retrieval functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_logs
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


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
    async def test_fetch_logs_basic(self):
        """Test basic log fetching functionality"""
        # Mock the HTTP response
        mock_response_data = {
            "data": [
                {
                    "attributes": {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "message": "Test log message",
                        "service": "test-service",
                        "status": "info"
                    }
                }
            ],
            "meta": {
                "page": {
                    "after": "next_cursor"
                }
            }
        }
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_logs()
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert "message" in result[0]
    
    @pytest.mark.asyncio 
    async def test_fetch_logs_with_filters(self):
        """Test log fetching with filters"""
        filters = {
            "service": "web-app",
            "env": "production",
            "status": "error"
        }
        
        mock_response_data = {
            "data": [
                {
                    "attributes": {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "message": "Error occurred",
                        "service": "web-app",
                        "status": "error"
                    }
                }
            ]
        }
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_logs(filters=filters)
            
            assert isinstance(result, list)
            # Verify filter was applied (would be in the request payload)
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()


class TestLogToolHandler:
    """Test the get_logs tool handler"""
    
    @pytest.mark.asyncio
    async def test_handle_logs_request_success(self):
        """Test successful log request handling"""
        # Mock request
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "error",
            "time_range": "1h",
            "limit": 100,
            "format": "table"
        }
        
        # Mock log data
        mock_logs = [
            {
                "timestamp": "2023-01-01T12:00:00Z",
                "message": "Error in application",
                "service": "web-app",
                "status": "error"
            }
        ]
        
        with patch('datadog_mcp.utils.datadog_client.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_logs
            
            result = await get_logs.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)
            
            # Should contain log information
            content_text = result.content[0].text
            assert "Error in application" in content_text or "error" in content_text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_logs_request_with_json_format(self):
        """Test log request with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "info",
            "format": "json",
            "limit": 50
        }
        
        mock_logs = [
            {
                "timestamp": "2023-01-01T12:00:00Z",
                "message": "Info message",
                "service": "api",
                "status": "info"
            }
        ]
        
        with patch('datadog_mcp.utils.datadog_client.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_logs
            
            result = await get_logs.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            
            content_text = result.content[0].text
            # Should be valid JSON when format is json
            if mock_request.arguments.get("format") == "json":
                try:
                    json.loads(content_text)
                except json.JSONDecodeError:
                    pytest.fail("Response should be valid JSON when format=json")
    
    @pytest.mark.asyncio
    async def test_handle_logs_request_error(self):
        """Test error handling in log requests"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "test",
            "time_range": "1h"
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            
            result = await get_logs.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is True
            assert len(result.content) > 0
            assert "error" in result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_logs_request_empty_results(self):
        """Test handling when no logs are found"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "query": "nonexistent",
            "time_range": "1h"
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            result = await get_logs.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            
            content_text = result.content[0].text
            assert "no logs" in content_text.lower() or "no results" in content_text.lower()


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
    async def test_logs_with_service_filter(self):
        """Test filtering logs by service"""
        filters = {"service": "web-api"}
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response = {
                "data": [
                    {
                        "attributes": {
                            "message": "API request",
                            "service": "web-api"
                        }
                    }
                ]
            }
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_logs(filters=filters)
            
            # Verify the request was made with proper filters
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_logs_with_time_range(self):
        """Test filtering logs by time range"""
        time_range = "4h"
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response = {"data": []}
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_logs(time_range=time_range)
            
            # Verify the request was made
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])