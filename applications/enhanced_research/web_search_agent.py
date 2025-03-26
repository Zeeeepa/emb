"""Web search agent based on MindSearch's multi-agent architecture."""

import json
import logging
import os
import re
from copy import deepcopy
from typing import Dict, List, Optional, Tuple, Union, Generator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph

from agentgen.extensions.langchain.llm import get_llm
from agentgen.agents.utils import AgentConfig


class WebSearchTool:
    """Tool for performing web searches using DuckDuckGo."""
    
    def __init__(self):
        try:
            from duckduckgo_search import DDGS
            self.ddgs = DDGS()
        except ImportError:
            raise ImportError(
                "The duckduckgo-search package is required to use the WebSearchTool. "
                "Please install it with `pip install duckduckgo-search`."
            )
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Perform a web search using DuckDuckGo.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with title, link, and snippet
        """
        results = []
        try:
            for r in self.ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        except Exception as e:
            logging.error(f"Error during web search: {e}")
            results.append({
                "title": "Error",
                "link": "",
                "snippet": f"An error occurred during the search: {str(e)}"
            })
        
        return results


class WebSearchGraph:
    """Graph-based web search implementation inspired by MindSearch."""
    
    def __init__(self):
        self.nodes = {}
        self.adjacency_list = {}
        self.search_tool = WebSearchTool()
    
    def add_root_node(self, node_content: str, node_name: str = "root"):
        """Add the root node with the main query.
        
        Args:
            node_content: The main query
            node_name: Name of the node (default: "root")
        """
        self.nodes[node_name] = {"content": node_content, "type": "root"}
        self.adjacency_list[node_name] = []
    
    def add_search_node(self, node_name: str, node_content: str) -> List[Dict]:
        """Add a search node and perform the search.
        
        Args:
            node_name: Name of the node
            node_content: The search query
            
        Returns:
            List of search results
        """
        self.nodes[node_name] = {"content": node_content, "type": "searcher"}
        self.adjacency_list[node_name] = []
        
        # Perform the search
        results = self.search_tool.search(node_content)
        self.nodes[node_name]["results"] = results
        
        return results
    
    def add_edge(self, start_node: str, end_node: str):
        """Add an edge between nodes.
        
        Args:
            start_node: Starting node name
            end_node: Ending node name
        """
        if start_node not in self.adjacency_list:
            self.adjacency_list[start_node] = []
        
        self.adjacency_list[start_node].append({"name": end_node})
    
    def add_response_node(self, content: str, node_name: str = "response"):
        """Add a response node with the final answer.
        
        Args:
            content: The final answer
            node_name: Name of the node (default: "response")
        """
        self.nodes[node_name] = {"content": content, "type": "response"}
    
    def get_all_search_results(self) -> List[Dict]:
        """Get all search results from all search nodes.
        
        Returns:
            List of all search results with node information
        """
        all_results = []
        for node_name, node_data in self.nodes.items():
            if node_data.get("type") == "searcher" and "results" in node_data:
                for result in node_data["results"]:
                    all_results.append({
                        "query": node_data["content"],
                        "title": result["title"],
                        "link": result["link"],
                        "snippet": result["snippet"]
                    })
        
        return all_results
    
    def get_graph_state(self) -> Dict:
        """Get the current state of the graph.
        
        Returns:
            Dictionary with nodes and adjacency list
        """
        return {
            "nodes": deepcopy(self.nodes),
            "adjacency_list": deepcopy(self.adjacency_list)
        }


def create_web_search_agent(
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    config: Optional[AgentConfig] = None,
    **kwargs
) -> CompiledGraph:
    """Create a web search agent using LangGraph.
    
    Args:
        model_provider: The model provider to use
        model_name: Name of the model to use
        config: Agent configuration
        **kwargs: Additional LLM configuration options
        
    Returns:
        A compiled LangGraph for web search
    """
    # Initialize the LLM
    llm = get_llm(model_provider=model_provider, model_name=model_name, **kwargs)
    
    # System prompt for the query decomposition agent
    decompose_system_prompt = """You are an expert at breaking down complex research questions into specific sub-questions.
Your task is to analyze a main research question and decompose it into 3-5 specific sub-questions that will help answer the main question comprehensively.

