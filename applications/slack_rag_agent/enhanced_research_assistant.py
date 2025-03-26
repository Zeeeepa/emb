"""Enhanced Research Assistant with internet search and academic integration capabilities.

This module implements an advanced research assistant that combines:
1. Code analysis using Codegen's powerful tools
2. Web search for external information
3. Academic paper search and analysis
4. Memory and personalization features
5. Multi-modal support for code visualization
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Tuple, Set, Optional
from pathlib import Path
from datetime import datetime
import time
import hashlib

from openai import OpenAI
from codegen import Codebase
from codegen.extensions import FileIndex, CodeIndex
from AgentGen.agents.base import BaseAgent
from AgentGen.extensions.langchain.tools import (
    ViewFileTool,
    SearchTool,
    SemanticSearchTool,
    RevealSymbolTool
)

from applications.slack_rag_agent.agent import SlackRAGAgent
from applications.slack_rag_agent.web_search_agent import WebSearchAgent

logger = logging.getLogger(__name__)

class EnhancedResearchAssistant(BaseAgent):
    """
    Advanced research assistant that combines code analysis, web search,
    academic research, and personalized learning.
    """
    
    def __init__(self, repo_name: str, cache_dir: str = ".cache", user_id: Optional[str] = None):
        """
        Initialize the EnhancedResearchAssistant.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            cache_dir: Directory to store cache files
            user_id: Optional Slack user ID for personalization
        """
        super().__init__()
        self.repo_name = repo_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.user_id = user_id
        
        # Initialize specialized agents
        self.code_agent = SlackRAGAgent(repo_name, cache_dir)
        self.web_agent = WebSearchAgent(cache_dir)
        
        # Initialize OpenAI client
        self.client = OpenAI()
        
        # Create research results directory
        self.results_dir = self.cache_dir / "research_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Create user profiles directory for personalization
        self.profiles_dir = self.cache_dir / "user_profiles"
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Initialize user profile if provided
        if user_id:
            self.user_profile = self._load_or_create_user_profile(user_id)
        else:
            self.user_profile = None
        
        # Initialize rate limiting for API calls
        self.last_api_call = 0
        self.min_api_interval = 1.0  # seconds
        
        # Path for logging research activities
        self.log_path = self.cache_dir / "research_logs.jsonl"
    
    def _load_or_create_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Load existing user profile or create a new one."""
        profile_path = self.profiles_dir / f"{user_id}.json"
        
        if profile_path.exists():
            try:
                with open(profile_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Corrupted profile for user {user_id}, creating new one")
        
        # Create new profile
        profile = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "preferences": {
                "code_detail_level": "medium",  # low, medium, high
                "include_academic_sources": True,
                "preferred_languages": [],  # empty means all languages
                "visualization_enabled": True
            },
            "research_history": [],
            "topics_of_interest": [],
            "feedback": {}
        }
        
        # Save new profile
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        
        return profile
    
    def _update_user_profile(self, query: str, feedback: Optional[str] = None):
        """Update user profile with new research query and optional feedback."""
        if not self.user_profile:
            return
        
        # Update research history
        self.user_profile["research_history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "feedback": feedback
        })
        
        # Limit history size
        if len(self.user_profile["research_history"]) > 100:
            self.user_profile["research_history"] = self.user_profile["research_history"][-100:]
        
        # Update last modified time
        self.user_profile["updated_at"] = datetime.utcnow().isoformat()
        
        # Save updated profile
        profile_path = self.profiles_dir / f"{self.user_profile['user_id']}.json"
        with open(profile_path, "w") as f:
            json.dump(self.user_profile, f, indent=2)
    
    def _log_research(self, query: str, plan: str, results: Dict[str, Any], final_answer: str):
        """Log research activities for analysis and improvement."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "plan": plan,
            "results": results,
            "final_answer": final_answer
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def _cache_research_result(self, query: str, result: str):
        """Cache research results for future reference."""
        # Create a hash of the query for the filename
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_file = self.results_dir / f"{query_hash}.json"
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "result": result
        }
        
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _get_cached_result(self, query: str) -> Optional[str]:
        """Get cached research result if available and fresh."""
        # Create a hash of the query for the filename
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_file = self.results_dir / f"{query_hash}.json"
        
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                
                # Check if cache is fresh (less than 24 hours old)
                cache_time = datetime.fromisoformat(data["timestamp"])
                if (datetime.utcnow() - cache_time).total_seconds() < 86400:
                    return data["result"]
        
        return None
    
    async def _rate_limited_api_call(self, func, *args, **kwargs):
        """Perform rate-limited API calls to avoid hitting rate limits."""
        now = time.time()
        if now - self.last_api_call < self.min_api_interval:
            await asyncio.sleep(self.min_api_interval - (now - self.last_api_call))
        
        result = await func(*args, **kwargs)
        self.last_api_call = time.time()
        return result
    
    async def _create_research_plan(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Create a comprehensive research plan by breaking down the query into sub-questions.
        
        Args:
            query: The main research question
            
        Returns:
            Tuple of (plan_summary, sub_questions)
        """
        # Include user preferences if available
        user_context = ""
        if self.user_profile:
            interests = ", ".join(self.user_profile["topics_of_interest"]) if self.user_profile["topics_of_interest"] else "None specified"
            detail_level = self.user_profile["preferences"]["code_detail_level"]
            include_academic = self.user_profile["preferences"]["include_academic_sources"]
            
            user_context = f"""
User Preferences:
- Code detail level: {detail_level}
- Include academic sources: {"Yes" if include_academic else "No"}
- Topics of interest: {interests}
"""
        
        prompt = f"""You are an expert research planner specializing in software engineering and programming. Your task is to break down a complex research question into smaller, focused sub-questions that can be answered independently.

Main Question: {query}

{user_context}

For this question about code and programming:
1. Identify 3-5 key sub-questions that would help answer the main question comprehensively
2. For each sub-question, specify whether it requires:
   - CODE_ANALYSIS: Looking at the codebase structure, patterns, or specific implementations
   - WEB_SEARCH: Finding external information, documentation, or best practices
   - ACADEMIC_SEARCH: Finding relevant academic papers or formal documentation
   - VISUALIZATION: Creating or analyzing visual representations of code or data
   - COMBINATION: Requiring multiple types of research

Format your response as JSON:
{{
  "plan_summary": "Brief explanation of your research approach",
  "sub_questions": [
    {{
      "question": "First sub-question",
      "type": "CODE_ANALYSIS|WEB_SEARCH|ACADEMIC_SEARCH|VISUALIZATION|COMBINATION",
      "rationale": "Why this question helps",
      "priority": 1-5 (1 being highest priority)
    }},
    ...
  ]
}}
"""
        
        response = await self._rate_limited_api_call(
            lambda: self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert research planner specializing in code and software engineering questions."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return result["plan_summary"], result["sub_questions"]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing research plan: {e}")
            # Fallback to a simple plan
            return "Basic research plan", [
                {
                    "question": query,
                    "type": "COMBINATION",
                    "rationale": "Direct answer to main question",
                    "priority": 1
                }
            ]
    
    async def _search_academic_papers(self, query: str) -> str:
        """
        Search for relevant academic papers and documentation.
        
        Args:
            query: The search query
            
        Returns:
            Formatted results from academic sources
        """
        # In a real implementation, this would use an academic API like Semantic Scholar, arXiv, etc.
        # For now, we'll simulate academic search results
        
        # Simulate a delay to mimic real API calls
        await asyncio.sleep(0.5)
        
        # Mock academic search results
        mock_results = [
            {
                "title": f"Academic paper related to: {query}",
                "authors": ["Author One", "Author Two"],
                "abstract": f"This is a simulated academic paper abstract related to {query}. It would contain a summary of the research findings.",
                "url": "https://example.com/academic1",
                "year": 2023
            },
            {
                "title": f"Another academic resource for: {query}",
                "authors": ["Researcher A", "Researcher B"],
                "abstract": f"Another simulated academic resource with information about {query}. This would include methodology and results.",
                "url": "https://example.com/academic2",
                "year": 2022
            }
        ]
        
        # Format the results
        formatted_results = ""
        for i, result in enumerate(mock_results):
            formatted_results += f"[{i+1}] {result['title']} ({result['year']})\n"
            formatted_results += f"Authors: {', '.join(result['authors'])}\n"
            formatted_results += f"URL: {result['url']}\n"
            formatted_results += f"Abstract: {result['abstract']}\n\n"
        
        return formatted_results
    
    async def _generate_code_visualization(self, query: str, code_context: str) -> str:
        """
        Generate a visualization description for code or data.
        
        Args:
            query: The visualization request
            code_context: The code context to visualize
            
        Returns:
            Textual description of the visualization
        """
        prompt = f"""You are an expert in code visualization. Your task is to describe how the given code could be visualized to enhance understanding.

Query: {query}

Code Context:
{code_context}

Please describe a visualization that would help understand this code better. Include:
1. The type of visualization (e.g., flowchart, sequence diagram, dependency graph)
2. Key elements to include in the visualization
3. How the visualization would help answer the original query
4. Any color coding or special notation that would enhance clarity

Your description should be detailed enough that someone could create the visualization from your instructions.
"""
        
        response = await self._rate_limited_api_call(
            lambda: self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in code visualization and software architecture."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
        )
        
        return response.choices[0].message.content
    
    async def _execute_sub_question(self, sub_question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single sub-question using the appropriate specialized agent(s).
        
        Args:
            sub_question: Dictionary containing the sub-question details
            
        Returns:
            Dictionary with the results
        """
        question = sub_question["question"]
        question_type = sub_question["type"]
        
        results = {}
        
        if question_type in ["CODE_ANALYSIS", "COMBINATION"]:
            # Use code agent for code-related questions
            code_answer = await self.code_agent.answer_question(question)
            results["code_analysis"] = code_answer
        
        if question_type in ["WEB_SEARCH", "COMBINATION"]:
            # Use web agent for external information
            web_answer = await self.web_agent.search(question)
            results["web_search"] = web_answer
        
        if question_type in ["ACADEMIC_SEARCH", "COMBINATION"]:
            # Search academic papers
            academic_answer = await self._search_academic_papers(question)
            results["academic_search"] = academic_answer
        
        if question_type in ["VISUALIZATION", "COMBINATION"]:
            # Only attempt visualization if we have code context
            if "code_analysis" in results:
                visualization = await self._generate_code_visualization(question, results["code_analysis"])
                results["visualization"] = visualization
        
        return {
            "question": question,
            "type": question_type,
            "results": results
        }
    
    async def _synthesize_results(self, main_query: str, plan_summary: str, sub_question_results: List[Dict[str, Any]]) -> str:
        """
        Synthesize the results from all sub-questions into a coherent answer.
        
        Args:
            main_query: The original research question
            plan_summary: Summary of the research plan
            sub_question_results: Results from all sub-questions
            
        Returns:
            Synthesized answer to the main question
        """
        # Format the results for the prompt
        formatted_results = []
        for result in sub_question_results:
            question = result["question"]
            question_type = result["type"]
            
            result_text = f"Sub-question: {question}\nType: {question_type}\n\n"
            
            if "code_analysis" in result["results"]:
                result_text += f"Code Analysis Results:\n{result['results']['code_analysis']}\n\n"
            
            if "web_search" in result["results"]:
                result_text += f"Web Search Results:\n{result['results']['web_search']}\n\n"
            
            if "academic_search" in result["results"]:
                result_text += f"Academic Research Results:\n{result['results']['academic_search']}\n\n"
            
            if "visualization" in result["results"]:
                result_text += f"Visualization Description:\n{result['results']['visualization']}\n\n"
            
            formatted_results.append(result_text)
        
        all_results = "\n\n".join(formatted_results)
        
        # Include user preferences if available
        user_context = ""
        if self.user_profile:
            detail_level = self.user_profile["preferences"]["code_detail_level"]
            user_context = f"\nThe user prefers {detail_level} level of code detail in responses."
        
        prompt = f"""You are an expert code researcher tasked with synthesizing information from multiple sources to answer a complex question.

Original Question: {main_query}

Research Plan: {plan_summary}

Research Results:
{all_results}

Based on all the information above, provide a comprehensive, well-structured answer to the original question. Include:{user_context}
1. A clear, direct answer to the main question
2. Supporting evidence from code analysis, web search, and academic sources
3. Any relevant code patterns, best practices, or implementation details
4. References to visualizations where they help explain concepts
5. Acknowledgment of limitations or areas where more information might be needed

Your answer should be technical but accessible, focusing on practical insights rather than just theoretical knowledge.
"""
        
        response = await self._rate_limited_api_call(
            lambda: self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert code researcher with deep knowledge of software engineering principles and practices."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
        )
        
        return response.choices[0].message.content
    
    async def research(self, query: str, channel_id: Optional[str] = None) -> str:
        """
        Perform comprehensive research on a given query.
        
        Args:
            query: The research question
            channel_id: Optional Slack channel ID for logging
            
        Returns:
            Comprehensive answer to the research question
        """
        try:
            # Check cache first
            cached_result = self._get_cached_result(query)
            if cached_result:
                logger.info(f"Using cached result for query: {query}")
                return cached_result
            
            # Step 1: Create a research plan
            plan_summary, sub_questions = await self._create_research_plan(query)
            logger.info(f"Created research plan with {len(sub_questions)} sub-questions")
            
            # Step 2: Sort sub-questions by priority
            sub_questions.sort(key=lambda x: x.get("priority", 5))
            
            # Step 3: Execute all sub-questions in parallel
            tasks = [self._execute_sub_question(sq) for sq in sub_questions]
            sub_question_results = await asyncio.gather(*tasks)
            
            # Step 4: Synthesize the results
            final_answer = await self._synthesize_results(query, plan_summary, sub_question_results)
            
            # Step 5: Cache the result
            self._cache_research_result(query, final_answer)
            
            # Step 6: Log the research
            self._log_research(query, plan_summary, 
                              {sq["question"]: sq["results"] for sq in sub_question_results}, 
                              final_answer)
            
            # Step 7: Update user profile if user_id is provided
            if self.user_id:
                self._update_user_profile(query)
            
            return final_answer
            
        except Exception as e:
            logger.exception(f"Error in research: {e}")
            return f"I encountered an error while researching your question: {str(e)}. Please try a different query or try again later."
    
    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> str:
        """
        Update user preferences for personalization.
        
        Args:
            user_id: Slack user ID
            preferences: Dictionary of preferences to update
            
        Returns:
            Confirmation message
        """
        if not self.user_profile or self.user_profile["user_id"] != user_id:
            self.user_profile = self._load_or_create_user_profile(user_id)
        
        # Update preferences
        for key, value in preferences.items():
            if key in self.user_profile["preferences"]:
                self.user_profile["preferences"][key] = value
        
        # Save updated profile
        profile_path = self.profiles_dir / f"{user_id}.json"
        with open(profile_path, "w") as f:
            json.dump(self.user_profile, f, indent=2)
        
        return f"Preferences updated successfully. Your current preferences are: {json.dumps(self.user_profile['preferences'], indent=2)}"
    
    async def add_topic_of_interest(self, user_id: str, topic: str) -> str:
        """
        Add a topic of interest to the user profile.
        
        Args:
            user_id: Slack user ID
            topic: Topic to add
            
        Returns:
            Confirmation message
        """
        if not self.user_profile or self.user_profile["user_id"] != user_id:
            self.user_profile = self._load_or_create_user_profile(user_id)
        
        # Add topic if not already present
        if topic not in self.user_profile["topics_of_interest"]:
            self.user_profile["topics_of_interest"].append(topic)
        
        # Save updated profile
        profile_path = self.profiles_dir / f"{user_id}.json"
        with open(profile_path, "w") as f:
            json.dump(self.user_profile, f, indent=2)
        
        return f"Added '{topic}' to your topics of interest. Your current topics are: {', '.join(self.user_profile['topics_of_interest'])}"
    
    async def save_feedback(self, user_id: str, query: str, feedback: str) -> str:
        """
        Save user feedback on a research result.
        
        Args:
            user_id: Slack user ID
            query: The original query
            feedback: User feedback
            
        Returns:
            Confirmation message
        """
        if not self.user_profile or self.user_profile["user_id"] != user_id:
            self.user_profile = self._load_or_create_user_profile(user_id)
        
        # Update user profile with feedback
        self._update_user_profile(query, feedback)
        
        # Add to feedback collection
        query_hash = hashlib.md5(query.encode()).hexdigest()
        self.user_profile["feedback"][query_hash] = {
            "query": query,
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save updated profile
        profile_path = self.profiles_dir / f"{user_id}.json"
        with open(profile_path, "w") as f:
            json.dump(self.user_profile, f, indent=2)
        
        return "Thank you for your feedback! It will help improve future research results."