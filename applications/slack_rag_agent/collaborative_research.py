"""Collaborative research session handler for Slack.

This module implements a collaborative research session where multiple users
can work together on a research question, contributing insights and feedback.
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Set, Optional
from pathlib import Path
from datetime import datetime
import uuid

from applications.slack_rag_agent.enhanced_research_assistant import EnhancedResearchAssistant

logger = logging.getLogger(__name__)

class CollaborativeResearchSession:
    """
    Manages a collaborative research session where multiple users can
    contribute to a research question.
    """
    
    def __init__(self, session_id: str, repo_name: str, cache_dir: str = ".cache"):
        """
        Initialize a collaborative research session.
        
        Args:
            session_id: Unique identifier for the session
            repo_name: GitHub repository name (format: "owner/repo")
            cache_dir: Directory to store cache files
        """
        self.session_id = session_id
        self.repo_name = repo_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create sessions directory
        self.sessions_dir = self.cache_dir / "collaborative_sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Initialize session data
        self.session_path = self.sessions_dir / f"{session_id}.json"
        
        if self.session_path.exists():
            with open(self.session_path, "r") as f:
                self.session_data = json.load(f)
        else:
            self.session_data = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "repo_name": repo_name,
                "main_question": "",
                "participants": [],
                "contributions": [],
                "research_plan": {},
                "final_answer": "",
                "status": "created"  # created, active, completed
            }
            self._save_session()
        
        # Initialize research assistant
        self.research_assistant = EnhancedResearchAssistant(repo_name, cache_dir)
    
    def _save_session(self):
        """Save session data to disk."""
        self.session_data["updated_at"] = datetime.utcnow().isoformat()
        with open(self.session_path, "w") as f:
            json.dump(self.session_data, f, indent=2)
    
    async def start_session(self, main_question: str, creator_id: str) -> str:
        """
        Start a new collaborative research session.
        
        Args:
            main_question: The main research question
            creator_id: Slack user ID of the session creator
            
        Returns:
            Session information message
        """
        self.session_data["main_question"] = main_question
        self.session_data["status"] = "active"
        
        # Add creator as first participant
        if creator_id not in self.session_data["participants"]:
            self.session_data["participants"].append(creator_id)
        
        # Create initial research plan
        plan_summary, sub_questions = await self.research_assistant._create_research_plan(main_question)
        
        self.session_data["research_plan"] = {
            "summary": plan_summary,
            "sub_questions": sub_questions
        }
        
        self._save_session()
        
        # Format sub-questions for display
        formatted_questions = "\n".join([
            f"{i+1}. {sq['question']} (Type: {sq['type']}, Priority: {sq.get('priority', 'N/A')})"
            for i, sq in enumerate(sub_questions)
        ])
        
        return f"""Collaborative research session started!

Session ID: {self.session_id}
Main Question: {main_question}

Research Plan:
{plan_summary}

Sub-questions:
{formatted_questions}

To contribute to this session, use the command:
`@bot contribute to session {self.session_id} [your insights]`

To view the current status:
`@bot session status {self.session_id}`

To finalize the research:
`@bot finalize session {self.session_id}`
"""
    
    async def add_contribution(self, user_id: str, contribution: str) -> str:
        """
        Add a contribution to the research session.
        
        Args:
            user_id: Slack user ID of the contributor
            contribution: The contribution text
            
        Returns:
            Confirmation message
        """
        if self.session_data["status"] == "completed":
            return f"This research session has already been completed. You cannot add new contributions."
        
        # Add user to participants if not already present
        if user_id not in self.session_data["participants"]:
            self.session_data["participants"].append(user_id)
        
        # Add contribution
        self.session_data["contributions"].append({
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "content": contribution
        })
        
        self._save_session()
        
        return f"Thank you for your contribution to the research session! Your insights have been added."
    
    def get_status(self) -> str:
        """
        Get the current status of the research session.
        
        Returns:
            Formatted status message
        """
        participants = len(self.session_data["participants"])
        contributions = len(self.session_data["contributions"])
        
        status = f"""Research Session Status:

