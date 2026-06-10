# BE Engineer agent image
# Build context: parent agents/ directory
#   docker build -f agents/be-engineer/Dockerfile -t opencode-be-engineer:latest agents/

FROM opencode-base:latest

ENV AGENT_NAME=be-engineer

# 1. Install the opencode agent file globally
RUN mkdir -p /root/.config/opencode/agents
COPY be-engineer/be-engineer.md /root/.config/opencode/agents/be-engineer.md

# 2. Bake knowledge files into the image
RUN mkdir -p /opencode-knowledge
COPY _shared/                   /opencode-knowledge/_shared/
COPY be-engineer/docs/          /opencode-knowledge/docs/
COPY be-engineer/skills/        /opencode-knowledge/skills/

# 3. Entrypoint: symlinks knowledge into /workspace/, then runs opencode
COPY be-engineer/entrypoint.sh /usr/local/bin/be-engineer-entrypoint
RUN chmod +x /usr/local/bin/be-engineer-entrypoint

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/be-engineer-entrypoint"]
