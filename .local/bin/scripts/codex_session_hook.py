#!/usr/bin/env python3

"""Track Codex sessions that should be restored into tmux."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess  # noqa: S404  # Required to call tmux and systemd without a shell.
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

_TMUX = shutil.which("tmux")
_SYSTEMCTL = shutil.which("systemctl")


def main() -> int:
    """Update restore state from one Codex lifecycle event."""
    try:
        event = _read_event()
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        _report(f"Invalid Codex hook input: {error}")
        return 1

    directory = _state_directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = directory / ".state.lock"
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if event["hook_event_name"] == "SessionStart":
            _write_marker(event, directory)
        else:
            _remove_marker(event, directory)

    return 0


class _HookEvent(TypedDict):
    hook_event_name: str
    session_id: str
    cwd: str


def _read_event() -> _HookEvent:
    raw_event: object = json.load(sys.stdin)
    if not isinstance(raw_event, dict):
        raise TypeError("expected a JSON object")

    event_name = raw_event.get("hook_event_name")
    session_id = raw_event.get("session_id")
    cwd = raw_event.get("cwd")
    if event_name not in {"SessionStart", "SessionEnd"}:
        raise ValueError("unsupported hook event")
    if not isinstance(session_id, str) or not isinstance(cwd, str):
        raise TypeError("session_id and cwd must be strings")
    try:
        uuid.UUID(session_id)
    except ValueError as error:
        raise ValueError("session_id must be a UUID") from error

    return {"hook_event_name": event_name, "session_id": session_id, "cwd": cwd}


def _write_marker(event: _HookEvent, directory: Path) -> None:
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return

    tmux_session = _run_tmux("display-message", "-p", "-t", pane, "#{session_name}")
    tmux_session_path = _run_tmux(
        "display-message", "-p", "-t", pane, "#{session_path}"
    )
    if not tmux_session:
        return

    current_boot_id = _boot_id()
    _remove_previous_pane_marker(event, directory, pane, current_boot_id)

    record = {
        "session_id": event["session_id"],
        "cwd": event["cwd"],
        "codex_home": os.environ.get("CODEX_HOME", str(Path.home() / ".codex")),
        "tmux_session": tmux_session,
        "tmux_session_path": tmux_session_path or event["cwd"],
        "tmux_pane": pane,
        "boot_id": current_boot_id,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    path = directory / f"{event['session_id']}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)

    _run_tmux("set-option", "-w", "-t", pane, "@codex_session_id", event["session_id"])
    _run_tmux("set-option", "-w", "-t", pane, "allow-rename", "on")
    # Follow the thread title Codex updates on /rename and /fork.
    _run_tmux(
        "set-option", "-w", "-t", pane, "automatic-rename-format", "#{pane_title}"
    )
    _run_tmux("set-option", "-w", "-t", pane, "automatic-rename", "on")


def _remove_previous_pane_marker(
    event: _HookEvent,
    directory: Path,
    pane: str,
    current_boot_id: str,
) -> None:
    for marker in directory.glob("*.json"):
        try:
            previous: object = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(previous, dict):
            continue
        if (
            previous.get("boot_id") == current_boot_id
            and previous.get("tmux_pane") == pane
            and previous.get("session_id") != event["session_id"]
        ):
            marker.unlink(missing_ok=True)


def _remove_marker(event: _HookEvent, directory: Path) -> None:
    if _system_is_stopping() is not False:
        return
    # Keep markers when the tmux server died, e.g. from an OOM kill, so they come back.
    if _tmux_server_is_gone():
        return

    (directory / f"{event['session_id']}.json").unlink(missing_ok=True)

    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return
    tagged_session = _run_tmux(
        "display-message", "-p", "-t", pane, "#{@codex_session_id}"
    )
    if tagged_session == event["session_id"]:
        _run_tmux("set-option", "-w", "-u", "-t", pane, "@codex_session_id")
        _run_tmux("set-option", "-w", "-u", "-t", pane, "allow-rename")
        _run_tmux("set-option", "-w", "-u", "-t", pane, "automatic-rename-format")
        _run_tmux("set-option", "-w", "-u", "-t", pane, "automatic-rename")


def _tmux_server_is_gone() -> bool:
    if not os.environ.get("TMUX"):
        return False
    # A window closed on a live server still lists sessions; a dead server fails.
    return _run_tmux("list-sessions", "-F", "#{session_id}") is None


def _run_tmux(*arguments: str) -> str | None:
    if _TMUX is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603  # Arguments are passed without a shell.
            [_TMUX, *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.rstrip("\n")


def _boot_id() -> str:
    try:
        return (
            Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
        )
    except OSError:
        return "unknown"


def _system_is_stopping() -> bool | None:
    if _SYSTEMCTL is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603  # Executable and arguments are fixed.
            [_SYSTEMCTL, "is-system-running"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    state = result.stdout.strip()
    if state == "stopping":
        return True
    if state in {"running", "degraded", "maintenance", "starting"}:
        return False
    return None


def _state_directory() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "codex" / "active-sessions"


def _report(message: str) -> None:
    sys.stderr.write(f"{message}\n")


if __name__ == "__main__":
    raise SystemExit(main())
