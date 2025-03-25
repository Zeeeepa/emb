#!/usr/bin/env python3
"""
Repository Difference Tool (Specialized for __init__.py)

This script compares two repositories (original and past) and saves the differences
in a structured way, with special handling for Python __init__.py files and their
imports and __all__ lists.

Usage:
    python repo_diff_init_specialized_fixed_v3.py <original_repo_path> <past_repo_path> <output_path>

Example:
    python repo_diff_init_specialized_fixed_v3.py ./original_repo ./past_repo ./diff_output
"""

import os
import sys
import shutil
import difflib
import re
from pathlib import Path
import argparse
import ast


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare two repositories and save the differences with special handling for __init__.py files."
    )
    parser.add_argument(
        "original_repo", 
        help="Path to the original repository (with removed contents)"
    )
    parser.add_argument(
        "past_repo", 
        help="Path to the past repository (with all contents)"
    )
    parser.add_argument(
        "output_path", 
        help="Path where to save the differences"
    )
    parser.add_argument(
        "--ignore", 
        nargs="+", 
        default=[".git", "__pycache__", ".idea", ".vscode", ".DS_Store"],
        help="Directories or files to ignore during comparison"
    )
    
    return parser.parse_args()


def get_file_content(file_path):
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # For binary files, return empty content
        return ""
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def extract_imports(content):
    """
    Extract import statements from Python code using AST.
    Returns a list of tuples (import_type, module, names).
    """
    imports = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(('import', name.name, None))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names = [alias.name for alias in node.names]
                imports.append(('from', module, names))
    except SyntaxError:
        # Fall back to regex for files with syntax errors
        import_regex = re.compile(r'^(?:from\s+(\S+)\s+import\s+(.+)|import\s+(.+))$', re.MULTILINE)
        for match in import_regex.finditer(content):
            if match.group(1):  # from ... import ...
                module = match.group(1)
                names = [n.strip() for n in match.group(2).split(',')]
                imports.append(('from', module, names))
            else:  # import ...
                modules = [m.strip() for m in match.group(3).split(',')]
                for module in modules:
                    imports.append(('import', module, None))
    
    return imports


