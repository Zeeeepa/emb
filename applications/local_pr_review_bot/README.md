# Local PR Review Bot

This is a locally hostable version of the PR review bot that can be exposed via Cloudflare or any other reverse proxy. It provides the same functionality as the Modal-based PR review bot but can be run on your own infrastructure.

## Prerequisites

Before running this application, you'll need the following:

- GitHub API Token with repo access
- Anthropic API Key (or OpenAI API Key as an alternative)
- A domain name configured with Cloudflare (for exposing the webhook)
- Python 3.12 or newer

## Setup

1. Clone the repository
2. Navigate to the `applications/local_pr_review_bot` directory
3. Set up your environment variables in a `.env` file:

```env
GITHUB_TOKEN=your_github_token
ANTHROPIC_API_KEY=your_anthropic_key
# Optional: OPENAI_API_KEY if you prefer using OpenAI
# Optional: SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET for Slack notifications
WEBHOOK_SECRET=your_webhook_secret  # Used to verify GitHub webhook requests
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running Locally

1. Start the server:
```bash
python server.py
```

2. By default, the server will run on port 8000. You can change this by setting the `PORT` environment variable.

## Exposing via Cloudflare

1. Set up Cloudflare Tunnel (formerly Argo Tunnel) to expose your local server:
   - Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
   - Authenticate: `cloudflared tunnel login`
   - Create a tunnel: `cloudflared tunnel create pr-review-bot`
   - Configure the tunnel (create a config.yml file):
     ```yaml
     tunnel: <TUNNEL_ID>
     credentials-file: /path/to/credentials.json
     ingress:
       - hostname: pr-review.yourdomain.com
         service: http://localhost:8000
       - service: http_status:404
     ```
   - Route DNS to your tunnel: `cloudflared tunnel route dns <TUNNEL_ID> pr-review.yourdomain.com`
   - Start the tunnel: `cloudflared tunnel run pr-review-bot`

2. Set up GitHub webhook:
   - Go to your GitHub repository settings → Webhooks
   - Add a new webhook with:
     - Payload URL: `https://pr-review.yourdomain.com/webhook`
     - Content type: `application/json`
     - Secret: The same value as your `WEBHOOK_SECRET` environment variable
     - Events: Select "Pull requests"

## How It Works

The bot will:
1. Listen for PRs labeled with "analyzer" (configurable)
2. When a PR gets this label, it will:
   - Clone your repository
   - Analyze the code changes
   - Generate a comprehensive review
   - Post comments directly on the PR

## Customization

You can customize the bot by:
1. Modifying the prompt in `helpers.py`
2. Changing the label that triggers reviews (default is "analyzer")
3. Adjusting the configuration in `config.py`

## Troubleshooting

If you encounter issues:
1. Check the logs for errors
2. Verify your GitHub token has sufficient permissions
3. Make sure your webhook is correctly configured
4. Ensure Cloudflare Tunnel is running properly