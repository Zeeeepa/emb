import logging
import os
import re
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

import modal
from codegen import CodegenApp, Codebase
from codegen.configs.models.secrets import SecretsConfig
from agentgen import CodeAgent
from agentgen.extensions.github.types.events.pull_request import (
    PullRequestLabeledEvent,
    PullRequestOpenedEvent,
    PullRequestReviewRequestedEvent,
    PullRequestUnlabeledEvent
)
from agentgen.extensions.linear.types import LinearEvent, LinearIssueCreatedEvent, LinearIssueUpdatedEvent
from agentgen.extensions.slack.types import SlackEvent
from agentgen.extensions.tools.github.create_pr_comment import create_pr_comment
from agentgen.extensions.langchain.tools import (
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
    GithubCreatePRTool,
    LinearCreateIssueTool,
    LinearUpdateIssueTool,
    LinearCommentOnIssueTool,
    LinearGetIssueTool,
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
)
from fastapi import Request, BackgroundTasks
from github import Github

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MODAL_API_KEY = os.getenv("MODAL_API_KEY", "")
TRIGGER_LABEL = os.getenv("TRIGGER_LABEL", "analyzer")
SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "codegen-sh/Kevin-s-Adventure-Game")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REPO_CACHE_DIR = os.getenv("REPO_CACHE_DIR", "/tmp/codegen_repos")

########################################################################################################################
# INTENT RECOGNITION
########################################################################################################################

class UserIntent(Enum):
    """Enum representing different user intents for the bot."""
    ANALYZE_REPO = "analyze_repo"
    CREATE_PR = "create_pr"
    SUGGEST_PR = "suggest_pr"
    CREATE_ISSUE = "create_issue"
    REVIEW_PR = "review_pr"
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"

def detect_intent(text: str) -> Tuple[UserIntent, Dict[str, Any]]:
    """
    Detect the user's intent from their message text.
    
    Args:
        text: The user's message text
        
    Returns:
        A tuple of (intent, extracted_params)
    """
    text_lower = text.lower()
    params = {}
    
    # Extract repository information first as it's used in multiple intents
    repo = extract_repo_from_text(text)
    if repo:
        params["repo"] = repo
    
    # Analyze repository intent
    if any(phrase in text_lower for phrase in ["analyze repo", "analyze repository", "analyze codebase", "code analysis"]):
        return UserIntent.ANALYZE_REPO, params
    
    # PR creation intent
    if any(phrase in text_lower for phrase in ["create pr", "make pr", "submit pr", "open pr"]):
        pr_params = parse_pr_suggestion_request(text)
        params.update(pr_params)
        return UserIntent.CREATE_PR, params
    
    # PR suggestion intent
    if any(phrase in text_lower for phrase in ["suggest pr", "pr suggestion", "recommend changes", "propose pr"]):
        pr_params = parse_pr_suggestion_request(text)
        params.update(pr_params)
        return UserIntent.SUGGEST_PR, params
    
    # Issue creation intent
    if any(phrase in text_lower for phrase in ["create issue", "create ticket", "new issue", "open issue"]):
        issue_params = parse_issue_request(text)
        params.update(issue_params)
        return UserIntent.CREATE_ISSUE, params
    
    # PR review intent
    if any(phrase in text_lower for phrase in ["review pr", "review pull request", "check pr"]):
        pr_number_match = re.search(r'pr\s*#?(\d+)', text_lower)
        if pr_number_match:
            params["pr_number"] = int(pr_number_match.group(1))
        return UserIntent.REVIEW_PR, params
    
    # Default to general question if no specific intent is detected
    return UserIntent.GENERAL_QUESTION, params

def parse_issue_request(text: str) -> Dict[str, Any]:
    """Parse an issue creation request from Slack message text."""
    result = {
        "title": None,
        "description": None,
        "priority": None,
    }
    
    # Extract issue title
    title_match = re.search(r'title[:\s]+([^\n]+)', text, re.IGNORECASE)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    # Extract issue description
    desc_match = re.search(r'description[:\s]+(.*?)(?:priority|$)', text, re.IGNORECASE | re.DOTALL)
    if desc_match:
        result["description"] = desc_match.group(1).strip()
    
    # Extract priority
    priority_match = re.search(r'priority[:\s]+(high|medium|low)', text, re.IGNORECASE)
    if priority_match:
        result["priority"] = priority_match.group(1).lower()
    
    return result

