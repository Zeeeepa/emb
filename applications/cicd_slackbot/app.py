"""
CICD SlackChatbot - An intelligent agent that manages the CI/CD cycle by:
1. Analyzing GitHub PRs and providing feedback
2. Reflecting on overall plan goals (from Linear)
3. Suggesting next steps based on plan progress
4. Sending requests via Slack to continue the development cycle
"""

import logging
import os
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import modal
from fastapi import Request, BackgroundTasks
from github import Github
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from codegen import Codebase
from codegen.configs.models.secrets import SecretsConfig
from agentgen import CodeAgent
from agentgen.extensions.events.codegen_app import CodegenApp
from agentgen.extensions.github.types.events.pull_request import (
    PullRequestOpenedEvent,
    PullRequestClosedEvent,
    PullRequestMergedEvent,
    PullRequestReviewSubmittedEvent
)
from agentgen.extensions.linear.types import LinearEvent, LinearIssueCreatedEvent, LinearIssueUpdatedEvent
from agentgen.extensions.slack.types import SlackEvent
from agentgen.extensions.linear.linear_client import LinearClient
from agentgen.extensions.langchain.tools import (
    # GitHub tools
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
    GithubCreatePRTool,
    # Linear tools
    LinearGetIssueTool,
    LinearGetIssueCommentsTool,
    LinearSearchIssuesTool,
    LinearGetTeamsTool,
    LinearGetIssueStatesTool,
    LinearCreateIssueTool,
    LinearUpdateIssueTool,
    LinearCommentOnIssueTool,
    # Code analysis tools
    ViewFileTool,
    ListDirectoryTool,
    RipGrepTool,
    SemanticSearchTool,
    RevealSymbolTool,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")
LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_DEFAULT_CHANNEL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "")

# Create the base image with dependencies
base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install(
        "codegen>=0.6.1",
        "openai>=1.1.0",
        "anthropic>=0.5.0",
        "fastapi[standard]",
        "slack_sdk",
        "pygithub",
        "linear-sdk",
    )
)

# Create the app
app = CodegenApp(
    name="cicd-slackbot",
    image=base_image,
    modal_api_key=os.getenv("MODAL_API_KEY", "")
)

