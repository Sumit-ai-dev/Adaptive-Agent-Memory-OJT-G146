# AEMA MemoryAgentBench Pilot Evaluation Runner for Windows Gaming PC
# Powered by Local Ollama (Zero paid APIs, 100% genuine local hardware evaluation)
#
# Usage:
#   Smoke Test (2 tasks per condition, ~2 mins):
#     powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -SmokeTest
#
#   Full 50-Task Pilot (25 CR + 25 AR across 5 conditions):
#     powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -FullPilot
#
#   Custom Model or Limit:
#     powershell -ExecutionPolicy Bypass -File scripts\run_pilot_windows.ps1 -Model llama3.1:8b -Limit 10

param (
    [switch]$SmokeTest,
    [switch]$FullPilot,
    [string]$Provider = "ollama",
    [string]$Model = "",
    [string]$Competency = "all",
    [int]$Limit = 0,
    [int]$Trials = 1,
    [int]$Seed = 42
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " AEMA MemoryAgentBench Pilot Evaluation (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 0. Resolve Task Limit
if ($SmokeTest) {
    $Limit = 2
    Write-Host "[*] Mode: SMOKE TEST (2 tasks per competency split)" -ForegroundColor Magenta
} elseif ($FullPilot -or $Limit -eq 0) {
    $Limit = 25
    Write-Host "[*] Mode: FULL PILOT (25 tasks per split, 50 total tasks)" -ForegroundColor Magenta
}

# 1. Health & Hardware Check (via check_ollama.ps1)
if ($Provider.ToLower() -eq "ollama") {
    Write-Host "`n[1/4] Auditing Ollama & Host GPU Hardware..." -ForegroundColor Yellow
    $checkerScript = "$PSScriptRoot\check_ollama.ps1"
    if (Test-Path $checkerScript) {
        & powershell -ExecutionPolicy Bypass -File $checkerScript
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[-] Ollama health check failed. Please ensure Ollama is running."
            exit 1
        }
    } else {
        # Fallback inline check
        try {
            $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
            Write-Host "  [+] Ollama server is active." -ForegroundColor Green
        } catch {
            Write-Error "[-] Ollama server is not responding at http://localhost:11434."
            exit 1
        }
    }

    # If Model was not explicitly passed, inspect installed models
    if (-not $Model) {
        try {
            $tagsResp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
            $installed = $tagsResp.models | Select-Object -ExpandProperty name
            if ($installed -contains "llama3.1:8b") {
                $Model = "llama3.1:8b"
            } elseif ($installed -contains "llama3.2:3b") {
                $Model = "llama3.2:3b"
            } elseif ($installed -contains "qwen2.5:7b") {
                $Model = "qwen2.5:7b"
            } elseif ($installed -contains "qwen2.5:1.5b") {
                $Model = "qwen2.5:1.5b"
            } elseif ($installed.Count -gt 0) {
                $Model = $installed[0]
            } else {
                $Model = "llama3.2:3b"
            }
            Write-Host "  [*] Auto-selected model: $Model" -ForegroundColor Cyan
        } catch {
            $Model = "llama3.2:3b"
        }
    }
} else {
    Write-Host "`n[1/4] Validating Provider Configuration ($Provider)..." -ForegroundColor Yellow
    $provUpper = $Provider.ToUpper()
    $envVarName = "${provUpper}_API_KEY"
    $apiKey = [System.Environment]::GetEnvironmentVariable($envVarName)
    if (-not $apiKey) {
        $apiKey = (Get-Item "env:$envVarName" -ErrorAction SilentlyContinue).Value
    }
    if (-not $apiKey) {
        Write-Error "[-] Missing API Key: Environment variable '$envVarName' is NOT set."
        exit 1
    }
    Write-Host "  [+] $envVarName detected." -ForegroundColor Green
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
Write-Host "  Provider:           $Provider"
Write-Host "  Model:              $Model"
Write-Host "  Competency:         $Competency"
Write-Host "  Limit per Split:    $Limit"
Write-Host "  Conditions:         vanilla, naive_rag, recency, symmetric, adaptive"
Write-Host "  Seed:               $Seed"
Write-Host "  Strict Integrity:   Zero mocks, authentic GPU token counting via Ollama native REST API"

$runnerArgs = @(
    "-m", "benchmarks.memoryagentbench_runner",
    "--provider", $Provider,
    "--model", $Model,
    "--competency", $Competency,
    "--limit", $Limit,
    "--trials", $Trials,
    "--seed", $Seed
)

# Set PYTHONPATH to project root
$env:PYTHONPATH = "$PSScriptRoot\.."

& $pythonExec $runnerArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host " [+] Pilot Evaluation Finished Successfully!" -ForegroundColor Green
    Write-Host " Results saved to: benchmarks\results\memoryagentbench\" -ForegroundColor Green
    Write-Host "   - Raw telemetry: JSONL files in condition subdirectories"
    Write-Host "   - Summary table: summary_pilot_${Provider}_*.csv"
    Write-Host "==================================================" -ForegroundColor Green
} else {
    Write-Error "`n[-] Execution ended with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}
