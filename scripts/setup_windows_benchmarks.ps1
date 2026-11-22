# AEMA Benchmark Setup and Verification Script for Windows Gaming PC
# Compatible with Windows 10/11 PowerShell 5.1 / PowerShell Core 7+
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows_benchmarks.ps1

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " AEMA Research Evaluation Setup - Windows Host" -ForegroundColor Cyan
Write-Host "=================================================="

# 1. System Hardware & Environment Audit
Write-Host "`n[1/5] Auditing System Environment..." -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$ramGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$gpu = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name -First 1

Write-Host "  OS:       $($os.Caption) ($($os.Version))"
Write-Host "  CPU:      $($cpu.Name)"
Write-Host "  RAM:      $ramGB GB"
Write-Host "  GPU:      $gpu"

# Check Python installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "[-] Python not found in PATH. Please install Python 3.10+ (64-bit)."
    exit 1
}

$pyVersion = & python --version 2>&1
Write-Host "  Python:   $pyVersion"

# 2. Virtual Environment Setup
Write-Host "`n[2/5] Checking Python Virtual Environment..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment in .venv..."
    & python -m venv .venv
}

$venvPython = "$PSScriptRoot\..\.venv\Scripts\python.exe"
$venvPip = "$PSScriptRoot\..\.venv\Scripts\pip.exe"
$venvPytest = "$PSScriptRoot\..\.venv\Scripts\pytest.exe"

if (-not (Test-Path $venvPython)) {
    # Fallback to system python if venv structure differs
    $venvPython = "python"
    $venvPip = "pip"
    $venvPytest = "pytest"
}

# 3. Installing Pinned Dependencies
Write-Host "`n[3/5] Installing Pinned Benchmark Dependencies..." -ForegroundColor Yellow
$reqFile = "$PSScriptRoot\..\requirements-benchmarks.txt"
if (Test-Path $reqFile) {
    & $venvPip install -r $reqFile
} else {
    Write-Warning "[-] requirements-benchmarks.txt not found, skipping pip install."
}

# 4. Verifying Pilot Manifests
Write-Host "`n[4/5] Verifying MemoryAgentBench Manifest Integrity..." -ForegroundColor Yellow
$verifierScript = "$PSScriptRoot\..\benchmarks\data\memoryagentbench\download_and_verify.ps1"
if (Test-Path $verifierScript) {
    & powershell -ExecutionPolicy Bypass -File $verifierScript
} else {
    Write-Warning "[-] download_and_verify.ps1 not found."
}

# 5. Executing Test Suite
Write-Host "`n[5/5] Running Independent Evaluator Tests..." -ForegroundColor Yellow
& $venvPytest tests\test_memoryagentbench_evaluator.py -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host " [+] Windows Gaming PC Setup & Verification: PASSED" -ForegroundColor Green
    Write-Host "=================================================="
    exit 0
} else {
    Write-Error "`n[-] Setup test execution failed with exit code $LASTEXITCODE."
    exit 1
}
