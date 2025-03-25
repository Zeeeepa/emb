# Repository Comparison Tool with GUI

This tool provides a graphical user interface for comparing two repositories and saving the differences in a structured way. It allows users to select repositories using a file explorer and configure comparison options.

## Features

- **User-friendly interface**: Select repositories and output directory using file dialogs
- **Multiple comparison modes**: Choose between basic, enhanced, or specialized comparison
- **Customizable ignore patterns**: Specify files and directories to ignore during comparison
- **Real-time progress tracking**: View comparison progress and logs in real-time
- **Cross-platform support**: Works on Windows, macOS, and Linux
- **Error handling**: Comprehensive error handling and user feedback

## Screenshots

(Screenshots would be added here after the application is deployed)

## Installation

1. Ensure you have Python 3.6+ installed
2. Clone this repository:
   ```
   git clone https://github.com/Zeeeepa/emb.git
   cd emb
   ```
3. Install required dependencies (Tkinter is included with standard Python installations)

## Usage

1. Run the GUI application:
   ```
   python repo_diff_gui.py
   ```

2. Use the interface to:
   - Select the original repository (current version with removed content)
   - Select the past repository (version with all content)
   - Choose an output directory for the differences
   - Configure comparison options
   - Start the comparison process

3. After comparison completes:
   - View the results in the log area
   - Open the output directory to see the saved differences

## Comparison Modes

The application offers three comparison modes:

1. **Basic**: Simple file-by-file comparison that identifies removed content
2. **Enhanced**: Improved comparison with better handling of Python files
3. **Specialized**: Advanced comparison specifically optimized for `__init__.py` files and their imports/exports

## Example

For example, if you have:

**Original Repository** (`__init__.py`):
```python
__all__ = ["Codebase", "CodegenApp", "Function", "ProgrammingLanguage", "function"]
```

**Past Repository** (`__init__.py`):
```python
from AgentGen import CodeAgent
# from codegen.extensions.index.file_index import FileIndex
# from codegen.extensions.langchain.agent import create_agent_with_tools, create_codebase_agent
__all__ = ["CodeAgent", "Codebase", "CodegenApp", "Function", "ProgrammingLanguage", "function"]
```

The tool will create a difference file showing what was removed:
```python
from AgentGen import CodeAgent
# from codegen.extensions.index.file_index import FileIndex
# from codegen.extensions.langchain.agent import create_agent_with_tools, create_codebase_agent
__all__ = ['CodeAgent']
```

## Edge Cases Handled

The application handles various edge cases:

- **Binary files**: Properly skips binary files during comparison
- **Large repositories**: Efficiently processes large repositories with many files
- **Syntax errors**: Gracefully handles Python files with syntax errors
- **Cross-platform paths**: Correctly manages file paths across different operating systems
- **Concurrent operations**: Uses threading to keep the UI responsive during comparison
- **Import failures**: Falls back to subprocess execution if direct imports fail
- **Cancellation**: Properly handles user cancellation of the comparison process
- **Error reporting**: Provides detailed error messages and logs for troubleshooting

## Requirements

- Python 3.6+
- Tkinter (included with standard Python installations)

## License

This project is licensed under the MIT License - see the LICENSE file for details.