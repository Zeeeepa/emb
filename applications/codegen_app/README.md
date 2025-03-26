# Codegen App

A versatile application that integrates with Slack, GitHub, and Linear to provide AI-powered code assistance, repository analysis, PR suggestions, and issue tracking.

## Features

- **Slack Integration**: Respond to mentions with AI-powered code assistance
- **Advanced Intent Recognition**: Automatically detect user intent from natural language requests
- **Repository Analysis**: Analyze repositories and provide comprehensive reports
- **PR Suggestions & Creation**: Generate PR suggestions or create actual PRs with code improvements
- **GitHub PR Reviews**: Automatically review PRs when labeled with a trigger label
- **PR Event Handling**: Welcome new PRs, respond to review requests, and clean up comments
- **Linear Issue Tracking**: Create, update, and track Linear issues with rich formatting
- **Slack Notifications**: Get notified about important events across platforms
- **Error Handling**: Comprehensive error handling with clear feedback
- **Background Processing**: Long-running tasks are processed in the background
- **Status Updates**: Real-time status updates for long-running operations
- **Efficient Repository Management**: Smart caching of repositories for faster analysis
- **Semantic Code Analysis**: Utilizes semantic search and symbol analysis for deeper insights
- **LangGraph Integration**: Robust conversation handling with better state management
- **Advanced Git Operations**: Leverages codegen's git functionality for better repository management

## Environment Variables

Create a `.env` file with the following variables:

```
# GitHub configuration
GITHUB_TOKEN="your_github_token"
TRIGGER_LABEL="analyzer"  # Label that triggers PR reviews

# Modal configuration
MODAL_API_KEY="your_modal_api_key"

# Default repository
DEFAULT_REPO="your_org/your_repo"

# Repository cache directory (optional)
REPO_CACHE_DIR="/tmp/codegen_repos"

# Server configuration
PORT=8000
HOST="0.0.0.0"
LOG_LEVEL="INFO"

# LLM configuration (at least one is required)
ANTHROPIC_API_KEY="your_anthropic_api_key"
OPENAI_API_KEY="your_openai_api_key"

# Slack configuration
SLACK_BOT_TOKEN="your_slack_bot_token"
SLACK_SIGNING_SECRET="your_slack_signing_secret"
SLACK_NOTIFICATION_CHANNEL="your_slack_channel_id"

# Linear configuration
LINEAR_API_KEY="your_linear_api_key"
```

## Installation

### Local Development

Install the required dependencies:

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install packages individually
pip install git+https://github.com/codegen-sh/codegen-sdk.git@6a0e101718c247c01399c60b7abf301278a41786
pip install git+https://github.com/Zeeeepa/AgentGen.git
pip install openai anthropic fastapi[standard] slack_sdk pygithub linear-sdk modal
```

## Run Locally

Spin up the server:

```bash
codegen serve
```

Expose with ngrok for webhook testing:

```bash
ngrok http 8000
```

Configure webhook URLs:

- Slack: `{ngrok_url}/slack/events`
- GitHub: `{ngrok_url}/github/events`
- Linear: `{ngrok_url}/linear/events`

## Deploy to Modal

Deploy as a Modal function:

```bash
# Make sure you have Modal CLI installed
pip install modal

# Deploy the application
modal deploy app.py
```

If you encounter import errors during deployment, ensure that both `codegen` and `agentgen` packages are properly installed in the Modal environment. The app.py file is configured to install these packages during deployment:

```python
# In app.py
base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .pip_install(
        # =====[ Codegen ]=====
        f"git+{REPO_URL}@{COMMIT_ID}",
        # =====[ AgentGen ]=====
        "git+https://github.com/Zeeeepa/AgentGen.git",
        # ... other dependencies
    )
)
```

After deployment, update your webhook URLs to use the Modal endpoints.

## GitHub Webhook Setup

1. Go to your repository settings → Webhooks
2. Add a new webhook with:
   - Payload URL: Your Modal or ngrok URL + `/github/events`
   - Content type: `application/json`
   - Secret: Create a secure random string
   - Events: Select "Pull requests" at minimum

## Linear Webhook Setup

1. Go to your Linear workspace settings → API → Webhooks
2. Add a new webhook with:
   - URL: Your Modal or ngrok URL + `/linear/events`
   - Resource types: Select "Issues" and "Comments" at minimum

## Usage

### Slack Commands

Mention the bot in Slack with different commands. The bot uses advanced intent recognition to understand your requests in natural language.

#### Repository Analysis

```
@codegen-app analyze repo Zeeeepa/emb
@codegen-app analyze the codebase at Zeeeepa/emb
@codegen-app can you analyze the repository structure of Zeeeepa/emb?
@codegen-app examine the codebase of Zeeeepa/emb
@codegen-app explore repo Zeeeepa/emb
```

#### PR Suggestions and Creation

```
# For suggestions only
@codegen-app suggest PR for Zeeeepa/emb
title: Improve error handling
description: Add better error handling to the core modules
files: AgentGen/agents/code_agent.py, AgentGen/extensions/events/github.py

