# AI-Me Project: Copilot Instructions

## Project Overview

This is a personal AI agent application that creates an agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The app is deployed as a Gradio chatbot interface on Hugging Face Spaces.

## Development Etiquette and Instructions

### Formatting

- Only break if the line is longer than 100 characters.
- try to keep function calls on a single line if possible.
- use the full 100 characters for comments and docstrings.

### Testing

- Always run tests after refactoring or adding features.
- **Always check and update notebooks** (`src/notebooks/experiments.ipynb`) when refactoring APIs or changing function signatures. Notebooks are just as important as test files and application code.
- **Use `uv` for all code execution** (tests, scripts, etc.). See `TESTING.md` for test commands: `uv run pytest src/test.py -v`

### Environment Setup

```bash
# Use uv for dependency management (see pyproject.toml)
uv sync

# Required environment variables (create .env):
OPENAI_API_KEY=<for tracing>
GROQ_API_KEY=<primary LLM provider>
GITHUB_PERSONAL_ACCESS_TOKEN=<for MCP servers and GitLoader>
```

### Running Locally

```bash
# Production app
cd src
python app.py  # Launches Gradio on default port

# Experiments (notebooks)
# Notebook can be run locally after a uv sync or in via docker-compose
docker-compose up notebooks
# Access Jupyter at localhost:7861
```

### Deployment

```bash
# Production app
cd src
gradio deploy

Automatic CI/CD via `.github/workflows/update_space.yml`:
- Push to `main` triggers Gradio CLI deployment to Hugging Face Spaces
- App metadata in `src/README.md` (Gradio Space config)

## Key Patterns & Conventions

### Configuration Management
- **Pydantic BaseSettings** with strict type safety and validation
- Automatically loads `.env` file via `SettingsConfigDict(env_file=".env")`
- All API keys are required fields - validation fails fast if missing from .env or environment
- **Immutable configuration pattern**: Prefer creating multiple config instances over mutating shared configs
  - Use smart `default` values in Pydantic Fields that get replaced at instantiation
  - Avoid `default_factory` unless values will be mutated after creation
  - Example: `DataManagerConfig(github_repos=["repo1"])` vs mutating a shared instance

**Note**: Pydantic secret fields must use `.get_secret_value()` when passed to other classes

### Async-First Architecture
- All agent operations are async (`async def chat`, `Runner.run`, `get_local_info`)
- MCP servers require async context: `async with MCPServerStdio(...)`
- Lazy initialization pattern for MCP servers (`ensure_mcp_servers()`)

### Document Loading Convention
- Local: `docs/` directory with glob patterns like `["*.md"]` - personal content not yet published or development purposes
- Remote: GITHUB_REPOS should be set to a comma separated list of public GitHub repos (e.g., `Neosofia/corporate`) - must be public for unauthenticated access
- Link rewriting: Baseless links get GitHub URL prefix for proper references based on the repo

## Integration Points

- **Groq API**: Non-standard OpenAI-compatible endpoint (`base_url="https://api.groq.com/openai/v1"`)
- **Hugging Face**: Deployment target and potentially model source
- **Docker**: Required for GitHub MCP server (mounted socket in docker-compose)
- **LangChain**: Document loading and chunking only (not for agents)
- **OpenAI Agents SDK**: Main agentic framework (`openai-agents` package, not `langchain`)

## Common Gotchas

1. **Model naming**: For some reason OpenAI and Groq can't agree to be concise so the default model name is `"openai/openai/gpt-oss-120b"` 
1. **uv vs pip**: Project uses `uv` for lock files; `requirements.txt` generated for Gradio deploy only. Would love to move fully to `uv` but Gradio deploy requires `requirements.txt`
1. **ChromaDB persistence**: EphemeralClient means vectorstore rebuilt on restart
1. **Hugging Face Spaces**: For some reason the python packages on huggingface spaces are slightly out of date (e.g. `networkx` 3.4.2 vs 3.5). If you hit weird dependency issues during `gradio deploy`, pin the versions in `src/requirements.txt` accordingly.

## File Organization

- `src/config.py` - **Centralized configuration class** (environment, models, prompts, constants)
- `src/data.py` - **Centralized data pipeline** (loading, processing, chunking, vectorstore)
- `src/app.py` - Production Gradio application (imports `config` and `data`)
- `src/notebooks/experiments.ipynb` - Development sandbox with MCP servers enabled
- `docs/` - Local markdown content for RAG during development (will migrate to public repositories based on testing outcomes)
- `pyproject.toml` - uv-managed dependencies
- `Dockerfile` - Includes Docker CLI for MCP server containers
- `docker-compose.yaml` - Dev environment with volume mounts
