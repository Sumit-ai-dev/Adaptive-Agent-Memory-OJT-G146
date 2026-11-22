#!/usr/bin/env python3
"""
MemoryAgentBench Pilot Data Download and Integrity Verification Tool.
Cross-platform compatible (macOS, Linux, Windows / PowerShell).

Usage:
    python download_and_verify.py           # Verify existing local pilot manifests
    python download_and_verify.py --download # Download official HuggingFace Parquet files
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

# Paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
METADATA_FILE = SCRIPT_DIR / "manifest_metadata.json"
CR_MANIFEST_FILE = SCRIPT_DIR / "pilot_conflict_resolution_25.json"
AR_MANIFEST_FILE = SCRIPT_DIR / "pilot_accurate_retrieval_25.json"

HF_BASE_URL = "https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/resolve/main/data"
PARQUET_URLS = {
    "Conflict_Resolution": f"{HF_BASE_URL}/Conflict_Resolution-00000-of-00001.parquet",
    "Accurate_Retrieval": f"{HF_BASE_URL}/Accurate_Retrieval-00000-of-00001.parquet",
}


def calculate_sha256(filepath: Path) -> str:
    """Calculate the SHA256 hash of a file in binary mode."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_manifests() -> bool:
    """Verify integrity of local pilot manifests against manifest_metadata.json."""
    if not METADATA_FILE.exists():
        print(f"[-] Error: Metadata file not found at {METADATA_FILE}")
        return False

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    files_meta = meta.get("files", {})
    all_valid = True

    for filename, info in files_meta.items():
        file_path = SCRIPT_DIR / filename
        expected_hash = info.get("sha256")
        expected_count = info.get("tasks_count")

        if not file_path.exists():
            print(f"[-] Missing file: {filename}")
            all_valid = False
            continue

        actual_hash = calculate_sha256(file_path)
        if actual_hash != expected_hash:
            print(f"[-] SHA256 mismatch for {filename}:")
            print(f"    Expected: {expected_hash}")
            print(f"    Actual:   {actual_hash}")
            all_valid = False
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            tasks = data.get("tasks", [])
            if len(tasks) != expected_count:
                print(f"[-] Task count mismatch in {filename}: expected {expected_count}, got {len(tasks)}")
                all_valid = False
                continue

        print(f"[+] Verified {filename}: SHA256 match, {len(tasks)} tasks validated.")

    return all_valid


def download_official_parquets(output_dir: Path) -> bool:
    """Download official upstream parquet files from HuggingFace."""
    output_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AEMA-Benchmark-Verifier/1.0"}

    for name, url in PARQUET_URLS.items():
        dest = output_dir / f"{name}.parquet"
        print(f"[*] Downloading {name} from {url}...")
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
                total_size = 0
                while chunk := resp.read(65536):
                    out.write(chunk)
                    total_size += len(chunk)
            print(f"[+] Successfully saved {dest.name} ({total_size / 1024 / 1024:.2f} MB)")
        except Exception as e:
            print(f"[-] Failed to download {name}: {e}")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="MemoryAgentBench Pilot Data Verifier and Downloader")
    parser.add_argument("--download", action="store_true", help="Download official HuggingFace Parquet files")
    parser.add_argument("--outdir", type=Path, default=SCRIPT_DIR / "upstream_parquets", help="Target dir for downloaded parquets")
    args = parser.parse_args()

    print("==================================================")
    print(" MemoryAgentBench Pilot Data Integrity Tool")
    print(" Target: Official dataset ai-hyz/MemoryAgentBench")
    print("==================================================")

    if args.download:
        success = download_official_parquets(args.outdir)
        if not success:
            sys.exit(1)

    print("\n[*] Verifying local pilot manifests...")
    valid = verify_manifests()
    if valid:
        print("\n[+] All pilot manifests are strictly verified and intact.")
        sys.exit(0)
    else:
        print("\n[-] Integrity check failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
