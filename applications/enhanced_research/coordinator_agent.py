"""Coordinator agent that integrates code analysis and web search."""

import logging
from typing import Dict, List, Optional, Union
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agentgen.agents.utils import AgentConfig
from agentgen.extensions.langchain.llm import get_llm
from agentgen.agents.code_agent import CodeAgent

from applications.enhanced_research.web_search_agent import WebSearchAgent


class CoordinatorAgent:
    """Agent that coordinates between code analysis and web search."""
    
    def __init__(
        self,
        codebase,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-5-sonnet-latest",
        agent_config: Optional[AgentConfig] = None,
        **kwargs
    ):
        """Initialize a CoordinatorAgent.
        
        Args:
            codebase: The codebase to operate on
            model_provider: The model provider to use
            model_name: Name of the model to use
            agent_config: Configuration for the agent
            **kwargs: Additional LLM configuration options
        """
        self.codebase = codebase
        self.model_name = model_name
        self.model_provider = model_provider
        self.llm_kwargs = kwargs
        
        # Initialize the LLM for coordination decisions
        self.llm = get_llm(model_provider=model_provider, model_name=model_name, **kwargs)
        
        # Initialize the code agent
        self.code_agent = CodeAgent(
            codebase=codebase,
            model_provider=model_provider,
            model_name=model_name,
            agent_config=agent_config,
            **kwargs
        )
        
        # Initialize the web search agent
        self.web_search_agent = WebSearchAgent(
            model_provider=model_provider,
            model_name=model_name,
            agent_config=agent_config,
            **kwargs
        )
        
        # System prompt for the coordinator
        self.coordinator_prompt = """You are an expert research coordinator that determines the best approach to answer complex questions about code and programming.

For each question, you need to decide whether to:
1. Use code analysis to examine the codebase directly
2. Use web search to find information online
3. Use both approaches in combination

Guidelines for your decision:
- Use code analysis for questions about the specific codebase structure, implementation details, or internal workings
- Use web search for general programming concepts, best practices, or information about external libraries and frameworks
- Use both when the question requires understanding both the specific codebase and broader context

Your task is to:
1. Analyze the question
2. Decide which approach(es) to use
3. If using both, determine what specific aspects should be researched via code analysis vs. web search
4. Format your response as a JSON object with the following structure:
   {
     "approach": "code_analysis" | "web_search" | "combined",
     "reasoning": "Brief explanation of your decision",
     "code_analysis_query": "Question for code analysis" (if applicable),
     "web_search_query": "Question for web search" (if applicable)
   }

Respond ONLY with the JSON object, nothing else."""
    
    def research(self, query: str, thread_id: Optional[str] = None) -> Dict:
        """Perform research using the appropriate agent(s).
        
        Args:
            query: The research query
            thread_id: Optional thread ID for message history
            
        Returns:
            Dictionary with research results
        """
        if thread_id is None:
            thread_id = str(uuid4())
        
        # Determine the approach to use
        approach = self._determine_approach(query)
        
        results = {
            "query": query,
            "approach": approach["approach"],
            "reasoning": approach["reasoning"],
            "code_analysis_result": None,
            "web_search_result": None,
            "combined_result": None
        }
        
        # Execute the appropriate agent(s)
        if approach["approach"] == "code_analysis":
            code_result = self.code_agent.run(approach["code_analysis_query"], thread_id=thread_id)
            results["code_analysis_result"] = code_result
            results["combined_result"] = code_result
            
        elif approach["approach"] == "web_search":
            web_result = self.web_search_agent.search(approach["web_search_query"], thread_id=thread_id)
            results["web_search_result"] = web_result
            results["combined_result"] = web_result
            
        elif approach["approach"] == "combined":
            # Run both agents
            code_result = self.code_agent.run(approach["code_analysis_query"], thread_id=f"{thread_id}_code")
            web_result = self.web_search_agent.search(approach["web_search_query"], thread_id=f"{thread_id}_web")
            
            results["code_analysis_result"] = code_result
            results["web_search_result"] = web_result
            
            # Synthesize the results
            combined_result = self._synthesize_results(
                query, 
                code_result, 
                web_result,
                thread_id=f"{thread_id}_synthesis"
            )
            results["combined_result"] = combined_result
        
        return results
    
    def _determine_approach(self, query: str) -> Dict:
        """Determine which approach to use for the query.
        
        Args:
            query: The research query
            
        Returns:
            Dictionary with the approach decision
        """
        # Prepare the prompt for the LLM
        prompt = f"Question: {query}\n\nDetermine the best approach to answer this question."
        
        # Call the LLM to determine the approach
        response = self.llm.invoke([
            SystemMessage(content=self.coordinator_prompt),
            HumanMessage(content=prompt)
        ])
        
        # Parse the response as JSON
        try:
            import json
            approach = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            logging.warning("Failed to parse coordinator response as JSON. Using default approach.")
            approach = {
                "approach": "combined",
                "reasoning": "Default approach due to parsing error",
                "code_analysis_query": query,
                "web_search_query": query
            }
        
        # Ensure all required fields are present
        if approach["approach"] == "code_analysis" and "code_analysis_query" not in approach:
            approach["code_analysis_query"] = query
            
        if approach["approach"] == "web_search" and "web_search_query" not in approach:
            approach["web_search_query"] = query
            
        if approach["approach"] == "combined":
            if "code_analysis_query" not in approach:
                approach["code_analysis_query"] = query
            if "web_search_query" not in approach:
                approach["web_search_query"] = query
        
        return approach
    
    def _synthesize_results(
        self, 
        original_query: str, 
        code_result: str, 
        web_result: str,
        thread_id: Optional[str] = None
    ) -> str:
        """Synthesize results from code analysis and web search.
        
        Args:
            original_query: The original research query
            code_result: Result from code analysis
            web_result: Result from web search
            thread_id: Optional thread ID for message history
            
        Returns:
            Synthesized result
        """
        # System prompt for synthesis
        synthesis_prompt = """You are an expert at synthesizing information from multiple sources to provide comprehensive answers.
Your task is to combine information from code analysis and web search to answer a research question about code.

Guidelines:
1. Analyze both the code analysis results and web search results
2. Identify the most relevant information from each source
3. Combine the information into a coherent, comprehensive answer
4. Highlight where the code-specific information and general knowledge complement each other
5. Structure your answer logically with clear sections and bullet points where appropriate
6. Provide specific code examples or references when relevant

Your response should be a well-structured, comprehensive answer to the original question."""
        
        # Prepare the prompt for the LLM
        prompt = f"""Original Question: {original_query}

Code Analysis Result:
{code_result}

Web Search Result:
{web_result}

Please synthesize these results into a comprehensive answer."""
        
        # Call the LLM to synthesize the results
        response = self.llm.invoke([
            SystemMessage(content=synthesis_prompt),
            HumanMessage(content=prompt)
        ])
        
        return response.content