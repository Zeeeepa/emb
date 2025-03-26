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
            # Process the PR opened event
            return {"message": "PR opened event handled"}
        
        @cg.github.event("pull_request:labeled")
        def handle_pr_labeled(event: dict):
            logger.info(f"Handling PR labeled event: {event}")
            # Process the PR labeled event
            return {"message": "PR labeled event handled"}
        
        # Set up Slack event handlers
        @cg.slack.event("app_mention")
        async def handle_app_mention(event: dict):
            logger.info(f"Handling app mention event: {event}")
            # Process the app mention event
            
            # Get the text of the message
            text = event.get("text", "")
            user = event.get("user", "")
            channel = event.get("channel", "")
            
            # Send a response
            cg.slack.client.chat_postMessage(
                channel=channel,
                text=f"Hello <@{user}>! I received your message: {text}",
                thread_ts=event.get("thread_ts", event.get("ts"))
            )
            
            return {"message": "App mention event handled"}
        
        @cg.slack.event("message")
        async def handle_message(event: dict):
            logger.info(f"Handling message event: {event}")
            # Only respond to messages in channels, not DMs
            if event.get("channel_type") == "channel":
                # Process the message event
                return {"message": "Message event handled"}
            return {"message": "Ignoring DM"}

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