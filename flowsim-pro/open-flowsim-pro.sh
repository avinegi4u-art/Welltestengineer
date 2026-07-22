#!/usr/bin/env bash
# One-click / one-command launcher for Linux, macOS, and Cursor Cloud
set -e
cd "$(dirname "$0")"
exec python3 ./launch.py
