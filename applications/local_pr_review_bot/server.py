import json
import logging
import os
import sys
import threading
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from helpers import parse_pr_event, pr_review_agent, remove_bot_comments, verify_webhook_signature

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Local PR Review Bot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint to check if the server is running."""
    return {"status": "ok", "message": "PR Review Bot is running"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

async def verify_github_webhook(request: Request) -> Dict[str, Any]:
    """Verify the GitHub webhook signature and parse the payload."""
    # Get the signature from the headers
    signature = request.headers.get("X-Hub-Signature")
    
    # Read the raw body
    body = await request.body()
    
    # Verify the signature if a webhook secret is configured
    if Config.WEBHOOK_SECRET:
        if not signature:
            logger.warning("Missing X-Hub-Signature header")
            raise HTTPException(status_code=401, detail="Missing signature header")
            
        if not verify_webhook_signature(body, signature, Config.WEBHOOK_SECRET):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse the JSON payload
    try:
        payload = json.loads(body)
        return payload
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

@app.post("/webhook")
async def github_webhook(background_tasks: BackgroundTasks, payload: Dict[str, Any] = Depends(verify_github_webhook)):
    """Handle GitHub webhook events."""
    logger.info("Received GitHub webhook")
    
    # Parse the PR event
    pr_event = parse_pr_event(payload)
    if not pr_event:
        logger.debug("Not a relevant PR event")
        return {"status": "ignored"}
    
    # Handle the PR event based on the action
    action = pr_event["action"]
    repo_owner = pr_event["repo_owner"]
    repo_name = pr_event["repo_name"]
    pr_number = pr_event["pr_number"]
    pr_url = pr_event["pr_url"]
    
    if action == "labeled":
        logger.info(f"PR #{pr_number} labeled with {Config.TRIGGER_LABEL}, starting review")
        # Run the PR review in the background
        background_tasks.add_task(
            pr_review_agent,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            pr_url=pr_url
        )
        return {"status": "processing", "message": f"Starting review of PR #{pr_number}"}
    
    elif action == "unlabeled":
        logger.info(f"PR #{pr_number} unlabeled with {Config.TRIGGER_LABEL}, removing comments")
        # Remove bot comments in the background
        background_tasks.add_task(
            remove_bot_comments,
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number
        )
        return {"status": "processing", "message": f"Removing comments from PR #{pr_number}"}
    
    return {"status": "ignored"}

def main():
    """Run the server."""
    # Validate configuration
    if not Config.validate():
        logger.error("Invalid configuration")
        sys.exit(1)
    
    # Log configuration
    logger.info(f"Starting PR Review Bot on {Config.HOST}:{Config.PORT}")
    logger.info(f"Trigger label: {Config.TRIGGER_LABEL}")
    
    # Run the server
    uvicorn.run(
        "server:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False
    )

if __name__ == "__main__":
    main()