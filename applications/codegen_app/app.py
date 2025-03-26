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
