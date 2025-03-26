# Enhanced Slack RAG Agent for Codebase Research

A powerful Slack bot that provides comprehensive answers to questions about codebases using advanced RAG (Retrieval-Augmented Generation) techniques, academic research integration, and collaborative features.

## Features

### Core Features

- **Dual-Index RAG**: Uses both file-level and code-level indices for comprehensive context retrieval
- **Multi-Agent Architecture**: Combines code analysis with web search for complex queries
- **MindSearch-Inspired Query Decomposition**: Breaks down complex questions into sub-questions
- **Parallel Processing**: Executes sub-questions in parallel for faster responses
- **Conversation History**: Tracks and logs all interactions for continuous improvement
- **Repository Switching**: Dynamically switch between different repositories
- **Index Refreshing**: Update indices on demand to reflect the latest code changes

### Advanced Features

- **Academic Research Integration**: Searches academic papers and formal documentation
- **Code Visualization**: Generates descriptions of how code could be visualized
- **User Personalization**: Maintains user profiles with preferences and topics of interest
- **Collaborative Research Sessions**: Enables multiple users to work together on research questions
- **Feedback Collection**: Gathers and stores user feedback to improve future responses
- **Memory and Caching**: Remembers previous research to avoid duplicating work

## Architecture

The system consists of several integrated components:

1. **SlackRAGAgent**: Core RAG agent for code-specific questions
   - Builds and maintains file and code indices
   - Retrieves relevant code context
   - Generates answers using LLM with code context

2. **EnhancedResearchAssistant**: Advanced research capabilities
   - Breaks down complex queries into sub-questions
   - Combines code analysis, web search, and academic research
   - Personalizes responses based on user preferences
   - Generates code visualizations

3. **CollaborativeResearchSession**: Team-based research
   - Manages collaborative research sessions
   - Tracks contributions from multiple users
   - Synthesizes insights into comprehensive answers

4. **WebSearchAgent**: Specialized agent for external information
   - Breaks down queries into focused sub-queries
   - Searches the web for relevant information
   - Synthesizes search results into coherent answers

## Usage

The Slack bot responds to mentions with answers about the codebase. Special commands include:

### Research Commands

- `@bot research [question]` - Research a question using code analysis and web search
- `@bot set repo [owner/repo]` - Switch to a different repository
- `@bot refresh index` - Rebuild the indices for the current repository

### Personalization Commands

- `@bot set preference [name] to [value]` - Update your preferences
  - `code_detail_level`: low, medium, high
  - `include_academic_sources`: true, false
  - `visualization_enabled`: true, false
- `@bot add topic [topic]` - Add a topic of interest to your profile
- `@bot feedback on [query]: [feedback]` - Provide feedback on a research result

### Collaborative Research Commands

- `@bot start session on [question]` - Start a new collaborative research session
- `@bot contribute to session [id] [insights]` - Add your insights to a session
- `@bot session status [id]` - Check the status of a research session
- `@bot finalize session [id]` - Generate a final answer for a session
- `@bot show session results [id]` - View the results of a completed session
- `@bot list sessions` - List all active research sessions

### Help Command

- `@bot help` - Show available commands and usage information

For complex research queries, include keywords like "research", "investigate", or "analyze" to automatically trigger the enhanced research system.

## Deployment

The application is deployed as a serverless Modal app:

```bash
modal deploy applications/slack_rag_agent/enhanced_modal_app.py
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
- Support for more visualization types (interactive diagrams, etc.)
- Enhanced collaborative features (voting on contributions, etc.)
- Integration with version control systems for historical context