# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.0.7] - 2026-08-27

### Changed
- **MCP SDK 2.x support**
  - Requires `mcp>=2.1.1`; the server no longer starts on the 1.x SDK
  - Replaced the removed `@server.list_tools()` / `@server.call_tool()` decorators with the
    `on_list_tools` / `on_call_tool` constructor handlers
  - Tool handlers now receive `CallToolRequestParams` directly and return `CallToolResult`
    unchanged, removing the internal `MockRequest` shim and content-unwrapping
  - Server capabilities are derived via `create_initialization_options()` instead of being
    hand-built
  - Renamed model fields to their SDK 2.x names: `inputSchema` -> `input_schema`,
    `isError` -> `is_error`

### Fixed
- `get_logs_field_values` no longer raises `AttributeError` when called with no arguments
- Unknown tool names now return `is_error=True` instead of a successful result

## [v0.0.6] - 2025-07-14

### Added
- **Enhanced Log Processing**
  - Enhanced log extraction to support new content format with additional attributes
  - Added new tool for retrieving field values from Datadog APIs
  - Improved log parsing capabilities for better data extraction

### Changed
- **Dependency Updates**
  - Upgraded to proper official Datadog SDK client
  - Updated Datadog API client dependencies
  - Improved MCP server self-referencing configuration

### Technical
- Merged PR #3 for enhanced error pattern detection
- Enhanced log content format handling
- Added support for additional log attributes extraction

## [v0.0.5] - 2025-06-27

### Added
- **Monitoring & Alerting Tools**
  - `list_monitors` - List all Datadog monitors with filtering by name, tags, and monitor tags
  - `list_slos` - List Service Level Objectives with filtering by name, tags, and query support
  - Comprehensive filtering options for both monitors and SLOs
  - Multiple output formats (table, json, summary) for monitoring tools

### Enhanced
- Extended tool registry in server.py with new monitoring capabilities
- Updated README with monitoring tools documentation
- Added examples for monitor and SLO management usage

### Technical
- New API endpoints: `/api/v1/monitor` and `/api/v1/slo`
- Enhanced Datadog API client with monitor and SLO support
- Improved pagination handling for large monitor/SLO datasets

## [v0.0.4] - 2025-06-18

### Added
- **CircleCI CI/CD Pipeline**
  - Comprehensive test suite for pull requests (syntax check, package structure, UVX installation, lint check, configuration validation, documentation check)
  - Manual release workflow with semver validation, changelog validation, package building, and GitHub release creation
  - Automatic release detection when changelog contains new versions not yet tagged in GitHub
- UVX support for direct installation from GitHub
- Comprehensive versioning documentation
- Console script entry points for CLI usage
- Proper Python package structure

### Changed
- **Package renamed from "ddmcp" to "datadog-mcp"**
- **Console script renamed from "ddmcp" to "datadog-mcp"**
- **UVX is now the recommended installation method**
- Restructured project as proper Python package in `ddmcp/` directory
- Updated all imports to use relative imports
- Enhanced README with UVX installation methods and versioning examples
- Simplified installation documentation (removed Docker Hub/Compose as primary options)

### Fixed
- Fixed regex pattern in auto-release version detection for reliable changelog parsing
- Corrected semver validation for CircleCI environment compatibility

### Technical
- Added `[project.scripts]` entry point in pyproject.toml
- Created sync wrapper function for async main
- Multi-architecture Docker builds (AMD64/ARM64)
- Comprehensive CI/CD configuration with both manual and automatic release triggers
- Changelog-driven release automation with version detection and GitHub integration 

## [v0.0.3] - 2025-06-16

### Added
- **Service Definitions Management**
  - `list_service_definitions` - List all service definitions with pagination and filtering
  - `get_service_definition` - Retrieve detailed service definition by name
  - Support for schema versions (v1, v2, v2.1, v2.2) with v2.2 as default
  - Multiple output formats (table, json, yaml, formatted)
- Service definition API client functions in `utils/datadog_client.py`

