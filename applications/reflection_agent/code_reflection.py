"""Example application demonstrating code reflection with evaluation.

This application shows how to create and use agents with code-specific reflection capabilities,
allowing them to critique and improve their own code responses with automated evaluation.
"""

import argparse
import os
import re
import tempfile
import subprocess
from typing import Optional, Dict, Any, List, Tuple

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from codegen import Codebase
from agentgen.agents.code_agent import CodeAgent
from agentgen.extensions.langchain.agent import create_codebase_agent
from agentgen.extensions.reflection import create_reflection_enhanced_agent


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a code reflection agent")
    parser.add_argument("--repo", type=str, required=True, help="Repository to analyze (owner/repo)")
    parser.add_argument("--query", type=str, required=True, help="Code-related query to run")
    parser.add_argument(
        "--model-provider",
        type=str,
        choices=["anthropic", "openai"],
        default="anthropic",
        help="Model provider to use",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="claude-3-5-sonnet-latest",
        help="Model name to use",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum number of reflection iterations",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Whether to evaluate the generated code",
    )
    return parser.parse_args()


def extract_python_code(text: str) -> List[Tuple[str, str]]:
    """Extract Python code blocks from text.
    
    Args:
        text: Text containing code blocks
        
    Returns:
        List of tuples (code, language)
    """
    # Pattern to match code blocks with optional language specification
    pattern = r"```(?:python)?\s*([\s\S]*?)```"
    
    # Find all code blocks
    matches = re.findall(pattern, text)
    
    # Return list of (code, language) tuples
    return [(match.strip(), "python") for match in matches]


def evaluate_python_code(code: str) -> Dict[str, Any]:
    """Evaluate Python code for syntax errors and basic execution.
    
    Args:
        code: Python code to evaluate
        
    Returns:
        Dictionary with evaluation results
    """
    # Check for syntax errors
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        return {
            "success": False,
            "error_type": "syntax",
            "error_message": str(e),
            "line_number": e.lineno,
            "offset": e.offset,
        }
    
    # Try to execute the code in a temporary file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(code.encode("utf-8"))
        temp_file_path = temp_file.name
    
    try:
        # Run the code with a timeout
        result = subprocess.run(
            ["python", temp_file_path],
            capture_output=True,
            text=True,
            timeout=5,  # 5 second timeout
        )
        
        # Check for runtime errors
        if result.returncode != 0:
            return {
                "success": False,
                "error_type": "runtime",
                "error_message": result.stderr,
                "stdout": result.stdout,
            }
        
        # Success
        return {
            "success": True,
            "stdout": result.stdout,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error_type": "timeout",
            "error_message": "Code execution timed out after 5 seconds",
        }
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


def create_code_evaluation_reflection_node(
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    temperature: float = 0.2,
    **kwargs
):
    """Create a reflection node that evaluates code and provides feedback.
    
    Args:
        model_provider: The model provider to use
        model_name: The model name to use
        temperature: Temperature for the LLM
        **kwargs: Additional LLM parameters
        
    Returns:
        A callable reflection node function
    """
    from agentgen.extensions.langchain.llm import LLM
    
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

I will provide you with the results of executing the code, which you should use in your evaluation.

If the response meets ALL criteria satisfactorily, set pass to True.

If you find ANY issues with the code, do NOT set pass to True. Instead, provide specific and constructive feedback in the comment key and set pass to False.

Be detailed in your critique so the assistant can understand exactly how to improve the code.
"""

    def code_evaluation_reflection_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Code evaluation reflection node that critiques the agent's code-related response.
        
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
        
        # Extract code from the response
        code_blocks = extract_python_code(last_message.content)
        
        # If no code blocks found, return unchanged state with a reflected flag
        if not code_blocks:
            reflected_message = AIMessage(
                content=last_message.content,
                additional_kwargs={"reflected": True, **last_message.additional_kwargs}
            )
            
            # Replace the last message with the reflected message
            new_messages = messages[:-1] + [reflected_message]
            
            # Decrement remaining steps
            remaining_steps = state.get("remaining_steps", 0) - 1
            
            return {"messages": new_messages, "remaining_steps": remaining_steps}
        
        # Evaluate each code block
        evaluation_results = []
        for code, language in code_blocks:
            if language == "python":
                result = evaluate_python_code(code)
                evaluation_results.append(result)
        
        # Create a reflection prompt with evaluation results
        reflection_prompt = f"""Please evaluate the following AI response to a code-related query:

User Query: {user_query}

AI Response: {last_message.content}

Code Evaluation Results:
"""
        
        for i, result in enumerate(evaluation_results):
            reflection_prompt += f"\nCode Block {i+1}:\n"
            if result["success"]:
                reflection_prompt += f"- Status: Success\n"
                reflection_prompt += f"- Output: {result.get('stdout', '(No output)')}\n"
            else:
                reflection_prompt += f"- Status: Failed\n"
                reflection_prompt += f"- Error Type: {result.get('error_type', 'Unknown')}\n"
                reflection_prompt += f"- Error Message: {result.get('error_message', 'Unknown error')}\n"
                if "line_number" in result:
                    reflection_prompt += f"- Line Number: {result['line_number']}\n"
        
        reflection_prompt += """
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
            content=f"Please improve your code based on this feedback and evaluation results:\n\n{reflection_content}"
        )
        
        # Add the feedback message to the messages
        new_messages = messages + [feedback_message]
        
        # Decrement remaining steps
        remaining_steps = state.get("remaining_steps", 0) - 1
        
        return {"messages": new_messages, "remaining_steps": remaining_steps}
    
    return code_evaluation_reflection_node


def run_code_reflection_agent(
    repo: str,
    query: str,
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    max_iterations: int = 3,
    evaluate: bool = True,
):
    """Run a code reflection agent on a repository.
    
    Args:
        repo: Repository to analyze (owner/repo)
        query: Query to run
        model_provider: Model provider to use
        model_name: Model name to use
        max_iterations: Maximum number of reflection iterations
        evaluate: Whether to evaluate the generated code
    """
    print(f"Loading codebase: {repo}")
    codebase = Codebase.from_repo(repo)
    
    print(f"Creating agent with code reflection")
    
    # Create the base agent graph
    base_agent_graph = create_codebase_agent(
        codebase=codebase,
        model_provider=model_provider,
        model_name=model_name,
        memory=True,
    )
    
    # Create the reflection-enhanced agent
    if evaluate:
        # Create a custom reflection node with code evaluation
        from agentgen.extensions.reflection.reflection_graph import (
            MessagesWithSteps,
            create_reflection_graph,
        )
        from langgraph.graph import END, START, StateGraph
        
        # Create a reflection node with code evaluation
        reflection_node = create_code_evaluation_reflection_node(
            model_provider=model_provider,
            model_name=model_name,
        )
        
        # Create a simple reflection graph
        reflection_graph = StateGraph(MessagesWithSteps)
        reflection_graph.add_node("reflect", reflection_node)
        reflection_graph.add_edge(START, "reflect")
        reflection_graph.add_edge("reflect", END)
        compiled_reflection = reflection_graph.compile()
        
        # Create the reflection-enhanced graph
        reflection_agent_graph = create_reflection_graph(
            agent_graph=base_agent_graph,
            reflection_graph=compiled_reflection,
            max_reflection_iterations=max_iterations,
        ).compile()
    else:
        # Use the standard code reflection
        reflection_agent_graph = create_reflection_enhanced_agent(
            agent_graph=base_agent_graph,
            reflection_type="code",
            model_provider=model_provider,
            model_name=model_name,
            max_reflection_iterations=max_iterations,
        )
    
    print(f"Running query: {query}")
    
    # Run the agent
    result = reflection_agent_graph.invoke({"messages": [], "query": query})
    
    # Print the final answer
    print("\nFinal Answer:")
    print("=" * 80)
    print(result["final_answer"])
    print("=" * 80)
    
    # Print reflection statistics
    reflection_count = 0
    for message in result["messages"]:
        if hasattr(message, "additional_kwargs") and message.additional_kwargs.get("reflected"):
            reflection_count += 1
    
    print(f"\nReflection Statistics:")
    print(f"- Total reflection iterations: {reflection_count}")
    print(f"- Maximum allowed iterations: {max_iterations}")
    
    return result["final_answer"]


def main():
    """Main entry point."""
    args = parse_args()
    run_code_reflection_agent(
        repo=args.repo,
        query=args.query,
        model_provider=args.model_provider,
        model_name=args.model_name,
        max_iterations=args.max_iterations,
        evaluate=args.evaluate,
    )


if __name__ == "__main__":
    main()