########################################################################################################################
# REPOSITORY MANAGEMENT
########################################################################################################################

class RepoManager:
    """
    Manages repository cloning, caching, and access.
    Ensures repositories are only cloned once and reused for efficiency.
    """
    def __init__(self, cache_dir: str = REPO_CACHE_DIR):
        self.cache_dir = cache_dir
        self.repo_cache = {}  # Maps repo_str to Codebase objects
        
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
    
    def clear_cache(self, repo_str: Optional[str] = None):
        """
        Clear the cache for a specific repository or all repositories.
        
        Args:
            repo_str: Repository to clear, or None to clear all
        """
        if repo_str:
            if repo_str in self.repo_cache:
                logger.info(f"[REPO_MANAGER] Clearing cache for {repo_str}")
                del self.repo_cache[repo_str]
        else:
            logger.info("[REPO_MANAGER] Clearing entire cache")
            self.repo_cache.clear()

# Initialize the repository manager
repo_manager = RepoManager()

def get_codebase_for_repo(repo_str: str) -> Codebase:
    """Initialize a codebase for a specific repository using the repo manager."""
    return repo_manager.get_codebase(repo_str)

# HELPER FUNCTIONS
########################################################################################################################

def get_codebase_for_repo(repo_str: str) -> Codebase:
    """Initialize a codebase for a specific repository."""
    logger.info(f"[CODEBASE] Initializing codebase for {repo_str}")
    return Codebase.from_repo(
        repo_str,
        secrets=SecretsConfig(github_token=GITHUB_TOKEN)
    )

def get_pr_review_agent(codebase: Codebase) -> CodeAgent:
    """Create a code agent with PR review tools."""
    pr_tools = [
        GithubViewPRTool(codebase),
        GithubCreatePRCommentTool(codebase),
        GithubCreatePRReviewCommentTool(codebase),
    ]
    return CodeAgent(codebase=codebase, tools=pr_tools)

def get_repo_analysis_agent(codebase: Codebase) -> CodeAgent:
    """Create a code agent with repository analysis tools."""
    analysis_tools = [
        GithubViewPRTool(codebase),
        GithubCreatePRCommentTool(codebase),
        GithubCreatePRTool(codebase),
    ]
    return CodeAgent(codebase=codebase, tools=analysis_tools)

def get_linear_agent(codebase: Codebase) -> CodeAgent:
    """Create a code agent with Linear integration tools."""
    linear_tools = [
        LinearCreateIssueTool(codebase),
        LinearUpdateIssueTool(codebase),
        LinearCommentOnIssueTool(codebase),
        LinearGetIssueTool(codebase),
    ]
    return CodeAgent(codebase=codebase, tools=linear_tools)

def extract_repo_from_text(text: str) -> Optional[str]:
    """Extract repository name from text using regex patterns."""
    # Match GitHub URL patterns
    github_url_pattern = r'https?://(?:www\.)?github\.com/([^/\s]+/[^/\s]+)'
    url_match = re.search(github_url_pattern, text)
    if url_match:
        return url_match.group(1)
    
    # Match org/repo patterns
    repo_pattern = r'([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)'
    repo_match = re.search(repo_pattern, text)
    if repo_match:
        return repo_match.group(1)
    
    return None

