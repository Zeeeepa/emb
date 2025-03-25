# Repository Difference Tool

This repository contains Python scripts to compare two repositories and save the differences in a structured way, preserving the project structure and showing only the content that was removed from the past repository.

## Scripts Overview

There are three scripts with increasing levels of specialization:

1. **repo_diff.py**: Basic repository comparison tool that identifies differences between files.
2. **repo_diff_enhanced.py**: Enhanced version with better handling of Python files, imports, and `__all__` lists.
3. **repo_diff_init_specialized.py**: Specialized version with advanced handling for `__init__.py` files, using AST parsing for accurate import and `__all__` list comparison.

## Usage

All scripts follow the same basic usage pattern:

```bash
python <script_name>.py <original_repo_path> <past_repo_path> <output_path> [--ignore <files_to_ignore>]
```

Where:
- `<original_repo_path>`: Path to the original repository (with removed contents)
- `<past_repo_path>`: Path to the past repository (with all contents)
- `<output_path>`: Path where to save the differences
- `--ignore`: Optional list of files or directories to ignore (default: `.git`, `__pycache__`, `.idea`, `.vscode`, `.DS_Store`)

### Example

```bash
python repo_diff_init_specialized.py ./original_repo ./past_repo ./diff_output
```

## Specialized Handling for `__init__.py` Files

The specialized script (`repo_diff_init_specialized.py`) is designed to handle the specific case mentioned in the requirements, where imports and `__all__` lists in `__init__.py` files need special attention.

For example, if the original `__init__.py` has:
```python
__all__ = ["Codebase", "CodegenApp", "Function", "ProgrammingLanguage", "function"]
```

And the past version had:
```python
from agentgen import CodeAgent
from codegen import Codebase
__all__ = ["CodeAgent", "Codebase", "CodegenApp", "Function", "ProgrammingLanguage", "function"]
```

The output will show what was removed:
```python
from agentgen import CodeAgent
from codegen import Codebase

__all__ = ['CodeAgent']
```

## Features

- Preserves project structure in the output
- Special handling for Python files, particularly `__init__.py` files
- Identifies removed imports and `__all__` entries
- Handles binary files appropriately
- Provides detailed summary of comparison results
- Ignores common non-source directories like `.git` and `__pycache__`

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library modules)

## How It Works

1. The script walks through both repositories to identify all files
2. For each file that exists in both repositories, it compares the content
3. For Python files, especially `__init__.py`, it uses specialized comparison logic
4. For files that only exist in the past repository, it copies them as-is
5. The output preserves the directory structure of the repositories

The specialized script uses AST (Abstract Syntax Tree) parsing for accurate identification of imports and `__all__` lists, with regex fallback for files with syntax errors.