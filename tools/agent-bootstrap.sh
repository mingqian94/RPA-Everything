#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

sh tools/setup.sh "$@"
PYTHON="$ROOT/.venv/bin/python"

echo "\n[check] Running safe doctor setup"
set +e
"$PYTHON" run.py harness/doctor --fix --required-only
DOCTOR_EXIT=$?
set -e

echo "\n[demo] Running the no-key lifecycle preview"
"$PYTHON" run.py harness/demo

echo "\nBootstrap complete."
if [ "$DOCTOR_EXIT" -ne 0 ]; then
  echo "LLM configuration is still expected to be incomplete. Add llm.api_key / llm.model to config.yaml before planning a real task."
fi
echo 'Next safe command: .venv/bin/python run.py harness/agent -- --goal "Plan a read-only task only. Do not submit, publish, send, approve, pay, delete, or modify remote data." --dry-run'
