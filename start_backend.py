"""
LaneLogic - Backend Launcher
Runs the Person 3 FastAPI backend from the correct working directory
so that its bare `import models / schemas / database` resolve correctly.

Usage:
    python start_backend.py
    python start_backend.py --port 8001
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "person3_backend"
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"

if not PYTHON.exists():
    # Fallback to system python
    PYTHON = Path(sys.executable)


def main():
    parser = argparse.ArgumentParser(description="LaneLogic Backend Launcher")
    parser.add_argument("--port", default="8000", help="Port to run on (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    reload_flag = [] if args.no_reload else ["--reload"]

    cmd = [
        str(PYTHON), "-m", "uvicorn",
        "main:app",
        "--host", args.host,
        "--port", args.port,
        *reload_flag,
    ]

    print(f"\n{'='*60}")
    print(f"  LANELOGIC BACKEND — Starting up")
    print(f"{'='*60}")
    print(f"  Directory : {BACKEND_DIR}")
    print(f"  URL       : http://localhost:{args.port}")
    print(f"  Docs      : http://localhost:{args.port}/docs")
    print(f"  Reload    : {'OFF' if args.no_reload else 'ON'}")
    print(f"{'-'*60}\n")

    subprocess.run(cmd, cwd=str(BACKEND_DIR))


if __name__ == "__main__":
    main()
