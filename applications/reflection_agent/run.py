"""Example application demonstrating the use of reflection-enhanced agents.

This application shows how to create and use agents with self-reflection capabilities,
allowing them to critique and improve their own responses.
"""

import argparse
import os
from typing import Optional

from langchain_core.messages import SystemMessage

from codegen import Codebase
from agentgen.agents.code_agent import CodeAgent
from agentgen.extensions.langchain.agent import create_codebase_agent
from agentgen.extensions.reflection import create_reflection_enhanced_agent


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a reflection-enhanced agent")
    parser.add_argument("--repo", type=str, required=True, help="Repository to analyze (owner/repo)")
    parser.add_argument("--query", type=str, required=True, help="Query to run")
    parser.add_argument(
        "--reflection-type",
        type=str,
        choices=["general", "code"],
        default="general",
        help="Type of reflection to use",
    )
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
    return parser.parse_args()


def run_reflection_agent(
    repo: str,
    query: str,
    reflection_type: str = "general",
    model_provider: str = "anthropic",
    model_name: str = "claude-3-5-sonnet-latest",
    max_iterations: int = 3,
):
    """Run a reflection-enhanced agent on a repository.
    
    Args:
        repo: Repository to analyze (owner/repo)
        query: Query to run
        reflection_type: Type of reflection to use
        model_provider: Model provider to use
        model_name: Model name to use
        max_iterations: Maximum number of reflection iterations
    """
    print(f"Loading codebase: {repo}")
    codebase = Codebase.from_repo(repo)
    
    print(f"Creating agent with {reflection_type} reflection")
    
    # Create the base agent graph
    base_agent_graph = create_codebase_agent(
        codebase=codebase,
        model_provider=model_provider,
        model_name=model_name,
        memory=True,
    )
    
    # Create the reflection-enhanced agent
    reflection_agent_graph = create_reflection_enhanced_agent(
        agent_graph=base_agent_graph,
        reflection_type=reflection_type,
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
    run_reflection_agent(
        repo=args.repo,
        query=args.query,
        reflection_type=args.reflection_type,
        model_provider=args.model_provider,
        model_name=args.model_name,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    main()