Guidelines:
1. Analyze the main question to understand its scope and requirements
2. Break it down into 3-5 specific, focused sub-questions
3. Ensure the sub-questions cover different aspects of the main question
4. Make each sub-question clear, specific, and searchable
5. Format your response as a JSON array of strings, each containing one sub-question

Example:
For the main question "What are the environmental impacts of electric vehicles?", you might generate:
["What are the carbon emissions associated with manufacturing electric vehicle batteries?",
"How does the electricity source affect the environmental impact of electric vehicles?",
"What are the end-of-life recycling challenges for electric vehicle components?",
"How do rare earth metals used in electric vehicles impact the environment?"]

Respond ONLY with the JSON array of sub-questions, nothing else."""

    # System prompt for the synthesis agent
    synthesis_system_prompt = """You are an expert at synthesizing information from multiple sources to answer complex questions.
Your task is to analyze search results from multiple queries and synthesize a comprehensive answer to the main question.

Guidelines:
1. Analyze all the search results provided
2. Identify key information relevant to the main question
3. Synthesize the information into a coherent, comprehensive answer
4. Cite sources using [1], [2], etc. when referencing specific information
5. Structure your answer logically with clear sections and bullet points where appropriate
6. Provide a balanced view that considers different perspectives
7. Highlight any areas where information is limited or contradictory

The search results are provided in the following format:
- Query: The specific sub-question that was searched
- Results: A list of search results with title, link, and snippet

Your response should be a well-structured, comprehensive answer to the main question."""

    # Define the state schema
    class WebSearchState(dict):
        """State for the web search agent."""
        def __init__(
            self,
            messages: Optional[List] = None,
            graph: Optional[WebSearchGraph] = None,
            sub_questions: Optional[List[str]] = None,
            main_question: Optional[str] = None,
            final_answer: Optional[str] = None,
        ):
            self.update({
                "messages": messages or [],
                "graph": graph or WebSearchGraph(),
                "sub_questions": sub_questions or [],
                "main_question": main_question or "",
                "final_answer": final_answer or "",
            })
    
    # Define the nodes for the graph
    def decompose_question(state: WebSearchState) -> WebSearchState:
        """Decompose the main question into sub-questions."""
        messages = state["messages"]
        main_question = state["main_question"]
        
        # Create a new state with the updated messages
        new_state = deepcopy(state)
        
        # Initialize the graph with the main question
        graph = WebSearchGraph()
        graph.add_root_node(main_question)
        new_state["graph"] = graph
        
        # Prepare the prompt for the LLM
        prompt = f"Main Question: {main_question}\n\nBreak this down into sub-questions."
        
        # Call the LLM to decompose the question
        response = llm.invoke([
            SystemMessage(content=decompose_system_prompt),
            HumanMessage(content=prompt)
        ])
        
        # Extract the sub-questions from the response
        try:
            # Try to parse the response as JSON
            sub_questions = json.loads(response.content)
            if not isinstance(sub_questions, list):
                sub_questions = [response.content]
        except json.JSONDecodeError:
            # If parsing fails, extract using regex
            pattern = r'\["(.+?)"\]'
            matches = re.findall(pattern, response.content)
            if matches:
                sub_questions = matches
            else:
                # Fallback: split by newlines and clean up
                sub_questions = [q.strip(' "[]') for q in response.content.split('\n') if q.strip()]
        
        # Update the state with the sub-questions
        new_state["sub_questions"] = sub_questions
        new_state["messages"] = messages + [
            HumanMessage(content=prompt),
            AIMessage(content=response.content)
        ]
        
        return new_state
    
    def perform_searches(state: WebSearchState) -> WebSearchState:
        """Perform searches for each sub-question."""
        new_state = deepcopy(state)
        graph = new_state["graph"]
        sub_questions = new_state["sub_questions"]
        
        # Add search nodes for each sub-question
        for i, question in enumerate(sub_questions):
            node_name = f"search_{i+1}"
            graph.add_search_node(node_name, question)
            graph.add_edge("root", node_name)
        
        return new_state
    
    def synthesize_results(state: WebSearchState) -> WebSearchState:
        """Synthesize the search results into a final answer."""
        messages = state["messages"]
        graph = state["graph"]
        main_question = state["main_question"]
        
        # Create a new state with the updated messages
        new_state = deepcopy(state)
        
        # Get all search results
        all_results = graph.get_all_search_results()
        
        # Prepare the prompt for the LLM
        prompt = f"""Main Question: {main_question}

