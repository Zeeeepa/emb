"""
Code Analysis Agent - Analyzes PRs, provides feedback, and handles merging.

This agent is responsible for:
1. Analyzing PRs when they are opened or updated
2. Providing feedback on code quality, potential issues, and improvements
3. Approving or requesting changes based on analysis
4. Automatically merging approved PRs
5. Notifying the Planning Agent when a PR is merged
"""

import logging
import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Union

import modal
from fastapi import Request, BackgroundTasks
from github import Github, GithubException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from codegen import Codebase
from codegen.configs.models.secrets import SecretsConfig
from agentgen import CodeAgent
from agentgen.extensions.github.types.events.pull_request import (
    PullRequestOpenedEvent,
    PullRequestClosedEvent,
    PullRequestMergedEvent,
    PullRequestReviewSubmittedEvent
)
from agentgen.extensions.langchain.tools import (
    ViewFileTool,
    ListDirectoryTool,
    RipGrepTool,
    SemanticSearchTool,
    RevealSymbolTool,
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_DEFAULT_CHANNEL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "")
AUTO_MERGE_APPROVED_PRS = os.getenv("AUTO_MERGE_APPROVED_PRS", "true").lower() == "true"
CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/three_platform_cache")

class CodeAnalysisAgent:
    """
    Code Analysis Agent that analyzes PRs, provides feedback, and handles merging.
    """
    def __init__(self):
        """Initialize the Code Analysis Agent."""
        self.github_client = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
        self.slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
        
        # Cache for repository codebases
        self.repo_cache = {}
        
        # Cache for PR analysis results
        self.analysis_cache = {}
        
        logger.info("Code Analysis Agent initialized")
    
    def get_codebase(self, repo_str: str) -> Codebase:
        """
        Get a Codebase object for the specified repository.
        Will use cached version if available, otherwise clones the repository.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            
        Returns:
            Codebase object for the repository
        """
        if repo_str in self.repo_cache:
            logger.info(f"Using cached codebase for {repo_str}")
            return self.repo_cache[repo_str]
        
        logger.info(f"Initializing new codebase for {repo_str}")
        repo_dir = os.path.join(CACHE_DIR, repo_str.replace('/', '_'))
        os.makedirs(repo_dir, exist_ok=True)
        
        codebase = Codebase.from_repo(
            repo_str,
            secrets=SecretsConfig(github_token=GITHUB_TOKEN),
            clone_dir=repo_dir
        )
        self.repo_cache[repo_str] = codebase
        return codebase
    
    def create_pr_analysis_agent(self, repo_str: str) -> CodeAgent:
        """
        Create a code agent with PR analysis tools.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            
        Returns:
            CodeAgent with PR analysis tools
        """
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
    
    async def analyze_pr(self, repo_str: str, pr_number: int) -> Dict[str, Any]:
        """
        Analyze a PR and provide feedback.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number to analyze
            
        Returns:
            Analysis result as a dictionary
        """
        logger.info(f"Analyzing PR #{pr_number} in {repo_str}")
        
        # Check if we have a cached analysis
        cache_key = f"{repo_str}:{pr_number}"
        if cache_key in self.analysis_cache:
            logger.info(f"Using cached analysis for PR #{pr_number} in {repo_str}")
            return self.analysis_cache[cache_key]
        
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
        Be thorough but constructive in your feedback.
        
        Format your response with clear sections and use markdown formatting.
        Include specific code examples when suggesting improvements.
        
        At the end, include a machine-readable section in the following format:
        
        ```json
        {{
            "recommendation": "approve|request_changes|comment",
            "issues_count": 0,
            "has_critical_issues": false,
            "issue_ids": []
        }}
        ```
        """
        
        # Run the agent
        result = agent.run(prompt)
        
        # Extract the machine-readable section
        json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
        recommendation_data = {}
        
        if json_match:
            try:
                recommendation_data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse recommendation JSON")
        
        # Create the analysis result
        analysis_result = {
            "repo": repo_str,
            "pr_number": pr_number,
            "analysis": result,
            "recommendation": recommendation_data.get("recommendation", "comment"),
            "issues_count": recommendation_data.get("issues_count", 0),
            "has_critical_issues": recommendation_data.get("has_critical_issues", False),
            "issue_ids": recommendation_data.get("issue_ids", []),
        }
        
        # Cache the analysis
        self.analysis_cache[cache_key] = analysis_result
        
        return analysis_result
    
    async def post_pr_comment(self, repo_str: str, pr_number: int, comment: str) -> bool:
        """
        Post a comment on a PR.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number to comment on
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        if not self.github_client:
            logger.warning("GitHub client not initialized")
            return False
        
        try:
            repo = self.github_client.get_repo(repo_str)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            return True
        except GithubException as e:
            logger.error(f"Error posting PR comment: {e}")
            return False
    
    async def submit_pr_review(self, repo_str: str, pr_number: int, analysis_result: Dict[str, Any]) -> bool:
        """
        Submit a review on a PR based on analysis result.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number to review
            analysis_result: Analysis result from analyze_pr
            
        Returns:
            True if successful, False otherwise
        """
        if not self.github_client:
            logger.warning("GitHub client not initialized")
            return False
        
        try:
            repo = self.github_client.get_repo(repo_str)
            pr = repo.get_pull(pr_number)
            
            # Determine review state based on recommendation
            recommendation = analysis_result["recommendation"]
            if recommendation == "approve":
                review_state = "APPROVE"
            elif recommendation == "request_changes":
                review_state = "REQUEST_CHANGES"
            else:
                review_state = "COMMENT"
            
            # Submit the review
            pr.create_review(
                body=analysis_result["analysis"],
                event=review_state
            )
            
            return True
        except GithubException as e:
            logger.error(f"Error submitting PR review: {e}")
            return False
    
    async def merge_pr(self, repo_str: str, pr_number: int) -> Dict[str, Any]:
        """
        Merge a PR if it's approved and all checks pass.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number to merge
            
        Returns:
            Result of the merge operation
        """
        if not self.github_client:
            logger.warning("GitHub client not initialized")
            return {"success": False, "message": "GitHub client not initialized"}
        
        try:
            repo = self.github_client.get_repo(repo_str)
            pr = repo.get_pull(pr_number)
            
            # Check if PR is mergeable
            if not pr.mergeable:
                return {"success": False, "message": "PR is not mergeable (conflicts or failing checks)"}
            
            # Check if PR is approved
            reviews = pr.get_reviews()
            approved = False
            for review in reviews:
                if review.state == "APPROVED":
                    approved = True
                    break
            
            if not approved:
                return {"success": False, "message": "PR is not approved"}
            
            # Merge the PR
            merge_result = pr.merge(
                commit_title=f"Merge PR #{pr_number}: {pr.title}",
                commit_message=f"Merged PR #{pr_number}: {pr.title}\n\n{pr.body}",
                merge_method="squash"
            )
            
            if merge_result.merged:
                # Extract issue ID from PR title or body
                issue_id = self.extract_issue_id(pr.title) or self.extract_issue_id(pr.body)
                
                return {
                    "success": True,
                    "message": "PR merged successfully",
                    "issue_id": issue_id
                }
            else:
                return {"success": False, "message": "Failed to merge PR"}
        
        except GithubException as e:
            logger.error(f"Error merging PR: {e}")
            return {"success": False, "message": f"GitHub error: {str(e)}"}
    
    def extract_issue_id(self, text: str) -> Optional[str]:
        """
        Extract a Linear issue ID from text.
        
        Args:
            text: Text to extract issue ID from
            
        Returns:
            Issue ID if found, None otherwise
        """
        if not text:
            return None
        
        # Look for patterns like "ABC-123" or "Implement ABC-123"
        issue_id_match = re.search(r'([A-Za-z]+-[0-9]+)', text)
        if issue_id_match:
            return issue_id_match.group(1)
        
        return None
    
    async def notify_planning_agent(self, repo_str: str, pr_number: int, issue_id: str = None) -> Dict[str, Any]:
        """
        Notify the Planning Agent that a PR has been merged.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number that was merged
            issue_id: Linear issue ID (optional)
            
        Returns:
            Result of the notification
        """
        logger.info(f"Notifying Planning Agent about merged PR #{pr_number} in {repo_str}")
        
        try:
            # Call the Planning Agent's handle_pr_merged endpoint
            import httpx
            
            url = "http://planning-agent:8000/handle_pr_merged"
            data = {
                "repo": repo_str,
                "pr_number": pr_number,
                "issue_id": issue_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Error notifying Planning Agent: {response.text}")
                    return {"success": False, "message": f"Error: {response.text}"}
        
        except Exception as e:
            logger.exception(f"Error notifying Planning Agent: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def send_slack_notification(self, message: str, channel: str = None) -> bool:
        """
        Send a notification to Slack.
        
        Args:
            message: Message to send
            channel: Slack channel ID (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.slack_client:
            logger.warning("Slack client not initialized")
            return False
        
        channel = channel or SLACK_DEFAULT_CHANNEL
        if not channel:
            logger.warning("No Slack channel specified")
            return False
        
        try:
            response = self.slack_client.chat_postMessage(
                channel=channel,
                text=message
            )
            return response["ok"]
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    async def handle_pr_opened(self, event: PullRequestOpenedEvent, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Handle a PR being opened.
        
        Args:
            event: PR opened event
            background_tasks: FastAPI background tasks
            
        Returns:
            Result of the operation
        """
        repo_str = f"{event.repository.owner.login}/{event.repository.name}"
        pr_number = event.number
        
        logger.info(f"Handling opened PR #{pr_number} in {repo_str}")
        
        # Add task to analyze PR
        background_tasks.add_task(self.analyze_and_review_pr, repo_str, pr_number)
        
        return {"status": "processing", "repo": repo_str, "pr_number": pr_number}
    
    async def handle_pr_closed(self, event: PullRequestClosedEvent, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Handle a PR being closed.
        
        Args:
            event: PR closed event
            background_tasks: FastAPI background tasks
            
        Returns:
            Result of the operation
        """
        repo_str = f"{event.repository.owner.login}/{event.repository.name}"
        pr_number = event.number
        
        logger.info(f"Handling closed PR #{pr_number} in {repo_str}")
        
        # If PR was merged, notify the Planning Agent
        if event.pull_request.merged:
            # Extract issue ID from PR title or body
            issue_id = self.extract_issue_id(event.pull_request.title) or self.extract_issue_id(event.pull_request.body)
            
            # Add task to notify Planning Agent
            background_tasks.add_task(self.notify_planning_agent, repo_str, pr_number, issue_id)
            
            # Send Slack notification
            await self.send_slack_notification(
                f"🎉 PR #{pr_number} in {repo_str} was merged! Issue: {issue_id or 'Unknown'}"
            )
            
            return {"status": "merged", "repo": repo_str, "pr_number": pr_number, "issue_id": issue_id}
        
        return {"status": "closed", "repo": repo_str, "pr_number": pr_number}
    
    async def analyze_and_review_pr(self, repo_str: str, pr_number: int) -> Dict[str, Any]:
        """
        Analyze a PR and submit a review.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            pr_number: PR number to analyze
            
        Returns:
            Result of the operation
        """
        try:
            # Analyze PR
            analysis_result = await self.analyze_pr(repo_str, pr_number)
            
            # Post a comment with the analysis
            await self.post_pr_comment(repo_str, pr_number, analysis_result["analysis"])
            
            # Submit a review
            await self.submit_pr_review(repo_str, pr_number, analysis_result)
            
            # Send Slack notification
            recommendation = analysis_result["recommendation"]
            emoji = "✅" if recommendation == "approve" else "❌" if recommendation == "request_changes" else "💬"
            
            await self.send_slack_notification(
                f"{emoji} Analyzed PR #{pr_number} in {repo_str} - Recommendation: {recommendation.upper()}"
            )
            
            # If PR is approved and auto-merge is enabled, merge it
            if recommendation == "approve" and AUTO_MERGE_APPROVED_PRS:
                merge_result = await self.merge_pr(repo_str, pr_number)
                
                if merge_result["success"]:
                    await self.send_slack_notification(
                        f"🎉 Automatically merged PR #{pr_number} in {repo_str}"
                    )
                    
                    # Notify Planning Agent
                    await self.notify_planning_agent(repo_str, pr_number, merge_result.get("issue_id"))
                    
                    return {"status": "merged", "repo": repo_str, "pr_number": pr_number}
            
            return {"status": "analyzed", "repo": repo_str, "pr_number": pr_number, "recommendation": recommendation}
        
        except Exception as e:
            logger.exception(f"Error analyzing PR: {e}")
            
            # Send error notification to Slack
            await self.send_slack_notification(
                f"❌ Error analyzing PR #{pr_number} in {repo_str}: {str(e)}"
            )
            
            return {"status": "error", "repo": repo_str, "pr_number": pr_number, "error": str(e)}

# Initialize the Code Analysis Agent
code_analysis_agent = CodeAnalysisAgent()

# Modal app setup
app = modal.App("code-analysis-agent")

@app.function(secrets=[modal.Secret.from_dotenv()])
async def handle_pr_opened_endpoint(event: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Handle a PR being opened."""
    pr_event = PullRequestOpenedEvent(**event)
    return await code_analysis_agent.handle_pr_opened(pr_event, background_tasks)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def handle_pr_closed_endpoint(event: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Handle a PR being closed."""
    pr_event = PullRequestClosedEvent(**event)
    return await code_analysis_agent.handle_pr_closed(pr_event, background_tasks)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def analyze_pr_endpoint(repo_str: str, pr_number: int) -> Dict[str, Any]:
    """Analyze a PR."""
    return await code_analysis_agent.analyze_pr(repo_str, pr_number)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def merge_pr_endpoint(repo_str: str, pr_number: int) -> Dict[str, Any]:
    """Merge a PR."""
    return await code_analysis_agent.merge_pr(repo_str, pr_number)

if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        # Simulate analyzing a PR
        result = await code_analysis_agent.analyze_pr("owner/repo", 123)
        print(f"Analysis result: {result}")
    
    asyncio.run(main())