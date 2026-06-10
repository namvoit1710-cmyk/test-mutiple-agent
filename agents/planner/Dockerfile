# Planner agent image — opencode standard layout.
#
# OpenCode discovers agents from .opencode/agents/<name>.md (project)
# or ~/.config/opencode/agents/<name>.md (global).
# We install the agent globally so it works regardless of cwd.
#
# Build context: parent agents/ directory so we can copy _shared/ too.
#   docker build -f agents/planner/Dockerfile -t opencode-planner:latest agents/

FROM opencode-base:latest

ENV AGENT_NAME=planner

# 1. Install the agent file at the global opencode location.
#    Filename MUST be <agent-name>.md per opencode convention.
RUN mkdir -p /root/.config/opencode/agents
COPY planner/planner.md /root/.config/opencode/agents/planner.md

# 2. Knowledge files (docs/, skills/, io-contract.md) live next to the
#    workspace so paths inside planner.md (`_shared/...`, `docs/...`) resolve
#    relative to cwd. The orchestrator mounts the worktree at /workspace
#    and we copy our knowledge into a sibling layout the agent can read.
RUN mkdir -p /opencode-knowledge
COPY _shared/         /opencode-knowledge/_shared/
COPY planner/skills/  /opencode-knowledge/skills/
COPY planner/io-contract.md /opencode-knowledge/io-contract.md
COPY planner/AGENT.md       /opencode-knowledge/AGENT.md

# 3. Entry script: stage knowledge into the worktree before running opencode,
#    so the agent's relative reads (`_shared/docs/project-overview.md`) work.
#    Knowledge files are read-only context — they shouldn't pollute the
#    worktree's git status. We symlink them as hidden.
COPY planner/entrypoint.sh /usr/local/bin/planner-entrypoint
RUN chmod +x /usr/local/bin/planner-entrypoint

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/planner-entrypoint"]