class CICDSlackbot:
    """
    CICD Slackbot that manages the CI/CD cycle by analyzing PRs, reflecting on plan goals,
    and suggesting next steps.
    """
    def __init__(self):
        self.github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
        self.linear_client = LinearClient() if LINEAR_API_KEY else None
        self.slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
        
        # Cache for repository codebases
        self.repo_cache = {}
        
        # Cache for plan goals and progress
        self.plan_cache = {}
        
        # Initialize the event history for reflection
        self.event_history = []
        
        logger.info("CICD Slackbot initialized")
    
    def get_codebase(self, repo_str: str) -> Codebase:
        """Get a codebase for a repository, using cache if available."""
        if repo_str in self.repo_cache:
            logger.info(f"Using cached codebase for {repo_str}")
            return self.repo_cache[repo_str]
        
        logger.info(f"Initializing new codebase for {repo_str}")
        codebase = Codebase.from_repo(
            repo_str,
            secrets=SecretsConfig(github_token=GITHUB_TOKEN)
        )
        self.repo_cache[repo_str] = codebase
        return codebase
    
    def create_pr_analysis_agent(self, repo_str: str) -> CodeAgent:
        """Create an agent for PR analysis."""
        codebase = self.get_codebase(repo_str)
        
        tools = [
            # GitHub tools
            GithubViewPRTool(codebase),
            GithubCreatePRCommentTool(codebase),
            GithubCreatePRReviewCommentTool(codebase),
            
            # Code analysis tools
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            RipGrepTool(codebase),
            SemanticSearchTool(codebase),
            RevealSymbolTool(codebase),
        ]
        
        return CodeAgent(codebase=codebase, tools=tools)
    
    def create_plan_reflection_agent(self) -> CodeAgent:
        """Create an agent for plan reflection."""
        # Use a dummy codebase for tools that require it
        dummy_codebase = Codebase.from_repo(DEFAULT_REPO) if DEFAULT_REPO else None
        
        tools = [
            # Linear tools
            LinearGetIssueTool(self.linear_client),
            LinearGetIssueCommentsTool(self.linear_client),
            LinearSearchIssuesTool(self.linear_client),
            LinearGetTeamsTool(self.linear_client),
            LinearGetIssueStatesTool(self.linear_client),
        ]
        
        return CodeAgent(codebase=dummy_codebase, tools=tools)
    
    def create_next_step_agent(self, repo_str: str) -> CodeAgent:
        """Create an agent for suggesting next steps."""
        codebase = self.get_codebase(repo_str)
        
        tools = [
            # Linear tools
            LinearGetIssueTool(self.linear_client),
            LinearGetIssueCommentsTool(self.linear_client),
            LinearSearchIssuesTool(self.linear_client),
            LinearCreateIssueTool(self.linear_client),
            LinearUpdateIssueTool(self.linear_client),
            LinearCommentOnIssueTool(self.linear_client),
            
            # Code analysis tools
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            RipGrepTool(codebase),
            SemanticSearchTool(codebase),
            RevealSymbolTool(codebase),
        ]
        
        return CodeAgent(codebase=codebase, tools=tools)
    
    async def analyze_pr(self, repo_str: str, pr_number: int) -> str:
        """
        Analyze a PR and provide feedback.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number to analyze
            
        Returns:
            Analysis result as a string
        """
        logger.info(f"Analyzing PR #{pr_number} in {repo_str}")
        
        # Create PR analysis agent
        agent = self.create_pr_analysis_agent(repo_str)
        
        # Create prompt for PR analysis
        prompt = f"""
        Analyze the following pull request:
        
        Repository: {repo_str}
        PR Number: {pr_number}
        
        Please provide a comprehensive analysis including:
        1. Summary of changes
        2. Code quality assessment
        3. Potential issues or bugs
        4. Suggestions for improvement
        5. Overall recommendation (approve, request changes, or comment)
        
        Use the available tools to view the PR, examine the code, and provide specific feedback.
        """
        
        # Run the agent
        result = agent.run(prompt)
        
        # Add to event history
        self.event_history.append({
            "type": "pr_analysis",
            "repo": repo_str,
            "pr_number": pr_number,
            "timestamp": datetime.now().isoformat(),
            "result": result[:500]  # Store a summary
        })
        
        return result
    
    async def reflect_on_plan(self, team_id: str = None) -> Dict[str, Any]:
        """
        Reflect on the overall plan goals and progress.
        
        Args:
            team_id: Linear team ID (optional)
            
        Returns:
            Dictionary with reflection results
        """
        logger.info("Reflecting on plan goals")
        
        # Use default team ID if not provided
        team_id = team_id or LINEAR_TEAM_ID
        
        # Create plan reflection agent
        agent = self.create_plan_reflection_agent()
        
        # Create prompt for plan reflection
        prompt = f"""
        Reflect on the current state of the project plan for team ID: {team_id}
        
        Please analyze:
        1. Overall project goals
        2. Current progress
        3. Blockers or issues
        4. Next priorities
        
        Use the Linear tools to gather information about issues, their states, and relationships.
        Provide a comprehensive reflection on the project status and recommendations for next steps.
        """
        
        # Run the agent
        result = agent.run(prompt)
        
        # Parse the result to extract structured information
        # This is a simplified parsing, in a real implementation you might want to use a more robust approach
        reflection = {
            "overall_status": "unknown",
            "progress_percentage": 0,
            "blockers": [],
            "next_priorities": [],
            "raw_reflection": result
        }
        
        # Extract overall status
        status_match = re.search(r'Overall Status:?\s*([A-Za-z]+)', result)
        if status_match:
            reflection["overall_status"] = status_match.group(1).lower()
        
        # Extract progress percentage
        progress_match = re.search(r'Progress:?\s*(\d+)%', result)
        if progress_match:
            reflection["progress_percentage"] = int(progress_match.group(1))
        
        # Extract blockers
        blockers_section = re.search(r'Blockers:?\s*(.*?)(?:Next Priorities:|$)', result, re.DOTALL)
        if blockers_section:
            blockers_text = blockers_section.group(1).strip()
            blockers = re.findall(r'- (.*?)(?:\n|$)', blockers_text)
            reflection["blockers"] = [b.strip() for b in blockers if b.strip()]
        
        # Extract next priorities
        priorities_section = re.search(r'Next Priorities:?\s*(.*?)(?:$)', result, re.DOTALL)
        if priorities_section:
            priorities_text = priorities_section.group(1).strip()
            priorities = re.findall(r'- (.*?)(?:\n|$)', priorities_text)
            reflection["next_priorities"] = [p.strip() for p in priorities if p.strip()]
        
        # Add to event history
        self.event_history.append({
            "type": "plan_reflection",
            "team_id": team_id,
            "timestamp": datetime.now().isoformat(),
            "result": reflection
        })
        
        # Update plan cache
        self.plan_cache[team_id] = reflection
        
        return reflection
    
    async def suggest_next_step(self, repo_str: str, team_id: str = None) -> str:
        """
        Suggest the next step in the development cycle.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            team_id: Linear team ID (optional)
            
        Returns:
            Next step suggestion as a string
        """
        logger.info(f"Suggesting next step for {repo_str}")
        
        # Use default team ID if not provided
        team_id = team_id or LINEAR_TEAM_ID
        
        # Reflect on plan first if not in cache
        if team_id not in self.plan_cache:
            await self.reflect_on_plan(team_id)
        
        # Create next step agent
        agent = self.create_next_step_agent(repo_str)
        
        # Create prompt for next step suggestion
        prompt = f"""
        Based on the current project status and recent events, suggest the next development step for:
        
        Repository: {repo_str}
        Team ID: {team_id}
        
        Recent events:
        {self._format_recent_events()}
        
        Current plan status:
        {self._format_plan_status(team_id)}
        
        Please suggest a specific, actionable next step that will move the project forward.
        Include:
        1. What should be done next
        2. Why this is the priority
        3. Who should be involved (if relevant)
        4. Any specific implementation details or requirements
        
        The suggestion should be concrete enough to be implemented immediately.
        """
        
        # Run the agent
        result = agent.run(prompt)
        
        # Add to event history
        self.event_history.append({
            "type": "next_step_suggestion",
            "repo": repo_str,
            "team_id": team_id,
            "timestamp": datetime.now().isoformat(),
            "result": result[:500]  # Store a summary
        })
        
        return result
    
    async def send_slack_message(self, channel: str, message: str, thread_ts: str = None) -> Dict[str, Any]:
        """
        Send a message to Slack.
        
        Args:
            channel: Slack channel ID
            message: Message to send
            thread_ts: Thread timestamp for replies
            
        Returns:
            Slack API response
        """
        if not self.slack_client:
            logger.warning("Slack client not initialized")
            return {"ok": False, "error": "Slack client not initialized"}
        
        try:
            response = self.slack_client.chat_postMessage(
                channel=channel,
                text=message,
                thread_ts=thread_ts
            )
            return response
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
            return {"ok": False, "error": str(e)}
    
    def _format_recent_events(self, limit: int = 5) -> str:
        """Format recent events for inclusion in prompts."""
        if not self.event_history:
            return "No recent events."
        
        recent_events = self.event_history[-limit:]
        formatted_events = []
        
        for event in recent_events:
            event_type = event["type"]
            timestamp = event["timestamp"]
            
            if event_type == "pr_analysis":
                formatted_events.append(
                    f"PR Analysis ({timestamp}): PR #{event['pr_number']} in {event['repo']}"
                )
            elif event_type == "plan_reflection":
                formatted_events.append(
                    f"Plan Reflection ({timestamp}): Team {event['team_id']}"
                )
            elif event_type == "next_step_suggestion":
                formatted_events.append(
                    f"Next Step Suggestion ({timestamp}): For {event['repo']}"
                )
        
        return "\n".join(formatted_events)
    
    def _format_plan_status(self, team_id: str) -> str:
        """Format plan status for inclusion in prompts."""
        if team_id not in self.plan_cache:
            return "Plan status not available."
        
        reflection = self.plan_cache[team_id]
        
        status_lines = [
            f"Overall Status: {reflection['overall_status']}",
            f"Progress: {reflection['progress_percentage']}%",
        ]
        
        if reflection["blockers"]:
            status_lines.append("Blockers:")
            for blocker in reflection["blockers"]:
                status_lines.append(f"- {blocker}")
        
        if reflection["next_priorities"]:
            status_lines.append("Next Priorities:")
            for priority in reflection["next_priorities"]:
                status_lines.append(f"- {priority}")
        
        return "\n".join(status_lines)

