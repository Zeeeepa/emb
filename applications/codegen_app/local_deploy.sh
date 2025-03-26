#!/bin/bash
# Script to deploy the codegen_app locally for testing

# Set up Python path to include both codegen and agentgen
export PYTHONPATH=$PYTHONPATH:~/emb/AgentGen:~/emb/codegen

# Deploy with Modal
cd ~/emb/applications/codegen_app
modal deploy app.py

echo "Deployment completed!"