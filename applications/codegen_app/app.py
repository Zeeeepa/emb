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