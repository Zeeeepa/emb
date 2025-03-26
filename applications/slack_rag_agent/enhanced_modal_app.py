"""Enhanced Modal app for deploying the advanced Slack RAG agent with research capabilities.

This module implements a Modal app that integrates:
1. Enhanced Research Assistant with academic search and personalization
2. Collaborative Research Sessions for team-based research
3. Code Visualization capabilities
4. Memory and personalization features
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
import asyncio

import modal
from fastapi import FastAPI, Request, BackgroundTasks
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

from applications.slack_rag_agent.agent import SlackRAGAgent
from applications.slack_rag_agent.enhanced_research_assistant import EnhancedResearchAssistant
from applications.slack_rag_agent.collaborative_research import CollaborativeResearchManager

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
        "chromadb>=0.4.0",
        "matplotlib>=3.7.0",
        "networkx>=3.0",
        "pygraphviz>=1.10",
        "plotly>=5.13.0"
    )
)

# Modal app setup
app = modal.App("enhanced-slack-rag-agent")
stub = modal.Stub("enhanced-slack-rag-agent")

# Command patterns
COMMAND_PATTERNS = {
    "research": re.compile(r"(?:research|investigate|analyze|study)\s+(.+)", re.IGNORECASE),
    "set_repo": re.compile(r"(?:use|switch to|set)\s+repo\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)", re.IGNORECASE),
    "refresh_index": re.compile(r"(?:refresh|update|rebuild)\s+index", re.IGNORECASE),
    "set_preference": re.compile(r"set\s+preference\s+([a-zA-Z_]+)\s+to\s+(.+)", re.IGNORECASE),
    "add_topic": re.compile(r"add\s+topic\s+(.+)", re.IGNORECASE),
    "start_session": re.compile(r"start\s+(?:collaborative\s+)?(?:research\s+)?session(?:\s+on)?\s+(.+)", re.IGNORECASE),
    "contribute": re.compile(r"contribute\s+to\s+session\s+([a-zA-Z0-9]+)\s+(.+)", re.IGNORECASE),
    "session_status": re.compile(r"session\s+status\s+([a-zA-Z0-9]+)", re.IGNORECASE),
    "finalize_session": re.compile(r"finalize\s+session\s+([a-zA-Z0-9]+)", re.IGNORECASE),
    "show_results": re.compile(r"show\s+session\s+results\s+([a-zA-Z0-9]+)", re.IGNORECASE),
    "list_sessions": re.compile(r"list\s+(?:active\s+)?sessions", re.IGNORECASE),
    "help": re.compile(r"(?:help|commands|usage)", re.IGNORECASE),
    "feedback": re.compile(r"feedback(?:\s+on)?\s+(.+?):\s+(.+)", re.IGNORECASE),
}

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
    research_assistant = EnhancedResearchAssistant(repo_name)
    
    # Initialize collaborative research manager
    collab_manager = CollaborativeResearchManager()
    
    # Store user-specific repository settings
    user_repos = {}
    
    def get_repo_for_user(user_id: str) -> str:
        """Get the repository name for a specific user."""
        return user_repos.get(user_id, repo_name)
    
    def set_repo_for_user(user_id: str, new_repo: str):
        """Set the repository name for a specific user."""
        user_repos[user_id] = new_repo
    
    async def process_command(text: str, user_id: str, channel_id: str, thread_ts: Optional[str] = None) -> str:
        """
        Process a command from the user.
        
        Args:
            text: The command text
            user_id: Slack user ID
            channel_id: Slack channel ID
            thread_ts: Optional thread timestamp
            
        Returns:
            Response message
        """
        # Check for research command
        research_match = COMMAND_PATTERNS["research"].match(text)
        if research_match:
            query = research_match.group(1).strip()
            user_repo = get_repo_for_user(user_id)
            
            # Create a research assistant with the user's repository
            user_research_assistant = EnhancedResearchAssistant(user_repo, user_id=user_id)
            
            # Perform research
            result = await user_research_assistant.research(query, channel_id)
            return result
        
        # Check for set repository command
        set_repo_match = COMMAND_PATTERNS["set_repo"].match(text)
        if set_repo_match:
            new_repo = set_repo_match.group(1).strip()
            set_repo_for_user(user_id, new_repo)
            return f"✅ Switched to repository: `{new_repo}`"
        
        # Check for refresh index command
        refresh_match = COMMAND_PATTERNS["refresh_index"].match(text)
        if refresh_match:
            user_repo = get_repo_for_user(user_id)
            user_rag_agent = SlackRAGAgent(user_repo)
            await user_rag_agent.refresh_index()
            return "✅ Index refreshed successfully!"
        
        # Check for set preference command
        pref_match = COMMAND_PATTERNS["set_preference"].match(text)
        if pref_match:
            pref_name = pref_match.group(1).strip()
            pref_value = pref_match.group(2).strip()
            
            # Create a research assistant with the user's repository
            user_research_assistant = EnhancedResearchAssistant(get_repo_for_user(user_id), user_id=user_id)
            
            # Update preference
            try:
                if pref_name == "code_detail_level":
                    if pref_value not in ["low", "medium", "high"]:
                        return f"❌ Invalid value for code_detail_level. Must be one of: low, medium, high"
                elif pref_name == "include_academic_sources":
                    pref_value = pref_value.lower() in ["true", "yes", "1", "on"]
                elif pref_name == "visualization_enabled":
                    pref_value = pref_value.lower() in ["true", "yes", "1", "on"]
                
                result = await user_research_assistant.update_preferences(user_id, {pref_name: pref_value})
                return result
            except Exception as e:
                return f"❌ Error updating preference: {str(e)}"
        
        # Check for add topic command
        topic_match = COMMAND_PATTERNS["add_topic"].match(text)
        if topic_match:
            topic = topic_match.group(1).strip()
            
            # Create a research assistant with the user's repository
            user_research_assistant = EnhancedResearchAssistant(get_repo_for_user(user_id), user_id=user_id)
            
            # Add topic
            result = await user_research_assistant.add_topic_of_interest(user_id, topic)
            return result
        
        # Check for start collaborative session command
        start_session_match = COMMAND_PATTERNS["start_session"].match(text)
        if start_session_match:
            question = start_session_match.group(1).strip()
            
            # Create a new session
            session_id = collab_manager.create_session(get_repo_for_user(user_id))
            session = collab_manager.get_session(session_id)
            
            # Start the session
            result = await session.start_session(question, user_id)
            return result
        
        # Check for contribute to session command
        contribute_match = COMMAND_PATTERNS["contribute"].match(text)
        if contribute_match:
            session_id = contribute_match.group(1).strip()
            contribution = contribute_match.group(2).strip()
            
            # Get the session
            session = collab_manager.get_session(session_id)
            if not session:
                return f"❌ Session {session_id} not found."
            
            # Add contribution
            result = await session.add_contribution(user_id, contribution)
            return result
        
        # Check for session status command
        status_match = COMMAND_PATTERNS["session_status"].match(text)
        if status_match:
            session_id = status_match.group(1).strip()
            
            # Get the session
            session = collab_manager.get_session(session_id)
            if not session:
                return f"❌ Session {session_id} not found."
            
            # Get status
            return session.get_status()
        
        # Check for finalize session command
        finalize_match = COMMAND_PATTERNS["finalize_session"].match(text)
        if finalize_match:
            session_id = finalize_match.group(1).strip()
            
            # Get the session
            session = collab_manager.get_session(session_id)
            if not session:
                return f"❌ Session {session_id} not found."
            
            # Finalize session
            result = await session.finalize_session()
            return result
        
        # Check for show results command
        results_match = COMMAND_PATTERNS["show_results"].match(text)
        if results_match:
            session_id = results_match.group(1).strip()
            
            # Get the session
            session = collab_manager.get_session(session_id)
            if not session:
                return f"❌ Session {session_id} not found."
            
            # Get results
            return session.get_results()
        
        # Check for list sessions command
        list_match = COMMAND_PATTERNS["list_sessions"].match(text)
        if list_match:
            sessions = collab_manager.list_active_sessions()
            
            if not sessions:
                return "No active research sessions found."
            
            # Format sessions
            formatted_sessions = "\n".join([
                f"• Session {s['session_id']}: \"{s['main_question']}\" - {s['participants']} participants, {s['contributions']} contributions"
                for s in sessions
            ])
            
            return f"Active Research Sessions:\n\n{formatted_sessions}"
        
        # Check for feedback command
        feedback_match = COMMAND_PATTERNS["feedback"].match(text)
        if feedback_match:
            query = feedback_match.group(1).strip()
            feedback = feedback_match.group(2).strip()
            
            # Create a research assistant with the user's repository
            user_research_assistant = EnhancedResearchAssistant(get_repo_for_user(user_id), user_id=user_id)
            
            # Save feedback
            result = await user_research_assistant.save_feedback(user_id, query, feedback)
            return result
        
        # Check for help command
        help_match = COMMAND_PATTERNS["help"].match(text)
        if help_match:
            return """Available Commands:

