"""Conversation summary memory integration for Langchain."""

from typing import List, Optional, Dict, Any, Union, Callable
import os

from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, get_buffer_string
from langchain_core.language_models import BaseLanguageModel


class ConversationSummaryMemory(BaseMemory):
    """Wrapper for Langchain's conversation summary memory."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        memory_key: str = "history",
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
        return_messages: bool = False,
        human_prefix: str = "Human",
        ai_prefix: str = "AI",
        prompt_template: Optional[str] = None,
        summarize_step: int = 2,
    ):
        """Initialize the ConversationSummaryMemory.
        
        Args:
            llm: Language model to use for summarization
            memory_key: Key to use for the memory in the chain
            input_key: Key to use for the input in the chain
            output_key: Key to use for the output in the chain
            return_messages: Whether to return the messages directly
            human_prefix: Prefix for human messages
            ai_prefix: Prefix for AI messages
            prompt_template: Optional custom prompt template for summarization
            summarize_step: Number of conversation turns before summarizing
        """
        super().__init__()
        self.llm = llm
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.human_prefix = human_prefix
        self.ai_prefix = ai_prefix
        self.prompt_template = prompt_template
        self.summarize_step = summarize_step
        
        self.chat_memory = []
        self.current_summary = ""
        self.turn_count = 0
        
        # Set default prompt template if not provided
        if not self.prompt_template:
            self.prompt_template = """Progressively summarize the lines of conversation provided, adding onto the previous summary returning a new summary.

EXAMPLE
Current summary:
The human asks what the AI thinks of artificial intelligence. The AI thinks artificial intelligence is a force for good.

New lines of conversation:
Human: Why do you think artificial intelligence is a force for good?
AI: I think artificial intelligence is a force for good because it can help us solve many challenging problems such as climate change and disease.

New summary:
The human asks what the AI thinks of artificial intelligence. The AI thinks artificial intelligence is a force for good because it can help solve challenging problems such as climate change and disease.
END OF EXAMPLE

Current summary:
{summary}

New lines of conversation:
{new_lines}

New summary:"""
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables.
        
        Args:
            inputs: Input values
            
        Returns:
            Dictionary with memory variables
        """
        if self.return_messages:
            return {self.memory_key: self.chat_memory}
        else:
            if self.current_summary:
                return {self.memory_key: self.current_summary}
            else:
                return {self.memory_key: get_buffer_string(
                    self.chat_memory,
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
        
        # Increment turn count
        self.turn_count += 1
        
        # Check if we need to summarize
        if self.turn_count >= self.summarize_step:
            self._summarize()
            self.turn_count = 0
    
    def _summarize(self) -> None:
        """Summarize the conversation."""
        # Get the buffer string of the conversation
        buffer = get_buffer_string(
            self.chat_memory,
            human_prefix=self.human_prefix,
            ai_prefix=self.ai_prefix,
        )
        
        # Prepare the prompt
        prompt = self.prompt_template.format(
            summary=self.current_summary if self.current_summary else "None",
            new_lines=buffer,
        )
        
        # Generate the summary
        self.current_summary = self.llm.invoke(prompt).content
        
        # Clear the chat memory since it's now summarized
        self.chat_memory = []
    
    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory = []
        self.current_summary = ""
        self.turn_count = 0