#!/usr/bin/env bash
# Idempotent Cloud Agent install for the FlowSim Pro app (flowsim-pro/).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The default base image ships python3 but not the venv/ensurepip module,
# which is required to create the backend virtualenv.
if ! dpkg -s python3.12-venv >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3.12-venv
fi

# Backend: Python virtualenv + dependencies.
cd "$REPO_ROOT/flowsim-pro/backend"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# Frontend: Node dependencies.
cd "$REPO_ROOT/flowsim-pro/frontend"
npm install
