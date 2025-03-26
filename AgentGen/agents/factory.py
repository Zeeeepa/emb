"""
Factory functions for creating different types of agents.
"""
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from agents.chat_agent import ChatAgent
from agents.code_agent import CodeAgent


def create_agent_with_tools(
    codebase: Any,
    tools: List[BaseTool],
    system_message: Optional[SystemMessage] = None,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-opus-20240229",
    temperature: float = 0.2,
    **kwargs
) -> CodeAgent:
    """
    Create a code agent with custom tools.
    
    Args:
        codebase: The codebase to operate on
        tools: List of tools to provide to the agent
        system_message: Optional system message to initialize the agent with
        model_provider: The LLM provider to use (default: "anthropic")
        model_name: The model name to use (default: "claude-3-opus-20240229")
        temperature: The temperature to use for generation (default: 0.2)
        **kwargs: Additional arguments to pass to the CodeAgent constructor
        
    Returns:
        A CodeAgent with the specified tools
    """
    return CodeAgent(
        codebase=codebase,
        tools=tools,
        system_message=system_message,
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )


def create_codebase_agent(
    codebase: Any,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-opus-20240229",
    temperature: float = 0.2,
    system_message: Optional[SystemMessage] = None,
    **kwargs
) -> CodeAgent:
    """
    Create a code agent with default tools for codebase analysis.
    
    Args:
        codebase: The codebase to operate on
        model_provider: The LLM provider to use (default: "anthropic")
        model_name: The model name to use (default: "claude-3-opus-20240229")
        temperature: The temperature to use for generation (default: 0.2)
        system_message: Optional system message to initialize the agent with
        **kwargs: Additional arguments to pass to the CodeAgent constructor
        
    Returns:
        A CodeAgent with default tools for codebase analysis
    """
    # Import here to avoid circular imports
    from agentgen.extensions.langchain.tools import (
        ViewFileTool,
        ListDirectoryTool,
        RipGrepTool,
        SemanticSearchTool,
        RevealSymbolTool,
    )
    
    tools = [
        ViewFileTool(codebase),
        ListDirectoryTool(codebase),
        RipGrepTool(codebase),
        SemanticSearchTool(codebase),
        RevealSymbolTool(codebase),
    ]
    
    return create_agent_with_tools(
        codebase=codebase,
        tools=tools,
        system_message=system_message,
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )


def create_codebase_inspector_agent(
    codebase: Any,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-opus-20240229",
    temperature: float = 0.2,
    system_message: Optional[SystemMessage] = None,
    **kwargs
) -> CodeAgent:
    """
    Create a code agent specialized for code inspection and analysis.
    
    Args:
        codebase: The codebase to operate on
        model_provider: The LLM provider to use (default: "anthropic")
        model_name: The model name to use (default: "claude-3-opus-20240229")
        temperature: The temperature to use for generation (default: 0.2)
        system_message: Optional system message to initialize the agent with
        **kwargs: Additional arguments to pass to the CodeAgent constructor
        
    Returns:
        A CodeAgent specialized for code inspection
    """
    # Import here to avoid circular imports
    from agentgen.extensions.langchain.tools import (
        ViewFileTool,
        ListDirectoryTool,
        RipGrepTool,
        SemanticSearchTool,
        RevealSymbolTool,
    )
    
    tools = [
        ViewFileTool(codebase),
        ListDirectoryTool(codebase),
        RipGrepTool(codebase),
        SemanticSearchTool(codebase),
        RevealSymbolTool(codebase),
    ]
    
    default_system_message = SystemMessage(content="""
    You are an expert code inspector that helps developers understand their code.
    Your goal is to provide deep insights into the codebase structure, dependencies, and patterns.
    Focus on identifying key components, architectural patterns, and potential issues.
    """)
    
    return create_agent_with_tools(
        codebase=codebase,
        tools=tools,
        system_message=system_message or default_system_message,
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )


def create_chat_agent(
    codebase: Any,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-opus-20240229",
    temperature: float = 0.2,
    system_message: Optional[SystemMessage] = None,
    **kwargs
) -> ChatAgent:
    """
    Create a chat agent for conversational interactions.
    
    Args:
        codebase: The codebase to operate on
        model_provider: The LLM provider to use (default: "anthropic")
        model_name: The model name to use (default: "claude-3-opus-20240229")
        temperature: The temperature to use for generation (default: 0.2)
        system_message: Optional system message to initialize the agent with
        **kwargs: Additional arguments to pass to the ChatAgent constructor
        
    Returns:
        A ChatAgent for conversational interactions
    """
    return ChatAgent(
        codebase=codebase,
        system_message=system_message,
        model_provider=model_provider,
        model_name=model_name,
        temperature=temperature,
        **kwargs
    )