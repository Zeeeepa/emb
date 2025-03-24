# Git Branch Update and Merge Helper

A simple Windows batch script that uses WSL2 to streamline git branch updates and merges.

## Features

- One-click solution to update and merge branches
- Fetches the latest changes from your remote repository
- Updates a source branch (default: main)
- Merges those changes into your target branch
- Detects and reports merge conflicts
- Optionally pushes changes back to remote

## Requirements

- Windows with WSL2 installed
- Git installed in your WSL2 environment

## Installation

1. Download the `git-update-merge.bat` file
2. Place it in a convenient location (e.g., your desktop or a scripts folder)
3. Optionally, create a shortcut to the batch file for even quicker access

## Usage

### Basic Usage

1. Double-click on `git-update-merge.bat`
2. Enter your target branch name when prompted
3. Confirm the operation
4. Enter the path to your git repository in WSL (e.g., ~/projects/myrepo)
5. Follow the prompts in the WSL terminal

### Command Line Usage

You can also run the script with parameters:

```
git-update-merge.bat [source_branch] [target_branch]
```

For example:
```
git-update-merge.bat main feature/new-feature
```

This will:
1. Update the `main` branch from the remote repository
2. Merge those changes into your `feature/new-feature` branch
3. Check for any merge conflicts
4. Give you the option to push the changes back to the remote

## How It Works

The batch file creates a temporary shell script that runs in WSL2 to handle all the git operations. This approach avoids issues with Windows command prompt not supporting git commands directly.

## Troubleshooting

- **Error: Repository path not found** - Make sure you enter the correct path to your git repository in WSL format (e.g., ~/projects/myrepo)
- **Error: Branch not found** - Verify that both source and target branches exist in your repository
- **Merge conflicts** - If conflicts are detected, you'll need to resolve them manually in your preferred editor

## Customization

You can modify the batch file to:
- Change the default source branch
- Add additional git operations
- Customize the output messages