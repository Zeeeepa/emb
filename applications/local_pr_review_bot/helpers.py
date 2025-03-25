from github import Github
import logging
import os
from typing import Dict, Any, Optional

from codegen import Codebase
from codegen.configs.models.secrets import SecretsConfig
from agentgen import CodeAgent
from agentgen.extensions.langchain.tools import (
    # Github
    GithubViewPRTool,
    GithubCreatePRCommentTool,
    GithubCreatePRReviewCommentTool,
)

from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def remove_bot_comments(repo_owner: str, repo_name: str, pr_number: int) -> None:
    """Remove all comments made by the bot on a PR."""
    g = Github(Config.GITHUB_TOKEN)
    logger.info(f"Removing bot comments from {repo_owner}/{repo_name} PR #{pr_number}")
    
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    pr = repo.get_pull(pr_number)
    
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

def send_slack_notification(message: str) -> None:
    """Send a notification to Slack if configured."""
    if Config.SLACK_BOT_TOKEN and Config.SLACK_NOTIFICATION_CHANNEL:
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=Config.SLACK_BOT_TOKEN)
            client.chat_postMessage(
                channel=Config.SLACK_NOTIFICATION_CHANNEL,
                text=message
            )
            logger.info(f"Sent Slack notification: {message}")
        except ImportError:
            logger.warning("slack_sdk not installed. Skipping Slack notification.")
        except SlackApiError as e:
            logger.error(f"Error sending Slack notification: {e}")
    else:
        logger.debug("Slack not configured. Skipping notification.")

def pr_review_agent(repo_owner: str, repo_name: str, pr_number: int, pr_url: str) -> None:
    """Run the PR review agent on a PR."""
    # Initialize the codebase
    repo_str = f"{repo_owner}/{repo_name}"
    logger.info(f"Initializing codebase for {repo_str}")
    
    codebase = Codebase.from_repo(
        repo_str, 
        language="python",  # TODO: Make this configurable or auto-detect
        secrets=SecretsConfig(github_token=Config.GITHUB_TOKEN)
    )
    
    # Create an initial comment to indicate the review is starting
    review_attention_message = "analyzer is starting to review the PR please wait..."
    comment = codebase._op.create_pr_comment(pr_number, review_attention_message)
    
    # Define tools for the agent
    pr_tools = [
        GithubViewPRTool(codebase),
        GithubCreatePRCommentTool(codebase),
        GithubCreatePRReviewCommentTool(codebase),
    ]
    
    # Create the agent with the defined tools
    agent = CodeAgent(codebase=codebase, tools=pr_tools)
    
    # Using a prompt from the original implementation
    prompt = f"""
Hey CodegenBot!

Here's a SWE task for you. Please Review this pull request!
{pr_url}
Do not terminate until have reviewed the pull request and are satisfied with your review.

Review this Pull request like the señor ingenier you are
be explicit about the changes, produce a short summary, and point out possible improvements where pressent dont be self congratulatory stick to the facts
use the tools at your disposal to create propper pr reviews include code snippets if needed, and suggest improvements if feel its necesary
"""
    
    # Run the agent
    logger.info(f"Starting PR review for {repo_str} PR #{pr_number}")
    agent.run(prompt)
    
    # Delete the initial comment
    comment.delete()
    
    # Send a Slack notification if configured
    send_slack_notification(f"Completed PR review for {repo_str} PR #{pr_number}")

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the GitHub webhook signature."""
    import hmac
    import hashlib
    
    if not signature or not secret:
        return False
        
    # The signature comes in as "sha1=<signature>"
    signature_parts = signature.split('=', 1)
    if len(signature_parts) != 2:
        return False
        
    algorithm, signature = signature_parts
    
    if algorithm != 'sha1':
        return False
        
    # Create the expected signature
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha1)
    expected_signature = mac.hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(signature, expected_signature)

def parse_pr_event(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse a GitHub webhook payload for PR events."""
    try:
        # Check if this is a PR event
        if payload.get('pull_request') is None:
            logger.debug("Not a pull request event")
            return None
            
        # Extract the relevant information
        action = payload.get('action')
        if not action:
            logger.debug("No action in payload")
            return None
            
        # For labeled events, check if it's our trigger label
        if action == 'labeled':
            label_name = payload.get('label', {}).get('name')
            if label_name != Config.TRIGGER_LABEL:
                logger.debug(f"Label {label_name} is not the trigger label {Config.TRIGGER_LABEL}")
                return None
                
        # For unlabeled events, check if it's our trigger label
        elif action == 'unlabeled':
            label_name = payload.get('label', {}).get('name')
            if label_name != Config.TRIGGER_LABEL:
                logger.debug(f"Unlabeled {label_name} is not the trigger label {Config.TRIGGER_LABEL}")
                return None
        else:
            logger.debug(f"Action {action} is not supported")
            return None
            
        # Extract repository information
        repo = payload.get('repository', {})
        repo_owner = repo.get('owner', {}).get('login')
        repo_name = repo.get('name')
        
        # Extract PR information
        pr = payload.get('pull_request', {})
        pr_number = pr.get('number')
        pr_url = pr.get('html_url')
        
        if not all([repo_owner, repo_name, pr_number, pr_url]):
            logger.warning("Missing required PR information")
            return None
            
        return {
            'action': action,
            'repo_owner': repo_owner,
            'repo_name': repo_name,
            'pr_number': pr_number,
            'pr_url': pr_url,
        }
    except Exception as e:
        logger.error(f"Error parsing PR event: {e}")
        return None