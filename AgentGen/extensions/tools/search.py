"""Simple text-based search functionality for the codebase.

This performs either a regex pattern match or simple text search across all files in the codebase.
Each matching line will be returned with its line number.
Results are paginated with a default of 10 files per page.
"""

import re
from typing import ClassVar, List, Optional

from pydantic import Field

from agentgen.extensions.tools.base import CodegenTool