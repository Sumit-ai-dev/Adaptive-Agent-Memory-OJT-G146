"""
Ollama and Hardware Health Inspector for AEMA Benchmarks.

Cross-platform utility (Windows, macOS, Linux) that:
1. Audits host system hardware (CPU, RAM, GPU, VRAM, Disk).
2. Connects to the local Ollama instance (http://localhost:11434).
3. Queries installed models, exact tags, parameter sizes, and quantization levels.
4. Evaluates hardware suitability and recommends the optimal model for Phase 4A evaluation.
5. Emits structured JSON and console diagnostics.
"""

import argparse
import json
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

logger = logging.getLogger("benchmarks.check_ollama")


def get_system_hardware() -> Dict[str, Any]:
    """Inspect CPU, RAM, GPU, VRAM, and disk space across Windows, macOS, and Linux."""
    info: Dict[str, Any] = {
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu": platform.processor() or platform.machine(),
        "ram_gb": 0.0,
        "gpu_name": "Unknown",
        "vram_total_mb": 0.0,
        "vram_free_mb": 0.0,
        "disk_free_gb": 0.0,
        "has_nvidia_gpu": False,
        "is_apple_silicon": False,
    }

    # 1. Total System RAM
    try:
        if platform.system() == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            info["ram_gb"] = round(int(out) / (1024 ** 3), 1)
            info["is_apple_silicon"] = platform.machine() == "arm64"
            if info["is_apple_silicon"]:
                info["gpu_name"] = f"Apple Silicon Unified Memory ({info['ram_gb']} GB)"
                info["vram_total_mb"] = info["ram_gb"] * 1024.0
        elif platform.system() == "Windows":
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize"],
                text=True,
            ).strip()
            info["ram_gb"] = round(int(out) / (1024 ** 2), 1)
        else:  # Linux
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        info["ram_gb"] = round(kb / (1024 ** 2), 1)
                        break
    except Exception as e:
        logger.debug(f"Failed to inspect RAM: {e}")

    # 2. NVIDIA GPU & VRAM Inspection (via nvidia-smi)
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            cmd = [
                nvidia_smi,
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ]
            out = subprocess.check_output(cmd, text=True).strip()
            if out:
                first_line = out.splitlines()[0]
                parts = [p.strip() for p in first_line.split(",")]
                if len(parts) >= 3:
                    info["gpu_name"] = parts[0]
                    info["vram_total_mb"] = float(parts[1])
                    info["vram_free_mb"] = float(parts[2])
                    info["has_nvidia_gpu"] = True
        except Exception as e:
            logger.debug(f"Failed nvidia-smi query: {e}")

    # 3. Windows WMI GPU Fallback (if not NVIDIA or nvidia-smi not in PATH)
    if platform.system() == "Windows" and not info["has_nvidia_gpu"]:
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name -First 1"],
                text=True,
            ).strip()
            if out:
                info["gpu_name"] = out
        except Exception:
            pass

    # 4. Available Disk Space
    try:
        usage = shutil.disk_usage(Path.cwd())
        info["disk_free_gb"] = round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass

    return info