# Initialize the CICD Slackbot
cicd_bot = CICDSlackbot()

@app.github.event("pull_request:opened")
async def handle_pr_opened(event: PullRequestOpenedEvent, background_tasks: BackgroundTasks):
    """Handle pull request opened events."""
    logger.info(f"[PR:OPENED] Received PR opened event for #{event.number}")
    
    repo_str = f"{event.repository.owner.login}/{event.repository.name}"
    
    # Add task to analyze PR
    background_tasks.add_task(analyze_and_notify_pr, repo_str, event.number)

@app.github.event("pull_request:closed")
async def handle_pr_closed(event: PullRequestClosedEvent, background_tasks: BackgroundTasks):
    """Handle pull request closed events."""
    logger.info(f"[PR:CLOSED] Received PR closed event for #{event.number}")
    
    repo_str = f"{event.repository.owner.login}/{event.repository.name}"
    
    # If PR was merged, reflect on plan and suggest next steps
    if event.pull_request.merged:
        background_tasks.add_task(reflect_and_suggest_next_step, repo_str)

@app.linear.event("Issue:created")
async def handle_issue_created(event: LinearIssueCreatedEvent):
    """Handle Linear issue created events."""
    logger.info(f"[LINEAR:ISSUE:CREATED] Received issue created event for {event.data.id}")
    
    # Send notification to Slack
    if SLACK_DEFAULT_CHANNEL:
        await cicd_bot.send_slack_message(
            SLACK_DEFAULT_CHANNEL,
            f"📝 New issue created: *{event.data.title}*\n\n<{event.url}|View in Linear>"
        )

