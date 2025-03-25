"""Tools for running bash commands."""

import re
import shlex
import subprocess

from AgentGen.extensions.tools.base import CodegenTool