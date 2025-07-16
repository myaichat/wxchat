@REM Debugging: Echo the initial arguments
echo Initial Arguments: %*

@REM Check if a Conda environment name is provided
@if "%~1"=="" (
    echo Error: No Conda environment specified.
    GOTO :End
) else (
    echo Conda environment specified: %~1
    @set CONDA_ENV=%~1
)

@REM Check if a script name is provided
@if "%~2"=="" (
    echo No second argument provided. Using default script: ui_down.py
    @set SCRIPT_NAME=ui_down.py
) else (
    echo Second argument provided: %~2
    @set SCRIPT_NAME=%~2
)

@REM Activate the specified Conda environment
echo Activating conda environment: %CONDA_ENV%
@CALL "C:\tmp\M\miniconda3\condabin\conda.bat" activate %CONDA_ENV%

@REM Navigate to the script directory
echo Changing directory to: "C:\Users\alex_\aichat\ui_interview_copilot"
@cd /d "C:\Users\alex_\aichat\ui_interview_copilot"

@REM Debugging: Echo the script to be executed
echo Script to execute: streamlit run %SCRIPT_NAME%

@REM Verify that the script exists
@if NOT EXIST "%SCRIPT_NAME%" (
    echo Error: Script "%SCRIPT_NAME%" not found in the current directory.
    GOTO :End
)

@REM Execute the Python script
echo Executing Python script: %SCRIPT_NAME%
@CALL streamlit run "%SCRIPT_NAME%"

:End
