import os
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from agentgen.agents.loggers import ExternalLogger
from agentgen.agents.tracer import MessageStreamTracer
from agentgen.extensions.langchain.agent import create_agent_with_tools
from agentgen.extensions.langchain.utils.get_langsmith_url import (
    find_and_print_langsmith_run_url,
)

if TYPE_CHECKING:
    from codegen import Codebase

from agentgen.agents.utils import AgentConfig


class ResearchAgent:
    """Agent for conducting in-depth research on topics and generating comprehensive reports."""

    codebase: "Codebase"
    agent: CompiledGraph
    langsmith_client: Client
    project_name: str
    thread_id: str | None = None
    run_id: str | None = None
    instance_id: str | None = None
    difficulty: int | None = None
    logger: Optional[ExternalLogger] = None

    def __init__(
        self,
        codebase: "Codebase",
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        tools: Optional[list[BaseTool]] = None,
        tags: Optional[list[str]] = [],
        metadata: Optional[dict] = {},
        agent_config: Optional[AgentConfig] = None,
        thread_id: Optional[str] = None,
        logger: Optional[ExternalLogger] = None,
        system_message: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a ResearchAgent.

        Args:
            codebase: The codebase to operate on
            model_provider: The model provider to use ("anthropic" or "openai")
            model_name: Name of the model to use
            memory: Whether to let LLM keep track of the conversation history
            tools: Additional tools to use
            tags: Tags to add to the agent trace. Must be of the same type.
            metadata: Metadata to use for the agent. Must be a dictionary.
            agent_config: Configuration options for the agent
            thread_id: Optional thread ID for message history
            logger: Optional external logger
            system_message: Optional custom system message
            **kwargs: Additional LLM configuration options. Supported options:
                - temperature: Temperature parameter (0-1)
                - top_p: Top-p sampling parameter (0-1)
                - top_k: Top-k sampling parameter (>= 1)
                - max_tokens: Maximum number of tokens to generate
        """
        self.codebase = codebase
        
        # Default research tools
        default_tools = []
        if tools:
            default_tools.extend(tools)
            
        # Create the agent with research-specific tools
        # Use custom system message if provided, otherwise use default
        if system_message:
            system_msg = SystemMessage(content=system_message)
        else:
            system_msg = SystemMessage(content=self._get_default_system_message())
            
        self.agent = create_agent_with_tools(
            tools=default_tools,
            model_provider=model_provider,
            model_name=model_name,
            system_message=system_msg,
            memory=memory,
            config=agent_config,
            **kwargs,
        )
        
        self.model_name = model_name
        self.langsmith_client = Client()

        if thread_id is None:
            self.thread_id = str(uuid4())
        else:
            self.thread_id = thread_id

        # Get project name from environment variable or use a default
        self.project_name = os.environ.get("LANGCHAIN_PROJECT", "RELACE")
        print(f"Using LangSmith project: {self.project_name}")

        # Store SWEBench metadata if provided
        self.run_id = metadata.get("run_id")
        self.instance_id = metadata.get("instance_id")
        # Extract difficulty value from "difficulty_X" format
        difficulty_str = metadata.get("difficulty", "")
        self.difficulty = int(difficulty_str.split("_")[1]) if difficulty_str and "_" in difficulty_str else None

        # Initialize tags for agent trace
        self.tags = [*tags, self.model_name]

        # set logger if provided
        self.logger = logger

        # Initialize metadata for agent trace
        self.metadata = {
            "project": self.project_name,
            "model": self.model_name,
            **metadata,
        }

    def _get_default_system_message(self) -> str:
        """Get the default system message for the research agent."""
        return """
        You are an expert research agent specialized in conducting comprehensive research on any topic.
        
        Your primary responsibilities are:
        
        1. Information Gathering:
           - Search for and collect relevant information from various sources
           - Evaluate the credibility and relevance of sources
           - Extract key facts, data, and insights
           - Identify different perspectives and viewpoints on the topic
        
        2. Analysis and Synthesis:
           - Organize information into coherent themes and categories
           - Identify patterns, trends, and relationships in the data
           - Compare and contrast different viewpoints and approaches
           - Recognize gaps in available information
        
        3. Critical Evaluation:
           - Assess the quality, reliability, and bias of sources
           - Identify methodological strengths and weaknesses
           - Evaluate the validity of claims and arguments
           - Consider alternative interpretations of the evidence
        
        4. Report Generation:
           - Synthesize findings into clear, well-structured reports
           - Present information in a balanced and objective manner
           - Support claims with appropriate evidence and citations
           - Organize content logically with clear sections and headings
           - Provide executive summaries for quick understanding
        
        When conducting research:
        - Be thorough and comprehensive in your information gathering
        - Consider multiple perspectives and sources
        - Maintain objectivity and avoid confirmation bias
        - Clearly distinguish between facts, expert opinions, and your own analysis
        - Use proper citations and references for all information
        - Structure your reports with clear sections, headings, and summaries
        
        Your goal is to provide comprehensive, accurate, and balanced research on any topic requested.
        """

    def run(self, prompt: str, image_urls: Optional[list[str]] = None) -> str:
        """Run the agent with a prompt and optional images.

        Args:
            prompt: The prompt to run
            image_urls: Optional list of base64-encoded image strings. Example: ["data:image/png;base64,<base64_str>"]

        Returns:
            The agent's response
        """
        self.config = {
            "configurable": {
                "thread_id": self.thread_id,
                "metadata": {"project": self.project_name},
            },
            "recursion_limit": 100,
        }

        # Prepare content with prompt and images if provided
        content = [{"type": "text", "text": prompt}]
        if image_urls:
            content += [{"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls]

        config = RunnableConfig(configurable={"thread_id": self.thread_id}, tags=self.tags, metadata=self.metadata, recursion_limit=200)
        # we stream the steps instead of invoke because it allows us to access intermediate nodes

        stream = self.agent.stream({"messages": [HumanMessage(content=content)]}, config=config, stream_mode="values")

        _tracer = MessageStreamTracer(logger=self.logger)

        # Process the stream with the tracer
        traced_stream = _tracer.process_stream(stream)

        # Keep track of run IDs from the stream
        run_ids = []

        for s in traced_stream:
            if len(s["messages"]) == 0 or isinstance(s["messages"][-1], HumanMessage):
                message = HumanMessage(content=content)
            else:
                message = s["messages"][-1]

            if isinstance(message, tuple):
                # print(message)
                pass
            else:
                if isinstance(message, AIMessage) and isinstance(message.content, list) and len(message.content) > 0 and "text" in message.content[0]:
                    AIMessage(message.content[0]["text"]).pretty_print()
                else:
                    message.pretty_print()

                # Try to extract run ID if available in metadata
                if hasattr(message, "additional_kwargs") and "run_id" in message.additional_kwargs:
                    run_ids.append(message.additional_kwargs["run_id"])

        # Get the last message content
        result = s["final_answer"]

        # Try to find run IDs in the LangSmith client's recent runs
        try:
            # Find and print the LangSmith run URL
            find_and_print_langsmith_run_url(self.langsmith_client, self.project_name)
        except Exception as e:
            separator = "=" * 60
            print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
            import traceback

            print(traceback.format_exc())
            print(separator)

        return result

    def research_topic(self, topic: str, depth: str = "medium", focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Conduct research on a specific topic.

        Args:
            topic: The topic to research
            depth: Depth of research ("brief", "medium", "comprehensive")
            focus_areas: Optional list of specific areas to focus on

        Returns:
            A dictionary containing the research results
        """
        prompt = f"Conduct {depth} research on the following topic: {topic}"
        
        if focus_areas:
            focus_str = ", ".join(focus_areas)
            prompt += f"\n\nPlease focus specifically on these areas: {focus_str}"
            
        response = self.run(prompt)
        
        # Here you could add parsing logic to convert the response into a structured format
        # For now, we'll return the raw response
        return {"research": response}

    def generate_report(self, research_data: str, format_type: str = "detailed", include_summary: bool = True) -> str:
        """Generate a structured report from research data.

        Args:
            research_data: The research data to include in the report
            format_type: Type of report format ("brief", "detailed", "academic")
            include_summary: Whether to include an executive summary

        Returns:
            The formatted report
        """
        summary_request = "Include an executive summary at the beginning." if include_summary else ""
        
        prompt = f"""
        Generate a {format_type} report based on the following research data:
        
        {research_data}
        
        {summary_request}
        """
        
        return self.run(prompt)

    def analyze_sources(self, sources: List[Dict[str, str]]) -> str:
        """Analyze and evaluate the credibility of sources.

        Args:
            sources: List of dictionaries containing source information
                    (e.g. [{"title": "Source Title", "content": "Source content", "url": "http://..."}])

        Returns:
            Analysis of the sources' credibility and relevance
        """
        sources_str = "\n\n".join([f"Source: {s.get('title', 'Untitled')}\nURL: {s.get('url', 'No URL')}\nContent: {s.get('content', 'No content')}" for s in sources])
        
        prompt = f"""
        Analyze the credibility and relevance of the following sources:
        
        {sources_str}
        
        For each source, please evaluate:
        1. Credibility (author expertise, publication reputation, etc.)
        2. Relevance to the research topic
        3. Potential biases or limitations
        4. Overall quality rating
        """
        
        return self.run(prompt)

    def get_agent_trace_url(self) -> str | None:
        """Get the URL for the most recent agent run in LangSmith.

        Returns:
            The URL for the run in LangSmith if found, None otherwise
        """
        try:
            return find_and_print_langsmith_run_url(client=self.langsmith_client, project_name=self.project_name)
        except Exception as e:
            separator = "=" * 60
            print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
            import traceback

            print(traceback.format_exc())
            print(separator)
            return None

    def get_tools(self) -> list[BaseTool]:
        """Get the list of tools available to the agent.
        
        Returns:
            List of BaseTool instances
        """
        return list(self.agent.get_graph().nodes["tools"].data.tools_by_name.values())

    def get_state(self) -> dict:
        """Get the current state of the agent.
        
        Returns:
            Dictionary containing the agent's state
        """
        return self.agent.get_state(self.config)

    def get_tags_metadata(self) -> tuple[list[str], dict]:
        """Get tags and metadata for the agent.
        
        Returns:
            Tuple of (tags, metadata)
        """
        tags = [self.model_name]
        metadata = {"project": self.project_name, "model": self.model_name}
        
        # Add SWEBench run ID and instance ID to the metadata and tags for filtering
        if self.run_id is not None:
            metadata["swebench_run_id"] = self.run_id
            tags.append(self.run_id)

        if self.instance_id is not None:
            metadata["swebench_instance_id"] = self.instance_id
            tags.append(self.instance_id)

        if self.difficulty is not None:
            metadata["swebench_difficulty"] = self.difficulty
            tags.append(f"difficulty_{self.difficulty}")

        return tags, metadata