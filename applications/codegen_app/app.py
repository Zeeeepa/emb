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

    from agentgen.extensions.slack.types import SlackEvent
    from agentgen.extensions.tools.github.create_pr_comment import create_pr_comment
    from agentgen.extensions.langchain.tools import (
        GithubViewPRTool,
        GithubCreatePRCommentTool,
        GithubCreatePRReviewCommentTool,
        GithubCreatePRTool,
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
    from agentgen.extensions.events.modal.base import EventRouterMixin, CodebaseEventsApp
    from agentgen.extensions.events.codegen_app import CodegenApp as AgentGenCodegenApp
    from agentgen.extensions.events.github import GitHub
    from agentgen.extensions.events.slack import Slack
    from langchain_core.messages import SystemMessage
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

    def push_changes(self, repo_str: str, branch_name: str) -> bool:
        """
        Push changes to the repository.

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
            logger.exception(f"Error pushing changes to {repo_str}: {e}")
            return False

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

# Create the Modal app
app = modal.App("coder")

# Initialize the repository manager
repo_manager = RepoManager()

# Define the CodebaseEventsApp implementation
@app.cls(image=base_image, container_idle_timeout=300)
class CodegenEventsApp(CodebaseEventsApp):
    """
    Implementation of CodebaseEventsApp for handling events.
    This class is responsible for setting up event handlers for GitHub and Slack events.
    """
    
    def setup_handlers(self, cg: AgentGenCodegenApp):
        """
        Set up event handlers for GitHub and Slack events.
        
        Args:
            cg: The CodegenApp instance to use for handling events
        """
        logger.info("Setting up event handlers")
        
        # Set up GitHub event handlers
        @cg.github.event("pull_request:opened")
        def handle_pr_opened(event: dict):
            logger.info(f"Handling PR opened event: {event}")
            
            # Extract repository information
            repo_name = event.get("repository", {}).get("full_name", DEFAULT_REPO)
            pr_number = event.get("number")
            
            if not pr_number:
                return {"message": "No PR number found in event"}
            
            # Get the codebase for the repository
            try:
                codebase = repo_manager.get_codebase(repo_name)
                
                # Create an advanced code agent for the repository
                agent = create_advanced_code_agent(codebase)
                
                # Analyze the PR
                pr_analysis = agent.run(f"Analyze PR #{pr_number} and provide a summary of the changes.")
                
                # Comment on the PR with the analysis
                if GITHUB_TOKEN:
                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(repo_name)
                    pr = repo.get_pull(pr_number)
                    pr.create_issue_comment(pr_analysis)
                
                return {"message": "PR opened event handled", "analysis": pr_analysis}
            except Exception as e:
                logger.exception(f"Error handling PR opened event: {e}")
                return {"message": f"Error handling PR opened event: {str(e)}"}
        
        @cg.github.event("pull_request:labeled")
        def handle_pr_labeled(event: dict):
            logger.info(f"Handling PR labeled event: {event}")
            
            # Extract repository information
            repo_name = event.get("repository", {}).get("full_name", DEFAULT_REPO)
            pr_number = event.get("number")
            label = event.get("label", {}).get("name", "")
            
            if not pr_number:
                return {"message": "No PR number found in event"}
            
            # Only process if the label matches the trigger label
            if label != TRIGGER_LABEL:
                return {"message": f"Ignoring label {label}, not a trigger label"}
            
            # Get the codebase for the repository
            try:
                codebase = repo_manager.get_codebase(repo_name)
                
                # Create an advanced code agent for the repository
                agent = create_advanced_code_agent(codebase)
                
                # Analyze the PR
                pr_analysis = agent.run(f"Analyze PR #{pr_number} in detail and provide a comprehensive review.")
                
                # Comment on the PR with the analysis
                if GITHUB_TOKEN:
                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(repo_name)
                    pr = repo.get_pull(pr_number)
                    pr.create_issue_comment(pr_analysis)
                
                return {"message": "PR labeled event handled", "analysis": pr_analysis}
            except Exception as e:
                logger.exception(f"Error handling PR labeled event: {e}")
                return {"message": f"Error handling PR labeled event: {str(e)}"}
        
        # Set up Slack event handlers
        @cg.slack.event("app_mention")
        async def handle_app_mention(event: dict):
            logger.info(f"Handling app mention event: {event}")
            
            # Get the text of the message
            text = event.get("text", "")
            user = event.get("user", "")
            channel = event.get("channel", "")
            thread_ts = event.get("thread_ts", event.get("ts"))
            
            # Send an acknowledgement
            cg.slack.client.chat_postMessage(
                channel=channel,
                text=f"Hello <@{user}>! I'm processing your request...",
                thread_ts=thread_ts
            )
            
            # Extract repository information from the message
            repo_pattern = r"(?:analyze|review|check)\s+(?:repo|repository)\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"
            repo_match = re.search(repo_pattern, text, re.IGNORECASE)
            
            repo_name = repo_match.group(1) if repo_match else DEFAULT_REPO
            
            try:
                # Get the codebase for the repository
                codebase = repo_manager.get_codebase(repo_name)
                
                # Create a chat agent for the repository
                agent = create_chat_agent_with_graph(codebase, f"""
                You are a helpful code assistant that can analyze repositories and answer questions about code.
                You are currently analyzing the repository {repo_name}.
                """)
                
                # Process the message
                response = agent.run(text)
                
                # Send the response
                cg.slack.client.chat_postMessage(
                    channel=channel,
                    text=response,
                    thread_ts=thread_ts
                )
                
                return {"message": "App mention event handled", "response": response}
            except Exception as e:
                logger.exception(f"Error handling app mention event: {e}")
                
                # Send error message
                cg.slack.client.chat_postMessage(
                    channel=channel,
                    text=f"Sorry, I encountered an error: {str(e)}",
                    thread_ts=thread_ts
                )
                
                return {"message": f"Error handling app mention event: {str(e)}"}
        
        @cg.slack.event("message")
        async def handle_message(event: dict):
            logger.info(f"Handling message event: {event}")
            
            # Only respond to messages in channels, not DMs
            if event.get("channel_type") == "channel":
                # Only respond to messages in threads or direct mentions
                if event.get("thread_ts") or f"<@{cg.slack.client.auth_test()['user_id']}>" in event.get("text", ""):
                    # Process the message similar to app_mention
                    text = event.get("text", "")
                    user = event.get("user", "")
                    channel = event.get("channel", "")
                    thread_ts = event.get("thread_ts", event.get("ts"))
                    
                    # Extract repository information from the message
                    repo_pattern = r"(?:analyze|review|check)\s+(?:repo|repository)\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"
                    repo_match = re.search(repo_pattern, text, re.IGNORECASE)
                    
                    repo_name = repo_match.group(1) if repo_match else DEFAULT_REPO
                    
                    try:
                        # Get the codebase for the repository
                        codebase = repo_manager.get_codebase(repo_name)
                        
                        # Create a chat agent for the repository
                        agent = create_chat_agent_with_graph(codebase, f"""
                        You are a helpful code assistant that can analyze repositories and answer questions about code.
                        You are currently analyzing the repository {repo_name}.
                        """)
                        
                        # Process the message
                        response = agent.run(text)
                        
                        # Send the response
                        cg.slack.client.chat_postMessage(
                            channel=channel,
                            text=response,
                            thread_ts=thread_ts
                        )
                        
                        return {"message": "Message event handled", "response": response}
                    except Exception as e:
                        logger.exception(f"Error handling message event: {e}")
                        
                        # Send error message
                        cg.slack.client.chat_postMessage(
                            channel=channel,
                            text=f"Sorry, I encountered an error: {str(e)}",
                            thread_ts=thread_ts
                        )
                        
                        return {"message": f"Error handling message event: {str(e)}"}
            
            return {"message": "Ignoring message"}

# Define the EventRouterMixin implementation
@app.cls(image=base_image)
class CodegenEventsAPI(EventRouterMixin):
    """
    Implementation of EventRouterMixin for routing events to the correct handler.
    This class is responsible for routing events to the CodegenEventsApp.
    """
    
    def get_event_handler_cls(self):
        """Get the Modal Class where the event handlers are defined."""
        return CodegenEventsApp

# Define the FastAPI app endpoint
@app.function(image=base_image)
@modal.asgi_app()
def fastapi_app():
    """Entry point for the FastAPI app."""
    # Import here to ensure the imports work in the Modal environment
    import sys
    import os
    
    # Add paths to ensure agentgen is found
    sys.path.append('/root')
    
    # Now import the required modules
    from fastapi import FastAPI
    
    # Create the FastAPI app
    logger.info("Starting coder FastAPI app")
    app = FastAPI()
    
    # Create the event router
    event_router = CodegenEventsAPI()
    
    # Set up routes
    @app.get("/")
    async def root():
        return {"message": "Welcome to the Codegen App"}
    
    @app.post("/github/events")
    async def github_events(request: Request):
        """Handle GitHub webhook events."""
        logger.info("Received GitHub webhook")
        org = request.query_params.get("org", "codegen-sh")
        repo = request.query_params.get("repo", "Kevin-s-Adventure-Game")
        return await event_router.handle_event(org=org, repo=repo, provider="github", request=request)
    
    @app.post("/slack/events")
    async def slack_events(request: Request):
        """Handle Slack events."""
        logger.info("Received Slack event")
        org = request.query_params.get("org", "codegen-sh")
        repo = request.query_params.get("repo", "Kevin-s-Adventure-Game")
        return await event_router.handle_event(org=org, repo=repo, provider="slack", request=request)
    
    # Return the app
    return app

# Define the webhook endpoint for GitHub events
@app.function(image=base_image)
@modal.fastapi_endpoint(method="POST")
def github_webhook(event: dict, request: Request):
    """Entry point for GitHub webhook events."""
    # Import here to ensure the imports work in the Modal environment
    import sys
    import os
    
    # Add paths to ensure agentgen is found
    sys.path.append('/root')
    
    # Create the event router
    event_router = CodegenEventsAPI()
    
    # Extract org and repo from the event
    org = "codegen-sh"
    repo = "Kevin-s-Adventure-Game"
    
    if "repository" in event:
        full_name = event["repository"].get("full_name", "")
        if "/" in full_name:
            org, repo = full_name.split("/", 1)
    
    logger.info(f"Handling GitHub webhook for {org}/{repo}")
    return event_router.handle_event(org=org, repo=repo, provider="github", request=request)

# Define the webhook endpoint for Slack events
@app.function(image=base_image)
@modal.fastapi_endpoint(method="POST")
def slack_webhook(event: dict, request: Request):
    """Entry point for Slack events."""
    # Import here to ensure the imports work in the Modal environment
    import sys
    import os
    
    # Add paths to ensure agentgen is found
    sys.path.append('/root')
    
    # Create the event router
    event_router = CodegenEventsAPI()
    
    # Use default org and repo for Slack events
    org = "codegen-sh"
    repo = "Kevin-s-Adventure-Game"
    
    logger.info(f"Handling Slack webhook for {org}/{repo}")
    return event_router.handle_event(org=org, repo=repo, provider="slack", request=request)

# Define the entrypoint for the app
@app.function(image=base_image)
@modal.fastapi_endpoint(method="GET")
def entrypoint():
    """Entry point for the app."""
    return {
        "message": "Welcome to the Codegen App",
        "endpoints": {
            "github_webhook": "/github/events",
            "slack_webhook": "/slack/events",
        }
    }
