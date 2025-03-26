# Integrating AgentGen with Codegen

This guide explains how to integrate the AgentGen module with the Codegen application.

## Option 1: Install AgentGen as a Package in Codegen

The simplest way to integrate AgentGen with Codegen is to install it as a package within the Codegen environment.

1. Clone both repositories:
   ```bash
   # Clone Codegen
   git clone https://github.com/codegen-sh/codegen.git
   cd codegen
   
   # Clone AgentGen
   git clone https://github.com/Zeeeepa/emb.git
   ```

2. Install Codegen in development mode:
   ```bash
   cd codegen
   pip install -e .
   ```

3. Install AgentGen in development mode:
   ```bash
   cd ../emb/AgentGen
   pip install -e .
   ```

4. Now you can import AgentGen in your Codegen applications:
   ```python
   from codegen import CodegenApp, Codebase
   from agentgen import CodeAgent, ChatAgent, create_codebase_agent
   ```

## Option 2: Add AgentGen as a Submodule in Codegen

For tighter integration, you can add AgentGen as a Git submodule within the Codegen repository.

1. Add AgentGen as a submodule in the Codegen repository:
   ```bash
   cd codegen
   git submodule add https://github.com/Zeeeepa/emb.git submodules/emb
   ```

2. Create a symbolic link to the AgentGen directory:
   ```bash
   ln -s submodules/emb/AgentGen src/codegen/agentgen
   ```

3. Add an `__init__.py` file to make it a proper package:
   ```bash
   touch src/codegen/agentgen/__init__.py
   ```

4. Update the `__init__.py` file to expose the necessary modules:
   ```python
   # src/codegen/agentgen/__init__.py
   from submodules.emb.AgentGen.agents.code_agent import CodeAgent
   from submodules.emb.AgentGen.agents.chat_agent import ChatAgent
   from submodules.emb.AgentGen.agents.factory import create_codebase_agent, create_chat_agent, create_codebase_inspector_agent, create_agent_with_tools
   
   __all__ = [
       'CodeAgent',
       'ChatAgent',
       'create_codebase_agent',
       'create_chat_agent',
       'create_codebase_inspector_agent',
       'create_agent_with_tools',
   ]
   ```

5. Install Codegen with the AgentGen submodule:
   ```bash
   pip install -e .
   ```

6. Now you can import AgentGen from within Codegen:
   ```python
   from codegen.agentgen import CodeAgent, ChatAgent, create_codebase_agent
   ```

## Option 3: Copy AgentGen into Codegen

If you prefer to have a standalone copy of AgentGen within Codegen:

1. Copy the AgentGen directory into the Codegen repository:
   ```bash
   cp -r emb/AgentGen codegen/src/codegen/agentgen
   ```

2. Update imports in your application to use the new location:
   ```python
   from codegen.agentgen import CodeAgent, ChatAgent, create_codebase_agent
   ```

3. Install Codegen with the integrated AgentGen:
   ```bash
   cd codegen
   pip install -e .
   ```

## Updating the Application Code

After integrating AgentGen with Codegen, update your application imports:

```python
# Before
from agentgen import CodeAgent, ChatAgent, create_codebase_agent

# After (if using Option 2 or 3)
from codegen.agentgen import CodeAgent, ChatAgent, create_codebase_agent
```

## Troubleshooting

If you encounter import errors:

1. Verify that both Codegen and AgentGen are installed in your environment:
   ```bash
   pip list | grep -E 'codegen|agentgen'
   ```

2. Check the Python path:
   ```python
   import sys
   print(sys.path)
   ```

3. Ensure all necessary `__init__.py` files exist in the directory structure.