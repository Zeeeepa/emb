"""Research agent implementation for the EMB framework."""

import os
from typing import List, Optional, Dict, Any
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from emb.core import BaseAgent, Config
from emb.agents.utils import AgentConfig
from emb.agents.loggers import ExternalLogger
from emb.agents.tracer import MessageStreamTracer


class ResearchAgent(BaseAgent):
    """Agent for conducting research."""

    agent: CompiledGraph
    langsmith_client: Client
    project_name: str
    thread_id: str | None = None
    logger: Optional[ExternalLogger] = None

    def __init__(
        self,
        config: Optional[Config] = None,
        tools: Optional[List[BaseTool]] = None,
        agent_config: Optional[AgentConfig] = None,
        thread_id: Optional[str] = None,
        logger: Optional[ExternalLogger] = None,
        **kwargs,
    ):
        """Initialize a ResearchAgent.

        Args:
            config: Configuration for the agent
            tools: Additional tools to use
            agent_config: Additional agent configuration
            thread_id: Thread ID for message history
            logger: External logger to use
            **kwargs: Additional configuration options
        """
        if config is None:
            config = Config()
        
        super().__init__(config)
        
        self.agent = self._create_research_agent(
            model_provider=config.model_provider,
            model_name=config.model_name,
            memory=config.memory,
            additional_tools=tools,
            config=agent_config,
            **kwargs,
        )
        self.model_name = config.model_name
        self.langsmith_client = Client()

        if thread_id is None:
            self.thread_id = str(uuid4())
        else:
            self.thread_id = thread_id

        # Get project name from environment variable or use a default
        self.project_name = os.environ.get("LANGCHAIN_PROJECT", "EMB")
        print(f"Using LangSmith project: {self.project_name}")

        # Initialize tags for agent trace
        self.tags = [*config.tags, self.model_name]

        # set logger if provided
        self.logger = logger

        # Initialize metadata for agent trace
        self.metadata = {
            "project": self.project_name,
            "model": self.model_name,
            **config.metadata,
        }

    def _create_research_agent(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-latest",
        memory: bool = True,
        additional_tools: Optional[List[BaseTool]] = None,
        config: Optional[AgentConfig] = None,
        **kwargs,
    ) -> CompiledGraph:
        """Create a research agent.
        
        This is a placeholder for the actual implementation that would be in the extensions module.
        
        Args:
            model_provider: The model provider to use
            model_name: The model name to use
            memory: Whether to use memory
            additional_tools: Additional tools to use
            config: Additional agent configuration
            **kwargs: Additional configuration options
            
        Returns:
            A compiled graph for the agent
        """
        # This would be imported from the extensions module in the actual implementation
        from emb.extensions.langchain.agent import create_research_agent
        
        return create_research_agent(
            model_provider=model_provider,
            model_name=model_name,
            memory=memory,
            additional_tools=additional_tools,
            config=config,
            **kwargs,
        )

    def run(self, prompt: str, image_urls: Optional[List[str]] = None) -> str:
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

        config = RunnableConfig(
            configurable={"thread_id": self.thread_id},
            tags=self.tags,
            metadata=self.metadata,
            recursion_limit=200
        )

        stream = self.agent.stream(
            {"messages": [HumanMessage(content=content)]},
            config=config,
            stream_mode="values"
        )

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
            self._find_and_print_langsmith_run_url()
        except Exception as e:
            separator = "=" * 60
            print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
            import traceback

            print(traceback.format_exc())
            print(separator)

        return result

    def _find_and_print_langsmith_run_url(self) -> str | None:
        """Find and print the LangSmith run URL.
        
        This is a placeholder for the actual implementation that would be in the extensions module.
        
        Returns:
            The LangSmith run URL if found, None otherwise
        """
        # This would be imported from the extensions module in the actual implementation
        from emb.extensions.langchain.utils.get_langsmith_url import find_and_print_langsmith_run_url
        
        return find_and_print_langsmith_run_url(self.langsmith_client, self.project_name)

    def get_agent_trace_url(self) -> str | None:
        """Get the URL for the most recent agent run in LangSmith.

        Returns:
            The URL for the run in LangSmith if found, None otherwise
        """
        try:
            return self._find_and_print_langsmith_run_url()
        except Exception as e:
            separator = "=" * 60
            print(f"\n{separator}\nCould not retrieve LangSmith URL: {e}")
            import traceback

            print(traceback.format_exc())
            print(separator)
            return None

    def get_tools(self) -> List[BaseTool]:
        """Get the tools used by the agent.
        
        Returns:
            The tools used by the agent
        """
        return list(self.agent.get_graph().nodes["tools"].data.tools_by_name.values())

    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the agent.
        
        Returns:
            The current state of the agent
        """
        return self.agent.get_state(self.config)