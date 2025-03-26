# Codebase Reorganization Plan

This document outlines the plan for reorganizing the EMB codebase to improve modularity, maintainability, and usability.

## Current Structure

```
emb/
├── AgentGen/
│   ├── agents/
│   ├── cli/
│   ├── configs/
│   ├── extensions/
│   └── tests/
├── applications/
│   ├── codegen_app/
│   ├── pr_review_bot/
│   └── ...
└── shared/
    └── logging/
```

## Target Structure

```
emb/
├── emb-core/
│   ├── emb/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── config.py
│   │   │   └── utils.py
│   │   └── __init__.py
│   ├── setup.py
│   ├── pyproject.toml
│   └── tests/
├── emb-agents/
│   ├── emb/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── code_agent.py
│   │   │   ├── chat_agent.py
│   │   │   ├── plan_agent.py
│   │   │   ├── research_agent.py
│   │   │   └── utils.py
│   │   └── __init__.py
│   ├── setup.py
│   ├── pyproject.toml
│   └── tests/
├── emb-extensions/
│   ├── emb/
│   │   ├── extensions/
│   │   │   ├── __init__.py
│   │   │   ├── github/
│   │   │   ├── slack/
│   │   │   ├── linear/
│   │   │   ├── langchain/
│   │   │   └── ...
│   │   └── __init__.py
│   ├── setup.py
│   ├── pyproject.toml
│   └── tests/
├── emb-cli/
│   ├── emb/
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   ├── commands/
│   │   │   └── ...
│   │   └── __init__.py
│   ├── setup.py
│   ├── pyproject.toml
│   └── tests/
├── applications/
│   ├── codegen_app/
│   ├── pr_review_bot/
│   └── ...
└── shared/
    └── logging/
```

## Migration Steps

1. Create the new directory structure
2. Move code from AgentGen to the appropriate new modules
3. Update imports to use the new module structure
4. Update setup.py files for each module
5. Update applications to use the new module structure
6. Add namespace package declarations to ensure proper import resolution
7. Update documentation and examples
8. Add tests to verify the new structure works correctly

## Import Structure

The new import structure will use namespace packages to allow for a clean import hierarchy:

```python
# Core functionality
from emb.core import BaseAgent, Config

# Agent implementations
from emb.agents import CodeAgent, ChatAgent

# Extensions
from emb.extensions.github import GitHubExtension
from emb.extensions.slack import SlackExtension

# CLI tools
from emb.cli import main
```

## Backward Compatibility

To maintain backward compatibility during the transition:

1. Create compatibility layers in the old locations that import from the new locations
2. Add deprecation warnings to encourage users to update their imports
3. Provide a migration guide for users to update their code

## Timeline

1. Phase 1: Create the new directory structure and move code (1-2 weeks)
2. Phase 2: Update imports and ensure everything works (1-2 weeks)
3. Phase 3: Update applications and documentation (1-2 weeks)
4. Phase 4: Testing and refinement (1-2 weeks)

## Benefits

This reorganization will provide several benefits:

1. Clearer separation of concerns
2. More modular codebase
3. Easier to understand and maintain
4. Better dependency management
5. Improved developer experience
6. Cleaner import structure
7. Better testability