def remove_bot_comments(repo_str: str, pr_number: int) -> None:
    """Remove all comments made by the bot on a PR."""
    g = Github(GITHUB_TOKEN)
    logger.info(f"Removing bot comments from {repo_str} PR #{pr_number}")
    
    repo = g.get_repo(repo_str)
    pr = repo.get_pull(int(pr_number))
    
    # Remove PR comments
    comments = pr.get_comments()
    if comments:
        for comment in comments:
            if comment.user.login == "codegen-app":  # Bot username
                logger.info("Removing comment")
                comment.delete()
    
    # Remove PR reviews
    reviews = pr.get_reviews()
    if reviews:
        for review in reviews:
            if review.user.login == "codegen-app":  # Bot username
                logger.info("Removing review")
                review.delete()
    
    # Remove issue comments
    issue_comments = pr.get_issue_comments()
    if issue_comments:
        for comment in issue_comments:
            if comment.user.login == "codegen-app":  # Bot username
                logger.info("Removing comment")
                comment.delete()

def parse_pr_suggestion_request(text: str) -> Dict[str, Any]:
    """Parse a PR suggestion request from Slack message text."""
    result = {
        "repo": extract_repo_from_text(text),
        "title": None,
        "description": None,
        "files": [],
    }
    
    # Extract PR title
    title_match = re.search(r'title[:\s]+([^\n]+)', text, re.IGNORECASE)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    # Extract PR description
    desc_match = re.search(r'description[:\s]+(.*?)(?:file[s]?:|$)', text, re.IGNORECASE | re.DOTALL)
    if desc_match:
        result["description"] = desc_match.group(1).strip()
    
    # Extract files to modify
    files_match = re.search(r'file[s]?[:\s]+(.*?)(?:$)', text, re.IGNORECASE | re.DOTALL)
    if files_match:
        files_text = files_match.group(1).strip()
        result["files"] = [f.strip() for f in files_text.split(',') if f.strip()]
    
    return result

########################################################################################################################
# EVENTS
########################################################################################################################

# Create the cg_app with Modal API key
cg = CodegenApp(
    name="codegen-app", 
    repo=DEFAULT_REPO,
    modal_api_key=MODAL_API_KEY
)

@cg.slack.event("app_mention")
async def handle_mention(event: SlackEvent, background_tasks: BackgroundTasks):
    """Handle Slack app mention events with advanced intent recognition."""
    logger.info("[APP_MENTION] Received app_mention event")
    
    # Send an immediate acknowledgment
    cg.slack.client.chat_postMessage(
        channel=event.channel, 
        text="I'm processing your request...", 
        thread_ts=event.ts
    )
    
    # Detect user intent
    intent, params = detect_intent(event.text)
    logger.info(f"[INTENT] Detected intent: {intent.value} with params: {params}")
    
    # Handle the intent with the appropriate handler
    if intent == UserIntent.ANALYZE_REPO:
        background_tasks.add_task(handle_repo_analysis, event, params)
        return {"message": "Repository analysis request received", "status": "processing"}
    
    elif intent == UserIntent.CREATE_PR:
        background_tasks.add_task(handle_pr_creation, event, params)
        return {"message": "PR creation request received", "status": "processing"}
    
    elif intent == UserIntent.SUGGEST_PR:
        background_tasks.add_task(handle_pr_suggestion, event, params)
        return {"message": "PR suggestion request received", "status": "processing"}
    
    elif intent == UserIntent.CREATE_ISSUE:
        background_tasks.add_task(handle_linear_issue_creation, event, params)
        return {"message": "Linear issue creation request received", "status": "processing"}
    
    elif intent == UserIntent.REVIEW_PR:
        background_tasks.add_task(handle_pr_review, event, params)
        return {"message": "PR review request received", "status": "processing"}
    
    else:  # UserIntent.GENERAL_QUESTION or UserIntent.UNKNOWN
        background_tasks.add_task(handle_default_mention, event)
        return {"message": "Default mention handling", "status": "processing"}

