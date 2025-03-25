import logging

import modal
from agentgen import CodeAgent
from codegen import Codebase
from agentgen.extensions.github.types.events.pull_request import PullRequestLabeledEvent