"""Web search agent for retrieving external information.

This module implements a MindSearch-inspired web search agent that:
1. Breaks down complex queries into sub-queries
2. Searches the web for relevant information
3. Synthesizes the results into a coherent answer
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from openai import OpenAI

logger = logging.getLogger(__name__)

class WebSearchAgent:
    """
    Agent for performing web searches and synthesizing results.
    Inspired by MindSearch's web search capabilities.
    """
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize the WebSearchAgent.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize OpenAI client
        self.client = OpenAI()
        
        # Path for logging search activities
        self.log_path = self.cache_dir / "web_search_logs.jsonl"
        
        # Configure search API (using a mock implementation for now)
        # In a real implementation, this would use a search API like Bing, Google, or DuckDuckGo
        self.search_api_key = os.environ.get("SEARCH_API_KEY", "")
        self.search_endpoint = os.environ.get("SEARCH_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search")
    
    def _log_search(self, query: str, sub_queries: List[str], results: Dict[str, Any], synthesis: str):
        """Log search activities for analysis."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "sub_queries": sub_queries,
            "results": results,
            "synthesis": synthesis
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    async def _generate_sub_queries(self, query: str) -> List[str]:
        """
        Break down a complex query into simpler sub-queries.
        
        Args:
            query: The main search query
            
        Returns:
            List of sub-queries
        """
        prompt = f"""You are an expert search query generator. Your task is to break down a complex search query into 2-4 simpler, more focused sub-queries that will help gather comprehensive information.

Main Query: {query}

For this programming/code-related query:
1. Identify key aspects that need to be researched separately
2. Create focused sub-queries that target specific information needs
3. Ensure the sub-queries are clear and specific enough for web search

Format your response as a JSON array of strings, each representing a sub-query:
["sub-query 1", "sub-query 2", ...]
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert search query generator specializing in programming and software engineering topics."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "sub_queries" in result:
                return result["sub_queries"]
            else:
                # Try to extract an array from the response
                for key, value in result.items():
                    if isinstance(value, list):
                        return value
                
                # Fallback
                logger.warning(f"Unexpected format in sub-query generation: {result}")
                return [query]
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing sub-queries: {e}")
            return [query]
    
    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the web for a given query.
        
        Args:
            query: The search query
            
        Returns:
            List of search results
        """
        # In a real implementation, this would use an actual search API
        # For now, we'll simulate search results with a mock implementation
        
        # Simulate web search with a mock response
        mock_results = [
            {
                "title": f"Result for: {query}",
                "snippet": f"This is a simulated search result for the query: {query}. In a real implementation, this would contain actual content from the web.",
                "url": "https://example.com/result1"
            },
            {
                "title": f"Another result for: {query}",
                "snippet": f"Another simulated search result with different content related to: {query}.",
                "url": "https://example.com/result2"
            }
        ]
        
        # Simulate a delay to mimic real API calls
        await asyncio.sleep(0.5)
        
        return mock_results
    
    async def _synthesize_search_results(self, query: str, all_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Synthesize search results into a coherent answer.
        
        Args:
            query: The original search query
            all_results: Dictionary mapping sub-queries to their search results
            
        Returns:
            Synthesized answer
        """
        # Format the results for the prompt
        formatted_results = []
        for sub_query, results in all_results.items():
            result_text = f"Sub-query: {sub_query}\n\nResults:\n"
            
            for i, result in enumerate(results):
                result_text += f"[{i+1}] {result['title']}\n{result['url']}\n{result['snippet']}\n\n"
            
            formatted_results.append(result_text)
        
        all_results_text = "\n\n".join(formatted_results)
        
        prompt = f"""You are an expert researcher tasked with synthesizing information from multiple web search results to answer a complex question.

Original Query: {query}

Search Results:
{all_results_text}

Based on these search results, provide a comprehensive, well-structured answer to the original query. Include:
1. A clear, direct answer to the main question
2. Supporting information from the search results (cite sources when appropriate)
3. Any relevant code patterns, best practices, or implementation details mentioned
4. Acknowledgment of limitations or areas where more information might be needed

Your answer should be technical but accessible, focusing on practical insights rather than just theoretical knowledge.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert researcher with deep knowledge of software engineering principles and practices."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    async def search(self, query: str) -> str:
        """
        Perform a comprehensive web search for a given query.
        
        Args:
            query: The search query
            
        Returns:
            Synthesized answer based on search results
        """
        try:
            # Step 1: Generate sub-queries
            sub_queries = await self._generate_sub_queries(query)
            
            # Step 2: Search for each sub-query in parallel
            search_tasks = {sq: self._search_web(sq) for sq in sub_queries}
            results = {}
            
            for sq, task in search_tasks.items():
                results[sq] = await task
            
            # Step 3: Synthesize the results
            synthesis = await self._synthesize_search_results(query, results)
            
            # Log the search
            self._log_search(query, sub_queries, results, synthesis)
            
            return synthesis
            
        except Exception as e:
            logger.exception(f"Error in web search: {e}")
            return f"I encountered an error while searching the web: {str(e)}. Please try a different query or try again later."