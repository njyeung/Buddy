@echo off
REM Batch script to install minimal C++ build tools for Python compilation
REM Run this as Administrator

echo Installing Microsoft C++ Build Tools (minimal setup)...

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script must be run as Administrator. Right-click and 'Run as Administrator'
    pause
    exit /b 1
)

REM Create temp directory
set TEMP_DIR=%TEMP%\VSBuildTools
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM Download Visual Studio Build Tools
set BUILD_TOOLS_URL=https://aka.ms/vs/17/release/vs_buildtools.exe
set BUILD_TOOLS_PATH=%TEMP_DIR%\vs_buildtools.exe

echo Downloading Visual Studio Build Tools...
powershell -Command "Invoke-WebRequest -Uri '%BUILD_TOOLS_URL%' -OutFile '%BUILD_TOOLS_PATH%' -UseBasicParsing"

if not exist "%BUILD_TOOLS_PATH%" (
    echo Download failed!
    pause
    exit /b 1
)

echo Download completed.

REM Install with minimal C++ components needed for Python
echo Installing C++ build tools (this may take 10-15 minutes)...
echo Please wait, this runs silently in the background...

"%BUILD_TOOLS_PATH%" --quiet --wait ^
    --add Microsoft.VisualStudio.Workload.MSBuildTools ^
    --add Microsoft.VisualStudio.Workload.VCTools ^
    --add Microsoft.Component.MSBuild ^
    --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
    --add Microsoft.VisualStudio.Component.VC.CMake.Project ^
    --add Microsoft.VisualStudio.Component.Windows10SDK.19041

if %errorLevel% equ 0 (
    echo Installation completed successfully!
) else (
    echo Installation may have failed. Error code: %errorLevel%
)

REM Cleanup
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo Installation completed!
echo.
echo Next steps:
echo 1. Close and reopen your terminal/command prompt
echo 2. Activate your Python virtual environment  
echo 3. Run: pip install TTS^>=0.22.0
echo.
echo The build tools are now ready for compiling Python packages with C++ extensions.

pause