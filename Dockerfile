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

# Install Playwright system dependencies for headless browser automation
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
        libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libpangocairo-1.0-0 \
        libxshmfence1 libxkbcommon-x11-0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Download official GitHub MCP server binary
RUN mkdir -p /app/bin \
    && curl -L https://github.com/github/github-mcp-server/releases/download/v0.19.0/github-mcp-server_Linux_x86_64.tar.gz \
    | tar -xz -C /app/bin \
    && chmod +x /app/bin/github-mcp-server

WORKDIR /app

# Copy only dependency specifications for layer caching
COPY pyproject.toml uv.lock ./

# Create virtual environment and sync dependencies from lock file
# --no-install-project defers building the local package until source is copied
RUN uv venv && uv sync --locked --no-install-project

# Now copy the complete source code
COPY . /app

# Sync again to install the local package (now that source is present)
RUN uv sync --locked

# Install Playwright browsers for E2E tests
RUN uv run playwright install chromium

# Non-root user with access to /app
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# ENTRYPOINT ensures uv is always the executor (mandatory)
# CMD provides the default argument (can be overridden)
ENTRYPOINT ["uv", "run"]
CMD ["src/app.py"]
