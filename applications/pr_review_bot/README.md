# AI-Powered Pull Request Review Bot

This example project demonstrates how to deploy an agentic bot that automatically reviews GitHub Pull Requests. The bot analyzes code changes and their dependencies to provide comprehensive code reviews using AI, considering both direct modifications and their impact on the codebase.

## Features

- Automated PR code review using AI
- Deep dependency analysis of code changes
- Context-aware feedback generation
- Structured review format with actionable insights
- Integration with GitHub PR system
- Slack notifications for review events

## Prerequisites

Before running this application, you'll need the following:

- [Modal](https://modal.com/) account and API key
- GitHub API Token with repository access
- Anthropic API Key (or OpenAI API Key)
- GitHub Repository with webhook access

## Setup

1. Clone the repository
2. Navigate to the PR review bot directory:
   ```bash
   cd applications/pr_review_bot
   ```
3. Copy the template environment file:
   ```bash
   cp .env.template .env
   ```
4. Edit the `.env` file with your credentials:
   ```env
   # GitHub configuration
   MODAL_API_KEY="your_modal_api_key"
   GITHUB_TOKEN="your_github_token"
   WEBHOOK_SECRET="your_webhook_secret"
   TRIGGER_LABEL="analyzer"

   # LLM configuration (at least one is required)
   ANTHROPIC_API_KEY="your_anthropic_api_key"
   OPENAI_API_KEY="your_openai_api_key"

   # Slack configuration (optional)
   SLACK_SIGNING_SECRET="your_slack_signing_secret"
   SLACK_BOT_TOKEN="your_slack_bot_token"
   SLACK_NOTIFICATION_CHANNEL="your_slack_channel_id"
   ```

## Deployment

1. Install dependencies:
   ```bash
   pip install uv
   uv sync
   ```

2. Deploy to Modal:
   ```bash
   uv run modal deploy app.py
   ```
   This will deploy a Modal app that can be triggered to review PRs and provide you with a webhook URL.

3. Set up GitHub webhook:
   - Go to your GitHub repository settings → Webhooks
   - Add a new webhook with:
     - Payload URL: The Modal endpoint URL from the previous step
     - Content type: `application/json`
     - Secret: The same value as your `WEBHOOK_SECRET` environment variable
     - Events: Select "Pull requests"

## Usage

Once deployed, the bot will:

1. Listen for PRs labeled with your configured trigger label (default: "analyzer")
2. When a PR gets this label, it will:
   - Clone your repository
   - Analyze the code changes
   - Generate a comprehensive review
   - Post comments directly on the PR
   - Send a notification to your Slack channel (if configured)

To trigger a review:
1. Create or update a PR in your repository
2. Add the "analyzer" label (or your custom trigger label) to the PR
3. The bot will automatically start reviewing the PR

To remove review comments:
1. Remove the "analyzer" label from the PR
2. The bot will automatically remove all its comments

## Customization

You can customize the bot by:
1. Modifying the prompt in `helpers.py`
2. Changing the trigger label in your `.env` file
3. Adjusting the Slack notification settings

## Note on PR Merging

This bot does NOT automatically merge PRs. It only provides code reviews and comments. The decision to merge a PR remains with the repository maintainers.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
