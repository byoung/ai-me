---
title: ben-bot
app_file: src/app.py
sdk: docker
---
# ai-me

An agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The agent learns from personal docs and public GitHub repos to answer questions and maintain context about a person's work, writing, and expertise.

Deployed as a Gradio chatbot on Hugging Face Spaces.

## Architecture Overview

### Core Design

**Data Pipeline** → **Agent System Set Up** → **Chat Interface**

1. **Data Pipeline** (`src/data.py`)
   - Loads markdown from local `docs/` and public GitHub repos
   - Chunks with LangChain, embeds with HuggingFace sentence-transformers
   - Stores in ephemeral ChromaDB vectorstore

2. **Agent System** (`src/agent.py`)
   - Primary agent personifies a real person using RAG
   - Queries vectorstore via async `get_local_info` tool
   - Uses Groq API (`openai/openai/gpt-oss-120b`) for LLM inference
   - OpenAI API for tracing/debugging only

3. **UI Layer** (`src/app.py`)
   - Simple chat interface streams responses
   - Async-first architecture throughout

### Key Technologies

- **Python 3.12** with `uv` for dependency management
- **OpenAI Agents SDK** for agentic framework
- **LangChain** for document loading/chunking only
- **ChromaDB** with ephemeral in-memory storage
- **Gradio** for UI and Hugging Face Spaces deployment
- **Groq** as primary LLM provider for fast inference
- **Pydantic** for type-safe configuration

## Getting Started

### Environment Setup

```bash
# Install dependencies Locally
uv sync

# OR build the container
docker compose build notebooks

# NOTE: if you go the local route it's assume you have nodejs and npx installed

# Create .env with required keys:
OPENAI_API_KEY=<for tracing>
GROQ_API_KEY=<primary LLM provider>
GITHUB_PERSONAL_ACCESS_TOKEN=<for searching GitHub repos>
BOT_FULL_NAME=<full name of the persona>
APP_NAME=<name that appears on HF chat page>
GITHUB_REPOS=<comma-separated list of public repos: owner/repo,owner/repo>
```

**Note**: A Git pre-commit hook is installed at `.git/hooks/pre-commit` that automatically clears all notebook outputs before committing. This keeps the repository clean and reduces diff noise.

### Running

```bash
# Local
uv run src/app.py  # Launches Gradio on default port

# Docker
docker compose up notebooks
```

If you use the Docker route, you can use the Dev Containers extension in most popular IDEs to attach to the running container and run notebook cells as you would in a normal local environment.


## Deployment

```bash
# Run from the root directory
gradio deploy
```

**Automatic CI/CD**: Push to `main` triggers a GitHub Actions workflow that deploys to Hugging Face Spaces via Gradio CLI. The following environment variables need to be set up in GitHub for the CI/CD pipeline:

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

# Public
APP_NAME
BOT_FULL_NAME
GITHUB_REPOS
```

## Design Principles

1. **Decoupled Architecture**: Config handles sources, DataManager handles pipeline, app orchestrates
2. **Smart Defaults**: Minimal configuration required - most params have sensible defaults
3. **Async-First**: All agent operations are async for responsive UI
4. **Ephemeral Storage**: Vectorstore rebuilt on each restart (fast, simple, stateless)
5. **Type Safety**: Pydantic models with validation throughout
6. **Development/Production Parity**: Same DataManager used in notebooks and production app

## Project Structure

```
src/
  ├── config.py              # Pydantic settings, API keys, data sources
  ├── data.py                # DataManager class - complete pipeline
  ├── agent.py               # Agent creation and orchestration
  ├── app.py                 # Production Gradio app
  ├── test.py                # Unit tests
  ├── __init__.py
  └── notebooks/
      └── experiments.ipynb  # Development sandbox with MCP servers

docs/                        # Local markdown for RAG (development)
test_data/                   # Test fixtures and sample data
.github/
  ├── copilot-instructions.md  # Detailed implementation guide for AI
  └── workflows/
      └── update_space.yml     # CI/CD to Hugging Face
```

## Reminders/Warnings

- **Data Sources**: The default for local development is the `docs/` folder. If you want your production app to access this content post deploy, it must be pushed to a public GitHub repo until we support private repo document loading for RAG.
- **Model Choice**: Groq's `gpt-oss-120b` provides good quality with ultra-fast inference. If you change the model, be aware that tool calling may degrade which can lead to runtime errors.
- **Docker in Docker**: A prior version of this app had the Docker command built into the container. Because the GitHub MCP server was moved from `docker` to `npx`, the CLI is no longer included in the [Dockerfile](Dockerfile). However, the socket mount in [docker-compose](docker-compose.yaml) was left as we may revisit Docker MCP servers in the future. We will never support a pure docker-in-docker setup, but socket mounting may still be an option.
- **The Agent does not have memory!**: This was an intentional design decision until multithreaded operations can be supported/tested on HF.

---

For detailed implementation patterns, code conventions, and AI assistant context, see [`.github/copilot-instructions.md`](.github/copilot-instructions.md).