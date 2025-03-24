@echo off
echo ===== Revert Last Merge Commit =====
echo.

REM Store the current directory
set REPO_DIR=%CD%

REM Ensure we're on the main branch and it's up to date
echo Updating main branch...
git checkout main
git pull origin main

REM Find the last merge commit
echo Finding last merge commit...
for /f "tokens=*" %%a in ('git log --merges -n 1 --pretty=format:"%%H"') do (
    set MERGE_COMMIT=%%a
)

REM Show merge commit details for confirmation
echo.
echo Last Merge Commit Details:
git log -1 %MERGE_COMMIT% --pretty=format:"Commit: %%h%%nAuthor: %%an%%nDate: %%ad%%nTitle: %%s%%n%%n%%b"
echo.

REM Ask for confirmation
set /p CONFIRM=Do you want to revert this merge commit? (y/n): 

if /i "%CONFIRM%" neq "y" (
    echo Revert cancelled.
    exit /b 1
)

REM Create a new branch for the revert
set REVERT_BRANCH=revert-merge-%MERGE_COMMIT:~0,7%
echo Creating revert branch: %REVERT_BRANCH%
git checkout -b %REVERT_BRANCH%

REM Revert the merge commit
echo Reverting merge commit %MERGE_COMMIT%...
git revert -m 1 %MERGE_COMMIT%

REM Show the revert commit
echo.
echo Revert Commit Details:
git log -1 --pretty=format:"Commit: %%h%%nAuthor: %%an%%nDate: %%ad%%nTitle: %%s%%n%%n%%b"
echo.

REM Ask for confirmation to push the revert
set /p PUSH_CONFIRM=Do you want to push this revert to main? (y/n): 

if /i "%PUSH_CONFIRM%" neq "y" (
    echo Push cancelled. The revert is still in your local branch %REVERT_BRANCH%.
    echo You can push it later with: git checkout main && git merge %REVERT_BRANCH% && git push origin main
    exit /b 0
)

REM Push the revert to main
echo Pushing revert to main...
git checkout main
git merge --no-ff %REVERT_BRANCH% -m "Merge revert of commit %MERGE_COMMIT:~0,7%"
git push origin main

echo.
echo The last merge commit has been successfully reverted!
echo.

REM Clean up the revert branch
git branch -D %REVERT_BRANCH%

exit /b 0