async def handle_repo_analysis(event: SlackEvent, params: Dict[str, Any]):
    """Handle repository analysis requests."""
    # Extract repository from params or use default
    repo_str = params.get("repo") or DEFAULT_REPO
    
    # Send initial status message
    status_msg = cg.slack.client.chat_postMessage(
        channel=event.channel,
        text=f"🔍 Analyzing repository `{repo_str}`...",
        thread_ts=event.ts
    )
    
    try:
        # Initialize codebase
        codebase = get_codebase_for_repo(repo_str)
        
        # Create analysis agent with enhanced tools
        agent = CodeAgent(
            codebase=codebase,
            tools=[
                ViewFileTool(codebase),
                ListDirectoryTool(codebase),
                RipGrepTool(codebase),
                SemanticSearchTool(codebase),
                RevealSymbolTool(codebase),
                GithubViewPRTool(codebase),
            ]
        )
        
        # Create prompt for repository analysis
        prompt = f"""
        Analyze the repository {repo_str} and provide a comprehensive report including:
        
        1. Overall architecture and structure
        2. Key components and their relationships
        3. Code quality assessment
        4. Potential areas for improvement
        5. Best practices being followed or missing
        
        Focus on providing actionable insights that would be valuable to the development team.
        Use the semantic search and symbol analysis tools to gain deeper insights into the codebase.
        """
        
        # Run the agent
        response = agent.run(prompt)
        
        # Format the response
        formatted_response = f"📊 *Repository Analysis for {repo_str}*\n\n{response}"
        
        # Update the status message with the result
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=formatted_response,
            thread_ts=event.ts
        )
    
    except Exception as e:
        # Handle errors
        logger.exception(f"Error in repository analysis: {e}")
        error_message = f"❌ *Error analyzing repository*\n\n```\n{str(e)}\n```\n\nPlease try again or contact support."
        
        # Update the status message with the error
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=error_message,
            thread_ts=event.ts
        )

async def handle_pr_creation(event: SlackEvent, params: Dict[str, Any]):
    """Handle PR creation requests."""
    # This is similar to handle_pr_suggestion but always creates a PR
    params["create_pr"] = True
    await handle_pr_suggestion(event, params)

async def handle_pr_suggestion(event: SlackEvent, params: Dict[str, Any]):
    """Handle PR suggestion requests and create actual PRs when requested."""
    # If no repository specified, use default
    repo_str = params.get("repo") or DEFAULT_REPO
    create_pr = params.get("create_pr", False) or "create pr" in event.text.lower()
    
    # Send initial status message
    status_msg = cg.slack.client.chat_postMessage(
        channel=event.channel,
        text=f"🔍 {'Creating PR for' if create_pr else 'Analyzing'} repository `{repo_str}`...",
        thread_ts=event.ts
    )
    
    try:
        # Initialize codebase
        codebase = get_codebase_for_repo(repo_str)
        
        if create_pr:
            # Create a unique branch name
            branch_name = f"codegen-pr-{uuid.uuid4().hex[:8]}"
            
            # Create PR creation agent with GitHub tools
            agent = CodeAgent(
                codebase=codebase,
                tools=[
                    GithubViewPRTool(codebase),
                    GithubCreatePRCommentTool(codebase),
                    GithubCreatePRTool(codebase),
                    ViewFileTool(codebase),
                    ListDirectoryTool(codebase),
                    RipGrepTool(codebase),
                    CreateFileTool(codebase),
                    DeleteFileTool(codebase),
                    RenameFileTool(codebase),
                    ReplacementEditTool(codebase),
                    RelaceEditTool(codebase),
                    SemanticSearchTool(codebase),
                    RevealSymbolTool(codebase),
                ]
            )
            
            # Create prompt for PR creation
            prompt = f"""
            Create a pull request for the repository {repo_str} with the following details:
            
            Branch name: {branch_name}
            Title: {params.get("title") or "Improvements by CodegenApp"}
            Description: {params.get("description") or "Improvements based on code analysis"}
            Files to focus on: {', '.join(params.get("files", [])) if params.get("files") else "Identify key files that need improvement"}
            
            Follow these steps:
            1. Analyze the codebase and identify areas for improvement
            2. Create a new branch named '{branch_name}'
            3. Make specific code changes to improve the identified areas
            4. Create a PR with the changes
            5. Return the PR URL and a summary of changes
            
            Focus on code quality, performance, and best practices.
            Use semantic search and symbol analysis to better understand the codebase structure.
            """
        else:
            # Create PR suggestion agent
            agent = CodeAgent(
                codebase=codebase,
                tools=[
                    ViewFileTool(codebase),
                    ListDirectoryTool(codebase),
                    RipGrepTool(codebase),
                    SemanticSearchTool(codebase),
                    RevealSymbolTool(codebase),
                ]
            )
            
            # Create prompt for PR suggestion
            prompt = f"""
            Create a pull request suggestion for the repository {repo_str} with the following details:
            
            Title: {params.get("title") or "Suggested improvements"}
            Description: {params.get("description") or "Improvements based on code analysis"}
            Files to focus on: {', '.join(params.get("files", [])) if params.get("files") else "Identify key files that need improvement"}
            
            Analyze the codebase, identify areas for improvement, and suggest specific code changes.
            Focus on code quality, performance, and best practices.
            Do not actually create the PR, just provide suggestions.
            Use semantic search and symbol analysis to better understand the codebase structure.
            """
        
        # Run the agent
        response = agent.run(prompt)
        
        # Extract PR URL if created
        pr_url = None
        if create_pr:
            import re
            url_match = re.search(r'https://github.com/[^/]+/[^/]+/pull/[0-9]+', response)
            if url_match:
                pr_url = url_match.group(0)
        
        # Format the response
        if create_pr and pr_url:
            formatted_response = f"🎉 *PR Created Successfully!*\n\n<{pr_url}|View PR on GitHub>\n\n{response}"
        elif create_pr:
            formatted_response = f"⚠️ *PR Creation Attempted*\n\n{response}\n\n_Note: Could not extract PR URL. Please check if PR was created successfully._"
        else:
            formatted_response = f"📋 *PR Suggestion for {repo_str}*\n\n{response}\n\n_To create this PR, use `create PR` instead of `suggest PR`._"
        
        # Update the status message with the result
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=formatted_response,
            thread_ts=event.ts
        )
    
    except Exception as e:
        # Handle errors
        logger.exception(f"Error in PR suggestion/creation: {e}")
        error_message = f"❌ *Error {'creating PR' if create_pr else 'suggesting PR changes'}*\n\n```\n{str(e)}\n```\n\nPlease try again or contact support."
        
        # Update the status message with the error
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=error_message,
            thread_ts=event.ts
        )