# For actual PR creation
@codegen-app create PR for Zeeeepa/emb
title: Improve error handling
description: Add better error handling to the core modules
files: AgentGen/agents/code_agent.py, AgentGen/extensions/events/github.py

# Natural language requests also work
@codegen-app can you create a PR to fix the error handling in Zeeeepa/emb?
@codegen-app implement better error handling in Zeeeepa/emb
@codegen-app build a feature for improved logging in Zeeeepa/emb
```

The bot will analyze the repository, make the necessary changes, and create a PR with the specified details when using `create PR`. When using `suggest PR`, it will only provide suggestions without creating an actual PR.

#### PR Review

```
@codegen-app review PR #123 in Zeeeepa/emb
@codegen-app can you check PR #45?
@codegen-app evaluate PR #67 in Zeeeepa/emb
@codegen-app give feedback on PR #89
```

#### Linear Issue Creation

```
@codegen-app create issue
title: Implement better error handling
description: We need to improve error handling in the GitHub event handlers
priority: high
assignee: john
labels: bug, enhancement

# Natural language requests also work
@codegen-app can you create a high priority issue for improving error handling?
@codegen-app file a bug report for the login component
@codegen-app add a task to implement the new feature
```

#### General Code Assistance

```
@codegen-app Help me understand how to use the ripgrep tool in codegen
@codegen-app What's the best way to implement error handling in Python?
```

### PR Reviews

1. Open a PR in your repository
2. Add the label specified in `TRIGGER_LABEL` (default: "analyzer")
3. The bot will automatically review the PR and add comments

## Customization

You can customize the prompts for different features by modifying the corresponding handler functions in `app.py`:

- PR reviews: `handle_pr_labeled` and `handle_pr_review`
- Repository analysis: `handle_repo_analysis`
- PR suggestions: `handle_pr_suggestion`
- Linear issue creation: `handle_linear_issue_creation`
- Intent recognition: `detect_intent`

## Architecture

The application uses the following components:

- **CodegenApp**: Core application that handles events from different platforms
- **Intent Recognition**: Enhanced system for detecting user intent from natural language
- **Repository Manager**: Advanced repository management with codegen's git functionality
- **CodeAgent**: AI agent that performs code analysis and generation
- **ChatAgent with LangGraph**: Robust conversation handling with better state management
- **GitHub Tools**: Tools for interacting with GitHub repositories and PRs
- **Linear Tools**: Tools for creating and managing Linear issues
- **Semantic Analysis**: Tools for deeper code understanding (semantic search, symbol analysis)
- **Background Tasks**: Asynchronous task processing for long-running operations

## Recent Enhancements

### 1. Advanced Repository Management

The application now uses `RepoOperator` from the codegen git module for more efficient repository operations:

- Efficient repository caching
- Better branch management
- Improved error handling for git operations

### 2. LangGraph Integration

The application now uses LangGraph for more robust conversation handling:

- Better conversation state management
- Improved error handling and recovery
- More natural conversational experience

### 3. Enhanced Intent Recognition

The application now has a more sophisticated intent recognition system:

- Expanded pattern matching for better natural language understanding
- More detailed parameter extraction
- Better handling of ambiguous requests

### 4. Comprehensive Tool Integration

The application now integrates all available tools from AgentGen:

- Semantic search for better code understanding
- Symbol analysis for deeper code insights
- Advanced code editing capabilities