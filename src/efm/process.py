"""PID tracking, start and stop for mock service processes.

Stores PID files in ``/tmp/efm-<name>.pid`` so ``efm down`` can reliably
terminate previously-started processes.

Docs: process.doc.md
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

PID_DIR = Path("/tmp")


def _pid_file(name: str) -> Path:
    return PID_DIR / f"efm-{name}.pid"


def write_pid(name: str, pid: int) -> None:
    """Persist a process ID so it can be stopped later."""
    _pid_file(name).write_text(str(pid), encoding="utf-8")


def read_pid(name: str) -> int | None:
    """Return the stored PID or *None* if the service is not running."""
    pf = _pid_file(name)
    if not pf.exists():
        return None
    try:
        return int(pf.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def is_running(pid: int) -> bool:
    """Check whether a process with *pid* is still alive."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def kill_service(name: str, pid: int) -> None:
    """Terminate a service and clean up its PID file."""
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    _pid_file(name).unlink(missing_ok=True)


def stop_all(services: list[dict[str, Any]]) -> list[str]:
    """Stop every known service and return the list of names that were killed."""
    stopped: list[str] = []
    for svc in services:
        name = svc["name"]
        pid = read_pid(name)
        if pid is not None and is_running(pid):
            kill_service(name, pid)
            stopped.append(name)
        else:
            # Always clean up stale PID files
            _pid_file(name).unlink(missing_ok=True)
    return stopped


def list_running(services: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return a list of running services with their PID and type."""
    running: list[dict[str, Any]] = []
    if services is None:
        # Discover from PID files
        for pf in PID_DIR.glob("efm-*.pid"):
            name = pf.stem[len("efm-"):]
            pid = read_pid(name)
            if pid is not None and is_running(pid):
                running.append({"name": name, "pid": pid, "type": "unknown"})
            else:
                pf.unlink(missing_ok=True)
        return running

    for svc in services:
        name = svc["name"]
        pid = read_pid(name)
        if pid is not None and is_running(pid):
            running.append({"name": name, "pid": pid, "type": svc.get("type", "unknown")})
    return running


def spawn_python_module(module: str, args: list[str], name: str) -> int:
    """Start a Python module in a background process and store its PID."""
    cmd = [sys.executable, "-m", module, *args]
    # Use start_new_session so uvicorn/FastAPI child processes are in a new
    # process group — makes cleanup easier.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    write_pid(name, proc.pid)
    return proc.pid