Search Results:
"""
        
        # Group results by query
        results_by_query = {}
        for result in all_results:
            query = result["query"]
            if query not in results_by_query:
                results_by_query[query] = []
            results_by_query[query].append(result)
        
        # Format the results
        for query, results in results_by_query.items():
            prompt += f"\nQuery: {query}\nResults:\n"
            for i, result in enumerate(results):
                prompt += f"{i+1}. {result['title']} - {result['link']}\n   {result['snippet']}\n"
        
        # Call the LLM to synthesize the results
        response = llm.invoke([
            SystemMessage(content=synthesis_system_prompt),
            HumanMessage(content=prompt)
        ])
        
        # Add the response node to the graph
        graph.add_response_node(response.content)
        
        # Update the state with the final answer
        new_state["final_answer"] = response.content
        new_state["messages"] = messages + [
            HumanMessage(content=prompt),
            AIMessage(content=response.content)
        ]
        
        return new_state
    
    def should_end(state: WebSearchState) -> str:
        """Determine if the workflow should end."""
        if state["final_answer"]:
            return "end"
        return "continue"
    
    # Create the graph
    workflow = StateGraph(WebSearchState)
    
    # Add the nodes
    workflow.add_node("decompose", decompose_question)
    workflow.add_node("search", perform_searches)
    workflow.add_node("synthesize", synthesize_results)
    
    # Add the edges
    workflow.add_edge("decompose", "search")
    workflow.add_edge("search", "synthesize")
    workflow.add_conditional_edges("synthesize", should_end, {
        "end": END,
        "continue": "decompose"  # This creates a loop if needed
    })
    
    # Set the entry point
    workflow.set_entry_point("decompose")
    
    # Compile the graph
    return workflow.compile()


class WebSearchAgent:
    """Agent for performing web searches using a multi-agent approach."""
    
    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-5-sonnet-latest",
        agent_config: Optional[AgentConfig] = None,
        **kwargs
    ):
        """Initialize a WebSearchAgent.
        
        Args:
            model_provider: The model provider to use
            model_name: Name of the model to use
            agent_config: Configuration for the agent
            **kwargs: Additional LLM configuration options
        """
        self.model_name = model_name
        self.agent = create_web_search_agent(
            model_provider=model_provider,
            model_name=model_name,
            config=agent_config,
            **kwargs
        )
    
    def search(self, query: str, thread_id: Optional[str] = None) -> str:
        """Perform a web search using the multi-agent approach.
        
        Args:
            query: The search query
            thread_id: Optional thread ID for message history
            
        Returns:
            The synthesized answer
        """
        # Configure the agent
        config = RunnableConfig(
            configurable={"thread_id": thread_id or "default"},
            recursion_limit=100
        )
        
        # Initialize the state
        initial_state = {
            "messages": [],
            "graph": WebSearchGraph(),
            "sub_questions": [],
            "main_question": query,
            "final_answer": ""
        }
        
        # Run the agent
        result = self.agent.invoke(initial_state, config=config)
        
        return result["final_answer"]
    
    def stream_search(self, query: str, thread_id: Optional[str] = None) -> Generator[Dict, None, Dict]:
        """Stream the web search process.
        
        Args:
            query: The search query
            thread_id: Optional thread ID for message history
            
        Yields:
            State updates during the search process
            
        Returns:
            The final state
        """
        # Configure the agent
        config = RunnableConfig(
            configurable={"thread_id": thread_id or "default"},
            recursion_limit=100
        )
        
        # Initialize the state
        initial_state = {
            "messages": [],
            "graph": WebSearchGraph(),
            "sub_questions": [],
            "main_question": query,
            "final_answer": ""
        }
        
        # Stream the agent execution
        for chunk in self.agent.stream(initial_state, config=config):
            yield chunk
        
        return chunk  # Return the final state