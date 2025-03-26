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

### Troubleshooting Modal Deployment

If you encounter import errors during deployment, try the following steps:

1. **Ensure packages are installed locally**:
   ```bash
   # Install both packages in development mode
   cd ~/emb/AgentGen && pip install -e . && cd -
   cd ~/emb/codegen && pip install -e . && cd -
   ```

2. **Check Python path**:
   ```bash
   # The deploy_modal.sh script sets this automatically
   export PYTHONPATH=$PYTHONPATH:~/emb/AgentGen:~/emb/codegen
   ```

3. **Verify imports work locally**:
   ```bash
   python -c "import agentgen; import codegen; print('Imports successful!')"
   ```

4. **Check Modal image configuration**:
   The app.py file is configured to install these packages during deployment:

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
       .run_function(verify_agentgen_installation)
   )
   ```

   The `verify_agentgen_installation` function checks if the agentgen package is properly installed in the Modal environment.

5. **Common issues**:
   - Case sensitivity: Make sure the directory name matches the import name (AgentGen vs agentgen)
   - Path issues: Ensure the Python path includes the correct directories
   - Installation issues: Make sure the packages are installed correctly

After deployment, update your webhook URLs to use the Modal endpoints.

