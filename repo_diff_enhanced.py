#!/usr/bin/env python3
"""
Repository Difference Tool (Enhanced)

This script compares two repositories (original and past) and saves the differences
in a structured way, preserving the project structure and showing only the content
that was removed from the past repository.

This enhanced version specifically focuses on identifying removed content and
preserving it in a way that shows what was removed from the past version.

Usage:
    python repo_diff_enhanced.py <original_repo_path> <past_repo_path> <output_path>

Example:
    python repo_diff_enhanced.py ./original_repo ./past_repo ./diff_output
"""

import os
import sys
import shutil
import difflib
import re
from pathlib import Path
import argparse


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare two repositories and save the differences."
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


def find_removed_content(original_content, past_content):
    """
    Find content that was in the past version but removed in the original.
    
    This function specifically handles the case of identifying what was removed
    from the past version, like imports and entries in __all__ lists.
    """
    # If either file is empty, handle appropriately
    if not original_content and not past_content:
        return ""
    
    # Split content into lines for processing
    original_lines = original_content.splitlines()
    past_lines = past_content.splitlines()
    
    # Use difflib to get a detailed comparison
    differ = difflib.Differ()
    diff = list(differ.compare(original_lines, past_lines))
    
    # Extract lines that were in past but not in original (removed content)
    removed_lines = []
    for line in diff:
        if line.startswith('+ '):  # Lines in past but not in original
            removed_lines.append(line[2:])  # Remove the '+ ' prefix
    
    # Special handling for __all__ lists
    if '__all__' in original_content and '__all__' in past_content:
        # Extract __all__ from both files
        original_all = extract_all_list(original_content)
        past_all = extract_all_list(past_content)
        
        # Find items that were removed from __all__
        removed_items = [item for item in past_all if item not in original_all]
        
        if removed_items:
            # Add a special section for removed __all__ items
            removed_lines.append("\n# Items removed from __all__:")
            removed_lines.append(f'__all__ = {str(removed_items)}')
    
    return '\n'.join(removed_lines)


def extract_all_list(content):
    """Extract the __all__ list from a Python file content."""
    # Look for __all__ = [...] pattern
    match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not match:
        return []
    
    # Extract the items
    items_str = match.group(1)
    # Parse the items (handling quotes and commas)
    items = []
    for item in re.finditer(r'["\']([^"\']+)["\']', items_str):
        items.append(item.group(1))
    
    return items


def compare_files(original_file, past_file, output_file):
    """Compare two files and save the differences."""
    original_content = get_file_content(original_file)
    past_content = get_file_content(past_file)
    
    # Find content that was removed from the past version
    removed_content = find_removed_content(original_content, past_content)
    
    # Special handling for Python files to identify removed imports and __all__ entries
    if original_file.endswith('.py') or past_file.endswith('.py'):
        # Extract imports that were removed
        original_imports = extract_imports(original_content)
        past_imports = extract_imports(past_content)
        removed_imports = [imp for imp in past_imports if imp not in original_imports]
        
        # If we found removed imports, add them to the removed content
        if removed_imports and not removed_content:
            removed_content = '\n'.join(removed_imports)
        elif removed_imports:
            removed_content = '\n'.join(removed_imports) + '\n\n' + removed_content
    
    # If there are differences, save them
    if removed_content:
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(removed_content)
        
        return True
    
    return False


def extract_imports(content):
    """Extract import statements from Python code."""
    imports = []
    # Match both 'import x' and 'from x import y' patterns
    import_patterns = [
        r'^import\s+.*$',  # import statements
        r'^from\s+.*\s+import\s+.*$'  # from ... import statements
    ]
    
    for pattern in import_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            imports.append(match.group(0))
    
    return imports


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
    for rel_path in only_in_past:
        past_file = os.path.join(past_repo, rel_path)
        output_file = os.path.join(output_path, rel_path)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Copy the file as is, since it was completely removed
        shutil.copy2(past_file, output_file)
        files_with_diff += 1
        print(f"File only in past repository: {rel_path}")
    
    return files_compared, files_with_diff, len(only_in_past)


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
    files_compared, files_with_diff, files_only_in_past = compare_repositories(
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
    print(f"Total differences: {files_with_diff + files_only_in_past}")
    print(f"Differences saved to: {args.output_path}")


if __name__ == "__main__":
    main()