async def handle_pr_review(event: SlackEvent, params: Dict[str, Any]):
    """Handle PR review requests."""
    # Extract repository and PR number
    repo_str = params.get("repo") or DEFAULT_REPO
    pr_number = params.get("pr_number")
    
    if not pr_number:
        # Try to extract PR number from text if not in params
        pr_number_match = re.search(r'pr\s*#?(\d+)', event.text.lower())
        if pr_number_match:
            pr_number = int(pr_number_match.group(1))
        else:
            # Send error message if PR number not found
            cg.slack.client.chat_postMessage(
                channel=event.channel,
                text="❌ Error: PR number not specified. Please include a PR number (e.g., 'review PR #123').",
                thread_ts=event.ts
            )
            return
    
    # Send initial status message
    status_msg = cg.slack.client.chat_postMessage(
        channel=event.channel,
        text=f"🔍 Reviewing PR #{pr_number} in repository `{repo_str}`...",
        thread_ts=event.ts
    )
    
    try:
        # Initialize codebase
        codebase = get_codebase_for_repo(repo_str)
        
        # Create PR review agent
        agent = CodeAgent(
            codebase=codebase,
            tools=[
                GithubViewPRTool(codebase),
                GithubCreatePRCommentTool(codebase),
                GithubCreatePRReviewCommentTool(codebase),
                ViewFileTool(codebase),
                ListDirectoryTool(codebase),
                RipGrepTool(codebase),
                SemanticSearchTool(codebase),
                RevealSymbolTool(codebase),
            ]
        )
        
        # Create prompt for PR review
        prompt = f"""
        Please review pull request #{pr_number} in repository {repo_str}.
        
        Provide a comprehensive review that includes:
        1. A summary of the changes
        2. Code quality assessment
        3. Potential bugs or issues
        4. Suggestions for improvements
        
        Use the tools at your disposal to create proper PR review comments.
        Include code snippets if needed, and suggest specific improvements.
        Use semantic search and symbol analysis to better understand the impact of changes.
        """
        
        # Run the agent
        response = agent.run(prompt)
        
        # Format the response
        formatted_response = f"📝 *PR Review for {repo_str} PR #{pr_number}*\n\n{response}"
        
        # Update the status message with the result
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=formatted_response,
            thread_ts=event.ts
        )
    
    except Exception as e:
        # Handle errors
        logger.exception(f"Error in PR review: {e}")
        error_message = f"❌ *Error reviewing PR*\n\n```\n{str(e)}\n```\n\nPlease try again or contact support."
        
        # Update the status message with the error
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=error_message,
            thread_ts=event.ts
        )

