"""
Code Generation Agent - Receives requests via Slack and generates code/PRs.

This agent is responsible for:
1. Receiving implementation requests from Slack
2. Analyzing the codebase to understand the context
3. Generating code to implement the requested feature
4. Creating a PR with the implementation
"""

import logging
import os
import re
import uuid
import tempfile
from typing import Dict, Any, List, Optional, Tuple

import modal
from fastapi import Request, BackgroundTasks
from github import Github
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from codegen import Codebase
from codegen.configs.models.secrets import SecretsConfig
from codegen.git.repo_operator import RepoOperator
from agentgen import CodeAgent
from agentgen.extensions.slack.types import SlackEvent
from agentgen.extensions.langchain.tools import (
    ViewFileTool,
    ListDirectoryTool,
    RipGrepTool,
    CreateFileTool,
    DeleteFileTool,
    RenameFileTool,
    ReplacementEditTool,
    RelaceEditTool,
    SemanticSearchTool,
    RevealSymbolTool,
    GithubCreatePRTool,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_DEFAULT_CHANNEL = os.getenv("SLACK_DEFAULT_CHANNEL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "")
CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/three_platform_cache")

class RepoManager:
    """
    Repository manager that handles cloning, caching, and operations on repositories.
    """
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self.repo_cache = {}  # Maps repo_str to Codebase objects
        self.repo_operators = {}  # Maps repo_str to RepoOperator objects
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        logger.info(f"Initialized RepoManager with cache directory: {cache_dir}")
    
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
            logger.info(f"[REPO_MANAGER] Using cached codebase for {repo_str}")
            return self.repo_cache[repo_str]
        
        logger.info(f"[REPO_MANAGER] Initializing new codebase for {repo_str}")
        repo_dir = os.path.join(self.cache_dir, repo_str.replace('/', '_'))
        
        # Create Codebase object
        codebase = Codebase.from_repo(
            repo_str,
            secrets=SecretsConfig(github_token=GITHUB_TOKEN),
            clone_dir=repo_dir
        )
        
        # Cache the codebase
        self.repo_cache[repo_str] = codebase
        return codebase
    
    def get_repo_operator(self, repo_str: str) -> RepoOperator:
        """
        Get a RepoOperator object for the specified repository.
        Will use cached version if available, otherwise creates a new one.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            
        Returns:
            RepoOperator object for the repository
        """
        if repo_str in self.repo_operators:
            logger.info(f"[REPO_MANAGER] Using cached repo operator for {repo_str}")
            return self.repo_operators[repo_str]
        
        logger.info(f"[REPO_MANAGER] Initializing new repo operator for {repo_str}")
        
        # Get the codebase first to ensure the repo is cloned
        codebase = self.get_codebase(repo_str)
        
        # Create RepoOperator object
        repo_operator = RepoOperator(
            repo_url=f"https://github.com/{repo_str}.git",
            github_token=GITHUB_TOKEN,
            clone_dir=os.path.join(self.cache_dir, repo_str.replace('/', '_')),
            use_cache=True
        )
        
        # Cache the repo operator
        self.repo_operators[repo_str] = repo_operator
        return repo_operator
    
    def create_branch(self, repo_str: str, branch_name: str) -> bool:
        """
        Create a new branch in the repository.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            branch_name: Name of the branch to create
            
        Returns:
            True if branch was created successfully, False otherwise
        """
        repo_operator = self.get_repo_operator(repo_str)
        try:
            repo_operator.checkout_branch(branch_name, create=True)
            return True
        except Exception as e:
            logger.exception(f"Error creating branch {branch_name} in {repo_str}: {e}")
            return False
    
    def commit_changes(self, repo_str: str, commit_message: str) -> bool:
        """
        Commit changes to the repository.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            commit_message: Commit message
            
        Returns:
            True if commit was successful, False otherwise
        """
        repo_operator = self.get_repo_operator(repo_str)
        try:
            repo_operator.commit(commit_message)
            return True
        except Exception as e:
            logger.exception(f"Error committing changes to {repo_str}: {e}")
            return False
    
    def push_branch(self, repo_str: str, branch_name: str) -> bool:
        """
        Push a branch to the remote repository.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            branch_name: Name of the branch to push
            
        Returns:
            True if push was successful, False otherwise
        """
        repo_operator = self.get_repo_operator(repo_str)
        try:
            repo_operator.push(branch_name)
            return True
        except Exception as e:
            logger.exception(f"Error pushing branch {branch_name} to {repo_str}: {e}")
            return False
    
    def create_pr(self, repo_str: str, title: str, body: str, head_branch: str, base_branch: str = "main") -> Optional[int]:
        """
        Create a pull request in the repository.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (default: main)
            
        Returns:
            PR number if created successfully, None otherwise
        """
        repo_operator = self.get_repo_operator(repo_str)
        try:
            pr = repo_operator.create_pr(title, body, head_branch, base_branch)
            return pr.number
        except Exception as e:
            logger.exception(f"Error creating PR in {repo_str}: {e}")
            return None

class CodeGenerationAgent:
    """
    Code Generation Agent that receives requests via Slack and generates code/PRs.
    """
    def __init__(self):
        """Initialize the Code Generation Agent."""
        self.repo_manager = RepoManager()
        self.slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
        
        logger.info("Code Generation Agent initialized")
    
    def create_code_agent(self, repo_str: str) -> CodeAgent:
        """
        Create a code agent with tools for code generation and PR creation.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            
        Returns:
            CodeAgent with appropriate tools
        """
        codebase = self.repo_manager.get_codebase(repo_str)
        
        tools = [
            # Code analysis tools
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            RipGrepTool(codebase),
            SemanticSearchTool(codebase),
            RevealSymbolTool(codebase),
            
            # Code editing tools
            CreateFileTool(codebase),
            DeleteFileTool(codebase),
            RenameFileTool(codebase),
            ReplacementEditTool(codebase),
            RelaceEditTool(codebase),
            
            # GitHub tools
            GithubCreatePRTool(codebase),
        ]
        
        return CodeAgent(codebase=codebase, tools=tools)
    
    async def extract_issue_id(self, text: str) -> Optional[str]:
        """
        Extract a Linear issue ID from text.
        
        Args:
            text: Text to extract issue ID from
            
        Returns:
            Issue ID if found, None otherwise
        """
        # Look for patterns like "ID: ABC-123" or "Issue ID: ABC-123"
        issue_id_match = re.search(r'(?:Issue\s+)?ID:?\s*([A-Za-z]+-[0-9]+)', text)
        if issue_id_match:
            return issue_id_match.group(1)
        
        return None
    
    async def handle_implementation_request(self, event: SlackEvent, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        """
        Handle an implementation request from Slack.
        
        Args:
            event: Slack event
            background_tasks: FastAPI background tasks
            
        Returns:
            Response data
        """
        logger.info(f"Handling implementation request from Slack: {event.text}")
        
        # Extract issue ID from the message
        issue_id = await self.extract_issue_id(event.text)
        if not issue_id:
            logger.warning("No issue ID found in message")
            await self.send_slack_message(
                event.channel,
                "❌ Could not find an issue ID in the message. Please include the issue ID in the format 'ID: ABC-123'.",
                event.ts
            )
            return {"status": "error", "message": "No issue ID found"}
        
        # Extract repository from the message or use default
        repo_str = self.extract_repo_from_text(event.text) or DEFAULT_REPO
        if not repo_str:
            logger.warning("No repository specified and no default repository configured")
            await self.send_slack_message(
                event.channel,
                "❌ No repository specified and no default repository configured. Please specify a repository in the format 'repo: owner/repo'.",
                event.ts
            )
            return {"status": "error", "message": "No repository specified"}
        
        # Send acknowledgement
        status_msg = await self.send_slack_message(
            event.channel,
            f"🔍 Processing implementation request for issue {issue_id} in repository {repo_str}...",
            event.ts
        )
        
        # Add task to generate code and create PR
        background_tasks.add_task(
            self.generate_code_and_create_pr,
            repo_str,
            issue_id,
            event.text,
            event.channel,
            status_msg["ts"],
            event.ts
        )
        
        return {"status": "processing", "issue_id": issue_id, "repo": repo_str}
    
    async def generate_code_and_create_pr(
        self,
        repo_str: str,
        issue_id: str,
        request_text: str,
        channel: str,
        status_msg_ts: str,
        thread_ts: str
    ) -> Dict[str, Any]:
        """
        Generate code and create a PR for an implementation request.
        
        Args:
            repo_str: Repository string in format "owner/repo"
            issue_id: Linear issue ID
            request_text: Original request text
            channel: Slack channel ID
            status_msg_ts: Timestamp of the status message to update
            thread_ts: Timestamp of the thread to reply to
            
        Returns:
            Result of the operation
        """
        try:
            # Update status message
            await self.update_slack_message(
                channel,
                status_msg_ts,
                f"🔍 Analyzing repository {repo_str} for issue {issue_id}...",
                thread_ts
            )
            
            # Create a unique branch name
            branch_name = f"codegen-{issue_id.lower()}-{uuid.uuid4().hex[:8]}"
            
            # Create branch
            if not self.repo_manager.create_branch(repo_str, branch_name):
                raise Exception(f"Failed to create branch {branch_name}")
            
            # Update status message
            await self.update_slack_message(
                channel,
                status_msg_ts,
                f"🌿 Created branch `{branch_name}`. Generating implementation...",
                thread_ts
            )
            
            # Create code agent
            agent = self.create_code_agent(repo_str)
            
            # Create prompt for code generation
            prompt = f"""
            Generate code to implement the following feature:
            
            Issue ID: {issue_id}
            Repository: {repo_str}
            Branch: {branch_name}
            
            Request details:
            {request_text}
            
            Follow these steps:
            1. Analyze the codebase to understand the context
            2. Identify the files that need to be modified or created
            3. Make the necessary changes to implement the feature
            4. Create a PR with a clear title and description
            
            The PR title should include the issue ID and a brief description of the changes.
            The PR description should explain the implementation details and any design decisions.
            
            Make sure to follow the coding style and patterns used in the existing codebase.
            """
            
            # Run the agent
            response = agent.run(prompt)
            
            # Extract PR URL if created
            url_match = re.search(r'https://github.com/[^/]+/[^/]+/pull/[0-9]+', response)
            pr_url = url_match.group(0) if url_match else None
            
            # If PR URL not found in response, try to create PR manually
            if not pr_url:
                # Update status message
                await self.update_slack_message(
                    channel,
                    status_msg_ts,
                    f"💾 Implementation generated. Creating PR...",
                    thread_ts
                )
                
                # Commit changes
                if not self.repo_manager.commit_changes(repo_str, f"Implement {issue_id}: {self.extract_title(request_text)}"):
                    raise Exception("Failed to commit changes")
                
                # Push branch
                if not self.repo_manager.push_branch(repo_str, branch_name):
                    raise Exception(f"Failed to push branch {branch_name}")
                
                # Create PR
                pr_title = f"Implement {issue_id}: {self.extract_title(request_text)}"
                pr_body = f"""
                Implementation for issue {issue_id}
                
                ## Description
                {self.extract_description(request_text)}
                
                ## Changes
                {self.extract_changes_from_response(response)}
                """
                
                pr_number = self.repo_manager.create_pr(
                    repo_str,
                    pr_title,
                    pr_body,
                    branch_name
                )
                
                if pr_number:
                    pr_url = f"https://github.com/{repo_str}/pull/{pr_number}"
            
            # Format the final response
            if pr_url:
                formatted_response = f"""
                🎉 *PR Created Successfully!*
                
                <{pr_url}|View PR on GitHub>
                
                *Implementation for issue {issue_id}*
                
                {self.extract_changes_from_response(response)}
                """
                
                # Update the status message with the result
                await self.update_slack_message(
                    channel,
                    status_msg_ts,
                    formatted_response,
                    thread_ts
                )
                
                return {"status": "success", "pr_url": pr_url, "issue_id": issue_id}
            else:
                error_message = f"""
                ⚠️ *PR Creation Failed*
                
                The implementation was generated, but creating a PR failed.
                
                *Response from agent:*
                {response[:1000]}...
                """
                
                # Update the status message with the error
                await self.update_slack_message(
                    channel,
                    status_msg_ts,
                    error_message,
                    thread_ts
                )
                
                return {"status": "error", "message": "Failed to create PR", "issue_id": issue_id}
        
        except Exception as e:
            # Handle errors
            logger.exception(f"Error in code generation: {e}")
            error_message = f"❌ *Error generating code*\n\n```\n{str(e)}\n```\n\nPlease try again or contact support."
            
            # Update the status message with the error
            await self.update_slack_message(
                channel,
                status_msg_ts,
                error_message,
                thread_ts
            )
            
            return {"status": "error", "message": str(e), "issue_id": issue_id}
    
    def extract_repo_from_text(self, text: str) -> Optional[str]:
        """Extract repository name from text using regex patterns."""
        # Match GitHub URL patterns
        github_url_pattern = r'https?://(?:www\.)?github\.com/([^/\s]+/[^/\s]+)'
        url_match = re.search(github_url_pattern, text)
        if url_match:
            return url_match.group(1)
        
        # Match "repo: org/name" patterns
        repo_pattern = r'repo:?\s+([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)'
        repo_match = re.search(repo_pattern, text, re.IGNORECASE)
        if repo_match:
            return repo_match.group(1)
        
        # Match org/repo patterns
        simple_repo_pattern = r'([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)'
        simple_match = re.search(simple_repo_pattern, text)
        if simple_match:
            return simple_match.group(1)
        
        return None
    
    def extract_title(self, text: str) -> str:
        """Extract a title from the request text."""
        # Look for patterns like "Title: Some Title" or the first line after "Description:"
        title_match = re.search(r'Title:?\s+([^\n]+)', text, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # If no explicit title, use the first line of the description
        desc_match = re.search(r'Description:?\s+([^\n]+)', text, re.IGNORECASE)
        if desc_match:
            return desc_match.group(1).strip()
        
        # If all else fails, use the first line of the text
        first_line = text.strip().split('\n')[0]
        return first_line[:50] + ('...' if len(first_line) > 50 else '')
    
    def extract_description(self, text: str) -> str:
        """Extract a description from the request text."""
        # Look for patterns like "Description: Some description"
        desc_match = re.search(r'Description:?\s+(.*?)(?:Priority:|$)', text, re.IGNORECASE | re.DOTALL)
        if desc_match:
            return desc_match.group(1).strip()
        
        # If no explicit description, use the text after the first line
        lines = text.strip().split('\n')
        if len(lines) > 1:
            return '\n'.join(lines[1:]).strip()
        
        return "No description provided"
    
    def extract_changes_from_response(self, response: str) -> str:
        """Extract a summary of changes from the agent response."""
        # Look for patterns like "Changes:" or "Files changed:"
        changes_match = re.search(r'(?:Changes|Files changed|Modified files):?\s+(.*?)(?:## |$)', response, re.IGNORECASE | re.DOTALL)
        if changes_match:
            return changes_match.group(1).strip()
        
        # If no explicit changes section, look for bullet points
        bullet_points = re.findall(r'[-*]\s+([^\n]+)', response)
        if bullet_points:
            return '\n'.join([f"- {point}" for point in bullet_points])
        
        # If all else fails, return a generic message
        return "Implementation completed. See PR for details."
    
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
    
    async def update_slack_message(self, channel: str, ts: str, message: str, thread_ts: str = None) -> Dict[str, Any]:
        """
        Update a Slack message.
        
        Args:
            channel: Slack channel ID
            ts: Timestamp of the message to update
            message: New message text
            thread_ts: Thread timestamp for context
            
        Returns:
            Slack API response
        """
        if not self.slack_client:
            logger.warning("Slack client not initialized")
            return {"ok": False, "error": "Slack client not initialized"}
        
        try:
            response = self.slack_client.chat_update(
                channel=channel,
                ts=ts,
                text=message,
                thread_ts=thread_ts
            )
            return response
        except SlackApiError as e:
            logger.error(f"Error updating Slack message: {e}")
            return {"ok": False, "error": str(e)}

# Initialize the Code Generation Agent
code_generation_agent = CodeGenerationAgent()

# Modal app setup
app = modal.App("code-generation-agent")

@app.function(secrets=[modal.Secret.from_dotenv()])
async def handle_slack_message(event: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Handle a Slack message."""
    slack_event = SlackEvent(**event)
    return await code_generation_agent.handle_implementation_request(slack_event, background_tasks)

if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        # Simulate a Slack event
        event = SlackEvent(
            type="app_mention",
            user="U12345678",
            text="@bot Implement feature X for issue ID: ABC-123 in repo: owner/repo",
            channel="C12345678",
            ts="1234567890.123456"
        )
        
        # Create a mock background tasks object
        class MockBackgroundTasks:
            def add_task(self, func, *args, **kwargs):
                asyncio.create_task(func(*args, **kwargs))
        
        background_tasks = MockBackgroundTasks()
        
        # Handle the event
        result = await code_generation_agent.handle_implementation_request(event, background_tasks)
        print(f"Result: {result}")
    
    asyncio.run(main())