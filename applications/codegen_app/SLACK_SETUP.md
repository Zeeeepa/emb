# Setting Up Slack Integration for Codegen App

This guide will help you set up your Codegen App to appear on Slack and respond to messages.

## Prerequisites

- A Slack workspace where you have admin permissions
- Your Modal deployment of the Codegen App is working

## Step 1: Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter a name for your app (e.g., "Codegen Assistant")
5. Select your workspace
6. Click "Create App"

## Step 2: Configure Bot Permissions

1. In the left sidebar, click on "OAuth & Permissions"
2. Scroll down to "Scopes" and add the following Bot Token Scopes:
   - `app_mentions:read` - To read when the bot is mentioned
   - `channels:history` - To read messages in channels
   - `chat:write` - To send messages
   - `files:write` - To upload files
   - `reactions:write` - To add reactions to messages
   - `users:read` - To read user information
   - `channels:read` - To read channel information

3. Scroll up and click "Install to Workspace"
4. Authorize the app when prompted

## Step 3: Get Your Bot Token

1. After installation, you'll be redirected to the "OAuth & Permissions" page
2. Copy the "Bot User OAuth Token" (it starts with `xoxb-`)
3. Save this token as you'll need it for your environment variables

## Step 4: Configure Event Subscriptions

1. In the left sidebar, click on "Event Subscriptions"
2. Toggle "Enable Events" to On
3. In the "Request URL" field, enter your Modal deployment URL followed by `/slack/events`:
   ```
   https://zeeeepa--coder-fastapi-app.modal.run/slack/events
   ```
4. Slack will verify this endpoint - it should respond with a challenge
5. Under "Subscribe to bot events", add the following events:
   - `app_mention` - When someone mentions your bot
   - `message.channels` - When a message is posted to a channel

6. Click "Save Changes"

## Step 5: Update Environment Variables

1. Add the following environment variables to your Modal deployment:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_SIGNING_SECRET=your-signing-secret-here
   SLACK_NOTIFICATION_CHANNEL=your-channel-id
   ```

2. You can find your signing secret in the "Basic Information" section of your Slack app settings

3. To get a channel ID, right-click on the channel in Slack and select "Copy Link". The ID is the part after the last slash.

## Step 6: Redeploy Your App

1. Run the deployment script again:
   ```bash
   cd ~/emb/applications/codegen_app
   ./deploy_modal.sh
   ```

## Step 7: Invite Your Bot to Channels

1. In Slack, go to the channel where you want to use the bot
2. Type `/invite @YourBotName` (replace YourBotName with the name of your bot)

## Testing Your Integration

1. In a channel where your bot is present, mention the bot with a message:
   ```
   @YourBotName Hello, can you help me analyze a repository?
   ```

2. The bot should respond to your message

## Troubleshooting

If your bot doesn't respond:

1. Check the Modal logs for any errors
2. Verify that your environment variables are set correctly
3. Make sure the bot has been invited to the channel
4. Confirm that the event subscriptions are properly configured
5. Check that your bot has the necessary permissions

## Advanced Configuration

For more advanced features, you can modify the `app.py` file to add custom handlers for different types of Slack events. The current implementation handles basic message events, but you can extend it to handle interactive components, slash commands, and more.