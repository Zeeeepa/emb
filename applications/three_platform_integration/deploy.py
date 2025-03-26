"""
Deployment script for the Three-Platform Integration System.

This script deploys all components of the system:
1. Planning Agent
2. Code Generation Agent
3. Code Analysis Agent
4. Main Application
"""

import os
import subprocess
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def deploy_component(component_name: str, module_path: str):
    """
    Deploy a component using Modal.
    
    Args:
        component_name: Name of the component
        module_path: Path to the module to deploy
    """
    logger.info(f"Deploying {component_name}...")
    
    try:
        result = subprocess.run(
            ["modal", "deploy", module_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Successfully deployed {component_name}")
        logger.debug(result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to deploy {component_name}: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        
        return False

def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy the Three-Platform Integration System")
    parser.add_argument("--component", choices=["all", "planning", "code-generation", "code-analysis", "main"], 
                        default="all", help="Component to deploy (default: all)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        logger.warning("No .env file found. Make sure environment variables are set.")
    
    # Deploy components based on argument
    if args.component in ["all", "planning"]:
        deploy_component("Planning Agent", "planning_agent.py")
    
    if args.component in ["all", "code-generation"]:
        deploy_component("Code Generation Agent", "code_generation_agent.py")
    
    if args.component in ["all", "code-analysis"]:
        deploy_component("Code Analysis Agent", "code_analysis_agent.py")
    
    if args.component in ["all", "main"]:
        deploy_component("Main Application", "app.py")
    
    logger.info("Deployment completed")

if __name__ == "__main__":
    main()