Research:
• `research [question]` - Research a question using code analysis and web search
• `set repo [owner/repo]` - Switch to a different repository
• `refresh index` - Rebuild the indices for the current repository

Personalization:
• `set preference [name] to [value]` - Update your preferences
• `add topic [topic]` - Add a topic of interest to your profile
• `feedback on [query]: [feedback]` - Provide feedback on a research result

Collaborative Research:
• `start session on [question]` - Start a new collaborative research session
• `contribute to session [id] [insights]` - Add your insights to a session
• `session status [id]` - Check the status of a research session
• `finalize session [id]` - Generate a final answer for a session
• `show session results [id]` - View the results of a completed session
• `list sessions` - List all active research sessions

For complex research queries, include keywords like "research", "investigate", or "analyze" to trigger the enhanced research system.
"""
        
        # If no command matched, use the RAG agent to answer the question
        user_rag_agent = SlackRAGAgent(get_repo_for_user(user_id))
        return await user_rag_agent.answer_question(text, channel_id)

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
                    text="Please ask a question or provide a command!"
                )
                return

            # Add thinking indicator
            slack_app.client.reactions_add(
                channel=event["channel"],
                timestamp=event["ts"],
                name="thinking_face"
            )

            # Process the command
            response = await process_command(
                query, 
                event["user"], 
                event["channel"],
                event.get("thread_ts", event["ts"])
            )
            
            # Split long messages if needed (Slack has a 3000 character limit)
            if len(response) > 3000:
                chunks = [response[i:i+3000] for i in range(0, len(response), 3000)]
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
                    text=response
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