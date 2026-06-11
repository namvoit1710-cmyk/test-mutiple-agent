# QC Engineer agent image
# Build context: parent agents/ directory
#   docker build -f agents/qc-engineer/Dockerfile -t opencode-qc-engineer:latest agents/

FROM opencode-base:latest

ENV AGENT_NAME=qc-engineer

# 1. Install the opencode agent file globally
RUN mkdir -p /root/.config/opencode/agents
COPY qc-engineer/qc-engineer.md /root/.config/opencode/agents/qc-engineer.md

# 2. Bake knowledge files into the image
RUN mkdir -p /opencode-knowledge
COPY _shared/                    /opencode-knowledge/_shared/
COPY qc-engineer/docs/           /opencode-knowledge/docs/
COPY qc-engineer/skills/         /opencode-knowledge/skills/

# 3. Entrypoint: symlinks knowledge into /workspace/, then runs opencode
COPY qc-engineer/entrypoint.sh /usr/local/bin/qc-engineer-entrypoint
RUN chmod +x /usr/local/bin/qc-engineer-entrypoint

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/qc-engineer-entrypoint"]
