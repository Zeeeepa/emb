@echo off
echo ===== Auto Merge Most Recent PR to Main =====
echo.

REM Store the current directory
set REPO_DIR=%CD%

REM Ensure we're on the main branch and it's up to date
echo Updating main branch...
git checkout main
git pull origin main

REM Find the most recent open PR
echo Finding most recent PR...
for /f "tokens=*" %%a in ('git ls-remote --refs origin ^| findstr "refs/pull/" ^| sort /r ^| findstr "/head" ^| head -n 1') do (
    set PR_REF=%%a
)

REM Extract PR number from the ref
for /f "tokens=3 delims=/" %%a in ("%PR_REF%") do (
    set PR_NUM=%%a
)
set PR_NUM=%PR_NUM:~0,-5%

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