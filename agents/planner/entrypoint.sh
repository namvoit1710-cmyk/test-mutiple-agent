#!/usr/bin/env bash
# Stage knowledge files into the worktree so the agent can read them by
# relative path, then run opencode with the planner agent.
set -euo pipefail

# Make the knowledge available in cwd. Use symlinks so the worktree's git
# isn't polluted (add the paths to .gitignore at orchestrator level).
# The worktree usually already has docs/ (requirement.md lives there), so
# merge knowledge file-by-file instead of skipping existing directories.
for path in _shared skills io-contract.md AGENT.md; do
  # Remove existing symlink if present (handles broken symlinks too)
  if [ -L "/workspace/$path" ]; then
    rm "/workspace/$path"
  fi
  # Create symlink if target doesn't exist (or was a symlink we just removed)
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done
# models.dev flags gemma-4-31b-it as reasoning:true, which makes opencode send
# thinkingConfig.thinkingLevel — the Gemini API rejects that for gemma models
# (400 "Thinking level is not supported"). Force reasoning off; model is defined
# in planner.md frontmatter and does not need to be repeated here.
cat > /workspace/opencode.json << 'JSONEOF'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "google": {
      "models": {
        "gemma-4-31b-it": {
          "reasoning": false
        }
      }
    }
  }
}
JSONEOF

# Ensure staged knowledge and generated config never land in commits
GI="/workspace/.gitignore"
touch "$GI"
for entry in _shared skills io-contract.md AGENT.md opencode.json .pipeline-state.json; do
  grep -qxF "$entry" "$GI" || echo "$entry" >> "$GI"
done
# Also exclude the skill symlinks under skills/
for entry in writing-plans; do
  grep -qxF "skills/$entry" "$GI" || echo "skills/$entry" >> "$GI"
done

# Run opencode with the planner agent. The prompt comes from $PROMPT env var
# (set by the orchestrator), or you can pass args to docker run.
PROMPT="${PROMPT:-Read the specification from app/docs/spec/requirement.md and write an implementation plan to app/docs/plan/requirement.md.}"

exec opencode run \
  --agent planner \
  --print-logs \
  "$PROMPT"