async def handle_linear_issue_creation(event: SlackEvent, params: Dict[str, Any]):
    """Handle Linear issue creation requests with status updates."""
    # Extract repository from params (if applicable)
    repo_str = params.get("repo") or DEFAULT_REPO
    
    # Send initial status message
    status_msg = cg.slack.client.chat_postMessage(
        channel=event.channel,
        text=f"🔍 Creating Linear issue...",
        thread_ts=event.ts
    )
    
    try:
        # Initialize codebase
        codebase = get_codebase_for_repo(repo_str)
        
        # Create Linear agent
        agent = CodeAgent(
            codebase=codebase,
            tools=[
                LinearCreateIssueTool(codebase),
                LinearUpdateIssueTool(codebase),
                LinearCommentOnIssueTool(codebase),
                LinearGetIssueTool(codebase),
            ]
        )
        
        # Create prompt for Linear issue creation
        prompt = f"""
        Create a Linear issue with the following details:
        
        Title: {params.get('title') or 'Extract title from the message'}
        Description: {params.get('description') or 'Extract description from the message'}
        Priority: {params.get('priority') or 'Extract priority from the message'}
        
        If any details are missing, extract them from this message:
        {event.text}
        
        If the repository {repo_str} is relevant, include it in the issue description.
        
        Return the issue ID, title, and URL in your response.
        """
        
        # Run the agent
        response = agent.run(prompt)
        
        # Extract issue ID and URL if available
        import re
        issue_id_match = re.search(r'Issue ID: ([A-Z]+-[0-9]+)', response)
        issue_url_match = re.search(r'https://linear.app/[^ ]+', response)
        
        issue_id = issue_id_match.group(1) if issue_id_match else None
        issue_url = issue_url_match.group(0) if issue_url_match else None
        
        # Format the response
        if issue_id and issue_url:
            formatted_response = f"🎯 *Linear Issue Created Successfully!*\n\n<{issue_url}|View Issue {issue_id}>\n\n{response}"
        else:
            formatted_response = f"📋 *Linear Issue Creation*\n\n{response}"
        
        # Update the status message with the result
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=formatted_response,
            thread_ts=event.ts
        )
        
        # Send a notification to the configured channel if different from the request channel
        if SLACK_NOTIFICATION_CHANNEL and SLACK_NOTIFICATION_CHANNEL != event.channel:
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"New Linear issue created from Slack request in <#{event.channel}>"
            )
    
    except Exception as e:
        # Handle errors
        logger.exception(f"Error in Linear issue creation: {e}")
        error_message = f"❌ *Error creating Linear issue*\n\n```\n{str(e)}\n```\n\nPlease try again or contact support."
        
        # Update the status message with the error
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=error_message,
            thread_ts=event.ts
        )

