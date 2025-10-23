# Contributing to AI-Me

Welcome! This document outlines the process for contributing to the AI-Me project.

## Prerequisites

- Python 3.12+ (managed by `uv`)
- Git with GPG signing configured
- Basic understanding of async Python and RAG concepts (see `.specify/memory/constitution.md`)

## Setup

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/byoung/ai-me.git
cd ai-me
uv sync
```

### 2. Environment Configuration

Create a `.env` file in the project root with required keys:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...

# Bot Identity
BOT_FULL_NAME="Ben Young"
APP_NAME="AI-Me"

# Optional: External Tools
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
LINKEDIN_API_TOKEN=...

# Optional: Remote Logging (Grafana Loki)
LOKI_URL=https://logs-prod-us-central1.grafana.net
LOKI_USERNAME=...
LOKI_PASSWORD=...
```

### 3. Configure Git Commit Signing

See this guide on setting up gpg keys:

https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key


**All commits MUST be GPG-signed.**
