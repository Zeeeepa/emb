"""Enhanced reflection capabilities for AgentGen using LangGraph-style reflection.

This module provides a framework for creating agents with self-reflection capabilities,
allowing them to critique and improve their own responses through a reflection process.
"""

from typing import Any, Callable, Dict, Literal, Optional, Type, Union
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledGraph
from langgraph.managed import RemainingSteps
from langgraph.checkpoint.memory import MemorySaver

from agentgen.agents.utils import AgentConfig
from agentgen.extensions.langchain.llm import LLM
from agentgen.extensions.tools.reflection import perform_reflection, ReflectionObservation


class MessagesWithSteps(dict):
    """State class for reflection graph with remaining steps tracking."""
    
    messages: list
    remaining_steps: RemainingSteps


def end_or_reflect(state: MessagesWithSteps) -> Literal[END, "agent", "reflection"]:
    """Decide whether to end, continue with the agent, or reflect.
    
    Args:
        state: Current state with messages and remaining steps
        
    Returns:
        Next node to route to or END
    """
    # End if we're out of steps
    if state["remaining_steps"] < 2:
        return END
        
    # End if there are no messages
    if len(state["messages"]) == 0:
        return END
        
    # Get the last message
    last_message = state["messages"][-1]
    
    # If the last message is from a human, route to the agent
    if isinstance(last_message, HumanMessage):
        return "agent"
    # If the last message is from the AI and has a reflection flag, route to reflection
    elif isinstance(last_message, AIMessage) and not last_message.additional_kwargs.get("reflected", False):
        return "reflection"
    # Otherwise end
    else:
        return END


def create_reflection_graph(
    agent_graph: CompiledGraph,
    reflection_graph: CompiledGraph,
    state_schema: Optional[Type[Any]] = None,
    config_schema: Optional[Type[Any]] = None,
    max_reflection_iterations: int = 3,
) -> StateGraph:
    """Create a reflection-enhanced graph that combines an agent with a reflection process.
    
    Args:
        agent_graph: The main agent graph that generates responses
        reflection_graph: The reflection graph that critiques responses
        state_schema: Optional schema for the state
        config_schema: Optional schema for configuration
        max_reflection_iterations: Maximum number of reflection iterations
        
    Returns:
        A compiled StateGraph with reflection capabilities
    """
    # Use MessagesWithSteps as the state schema if none provided
    if state_schema is None:
        state_schema = MessagesWithSteps
    
    # Create the reflection-enhanced graph
    rgraph = StateGraph(state_schema, config_schema=config_schema)
    
    # Add the agent and reflection nodes
    rgraph.add_node("agent", agent_graph)
    rgraph.add_node("reflection", reflection_graph)
    
    # Add edges
    rgraph.add_edge(START, "agent")
    rgraph.add_edge("agent", "reflection")
    rgraph.add_conditional_edges("reflection", end_or_reflect)
    
    # Set the initial state with remaining steps
    def set_initial_state(state: Dict[str, Any]) -> Dict[str, Any]:
        """Set the initial state with remaining steps."""
        state["remaining_steps"] = max_reflection_iterations
        return state
    
    rgraph.set_entry_point(set_initial_state)
    
    return rgraph


