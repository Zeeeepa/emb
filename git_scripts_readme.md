# Git Automation Scripts

This directory contains batch scripts to automate common Git operations for the repository.

## Available Scripts

### 1. Auto Merge PR (`auto_merge_pr.bat`)

This script automatically finds the most recent PR and merges it into the main branch.

**Features:**
- Automatically identifies the most recent PR
- Shows PR details before merging
- Requires confirmation before proceeding with the merge
- Cleans up temporary branches after merging
- Checks if you're in a git repository before proceeding
- Uses GitHub CLI if available for better PR detection

**Usage:**
1. Double-click the `auto_merge_pr.bat` file or run it from the command line
2. Review the PR details that are displayed
3. Type 'y' to confirm the merge or 'n' to cancel

### 2. Revert Last Merge (`revert_last_merge.bat`)

This script identifies and reverts the most recent merge commit on the main branch.

**Features:**
- Automatically identifies the last merge commit
- Shows merge commit details before reverting
- Creates a separate branch for the revert operation
- Requires confirmation before pushing the revert
- Cleans up temporary branches after reverting
- Checks if you're in a git repository before proceeding

**Usage:**
1. Double-click the `revert_last_merge.bat` file or run it from the command line
2. Review the merge commit details that are displayed
3. Type 'y' to confirm the revert or 'n' to cancel
4. After the revert is created, you'll be asked if you want to push it to main
5. Type 'y' to push the revert to main or 'n' to keep it in a local branch

## Requirements

- Git must be installed and available in your PATH
- You must have appropriate permissions to push to the main branch
- The scripts should be run from the root directory of the repository
- GitHub CLI (`gh`) is recommended but not required for better PR detection

## Notes

- These scripts include confirmation steps to prevent accidental operations
- Both scripts will update your local main branch before performing any operations
- If you choose not to push a revert, the script will tell you how to do it later
- The scripts will check if you're in a git repository and exit with an error if not