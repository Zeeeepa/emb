"""Conversation buffer window memory integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os

from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, get_buffer_string


class ConversationBufferWindowMemory(BaseMemory):
    """Wrapper for Langchain's conversation buffer window memory."""
    
    def __init__(
        self,
        memory_key: str = "history",
        k: int = 5,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        return_messages: bool = False,
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
    ):
        """Initialize the ConversationBufferWindowMemory.
        
        Args:
            memory_key: Key to use for the memory in the chain
            k: Number of conversation turns to keep in memory
            input_key: Key to use for the input in the chain
            output_key: Key to use for the output in the chain
            return_messages: Whether to return the messages directly
            human_prefix: Prefix for human messages
            ai_prefix: Prefix for AI messages
        """
        super().__init__()
        self.memory_key = memory_key
        self.k = k
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.human_prefix = human_prefix
        self.ai_prefix = ai_prefix
        self.chat_memory = []
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables.
        
        Args:
            inputs: Input values
            
        Returns:
            Dictionary with memory variables
        """
        # Get the window of the most recent k conversation turns
        window_chat_memory = self.chat_memory[-2 * self.k:] if self.chat_memory else []
        
        if self.return_messages:
            return {self.memory_key: window_chat_memory}
        else:
            return {self.memory_key: get_buffer_string(
                window_chat_memory,
                human_prefix=self.human_prefix,
                ai_prefix=self.ai_prefix,
            )}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save context from this conversation turn.
        
        Args:
            inputs: Input values
            outputs: Output values
        """
        # Get input and output keys
        input_key = self.input_key if self.input_key is not None else list(inputs.keys())[0]
        output_key = self.output_key if self.output_key is not None else list(outputs.keys())[0]
        
        # Save the context
        from langchain_core.messages import HumanMessage, AIMessage
        
        self.chat_memory.append(HumanMessage(content=inputs[input_key]))
        self.chat_memory.append(AIMessage(content=outputs[output_key]))
    
    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory = []