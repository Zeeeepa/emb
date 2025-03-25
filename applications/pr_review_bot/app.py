import logging
from logging import getLogger
import os
import modal
from agentgen.extensions.events.codegen_app import CodegenApp
from fastapi import Request
from agentgen.extensions.github.types.events.pull_request import PullRequestLabeledEvent, PullRequestUnlabeledEvent
from helpers import remove_bot_comments, pr_review_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)

# Load environment variables
REPO_URL = "https://github.com/codegen-sh/codegen-sdk.git"
COMMIT_ID = "20ba52b263ba8bab552b5fb6f68ca3667c0309fb"
TRIGGER_LABEL = os.getenv("TRIGGER_LABEL", "analyzer")
SLACK_NOTIFICATION_CHANNEL = os.getenv("SLACK_NOTIFICATION_CHANNEL", "C08K05KUL9G")

# Create the base image
base_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install(
        # =====[ Codegen ]=====
        f"git+{REPO_URL}@{COMMIT_ID}",
        # =====[ Rest ]=====
        "openai>=1.1.0",
        "anthropic>=0.5.0",
        "fastapi[standard]",
        "slack_sdk",
    )
)

# Create the app with the Modal API key from environment
app = CodegenApp(
    name="github-pr-review", 
    image=base_image, 
    modal_api_key=os.getenv("MODAL_API_KEY", "")
)

@app.github.event("pull_request:labeled")
def handle_labeled(event: PullRequestLabeledEvent):
    """Handle pull request labeled events."""
    logger.info("[PULL_REQUEST:LABELED] Received pull request labeled event")
    logger.info(f"PR #{event.number} labeled with: {event.label.name}")
    logger.info(f"PR title: {event.pull_request.title}")
    
    # Check if the label matches our trigger label
    if event.label.name == TRIGGER_LABEL:
        # Send a Slack notification if configured
        if app.slack.client and SLACK_NOTIFICATION_CHANNEL:
            app.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"PR #{event.number} labeled with: {event.label.name}, starting review",
            )

        logger.info(f"PR ID: {event.pull_request.id}")
        logger.info(f"PR title: {event.pull_request.title}")
        logger.info(f"PR number: {event.number}")
        
        # Run the PR review agent
        pr_review_agent(event)

@app.github.event("pull_request:unlabeled")
def handle_unlabeled(event: PullRequestUnlabeledEvent):
    """Handle pull request unlabeled events."""
    logger.info("[PULL_REQUEST:UNLABELED] Received pull request unlabeled event")
    logger.info(f"PR #{event.number} unlabeled with: {event.label.name}")
    
    # Check if the label matches our trigger label
    if event.label.name == TRIGGER_LABEL:
        # Remove bot comments
        remove_bot_comments(event)
        
        # Send a Slack notification if configured
        if app.slack.client and SLACK_NOTIFICATION_CHANNEL:
            app.slack.client.chat_postMessage(
                channel=SLACK_NOTIFICATION_CHANNEL,
                text=f"PR #{event.number} unlabeled with: {event.label.name}, removed review comments",
            )

@app.function(secrets=[modal.Secret.from_dotenv()])
@modal.web_endpoint(method="POST")
def entrypoint(event: dict, request: Request):
    """Entry point for GitHub webhook events."""
    logger.info("[OUTER] Received GitHub webhook")
    return app.github.handle(event, request)
