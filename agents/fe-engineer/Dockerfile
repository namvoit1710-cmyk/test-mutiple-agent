# FE Engineer agent image
# Build context: parent agents/ directory
#   docker build -f agents/fe-engineer/Dockerfile -t opencode-fe-engineer:latest agents/

FROM opencode-base:latest

ENV AGENT_NAME=fe-engineer

# 1. Install the opencode agent file globally
RUN mkdir -p /root/.config/opencode/agents
COPY fe-engineer/fe-engineer.md /root/.config/opencode/agents/fe-engineer.md

# 2. Bake knowledge files into the image
RUN mkdir -p /opencode-knowledge
COPY _shared/                   /opencode-knowledge/_shared/
COPY fe-engineer/docs/          /opencode-knowledge/docs/
COPY fe-engineer/skills/        /opencode-knowledge/skills/

# 3. Entrypoint: symlinks knowledge into /workspace/, then runs opencode
COPY fe-engineer/entrypoint.sh /usr/local/bin/fe-engineer-entrypoint
RUN chmod +x /usr/local/bin/fe-engineer-entrypoint

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/fe-engineer-entrypoint"]
