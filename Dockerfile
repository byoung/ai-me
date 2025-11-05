# =============================================================================
# Builder Stage: Install dependencies and build wheels
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /build

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Create venv and install ONLY production dependencies in builder
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv sync --locked --no-install-project

# Copy source and install project
COPY . .
RUN . /opt/venv/bin/activate && uv sync --locked

# =============================================================================
# Runtime Stage: Minimal image with Playwright support
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TORCH_DEVICE=cpu \
    NO_CUDA=1 \
    CUDA_VISIBLE_DEVICES=""

# Install runtime + Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm cache clean --force

# Install uv in runtime
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create non-root user early
RUN useradd -m -u 5678 appuser

# Copy venv from builder with ownership
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Download GitHub MCP server binary
RUN mkdir -p /app/bin && \
    curl -L https://github.com/github/github-mcp-server/releases/download/v0.19.0/github-mcp-server_Linux_x86_64.tar.gz \
    | tar -xz -C /app/bin && \
    chmod +x /app/bin/github-mcp-server && \
    chown appuser:appuser /app/bin/github-mcp-server

WORKDIR /app
COPY --chown=appuser:appuser . .

# Switch to non-root user for runtime
USER appuser

ENTRYPOINT ["uv", "run"]
CMD ["src/app.py"]

# ============================================================================
# Test Stage - Extends runtime with dev dependencies for testing
# ============================================================================
FROM runtime AS test

# Switch back to root to install test dependencies
USER root

# Install dev dependencies (playwright, pytest, etc.) into existing venv
# Use UV_PROJECT_ENVIRONMENT to force uv to use /opt/venv instead of creating .venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv sync --locked --group dev

# Install Playwright browsers (now that playwright package is available)
RUN /opt/venv/bin/python -m playwright install chromium

# Switch back to appuser for test execution
USER appuser
