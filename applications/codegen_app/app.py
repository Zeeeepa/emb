import logging
import os
import re
import sys
import uuid
import tempfile
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Union

import modal

# Import codegen packages
from codegen import CodegenApp, Codebase
from codegen.configs.models.secrets import SecretsConfig
from codegen.git.repo_operator.repo_operator import RepoOperator

# Import agentgen packages - we need to handle this differently for Modal deployment
try:
    from agentgen import CodeAgent, ChatAgent, create_codebase_agent, create_chat_agent, create_codebase_inspector_agent, create_agent_with_tools
    from agentgen.extensions.github.types.events.pull_request import (
        PullRequestLabeledEvent,
        PullRequestOpenedEvent,
        PullRequestReviewRequestedEvent,
        PullRequestUnlabeledEvent
    )
    # Linear imports removed
    from agentgen.extensions.slack.types import SlackEvent
    from agentgen.extensions.tools.github.create_pr_comment import create_pr_comment
    from agentgen.extensions.langchain.tools import (
        GithubViewPRTool,
        GithubCreatePRCommentTool,
        GithubCreatePRReviewCommentTool,
        GithubCreatePRTool,
        # Linear tools removed
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
    from agentgen.extensions.langchain.graph import create_react_agent
    from agentgen.extensions.events.client import EventClient
except ImportError:
    # If we're in the Modal environment, we need to ensure the package is properly imported
    print("Failed to import agentgen directly. This is expected in Modal deployment.")
    # We'll import these modules after the Modal image is built

from fastapi import Request, BackgroundTasks
from github import Github
from langchain_core.messages import SystemMessage

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
    Detect the user's intent from their message text using advanced NLP techniques.
    
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
    
    # Analyze repository intent - expanded patterns
    if any(phrase in text_lower for phrase in [
        "analyze repo", "analyze repository", "analyze codebase", "code analysis",
        "examine repo", "examine codebase", "look at repo", "check repo", 
        "review codebase", "understand repo", "explore repo"
    ]):
        return UserIntent.ANALYZE_REPO, params
    
    # PR creation intent - expanded patterns
    if any(phrase in text_lower for phrase in [
        "create pr", "make pr", "submit pr", "open pr", 
        "create pull request", "make a pull request", "implement", "code up",
        "build feature", "add feature", "fix bug", "implement feature"
    ]):
        pr_params = parse_pr_suggestion_request(text)
        params.update(pr_params)
        return UserIntent.CREATE_PR, params
    
    # PR suggestion intent - expanded patterns
    if any(phrase in text_lower for phrase in [
        "suggest pr", "pr suggestion", "recommend changes", "propose pr",
        "suggest changes", "suggest improvements", "recommend pr", "how would you change",
        "what changes", "how to improve", "suggest refactoring"
    ]):
        pr_params = parse_pr_suggestion_request(text)
        params.update(pr_params)
        return UserIntent.SUGGEST_PR, params
    
    # Issue creation intent - expanded patterns
    if any(phrase in text_lower for phrase in [
        "create issue", "create ticket", "new issue", "open issue",
        "make issue", "file issue", "report bug", "track feature", "add task",
        "create task", "make ticket", "add to backlog"
    ]):
        issue_params = parse_issue_request(text)
        params.update(issue_params)
        return UserIntent.CREATE_ISSUE, params
    
    # PR review intent - expanded patterns
    if any(phrase in text_lower for phrase in [
        "review pr", "review pull request", "check pr", "evaluate pr",
        "look at pr", "assess pr", "analyze pr", "examine pr", "feedback on pr"
    ]):
        pr_number_match = re.search(r'pr\s*#?(\d+)', text_lower)
        if pr_number_match:
            params["pr_number"] = int(pr_number_match.group(1))
        return UserIntent.REVIEW_PR, params
    
    # Default to general question if no specific intent is detected
    return UserIntent.GENERAL_QUESTION, params

def parse_issue_request(text: str) -> Dict[str, Any]:
    """Parse an issue creation request from Slack message text with improved pattern matching."""
    result = {
        "title": None,
        "description": None,
        "priority": None,
        "assignee": None,
        "labels": [],
    }
    
    # Extract issue title
    title_match = re.search(r'title[:\s]+([^\n]+)', text, re.IGNORECASE)
    if title_match:
        result["title"] = title_match.group(1).strip()
    
    # Extract issue description
    desc_match = re.search(r'description[:\s]+(.*?)(?:priority|assignee|labels|$)', text, re.IGNORECASE | re.DOTALL)
    if desc_match:
        result["description"] = desc_match.group(1).strip()
    
    # Extract priority
    priority_match = re.search(r'priority[:\s]+(high|medium|low|urgent)', text, re.IGNORECASE)
    if priority_match:
        result["priority"] = priority_match.group(1).lower()
    
    # Extract assignee
    assignee_match = re.search(r'assignee[:\s]+([^\n,]+)', text, re.IGNORECASE)
    if assignee_match:
        result["assignee"] = assignee_match.group(1).strip()
    
    # Extract labels
    labels_match = re.search(r'labels[:\s]+([^\n]+)', text, re.IGNORECASE)
    if labels_match:
        labels_text = labels_match.group(1).strip()
        result["labels"] = [label.strip() for label in labels_text.split(',')]
    
    return result

# REPOSITORY MANAGEMENT
########################################################################################################################

class RepoManager:
    """
    Advanced repository manager that leverages codegen's git functionality.
    Manages repository cloning, caching, and access with efficient operations.
    """
    def __init__(self, cache_dir: str = REPO_CACHE_DIR):
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
            if repo_str in self.repo_operators:
                logger.info(f"[REPO_MANAGER] Clearing repo operator for {repo_str}")
                del self.repo_operators[repo_str]
        else:
            logger.info("[REPO_MANAGER] Clearing entire cache")
            self.repo_cache.clear()
            self.repo_operators.clear()

# Initialize the repository manager
repo_manager = RepoManager()

def get_codebase_for_repo(repo_str: str) -> Codebase:
    """Initialize a codebase for a specific repository using the repo manager."""
    return repo_manager.get_codebase(repo_str)

# HELPER FUNCTIONS
########################################################################################################################

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

# AGENT CREATION
########################################################################################################################

def create_advanced_code_agent(codebase: Codebase):
    """
    Create an advanced code agent with comprehensive tools for code analysis and manipulation.
    
    This agent combines semantic search, symbol analysis, and code editing capabilities
    to provide deep insights into codebases and make precise modifications.
    
    Args:
        codebase: The codebase to operate on
        
    Returns:
        A CodeAgent with comprehensive tools
    """
    # Import agentgen modules here to ensure they're available in the Modal environment
    try:
        from agentgen import create_agent_with_tools
        from agentgen.extensions.langchain.tools import (
            ViewFileTool,
            ListDirectoryTool,
            RipGrepTool,
            SemanticSearchTool,
            RevealSymbolTool,
            CreateFileTool,
            DeleteFileTool,
            RenameFileTool,
            ReplacementEditTool,
            RelaceEditTool,
            GithubViewPRTool,
            GithubCreatePRCommentTool,
            GithubCreatePRReviewCommentTool,
            GithubCreatePRTool,
            # Linear tools removed
        )
        from langchain_core.messages import SystemMessage
        
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
            GithubViewPRTool(codebase),
            GithubCreatePRCommentTool(codebase),
            GithubCreatePRReviewCommentTool(codebase),
            GithubCreatePRTool(codebase),
            
            # Linear tools removed
        ]
        
        # Create agent with enhanced tools
        return create_agent_with_tools(
            codebase=codebase,
            tools=tools,
            system_message=SystemMessage(content="""
            You are an expert code assistant that helps developers understand and improve their code.
            You have access to a comprehensive set of tools for code analysis and manipulation.
            
            When analyzing code or suggesting changes, consider:
            1. The overall architecture and design patterns
            2. Dependencies between components
            3. Potential side effects of changes
            4. Best practices for the specific language and framework
            5. Performance implications
            
            Your goal is to provide high-quality, contextually aware assistance.
            """)
        )
    except ImportError as e:
        logger.error(f"Failed to import agentgen modules: {e}")
        raise

