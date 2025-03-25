"""Tests for Linear tools."""

import os

import pytest
import requests

from codegen.extensions.linear.linear_client import LinearClient
from codegen.extensions.tools.linear.linear import (
    linear_comment_on_issue_tool,
    linear_create_issue_tool,
    linear_get_issue_comments_tool,
    linear_get_issue_tool,
    linear_get_teams_tool,
    linear_search_issues_tool,
)


@pytest.fixture
def client() -> LinearClient:
    """Create a Linear client for testing."""
    token = os.getenv("LINEAR_ACCESS_TOKEN")
    if not token:
        pytest.skip("LINEAR_ACCESS_TOKEN environment variable not set")
    team_id = os.getenv("LINEAR_TEAM_ID")
    if not team_id:
        pytest.skip("LINEAR_TEAM_ID environment variable not set")
    return LinearClient(token, team_id)


def test_linear_get_issue(client: LinearClient) -> None:
    """Test getting an issue from Linear."""
    # Link to issue: https://linear.app/codegen-sh/issue/CG-10775/read-file-and-reveal-symbol-tool-size-limits
    result = linear_get_issue_tool(client, "CG-10775")
    assert result.status == "success"
    assert result.issue_id == "CG-10775"
    assert result.issue_data["id"] == "d5a7d6db-e20d-4d67-98f8-acedef6d3536"


def test_linear_get_issue_comments(client: LinearClient) -> None:
    """Test getting comments for an issue from Linear."""
    result = linear_get_issue_comments_tool(client, "CG-10775")
    assert result.status == "success"
    assert result.issue_id == "CG-10775"
    assert len(result.comments) > 1


def test_linear_comment_on_issue(client: LinearClient) -> None:
    """Test commenting on a Linear issue."""
    test_comment = "Test comment from automated testing"
    result = linear_comment_on_issue_tool(client, "CG-10775", test_comment)
    assert result.status == "success"
    assert result.issue_id == "CG-10775"
    assert result.comment["body"] == test_comment


def test_search_issues(client: LinearClient) -> None:
    """Test searching for issues in Linear."""
    result = linear_search_issues_tool(client, "REVEAL_SYMBOL")
    assert result.status == "success"
    assert result.query == "REVEAL_SYMBOL"
    assert len(result.issues) > 0


def test_create_issue(client: LinearClient) -> None:
    """Test creating an issue in Linear."""
    # Test creating an issue with explicit team_id
    title = "Test Issue - Automated Testing (Explicit Team)"
    description = "This is a test issue created by automated testing with explicit team_id"

    issue = client.create_issue(title, description)
    assert issue.title == title
    assert issue.description == description

    # Test creating an issue using default team_id from environment
    title2 = "Test Issue - Automated Testing (Default Team)"
    description2 = "This is a test issue created by automated testing with default team_id"

    issue2 = client.create_issue(title2, description2)
    assert issue2.title == title2
    assert issue2.description == description2

    # Test the tool wrapper with default team_id
    result = linear_create_issue_tool(client, "Test Tool Issue", "Test description from tool")
    assert result.status == "success"
    assert result.title == "Test Tool Issue"
    assert result.issue_data["title"] == "Test Tool Issue"
    assert result.issue_data["description"] == "Test description from tool"


def test_get_teams(client: LinearClient) -> None:
    """Test getting teams from Linear."""
    result = linear_get_teams_tool(client)
    assert result.status == "success"
    assert len(result.teams) > 0

    # Verify team structure
    team = result.teams[0]
    assert "id" in team
    assert "name" in team
    assert "key" in team


def test_linear_get_issue_network_error(client):
    """Test handling of network errors."""
    # Setup mock to raise network error
    client.get_issue.side_effect = requests.exceptions.ConnectionError("Network error")

    # Call function
    result = linear_get_issue_tool(client, "TEST-123")

    # Verify
    assert result.status == "error"
    assert "Network error" in result.error
    assert result.issue_id == "TEST-123"
    assert result.issue_data == {}
