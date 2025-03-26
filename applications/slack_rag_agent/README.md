# Slack RAG Agent for Codebase Q&A

A powerful Slack bot that provides comprehensive answers to questions about codebases using RAG (Retrieval-Augmented Generation) and multi-agent techniques inspired by MindSearch.

## Features

- **Dual-Index RAG**: Uses both file-level and code-level indices for comprehensive context retrieval
- **Multi-Agent Architecture**: Combines code analysis with web search for complex queries
- **MindSearch-Inspired Query Decomposition**: Breaks down complex questions into sub-questions
- **Parallel Processing**: Executes sub-questions in parallel for faster responses
- **Conversation History**: Tracks and logs all interactions for continuous improvement
- **Repository Switching**: Dynamically switch between different repositories
- **Index Refreshing**: Update indices on demand to reflect the latest code changes

## Architecture

The system consists of three main components:

1. **SlackRAGAgent**: Core RAG agent for code-specific questions
   - Builds and maintains file and code indices
   - Retrieves relevant code context
   - Generates answers using LLM with code context

2. **WebSearchAgent**: Specialized agent for external information
   - Breaks down queries into focused sub-queries
   - Searches the web for relevant information
   - Synthesizes search results into coherent answers

3. **MultiAgentCoordinator**: Orchestrates the entire system
   - Creates research plans for complex queries
   - Delegates sub-questions to appropriate agents
   - Synthesizes results from multiple agents

## Usage

The Slack bot responds to mentions with answers about the codebase. Special commands include:

- `@bot use repo owner/repo` - Switch to a different repository
- `@bot refresh index` - Rebuild the indices for the current repository
- `@bot deep research on [topic]` - Trigger the multi-agent system for comprehensive research

For complex research queries, include keywords like "deep", "comprehensive", or "research" to automatically trigger the multi-agent system.

## Deployment

The application is deployed as a serverless Modal app:

```bash
modal deploy applications/slack_rag_agent/modal_app.py
```

### Environment Variables

Required environment variables:
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_SIGNING_SECRET`: Slack signing secret
- `OPENAI_API_KEY`: OpenAI API key
- `DEFAULT_REPO`: Default repository to analyze (e.g., "owner/repo")

Optional environment variables:
- `SEARCH_API_KEY`: API key for web search (if using a real search API)
- `SEARCH_ENDPOINT`: Endpoint for web search API

## Integration with MindSearch

This implementation is inspired by the MindSearch multi-agent architecture, particularly:

1. **Query Decomposition**: Breaking down complex queries into simpler sub-questions
2. **Parallel Processing**: Executing sub-questions concurrently
3. **Result Synthesis**: Combining results from multiple sources into a coherent answer

The key innovation is combining MindSearch's web search capabilities with Codegen's powerful code analysis to create a comprehensive research system specifically for code-related questions.

## Future Improvements

- Integrate with real search APIs (Google, Bing, DuckDuckGo)
- Add more specialized agents (security analysis, performance analysis, etc.)
- Implement feedback mechanisms to improve responses over time
- Add support for code generation and automated fixes
- Integrate with CI/CD systems for automated code reviews