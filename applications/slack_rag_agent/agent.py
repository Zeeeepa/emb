"""Enhanced Slack RAG Agent for Codebase Q&A with comprehensive context handling."""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Set, Optional

from codegen import Codebase
from codegen.extensions import FileIndex, CodeIndex
from AgentGen.agents.base import BaseAgent
from AgentGen.extensions.langchain.tools import (
    ViewFileTool,
    SearchTool,
    SemanticSearchTool,
    RevealSymbolTool
)

logger = logging.getLogger(__name__)

class SlackRAGAgent(BaseAgent):
    """
    A RAG-powered agent for answering questions about codebases via Slack.
    Combines file and code indices for comprehensive context retrieval.
    """
    
    def __init__(self, repo_name: str, cache_dir: str = ".cache"):
        """
        Initialize the SlackRAGAgent.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            cache_dir: Directory to store cache files
        """
        super().__init__()
        self.repo_name = repo_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize codebase
        self.codebase = Codebase.from_repo(repo_name)

        # Initialize both file and code indices
        self.file_index = self._initialize_file_index()
        self.code_index = self._initialize_code_index()

        # Add conversation history tracking
        self.history_path = self.cache_dir / "conversation_history.jsonl"

        # Initialize tools
        self.tools = [
            ViewFileTool(self.codebase),
            SearchTool(self.codebase),
            SemanticSearchTool(self.codebase),
            RevealSymbolTool(self.codebase)
        ]

    def _initialize_file_index(self) -> FileIndex:
        """Initialize or load cached file index."""
        index = FileIndex(self.codebase)
        index_path = self.cache_dir / f"{self.repo_name.replace('/', '_')}_file_index.pkl"

        if index_path.exists():
            try:
                index.load(str(index_path))
                logger.info("Loaded cached file index")
                return index
            except Exception as e:
                logger.warning(f"Failed to load cached file index: {e}")

        logger.info("Creating new file index")
        index.create()
        index.save(str(index_path))
        return index

    def _initialize_code_index(self) -> CodeIndex:
        """Initialize or load cached code index."""
        index = CodeIndex(self.codebase)
        index_path = self.cache_dir / f"{self.repo_name.replace('/', '_')}_code_index.pkl"

        if index_path.exists():
            try:
                index.load(str(index_path))
                logger.info("Loaded cached code index")
                return index
            except Exception as e:
                logger.warning(f"Failed to load cached code index: {e}")

        logger.info("Creating new code index")
        index.create()
        index.save(str(index_path))
        return index

    def _log_conversation(self, channel: str, query: str, answer: str):
        """Log conversation for analysis and improvement."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "channel": channel,
            "query": query,
            "answer": answer
        }
        with open(self.history_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def refresh_index(self):
        """Refresh the vector index with latest code."""
        self.codebase = Codebase.from_repo(self.repo_name)
        self.file_index = FileIndex(self.codebase)
        self.file_index.create()
        self.file_index.save(str(self.cache_dir / f"{self.repo_name.replace('/', '_')}_file_index.pkl"))

        self.code_index = CodeIndex(self.codebase)
        self.code_index.create()
        self.code_index.save(str(self.cache_dir / f"{self.repo_name.replace('/', '_')}_code_index.pkl"))

    def format_context(self, results):
        """Format search results into a readable context string."""
        context = []
        for filepath, score in results:
            try:
                file = self.codebase.get_file(filepath)
                if file:
                    context.append({
                        "filepath": filepath,
                        "snippet": file.content[:1500],  # Increased context window
                        "score": f"{score:.3f}"
                    })
            except Exception as e:
                logger.error(f"Error reading file {filepath}: {e}")

        return "\n\n".join([
            f"File: {c['filepath']}\nRelevance: {c['score']}\n```\n{c['snippet']}\n```"
            for c in context
        ])

    async def answer_question(self, query: str, channel_id: str = None) -> str:
        """
        Answer a question about the codebase using RAG.
        
        Args:
            query: The question to answer
            channel_id: Optional Slack channel ID for logging
            
        Returns:
            Formatted answer to the question
        """
        # Get relevant context using both indices
        file_results = self.file_index.similarity_search(query, k=3)
        code_results = self.code_index.similarity_search(query, k=3)

        # Combine and deduplicate results
        all_results = []
        seen_files = set()

        for filepath, score in file_results:
            if filepath not in seen_files:
                all_results.append((filepath, score, "file"))
                seen_files.add(filepath)

        for filepath, score in code_results:
            if filepath not in seen_files:
                all_results.append((filepath, score, "code"))
                seen_files.add(filepath)

        # Sort by score
        all_results.sort(key=lambda x: x[1], reverse=True)

        # Format context
        context = []
        for filepath, score, index_type in all_results[:5]:  # Take top 5 unique results
            try:
                file = self.codebase.get_file(filepath)
                if file:
                    context.append({
                        "filepath": filepath,
                        "snippet": file.content[:1500],
                        "score": f"{score:.3f}",
                        "type": index_type
                    })
            except Exception as e:
                logger.error(f"Error reading file {filepath}: {e}")

        # Format context string
        context_str = "\n\n".join([
            f"File: {c['filepath']}\nRelevance: {c['score']} ({c['type']})\n```\n{c['snippet']}\n```"
            for c in context
        ])

        # Enhanced prompt with better context handling
        prompt = f"""You are an expert code assistant analyzing the following codebase.
Given the context and question, provide a detailed technical answer.

Question: {query}

Relevant Code Context:
{context_str}

Additional Instructions:
- Focus on technical accuracy and implementation details
- Include relevant code snippets when helpful
- Explain relationships between different code components
- Highlight any important patterns or architectural decisions
- If context is insufficient, explain what additional information would be helpful

Answer:"""

        # Get response from OpenAI
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert code assistant with deep knowledge of software architecture and best practices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        answer = response.choices[0].message.content
        
        # Log the conversation if channel_id is provided
        if channel_id:
            self._log_conversation(channel_id, query, answer)
            
        return answer