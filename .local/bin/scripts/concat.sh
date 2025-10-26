#!/usr/bin/env bash

# Concatenate all non-hidden files in the current tree to stdout, with clear separators.
#
# Hidden paths are excluded: any path segment starting with '.' is skipped
# (e.g. .git, .github, .venv, .env, .vscode, and dotfiles at repo root).
#
# Output format per file:
#   # relative/path/to/file
#   ```
#   <file contents>
#   ```
#
# Example usage:
#   ./concat.sh > out.txt
#
# Notes:
# - Uses find ... -path '*/.*' -prune to avoid dotdirs and dotfiles.
# - Skips the destination file you redirect to (if stdout is a regular file).
# - Requires GNU find/sort for -print0/-z to be fully NUL-safe. On macOS, install coreutils.

set -euo pipefail

find . -path '*/.*' -prune -o -type f -print0 | sort -z | while IFS= read -r -d '' f; do
  abs="$PWD/${f#./}"
  if [ -e /dev/fd/1 ] && [ "$abs" -ef /dev/fd/1 ]; then continue; fi
  printf '# %s\n' "$abs"
  printf '```\n'
  cat -- "$f"
  printf '\n```\n\n'
done
