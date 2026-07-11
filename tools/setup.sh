#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEV=0
IPHONE=0
for arg in "$@"; do
  case "$arg" in
    --dev) DEV=1 ;;
    --iphone) IPHONE=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "RPA-Everything setup"

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/5] Creating .venv"
  python3 -m venv .venv
else
  echo "[1/5] .venv already exists"
fi

PYTHON="$ROOT/.venv/bin/python"

echo "[2/5] Upgrading pip"
"$PYTHON" -m pip install --upgrade pip

echo "[3/5] Installing Python dependencies"
if [ "$DEV" -eq 1 ]; then
  "$PYTHON" -m pip install -r requirements-dev.txt
else
  "$PYTHON" -m pip install -r requirements.txt
fi

if [ "$IPHONE" -eq 1 ]; then
  echo "[3b/5] Installing optional iPhone dependency"
  "$PYTHON" -m pip install pymobiledevice3
fi

echo "[4/5] Installing Playwright Chromium"
"$PYTHON" -m playwright install chromium

if [ ! -f "config.yaml" ]; then
  echo "[5/5] Creating config.yaml from template"
  cp config.yaml.example config.yaml
else
  echo "[5/5] config.yaml already exists"
fi

echo ""
echo "Setup complete."
echo "Next:"
echo "  1. Open config.yaml and fill llm.api_key / llm.model."
echo "  2. Run: .venv/bin/python run.py harness/doctor"
echo "  3. Start browser tasks with: sh tools/start_chrome.sh"
