#!/bin/bash
# Script to deploy the codegen_app to Modal with proper Python path setup

# Set up Python path to include both codegen and agentgen
export PYTHONPATH=$PYTHONPATH:~/emb/AgentGen:~/emb/codegen

# Print Python path for debugging
echo "Python path: $PYTHONPATH"

# Deploy with Modal
cd ~/emb/applications/codegen_app
modal deploy app.py

echo "Deployment completed!"