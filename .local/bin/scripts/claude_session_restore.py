#!/usr/bin/env python3

"""Restore tracked Claude Code sessions into their tmux project sessions."""

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
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    claude = shutil.which("claude")
    if not claude or _TMUX is None or _ENV is None:
        _report("Claude session restore requires claude, env, and tmux in PATH")
        return 1

    directory = _state_directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / ".restore.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        _restore_records(directory, claude, arguments.dry_run)

    return 0


class _SessionRecord(TypedDict):
    session_id: str
    cwd: str
    claude_config_dir: str | None
    tmux_session: str


def _restore_records(directory: Path, claude: str, dry_run: bool) -> None:
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
                _restore_record(record, claude, existing_ids, dry_run)
            except subprocess.CalledProcessError as error:
                detail = error.stderr.strip() or str(error)
                _report(
                    f"Failed to restore {record['session_id']} into "
                    f"{tmux_session}: {detail}"
                )


def _load_records(directory: Path) -> list[_SessionRecord]:
    records = []
    for marker in sorted(directory.glob("*.json")):
        try:
            record = _load_record(marker)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            _report(f"Skipping invalid Claude session marker {marker}: {error}")
            continue
        records.append(record)
    return records


def _load_record(marker: Path) -> _SessionRecord:
    raw_record: object = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(raw_record, dict):
        raise TypeError("expected a JSON object")

    session_id = raw_record.get("session_id")
    cwd = raw_record.get("cwd")
    claude_config_dir = raw_record.get("claude_config_dir")
    tmux_session = raw_record.get("tmux_session")
    if not isinstance(session_id, str):
        raise TypeError("session_id must be a string")
    if not isinstance(cwd, str):
        raise TypeError("cwd must be a string")
    if claude_config_dir is not None and not isinstance(claude_config_dir, str):
        raise TypeError("claude_config_dir must be a string or null")
    if not isinstance(tmux_session, str) or not tmux_session:
        raise TypeError("tmux_session must be a nonempty string")
    try:
        uuid.UUID(session_id)
    except ValueError as error:
        raise ValueError("session_id must be a UUID") from error

    return {
        "session_id": session_id,
        "cwd": cwd,
        "claude_config_dir": claude_config_dir,
        "tmux_session": tmux_session,
    }


def _restore_record(
    record: _SessionRecord,
    claude: str,
    existing_ids: set[str],
    dry_run: bool,
) -> None:
    session_id = record["session_id"]
    if session_id in existing_ids:
        return

    # Claude stores transcripts per working directory, so resume must start there.
    cwd = Path(record["cwd"])
    if not cwd.is_dir():
        _report(f"Skipping {session_id}: working directory does not exist: {cwd}")
        return

    tmux_session = record["tmux_session"]
    command = _resume_command(record, claude)
    if dry_run:
        action = "new-window" if _session_exists(tmux_session) else "new-session"
        _show(f"{action}: {tmux_session}: {session_id} ({cwd})")
        return

    window_id = _create_window(tmux_session, cwd, command)
    _tag_window(window_id, session_id)
    existing_ids.add(session_id)


def _resume_command(record: _SessionRecord, claude: str) -> str:
    if _ENV is None:
        raise FileNotFoundError("env is not available")
    arguments = [_ENV]
    if record["claude_config_dir"]:
        arguments.append(f"CLAUDE_CONFIG_DIR={record['claude_config_dir']}")
    arguments += [
        claude,
        "--dangerously-skip-permissions",
        "--resume",
        record["session_id"],
    ]
    return f"exec {shlex.join(arguments)}"


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
    result = _run_tmux("list-windows", "-a", "-F", "#{@claude_session_id}", check=False)
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def _tag_window(window_id: str, session_id: str) -> None:
    _run_tmux("set-option", "-w", "-t", window_id, "@claude_session_id", session_id)
    _run_tmux("select-pane", "-t", window_id, "-T", f"claude-{session_id[:8]}")
    _run_tmux(
        "set-option",
        "-w",
        "-t",
        window_id,
        "automatic-rename-format",
        # Drop the status glyph Claude puts before its terminal title.
        "#{s/^[^a-zA-Z0-9]+ //:pane_title}",
    )
    _run_tmux("set-option", "-w", "-t", window_id, "automatic-rename", "on")


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
    return root / "claude" / "active-sessions"


def _report(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _show(message: str) -> None:
    sys.stdout.write(f"{message}\n")


if __name__ == "__main__":
    raise SystemExit(main())
