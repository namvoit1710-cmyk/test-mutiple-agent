#!/usr/bin/env bash
# Stage knowledge files into the worktree so the agent can read them by
# relative path, then run opencode with the planner agent.
set -euo pipefail

# Make the knowledge available in cwd. Use symlinks so the worktree's git
# isn't polluted (add the paths to .gitignore at orchestrator level).
for path in _shared docs skills io-contract.md; do
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done

# Generate opencode.json with small_model set to prevent title gen
# from burning quota on gemini-3-flash-preview
MODEL="${OPENCODE_MODEL:-google/gemma-4-31b-it}"
cat > /workspace/opencode.json << JSONEOF
{
  "$schema": "https://opencode.ai/config.json",
  "model": "$MODEL",
  "small_model": "$MODEL"
}
JSONEOF

# Run opencode with the planner agent. The prompt comes from $PROMPT env var
# (set by the orchestrator), or you can pass args to docker run.
PROMPT="${PROMPT:-Read docs/requirement.md and produce docs/tasks.md.}"

exec opencode run \
  --agent planner \
  --print-logs \
  "$PROMPT"