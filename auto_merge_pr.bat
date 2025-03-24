@echo off
echo ===== Auto Merge Most Recent PR to Main =====
echo.

REM Check if we're in a git repository
git rev-parse --is-inside-work-tree >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Not a git repository. Please run this script from the root of a git repository.
    exit /b 1
)

REM Store the current directory
set REPO_DIR=%CD%

REM Ensure we're on the main branch and it's up to date
echo Updating main branch...
git checkout main
git pull origin main

REM Find the most recent open PR using GitHub CLI if available
where gh >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Using GitHub CLI to find most recent PR...
    for /f "tokens=1" %%a in ('gh pr list --limit 1 --json number --jq ".[0].number"') do (
        set PR_NUM=%%a
    )
) else (
    REM Fallback method using git commands
    echo GitHub CLI not found, using git commands...
    
    REM Get the list of remote PRs
    git ls-remote --refs origin | findstr "refs/pull/" > "%TEMP%\pr_list.txt"
    
    REM Sort the list in reverse order to get the most recent PR
    type "%TEMP%\pr_list.txt" | sort /r > "%TEMP%\pr_list_sorted.txt"
    
    REM Get the first PR that has /head in it
    for /f "tokens=3 delims=/" %%a in ('findstr /i "/head" "%TEMP%\pr_list_sorted.txt"') do (
        set PR_NUM=%%a
        goto :found_pr
    )
    
    :found_pr
    REM Extract PR number from the ref
    set PR_NUM=%PR_NUM:~0,-5%
    
    REM Clean up temporary files
    del "%TEMP%\pr_list.txt" 2>nul
    del "%TEMP%\pr_list_sorted.txt" 2>nul
)

echo Found PR #%PR_NUM%

REM Fetch and checkout the PR branch
echo Fetching PR #%PR_NUM%...
git fetch origin pull/%PR_NUM%/head:pr-%PR_NUM%
git checkout pr-%PR_NUM%

REM Show PR details for confirmation
echo.
echo PR Details:
git log -1 --pretty=format:"Author: %%an%%nDate: %%ad%%nTitle: %%s%%n%%n%%b"
echo.

REM Ask for confirmation
set /p CONFIRM=Do you want to merge this PR into main? (y/n): 

if /i "%CONFIRM%" neq "y" (
    echo Merge cancelled.
    git checkout main
    exit /b 1
)

REM Merge the PR into main
echo Merging PR #%PR_NUM% into main...
git checkout main
git merge --no-ff pr-%PR_NUM% -m "Merge PR #%PR_NUM%"

REM Push the merge to origin
echo Pushing changes to origin...
git push origin main

echo.
echo PR #%PR_NUM% has been successfully merged into main!
echo.

REM Clean up the local PR branch
git branch -D pr-%PR_NUM%

exit /b 0