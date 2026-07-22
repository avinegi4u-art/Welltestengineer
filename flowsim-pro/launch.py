#!/usr/bin/env python3
"""
FlowSim Pro one-click launcher.

Starts the FastAPI backend (port 8000) and Next.js frontend (port 3000),
waits until both are ready, then opens the app in your default browser.

Usage:
  python launch.py
  ./open-flowsim-pro.sh
  Double-click "Open FlowSim Pro.bat" (Windows)
  Double-click "Open FlowSim Pro.command" (macOS)
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
BACKEND_URL = "http://127.0.0.1:8000/api/health"
FRONTEND_URL = "http://127.0.0.1:3000"
APP_URL = "http://127.0.0.1:3000"

processes: list[subprocess.Popen] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def require(cmd: str, hint: str) -> str:
    path = which(cmd)
    if not path:
        log(f"ERROR: '{cmd}' not found. {hint}")
        sys.exit(1)
    return path


def wait_for(url: str, label: str, timeout_s: float = 120.0) -> bool:
    log(f"Waiting for {label} ({url}) ...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:
                if 200 <= resp.status < 500:
                    log(f"  {label} is ready.")
                    return True
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(1.0)
    log(f"ERROR: timed out waiting for {label}.")
    return False


def setup_backend(python: str) -> Path:
    venv = BACKEND / ".venv"
    if sys.platform == "win32":
        venv_python = venv / "Scripts" / "python.exe"
        pip = venv / "Scripts" / "pip.exe"
    else:
        venv_python = venv / "bin" / "python"
        pip = venv / "bin" / "pip"

    if not venv_python.exists():
        log("Creating Python virtual environment...")
        subprocess.check_call([python, "-m", "venv", str(venv)], cwd=str(BACKEND))

    log("Installing / updating backend packages (first run may take a minute)...")
    subprocess.check_call(
        [str(pip), "install", "-q", "-r", "requirements.txt"],
        cwd=str(BACKEND),
    )
    return venv_python


def setup_frontend(npm: str) -> None:
    node_modules = FRONTEND / "node_modules"
    if not node_modules.exists():
        log("Installing frontend packages (first run may take a few minutes)...")
        subprocess.check_call([npm, "install"], cwd=str(FRONTEND))
    else:
        log("Frontend packages already installed.")


def start_backend(venv_python: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    log("Starting backend on http://127.0.0.1:8000 ...")
    return subprocess.Popen(
        [
            str(venv_python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(BACKEND),
        env=env,
        creationflags=creationflags,
    )


def start_frontend(npm: str) -> subprocess.Popen:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    log("Starting frontend on http://127.0.0.1:3000 ...")
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3000"],
        cwd=str(FRONTEND),
        creationflags=creationflags,
    )


def cleanup(_signum=None, _frame=None) -> None:
    log("\nStopping FlowSim Pro...")
    for proc in reversed(processes):
        if proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
    for proc in reversed(processes):
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
    log("Stopped. You can close this window.")
    sys.exit(0)


def main() -> None:
    os.chdir(ROOT)
    log("=" * 56)
    log("  FlowSim Pro — one-click launcher")
    log("=" * 56)

    python = sys.executable or require("python3", "Install Python 3.10+ from https://python.org")
    npm = require("npm", "Install Node.js LTS from https://nodejs.org (includes npm)")

    if not BACKEND.exists() or not FRONTEND.exists():
        log("ERROR: backend/ or frontend/ folder missing. Run this from the flowsim-pro folder.")
        sys.exit(1)

    signal.signal(signal.SIGINT, cleanup)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, cleanup)

    venv_python = setup_backend(python)
    setup_frontend(npm)

    backend = start_backend(venv_python)
    processes.append(backend)
    frontend = start_frontend(npm)
    processes.append(frontend)

    if not wait_for(BACKEND_URL, "backend"):
        cleanup()
    if not wait_for(FRONTEND_URL, "frontend"):
        cleanup()

    log(f"\nOpening {APP_URL}")
    webbrowser.open(APP_URL)
    log("\nFlowSim Pro is running.")
    log("  Dashboard : http://127.0.0.1:3000")
    log("  Case Editor: http://127.0.0.1:3000/editor")
    log("  API docs  : http://127.0.0.1:8000/docs")
    log("\nKeep this window open while you use the app.")
    log("Press Ctrl+C to stop both servers.\n")

    try:
        while True:
            if backend.poll() is not None:
                log("Backend exited unexpectedly.")
                break
            if frontend.poll() is not None:
                log("Frontend exited unexpectedly.")
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
