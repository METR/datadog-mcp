#!/usr/bin/env python3
"""
Datadog CI Visibility MCP Server

Provides tools to query Datadog CI pipelines with filtering capabilities.
"""

import asyncio
import logging

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
)

from .tools import get_fingerprints, list_pipelines, get_logs, get_teams, get_metrics, get_metric_fields, get_metric_field_values, list_metrics, list_service_definitions, get_service_definition, list_monitors, list_slos, get_logs_field_values

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("datadog-mcp-server")

SERVER_NAME = "datadog-mcp-server"
SERVER_VERSION = "1.0.0"

# Tool registry
TOOLS = {
    "list_ci_pipelines": {
        "definition": list_pipelines.get_tool_definition,
        "handler": list_pipelines.handle_call,
    },
    "get_pipeline_fingerprints": {
        "definition": get_fingerprints.get_tool_definition,
        "handler": get_fingerprints.handle_call,
    },
    "get_logs": {
        "definition": get_logs.get_tool_definition,
        "handler": get_logs.handle_call,
    },
    "get_logs_field_values": {
        "definition": get_logs_field_values.get_tool_definition,
        "handler": get_logs_field_values.handle_call,
    },
    "get_teams": {
        "definition": get_teams.get_tool_definition,
        "handler": get_teams.handle_call,
    },
    "get_metrics": {
        "definition": get_metrics.get_tool_definition,
        "handler": get_metrics.handle_call,
    },
    "get_metric_fields": {
        "definition": get_metric_fields.get_tool_definition,
        "handler": get_metric_fields.handle_call,
    },
    "get_metric_field_values": {
        "definition": get_metric_field_values.get_tool_definition,
        "handler": get_metric_field_values.handle_call,
    },
    "list_metrics": {
        "definition": list_metrics.get_tool_definition,
        "handler": list_metrics.handle_call,
    },
    "list_service_definitions": {
        "definition": list_service_definitions.get_tool_definition,
        "handler": list_service_definitions.handle_call,
    },
    "get_service_definition": {
        "definition": get_service_definition.get_tool_definition,
        "handler": get_service_definition.handle_call,
    },
    "list_monitors": {
        "definition": list_monitors.get_tool_definition,
        "handler": list_monitors.handle_call,
    },
    "list_slos": {
        "definition": list_slos.get_tool_definition,
        "handler": list_slos.handle_call,
    },
}


async def handle_list_tools(
    ctx: ServerRequestContext,
    params: PaginatedRequestParams | None,
) -> ListToolsResult:
    """List available tools."""
    return ListToolsResult(
        tools=[tool_config["definition"]() for tool_config in TOOLS.values()]
    )


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: CallToolRequestParams,
) -> CallToolResult:
    """Handle tool calls."""
    tool_config = TOOLS.get(params.name)
    if tool_config is None:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {params.name}")],
            is_error=True,
        )

    try:
        return await tool_config["handler"](params)
    except Exception as e:
        logger.error(f"Error handling tool call: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            is_error=True,
        )


# Create MCP server instance
server = Server(
    SERVER_NAME,
    version=SERVER_VERSION,
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


async def async_main():
    """Async main entry point."""
    try:
        logger.info("Starting Datadog MCP Server...")
        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server transport initialized")
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        raise


def cli_main():
    """Main entry point for console scripts."""
    asyncio.run(async_main())


if __name__ == "__main__":
    cli_main()
