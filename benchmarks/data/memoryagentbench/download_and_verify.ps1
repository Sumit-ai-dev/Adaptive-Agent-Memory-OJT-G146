# MemoryAgentBench Pilot Data Integrity Verifier for Windows PowerShell
# Usage:
#   powershell -ExecutionPolicy Bypass -File download_and_verify.ps1
#   powershell -ExecutionPolicy Bypass -File download_and_verify.ps1 -Download

param (
    [switch]$Download,
    [string]$OutputDir = "$PSScriptRoot\upstream_parquets"
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " MemoryAgentBench Pilot Data Integrity Tool (PowerShell)" -ForegroundColor Cyan
Write-Host " Target: Official dataset ai-hyz/MemoryAgentBench" -ForegroundColor Cyan
Write-Host "=================================================="

$metadataFile = "$PSScriptRoot\manifest_metadata.json"

if (-not (Test-Path $metadataFile)) {
    Write-Error "[-] Metadata file not found at $metadataFile"
    exit 1
}

$metadata = Get-Content -Raw -Path $metadataFile | ConvertFrom-Json

if ($Download) {
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }

    $urls = @{
        "Conflict_Resolution" = "https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/resolve/main/data/Conflict_Resolution-00000-of-00001.parquet"
        "Accurate_Retrieval" = "https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/resolve/main/data/Accurate_Retrieval-00000-of-00001.parquet"
        "Test_Time_Learning" = "https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/resolve/main/data/Test_Time_Learning-00000-of-00001.parquet"
    }

    foreach ($name in $urls.Keys) {
        $dest = "$OutputDir\$name.parquet"
        $url = $urls[$name]
        Write-Host "[*] Downloading $name to $dest..." -ForegroundColor Yellow
        try {
            Invoke-WebRequest -Uri $url -OutFile $dest -TimeoutSec 120
            Write-Host "[+] Downloaded $name successfully." -ForegroundColor Green
        } catch {
            Write-Error "[-] Failed to download $name : $_"
            exit 1
        }
    }
}

Write-Host "`n[*] Verifying pilot manifest integrity..." -ForegroundColor Yellow
$allValid = $true

foreach ($prop in $metadata.files.PSObject.Properties) {
    $filename = $prop.Name
    $info = $prop.Value
    $expectedHash = $info.sha256
    $expectedCount = $info.tasks_count

    $filePath = "$PSScriptRoot\$filename"
    if (-not (Test-Path $filePath)) {
        Write-Error "[-] Missing file: $filePath"
        $allValid = $false
        continue
    }

    $actualHash = (Get-FileHash -Path $filePath -Algorithm SHA256).Hash.ToLower()
    if ($actualHash -ne $expectedHash.ToLower()) {
        Write-Error "[-] Hash mismatch for $filename (Expected: $expectedHash, Actual: $actualHash)"
        $allValid = $false
        continue
    }

    $content = Get-Content -Raw -Path $filePath | ConvertFrom-Json
    $tasksCount = $content.tasks.Count
    if ($tasksCount -ne $expectedCount) {
        Write-Error "[-] Task count mismatch in $filename (Expected: $expectedCount, Got: $tasksCount)"
        $allValid = $false
        continue
    }

    Write-Host "[+] Verified $filename : SHA256 match, $tasksCount tasks validated." -ForegroundColor Green
}

if ($allValid) {
    Write-Host "`n[+] All pilot manifests are strictly verified and intact." -ForegroundColor Green
    exit 0
} else {
    Write-Error "`n[-] Manifest integrity check failed."
    exit 1
}
