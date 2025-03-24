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

REM Create the temporary shell script
echo #!/bin/bash > "%TEMP%\git-update-merge.sh"
echo echo "====================================" >> "%TEMP%\git-update-merge.sh"
echo echo "Git Branch Update and Merge Helper" >> "%TEMP%\git-update-merge.sh"
echo echo "====================================" >> "%TEMP%\git-update-merge.sh"
echo echo "" >> "%TEMP%\git-update-merge.sh"
echo SOURCE_BRANCH="%SOURCE_BRANCH%" >> "%TEMP%\git-update-merge.sh"
echo TARGET_BRANCH="%TARGET_BRANCH%" >> "%TEMP%\git-update-merge.sh"
echo echo "Fetching latest changes from remote..." >> "%TEMP%\git-update-merge.sh"
echo git fetch origin >> "%TEMP%\git-update-merge.sh"
echo echo "" >> "%TEMP%\git-update-merge.sh"
echo echo "Checking out source branch: $SOURCE_BRANCH" >> "%TEMP%\git-update-merge.sh"
echo git checkout $SOURCE_BRANCH >> "%TEMP%\git-update-merge.sh"
echo echo "Pulling latest changes for $SOURCE_BRANCH" >> "%TEMP%\git-update-merge.sh"
echo git pull origin $SOURCE_BRANCH >> "%TEMP%\git-update-merge.sh"
echo echo "" >> "%TEMP%\git-update-merge.sh"
echo echo "Checking out target branch: $TARGET_BRANCH" >> "%TEMP%\git-update-merge.sh"
echo git checkout $TARGET_BRANCH >> "%TEMP%\git-update-merge.sh"
echo echo "" >> "%TEMP%\git-update-merge.sh"
echo echo "Merging $SOURCE_BRANCH into $TARGET_BRANCH" >> "%TEMP%\git-update-merge.sh"
echo git merge $SOURCE_BRANCH >> "%TEMP%\git-update-merge.sh"
echo echo "" >> "%TEMP%\git-update-merge.sh"
echo echo "Checking for merge conflicts..." >> "%TEMP%\git-update-merge.sh"
echo if [ $(git status --porcelain | grep -E "^(U.|.U)" | wc -l) -gt 0 ]; then >> "%TEMP%\git-update-merge.sh"
echo   echo "MERGE CONFLICTS DETECTED!" >> "%TEMP%\git-update-merge.sh"
echo   echo "Please resolve conflicts manually, then commit the changes." >> "%TEMP%\git-update-merge.sh"
echo   echo "Conflicted files:" >> "%TEMP%\git-update-merge.sh"
echo   git status --porcelain | grep -E "^(U.|.U)" | awk '{print $2}' >> "%TEMP%\git-update-merge.sh"
echo else >> "%TEMP%\git-update-merge.sh"
echo   echo "No conflicts detected." >> "%TEMP%\git-update-merge.sh"
echo   echo "Would you like to push the changes to remote? (y/n)" >> "%TEMP%\git-update-merge.sh"
echo   read PUSH_CONFIRM >> "%TEMP%\git-update-merge.sh"
echo   if [ "$PUSH_CONFIRM" = "y" ] || [ "$PUSH_CONFIRM" = "Y" ]; then >> "%TEMP%\git-update-merge.sh"
echo     echo "Pushing changes to remote..." >> "%TEMP%\git-update-merge.sh"
echo     git push origin $TARGET_BRANCH >> "%TEMP%\git-update-merge.sh"
echo     echo "Push completed successfully!" >> "%TEMP%\git-update-merge.sh"
echo   else >> "%TEMP%\git-update-merge.sh"
echo     echo "Changes were not pushed to remote." >> "%TEMP%\git-update-merge.sh"
echo   fi >> "%TEMP%\git-update-merge.sh"
echo fi >> "%TEMP%\git-update-merge.sh"
echo echo "" >> "%TEMP%\git-update-merge.sh"
echo echo "Operation completed." >> "%TEMP%\git-update-merge.sh"
echo echo "Press Enter to exit..." >> "%TEMP%\git-update-merge.sh"
echo read -p "" >> "%TEMP%\git-update-merge.sh"

REM Convert Windows path to WSL path
for /f "tokens=*" %%a in ('wsl wslpath -u "%TEMP%\git-update-merge.sh"') do set WSL_PATH=%%a

REM Make the script executable and run it
echo Running script in WSL...
wsl chmod +x %WSL_PATH% ^&^& %WSL_PATH%

REM Clean up
del "%TEMP%\git-update-merge.sh"

echo.
echo Press any key to exit...
pause > nul