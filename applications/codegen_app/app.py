import logging
import os
import re
import uuid
import tempfile
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Union

import modal
from codegen import CodegenApp, Codebase
from codegen.configs.models.secrets import SecretsConfig
from codegen.git.repo_operator import RepoOperator
from agentgen import CodeAgent, ChatAgent, create_codebase_agent, create_chat_agent, create_codebase_inspector_agent, create_agent_with_tools
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
from agentgen.extensions.langchain.graph import create_react_agent
from agentgen.extensions.events.client import EventClient
from agentgen.extensions.context import CodeContextProvider
from agentgen.extensions.planning import PlanningAgent
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

# ... keep existing intent recognition code ...

# ... keep existing repository management code ...

# ... keep existing helper functions ...

########################################################################################################################
# AGENT CREATION
########################################################################################################################

def create_advanced_code_agent(codebase: Codebase) -> CodeAgent:
    """
    Create an advanced code agent with comprehensive tools for code analysis and manipulation.
    
    This agent combines semantic search, symbol analysis, and code editing capabilities
    to provide deep insights into codebases and make precise modifications.
    
    Args:
        codebase: The codebase to operate on
        
    Returns:
        A CodeAgent with comprehensive tools
    """
    # Create a context provider for enhanced code understanding
    context_provider = CodeContextProvider(codebase)
    
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
        
        # Linear tools
        LinearCreateIssueTool(codebase),
        LinearUpdateIssueTool(codebase),
        LinearCommentOnIssueTool(codebase),
        LinearGetIssueTool(codebase),
    ]
    
    # Create agent with enhanced context understanding
    return create_agent_with_tools(
        codebase=codebase,
        tools=tools,
        context_provider=context_provider
    )

def create_planning_code_agent(codebase: Codebase, task_description: str) -> Any:
    """
    Create a planning-based code agent that can break down complex tasks into steps.
    
    This agent uses a planning approach to decompose complex coding tasks into
    manageable steps, improving the quality of PR implementations.
    
    Args:
        codebase: The codebase to operate on
        task_description: Description of the coding task to perform
        
    Returns:
        A planning-based code agent
    """
    # Create context provider for enhanced code understanding
    context_provider = CodeContextProvider(codebase)
    
    # Create tools list
    tools = [
        ViewFileTool(codebase),
        ListDirectoryTool(codebase),
        RipGrepTool(codebase),
        SemanticSearchTool(codebase),
        RevealSymbolTool(codebase),
        CreateFileTool(codebase),
        DeleteFileTool(codebase),
        RenameFileTool(codebase),
        ReplacementEditTool(codebase),
        RelaceEditTool(codebase),
        GithubCreatePRTool(codebase),
    ]
    
    # Create planning agent
    return PlanningAgent(
        codebase=codebase,
        tools=tools,
        context_provider=context_provider,
        task_description=task_description
    )

def create_chat_agent_with_graph(codebase: Codebase, system_message: str) -> Any:
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
    from agentgen.extensions.langchain.llm import LLM
    
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
        LinearGetIssueTool(codebase),
    ]
    
    # Create context provider
    context_provider = CodeContextProvider(codebase)
    
    # Create system message with enhanced context understanding
    enhanced_system_message = f"""
    {system_message}
    
    You have access to advanced code context understanding capabilities.
    Use the context provider to gain deeper insights into the codebase structure,
    dependencies, and relationships between components.
    
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
    
    # Create and return the agent graph with context provider
    return create_react_agent(model, tools, system_msg, config=config, context_provider=context_provider)

# ... keep existing events ...

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

app = modal.App("coder")  # Changed from "codegen-app" to "coder"

@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def fastapi_app():
    """Entry point for the FastAPI app."""
    logger.info("Starting coder FastAPI app")  # Updated log message
    return cg.app

@app.function(image=base_image, secrets=[modal.Secret.from_dotenv()])
@modal.web_endpoint(method="POST")
def entrypoint(event: dict, request: Request):
    """Entry point for GitHub webhook events."""
    logger.info("[OUTER] Received GitHub webhook")
    return cg.github.handle(event, request)

async def handle_pr_creation(event: SlackEvent, params: Dict[str, Any]):
    """Handle PR creation requests with enhanced repository management and code context understanding."""
    # If no repository specified, use default
    repo_str = params.get("repo") or DEFAULT_REPO
    
    # Send initial status message
    status_msg = cg.slack.client.chat_postMessage(
        channel=event.channel,
        text=f"🔍 Creating PR for repository `{repo_str}`...",
        thread_ts=event.ts
    )
    
    try:
        # Create a unique branch name
        branch_name = f"coder-pr-{uuid.uuid4().hex[:8]}"  # Updated prefix from codegen to coder
        
        # Use the repo manager to create a branch
        if not repo_manager.create_branch(repo_str, branch_name):
            raise Exception(f"Failed to create branch {branch_name}")
        
        # Update status message
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=f"🔍 Created branch `{branch_name}`. Analyzing repository `{repo_str}`...",
            thread_ts=event.ts
        )
        
        # Initialize codebase
        codebase = repo_manager.get_codebase(repo_str)
        
        # Create task description for planning agent
        task_description = f"""
        Create a pull request for the repository {repo_str} with the following details:
        
        Branch name: {branch_name}
        Title: {params.get("title") or "Improvements by Coder"}
        Description: {params.get("description") or "Improvements based on code analysis"}
        Files to focus on: {', '.join(params.get("files", [])) if params.get("files") else "Identify key files that need improvement"}
        """
        
        # Use planning agent for better PR implementation
        agent = create_planning_code_agent(codebase, task_description)
        
        # Run the agent with enhanced context understanding
        response = agent.execute_task()
        
        # Extract PR URL if created
        import re
        url_match = re.search(r'https://github.com/[^/]+/[^/]+/pull/[0-9]+', response)
        pr_url = url_match.group(0) if url_match else None
        
        # If PR URL not found in response, try to create PR manually
        if not pr_url:
            # Commit changes
            if not repo_manager.commit_changes(repo_str, f"Changes by Coder: {params.get('title') or 'Improvements'}"):
                raise Exception("Failed to commit changes")
            
            # Push branch
            if not repo_manager.push_branch(repo_str, branch_name):
                raise Exception(f"Failed to push branch {branch_name}")
            
            # Create PR
            pr_number = repo_manager.create_pr(
                repo_str,
                params.get("title") or "Improvements by Coder",
                params.get("description") or "Improvements based on code analysis",
                branch_name
            )
            
            if pr_number:
                pr_url = f"https://github.com/{repo_str}/pull/{pr_number}"
        
        # Format the response
        if pr_url:
            formatted_response = f"🎉 *PR Created Successfully!*\n\n<{pr_url}|View PR on GitHub>\n\n{response}"
        else:
            formatted_response = f"⚠️ *PR Creation Attempted*\n\n{response}\n\n_Note: Could not extract PR URL. Please check if PR was created successfully._"
        
        # Update the status message with the result
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=formatted_response,
            thread_ts=event.ts
        )
    
    except Exception as e:
        # Handle errors
        logger.exception(f"Error in PR creation: {e}")
        error_message = f"❌ *Error creating PR*\n\n```\n{str(e)}\n```\n\nPlease try again or contact support."
        
        # Update the status message with the error
        cg.slack.client.chat_update(
            channel=event.channel,
            ts=status_msg['ts'],
            text=error_message,
            thread_ts=event.ts
        )
