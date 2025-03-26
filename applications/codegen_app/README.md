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
pip install git+https://github.com/Zeeeepa/emb.git#subdirectory=AgentGen
pip install openai anthropic fastapi[standard] slack_sdk pygithub modal
```

For development with local packages:

```bash
# Make the install script executable
chmod +x install_dependencies.sh

# Run the install script
./install_dependencies.sh
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

# Deploy the application using the deployment script
chmod +x deploy_modal.sh
./deploy_modal.sh
```

The deployment script sets up the proper Python path to include both `codegen` and `agentgen` packages, which is necessary for the Modal deployment to work correctly.

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
        "git+https://github.com/Zeeeepa/emb.git#subdirectory=AgentGen",
        # ... other dependencies
    )
    .run_function(
        # This function runs during image build to ensure agentgen is properly installed
        lambda: (
            print("Verifying agentgen installation..."),
            __import__('sys').path.append('/root'),  # Add root to Python path
            print("Python path:", __import__('sys').path),
            print("AgentGen installation verified!")
        )
    )
)
```

After deployment, update your webhook URLs to use the Modal endpoints.