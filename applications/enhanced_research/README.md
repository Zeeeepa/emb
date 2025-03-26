# Enhanced Code Research with Web Search

This application combines Codegen's powerful code analysis capabilities with MindSearch's multi-agent web search framework to provide comprehensive research capabilities.

## Features

- **Code Analysis**: Analyze codebases using Codegen's tools
- **Web Search Integration**: Search the web for relevant information using MindSearch's multi-agent approach
- **Multi-Agent Collaboration**: Decompose complex queries into sub-questions and search for information in parallel
- **Comprehensive Answers**: Synthesize information from both code analysis and web search

## Usage

```bash
python -m applications.enhanced_research.run --repo owner/repo --query "Your research question"
```

## How It Works

1. The application initializes both a code analysis agent and a web search agent
2. The query is processed by a coordinator agent that determines whether to use code analysis, web search, or both
3. Sub-queries are generated and dispatched to the appropriate agents
4. Results are collected and synthesized into a comprehensive answer