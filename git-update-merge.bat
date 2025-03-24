@echo off
echo ===================================
echo Git Branch Update and Merge Helper
echo ===================================

REM Set default values
set SOURCE_BRANCH=main
set TARGET_BRANCH=

REM Check if parameters are provided
if not "%~1"=="" set SOURCE_BRANCH=%~1
if not "%~2"=="" set TARGET_BRANCH=%~2

REM If target branch is not provided, prompt for it
if "%TARGET_BRANCH%"=="" (
    set /p TARGET_BRANCH="Enter your target branch name: "
)

echo.
echo Source branch: %SOURCE_BRANCH%
echo Target branch: %TARGET_BRANCH%
echo.
echo This will update %SOURCE_BRANCH% from remote and merge it into %TARGET_BRANCH%
echo.
set /p CONFIRM="Continue? (Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo Operation cancelled.
    goto :EOF
)

REM Create a temporary directory for the script
set SCRIPT_DIR=%TEMP%\git-update-script
mkdir %SCRIPT_DIR% 2>nul

REM Create the temporary shell script
echo #!/bin/bash > "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "====================================" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Git Branch Update and Merge Helper" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "====================================" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo SOURCE_BRANCH="%SOURCE_BRANCH%" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo TARGET_BRANCH="%TARGET_BRANCH%" >> "%SCRIPT_DIR%\git-update-merge.sh"

REM Add repository directory selection
echo echo "Enter the path to your git repository in WSL (e.g., ~/projects/myrepo):" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo read -p "> " REPO_DIR >> "%SCRIPT_DIR%\git-update-merge.sh"
echo if [ ! -d "$REPO_DIR" ]; then >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   echo "Directory does not exist. Please check the path and try again." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   exit 1 >> "%SCRIPT_DIR%\git-update-merge.sh"
echo fi >> "%SCRIPT_DIR%\git-update-merge.sh"
echo cd "$REPO_DIR" >> "%SCRIPT_DIR%\git-update-merge.sh"

echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Fetching latest changes from remote..." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo git fetch origin >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Checking out source branch: $SOURCE_BRANCH" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo git checkout $SOURCE_BRANCH >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Pulling latest changes for $SOURCE_BRANCH" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo git pull origin $SOURCE_BRANCH >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Checking out target branch: $TARGET_BRANCH" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo git checkout $TARGET_BRANCH >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Merging $SOURCE_BRANCH into $TARGET_BRANCH" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo git merge $SOURCE_BRANCH >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Checking for merge conflicts..." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo CONFLICTS=$(git status --porcelain | grep -E "^(U.|.U)" | wc -l) >> "%SCRIPT_DIR%\git-update-merge.sh"
echo if [ "$CONFLICTS" -gt 0 ]; then >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   echo "MERGE CONFLICTS DETECTED!" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   echo "Please resolve conflicts manually, then commit the changes." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   echo "Conflicted files:" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   git status --porcelain | grep -E "^(U.|.U)" | awk '{print $2}' >> "%SCRIPT_DIR%\git-update-merge.sh"
echo else >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   echo "No conflicts detected." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   echo "Would you like to push the changes to remote? (y/n)" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   read PUSH_CONFIRM >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   if [ "$PUSH_CONFIRM" = "y" ] || [ "$PUSH_CONFIRM" = "Y" ]; then >> "%SCRIPT_DIR%\git-update-merge.sh"
echo     echo "Pushing changes to remote..." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo     git push origin $TARGET_BRANCH >> "%SCRIPT_DIR%\git-update-merge.sh"
echo     echo "Push completed successfully!" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   else >> "%SCRIPT_DIR%\git-update-merge.sh"
echo     echo "Changes were not pushed to remote." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo   fi >> "%SCRIPT_DIR%\git-update-merge.sh"
echo fi >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "" >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Operation completed." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo echo "Press Enter to exit..." >> "%SCRIPT_DIR%\git-update-merge.sh"
echo read -p "" >> "%SCRIPT_DIR%\git-update-merge.sh"

REM Convert Windows path to WSL path
for /f "tokens=*" %%a in ('wsl wslpath -u "%SCRIPT_DIR%\git-update-merge.sh"') do set WSL_PATH=%%a

REM Make the script executable and run it
echo Running script in WSL...
wsl chmod +x %WSL_PATH% ^&^& %WSL_PATH%

REM Clean up
rmdir /s /q %SCRIPT_DIR%

echo.
echo Press any key to exit...
pause > nul