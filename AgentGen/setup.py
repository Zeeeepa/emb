
from setuptools import setup, find_packages

setup(
    name="agentgen",
    packages=find_packages(include=["agents", "agents.*", "cli", "cli.*", "configs", "configs.*", 
                                    "extensions", "extensions.*", "tests", "tests.*"]),
    package_dir={"": "."},
)