@app.linear.event("Issue:updated")
async def handle_issue_updated(event: LinearIssueUpdatedEvent, background_tasks: BackgroundTasks):
    """Handle Linear issue updated events."""
    logger.info(f"[LINEAR:ISSUE:UPDATED] Received issue updated event for {event.data.id}")
    
    # If issue was completed, reflect on plan and suggest next steps
    # Note: This is a simplified check, in a real implementation you would check the state change
    if "state" in event.changes and event.changes["state"]["to"] == "completed":
        # Use default repo if available
        if DEFAULT_REPO:
            background_tasks.add_task(reflect_and_suggest_next_step, DEFAULT_REPO)

@app.slack.event("app_mention")
async def handle_slack_mention(event: SlackEvent, background_tasks: BackgroundTasks):
    """Handle Slack app mention events."""
    logger.info(f"[SLACK:APP_MENTION] Received app mention in channel {event.channel}")
    
    # Extract the text without the mention
    text = re.sub(r'<@[A-Z0-9]+>', '', event.text).strip()
    
    # Process commands
    if text.lower().startswith("analyze pr"):
        # Extract repo and PR number
        match = re.search(r'analyze pr (?:in )?(?:repo )?([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+) #?(\d+)', text.lower())
        if match:
            repo_str = match.group(1)
            pr_number = int(match.group(2))
            
            # Send acknowledgement
            await cicd_bot.send_slack_message(
                event.channel,
                f"🔍 Analyzing PR #{pr_number} in {repo_str}...",
                event.ts
            )
            
            # Add task to analyze PR
            background_tasks.add_task(analyze_pr_from_slack, repo_str, pr_number, event.channel, event.ts)
        else:
            await cicd_bot.send_slack_message(
                event.channel,
                "❌ Invalid format. Please use: `analyze PR in repo/name #123`",
                event.ts
            )
    
    elif text.lower().startswith("reflect on plan"):
        # Extract team ID if provided
        match = re.search(r'reflect on plan (?:for team )?([a-zA-Z0-9-]+)', text.lower())
        team_id = match.group(1) if match else LINEAR_TEAM_ID
        
        # Send acknowledgement
        await cicd_bot.send_slack_message(
            event.channel,
            "🤔 Reflecting on plan goals...",
            event.ts
        )
        
        # Add task to reflect on plan
        background_tasks.add_task(reflect_on_plan_from_slack, team_id, event.channel, event.ts)
    
    elif text.lower().startswith("suggest next step"):
        # Extract repo if provided
        match = re.search(r'suggest next step (?:for )?([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)', text.lower())
        repo_str = match.group(1) if match else DEFAULT_REPO
        
        if repo_str:
            # Send acknowledgement
            await cicd_bot.send_slack_message(
                event.channel,
                f"🔮 Suggesting next step for {repo_str}...",
                event.ts
            )
            
            # Add task to suggest next step
            background_tasks.add_task(suggest_next_step_from_slack, repo_str, event.channel, event.ts)
        else:
            await cicd_bot.send_slack_message(
                event.channel,
                "❌ Please specify a repository or set DEFAULT_REPO environment variable.",
                event.ts
            )
    
    elif text.lower().startswith("help"):
        # Send help message
        help_message = """
        *CICD Slackbot Commands*
        
        `analyze PR in repo/name #123` - Analyze a specific PR
        `reflect on plan [for team ID]` - Reflect on plan goals and progress
        `suggest next step [for repo/name]` - Suggest the next development step
        `help` - Show this help message
        """
        
        await cicd_bot.send_slack_message(
            event.channel,
            help_message,
            event.ts
        )
    
    else:
        # Unknown command
        await cicd_bot.send_slack_message(
            event.channel,
            "❓ Unknown command. Type `help` to see available commands.",
            event.ts
        )