async def handle_default_mention(event: SlackEvent):
    """Handle default mention requests with the code agent and enhanced response formatting."""
    # Send initial status message
    status_msg = cg.slack.client.chat_postMessage(
        channel=event.channel,
        text="🤔 Thinking about your request...",
        thread_ts=event.ts
    )
    
    try:
        # Initialize codebase
        codebase = cg.get_codebase()
        
        # Create code agent with comprehensive tools
        agent = CodeAgent(
            codebase=codebase,
            tools=[
                ViewFileTool(codebase),
                ListDirectoryTool(codebase),
                RipGrepTool(codebase),
                GithubViewPRTool(codebase),
                GithubCreatePRTool(codebase),
                LinearGetIssueTool(codebase),
                LinearCreateIssueTool(codebase),
                SemanticSearchTool(codebase),
                RevealSymbolTool(codebase),
            ]
        )
        
        # Create a more detailed prompt
        prompt = f"""
        You are CodegenApp, an AI assistant that helps with code-related tasks.
        
        User request: {event.text}
        
        Analyze the request and provide a helpful response. If the request is about:
        - Code analysis: Provide detailed insights
        - Repository information: Summarize key components
        - PR or issue creation: Suggest next steps
        - General questions: Provide clear, concise answers
        
        Format your response with Markdown for readability.
        Use semantic search and symbol analysis tools if they would help answer the question.
        """
        
        # Run the agent
        response = agent.run(prompt)
        
        # Update the status message with the result
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=response,
            thread_ts=event.ts
        )
    
    except Exception as e:
        # Handle errors
        logger.exception(f"Error in default mention handler: {e}")
        error_message = f"❌ *Error processing your request*\n\n```\n{str(e)}\n```\n\nPlease try again with a more specific request."
        
        # Update the status message with the error
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=error_message,
            thread_ts=event.ts
        )

@cg.github.event("pull_request:labeled")
def handle_pr_labeled(event: PullRequestLabeledEvent):
    """Handle pull request labeled events."""
    logger.info("[PULL_REQUEST:LABELED] Received pull request labeled event")
    logger.info(f"PR #{event.number} labeled with: {event.label.name}")
    
    # Check if the label matches our trigger label
    if event.label.name == TRIGGER_LABEL:
        # Send a Slack notification if configured
        if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"PR #{event.number} labeled with: {event.label.name}, starting review",
            )
        
        # Initialize the codebase for the repository
        repo_str = f"{event.organization.login}/{event.repository.name}"
        codebase = get_codebase_for_repo(repo_str)
        
        # Check out the PR head commit
        logger.info(f"Checking out PR head commit: {event.pull_request.head.sha}")
        codebase.checkout(commit=event.pull_request.head.sha)
        
        # Create an initial comment to indicate the review is starting
        review_attention_message = "CodegenApp is starting to review the PR, please wait..."
        comment = codebase._op.create_pr_comment(event.number, review_attention_message)
        
        # Create and run the PR review agent
        agent = get_pr_review_agent(codebase)
        
        # Using a prompt for PR review
        prompt = f"""
        Hey CodegenBot!

        Please review this pull request: {event.pull_request.url}
        
        Provide a comprehensive review that includes:
        1. A summary of the changes
        2. Code quality assessment
        3. Potential bugs or issues
        4. Suggestions for improvements
        
        Use the tools at your disposal to create proper PR review comments.
        Include code snippets if needed, and suggest specific improvements.
        """
        
        # Run the agent
        logger.info(f"Starting PR review for {repo_str} PR #{event.number}")
        agent.run(prompt)
        
        # Delete the initial comment
        comment.delete()
        
        # Send a completion notification to Slack
        if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"Completed PR review for {repo_str} PR #{event.number}"
            )
    
    return {"message": "PR labeled event handled", "label": event.label.name}

@cg.github.event("pull_request:unlabeled")
def handle_pr_unlabeled(event: PullRequestUnlabeledEvent):
    """Handle pull request unlabeled events."""
    logger.info("[PULL_REQUEST:UNLABELED] Received pull request unlabeled event")
    logger.info(f"PR #{event.number} unlabeled with: {event.label.name}")
    
    # Check if the label matches our trigger label
    if event.label.name == TRIGGER_LABEL:
        # Initialize the codebase for the repository
        repo_str = f"{event.organization.login}/{event.repository.name}"
        
        # Remove bot comments
        remove_bot_comments(repo_str, event.number)
        
        # Send a Slack notification if configured
        if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"PR #{event.number} unlabeled with: {event.label.name}, removed review comments",
            )
    
    return {"message": "PR unlabeled event handled", "label": event.label.name}

