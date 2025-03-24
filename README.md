# Git Branch Update and Merge Helper

A simple one-button solution to update and merge branches from GitHub using WSL2.

## What This Does

This batch file provides a streamlined way to:

1. Fetch the latest changes from your remote repository
2. Update a source branch (default: main)
3. Merge those changes into your target branch
4. Handle merge conflicts detection
5. Optionally push the changes back to the remote repository

## How to Use

### Basic Usage

1. Double-click on `git-update-merge.bat`
2. Enter your target branch name when prompted
3. Confirm the operation
4. Follow the prompts in the WSL terminal

### Advanced Usage

You can also run the batch file with parameters:

```
git-update-merge.bat [source_branch] [target_branch]
```

For example:
```
git-update-merge.bat main feature-branch
```

## Requirements

- Windows 10/11 with WSL2 installed
- Git installed in your WSL2 environment
- A git repository cloned in your WSL2 environment

## How It Works

1. The batch file creates a temporary shell script in your Windows temp directory
2. It converts the Windows path to a WSL path
3. It makes the script executable and runs it in WSL
4. The shell script performs all the git operations
5. The temporary script is deleted after execution

## Customization

You can modify the default source branch by editing line 7 in the batch file:

```batch
set SOURCE_BRANCH=main
```

Change `main` to your preferred default branch name (e.g., `master`, `develop`, etc.).