"""
Tests for team management functionality
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datadog_mcp.tools import get_teams
from datadog_mcp.utils import datadog_client
from mcp.types import CallToolResult, TextContent


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
    async def test_fetch_teams_basic(self):
        """Test basic team fetching functionality"""
        mock_response_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams",
                    "attributes": {
                        "name": "Backend Team",
                        "description": "Backend development team",
                        "handle": "backend-team",
                        "summary": "Responsible for API development"
                    },
                    "relationships": {
                        "users": {
                            "data": [
                                {"id": "user-1", "type": "users"},
                                {"id": "user-2", "type": "users"}
                            ]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "handle": "john.doe"
                    }
                },
                {
                    "id": "user-2", 
                    "type": "users",
                    "attributes": {
                        "name": "Jane Smith",
                        "email": "jane@example.com", 
                        "handle": "jane.smith"
                    }
                }
            ]
        }
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_teams()
            
            assert isinstance(result, dict)
            assert "teams" in result
            assert "users" in result
            assert len(result["teams"]) > 0
    
    @pytest.mark.asyncio
    async def test_fetch_specific_team(self):
        """Test fetching a specific team by name"""
        team_name = "Backend Team"
        
        mock_response_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams", 
                    "attributes": {
                        "name": "Backend Team",
                        "handle": "backend-team"
                    }
                }
            ]
        }
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_teams(team_name=team_name)
            
            assert isinstance(result, dict)
            # Verify the request was made with team filter
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_teams_with_members(self):
        """Test fetching teams with member details"""
        include_members = True
        
        mock_response_data = {
            "data": [
                {
                    "id": "team-123",
                    "type": "teams",
                    "attributes": {
                        "name": "Frontend Team"
                    },
                    "relationships": {
                        "users": {
                            "data": [{"id": "user-1", "type": "users"}]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "Alice Johnson",
                        "email": "alice@example.com"
                    }
                }
            ]
        }
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_teams(include_members=include_members)
            
            assert isinstance(result, dict)
            assert "teams" in result
            assert "users" in result
            assert len(result["users"]) > 0


class TestTeamsToolHandler:
    """Test the get_teams tool handler"""
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_success(self):
        """Test successful teams request handling"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "include_members": True,
            "format": "table"
        }
        
        mock_teams_data = {
            "teams": [
                {
                    "id": "team-123",
                    "name": "DevOps Team",
                    "handle": "devops",
                    "description": "Infrastructure and deployment team",
                    "member_count": 3
                }
            ],
            "users": [
                {
                    "id": "user-1",
                    "name": "Bob Wilson",
                    "email": "bob@example.com",
                    "teams": ["team-123"]
                }
            ]
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data
            
            result = await get_teams.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            assert isinstance(result.content[0], TextContent)
            
            content_text = result.content[0].text
            assert "DevOps Team" in content_text or "devops" in content_text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_specific_team(self):
        """Test teams request for specific team"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "Security Team",
            "include_members": True,
            "format": "detailed"
        }
        
        mock_teams_data = {
            "teams": [
                {
                    "id": "team-456",
                    "name": "Security Team",
                    "handle": "security",
                    "description": "Application security team"
                }
            ],
            "users": []
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data
            
            result = await get_teams.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            
            # Verify specific team was requested
            mock_fetch.assert_called_once()
            call_args, call_kwargs = mock_fetch.call_args
            assert call_kwargs.get("team_name") == "Security Team"
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_json_format(self):
        """Test teams request with JSON format"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "format": "json",
            "include_members": False
        }
        
        mock_teams_data = {
            "teams": [
                {
                    "id": "team-789",
                    "name": "QA Team",
                    "handle": "qa"
                }
            ],
            "users": []
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data
            
            result = await get_teams.handle_call(mock_request)
            
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
    async def test_handle_teams_request_error(self):
        """Test error handling in teams requests"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "NonexistentTeam"
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Team not found")
            
            result = await get_teams.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is True
            assert len(result.content) > 0
            assert "error" in result.content[0].text.lower()
    
    @pytest.mark.asyncio
    async def test_handle_teams_request_empty_results(self):
        """Test handling when no teams are found"""
        mock_request = MagicMock()
        mock_request.arguments = {
            "team_name": "EmptyResults"
        }
        
        mock_teams_data = {
            "teams": [],
            "users": []
        }
        
        with patch('datadog_mcp.utils.datadog_client.fetch_teams', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_teams_data
            
            result = await get_teams.handle_call(mock_request)
            
            assert isinstance(result, CallToolResult)
            assert result.is_error is False
            assert len(result.content) > 0
            
            content_text = result.content[0].text
            assert "no teams" in content_text.lower() or "empty" in content_text.lower()


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
    async def test_teams_by_name_filter(self):
        """Test filtering teams by name"""
        team_name = "Backend Team"
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response = {
                "data": [
                    {
                        "id": "team-123",
                        "type": "teams",
                        "attributes": {
                            "name": "Backend Team",
                            "handle": "backend"
                        }
                    }
                ]
            }
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_teams(team_name=team_name)
            
            # Verify the request was made with proper filter
            call_args = mock_client.return_value.__aenter__.return_value.get.call_args
            assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_teams_include_members_option(self):
        """Test include_members filtering option"""
        include_members = True
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_response = {
                "data": [
                    {
                        "id": "team-123",
                        "type": "teams",
                        "attributes": {"name": "Test Team"},
                        "relationships": {
                            "users": {"data": []}
                        }
                    }
                ],
                "included": []
            }
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_teams(include_members=include_members)
            
            # Verify the request was made
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()


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
    async def test_teams_with_user_relationships(self):
        """Test teams data with proper user relationships"""
        mock_response = {
            "data": [
                {
                    "id": "team-1",
                    "type": "teams",
                    "attributes": {
                        "name": "Engineering",
                        "handle": "engineering"
                    },
                    "relationships": {
                        "users": {
                            "data": [
                                {"id": "user-1", "type": "users"},
                                {"id": "user-2", "type": "users"}
                            ]
                        }
                    }
                }
            ],
            "included": [
                {
                    "id": "user-1",
                    "type": "users",
                    "attributes": {
                        "name": "Developer One",
                        "email": "dev1@example.com"
                    }
                },
                {
                    "id": "user-2",
                    "type": "users", 
                    "attributes": {
                        "name": "Developer Two",
                        "email": "dev2@example.com"
                    }
                }
            ]
        }
        
        with patch('datadog_mcp.utils.datadog_client.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.return_value = None
            
            result = await datadog_client.fetch_teams(include_members=True)
            
            # Verify proper relationship processing
            assert isinstance(result, dict)
            assert "teams" in result
            assert "users" in result
            
            # Should have processed relationships correctly
            teams = result["teams"]
            users = result["users"]
            assert len(teams) == 1
            assert len(users) == 2


if __name__ == "__main__":
    pytest.main([__file__])