def create_chat_agent_with_graph(codebase: Codebase, system_message: str):
    """
    Create a chat agent using the LangGraph architecture for more robust conversation handling.
    
    This agent uses the LangGraph framework to manage conversation state, handle errors,
    and provide a more natural conversational experience.
    
    Args:
        codebase: The codebase to operate on
        system_message: The system message to initialize the agent with
        
    Returns:
        A LangGraph-based chat agent
    """
    # Import agentgen modules here to ensure they're available in the Modal environment
    try:
        from agentgen.extensions.langchain.llm import LLM
        from agentgen.extensions.langchain.tools import (
            ViewFileTool,
            ListDirectoryTool,
            RipGrepTool,
            SemanticSearchTool,
            RevealSymbolTool,
            GithubViewPRTool,
            # Linear tools removed
        )
        from agentgen.extensions.langchain.graph import create_react_agent
        from langchain_core.messages import SystemMessage
        
        # Create LLM based on available API keys
        if ANTHROPIC_API_KEY:
            model = LLM(
                model_provider="anthropic",
                model_name="claude-3-opus-20240229",
                temperature=0.2,
                anthropic_api_key=ANTHROPIC_API_KEY
            )
        elif OPENAI_API_KEY:
            model = LLM(
                model_provider="openai",
                model_name="gpt-4-turbo",
                temperature=0.2,
                openai_api_key=OPENAI_API_KEY
            )
        else:
            raise ValueError("No LLM API keys available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
        
        # Create tools list with enhanced context understanding
        tools = [
            ViewFileTool(codebase),
            ListDirectoryTool(codebase),
            RipGrepTool(codebase),
            SemanticSearchTool(codebase),
            RevealSymbolTool(codebase),
            GithubViewPRTool(codebase),
            # Linear tools removed
        ]
        
        # Create enhanced system message
        enhanced_system_message = f"""
        {system_message}
        
        You have access to advanced code analysis capabilities.
        When analyzing code or suggesting changes, consider:
        1. The overall architecture and design patterns
        2. Dependencies between components
        3. Potential side effects of changes
        4. Best practices for the specific language and framework
        5. Performance implications
        
        Your goal is to provide high-quality, contextually aware assistance.
        """
        
        system_msg = SystemMessage(content=enhanced_system_message)
        
        # Create agent config
        config = {
            "max_messages": 100,
            "keep_first_messages": 2,
        }
        
        # Create and return the agent graph
        return create_react_agent(model=model, tools=tools, system_message=system_msg, config=config)
    except ImportError as e:
        logger.error(f"Failed to import agentgen modules: {e}")
        raise

# MODAL DEPLOYMENT
########################################################################################################################
# This deploys the FastAPI app to Modal

# For deploying local package
REPO_URL = "https://github.com/codegen-sh/codegen-sdk.git"
COMMIT_ID = "6a0e101718c247c01399c60b7abf301278a41786"

# Function to verify agentgen installation during image build
def verify_agentgen_installation():
    print("Verifying agentgen installation...")
    import sys
    import os
    import pkg_resources
    
    # Add root to Python path
    sys.path.append('/root')
    
    # List contents of root directory
    os.system('ls -la /root')
    
    # Print debug information
    print("Python path:", sys.path)
    print("Installed packages:", list(pkg_resources.working_set.by_key.keys()))
    
    # Try importing agentgen
    try:
        import agentgen
        print(f"AgentGen version: {agentgen.__version__}")
        print("AgentGen installation verified!")
        return True
    except ImportError as e:
        print(f"Failed to import agentgen: {e}")
        return False

# Create the base image with dependencies
base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install(
        # =====[ Codegen ]=====
        f"git+{REPO_URL}@{COMMIT_ID}",
        # =====[ AgentGen ]=====
        "git+https://github.com/Zeeeepa/emb.git#subdirectory=AgentGen",
        # =====[ Rest ]=====
        "openai>=1.1.0",
        "anthropic>=0.5.0",
        "fastapi[standard]",
        "slack_sdk",
        "pygithub",
    )
    .run_function(verify_agentgen_installation)
)

app = modal.App("coder")

@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def fastapi_app():
    """Entry point for the FastAPI app."""
    # Import here to ensure the imports work in the Modal environment
    import sys
    import os
    
    # Add paths to ensure agentgen is found
    sys.path.append('/root')
    
    # Now import the required modules
    from agentgen.extensions.events.client import EventClient
    from fastapi import FastAPI
    
    # Create the FastAPI app
    logger.info("Starting coder FastAPI app")
    app = FastAPI()
    
    # Set up event handlers
    event_client = EventClient()
    
    # Return the app
    return app

@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.fastapi_endpoint(method="POST")
def entrypoint(event: dict, request: Request):
    """Entry point for GitHub webhook events."""
    # Import here to ensure the imports work in the Modal environment
    import sys
    import os
    
    # Add paths to ensure agentgen is found
    sys.path.append('/root')
    
    # Now import the required modules
    from agentgen.extensions.events.client import EventClient
    
    # Create the event client
    event_client = EventClient()
    
    logger.info("[OUTER] Received GitHub webhook")
    return event_client.handle_github_event(event, request)