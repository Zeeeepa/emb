"""Tools for running bash commands."""

import re
import shlex
import subprocess

from agentgen.extensions.tools.base import CodegenTool