# Background task handlers
async def analyze_and_notify_pr(repo_str: str, pr_number: int):
    """Analyze a PR and notify via Slack."""
    try:
        # Analyze PR
        analysis = await cicd_bot.analyze_pr(repo_str, pr_number)
        
        # Send notification to Slack
        if SLACK_DEFAULT_CHANNEL:
            await cicd_bot.send_slack_message(
                SLACK_DEFAULT_CHANNEL,
                f"🔍 *PR Analysis for {repo_str} #{pr_number}*\n\n{analysis}"
            )
        
        # Add PR comment with analysis
        codebase = cicd_bot.get_codebase(repo_str)
        codebase._op.create_pr_comment(pr_number, f"## PR Analysis\n\n{analysis}")
        
    except Exception as e:
        logger.exception(f"Error analyzing PR: {e}")
        
        # Send error notification to Slack
        if SLACK_DEFAULT_CHANNEL:
            await cicd_bot.send_slack_message(
                SLACK_DEFAULT_CHANNEL,
                f"❌ Error analyzing PR {repo_str} #{pr_number}: {str(e)}"
            )

async def reflect_and_suggest_next_step(repo_str: str):
    """Reflect on plan and suggest next steps."""
    try:
        # Reflect on plan
        reflection = await cicd_bot.reflect_on_plan()
        
        # Suggest next step
        suggestion = await cicd_bot.suggest_next_step(repo_str)
        
        # Send notification to Slack
        if SLACK_DEFAULT_CHANNEL:
            message = f"""
            🔄 *CI/CD Cycle Update*
            
            *Plan Status:*
            Overall: {reflection['overall_status']}
            Progress: {reflection['progress_percentage']}%
            
            *Next Step Suggestion:*
            {suggestion}
            """
            
            await cicd_bot.send_slack_message(SLACK_DEFAULT_CHANNEL, message)
        
    except Exception as e:
        logger.exception(f"Error in reflect and suggest: {e}")
        
        # Send error notification to Slack
        if SLACK_DEFAULT_CHANNEL:
            await cicd_bot.send_slack_message(
                SLACK_DEFAULT_CHANNEL,
                f"❌ Error reflecting and suggesting next step: {str(e)}"
            )

