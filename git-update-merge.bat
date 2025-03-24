@echo off
setlocal enabledelayedexpansion

echo ===================================
echo Git Branch Update and Merge Helper
echo ===================================
echo.

REM Get source and target branches from command line arguments or prompt
set SOURCE_BRANCH=main
set TARGET_BRANCH=

if not "%~1"=="" (
    set SOURCE_BRANCH=%~1
)
if not "%~2"=="" (
    set TARGET_BRANCH=%~2
)

if "%TARGET_BRANCH%"=="" (
    set /p TARGET_BRANCH=Enter target branch name: 
)

echo Source branch: %SOURCE_BRANCH%
echo Target branch: %TARGET_BRANCH%
echo.
echo This will update %SOURCE_BRANCH% from remote and merge it into %TARGET_BRANCH%
echo.
set /p CONFIRM=Continue? (Y/N): 

if /i not "%CONFIRM%"=="Y" (
    echo Operation cancelled.
    goto :EOF
)

REM Get the repository path in WSL
set /p REPO_PATH=Enter the path to your git repository in WSL (e.g., ~/projects/myrepo): 

REM Create a temporary script to run in WSL
set TEMP_DIR=%TEMP%\git-update-merge-%RANDOM%
mkdir %TEMP_DIR%
set TEMP_SCRIPT=%TEMP_DIR%\update-merge.sh

echo #!/bin/bash > %TEMP_SCRIPT%
echo cd %REPO_PATH% >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Fetching latest changes..." >> %TEMP_SCRIPT%
echo git fetch >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Checking out source branch: %SOURCE_BRANCH%" >> %TEMP_SCRIPT%
echo git checkout %SOURCE_BRANCH% >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Pulling latest changes for %SOURCE_BRANCH%..." >> %TEMP_SCRIPT%
echo git pull >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Checking out target branch: %TARGET_BRANCH%" >> %TEMP_SCRIPT%
echo git checkout %TARGET_BRANCH% >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Merging %SOURCE_BRANCH% into %TARGET_BRANCH%..." >> %TEMP_SCRIPT%
echo git merge %SOURCE_BRANCH% >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo MERGE_STATUS=$? >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo if [ $MERGE_STATUS -ne 0 ]; then >> %TEMP_SCRIPT%
echo   echo "Merge conflict detected!" >> %TEMP_SCRIPT%
echo   echo "Please resolve conflicts manually, then commit the changes." >> %TEMP_SCRIPT%
echo   exit 1 >> %TEMP_SCRIPT%
echo fi >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Merge completed successfully!" >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo read -p "Push changes to remote? (y/n): " PUSH_CONFIRM >> %TEMP_SCRIPT%
echo if [ "$PUSH_CONFIRM" = "y" ] || [ "$PUSH_CONFIRM" = "Y" ]; then >> %TEMP_SCRIPT%
echo   echo "Pushing changes to remote..." >> %TEMP_SCRIPT%
echo   git push >> %TEMP_SCRIPT%
echo   echo "Push completed!" >> %TEMP_SCRIPT%
echo else >> %TEMP_SCRIPT%
echo   echo "Changes not pushed to remote." >> %TEMP_SCRIPT%
echo fi >> %TEMP_SCRIPT%
echo. >> %TEMP_SCRIPT%
echo echo "Operation completed!" >> %TEMP_SCRIPT%

REM Make the script executable in WSL and run it
wsl chmod +x %TEMP_SCRIPT:\=/%
wsl %TEMP_SCRIPT:\=/%

REM Clean up
rmdir /s /q %TEMP_DIR%

echo.
echo Done!