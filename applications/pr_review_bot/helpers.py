from github import Github
from agentgen.extensions.github.types.events.pull_request import PullRequestUnlabeledEvent
from logging import getLogger

import os

from codegen import Codebase

from agentgen.extensions.github.types.events.pull_request import PullRequestLabeledEvent
from codegen.configs.models.secrets import SecretsConfig
from agentgen import CodeAgent

from agentgen.extensions.langchain.tools import (
    # Github
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
)

from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

# Get environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "")
TRIGGER_LABEL = os.getenv("TRIGGER_LABEL", "analyzer")

def remove_bot_comments(event: PullRequestUnlabeledEvent):
    """Remove all comments made by the bot on a PR."""
    g = Github(GITHUB_TOKEN)
    logger.info(f"Removing bot comments from {event.organization.login}/{event.repository.name} PR #{event.number}")
    
    repo = g.get_repo(f"{event.organization.login}/{event.repository.name}")
    pr = repo.get_pull(int(event.number))
    
    # Remove PR comments
    comments = pr.get_comments()
    if comments:
        for comment in comments:
            logger.info(f"Checking comment by {comment.user.login}")
            if comment.user.login == "analyzer":  # TODO: Make this configurable
                logger.info("Removing comment")
                comment.delete()
    
    # Remove PR reviews
    reviews = pr.get_reviews()
    if reviews:
        for review in reviews:
            logger.info(f"Checking review by {review.user.login}")
            if review.user.login == "analyzer":  # TODO: Make this configurable
                logger.info("Removing review")
                review.delete()
    
    # Remove issue comments
    issue_comments = pr.get_issue_comments()
    if issue_comments:
        for comment in issue_comments:
            logger.info(f"Checking issue comment by {comment.user.login}")
            if comment.user.login == "analyzer":  # TODO: Make this configurable
                logger.info("Removing comment")
                comment.delete()

def pr_review_agent(event: PullRequestLabeledEvent) -> None:
    """Run the PR review agent on a PR."""
    # Initialize the codebase
    repo_str = f"{event.organization.login}/{event.repository.name}"
    logger.info(f"Initializing codebase for {repo_str}")
    
    codebase = Codebase.from_repo(
        repo_str, 
        language="python",  # TODO: Make this configurable or auto-detect
        secrets=SecretsConfig(github_token=GITHUB_TOKEN)
    )
    
    # Create an initial comment to indicate the review is starting
    review_attention_message = "analyzer is starting to review the PR please wait..."
    comment = codebase._op.create_pr_comment(event.number, review_attention_message)
    
    # Define tools for the agent
    pr_tools = [
        GithubViewPRTool(codebase),
        GithubCreatePRCommentTool(codebase),
        GithubCreatePRReviewCommentTool(codebase),
    ]
    
    # Create the agent with the defined tools
    agent = CodeAgent(codebase=codebase, tools=pr_tools)
    
    # Using a prompt for PR review
    prompt = f"""
Hey CodegenBot!

Here's a SWE task for you. Please Review this pull request!
{event.pull_request.url}
Do not terminate until have reviewed the pull request and are satisfied with your review.

Review this Pull request like the señor ingenier you are
be explicit about the changes, produce a short summary, and point out possible improvements where pressent dont be self congratulatory stick to the facts
use the tools at your disposal to create propper pr reviews include code snippets if needed, and suggest improvements if feel its necesary
"""
    
    # Run the agent
    logger.info(f"Starting PR review for {repo_str} PR #{event.number}")
    agent.run(prompt)
    
    # Delete the initial comment
    comment.delete()
    
    # Send a Slack notification if configured
    if SLACK_NOTIFICATION_CHANNEL:
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=os.getenv("SLACK_BOT_TOKEN", ""))
            client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"Completed PR review for {repo_str} PR #{event.number}"
            )
            logger.info(f"Sent Slack notification: Completed PR review")
        except ImportError:
            logger.warning("slack_sdk not installed. Skipping Slack notification.")
        except SlackApiError as e:
            logger.error(f"Error sending Slack notification: {e}")
    else:
        logger.debug("Slack not configured. Skipping notification.")
