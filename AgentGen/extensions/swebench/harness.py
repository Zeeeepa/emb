from codegen.agents.code_agent import CodeAgent
    agent = CodeAgent(codebase=codebase, tags=tags, metadata=metadata)
        result = agent.run(prompt=message)