def extract_all_list(content):
    """Extract the __all__ list from a Python file content using AST if possible."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            return [
                                elt.s for elt in node.value.elts 
                                if isinstance(elt, (ast.Str, ast.Constant))
                            ]
    except SyntaxError:
        pass
    
    # Fall back to regex if AST parsing fails
    match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        items_str = match.group(1)
        items = []
        for item in re.finditer(r'["\']([^"\']+)["\']', items_str):
            items.append(item.group(1))
        return items
    
    return []


def format_import(import_info):
    """Format an import tuple back to a string."""
    import_type, module, names = import_info
    if import_type == 'import':
        return f"import {module}"
    else:  # from ... import ...
        names_str = ', '.join(names)
        return f"from {module} import {names_str}"


def compare_init_file(original_content, past_content):
    """
    Special comparison for __init__.py files that focuses on imports and __all__ lists.
    Returns a string with the removed content formatted appropriately.
    """
    # Extract imports from both files
    original_imports = extract_imports(original_content)
    past_imports = extract_imports(past_content)
    
    # Find imports that were removed
    removed_imports = []
    for past_import in past_imports:
        if past_import not in original_imports:
            removed_imports.append(format_import(past_import))
    
    # Extract __all__ lists
    original_all = extract_all_list(original_content)
    past_all = extract_all_list(past_content)
    
    # Find items that were removed from __all__
    removed_all_items = [item for item in past_all if item not in original_all]
    
    # Build the output content
    output_lines = []
    
    # Add removed imports
    if removed_imports:
        output_lines.extend(removed_imports)
        if removed_all_items:
            output_lines.append("")  # Add a blank line between imports and __all__
    
    # Add removed __all__ items
    if removed_all_items:
        output_lines.append(f'__all__ = {str(removed_all_items)}')
    
    return '\n'.join(output_lines)


def compare_files(original_file, past_file, output_file):
    """Compare two files and save the differences."""
    original_content = get_file_content(original_file)
    past_content = get_file_content(past_file)
    
    # Skip if both files are empty or identical
    if original_content == past_content:
        return False
    
    # Special handling for __init__.py files
    if os.path.basename(original_file) == "__init__.py" or os.path.basename(past_file) == "__init__.py":
        removed_content = compare_init_file(original_content, past_content)
    else:
        # For other Python files, use a more general approach
        original_lines = original_content.splitlines()
        past_lines = past_content.splitlines()
        
        # Use difflib to find differences
        diff = difflib.unified_diff(
            original_lines, 
            past_lines,
            n=0,  # No context lines
            lineterm=''
        )
        
        # Extract only added lines (which represent content removed from original)
        removed_lines = []
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                # Remove the '+' prefix
                removed_lines.append(line[1:])
        
        removed_content = '\n'.join(removed_lines)
    
    # If there are differences, save them
    if removed_content:
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Ensure the file is created even if the directory is empty
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(removed_content)
        
        return True
    
    return False


def compare_repositories(original_repo, past_repo, output_path, ignore_list):
    """
    Compare two repositories and save the differences.
    
    Args:
        original_repo: Path to the original repository (with removed contents)
        past_repo: Path to the past repository (with all contents)
        output_path: Path where to save the differences
        ignore_list: List of directories or files to ignore
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Get all files in the past repository
    past_files = []
    for root, dirs, files in os.walk(past_repo):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_list]
        
        for file in files:
            if file not in ignore_list:
                rel_path = os.path.relpath(os.path.join(root, file), past_repo)
                past_files.append(rel_path)
    
    # Get all files in the original repository
    original_files = []
    for root, dirs, files in os.walk(original_repo):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_list]
        
        for file in files:
            if file not in ignore_list:
                rel_path = os.path.relpath(os.path.join(root, file), original_repo)
                original_files.append(rel_path)
    
    # Compare files that exist in both repositories
    common_files = set(past_files).intersection(set(original_files))
    files_compared = 0
    files_with_diff = 0
    
    for rel_path in common_files:
        original_file = os.path.join(original_repo, rel_path)
        past_file = os.path.join(past_repo, rel_path)
        output_file = os.path.join(output_path, rel_path)
        
        files_compared += 1
        if compare_files(original_file, past_file, output_file):
            files_with_diff += 1
            print(f"Differences found in: {rel_path}")
    
    # Find files that exist only in the past repository (completely removed files)
    only_in_past = set(past_files) - set(original_files)
    files_only_in_past = 0
    
    for rel_path in only_in_past:
        past_file = os.path.join(past_repo, rel_path)
        output_file = os.path.join(output_path, rel_path)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        try:
            # Copy the file as is, since it was completely removed
            shutil.copy2(past_file, output_file)
            files_only_in_past += 1
            print(f"File only in past repository: {rel_path}")
        except Exception as e:
            print(f"Error copying file {rel_path}: {str(e)}")
    
    # Find files that exist only in the original repository (newly added files)
    only_in_original = set(original_files) - set(past_files)
    files_only_in_original = 0
    
    # Copy files that exist only in the original repository to the output directory
    for rel_path in only_in_original:
        original_file = os.path.join(original_repo, rel_path)
        output_file = os.path.join(output_path, rel_path)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        try:
            # Copy the file as is, since it was newly added
            shutil.copy2(original_file, output_file)
            files_only_in_original += 1
            print(f"File only in original repository: {rel_path}")
        except Exception as e:
            print(f"Error copying file {rel_path}: {str(e)}")
    
    # Verify that files were actually created in the output directory
    created_files = []
    for root, dirs, files in os.walk(output_path):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), output_path)
            created_files.append(rel_path)
    
    print(f"Created {len(created_files)} files in output directory")
    
    return files_compared, files_with_diff, files_only_in_past, files_only_in_original


def main():
    """Main function."""
    args = parse_arguments()
    
    # Validate paths
    if not os.path.isdir(args.original_repo):
        print(f"Error: Original repository path '{args.original_repo}' is not a directory.")
        sys.exit(1)
    
    if not os.path.isdir(args.past_repo):
        print(f"Error: Past repository path '{args.past_repo}' is not a directory.")
        sys.exit(1)
    
    print(f"Comparing repositories:")
    print(f"  Original: {args.original_repo}")
    print(f"  Past: {args.past_repo}")
    print(f"  Output: {args.output_path}")
    print(f"  Ignoring: {args.ignore}")
    
    # Compare repositories
    files_compared, files_with_diff, files_only_in_past, files_only_in_original = compare_repositories(
        args.original_repo, 
        args.past_repo, 
        args.output_path,
        args.ignore
    )
    
    # Print summary
    print("\nComparison complete!")
    print(f"Files compared: {files_compared}")
    print(f"Files with differences: {files_with_diff}")
    print(f"Files only in past repository: {files_only_in_past}")
    print(f"Files only in original repository: {files_only_in_original}")
    print(f"Total differences: {files_with_diff + files_only_in_past + files_only_in_original}")
    print(f"Differences saved to: {args.output_path}")


if __name__ == "__main__":
    main()