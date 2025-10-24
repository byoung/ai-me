---
title: ben-bot
app_file: src/app.py
sdk: docker
---
# ai-me

An agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The agent learns from personal docs and public GitHub repos to answer questions and maintain context about a person's work, writing, and expertise.

Deployed as a Gradio chatbot on Hugging Face Spaces.

Example: https://huggingface.co/spaces/byoung-hf/ben-bot

## Getting Started

If you want to experiment with building your own agentic self, clone the repo and follow the steps below.

### Prerequisites

- [Docker](https://docs.docker.com/engine/install/) or [uv](https://docs.astral.sh/uv/getting-started/installation/) for running the application
- If you run locally, you need [npx](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) installed
- Groq and OpenAI for inference and tracing
- A GitHub PAT for the GitHub tool (optional)

### Environment Setup

```bash
# Install dependencies Locally
uv sync

# OR build the container
docker compose build notebooks

# Create .env with required keys:
OPENAI_API_KEY=<for tracing>
GROQ_API_KEY=<primary LLM provider>
GITHUB_PERSONAL_ACCESS_TOKEN=<for searching GitHub repos>
BOT_FULL_NAME=<full name of the persona>
APP_NAME=<name that appears on HF chat page>
GITHUB_REPOS=<comma-separated list of public repos: owner/repo,owner/repo with md files to be ingested by RAG>

# Optional: Set log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.
LOG_LEVEL=INFO
```

### Running

```bash
# Local
uv run src/app.py  # Launches Gradio on default port

# Docker
docker compose up notebooks
```

If you use the Docker route, you can use the Dev Containers extension in most popular IDEs to attach to the running container and run notebook cells as you would in a normal local environment.


## Deployment

To deploy the application to HF, you need to update the comment at the top of this README and create your own HF account and put a HF_TOKEN into your .env file.

```bash
# Run from the root directory
gradio deploy
```

**Automatic CI/CD**: Pushing to `main` triggers a GitHub Actions workflow that deploys to Hugging Face Spaces via Gradio CLI. The following environment variables need to be set up in GitHub for the CI/CD pipeline:

```bash
# Testing 
GROQ_API_KEY
OPENAI_API_KEY

# Deployment
HF_TOKEN
```

And Hugging Face needs to have these keys set:

```bash
# PRIVATE!!!
GROQ_API_KEY
OPENAI_API_KEY
GITHUB_PERSONAL_ACCESS_TOKEN

# Optional: Grafana Cloud Loki (Remote Logging)
LOKI_URL
LOKI_USERNAME
LOKI_PASSWORD

# Public
APP_NAME
BOT_FULL_NAME
GITHUB_REPOS
ENV  # e.g., "production" - used for log tagging
```

## Architecture and Design Overview

All of our architecture and design thinking can be found in our [constitution](/.specify/memory/constitution.md) and [ADRs](/architecture/adrs/)

Some implementation decisions have been captured in our [`.github/copilot-instructions.md`](.github/copilot-instructions.md), but will be integrated into other documents over time.

## Contributions

Check out our [CONTRIBUTING.md](/CONTRIBUTING.md) guide for detailed instructions on how you can contribute.

## Reminders/Warnings/Gotchas
- **Data Sources**: The default for local development is the `docs/local-testing` folder. If you want your production app to access this content post deploy, it must be pushed to a public GitHub repo until we support private repo document loading for RAG.
- **Model Choice**: Groq's `gpt-oss-120b` provides good quality with ultra-fast inference. If you change the model, be aware that tool calling may degrade which can lead to runtime errors.
- **Docker in Docker**: A prior version of this app had the Docker command built into the container. Because the GitHub MCP server was moved from `docker` to `npx`, the CLI is no longer included in the [Dockerfile](Dockerfile). However, the socket mount in [docker-compose](docker-compose.yaml) was left as we may revisit Docker MCP servers in the future. We will never support a pure docker-in-docker setup, but socket mounting may still be an option.

---
