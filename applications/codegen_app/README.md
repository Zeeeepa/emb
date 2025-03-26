# Codegen App

A versatile application that integrates with Slack, GitHub, and Linear to provide AI-powered code assistance, repository analysis, PR suggestions, and issue tracking.

## Installation

### Prerequisites

- Python 3.10+
- Modal CLI (`pip install modal`)
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/emb.git
   cd emb
   ```

2. Make the installation and deployment scripts executable:
   ```bash
   chmod +x applications/codegen_app/install_dependencies.sh
   chmod +x applications/codegen_app/local_deploy.sh
   ```

3. Install dependencies:
   ```bash
   cd applications/codegen_app
   ./install_dependencies.sh
   ```

4. Deploy the app:
   ```bash
   ./local_deploy.sh
   ```

## Troubleshooting

### ModuleNotFoundError: No module named 'agentgen'

If you encounter this error, it's likely due to a case-sensitivity issue between the directory name `AgentGen` and the package name `agentgen`. The installation script should create a symbolic link to fix this, but if it fails, you can create it manually:

```bash
ln -s ~/emb/AgentGen ~/emb/agentgen
```

Then try deploying again:

```bash
./local_deploy.sh
```

### Other Import Issues

If you're still having import issues, make sure your PYTHONPATH includes both the codegen and agentgen directories:

```bash
export PYTHONPATH=$PYTHONPATH:~/emb/AgentGen:~/emb/codegen:~/emb
```

Then try deploying again.

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
```

## Development

To make changes to the app:

1. Edit the files in `applications/codegen_app/`
2. Run `./local_deploy.sh` to deploy your changes

## License

This project is licensed under the terms of the MIT license.