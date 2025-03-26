"""
Planning Agent - Manages Linear plans, evaluates progress, and determines next steps.

This agent is responsible for:
1. Creating and managing project plans in Linear
2. Evaluating progress and determining the next steps
3. Sending implementation requests to Slack
4. Updating Linear issues based on PR status
"""

import logging
import os
import re
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

import modal
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from agentgen import CodeAgent
from agentgen.extensions.linear.linear_client import LinearClient
from agentgen.extensions.langchain.tools import (
    LinearGetIssueTool,
    LinearGetIssueCommentsTool,
    LinearSearchIssuesTool,
    LinearGetTeamsTool,
    LinearGetIssueStatesTool,
    LinearCreateIssueTool,
    LinearUpdateIssueTool,
    LinearCommentOnIssueTool,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_DEFAULT_CHANNEL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "")
PLANNING_INTERVAL_MINUTES = int(os.getenv("PLANNING_INTERVAL_MINUTES", "60"))

class IssueState(Enum):
    """Enum representing different Linear issue states."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELED = "canceled"

class PlanningAgent:
    """
    Planning Agent that manages Linear plans, evaluates progress, and determines next steps.
    """
    def __init__(self):
        """Initialize the Planning Agent."""
        self.linear_client = LinearClient(LINEAR_API_KEY) if LINEAR_API_KEY else None
        self.slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
        
        # Cache for plan data
        self.plan_cache = {}
        
        # Cache for issue states
        self.issue_states = {}
        
        # Cache for team data
        self.teams_cache = {}
        
        # Initialize the event history for reflection
        self.event_history = []
        
        # Last planning time
        self.last_planning_time = datetime.now() - timedelta(minutes=PLANNING_INTERVAL_MINUTES)
        
        logger.info("Planning Agent initialized")
    
    def create_planning_agent(self) -> CodeAgent:
        """Create a code agent with Linear planning tools."""
        tools = [
            LinearGetIssueTool(self.linear_client),
            LinearGetIssueCommentsTool(self.linear_client),
            LinearSearchIssuesTool(self.linear_client),
            LinearGetTeamsTool(self.linear_client),
            LinearGetIssueStatesTool(self.linear_client),
            LinearCreateIssueTool(self.linear_client),
            LinearUpdateIssueTool(self.linear_client),
            LinearCommentOnIssueTool(self.linear_client),
        ]
        
        return CodeAgent(codebase=None, tools=tools)
    
    async def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams from Linear."""
        if not self.teams_cache:
            logger.info("Fetching teams from Linear")
            teams = self.linear_client.get_teams()
            self.teams_cache = {team.id: {"id": team.id, "name": team.name, "key": team.key} for team in teams}
        
        return list(self.teams_cache.values())
    
    async def get_issue_states(self, team_id: str) -> Dict[str, str]:
        """Get all issue states for a team."""
        if team_id not in self.issue_states:
            logger.info(f"Fetching issue states for team {team_id}")
            
            # In a real implementation, you would fetch the actual states from Linear
            # For now, we'll use a simplified set of states
            self.issue_states[team_id] = {
                "backlog": "state_id_for_backlog",
                "todo": "state_id_for_todo",
                "in_progress": "state_id_for_in_progress",
                "in_review": "state_id_for_in_review",
                "done": "state_id_for_done",
                "canceled": "state_id_for_canceled",
            }
        
        return self.issue_states[team_id]
    
    async def get_next_issue_to_implement(self, team_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get the next issue that should be implemented.
        
        Args:
            team_id: Linear team ID (optional)
            
        Returns:
            Issue data or None if no issues are ready
        """
        # Use default team ID if not provided
        team_id = team_id or LINEAR_TEAM_ID
        
        logger.info(f"Finding next issue to implement for team {team_id}")
        
        # Create planning agent
        agent = self.create_planning_agent()
        
        # Create prompt for finding next issue
        prompt = f"""
        Find the next issue that should be implemented for team ID: {team_id}
        
        Please analyze:
        1. Issues in the "todo" state
        2. Priority of each issue
        3. Dependencies between issues
        4. Team capacity and current workload
        
        Use the Linear tools to gather information about issues, their states, and relationships.
        Return the ID and details of the single most important issue that should be implemented next.
        """
        
        # Run the agent
        result = agent.run(prompt)
        
        # Parse the result to extract issue information
        # This is a simplified parsing, in a real implementation you might want to use a more robust approach
        issue_id_match = re.search(r'Issue ID:?\s*([A-Za-z0-9-]+)', result)
        if not issue_id_match:
            logger.info("No next issue found")
            return None
        
        issue_id = issue_id_match.group(1)
        
        # Get full issue details
        issue = self.linear_client.get_issue(issue_id)
        
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "priority": issue.priority,
            "team_id": issue.team_id or team_id,
        }
    
    async def update_issue_state(self, issue_id: str, state: IssueState) -> bool:
        """
        Update the state of an issue.
        
        Args:
            issue_id: Linear issue ID
            state: New state for the issue
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating issue {issue_id} to state {state.value}")
        
        try:
            # Get the issue to determine its team
            issue = self.linear_client.get_issue(issue_id)
            team_id = issue.team_id or LINEAR_TEAM_ID
            
            # Get the state ID for the given state name
            states = await self.get_issue_states(team_id)
            state_id = states.get(state.value)
            
            if not state_id:
                logger.error(f"Could not find state ID for {state.value}")
                return False
            
            # Update the issue state
            # In a real implementation, you would use the Linear API to update the issue
            # For now, we'll just log the update
            logger.info(f"Updated issue {issue_id} to state {state.value} (state_id: {state_id})")
            
            return True
        
        except Exception as e:
            logger.exception(f"Error updating issue state: {e}")
            return False
    
    async def send_implementation_request(self, issue: Dict[str, Any]) -> bool:
        """
        Send an implementation request to Slack.
        
        Args:
            issue: Issue data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.slack_client:
            logger.warning("Slack client not initialized")
            return False
        
        logger.info(f"Sending implementation request for issue {issue['id']}")
        
        try:
            # Format the message
            message = f"""
            🚀 *New Implementation Request*
            
            *Issue:* {issue['title']}
            *ID:* {issue['id']}
            
            *Description:*
            {issue['description'] or 'No description provided'}
            
            *Priority:* {issue['priority'] or 'Not specified'}
            
            Please implement this feature and create a PR.
            """
            
            # Send the message
            response = self.slack_client.chat_postMessage(
                channel=SLACK_DEFAULT_CHANNEL,
                text=message
            )
            
            # Update issue state to in progress
            await self.update_issue_state(issue['id'], IssueState.IN_PROGRESS)
            
            return response["ok"]
        
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    async def run_planning_cycle(self, force: bool = False) -> Dict[str, Any]:
        """
        Run a planning cycle to find and request implementation of the next issue.
        
        Args:
            force: Force a planning cycle even if the interval hasn't elapsed
            
        Returns:
            Result of the planning cycle
        """
        now = datetime.now()
        
        # Check if it's time to run a planning cycle
        if not force and (now - self.last_planning_time).total_seconds() < PLANNING_INTERVAL_MINUTES * 60:
            time_to_next = self.last_planning_time + timedelta(minutes=PLANNING_INTERVAL_MINUTES) - now
            logger.info(f"Skipping planning cycle, next cycle in {time_to_next.total_seconds() / 60:.1f} minutes")
            return {"status": "skipped", "next_cycle_in_minutes": time_to_next.total_seconds() / 60}
        
        logger.info("Running planning cycle")
        
        # Update last planning time
        self.last_planning_time = now
        
        try:
            # Find the next issue to implement
            next_issue = await self.get_next_issue_to_implement()
            
            if not next_issue:
                logger.info("No issues ready for implementation")
                return {"status": "no_issues"}
            
            # Send implementation request
            success = await self.send_implementation_request(next_issue)
            
            if not success:
                logger.error("Failed to send implementation request")
                return {"status": "error", "message": "Failed to send implementation request"}
            
            logger.info(f"Successfully requested implementation of issue {next_issue['id']}")
            return {
                "status": "success",
                "issue_id": next_issue['id'],
                "issue_title": next_issue['title']
            }
        
        except Exception as e:
            logger.exception(f"Error in planning cycle: {e}")
            return {"status": "error", "message": str(e)}
    
    async def handle_pr_merged(self, repo: str, pr_number: int, issue_id: str = None) -> Dict[str, Any]:
        """
        Handle a PR being merged by updating the corresponding issue and planning the next step.
        
        Args:
            repo: Repository string in format "owner/repo"
            pr_number: PR number
            issue_id: Linear issue ID (optional, will be extracted from PR if not provided)
            
        Returns:
            Result of the operation
        """
        logger.info(f"Handling merged PR #{pr_number} in {repo}")
        
        try:
            # If issue_id not provided, extract it from PR description or title
            if not issue_id:
                # In a real implementation, you would fetch the PR and extract the issue ID
                # For now, we'll just log that we couldn't find an issue ID
                logger.warning(f"No issue ID provided for PR #{pr_number}")
                return {"status": "error", "message": "No issue ID provided"}
            
            # Update issue state to done
            success = await self.update_issue_state(issue_id, IssueState.DONE)
            
            if not success:
                logger.error(f"Failed to update issue {issue_id} state")
                return {"status": "error", "message": f"Failed to update issue {issue_id} state"}
            
            # Add comment to issue
            self.linear_client.comment_on_issue(
                issue_id,
                f"✅ Implementation completed and merged in PR #{pr_number} ({repo})"
            )
            
            # Run a planning cycle to find the next issue
            planning_result = await self.run_planning_cycle(force=True)
            
            return {
                "status": "success",
                "issue_id": issue_id,
                "planning_result": planning_result
            }
        
        except Exception as e:
            logger.exception(f"Error handling merged PR: {e}")
            return {"status": "error", "message": str(e)}

# Initialize the Planning Agent
planning_agent = PlanningAgent()

# Modal app setup for scheduled planning
app = modal.App("planning-agent")

@app.function(
    schedule=modal.Period(minutes=PLANNING_INTERVAL_MINUTES),
    secrets=[modal.Secret.from_dotenv()]
)
async def scheduled_planning():
    """Run a planning cycle on a schedule."""
    logger.info("Running scheduled planning cycle")
    return await planning_agent.run_planning_cycle()

@app.function(secrets=[modal.Secret.from_dotenv()])
async def handle_pr_merged_endpoint(repo: str, pr_number: int, issue_id: str = None):
    """Endpoint for handling merged PRs."""
    logger.info(f"Handling merged PR #{pr_number} in {repo}")
    return await planning_agent.handle_pr_merged(repo, pr_number, issue_id)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def get_next_issue_endpoint(team_id: str = None):
    """Endpoint for getting the next issue to implement."""
    logger.info(f"Getting next issue for team {team_id or LINEAR_TEAM_ID}")
    return await planning_agent.get_next_issue_to_implement(team_id)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def force_planning_cycle():
    """Endpoint for forcing a planning cycle."""
    logger.info("Forcing planning cycle")
    return await planning_agent.run_planning_cycle(force=True)

if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        result = await planning_agent.run_planning_cycle(force=True)
        print(f"Planning cycle result: {result}")
    
    asyncio.run(main())