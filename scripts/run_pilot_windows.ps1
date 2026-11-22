# AEMA MemoryAgentBench Pilot Evaluation Runner for Windows Gaming PC
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -Provider anthropic -Model claude-3-5-haiku-20241022
#   powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -Provider openai -Model gpt-4o-mini
#   powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -Provider gemini -Model gemini-1.5-flash
#   powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -Provider ollama -Model llama3.2:3b

param (
    [string]$Provider = "anthropic",
    [string]$Model = "",
    [string]$Competency = "all",
    [int]$Limit = 25,
    [int]$Trials = 1,
    [int]$Seed = 42
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " AEMA MemoryAgentBench Pilot Evaluation (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Validate API Keys / Provider Connectivity
Write-Host "`n[1/4] Validating Provider Configuration..." -ForegroundColor Yellow
$provUpper = $Provider.ToUpper()
$envVarName = "${provUpper}_API_KEY"

if ($Provider.ToLower() -eq "ollama") {
    Write-Host "  Using local Ollama provider. Checking localhost:11434..."
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
        Write-Host "  [+] Ollama local server is active." -ForegroundColor Green
    } catch {
        Write-Error "[-] Ollama server is not responding at http://localhost:11434. Please start Ollama before running."
        exit 1
    }
} else {
    $apiKey = [System.Environment]::GetEnvironmentVariable($envVarName)
    if (-not $apiKey) {
        # Check current process scope
        $apiKey = (Get-Item "env:$envVarName" -ErrorAction SilentlyContinue).Value
    }

    if (-not $apiKey) {
        Write-Error "[-] Missing API Key: Environment variable '$envVarName' is NOT set.`n    Please set it before running:`n    `$env:$envVarName = 'your-api-key-here'"
        exit 1
    }
    Write-Host "  [+] $envVarName detected (length: $($apiKey.Length))." -ForegroundColor Green
}

# 2. Check and Activate Virtual Environment
Write-Host "`n[2/4] Resolving Python Environment..." -ForegroundColor Yellow
$venvPython = "$PSScriptRoot\..\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Host "  [+] Using virtual environment Python at $venvPython" -ForegroundColor Green
    $pythonExec = $venvPython
} else {
    Write-Host "  [*] Using system Python from PATH"
    $pythonExec = "python"
}

# 3. Verify Manifest Integrity
Write-Host "`n[3/4] Verifying Pilot Manifest Checksums..." -ForegroundColor Yellow
$verifierScript = "$PSScriptRoot\..\benchmarks\data\memoryagentbench\download_and_verify.ps1"
if (Test-Path $verifierScript) {
    & powershell -ExecutionPolicy Bypass -File $verifierScript
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[-] Manifest verification failed."
        exit 1
    }
}

# 4. Execute Pilot Benchmark
Write-Host "`n[4/4] Launching Pilot Benchmark Execution..." -ForegroundColor Yellow
Write-Host "  Provider:     $Provider"
Write-Host "  Competency:   $Competency"
Write-Host "  Limit:        $Limit per split"
Write-Host "  Conditions:   vanilla, naive_rag, recency, symmetric, adaptive"
Write-Host "  Seed:         $Seed"

$runnerArgs = @(
    "-m", "benchmarks.memoryagentbench_runner",
    "--provider", $Provider,
    "--competency", $Competency,
    "--limit", $Limit,
    "--trials", $Trials,
    "--seed", $Seed
)

if ($Model) {
    $runnerArgs += @("--model", $Model)
}

& $pythonExec $runnerArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host " [+] Pilot Evaluation Finished Successfully!" -ForegroundColor Green
    Write-Host " Results saved to: benchmarks\results\memoryagentbench\" -ForegroundColor Green
    Write-Host "=================================================="
} else {
    Write-Error "`n[-] Execution ended with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}