@cg.github.event("pull_request:opened")
def handle_pr_opened(event: PullRequestOpenedEvent):
    """Handle pull request opened events."""
    logger.info("[PULL_REQUEST:OPENED] Received pull request opened event")
    logger.info(f"PR #{event.number} opened: {event.pull_request.title}")
    
    # Initialize the codebase for the repository
    repo_str = f"{event.organization.login}/{event.repository.name}"
    codebase = get_codebase_for_repo(repo_str)
    
    # Create a welcome comment
    welcome_message = (
        f"👋 Thanks for opening this PR!\n\n"
        f"To get an AI-powered code review, add the `{TRIGGER_LABEL}` label to this PR."
    )
    create_pr_comment(codebase, event.number, welcome_message)
    
    # Send a Slack notification if configured
    if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
        cg.slack.client.chat_postMessage(
            channel=SLACK_NOTIFICATION_CHANNEL,
            text=f"New PR opened: {event.pull_request.title} - {event.pull_request.html_url}",
        )
    
    return {"message": "PR opened event handled", "title": event.pull_request.title}

@cg.github.event("pull_request:review_requested")
def handle_pr_review_requested(event: PullRequestReviewRequestedEvent):
    """Handle pull request review requested events."""
    logger.info("[PULL_REQUEST:REVIEW_REQUESTED] Received pull request review requested event")
    logger.info(f"PR #{event.number} review requested")
    
    # Check if the review was requested from the bot
    # This would require knowing the bot's GitHub username
    # For now, we'll just add the trigger label to automatically start a review
    
    # Initialize the codebase for the repository
    repo_str = f"{event.organization.login}/{event.repository.name}"
    codebase = get_codebase_for_repo(repo_str)
    
    # Add the trigger label to start a review
    from github import Github
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(repo_str)
    pr = repo.get_pull(int(event.number))
    pr.add_to_labels(TRIGGER_LABEL)
    
    return {"message": "PR review requested event handled", "number": event.number}

@cg.linear.event("Issue")
def handle_linear_issue(event: LinearEvent):
    """Handle Linear issue events."""
    logger.info(f"[LINEAR:ISSUE] Linear issue event: {event.action}")
    
    # Initialize codebase
    codebase = cg.get_codebase()
    
    # Send a Slack notification if configured
    if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
        if event.action == "create":
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"New Linear issue created: {event.data.title}",
            )
        elif event.action == "update":
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"Linear issue updated: {event.data.title}",
            )
    
    return {"message": f"Linear Issue {event.action} event handled", "title": event.data.title}

@cg.linear.event("Comment")
def handle_linear_comment(event: LinearEvent):
    """Handle Linear comment events."""
    logger.info(f"[LINEAR:COMMENT] Linear comment event: {event.action}")
    
    # Initialize codebase
    codebase = cg.get_codebase()
    
    # Send a Slack notification if configured
    if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
        if event.action == "create":
            cg.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"New comment on Linear issue: {event.data.body}",
            )
    
    return {"message": f"Linear Comment {event.action} event handled"}

########################################################################################################################
# MODAL DEPLOYMENT
########################################################################################################################
# This deploys the FastAPI app to Modal

# For deploying local package
REPO_URL = "https://github.com/codegen-sh/codegen-sdk.git"
COMMIT_ID = "6a0e101718c247c01399c60b7abf301278a41786"

# Create the base image with dependencies
base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install(
        # =====[ Codegen ]=====
        f"git+{REPO_URL}@{COMMIT_ID}",
        # =====[ Rest ]=====
        "openai>=1.1.0",
        "anthropic>=0.5.0",
        "fastapi[standard]",
        "slack_sdk",
        "pygithub",
        "linear-sdk",
    )
)

app = modal.App("codegen-app")

@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def fastapi_app():
    """Entry point for the FastAPI app."""
    logger.info("Starting codegen FastAPI app")
    return cg.app

@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.web_endpoint(method="POST")
def entrypoint(event: dict, request: Request):
    """Entry point for GitHub webhook events."""
    logger.info("[OUTER] Received GitHub webhook")
    return cg.github.handle(event, request)
