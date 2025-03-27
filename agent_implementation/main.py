"""Main entry point for running the agent implementations."""
import argparse
import os
import sys

from codegen.sdk.core.codebase import Codebase
from codegen.shared.enums.programming_language import ProgrammingLanguage

from agent_implementation.sdk_expert_agent import create_sdk_expert_agent
from agent_implementation.codebase_inspector import run_mcp_server

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run Codegen agent implementations")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # SDK Expert Agent
    sdk_parser = subparsers.add_parser("sdk-expert", help="Run the SDK Expert Agent")
    sdk_parser.add_argument("--codebase-path", required=True, help="Path to the codebase")
    sdk_parser.add_argument("--language", default="python", choices=["python", "typescript", "javascript", "java", "go"], 
                           help="Programming language of the codebase")
    sdk_parser.add_argument("--model-name", default="claude-3-5-sonnet-latest", help="Name of the model to use")
    sdk_parser.add_argument("--model-provider", default="anthropic", help="Provider of the model to use")
    sdk_parser.add_argument("--no-memory", action="store_true", help="Disable memory for the agent")
    sdk_parser.add_argument("--no-debug", action="store_true", help="Disable debug output")
    
    # MCP Server
    mcp_parser = subparsers.add_parser("mcp-server", help="Run the MCP Server for codebase inspection")
    
    return parser.parse_args()

def run_sdk_expert_agent(args):
    """Run the SDK Expert Agent."""
    # Validate codebase path
    if not os.path.exists(args.codebase_path):
        print(f"Error: Codebase path '{args.codebase_path}' does not exist.")
        sys.exit(1)
    
    # Map language string to ProgrammingLanguage enum
    language_map = {
        "python": ProgrammingLanguage.PYTHON,
        "typescript": ProgrammingLanguage.TYPESCRIPT,
        "javascript": ProgrammingLanguage.JAVASCRIPT,
        "java": ProgrammingLanguage.JAVA,
        "go": ProgrammingLanguage.GO,
    }
    
    language = language_map.get(args.language)
    if language is None:
        print(f"Error: Unsupported language '{args.language}'.")
        sys.exit(1)
    
    try:
        # Initialize codebase
        codebase = Codebase(repo_path=args.codebase_path, language=language)
        
        # Create agent
        agent = create_sdk_expert_agent(
            codebase=codebase,
            model_name=args.model_name,
            model_provider=args.model_provider,
            memory=not args.no_memory,
            debug=not args.no_debug,
        )
        
        # Start interactive session
        print(f"SDK Expert Agent initialized for {args.language} codebase at {args.codebase_path}")
        print("Type 'exit' to quit.")
        
        while True:
            user_input = input("\nQuestion: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # Invoke agent
            result = agent.invoke({"input": user_input})
            print("\nResponse:", result["output"])
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == "sdk-expert":
        run_sdk_expert_agent(args)
    elif args.command == "mcp-server":
        run_mcp_server()
    else:
        print("Error: No command specified. Use --help for usage information.")
        sys.exit(1)

if __name__ == "__main__":
    main()