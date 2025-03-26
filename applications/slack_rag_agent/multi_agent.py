"""Multi-agent coordinator for complex code research queries.

This module implements a MindSearch-inspired multi-agent system that combines:
1. Code analysis using the SlackRAGAgent
2. Web search for external context
3. Coordination between multiple specialized agents
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

from openai import OpenAI
from codegen import Codebase

from applications.slack_rag_agent.agent import SlackRAGAgent
from applications.slack_rag_agent.web_search_agent import WebSearchAgent

logger = logging.getLogger(__name__)

class MultiAgentCoordinator:
    """
    Coordinates multiple specialized agents to answer complex code research questions.
    Inspired by MindSearch's multi-agent architecture.
    """
    
    def __init__(self, repo_name: str, cache_dir: str = ".cache"):
        """
        Initialize the MultiAgentCoordinator.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            cache_dir: Directory to store cache files
        """
        self.repo_name = repo_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize specialized agents
        self.code_agent = SlackRAGAgent(repo_name, cache_dir)
        self.web_agent = WebSearchAgent(cache_dir)
        
        # Initialize OpenAI client
        self.client = OpenAI()
        
        # Path for logging coordinator activities
        self.log_path = self.cache_dir / "coordinator_logs.jsonl"
    
    def _log_activity(self, query: str, plan: str, results: Dict[str, Any], final_answer: str):
        """Log coordinator activities for analysis."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "plan": plan,
            "agent_results": results,
            "final_answer": final_answer
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    async def _create_research_plan(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Create a research plan by breaking down the query into sub-questions.
        
        Args:
            query: The main research question
            
        Returns:
            Tuple of (plan_summary, sub_questions)
        """
        prompt = f"""You are an expert research planner. Your task is to break down a complex code research question into smaller, focused sub-questions that can be answered independently.

Main Question: {query}

For this question about code and programming:
1. Identify 2-4 key sub-questions that would help answer the main question
2. For each sub-question, specify whether it requires:
   - CODE_ANALYSIS: Looking at the codebase structure, patterns, or specific implementations
   - WEB_SEARCH: Finding external information, documentation, or best practices
   - BOTH: Requiring both code analysis and external information

Format your response as JSON:
{{
  "plan_summary": "Brief explanation of your research approach",
  "sub_questions": [
    {{
      "question": "First sub-question",
      "type": "CODE_ANALYSIS|WEB_SEARCH|BOTH",
      "rationale": "Why this question helps"
    }},
    ...
  ]
}}
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert research planner specializing in code and software engineering questions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
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
                    "type": "BOTH",
                    "rationale": "Direct answer to main question"
                }
            ]
    
    async def _execute_sub_question(self, sub_question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single sub-question using the appropriate agent(s).
        
        Args:
            sub_question: Dictionary containing the sub-question details
            
        Returns:
            Dictionary with the results
        """
        question = sub_question["question"]
        question_type = sub_question["type"]
        
        results = {}
        
        if question_type in ["CODE_ANALYSIS", "BOTH"]:
            # Use code agent for code-related questions
            code_answer = await self.code_agent.answer_question(question)
            results["code_analysis"] = code_answer
        
        if question_type in ["WEB_SEARCH", "BOTH"]:
            # Use web agent for external information
            web_answer = await self.web_agent.search(question)
            results["web_search"] = web_answer
        
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
            
            formatted_results.append(result_text)
        
        all_results = "\n\n".join(formatted_results)
        
        prompt = f"""You are an expert code researcher tasked with synthesizing information from multiple sources to answer a complex question.

Original Question: {main_query}

Research Plan: {plan_summary}

Research Results:
{all_results}

Based on all the information above, provide a comprehensive, well-structured answer to the original question. Include:
1. A clear, direct answer to the main question
2. Supporting evidence from both code analysis and external sources
3. Any relevant code patterns, best practices, or implementation details
4. Acknowledgment of limitations or areas where more information might be needed

Your answer should be technical but accessible, focusing on practical insights rather than just theoretical knowledge.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert code researcher with deep knowledge of software engineering principles and practices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    async def process_query(self, query: str, channel_id: Optional[str] = None) -> str:
        """
        Process a complex research query using the multi-agent system.
        
        Args:
            query: The research question
            channel_id: Optional Slack channel ID for logging
            
        Returns:
            Comprehensive answer to the question
        """
        try:
            # Step 1: Create a research plan
            plan_summary, sub_questions = await self._create_research_plan(query)
            
            # Step 2: Execute all sub-questions in parallel
            tasks = [self._execute_sub_question(sq) for sq in sub_questions]
            sub_question_results = await asyncio.gather(*tasks)
            
            # Step 3: Synthesize the results
            final_answer = await self._synthesize_results(query, plan_summary, sub_question_results)
            
            # Log the activity
            self._log_activity(query, plan_summary, 
                              {f"sub_question_{i}": result for i, result in enumerate(sub_question_results)}, 
                              final_answer)
            
            return final_answer
            
        except Exception as e:
            logger.exception(f"Error in multi-agent processing: {e}")
            # Fallback to the code agent if the multi-agent approach fails
            return await self.code_agent.answer_question(query, channel_id)