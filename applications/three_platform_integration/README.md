# Three-Platform Integration System

This application implements a complete CI/CD cycle using three integrated platforms:

1. **Linear** - Planning and project management
2. **Slack** - Communication and code generation requests
3. **GitHub** - Code repository and PR management

## Architecture

The system consists of three main components:

1. **Planning Agent** - Manages Linear plans, evaluates progress, and determines next steps
2. **Code Generation Agent** - Receives requests via Slack and generates code/PRs
3. **Code Analysis Agent** - Analyzes PRs, provides feedback, and handles merging

## Flow

1. Planning Agent creates and manages project plans in Linear
2. When a step is ready for implementation, Planning Agent sends a request to Slack
3. Code Generation Agent receives the request and creates a PR with implementation
4. Code Analysis Agent reviews the PR and provides feedback
5. If PR is approved, it's merged automatically
6. Planning Agent evaluates progress and determines the next step
7. The cycle continues

## Setup

1. Set up environment variables in `.env` file (see `.env.template`)
2. Deploy the three components using Modal
3. Configure webhooks for GitHub, Slack, and Linear

## Usage

The system operates autonomously once set up, but you can also interact with it:

- Use Slack commands to request specific actions
- Create Linear issues to add new tasks to the plan
- Open PRs manually to trigger code analysis

## Components

- `planning_agent.py` - Linear integration and planning logic
- `code_generation_agent.py` - Slack integration and code generation
- `code_analysis_agent.py` - GitHub integration and PR analysis
- `app.py` - Main application that ties everything together