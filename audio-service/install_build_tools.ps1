# PowerShell script to install minimal C++ build tools for Python compilation
# Run this as Administrator

Write-Host "Installing Microsoft C++ Build Tools (minimal setup)..." -ForegroundColor Green

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script must be run as Administrator. Right-click and 'Run as Administrator'" -ForegroundColor Red
    exit 1
}

# Create temp directory
$tempDir = "$env:TEMP\VSBuildTools"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# Download Visual Studio Build Tools
$buildToolsUrl = "https://aka.ms/vs/17/release/vs_buildtools.exe"
$buildToolsPath = "$tempDir\vs_buildtools.exe"

Write-Host "Downloading Visual Studio Build Tools..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $buildToolsUrl -OutFile $buildToolsPath -UseBasicParsing
    Write-Host "Download completed." -ForegroundColor Green
} catch {
    Write-Host "Download failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Install with minimal C++ components needed for Python
Write-Host "Installing C++ build tools (this may take 10-15 minutes)..." -ForegroundColor Yellow
$installArgs = @(
    '--quiet'
    '--wait'
    '--add', 'Microsoft.VisualStudio.Workload.MSBuildTools'
    '--add', 'Microsoft.VisualStudio.Workload.VCTools'
    '--add', 'Microsoft.Component.MSBuild'
    '--add', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64'
    '--add', 'Microsoft.VisualStudio.Component.VC.CMake.Project'
    '--add', 'Microsoft.VisualStudio.Component.Windows10SDK.19041'
)

try {
    Start-Process -FilePath $buildToolsPath -ArgumentList $installArgs -Wait -NoNewWindow
    Write-Host "Installation completed successfully!" -ForegroundColor Green
} catch {
    Write-Host "Installation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Cleanup
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host @"

Installation completed!

Next steps:
1. Close and reopen your terminal/command prompt
2. Activate your Python virtual environment
3. Run: pip install TTS>=0.22.0

The build tools are now ready for compiling Python packages with C++ extensions.
"@ -ForegroundColor Green

# Verify installation
Write-Host "Verifying installation..." -ForegroundColor Yellow
$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vsWhere) {
    $buildTools = & $vsWhere -products Microsoft.VisualStudio.Product.BuildTools -format json | ConvertFrom-Json
    if ($buildTools) {
        Write-Host "✓ Visual Studio Build Tools detected" -ForegroundColor Green
        Write-Host "Version: $($buildTools.displayName)" -ForegroundColor Gray
        Write-Host "Path: $($buildTools.installationPath)" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ Could not verify installation, but it should work" -ForegroundColor Yellow
}

Write-Host "`nYou can now install TTS and other packages requiring compilation!" -ForegroundColor Green