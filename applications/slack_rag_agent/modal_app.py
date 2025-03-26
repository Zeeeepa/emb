"""Modal app for deploying the SlackRAGAgent as a serverless Slack bot."""

import os
import logging
from typing import Optional

import modal
from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

from applications.slack_rag_agent.agent import SlackRAGAgent
from applications.slack_rag_agent.multi_agent import MultiAgentCoordinator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create image with dependencies
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .pip_install(
        "slack-bolt>=1.18.0",
        "codegen>=0.6.1",
        "openai>=1.1.0",
        "langchain>=0.1.0",
        "chromadb>=0.4.0"
    )
)

# Modal app setup
app = modal.App("slack-rag-agent")
stub = modal.Stub("slack-rag-agent")

@stub.function(
    image=image,
    secrets=[modal.Secret.from_name("slack-secrets"), modal.Secret.from_name("openai-api-key")],
    timeout=600,
    concurrency_limit=10
)
@modal.asgi_app()
def fastapi_app():
    """Create and configure the FastAPI app with Slack integration."""
    web_app = FastAPI()

    # Initialize Slack
    slack_app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        signing_secret=os.environ["SLACK_SIGNING_SECRET"]
    )
    handler = SlackRequestHandler(slack_app)

    # Get repository name from environment or use default
    repo_name = os.environ.get("DEFAULT_REPO", "Zeeeepa/emb")
    
    # Initialize agents
    rag_agent = SlackRAGAgent(repo_name)
    
    # Initialize multi-agent coordinator
    coordinator = MultiAgentCoordinator(repo_name)

    @slack_app.event("app_mention")
    async def handle_mention(event, say):
        """Handle mentions of the bot in Slack."""
        try:
            # Extract query
            text = event.get("text", "")
            # Find the position after the mention
            mention_end = text.find(">")
            if mention_end == -1:
                say(
                    channel=event["channel"],
                    thread_ts=event.get("thread_ts", event["ts"]),
                    text="I couldn't parse your message. Please mention me followed by a question."
                )
                return
                
            query = text[mention_end + 1:].strip()
            if not query:
                say(
                    channel=event["channel"],
                    thread_ts=event.get("thread_ts", event["ts"]),
                    text="Please ask a question about the codebase!"
                )
                return

            # Add thinking indicator
            slack_app.client.reactions_add(
                channel=event["channel"],
                timestamp=event["ts"],
                name="thinking_face"
            )

            # Check if this is a command to switch repositories
            if query.startswith("use repo "):
                new_repo = query[9:].strip()
                try:
                    # Update the agents with the new repository
                    nonlocal rag_agent, coordinator
                    rag_agent = SlackRAGAgent(new_repo)
                    coordinator = MultiAgentCoordinator(new_repo)
                    
                    say(
                        channel=event["channel"],
                        thread_ts=event.get("thread_ts", event["ts"]),
                        text=f"✅ Switched to repository: `{new_repo}`"
                    )
                except Exception as e:
                    say(
                        channel=event["channel"],
                        thread_ts=event.get("thread_ts", event["ts"]),
                        text=f"❌ Failed to switch to repository: `{new_repo}`\nError: {str(e)}"
                    )
                
                # Remove thinking indicator
                slack_app.client.reactions_remove(
                    channel=event["channel"],
                    timestamp=event["ts"],
                    name="thinking_face"
                )
                return

            # Check if this is a command to refresh the index
            if query.lower() in ["refresh index", "update index", "rebuild index"]:
                try:
                    await rag_agent.refresh_index()
                    say(
                        channel=event["channel"],
                        thread_ts=event.get("thread_ts", event["ts"]),
                        text="✅ Index refreshed successfully!"
                    )
                except Exception as e:
                    say(
                        channel=event["channel"],
                        thread_ts=event.get("thread_ts", event["ts"]),
                        text=f"❌ Failed to refresh index: {str(e)}"
                    )
                
                # Remove thinking indicator
                slack_app.client.reactions_remove(
                    channel=event["channel"],
                    timestamp=event["ts"],
                    name="thinking_face"
                )
                return

            # Check if this is a request for multi-agent processing
            use_multi_agent = "deep" in query.lower() or "comprehensive" in query.lower() or "research" in query.lower()
            
            # Get answer using the appropriate agent
            if use_multi_agent:
                # Use the multi-agent coordinator for complex queries
                answer = await coordinator.process_query(query, event["channel"])
                source_info = "\n\n_This answer was generated using the multi-agent research system, combining code analysis with web search._"
            else:
                # Use the RAG agent for standard code questions
                answer = await rag_agent.answer_question(query, event["channel"])
                source_info = "\n\n_This answer was generated using the codebase RAG system._"

            # Format and send response
            full_answer = f"{answer}{source_info}"
            
            # Split long messages if needed (Slack has a 3000 character limit)
            if len(full_answer) > 3000:
                chunks = [full_answer[i:i+3000] for i in range(0, len(full_answer), 3000)]
                for i, chunk in enumerate(chunks):
                    prefix = "..." if i > 0 else ""
                    suffix = "..." if i < len(chunks) - 1 else ""
                    say(
                        channel=event["channel"],
                        thread_ts=event.get("thread_ts", event["ts"]),
                        text=f"{prefix}{chunk}{suffix}"
                    )
            else:
                say(
                    channel=event["channel"],
                    thread_ts=event.get("thread_ts", event["ts"]),
                    text=full_answer
                )

        except Exception as e:
            logger.exception("Error processing Slack message")
            say(
                channel=event["channel"],
                thread_ts=event.get("thread_ts", event["ts"]),
                text=f"❌ Error: {str(e)}"
            )
        finally:
            # Always remove the thinking indicator
            try:
                slack_app.client.reactions_remove(
                    channel=event["channel"],
                    timestamp=event["ts"],
                    name="thinking_face"
                )
            except Exception:
                pass

    @web_app.post("/slack/events")
    async def endpoint(request: Request):
        """Handle Slack events."""
        return await handler.handle(request)

    @web_app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    return web_app