### Enhanced
- Updated README with service definition tools documentation
- Added examples for service definition usage
- Extended tool registry in server.py

### Technical
- New API endpoints: `/api/v2/services/definitions` and `/api/v2/services/definitions/{service_name}`
- Comprehensive service metadata parsing (team, contacts, links, integrations)

## [v0.0.2] - 2025-06-16

### Added
- **Enhanced Metrics System**
  - `list_metrics` - Discover available metrics with filtering
  - `get_metric_fields` - Get available fields/tags for metrics
  - `get_metric_field_values` - Get all values for specific metric fields
  - Dynamic field discovery and validation
- **Improved Logging**
  - `get_logs` - Flexible log retrieval with comprehensive filtering
  - Support for multiple environments, log levels, and time ranges
  - Enhanced log formatting options

### Changed
- Replaced `get_service_logs` and `get_service_metrics` with more flexible generic tools
- Improved error handling and user feedback
- Enhanced API client with better field discovery
- Reorganized tests into dedicated `tests/` directory

### Fixed
- Multi-environment query building with proper OR logic
- Zero-result handling with field suggestions
- Metric aggregation field validation

### Technical
- Added `/api/v2/metrics` endpoint for metric discovery
- Implemented `/api/v2/metrics/{metric_name}/all-tags` for field discovery
- Backward compatibility maintained through wrapper functions

## [v0.0.1] - 2025-06-14 (Initial Release)

### Added
- **Core MCP Server Framework**
  - Async MCP server with stdio transport
  - Tool registration and routing system
  - Comprehensive error handling and logging

- **CI/CD Pipeline Management**
  - `list_ci_pipelines` - List and filter CI pipelines
  - `get_pipeline_fingerprints` - Extract fingerprints for Terraform integration
  - Repository and pipeline name filtering

- **Service Monitoring**
  - `get_service_logs` - Retrieve service logs with environment filtering
  - `get_service_metrics` - Query service metrics with aggregation
  - Multi-environment support (prod, staging, backoffice)
  - Time range filtering (1h to 30d)

- **Team Management**
  - `get_teams` - List teams and member details
  - Team filtering and membership information

- **Data Formatting & Analysis**
  - Multiple output formats (table, json, summary, timeseries)
  - Statistical analysis for metrics (min, max, avg, latest)
  - Configurable data presentation

- **Datadog Integration**
  - Complete API client for Datadog v1 and v2 APIs
  - Authentication via DD_API_KEY and DD_APP_KEY
  - Support for CI pipelines, logs, metrics, and teams endpoints

- **Docker Support**
  - Multi-platform Docker support (AMD64/ARM64)
  - Docker Compose configuration
  - Multi-stage builds with UV package manager
  - Comprehensive installation methods

### Technical Details
- **Architecture**: Modular tool-based pattern with centralized registration
- **Dependencies**: MCP 1.9.4+, httpx, datadog-api-client
- **Python**: Requires Python 3.13+
- **Environment**: Configurable via environment variables
- **Testing**: Comprehensive test suite for all major components

### Documentation
- Complete README with installation, configuration, and usage examples
- Tool-specific documentation with parameter descriptions
- Claude Desktop integration examples
- API credential setup instructions
- Method comparison table for different deployment approaches

---

## Version History Summary

- **v0.0.5**: Monitoring & Alerting Tools (Monitors & SLOs)
- **v0.0.4**: CI/CD Pipeline & UVX Support
- **v0.0.3**: Service Definitions Management
- **v0.0.2**: Enhanced Metrics & Logging System  
- **v0.0.1**: Initial Release with Core MCP Server, Docker Support

## Migration Notes

### From v0.0.2 to v0.0.3
- No breaking changes
- New service definition tools available alongside existing tools

### From v0.0.1 to v0.0.2
- **Breaking Changes**: 
  - `get_service_logs` → `get_logs` (more flexible filtering)
  - `get_service_metrics` → `get_metrics` (supports any metric, not just service metrics)
- **Migration**: Update tool names in integrations, new tools have enhanced capabilities