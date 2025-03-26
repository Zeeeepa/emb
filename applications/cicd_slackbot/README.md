# CICD SlackChatbot

A Slack-based chatbot that manages the CI/CD cycle by analyzing PRs, reflecting on plan goals from Linear, and suggesting next steps.

## Features

- **PR Analysis**: Automatically analyzes PRs when they are opened or on-demand via Slack commands
- **Plan Reflection**: Reflects on overall plan goals and progress from Linear
- **Next Step Suggestions**: Suggests the next development step based on plan progress and PR history
- **Slack Integration**: Interacts with users via Slack for a seamless development experience
- **GitHub Integration**: Monitors PR events and provides feedback
- **Linear Integration**: Tracks project plans and issue status

## How It Works

The CICD SlackChatbot creates a continuous development cycle:

1. **PR Analysis**: When a PR is opened, the bot analyzes it and provides feedback
2. **PR Merged**: When a PR is merged, the bot reflects on the plan and suggests the next step
3. **Plan Reflection**: The bot analyzes the current state of the project plan from Linear
4. **Next Step Suggestion**: Based on the plan reflection, the bot suggests the next development task
5. **Task Implementation**: Developers implement the suggested task
6. **Cycle Continues**: The cycle repeats with the next PR

## Slack Commands

- `analyze PR in repo/name #123` - Analyze a specific PR
- `reflect on plan [for team ID]` - Reflect on plan goals and progress
- `suggest next step [for repo/name]` - Suggest the next development step
- `help` - Show available commands

## Setup

### Environment Variables

```
GITHUB_TOKEN=your_github_token
LINEAR_API_KEY=your_linear_api_key
LINEAR_TEAM_ID=your_linear_team_id
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_SIGNING_SECRET=your_slack_signing_secret
SLACK_DEFAULT_CHANNEL=your_slack_channel_id
MODAL_API_KEY=your_modal_api_key
DEFAULT_REPO=default_repo_to_use
```

### Deployment

The application is designed to be deployed using Modal:

```bash
modal deploy applications/cicd_slackbot/app.py
```

## Integration with Other Systems

### GitHub Integration

The bot listens for GitHub webhook events:
- `pull_request:opened` - Triggers PR analysis
- `pull_request:closed` - Triggers plan reflection and next step suggestion if the PR was merged

### Linear Integration

The bot listens for Linear webhook events:
- `Issue:created` - Notifies the team via Slack
- `Issue:updated` - Triggers plan reflection and next step suggestion if an issue was completed

### Slack Integration

The bot responds to mentions in Slack and provides a command interface for interacting with the CI/CD cycle.

## Example Workflow

1. Developer opens a PR
2. Bot analyzes the PR and provides feedback
3. Developer addresses feedback and merges the PR
4. Bot reflects on the plan and suggests the next step
5. Bot sends the next step suggestion to Slack
6. Developer implements the suggested step
7. Cycle continues

## Architecture

The CICD SlackChatbot is built using:
- **CodegenApp**: For handling webhook events and routing
- **CICDSlackbot**: Core class that manages the CI/CD cycle
- **CodeAgent**: For analyzing code and generating suggestions
- **Modal**: For serverless deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request