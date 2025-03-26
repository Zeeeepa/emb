"""
Three-Platform Integration System - Main Application

This application integrates three platforms:
1. Linear - Planning and project management
2. Slack - Communication and code generation requests
3. GitHub - Code repository and PR management

It ties together the three main components:
1. Planning Agent - Manages Linear plans, evaluates progress, and determines next steps
2. Code Generation Agent - Receives requests via Slack and generates code/PRs
3. Code Analysis Agent - Analyzes PRs, provides feedback, and handles merging
"""

import logging
import os
from typing import Dict, Any

import modal
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from planning_agent import planning_agent, handle_pr_merged_endpoint, force_planning_cycle
from code_generation_agent import code_generation_agent, handle_slack_message
from code_analysis_agent import code_analysis_agent, handle_pr_opened_endpoint, handle_pr_closed_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Create the base image with dependencies
base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install(
        "codegen>=0.6.1",
        "openai>=1.1.0",
        "anthropic>=0.5.0",
        "fastapi[standard]",
        "slack_sdk",
        "pygithub",
        "linear-sdk",
        "httpx",
    )
)

# Create the app
app = modal.App("three-platform-integration", image=base_image)

# Create the FastAPI app
fastapi_app = FastAPI(title="Three-Platform Integration System")

@fastapi_app.post("/github/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events."""
    logger.info("Received GitHub webhook")
    
    # Parse the event
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "")
    
    logger.info(f"GitHub event type: {event_type}")
    
    if event_type == "pull_request":
        action = payload.get("action", "")
        logger.info(f"Pull request action: {action}")
        
        if action == "opened" or action == "reopened":
            # Handle PR opened event
            return await handle_pr_opened_endpoint(payload, background_tasks)
        elif action == "closed":
            # Handle PR closed event
            return await handle_pr_closed_endpoint(payload, background_tasks)
    
    return {"status": "ignored", "event_type": event_type}

@fastapi_app.post("/slack/webhook")
async def slack_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Slack webhook events."""
    logger.info("Received Slack webhook")
    
    # Parse the event
    payload = await request.json()
    
    # Verify Slack request (in a real implementation)
    # ...
    
    # Handle different event types
    event_type = payload.get("type", "")
    
    if event_type == "url_verification":
        # Handle Slack URL verification challenge
        return {"challenge": payload.get("challenge", "")}
    
    if event_type == "event_callback":
        event = payload.get("event", {})
        if event.get("type") == "app_mention":
            # Handle app mention event
            return await handle_slack_message(event, background_tasks)
    
    return {"status": "ignored", "event_type": event_type}

@fastapi_app.post("/linear/webhook")
async def linear_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Linear webhook events."""
    logger.info("Received Linear webhook")
    
    # Parse the event
    payload = await request.json()
    
    # Handle different event types
    action = payload.get("action", "")
    data = payload.get("data", {})
    
    logger.info(f"Linear action: {action}")
    
    if action == "update" and data.get("state"):
        # If an issue was completed, run a planning cycle
        state_name = data.get("state", {}).get("name", "").lower()
        if state_name == "done" or state_name == "completed":
            background_tasks.add_task(force_planning_cycle)
            return {"status": "planning_cycle_triggered"}
    
    return {"status": "ignored", "action": action}

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.function(secrets=[modal.Secret.from_dotenv()])
@modal.asgi_app()
def serve_app():
    """Serve the FastAPI app."""
    logger.info("Starting Three-Platform Integration System")
    return fastapi_app

# Expose the individual agent endpoints
@app.function(secrets=[modal.Secret.from_dotenv()])
async def analyze_pr(repo_str: str, pr_number: int) -> Dict[str, Any]:
    """Analyze a PR."""
    from code_analysis_agent import analyze_pr_endpoint
    return await analyze_pr_endpoint(repo_str, pr_number)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def merge_pr(repo_str: str, pr_number: int) -> Dict[str, Any]:
    """Merge a PR."""
    from code_analysis_agent import merge_pr_endpoint
    return await merge_pr_endpoint(repo_str, pr_number)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def get_next_issue(team_id: str = None) -> Dict[str, Any]:
    """Get the next issue to implement."""
    from planning_agent import get_next_issue_endpoint
    return await get_next_issue_endpoint(team_id)

@app.function(secrets=[modal.Secret.from_dotenv()])
async def run_planning_cycle(force: bool = False) -> Dict[str, Any]:
    """Run a planning cycle."""
    from planning_agent import force_planning_cycle
    return await force_planning_cycle()

if __name__ == "__main__":
    # For local testing
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)