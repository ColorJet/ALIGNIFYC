# Build script for Windows (PowerShell)

param(
    [switch]$WithCUDA = $false,
    [switch]$WithPython = $false,
    [string]$Config = "Release"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Alinify Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$BUILD_DIR = "build"
$INSTALL_DIR = "install"

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (!(Get-Command cmake -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: CMake not found. Please install CMake 3.20+" -ForegroundColor Red
    Write-Host "Download from: https://cmake.org/download/" -ForegroundColor Yellow
    exit 1
}

$CMakeVersion = cmake --version | Select-Object -First 1
Write-Host "Found: $CMakeVersion" -ForegroundColor Gray

if (!(Get-Command cl -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: Visual Studio compiler (cl.exe) not found in PATH" -ForegroundColor Yellow
    Write-Host "You may need to run this from 'Developer Command Prompt for VS'" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Build Configuration:" -ForegroundColor Cyan
Write-Host "  Config Type: $Config" -ForegroundColor White
Write-Host "  CUDA: $WithCUDA" -ForegroundColor White
Write-Host "  Python Bindings: $WithPython" -ForegroundColor White
Write-Host ""

# Create build directory
if (!(Test-Path $BUILD_DIR)) {
    Write-Host "Creating build directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BUILD_DIR | Out-Null
}

Set-Location $BUILD_DIR

# Build CMake arguments
$CMakeArgs = @(
    "..",
    "-G", "Visual Studio 17 2022",
    "-A", "x64",
    "-DCMAKE_BUILD_TYPE=$Config"
)

# Add CUDA option
if ($WithCUDA) {
    $CMakeArgs += "-DUSE_CUDA=ON"
    Write-Host "NOTE: CUDA Toolkit must be installed for GPU support" -ForegroundColor Yellow
} else {
    $CMakeArgs += "-DUSE_CUDA=OFF"
}

# Add Python bindings option
if ($WithPython) {
    $CMakeArgs += "-DBUILD_PYTHON_BINDINGS=ON"
    Write-Host "NOTE: Python 3.10+ with dev headers must be installed" -ForegroundColor Yellow
} else {
    $CMakeArgs += "-DBUILD_PYTHON_BINDINGS=OFF"
}

# Check for optional dependencies and add to CMAKE_PREFIX_PATH if found
$PrefixPaths = @()

if (Test-Path "C:/libtorch") {
    $PrefixPaths += "C:/libtorch"
    Write-Host "Found LibTorch at C:/libtorch" -ForegroundColor Green
}

if (Test-Path "C:/ITK/install") {
    $PrefixPaths += "C:/ITK/install"
    Write-Host "Found ITK at C:/ITK/install" -ForegroundColor Green
} elseif (Test-Path "C:/ITK/build") {
    $PrefixPaths += "C:/ITK/build"
    Write-Host "Found ITK at C:/ITK/build" -ForegroundColor Green
}

$QtPath = Get-ChildItem "C:/Qt" -Directory -ErrorAction SilentlyContinue | 
          Where-Object { $_.Name -match "^\d+\.\d+\.\d+$" } | 
          Select-Object -First 1

if ($QtPath) {
    $QtMsvc = Join-Path $QtPath.FullName "msvc2019_64"
    if (Test-Path $QtMsvc) {
        $PrefixPaths += $QtMsvc
        Write-Host "Found Qt at $QtMsvc" -ForegroundColor Green
    }
}

if ($PrefixPaths.Count -gt 0) {
    $CMakeArgs += "-DCMAKE_PREFIX_PATH=$($PrefixPaths -join ';')"
}

Write-Host ""
Write-Host "Configuring CMake..." -ForegroundColor Yellow

cmake @CMakeArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  Configuration Failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "This is normal if dependencies are not installed." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The project will build with available dependencies." -ForegroundColor Cyan
    Write-Host "See QUICKSTART.md for full dependency installation." -ForegroundColor Cyan
    Write-Host ""
    Set-Location ..
    exit 1
}

Write-Host ""
Write-Host "Building..." -ForegroundColor Yellow
cmake --build . --config $Config -j 8

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Build failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host ""
Write-Host "Installing..." -ForegroundColor Yellow
cmake --install . --prefix "../$INSTALL_DIR" --config $Config

Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Build Successful!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Binaries are in: $BUILD_DIR\$Config" -ForegroundColor Cyan
Write-Host "Installed to: $INSTALL_DIR" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Setup Python: .\setup_python.ps1" -ForegroundColor White
Write-Host "  2. Run GUI: python gui\main_gui.py" -ForegroundColor White
Write-Host ""
Write-Host "To build with CUDA: .\build.ps1 -WithCUDA" -ForegroundColor Gray
Write-Host "To build with Python bindings: .\build.ps1 -WithPython" -ForegroundColor Gray
Write-Host ""
