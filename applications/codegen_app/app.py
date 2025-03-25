import logging

import modal
from AgentGen import CodeAgent, CodegenApp
from AgentGen.extensions.github.types.events.pull_request import PullRequestLabeledEvent