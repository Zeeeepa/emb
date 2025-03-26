from setuptools import setup, find_packages

setup(
    name="agentgen",
    version="0.1.0",
    description="A framework for creating code agents",
    packages=find_packages(include=["agents", "agents.*", "cli", "cli.*", "configs", "configs.*", 
                                    "extensions", "extensions.*", "tests", "tests.*"]),
    package_dir={"": "."},
    py_modules=["__init__"],
    entry_points={
        "console_scripts": [
            "agentgen=cli.commands.main:main",
        ],
    },
)