# Orchestrator agent image.
# Build context: parent agents/ directory.
#   docker build -f agents/orchestrator/Dockerfile -t opencode-orchestrator:latest agents/

FROM opencode-base:latest

ENV AGENT_NAME=orchestrator

# Install Docker CLI, GitHub CLI (gh), and jq for JSON parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gpg jq ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce-cli gh \
    && rm -rf /var/lib/apt/lists/*

# Entrypoint
COPY orchestrator/entrypoint.sh /usr/local/bin/orchestrator-entrypoint
RUN chmod +x /usr/local/bin/orchestrator-entrypoint

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/orchestrator-entrypoint"]
