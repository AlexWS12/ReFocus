#!/usr/bin/env bash
# to run tests, do: cd src/vision/tests && ./test.sh

set -euo pipefail

# Resolve project root from this script location so it works from any current directory.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Prefer the repo virtualenv on Windows; otherwise fall back to python on PATH.
if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON="python"
fi

# Pass through extra args (e.g., -v, -k pattern) to keep the script flexible.
"$PYTHON" -m pytest src/vision/tests -q "$@"