def create_llm_reflection_node(
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    temperature: float = 0.2,
    **kwargs
) -> Callable:
    """Create a reflection node that uses an LLM to critique agent responses.
    
    Args:
        model_provider: The model provider to use
        model_name: The model name to use
        temperature: Temperature for the LLM
        **kwargs: Additional LLM parameters
        
    Returns:
        A callable reflection node function
    """
    # Initialize the LLM
    llm = LLM(
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )
    
    # Define the reflection system prompt
    reflection_system_prompt = """You are an expert judge evaluating AI responses. Your task is to critique the AI assistant's latest response in the conversation below.

Evaluate the response based on these criteria:
1. Accuracy - Is the information correct and factual?
2. Completeness - Does it fully address the user's query?
3. Clarity - Is the explanation clear and well-structured?
4. Helpfulness - Does it provide actionable and useful information?
5. Safety - Does it avoid harmful or inappropriate content?

If the response meets ALL criteria satisfactorily, set pass to True.

If you find ANY issues with the response, do NOT set pass to True. Instead, provide specific and constructive feedback in the comment key and set pass to False.

Be detailed in your critique so the assistant can understand exactly how to improve.
"""

    def reflection_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Reflection node that critiques the agent's response.
        
        Args:
            state: Current state with messages
            
        Returns:
            Updated state with reflection results
        """
        # Get the messages
        messages = state["messages"]
        
        # If there are no messages, return unchanged state
        if not messages:
            return state
            
        # Get the last message (which should be from the AI)
        last_message = messages[-1]
        
        # If the last message is not from the AI, return unchanged state
        if not isinstance(last_message, AIMessage):
            return state
            
        # Get the user's query (the message before the AI response)
        user_query = ""
        for i in range(len(messages) - 2, -1, -1):
            if isinstance(messages[i], HumanMessage):
                user_query = messages[i].content
                break
                
        # If we couldn't find a user query, use a default
        if not user_query:
            user_query = "Unknown query"
            
        # Create a reflection prompt
        reflection_prompt = f"""Please evaluate the following AI response to a user query:

User Query: {user_query}

AI Response: {last_message.content}

Evaluate this response based on accuracy, completeness, clarity, helpfulness, and safety.
If the response is satisfactory, respond with "PASS: The response is satisfactory."
If the response needs improvement, provide specific feedback on how to improve it.
"""

        # Get the reflection result
        reflection_message = SystemMessage(content=reflection_system_prompt)
        reflection_query = HumanMessage(content=reflection_prompt)
        reflection_result = llm.invoke([reflection_message, reflection_query])
        
        # Check if the reflection passed
        reflection_content = reflection_result.content
        passed = "PASS:" in reflection_content or "pass: true" in reflection_content.lower()
        
        # If the reflection passed, mark the message as reflected and return
        if passed:
            # Create a copy of the last message with the reflected flag
            reflected_message = AIMessage(
                content=last_message.content,
                additional_kwargs={"reflected": True, **last_message.additional_kwargs}
            )
            
            # Replace the last message with the reflected message
            new_messages = messages[:-1] + [reflected_message]
            
            # Decrement remaining steps
            remaining_steps = state.get("remaining_steps", 0) - 1
            
            return {"messages": new_messages, "remaining_steps": remaining_steps}
        
        # If the reflection didn't pass, add a new user message with the feedback
        feedback_message = HumanMessage(
            content=f"Please improve your previous response based on this feedback: {reflection_content}"
        )
        
        # Add the feedback message to the messages
        new_messages = messages + [feedback_message]
        
        # Decrement remaining steps
        remaining_steps = state.get("remaining_steps", 0) - 1
        
        return {"messages": new_messages, "remaining_steps": remaining_steps}
    
    return reflection_node


def create_code_reflection_node(
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    temperature: float = 0.2,
    **kwargs
) -> Callable:
    """Create a reflection node specifically for code-related responses.
    
    Args:
        model_provider: The model provider to use
        model_name: The model name to use
        temperature: Temperature for the LLM
        **kwargs: Additional LLM parameters
        
    Returns:
        A callable reflection node function
    """
    # Initialize the LLM
    llm = LLM(
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )
    
    # Define the code reflection system prompt
    code_reflection_system_prompt = """You are an expert software engineer evaluating code-related responses. Your task is to critique the AI assistant's latest response in the conversation below.

Evaluate the code response based on these criteria:
1. Correctness - Is the code syntactically correct and free of bugs?
2. Efficiency - Does the code use efficient algorithms and data structures?
3. Readability - Is the code well-structured and easy to understand?
4. Best Practices - Does the code follow language-specific best practices?
5. Completeness - Does it fully address the user's requirements?

If the response meets ALL criteria satisfactorily, set pass to True.

If you find ANY issues with the code, do NOT set pass to True. Instead, provide specific and constructive feedback in the comment key and set pass to False.

