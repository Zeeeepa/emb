import os
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage, HumanMessage
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


class PlanAgent:
    """Agent for planning and breaking down complex tasks into actionable steps."""

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
        """Initialize a PlanAgent.

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
        
        # Default planning tools
        default_tools = []
        if tools:
            default_tools.extend(tools)
            
        # Create the agent with planning-specific tools
        from langchain_core.messages import SystemMessage
        
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
        """Get the default system message for the planning agent."""
        return """
        You are an expert planning agent specialized in breaking down complex tasks into clear, actionable steps.
        
        Your primary responsibilities are:
        
        1. Task Analysis:
           - Analyze complex requests to identify key components and dependencies
           - Break down large tasks into smaller, manageable subtasks
           - Identify potential challenges and dependencies between tasks
        
        2. Plan Creation:
           - Create structured, sequential plans with clear steps
           - Prioritize tasks based on dependencies and importance
           - Estimate effort and complexity for each step
           - Identify critical path items and potential bottlenecks
        
        3. Resource Allocation:
           - Suggest appropriate tools and approaches for each step
           - Identify when specialized knowledge or skills are needed
           - Recommend parallel work streams when possible
        
        4. Plan Refinement:
           - Adjust plans based on feedback and new information
           - Identify and address gaps in the initial plan
           - Provide alternatives when original approaches face obstacles
        
        When creating plans:
        - Be specific and concrete about each step
        - Include clear success criteria for each task
        - Consider edge cases and potential failure points
        - Provide context on why each step is necessary
        - Structure your response with clear headings and numbered steps
        
        Your goal is to transform complex, ambiguous requests into clear, executable plans that can be followed systematically.
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

    def create_plan(self, task_description: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Create a structured plan for a complex task.

        Args:
            task_description: Description of the task to plan
            context: Optional additional context about the task

        Returns:
            A dictionary containing the structured plan
        """
        prompt = f"Create a detailed plan for the following task:\n\n{task_description}"
        
        if context:
            prompt += f"\n\nAdditional context:\n{context}"
            
        response = self.run(prompt)
        
        # Here you could add parsing logic to convert the response into a structured format
        # For now, we'll return the raw response
        return {"plan": response}

    def refine_plan(self, original_plan: str, feedback: str) -> str:
        """Refine an existing plan based on feedback.

        Args:
            original_plan: The original plan to refine
            feedback: Feedback to incorporate into the plan

        Returns:
            The refined plan
        """
        prompt = f"""
        Here is an existing plan:
        
        {original_plan}
        
        Please refine this plan based on the following feedback:
        
        {feedback}
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