FROM mcr.microsoft.com/playwright:v1.48.0-noble

# Python runtime behavior
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"

# Install uv, Python, git, and Node.js (for Memory MCP server via npx)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg git git-lfs python3.12 python3.12-venv \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm cache clean --force

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

# Non-root user with access to /app
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# ENTRYPOINT ensures uv is always the executor (mandatory)
# CMD provides the default argument (can be overridden)
ENTRYPOINT ["uv", "run"]
CMD ["src/app.py"]