def inspect_ollama(base_url: str = "http://localhost:11434") -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """
    Check Ollama connectivity and query installed models via /api/tags.
    Returns: (is_running, list_of_models, error_message)
    """
    clean_url = base_url.rstrip("/").removesuffix("/v1")
    tags_url = f"{clean_url}/api/tags"

    req = urllib.request.Request(tags_url, headers={"User-Agent": "AEMA-Benchmark/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                return False, [], f"Ollama returned HTTP {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            raw_models = data.get("models", [])
            models = []
            for m in raw_models:
                details = m.get("details", {})
                size_gb = round(m.get("size", 0) / (1024 ** 3), 2)
                models.append({
                    "name": m.get("name", ""),
                    "model": m.get("model", ""),
                    "size_gb": size_gb,
                    "parameter_size": details.get("parameter_size", "unknown"),
                    "quantization_level": details.get("quantization_level", "unknown"),
                    "family": details.get("family", "unknown"),
                    "modified_at": m.get("modified_at", ""),
                })
            return True, models, None
    except urllib.error.URLError as e:
        return False, [], f"Cannot connect to Ollama at {clean_url}: {e.reason}"
    except Exception as e:
        return False, [], str(e)


def recommend_model(hardware: Dict[str, Any], installed_models: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Recommend the optimal model based on available VRAM / unified memory:
    - >= 16 GB VRAM: llama3.1:8b (recommended) or qwen2.5:14b
    - >= 8 GB VRAM: llama3.1:8b (recommended ~5.5 GB VRAM) or qwen2.5:7b
    - < 8 GB VRAM or CPU: llama3.2:3b (~2.5 GB VRAM) or qwen2.5:1.5b
    """
    vram_mb = hardware.get("vram_total_mb", 0.0)
    ram_gb = hardware.get("ram_gb", 0.0)

    # Determine recommended tier
    if vram_mb >= 15000:
        recommended_tag = "llama3.1:8b"
        tier_desc = "High-tier GPU (>=16 GB VRAM)"
    elif vram_mb >= 7500:
        recommended_tag = "llama3.1:8b"
        tier_desc = "Mid-tier GPU (>=8 GB VRAM)"
    elif hardware.get("is_apple_silicon") and ram_gb >= 16:
        recommended_tag = "llama3.1:8b"
        tier_desc = "Apple Silicon Unified Memory (>=16 GB)"
    elif hardware.get("is_apple_silicon") and ram_gb >= 8:
        recommended_tag = "llama3.2:3b"
        tier_desc = "Apple Silicon Unified Memory (8 GB)"
    else:
        recommended_tag = "llama3.2:3b"
        tier_desc = "Entry-level GPU / CPU-only (<8 GB VRAM)"

    # Check which installed models match
    installed_names = [m["name"] for m in installed_models]
    is_installed = recommended_tag in installed_names

    # If recommended model is not installed, find best installed alternative
    best_installed_match = None
    if not is_installed and installed_models:
        # Prioritize 8b -> 7b -> 3b -> 1.5b
        for pref in ["llama3.1:8b", "qwen2.5:7b", "llama3.2:3b", "qwen2.5:1.5b"]:
            if pref in installed_names:
                best_installed_match = pref
                break
        if not best_installed_match:
            best_installed_match = installed_names[0]

    return {
        "recommended_model": recommended_tag,
        "tier": tier_desc,
        "is_installed": is_installed,
        "best_installed_match": best_installed_match,
        "pull_command": f"ollama pull {recommended_tag}",
    }


def main():
    parser = argparse.ArgumentParser(description="Audit Host Hardware & Ollama Models for AEMA Benchmarks")
    parser.add_argument("--url", type=str, default="http://localhost:11434", help="Ollama server URL")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON output")
    args = parser.parse_args()

    hw = get_system_hardware()
    is_running, models, err = inspect_ollama(args.url)
    rec = recommend_model(hw, models) if is_running else {}

    report = {
        "hardware": hw,
        "ollama": {
            "url": args.url,
            "is_running": is_running,
            "error": err,
            "installed_models_count": len(models),
            "installed_models": models,
        },
        "recommendation": rec,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return

    # Formatted Console Output
    print("\n" + "=" * 65)
    print("  AEMA HARDWARE & OLLAMA BENCHMARK INSPECTOR")
    print("=" * 65)
    print(f"  Host OS:         {hw['os']} ({hw['architecture']})")
    print(f"  CPU:             {hw['cpu']}")
    print(f"  System RAM:      {hw['ram_gb']} GB")
    print(f"  GPU:             {hw['gpu_name']}")
    if hw["vram_total_mb"] > 0:
        vram_gb = round(hw["vram_total_mb"] / 1024.0, 1)
        free_gb = round(hw["vram_free_mb"] / 1024.0, 1)
        print(f"  VRAM:            {vram_gb} GB total ({free_gb} GB free)")
    print(f"  Free Storage:    {hw['disk_free_gb']} GB")
    print("-" * 65)

    if not is_running:
        print(f"  Ollama Status:   [FAILED] Server not reachable at {args.url}")
        print(f"  Reason:          {err}")
        print("  Action Required: Start Ollama before running benchmarks:")
        print("                   Windows: Start menu -> Ollama  OR  ollama serve")
        print("                   macOS:   open -a Ollama  OR  ollama serve")
        print("=" * 65 + "\n")
        sys.exit(1)

    print(f"  Ollama Status:   [ONLINE] Connected to {args.url}")
    print(f"  Models Found:    {len(models)}")
    if models:
        for idx, m in enumerate(models, 1):
            print(f"    [{idx}] {m['name']:<20} | Params: {m['parameter_size']:<6} | Quant: {m['quantization_level']:<8} | Size: {m['size_gb']} GB")
    else:
        print("    [!] No local models found in Ollama.")

    print("-" * 65)
    print(f"  Hardware Tier:   {rec.get('tier', 'Unknown')}")
    print(f"  Recommended Tag: {rec.get('recommended_model', 'None')}")

    if rec.get("is_installed"):
        print(f"  Ready for Run:   [YES] Recommended model '{rec['recommended_model']}' is installed locally.")
    elif rec.get("best_installed_match"):
        print(f"  Ready for Run:   [PARTIAL] Recommended model not installed.")
        print(f"                   Available alternative: '{rec['best_installed_match']}'")
        print(f"                   To pull recommended:   {rec['pull_command']}")
    else:
        print(f"  Ready for Run:   [NO] No models available.")
        print(f"                   Execute: {rec.get('pull_command')}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
