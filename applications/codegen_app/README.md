# Codegen App

A versatile application that integrates with Slack, GitHub, and Linear to provide AI-powered code assistance, repository analysis, PR suggestions, and issue tracking.

## Features

- **Slack Integration**: Respond to mentions with AI-powered code assistance
- **Repository Analysis**: Analyze repositories and provide comprehensive reports
- **PR Suggestions**: Generate PR suggestions with specific code improvements
- **GitHub PR Reviews**: Automatically review PRs when labeled with a trigger label
- **PR Event Handling**: Welcome new PRs, respond to review requests, and clean up comments
- **Linear Issue Tracking**: Create, update, and track Linear issues
- **Slack Notifications**: Get notified about important events across platforms

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
modal deploy app.py
```

Then update your webhook URLs to use the Modal endpoints.

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

Mention the bot in Slack with different commands:

#### Repository Analysis

```
@codegen-app analyze repo Zeeeepa/emb
```

#### PR Suggestions

```
@codegen-app suggest PR for Zeeeepa/emb
title: Improve error handling
description: Add better error handling to the core modules
files: AgentGen/agents/code_agent.py, AgentGen/extensions/events/github.py
```

#### Linear Issue Creation

```
@codegen-app create issue
title: Implement better error handling
description: We need to improve error handling in the GitHub event handlers
priority: high
```

#### General Code Assistance

```
@codegen-app Help me understand how to use the ripgrep tool in codegen
```

### PR Reviews

1. Open a PR in your repository
2. Add the label specified in `TRIGGER_LABEL` (default: "analyzer")
3. The bot will automatically review the PR and add comments

## Customization

You can customize the prompts for different features by modifying the corresponding handler functions in `app.py`:

- PR reviews: `handle_pr_labeled`
- Repository analysis: `handle_repo_analysis`
- PR suggestions: `handle_pr_suggestion`
- Linear issue creation: `handle_linear_issue_creation`

## Architecture

The application uses the following components:

- **CodegenApp**: Core application that handles events from different platforms
- **CodeAgent**: AI agent that performs code analysis and generation
- **GitHub Tools**: Tools for interacting with GitHub repositories and PRs
- **Linear Tools**: Tools for creating and managing Linear issues
- **Background Tasks**: Asynchronous task processing for long-running operations