async def analyze_pr_from_slack(repo_str: str, pr_number: int, channel: str, thread_ts: str):
    """Analyze a PR from a Slack command."""
    try:
        # Analyze PR
        analysis = await cicd_bot.analyze_pr(repo_str, pr_number)
        
        # Send response to Slack
        await cicd_bot.send_slack_message(
            channel,
            f"🔍 *PR Analysis for {repo_str} #{pr_number}*\n\n{analysis}",
            thread_ts
        )
        
    except Exception as e:
        logger.exception(f"Error analyzing PR from Slack: {e}")
        
        # Send error response to Slack
        await cicd_bot.send_slack_message(
            channel,
            f"❌ Error analyzing PR: {str(e)}",
            thread_ts
        )

async def reflect_on_plan_from_slack(team_id: str, channel: str, thread_ts: str):
    """Reflect on plan from a Slack command."""
    try:
        # Reflect on plan
        reflection = await cicd_bot.reflect_on_plan(team_id)
        
        # Format reflection for Slack
        message = f"""
        🤔 *Plan Reflection*
        
        *Overall Status:* {reflection['overall_status']}
        *Progress:* {reflection['progress_percentage']}%
        
        *Blockers:*
        {('- ' + '\\n- '.join(reflection['blockers'])) if reflection['blockers'] else 'None identified'}
        
        *Next Priorities:*
        {('- ' + '\\n- '.join(reflection['next_priorities'])) if reflection['next_priorities'] else 'None identified'}
        """
        
        # Send response to Slack
        await cicd_bot.send_slack_message(channel, message, thread_ts)
        
    except Exception as e:
        logger.exception(f"Error reflecting on plan from Slack: {e}")
        
        # Send error response to Slack
        await cicd_bot.send_slack_message(
            channel,
            f"❌ Error reflecting on plan: {str(e)}",
            thread_ts
        )

async def suggest_next_step_from_slack(repo_str: str, channel: str, thread_ts: str):
    """Suggest next step from a Slack command."""
    try:
        # Suggest next step
        suggestion = await cicd_bot.suggest_next_step(repo_str)
        
        # Send response to Slack
        await cicd_bot.send_slack_message(
            channel,
            f"🔮 *Next Step Suggestion for {repo_str}*\n\n{suggestion}",
            thread_ts
        )
        
    except Exception as e:
        logger.exception(f"Error suggesting next step from Slack: {e}")
        
        # Send error response to Slack
        await cicd_bot.send_slack_message(
            channel,
            f"❌ Error suggesting next step: {str(e)}",
            thread_ts
        )

# Modal deployment
@app.function(secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def fastapi_app():
    """Entry point for the FastAPI app."""
    logger.info("Starting CICD Slackbot FastAPI app")
    return app.app

@app.function(secrets=[modal.Secret.from_dotenv()])
@modal.web_endpoint(method="POST")
def entrypoint(event: dict, request: Request):
    """Entry point for webhook events."""
    logger.info("[OUTER] Received webhook event")
    return app.handle_event(event, request)