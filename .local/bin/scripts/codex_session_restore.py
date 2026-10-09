#!/usr/bin/env python3

"""Restore tracked Codex sessions into their tmux project sessions."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import shutil
import subprocess  # noqa: S404  # Required to call tmux without a shell.
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

_TMUX = shutil.which("tmux")
_ENV = shutil.which("env")


def main() -> int:
    """Restore all marked sessions that are not already open."""
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--activate-visible", action="store_true")
    action.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    directory = _state_directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if arguments.activate_visible:
        if _TMUX is None:
            _report("Codex session activation requires tmux in PATH")
            return 1
        _activate_visible_windows(directory)
        return 0

    codex = shutil.which("codex")
    if not codex or _TMUX is None or _ENV is None:
        _report("Codex session restore requires codex, env, and tmux in PATH")
        return 1

    with (directory / ".restore.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        _restore_records(directory, codex, arguments.dry_run)

    return 0


class _SessionRecord(TypedDict):
    session_id: str
    cwd: str
    codex_home: str
    tmux_session: str


def _restore_records(directory: Path, codex: str, dry_run: bool) -> None:
    records_by_session: defaultdict[str, list[_SessionRecord]] = defaultdict(list)
    for record in _load_records(directory):
        records_by_session[record["tmux_session"]].append(record)

    existing_ids = _tagged_session_ids()
    ordered_sessions = sorted(
        records_by_session,
        key=lambda name: (name != "0", name),
    )
    for tmux_session in ordered_sessions:
        for record in records_by_session[tmux_session]:
            try:
                _restore_record(record, codex, existing_ids, dry_run)
            except subprocess.CalledProcessError as error:
                detail = error.stderr.strip() or str(error)
                _report(
                    f"Failed to restore {record['session_id']} into "
                    f"{tmux_session}: {detail}"
                )

    if not dry_run:
        _activate_visible_windows(directory)


def _load_records(directory: Path) -> list[_SessionRecord]:
    records = []
    for marker in sorted(directory.glob("*.json")):
        try:
            record = _load_record(marker)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            _report(f"Skipping invalid Codex session marker {marker}: {error}")
            continue
        records.append(record)
    return records


def _load_record(marker: Path) -> _SessionRecord:
    raw_record: object = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(raw_record, dict):
        raise TypeError("expected a JSON object")

    session_id = raw_record.get("session_id")
    cwd = raw_record.get("cwd")
    codex_home = raw_record.get("codex_home", str(Path.home() / ".codex"))
    tmux_session = raw_record.get("tmux_session")
    if not isinstance(session_id, str):
        raise TypeError("session_id must be a string")
    if not isinstance(cwd, str):
        raise TypeError("cwd must be a string")
    if not isinstance(codex_home, str):
        raise TypeError("codex_home must be a string")
    if not isinstance(tmux_session, str) or not tmux_session:
        raise TypeError("tmux_session must be a nonempty string")
    try:
        uuid.UUID(session_id)
    except ValueError as error:
        raise ValueError("session_id must be a UUID") from error

    return {
        "session_id": session_id,
        "cwd": cwd,
        "codex_home": codex_home,
        "tmux_session": tmux_session,
    }


def _restore_record(
    record: _SessionRecord,
    codex: str,
    existing_ids: set[str],
    dry_run: bool,
) -> None:
    session_id = record["session_id"]
    if session_id in existing_ids:
        return

    cwd = Path(record["cwd"])
    if not cwd.is_dir():
        _report(f"Skipping {session_id}: working directory does not exist: {cwd}")
        return

    tmux_session = record["tmux_session"]
    command = _resume_command(record, codex)
    if dry_run:
        action = "new-window" if _session_exists(tmux_session) else "new-session"
        _show(f"{action}: {tmux_session}: {session_id} ({cwd})")
        return

    window_id = _create_window(tmux_session, cwd, command)
    _tag_window(window_id, session_id)
    existing_ids.add(session_id)


def _resume_command(record: _SessionRecord, codex: str) -> str:
    if _ENV is None or _TMUX is None:
        raise FileNotFoundError("env or tmux is not available")
    wait_arguments = [
        _TMUX,
        "wait-for",
        _resume_channel(record["session_id"]),
    ]
    arguments = [
        _ENV,
        f"CODEX_HOME={record['codex_home']}",
        codex,
        "--no-daemon",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        record["cwd"],
        "-c",
        'tui.terminal_title=["thread"]',
        "resume",
        record["session_id"],
    ]
    return f"{shlex.join(wait_arguments)} && exec {shlex.join(arguments)}"


def _create_window(tmux_session: str, cwd: Path, command: str) -> str:
    if _session_exists(tmux_session):
        tmux_session_id = _run_tmux(
            "display-message", "-p", "-t", f"={tmux_session}", "#{session_id}"
        ).stdout.strip()
        result = _run_tmux(
            "new-window",
            "-d",
            "-P",
            "-F",
            "#{window_id}",
            "-t",
            f"{tmux_session_id}:",
            "-c",
            str(cwd),
            command,
        )
    else:
        result = _run_tmux(
            "new-session",
            "-d",
            "-P",
            "-F",
            "#{window_id}",
            "-s",
            tmux_session,
            "-c",
            str(cwd),
            command,
        )
    return result.stdout.strip()


def _session_exists(name: str) -> bool:
    return _run_tmux("has-session", "-t", f"={name}", check=False).returncode == 0


def _tagged_session_ids() -> set[str]:
    result = _run_tmux("list-windows", "-a", "-F", "#{@codex_session_id}", check=False)
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def _tag_window(window_id: str, session_id: str) -> None:
    _run_tmux("set-option", "-w", "-t", window_id, "@codex_session_id", session_id)
    _run_tmux("set-option", "-w", "-t", window_id, "@codex_pending", "1")
    _run_tmux("select-pane", "-t", window_id, "-T", f"codex-{session_id[:8]}")
    _run_tmux(
        "set-option",
        "-w",
        "-t",
        window_id,
        "automatic-rename-format",
        "#{pane_title}",
    )
    _run_tmux("set-option", "-w", "-t", window_id, "automatic-rename", "on")


def _activate_visible_windows(directory: Path) -> None:
    with (directory / ".activate.lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for window_id, session_id in _visible_pending_windows():
            _run_tmux("wait-for", "-S", _resume_channel(session_id))
            _run_tmux("set-option", "-wu", "-t", window_id, "@codex_pending")


def _visible_pending_windows() -> list[tuple[str, str]]:
    window_format = "\t".join(
        (
            "#{window_id}",
            "#{@codex_session_id}",
            "#{@codex_pending}",
            "#{session_attached}",
            "#{window_active}",
        )
    )
    result = _run_tmux("list-windows", "-a", "-F", window_format, check=False)
    if result.returncode != 0:
        return []

    visible_windows = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 5:
            continue
        window_id, session_id, pending, attached, active = fields
        if session_id and pending == "1" and attached != "0" and active == "1":
            visible_windows.append((window_id, session_id))
    return visible_windows


def _resume_channel(session_id: str) -> str:
    return f"codex-resume-{session_id}"


def _run_tmux(
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    if _TMUX is None:
        raise FileNotFoundError("tmux is not available")
    return subprocess.run(  # noqa: S603  # Arguments are passed without a shell.
        [_TMUX, *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def _state_directory() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "codex" / "active-sessions"


def _report(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _show(message: str) -> None:
    sys.stdout.write(f"{message}\n")


if __name__ == "__main__":
    raise SystemExit(main())
