#!/usr/bin/env bash
set -euo pipefail

# Symlink knowledge into cwd so the agent can read by relative path.
for path in _shared docs skills; do
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done

PROMPT="${PROMPT:-Review the code changes in this workspace and report findings.}"

exec opencode run \
  --agent reviewer \
  --print-logs \
  "$PROMPT"
