# Ollama and Hardware Health Inspector for Windows Gaming PC
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\check_ollama.ps1

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " AEMA Windows Hardware & Ollama Health Inspector" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Hardware Inspection
Write-Host "`n[1/3] Inspecting Host Hardware..." -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name -First 1
$ramGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)

$drive = Get-PSDrive -Name C -ErrorAction SilentlyContinue
$diskFreeGB = if ($drive) { [math]::Round($drive.Free / 1GB, 1) } else { 0 }

# GPU & VRAM Detection
$gpuName = "Unknown GPU"
$vramMB = 0
$vramFreeMB = 0
$hasNvidia = $false

$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    try {
        $smiOut = & nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits 2>&1
        if ($LASTEXITCODE -eq 0 -and $smiOut) {
            $parts = $smiOut[0].Split(",")
            if ($parts.Count -ge 3) {
                $gpuName = $parts[0].Trim()
                $vramMB = [double]$parts[1].Trim()
                $vramFreeMB = [double]$parts[2].Trim()
                $hasNvidia = $true
            }
        }
    } catch {}
}

if (-not $hasNvidia) {
    $wmiGpu = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name -First 1
    if ($wmiGpu) { $gpuName = $wmiGpu }
}

Write-Host "  OS:           $($os.Caption) ($($os.Version))"
Write-Host "  CPU:          $cpu"
Write-Host "  RAM:          $ramGB GB"
Write-Host "  GPU:          $gpuName"
if ($vramMB -gt 0) {
    $vramGB = [math]::Round($vramMB / 1024, 1)
    $freeGB = [math]::Round($vramFreeMB / 1024, 1)
    Write-Host "  VRAM:         $vramGB GB total ($freeGB GB free)" -ForegroundColor Green
}
Write-Host "  Free Storage: $diskFreeGB GB on C:\"

# 2. Ollama Connectivity & Installed Models
Write-Host "`n[2/3] Checking Ollama Local Server (http://localhost:11434)..." -ForegroundColor Yellow
$ollamaUrl = "http://localhost:11434"
$tagsUrl = "$ollamaUrl/api/tags"

try {
    $resp = Invoke-RestMethod -Uri $tagsUrl -Method Get -TimeoutSec 5 -ErrorAction Stop
    $models = $resp.models
    Write-Host "  [+] Ollama is ONLINE at $ollamaUrl" -ForegroundColor Green
    Write-Host "  Installed Models: $($models.Count)"

    if ($models.Count -gt 0) {
        foreach ($m in $models) {
            $sizeGB = [math]::Round($m.size / 1GB, 2)
            $pSize = $m.details.parameter_size
            $quant = $m.details.quantization_level
            Write-Host "    - $($m.name) (Params: $pSize, Quant: $quant, Size: $sizeGB GB)"
        }
    } else {
        Write-Host "    [!] No models currently installed in Ollama." -ForegroundColor Yellow
    }
} catch {
    Write-Error "[-] Ollama server is NOT reachable at $ollamaUrl."
    Write-Host "    Please start Ollama:" -ForegroundColor Red
    Write-Host "      1. Check system tray or run 'ollama serve' in another terminal." -ForegroundColor Red
    Write-Host "      2. Download Ollama if not installed from https://ollama.ai/download" -ForegroundColor Red
    exit 1
}

# 3. Hardware Recommendation
Write-Host "`n[3/3] Hardware Sizing & Recommended Model..." -ForegroundColor Yellow

if ($vramMB -ge 15000) {
    $recTag = "llama3.1:8b"
    $tier = "High-Tier Dedicated GPU (>=16 GB VRAM)"
} elseif ($vramMB -ge 7500) {
    $recTag = "llama3.1:8b"
    $tier = "Mid-Tier Dedicated GPU (>=8 GB VRAM)"
} else {
    $recTag = "llama3.2:3b"
    $tier = "Entry-Level GPU / CPU (<8 GB VRAM)"
}

Write-Host "  Hardware Tier:    $tier"
Write-Host "  Recommended Tag:  $recTag" -ForegroundColor Cyan

$isInstalled = $false
if ($models) {
    foreach ($m in $models) {
        if ($m.name -eq $recTag -or $m.model -eq $recTag) {
            $isInstalled = $true
            break
        }
    }
}

if ($isInstalled) {
    Write-Host "  Status:           [READY] '$recTag' is already installed locally." -ForegroundColor Green
} else {
    Write-Host "  Status:           [ACTION REQUIRED] Recommended model '$recTag' is not installed." -ForegroundColor Yellow
    Write-Host "  To install:       Run 'ollama pull $recTag' before launching benchmarks."
}

Write-Host "`n==================================================" -ForegroundColor Cyan
