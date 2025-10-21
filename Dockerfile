FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Python runtime behavior
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies: git (for GitPython) and Node.js (for MCP servers via npx)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg git git-lfs \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Download official GitHub MCP server binary
RUN mkdir -p /app/bin \
    && curl -L https://github.com/github/github-mcp-server/releases/download/v0.19.0/github-mcp-server_Linux_x86_64.tar.gz \
    | tar -xz -C /app/bin \
    && chmod +x /app/bin/github-mcp-server

WORKDIR /app

# Install project dependencies with uv
COPY pyproject.toml uv.lock ./
RUN uv sync

COPY . /app

# Non-root user with access to /app
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

ENTRYPOINT ["uv", "run", "src/app.py"]
