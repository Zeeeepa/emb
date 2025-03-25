# Repository Comparison Tool

This set of scripts allows you to compare two repositories and save the differences in a structured way. It's particularly useful for tracking changes between different versions of a codebase.

## Features

- Compare two repositories and identify differences in file content
- Special handling for Python `__init__.py` files (imports and `__all__` lists)
- Identify files that exist only in one repository
- Save all differences to a structured output directory
- User-friendly GUI with file explorer integration

## Scripts

### 1. `repo_diff_init_specialized_fixed_v3.py`

This is the core comparison script with specialized handling for Python files, particularly `__init__.py` files.

**Usage:**
```bash
python repo_diff_init_specialized_fixed_v3.py <original_repo_path> <past_repo_path> <output_path> [--ignore <patterns>]
```

**Example:**
```bash
python repo_diff_init_specialized_fixed_v3.py ./original_repo ./past_repo ./diff_output --ignore .git __pycache__
```

### 2. `repo_diff_gui_fixed_v3.py`

A graphical user interface for the repository comparison tool, making it easy to select repositories and configure comparison options.

**Usage:**
```bash
python repo_diff_gui_fixed_v3.py
```

## How It Works

The tool performs the following operations:

1. **File Comparison**: For files that exist in both repositories, it compares the content and identifies differences.
2. **Special Handling for `__init__.py`**: For Python initialization files, it specifically tracks imports and `__all__` list changes.
3. **Files Only in Past Repository**: Files that exist in the past repository but not in the original are copied to the output directory.
4. **Files Only in Original Repository**: Files that exist in the original repository but not in the past are also copied to the output directory.

## Example

If the original repository has:
```python
# __init__.py
__all__ = ["Codebase", "CodegenApp", "Function", "ProgrammingLanguage", "function"]
```

And the past version had:
```python
# __init__.py
from AgentGen import CodeAgent
# from codegen.extensions.index.file_index import FileIndex
# from codegen.extensions.langchain.agent import create_agent_with_tools, create_codebase_agent
__all__ = ["CodeAgent", "Codebase", "CodegenApp", "Function", "ProgrammingLanguage", "function"]
```

The output will show what was removed:
```python
# __init__.py in output directory
from AgentGen import CodeAgent
# from codegen.extensions.index.file_index import FileIndex
# from codegen.extensions.langchain.agent import create_agent_with_tools, create_codebase_agent

__all__ = ['CodeAgent']
```

## GUI Features

The GUI provides the following features:

- **Repository Selection**: Select the original and past repositories using file explorer dialogs
- **Output Directory**: Choose where to save the differences
- **Ignore Patterns**: Specify files or directories to ignore during comparison
- **Comparison Modes**: Choose between basic, enhanced, or specialized comparison
- **Real-time Progress**: View progress and logs in real-time
- **Open Output**: Easily open the output directory after comparison completes

## Edge Cases Handled

- Binary files are properly skipped
- Files with syntax errors are gracefully handled
- Cross-platform path management
- Threading for UI responsiveness
- Comprehensive error handling

## Requirements

- Python 3.6 or higher
- Tkinter (included in standard Python installations)