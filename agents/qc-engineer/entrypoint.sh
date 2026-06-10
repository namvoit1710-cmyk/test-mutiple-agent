#!/usr/bin/env bash
set -euo pipefail

# Symlink knowledge into cwd so the agent can read by relative path.
for path in _shared docs skills; do
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done

PROMPT="${PROMPT:-Read docs/tasks.md and write failing tests for the task you were assigned.}"

exec opencode run \
  --agent qc-engineer \
  --print-logs \
  "$PROMPT"
