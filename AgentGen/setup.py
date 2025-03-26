from setuptools import setup

setup(
    name="agentgen",
    packages=["agents", "cli", "configs", "extensions", "tests"],
    package_dir={"": "."},
)