#!/usr/bin/env bash
# AEMA MemoryAgentBench Pilot Evaluation Runner for macOS
# Usage:
#   ./scripts/run_pilot_mac.sh --smoke-test
#   ./scripts/run_pilot_mac.sh --full-pilot
#   ./scripts/run_pilot_mac.sh --model qwen2.5:1.5b --limit 2

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}"

PROVIDER="ollama"
MODEL=""
COMPETENCY="all"
LIMIT=25
TRIALS=1
SEED=42

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --smoke-test) LIMIT=2; shift ;;
        --full-pilot) LIMIT=25; shift ;;
        --provider) PROVIDER="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --competency) COMPETENCY="$2"; shift 2 ;;
        --limit) LIMIT="$2"; shift 2 ;;
        --trials) TRIALS="$2"; shift 2 ;;
        --seed) SEED="$2"; shift 2 ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
done

echo "=================================================="
echo " AEMA MemoryAgentBench Pilot Evaluation (macOS)"
echo "=================================================="

# 1. Health & Hardware Check
python3 -m benchmarks.check_ollama

# 2. Manifest Verification
python3 benchmarks/data/memoryagentbench/download_and_verify.py

# 3. Resolve Model if empty
if [ -z "$MODEL" ]; then
    MODEL="qwen2.5:1.5b"
fi

echo ""
echo "[*] Launching Pilot Benchmark..."
echo "  Provider:   $PROVIDER"
echo "  Model:      $MODEL"
echo "  Competency: $COMPETENCY"
echo "  Limit:      $LIMIT per split"
echo "  Seed:       $SEED"

python3 -m benchmarks.memoryagentbench_runner \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    --competency "$COMPETENCY" \
    --limit "$LIMIT" \
    --trials "$TRIALS" \
    --seed "$SEED"
