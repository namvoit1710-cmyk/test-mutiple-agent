# Reviewer agent image
# Build context: parent agents/ directory
#   docker build -f agents/reviewer/Dockerfile -t opencode-reviewer:latest agents/

FROM opencode-base:latest

ENV AGENT_NAME=reviewer

# 1. Install the opencode agent file globally
RUN mkdir -p /root/.config/opencode/agents
COPY reviewer/reviewer.md /root/.config/opencode/agents/reviewer.md

# 2. Bake knowledge files into the image
RUN mkdir -p /opencode-knowledge
COPY _shared/              /opencode-knowledge/_shared/
COPY reviewer/docs/        /opencode-knowledge/docs/
COPY reviewer/skills/      /opencode-knowledge/skills/

# 3. Entrypoint: symlinks knowledge into /workspace/, then runs opencode
COPY reviewer/entrypoint.sh /usr/local/bin/reviewer-entrypoint
RUN chmod +x /usr/local/bin/reviewer-entrypoint

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/reviewer-entrypoint"]
