#!/bin/bash
# Script to install all required dependencies for the codegen_app

# Install codegen and agentgen packages
pip install -e ~/emb/AgentGen
pip install git+https://github.com/codegen-sh/codegen-sdk.git@6a0e101718c247c01399c60b7abf301278a41786

# Install other dependencies from requirements.txt
pip install -r requirements.txt

echo "All dependencies installed successfully!"