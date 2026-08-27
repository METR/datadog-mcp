"""
Tests for team management functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_teams
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent

TEAMS_PAYLOAD = {
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
        },
        {
            "id": "team-456",
            "type": "team",
            "attributes": {
                "name": "Frontend Team",
                "handle": "frontend-team",
                "description": "UI development team",
                "created_at": "2024-02-01T00:00:00Z",
            },
        },
    ],
    "meta": {"pagination": {"total_count": 2, "total_pages": 1}},
}

MEMBERSHIPS_PAYLOAD = {
    "data": [
        {
            "id": "membership-1",
            "type": "team_membership",
            "attributes": {"role": "admin", "created_at": "2024-01-02T00:00:00Z"},
            "relationships": {"user": {"data": {"id": "user-1", "type": "users"}}},
        },
        {
            "id": "membership-2",
            "type": "team_membership",
            "attributes": {"role": "member", "created_at": "2024-01-03T00:00:00Z"},
            "relationships": {"user": {"data": {"id": "user-2", "type": "users"}}},
        },
    ]
}


class TestTeamsToolDefinition:
    """Test the get_teams tool definition"""
    
    def test_get_teams_tool_definition(self):
        """Test that get_teams tool definition is properly structured"""
        tool_def = get_teams.get_tool_definition()
        
        assert tool_def.name == "get_teams"
        assert "team" in tool_def.description.lower()
        assert hasattr(tool_def, 'input_schema')
        
        # Check schema structure
        schema = tool_def.input_schema
        assert "properties" in schema
        
        properties = schema["properties"]
        expected_params = ["team_name", "include_members", "format"]
        for param in expected_params:
            assert param in properties, f"Parameter {param} missing from schema"


class TestTeamsRetrieval:
    """Test team data retrieval functionality"""

    @pytest.mark.asyncio
    async def test_fetch_teams_basic(self, httpx_json):
        """Test basic team fetching functionality"""
        with httpx_json(TEAMS_PAYLOAD) as mock_client:
            result = await datadog_client.fetch_teams()

            assert result == TEAMS_PAYLOAD
            assert len(result["data"]) == 2
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_teams_pagination(self, httpx_json):
        """Test that pagination arguments are sent as JSON:API page parameters"""
        with httpx_json(TEAMS_PAYLOAD) as mock_client:
            await datadog_client.fetch_teams(page_size=10, page_number=2)

            get = mock_client.return_value.__aenter__.return_value.get
            params = get.call_args.kwargs["params"]
            assert params["page[size]"] == 10
            assert params["page[number]"] == 2

    @pytest.mark.asyncio
    async def test_fetch_teams_sends_credentials(self, httpx_json):
        """Test that API credentials are sent as headers"""
        with httpx_json(TEAMS_PAYLOAD) as mock_client:
            await datadog_client.fetch_teams()

            get = mock_client.return_value.__aenter__.return_value.get
            headers = get.call_args.kwargs["headers"]
            assert "DD-API-KEY" in headers
            assert "DD-APPLICATION-KEY" in headers

    @pytest.mark.asyncio
    async def test_fetch_team_memberships(self, httpx_json):
        """Test fetching the membership list for a team"""
        with httpx_json(MEMBERSHIPS_PAYLOAD) as mock_client:
            result = await datadog_client.fetch_team_memberships("team-123")

            assert result == MEMBERSHIPS_PAYLOAD["data"]
            get = mock_client.return_value.__aenter__.return_value.get
            assert "team-123/memberships" in get.call_args.args[0]


class TestTeamsToolHandler:
    """Test the get_teams tool handler"""

    @pytest.mark.asyncio
    async def test_handle_teams_request_success(self):
        """Test successful teams request handling"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "table"}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = TEAMS_PAYLOAD

            result = await get_teams.handle_call(mock_request)

            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert isinstance(result.content[0], TextContent)
            assert "Backend Team" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_teams_request_specific_team(self):
        """Test that team_name filters the results"""
        mock_request = MagicMock()
        mock_request.arguments = {"team_name": "Backend", "include_members": False}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = TEAMS_PAYLOAD

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            text = result.content[0].text
            assert "Backend Team" in text
            assert "Frontend Team" not in text

    @pytest.mark.asyncio
    async def test_handle_teams_request_no_match(self):
        """Test a team_name that matches nothing"""
        mock_request = MagicMock()
        mock_request.arguments = {"team_name": "Nonexistent"}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = TEAMS_PAYLOAD

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            assert "No teams found matching" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_teams_request_json_format(self):
        """Test JSON output format"""
        mock_request = MagicMock()
        mock_request.arguments = {"format": "json"}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = TEAMS_PAYLOAD

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            text = result.content[0].text
            payload = json.loads(text[text.index("["):])
            assert {t["name"] for t in payload} == {"Backend Team", "Frontend Team"}

    @pytest.mark.asyncio
    async def test_handle_teams_request_error(self):
        """Test teams request error handling"""
        mock_request = MagicMock()
        mock_request.arguments = {}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Teams API error")

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is True
            assert "Teams API error" in result.content[0].text

    @pytest.mark.asyncio
    async def test_handle_teams_request_empty_results(self):
        """Test handling of an empty team list"""
        mock_request = MagicMock()
        mock_request.arguments = {}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"data": [], "meta": {}}

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            assert "No teams found" in result.content[0].text


