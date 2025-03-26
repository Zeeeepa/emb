import logging
import os
from typing import Optional

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
from agentgen.extensions.linear.types import LinearEvent
from agentgen.extensions.slack.types import SlackEvent
from agentgen.extensions.tools.github.create_pr_comment import create_pr_comment
from agentgen.extensions.langchain.tools import (
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
)
from fastapi import Request

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MODAL_API_KEY = os.getenv("MODAL_API_KEY", "")
TRIGGER_LABEL = os.getenv("TRIGGER_LABEL", "analyzer")
SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "")
DEFAULT_REPO = os.getenv("DEFAULT_REPO", "codegen-sh/Kevin-s-Adventure-Game")

########################################################################################################################
# EVENTS
########################################################################################################################

# Create the cg_app with Modal API key
cg = CodegenApp(
    name="codegen-app", 
    repo=DEFAULT_REPO,
    modal_api_key=MODAL_API_KEY
)

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

@cg.slack.event("app_mention")
async def handle_mention(event: SlackEvent):
    """Handle Slack app mention events."""
    logger.info("[APP_MENTION] Received app_mention event")
    logger.info(event)

    # Codebase
    logger.info("[CODEBASE] Initializing codebase")
    codebase = cg.get_codebase()

    # Code Agent
    logger.info("[CODE_AGENT] Initializing code agent")
    agent = CodeAgent(codebase=codebase)

    logger.info("[CODE_AGENT] Running code agent")
    response = agent.run(event.text)

    # Send response back to Slack
    cg.slack.client.chat_postMessage(channel=event.channel, text=response, thread_ts=event.ts)
    return {"message": "Mentioned", "received_text": event.text, "response": response}

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
        codebase = get_codebase_for_repo(repo_str)
        
        # Remove bot comments (similar to PR review bot)
        from github import Github
        g = Github(GITHUB_TOKEN)
        logger.info(f"Removing bot comments from {repo_str} PR #{event.number}")
        
        repo = g.get_repo(repo_str)
        pr = repo.get_pull(int(event.number))
        
        # Remove PR comments
        comments = pr.get_comments()
        if comments:
            for comment in comments:
                if comment.user.login == "codegen-app":  # Bot username
                    logger.info("Removing comment")
                    comment.delete()
        
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
def handle_issue(event: LinearEvent):
    """Handle Linear issue events."""
    logger.info(f"[LINEAR:ISSUE] Issue created: {event}")
    codebase = cg.get_codebase()
    
    # Send a Slack notification if configured
    if cg.slack.client and SLACK_NOTIFICATION_CHANNEL:
        cg.slack.client.chat_postMessage(
            channel=SLACK_NOTIFICATION_CHANNEL,
            text=f"New Linear issue created: {event.data.title}",
        )
    
    return {"message": "Linear Issue event handled", "title": event.data.title}

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