Session ID: {self.session_id}
Main Question: {self.session_data["main_question"]}
Status: {self.session_data["status"].capitalize()}
Participants: {participants}
Contributions: {contributions}
"""
        
        if self.session_data["status"] == "completed" and self.session_data["final_answer"]:
            status += f"\nThis session has been completed. Use `@bot show session results {self.session_id}` to see the final answer."
        
        return status
    
    async def finalize_session(self) -> str:
        """
        Finalize the research session and generate a comprehensive answer.
        
        Returns:
            Confirmation message
        """
        if self.session_data["status"] == "completed":
            return f"This research session has already been completed."
        
        if not self.session_data["contributions"]:
            return f"Cannot finalize session without any contributions. Please add some insights first."
        
        # Combine all contributions
        all_contributions = "\n\n".join([
            f"Contribution {i+1}:\n{c['content']}"
            for i, c in enumerate(self.session_data["contributions"])
        ])
        
        # Create a prompt that includes the research plan and all contributions
        prompt = f"""You are synthesizing the results of a collaborative research session.

Main Research Question: {self.session_data["main_question"]}

Research Plan:
{self.session_data["research_plan"]["summary"]}

Participant Contributions:
{all_contributions}

Based on all the contributions and the research plan, provide a comprehensive, well-structured answer to the main research question. Incorporate insights from all contributions and ensure the answer is technically accurate and practical.
"""
        
        # Generate final answer
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert research synthesizer with deep knowledge of software engineering and programming."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        final_answer = response.choices[0].message.content
        
        # Update session data
        self.session_data["final_answer"] = final_answer
        self.session_data["status"] = "completed"
        self._save_session()
        
        return f"Research session has been finalized! Use `@bot show session results {self.session_id}` to see the comprehensive answer."
    
    def get_results(self) -> str:
        """
        Get the final results of the research session.
        
        Returns:
            Final research answer or status message
        """
        if self.session_data["status"] != "completed":
            return f"This research session has not been finalized yet. Use `@bot finalize session {self.session_id}` to generate the final answer."
        
        return f"""Research Results for Session {self.session_id}:

Question: {self.session_data["main_question"]}

{self.session_data["final_answer"]}

This answer was synthesized from {len(self.session_data["contributions"])} contributions by {len(self.session_data["participants"])} participants.
"""

class CollaborativeResearchManager:
    """
    Manages all collaborative research sessions.
    """
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize the collaborative research manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create sessions directory
        self.sessions_dir = self.cache_dir / "collaborative_sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Load existing sessions
        self.active_sessions = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load existing sessions from disk."""
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    session_data = json.load(f)
                    
                session_id = session_data["session_id"]
                repo_name = session_data["repo_name"]
                
                # Only load active sessions
                if session_data["status"] != "completed":
                    self.active_sessions[session_id] = CollaborativeResearchSession(
                        session_id=session_id,
                        repo_name=repo_name,
                        cache_dir=str(self.cache_dir)
                    )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error loading session from {session_file}: {e}")
    
    def create_session(self, repo_name: str) -> str:
        """
        Create a new collaborative research session.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
        
        self.active_sessions[session_id] = CollaborativeResearchSession(
            session_id=session_id,
            repo_name=repo_name,
            cache_dir=str(self.cache_dir)
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[CollaborativeResearchSession]:
        """
        Get a collaborative research session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            CollaborativeResearchSession or None if not found
        """
        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Check if session file exists
        session_path = self.sessions_dir / f"{session_id}.json"
        if session_path.exists():
            try:
                session = CollaborativeResearchSession(
                    session_id=session_id,
                    repo_name="",  # Will be loaded from file
                    cache_dir=str(self.cache_dir)
                )
                
                # Add to active sessions if not completed
                if session.session_data["status"] != "completed":
                    self.active_sessions[session_id] = session
                
                return session
            except Exception as e:
                logger.error(f"Error loading session {session_id}: {e}")
        
        return None
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active research sessions.
        
        Returns:
            List of session information dictionaries
        """
        active_sessions = []
        
        for session_id, session in self.active_sessions.items():
            active_sessions.append({
                "session_id": session_id,
                "main_question": session.session_data["main_question"],
                "participants": len(session.session_data["participants"]),
                "contributions": len(session.session_data["contributions"]),
                "created_at": session.session_data["created_at"]
            })
        
        return active_sessions