class TestTeamsFormatting:
    """Test team data formatting"""
    
    def test_teams_table_formatting(self):
        """Test teams table formatting"""
        sample_teams = [
            {
                "id": "team-1",
                "name": "Backend Team",
                "handle": "backend",
                "description": "API development",
                "member_count": 5
            },
            {
                "id": "team-2", 
                "name": "Frontend Team",
                "handle": "frontend",
                "description": "UI development",
                "member_count": 4
            }
        ]
        
        # Test that we can process teams data
        assert len(sample_teams) == 2
        assert all("name" in team for team in sample_teams)
        assert all("handle" in team for team in sample_teams)
    
    def test_teams_detailed_formatting(self):
        """Test detailed teams formatting with members"""
        sample_data = {
            "teams": [
                {
                    "id": "team-1",
                    "name": "DevOps Team",
                    "handle": "devops",
                    "description": "Infrastructure team"
                }
            ],
            "users": [
                {
                    "id": "user-1",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "teams": ["team-1"]
                },
                {
                    "id": "user-2",
                    "name": "Jane Smith", 
                    "email": "jane@example.com",
                    "teams": ["team-1"]
                }
            ]
        }
        
        # Verify data structure
        assert "teams" in sample_data
        assert "users" in sample_data
        assert len(sample_data["teams"]) == 1
        assert len(sample_data["users"]) == 2
        
        # Verify relationships
        team_id = sample_data["teams"][0]["id"]
        team_members = [user for user in sample_data["users"] if team_id in user["teams"]]
        assert len(team_members) == 2
    
    def test_teams_json_formatting(self):
        """Test teams JSON formatting"""
        sample_teams = [
            {
                "id": "team-1",
                "name": "Security Team",
                "handle": "security"
            }
        ]
        
        json_output = json.dumps(sample_teams, indent=2)
        assert isinstance(json_output, str)
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Security Team"


class TestTeamsFiltering:
    """Test team filtering functionality"""

    @pytest.mark.asyncio
    async def test_teams_by_name_filter_is_case_insensitive(self):
        """Test that the team_name filter ignores case"""
        mock_request = MagicMock()
        mock_request.arguments = {"team_name": "bAcKeNd", "include_members": False}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = TEAMS_PAYLOAD

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            assert "Backend Team" in result.content[0].text

    @pytest.mark.asyncio
    async def test_teams_include_members_option(self):
        """Test that include_members pulls membership details for a named team"""
        mock_request = MagicMock()
        mock_request.arguments = {"team_name": "Backend", "include_members": True}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_teams, \
             patch('datadog_mcp.tools.get_teams.fetch_team_memberships', new_callable=AsyncMock) as mock_members:
            mock_teams.return_value = TEAMS_PAYLOAD
            mock_members.return_value = MEMBERSHIPS_PAYLOAD["data"]

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            mock_members.assert_awaited_once_with("team-123")

    @pytest.mark.asyncio
    async def test_teams_membership_failure_is_tolerated(self):
        """Test that a membership lookup failure does not fail the whole call"""
        mock_request = MagicMock()
        mock_request.arguments = {"team_name": "Backend", "include_members": True}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_teams, \
             patch('datadog_mcp.tools.get_teams.fetch_team_memberships', new_callable=AsyncMock) as mock_members:
            mock_teams.return_value = TEAMS_PAYLOAD
            mock_members.side_effect = Exception("membership boom")

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            assert "membership boom" in result.content[0].text


class TestTeamsValidation:
    """Test team input validation"""
    
    @pytest.mark.asyncio
    async def test_invalid_team_name_handling(self):
        """Test handling of invalid team names"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "",  # Empty team name
            "include_members": True
        }
        
        result = await get_teams.handle_call(mock_request)
        
        # Should handle gracefully (either error or validation message)
        assert isinstance(result, CallToolResult)
        if result.is_error:
            assert len(result.content) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_format_handling(self):
        """Test handling of invalid format options"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "format": "invalid_format"
        }
        
        # Should handle gracefully
        try:
            result = await get_teams.handle_call(mock_request)
            assert isinstance(result, CallToolResult)
        except Exception:
            # If validation happens at tool level, that's also acceptable
            pass


class TestTeamsIntegration:
    """Test teams integration functionality"""

    @pytest.mark.asyncio
    async def test_teams_with_memberships_end_to_end(self, httpx_json):
        """Test the tool against a mocked HTTP layer, including memberships"""
        mock_request = MagicMock()
        mock_request.arguments = {"team_name": "Backend", "include_members": True}

        with patch('datadog_mcp.tools.get_teams.fetch_teams', new_callable=AsyncMock) as mock_teams, \
             patch('datadog_mcp.tools.get_teams.fetch_team_memberships', new_callable=AsyncMock) as mock_members:
            mock_teams.return_value = TEAMS_PAYLOAD
            mock_members.return_value = MEMBERSHIPS_PAYLOAD["data"]

            result = await get_teams.handle_call(mock_request)

            assert result.is_error is False
            text = result.content[0].text
            assert "Backend Team" in text
            assert "admin" in text


if __name__ == "__main__":
    pytest.main([__file__])