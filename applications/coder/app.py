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
from agentgen import (
    CodeAgent, 
    ChatAgent, 
    create_codebase_agent, 
    create_chat_agent, 
    create_codebase_inspector_agent, 
    create_agent_with_tools
)
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
REPO_CACHE_DIR = os.getenv("REPO_CACHE_DIR", "/tmp/coder_repos")

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
    CODE_EXPLANATION = "code_explanation"
    REFACTOR_CODE = "refactor_code"
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
    
    # Code explanation intent - new intent
    if any(phrase in text_lower for phrase in [
        "explain code", "explain this", "how does this work", "what does this do",
        "understand this code", "clarify this", "help me understand", "code walkthrough"
    ]):
        # Extract file paths or code snippets
        file_path_match = re.search(r'file[:\s]+([^\n]+)', text, re.IGNORECASE)
        if file_path_match:
            params["file_path"] = file_path_match.group(1).strip()
        return UserIntent.CODE_EXPLANATION, params
    
    # Code refactoring intent - new intent
    if any(phrase in text_lower for phrase in [
        "refactor", "improve code", "clean up code", "optimize code", "restructure code",
        "make code better", "enhance code", "simplify code", "modernize code"
    ]):
        # Extract file paths
        file_path_match = re.search(r'file[:\s]+([^\n]+)', text, re.IGNORECASE)
        if file_path_match:
            params["file_path"] = file_path_match.group(1).strip()
        return UserIntent.REFACTOR_CODE, params
    
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