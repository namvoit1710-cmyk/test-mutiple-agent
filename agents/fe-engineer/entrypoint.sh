#!/usr/bin/env bash
set -euo pipefail

# Symlink knowledge into cwd so the agent can read by relative path.
for path in _shared docs skills; do
  # Remove existing symlink if present (handles broken symlinks too)
  if [ -L "/workspace/$path" ]; then
    rm "/workspace/$path"
  fi
  # Create symlink if target doesn't exist (or was a symlink we just removed)
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done

PROMPT="${PROMPT:-Read docs/tasks.md and implement the task you were assigned.}"

exec opencode run \
  --agent fe-engineer \
  --print-logs \
  "$PROMPT"
