FROM node:20-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai

WORKDIR /workspace

ENV AGENT_NAME=base
ENV ORCHESTRATOR_URL=http://orchestrator:8000
ENV OPENCODE_MODEL=google/gemma-4-31b-it

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
