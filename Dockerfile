FROM mcr.microsoft.com/playwright:v1.55.0-noble AS builder

# Python runtime behavior
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"
# uv link mode: use copy instead of hardlinks (Docker volumes often don't support hardlinks)
ENV UV_LINK_MODE=copy

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

# Clean up Python cache files to reduce image size
RUN find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type f -name "*.pyc" -delete && \
    find /app/.venv -type f -name "*.pyo" -delete && \
    rm -rf /root/.cache && \
    # Remove test files and docs from dependencies to save space
    find /app/.venv -type d -name tests -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name docs -exec rm -rf {} + 2>/dev/null || true && \
    # Remove NVIDIA CUDA libraries (not needed for inference, huge space waste)
    find /app/.venv -type d -path "*nvidia*" -exec rm -rf {} + 2>/dev/null || true

# ============================================================================
# Production image - minimal footprint
# ============================================================================
FROM mcr.microsoft.com/playwright:v1.55.0-noble

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"
# uv link mode: use copy instead of hardlinks (Docker volumes often don't support hardlinks)
ENV UV_LINK_MODE=copy

# Install only runtime dependencies (no dev tools)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git python3.12 python3.12-venv curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm cache clean --force

# Create non-root user BEFORE copying files (automatic ownership)
RUN adduser -u 5678 --disabled-password --gecos "" appuser

WORKDIR /app

# Copy files as the target user (automatic ownership, no chown needed)
COPY --chown=appuser:appuser --from=builder /app/bin /app/bin
COPY --chown=appuser:appuser --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appuser . /app

USER appuser

# ENTRYPOINT ensures uv is always the executor (mandatory)
# CMD provides the default argument (can be overridden)
ENTRYPOINT ["uv", "run"]
CMD ["src/app.py"]
