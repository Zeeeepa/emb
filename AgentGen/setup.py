from setuptools import setup

setup(
    name="agentgen",
    package_dir={"agentgen": "."},
    packages=["agentgen", "agentgen.agents", "agentgen.cli", "agentgen.configs", "agentgen.extensions"],
)