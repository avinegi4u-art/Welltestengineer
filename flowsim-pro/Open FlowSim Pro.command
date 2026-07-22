#!/bin/bash
# macOS double-click launcher (also works in Terminal on Linux/Mac)
cd "$(dirname "$0")" || exit 1

echo ""
echo "  FlowSim Pro — starting..."
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+."
  read -r -p "Press Enter to close..."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Install Node.js LTS from https://nodejs.org/"
  read -r -p "Press Enter to close..."
  exit 1
fi

exec python3 ./launch.py
