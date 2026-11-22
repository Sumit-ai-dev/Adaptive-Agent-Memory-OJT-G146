#!/usr/bin/env bash
# Ollama and Hardware Health Inspector for macOS / Linux
# Usage: ./scripts/check_ollama.sh

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${PROJECT_ROOT}"

python3 -m benchmarks.check_ollama "$@"
