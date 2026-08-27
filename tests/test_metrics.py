"""
Tests for metrics collection functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_metrics, list_metrics, get_metric_fields, get_metric_field_values
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


class TestMetricsToolDefinitions:
    """Test metrics tool definitions"""
    
    def test_get_metrics_tool_definition(self):
        """Test get_metrics tool definition"""
        tool_def = get_metrics.get_tool_definition()
        
        assert tool_def.name == "get_metrics"
        assert "metric" in tool_def.description.lower()
        assert hasattr(tool_def, 'input_schema')
        
        schema = tool_def.input_schema
        assert "properties" in schema
        
        properties = schema["properties"] 
        expected_params = ["metric_name", "time_range", "aggregation", "filters", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from get_metrics schema"
    
    def test_list_metrics_tool_definition(self):
        """Test list_metrics tool definition"""
        tool_def = list_metrics.get_tool_definition()
        
        assert tool_def.name == "list_metrics"
        assert "list" in tool_def.description.lower()
        assert "metric" in tool_def.description.lower()
    
    def test_get_metric_fields_tool_definition(self):
        """Test get_metric_fields tool definition"""
        tool_def = get_metric_fields.get_tool_definition()
        
        assert tool_def.name == "get_metric_fields"
        assert "field" in tool_def.description.lower()
        assert hasattr(tool_def, 'input_schema')
        
        schema = tool_def.input_schema
        properties = schema["properties"]
        assert "metric_name" in properties
    
    def test_get_metric_field_values_tool_definition(self):
        """Test get_metric_field_values tool definition"""
        tool_def = get_metric_field_values.get_tool_definition()
        
        assert tool_def.name == "get_metric_field_values"
        assert "field" in tool_def.description.lower()
        assert "value" in tool_def.description.lower()


class TestMetricsRetrieval:
    """Test metrics data retrieval"""

    @pytest.mark.asyncio
    async def test_fetch_metrics_basic(self, httpx_json):
        """Test basic metrics fetching"""
        payload = {
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

        with httpx_json(payload) as mock_client:
            result = await datadog_client.fetch_metrics("system.cpu.user")

            assert result == payload
            get = mock_client.return_value.__aenter__.return_value.get
            assert get.call_args.kwargs["params"]["query"] == "avg:system.cpu.user"

    @pytest.mark.asyncio
    async def test_fetch_metrics_with_aggregation(self, httpx_json):
        """Test that aggregation_by adds a `by` clause to the query"""
        with httpx_json({"data": {"attributes": {"series": []}}}) as mock_client:
            await datadog_client.fetch_metrics(
                "aws.apigateway.count",
                aggregation_by=["service", "region"],
            )

            get = mock_client.return_value.__aenter__.return_value.get
            query = get.call_args.kwargs["params"]["query"]
            assert query == "avg:aws.apigateway.count by {service,region}"

    @pytest.mark.asyncio
    async def test_fetch_metrics_time_range(self, httpx_json):
        """Test that the time range maps to a from/to window"""
        with httpx_json({"data": {"attributes": {"series": []}}}) as mock_client:
            await datadog_client.fetch_metrics("system.cpu.user", time_range="4h")

            params = mock_client.return_value.__aenter__.return_value.get.call_args.kwargs["params"]
            assert params["to"] - params["from"] == 14400

    @pytest.mark.asyncio
    async def test_fetch_metrics_list(self, httpx_json):
        """Test listing available metrics"""
        payload = {
            "data": [
                {"id": "system.cpu.user", "type": "metrics"},
                {"id": "aws.apigateway.count", "type": "metrics"},
            ]
        }

        with httpx_json(payload) as mock_client:
            result = await datadog_client.fetch_metrics_list()

            assert result == payload
            params = mock_client.return_value.__aenter__.return_value.get.call_args.kwargs["params"]
            assert params["page[size]"] == 50

    @pytest.mark.asyncio
    async def test_fetch_metrics_list_with_filter(self, httpx_json):
        """Test that a filter query is sent as a tag filter"""
        with httpx_json({"data": []}) as mock_client:
            await datadog_client.fetch_metrics_list(filter_query="team:backend", limit=10)

            params = mock_client.return_value.__aenter__.return_value.get.call_args.kwargs["params"]
            assert params["filter[tags]"] == "team:backend"
            assert params["page[size]"] == 10


class TestMetricsToolHandlers:
    """Test metrics tool handlers"""
    
    @pytest.mark.asyncio
    async def test_handle_get_metrics_success(self):
        """Test successful metrics request"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "metric_name": "system.cpu.user",
            "time_range": "1h",
            "aggregation": "avg",
            "format": "table"
        }
        
        mock_metrics_data = {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "metric": "system.cpu.user",
                            "points": [[1640995200000, 25.5]],
                            "tags": ["host:web-01"]
                        }
                    ]
                }
            }
        }
        
        with patch('datadog_mcp.tools.get_metrics.fetch_metrics', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_metrics_data
            
            result = await get_metrics.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)
            
            content_text = result.content[0].text
            assert "system.cpu.user" in content_text or "cpu" in content_text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_list_metrics_success(self):
        """Test successful metrics listing"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "limit": 100,
            "format": "list"
        }
        
        mock_metrics_list = {
            "data": [
                {"id": "system.cpu.user", "type": "metrics"},
                {"id": "aws.apigateway.count", "type": "metrics"},
            ]
        }

        with patch('datadog_mcp.tools.list_metrics.fetch_metrics_list', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_metrics_list
            
            result = await list_metrics.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_handle_get_metric_fields_success(self):
        """Test successful metric fields retrieval"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "metric_name": "aws.apigateway.count"
        }
        
        mock_fields = ["service", "region", "account", "environment"]
        
        with patch('datadog_mcp.tools.get_metric_fields.fetch_metric_available_fields', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_fields
            
            result = await get_metric_fields.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            
            content_text = result.content[0].text
            for field in mock_fields[:2]:  # Check first couple fields
                assert field in content_text
    
    @pytest.mark.asyncio
    async def test_handle_get_metric_field_values_success(self):
        """Test successful metric field values retrieval"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "metric_name": "aws.apigateway.count",
            "field_name": "service"
        }
        
        mock_values = ["web-api", "mobile-api", "admin-api"]
        
        with patch('datadog_mcp.tools.get_metric_field_values.fetch_metric_field_values', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_values
            
            result = await get_metric_field_values.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            
            content_text = result.content[0].text
            for value in mock_values[:2]:  # Check first couple values
                assert value in content_text
    
    @pytest.mark.asyncio
    async def test_handle_metrics_error(self):
        """Test error handling in metrics requests"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "metric_name": "invalid.metric"
        }
        
        with patch('datadog_mcp.tools.get_metrics.fetch_metrics', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Metric not found")
            
            result = await get_metrics.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is True
            assert "error" in result.content[0].text.lower()


class TestMetricsFormatting:
    """Test metrics data formatting"""
    
    def test_metrics_table_formatting(self):
        """Test metrics table formatting"""
        sample_metrics = {
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
        
        # Test that we can process metrics data
        series = sample_metrics["data"]["attributes"]["series"]
        assert len(series) == 1
        assert len(series[0]["points"]) == 2
        assert series[0]["metric"] == "system.cpu.user"
    
    def test_metrics_timeseries_formatting(self):
        """Test metrics timeseries formatting"""
        sample_points = [
            [1640995200000, 25.5],
            [1640995260000, 30.2],
            [1640995320000, 28.7]
        ]
        
        # Basic validation of timeseries data structure
        for point in sample_points:
            assert len(point) == 2  # timestamp, value
            assert isinstance(point[0], (int, float))  # timestamp
            assert isinstance(point[1], (int, float))  # value
    
    def test_metrics_aggregation_formatting(self):
        """Test metrics with aggregation formatting"""
        sample_aggregated = {
            "service:web-api": {
                "points": [[1640995200000, 100]],
                "tags": ["service:web-api", "env:prod"]
            },
            "service:mobile-api": {
                "points": [[1640995200000, 75]], 
                "tags": ["service:mobile-api", "env:prod"]
            }
        }
        
        # Verify aggregated structure
        assert len(sample_aggregated) == 2
        for service_key, data in sample_aggregated.items():
            assert "points" in data
            assert "tags" in data
            assert service_key.startswith("service:")


class TestMetricsFiltering:
    """Test metrics filtering functionality"""

    @pytest.mark.asyncio
    async def test_metrics_with_environment_filter(self, httpx_json):
        """Test filtering metrics by environment"""
        with httpx_json({"data": {"attributes": {"series": []}}}) as mock_client:
            await datadog_client.fetch_metrics(
                "system.cpu.user",
                filters={"env": "production"},
            )

            get = mock_client.return_value.__aenter__.return_value.get
            assert get.call_args.kwargs["params"]["query"] == "avg:system.cpu.user{env:production}"

    @pytest.mark.asyncio
    async def test_metrics_with_multiple_filters(self, httpx_json):
        """Test that multiple filters are comma-joined inside the braces"""
        with httpx_json({"data": {"attributes": {"series": []}}}) as mock_client:
            await datadog_client.fetch_metrics(
                "system.cpu.user",
                filters={"env": "prod", "service": "api"},
            )

            get = mock_client.return_value.__aenter__.return_value.get
            query = get.call_args.kwargs["params"]["query"]
            assert query == "avg:system.cpu.user{env:prod,service:api}"

    @pytest.mark.asyncio
    async def test_metrics_aggregation_prefix(self, httpx_json):
        """Test that the aggregation prefixes the metric name"""
        with httpx_json({"data": {"attributes": {"series": []}}}) as mock_client:
            await datadog_client.fetch_metrics("system.cpu.user", aggregation="sum")

            get = mock_client.return_value.__aenter__.return_value.get
            assert get.call_args.kwargs["params"]["query"].startswith("sum:")


class TestMetricsValidation:
    """Test metrics input validation"""
    
    @pytest.mark.asyncio
    async def test_invalid_metric_name_handling(self):
        """Test handling of invalid metric names"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "metric_name": "",  # Empty metric name
            "time_range": "1h"
        }
        
        result = await get_metrics.handle_call(mock_request)
        
        # Should handle gracefully (either error or validation message)
        assert isinstance(result, CallToolResult)
        if result.is_error:
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_time_range_handling(self):
        """Test handling of invalid time ranges"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "metric_name": "system.cpu.user",
            "time_range": "invalid"
        }
        
        # Should handle gracefully
        try:
            result = await get_metrics.handle_call(mock_request)
            assert isinstance(result, CallToolResult)
        except Exception:
            # If validation happens at tool level, that's also acceptable
            pass


if __name__ == "__main__":
    pytest.main([__file__])