Be detailed in your critique so the assistant can understand exactly how to improve the code.
"""

    def code_reflection_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Code reflection node that critiques the agent's code-related response.
        
        Args:
            state: Current state with messages
            
        Returns:
            Updated state with reflection results
        """
        # Get the messages
        messages = state["messages"]
        
        # If there are no messages, return unchanged state
        if not messages:
            return state
            
        # Get the last message (which should be from the AI)
        last_message = messages[-1]
        
        # If the last message is not from the AI, return unchanged state
        if not isinstance(last_message, AIMessage):
            return state
            
        # Get the user's query (the message before the AI response)
        user_query = ""
        for i in range(len(messages) - 2, -1, -1):
            if isinstance(messages[i], HumanMessage):
                user_query = messages[i].content
                break
                
        # If we couldn't find a user query, use a default
        if not user_query:
            user_query = "Unknown code request"
            
        # Create a reflection prompt
        reflection_prompt = f"""Please evaluate the following AI response to a code-related query:

User Query: {user_query}

AI Response: {last_message.content}

Evaluate this code response based on correctness, efficiency, readability, best practices, and completeness.
If the code is satisfactory, respond with "PASS: The code is satisfactory."
If the code needs improvement, provide specific feedback on how to improve it.
"""

        # Get the reflection result
        reflection_message = SystemMessage(content=code_reflection_system_prompt)
        reflection_query = HumanMessage(content=reflection_prompt)
        reflection_result = llm.invoke([reflection_message, reflection_query])
        
        # Check if the reflection passed
        reflection_content = reflection_result.content
        passed = "PASS:" in reflection_content or "pass: true" in reflection_content.lower()
        
        # If the reflection passed, mark the message as reflected and return
        if passed:
            # Create a copy of the last message with the reflected flag
            reflected_message = AIMessage(
                content=last_message.content,
                additional_kwargs={"reflected": True, **last_message.additional_kwargs}
            )
            
            # Replace the last message with the reflected message
            new_messages = messages[:-1] + [reflected_message]
            
            # Decrement remaining steps
            remaining_steps = state.get("remaining_steps", 0) - 1
            
            return {"messages": new_messages, "remaining_steps": remaining_steps}
        
        # If the reflection didn't pass, add a new user message with the feedback
        feedback_message = HumanMessage(
            content=f"Please improve your code based on this feedback: {reflection_content}"
        )
        
        # Add the feedback message to the messages
        new_messages = messages + [feedback_message]
        
        # Decrement remaining steps
        remaining_steps = state.get("remaining_steps", 0) - 1
        
        return {"messages": new_messages, "remaining_steps": remaining_steps}
    
    return code_reflection_node


def create_reflection_enhanced_agent(
    agent_graph: CompiledGraph,
    reflection_type: str = "general",
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    max_reflection_iterations: int = 3,
    **kwargs
) -> CompiledGraph:
    """Create a reflection-enhanced agent that can self-critique and improve.
    
    Args:
        agent_graph: The main agent graph
        reflection_type: Type of reflection to use ("general", "code", or "custom")
        model_provider: The model provider to use for reflection
        model_name: The model name to use for reflection
        max_reflection_iterations: Maximum number of reflection iterations
        **kwargs: Additional parameters for the reflection LLM
        
    Returns:
        A compiled graph with reflection capabilities
    """
    # Create the appropriate reflection node based on the type
    if reflection_type == "code":
        reflection_node = create_code_reflection_node(
            model_provider=model_provider,
            model_name=model_name,
            **kwargs
        )
    else:  # Default to general reflection
        reflection_node = create_llm_reflection_node(
            model_provider=model_provider,
            model_name=model_name,
            **kwargs
        )
    
    # Create a simple reflection graph
    reflection_graph = StateGraph(MessagesWithSteps)
    reflection_graph.add_node("reflect", reflection_node)
    reflection_graph.add_edge(START, "reflect")
    reflection_graph.add_edge("reflect", END)
    compiled_reflection = reflection_graph.compile()
    
    # Create and return the reflection-enhanced graph
    return create_reflection_graph(
        agent_graph=agent_graph,
        reflection_graph=compiled_reflection,
        max_reflection_iterations=max_reflection_iterations
    ).compile()