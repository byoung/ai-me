# AI-Me Project: Copilot Instructions

## Project Overview

This is a personal AI agent application that creates an agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The app is deployed as a Gradio chatbot interface on Hugging Face Spaces.

## Architecture

### Core Components

1. **Data Pipeline** (`src/data.py`)
   - **Centralized `DataManager` class** handles complete data pipeline
   - **No dependencies** - accepts configuration parameters directly (decoupled from config.py)
   - Loads markdown files from local `docs/` (default) directory for personal info and development purposes
   - Clones and filters public GitHub repos (e.g., `Neosofia/corporate`) for public context
   - Chunks documents with `CharacterTextSplitter` (default 1200 chars, 200 overlap)
   - Creates an ephemeral ChromaDB vectorstore with `sentence-transformers/all-MiniLM-L6-v2` (default) embeddings

2. **Agent System** (OpenAI Agents SDK)
   - Primary agent: `ai_me` personifies a real person using our vectorstore for RAG
   - Tool: `get_local_info` - async function that queries vectorstore for context
   - Optional: `SourceCodeResearcher` agent (currently disabled due to MCP loop issues) uses GitHub MCP server
   - Uses Groq API with model `openai/openai/gpt-oss-120b` for all agents by default
   - Tracing is enabled via `OPENAI_API_KEY` for debugging and monitoring

3. **MCP Server Integration** (Model Context Protocol)
   - GitHub MCP server runs in Docker (`ghcr.io/github/github-mcp-server`)
   - Time MCP server via `uvx mcp-server-time`
   - MCP servers currently disabled in production (loop issues with current prompts) but fully implemented in notebooks for testing
   - Access via `agents.mcp.MCPServerStdio` wrapper

4. **UI Layer**
   - Gradio `ChatInterface` for conversational UI
   - Single async `chat()` function handles user queries
   - Streams through OpenAI Agents `Runner.run()` with max 30 turns

## Development Workflow

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
- Requires `HF_TOKEN` secret in GitHub repo settings
- App metadata in `src/README.md` (Gradio Space config)

## Key Patterns & Conventions

### Configuration Management (`src/config.py`)
- **Pydantic BaseSettings** with strict type safety and validation
- Automatically loads `.env` file via `SettingsConfigDict(env_file=".env")`
- Import pattern: `from config import config` (singleton instance created by `_load_config()`)
- All API keys are required fields - validation fails fast if missing from .env
- Key typed properties: `config.model: str`, `config.doc_load_local: List[str]`, `config.github_repos: List[str]`, `config.agent_prompt: str`
- **Focused on app/agent config and data sources** - data pipeline implementation details in `DataManager`
- Properties (not computed fields): `mcp_github_params`, `mcp_time_params`, `mcp_params_list`, `agent_prompt`
- Uses `MCPServerParams` Pydantic model for type-safe MCP server configuration

### Data Management Pattern (`src/data.py`)
- **Centralized `DataManager` class** handles complete data pipeline
- **Self-contained with smart defaults** - minimal configuration required
- Import pattern: `from data import DataManager`
- Simplified initialization:
  ```python
  # Typical usage - pass data source configs
  data_manager = DataManager(
      doc_load_local=config.doc_load_local,
      github_repos=config.github_repos
  )
  ```
- Class-level defaults: `DEFAULT_DOC_ROOT` (computed relative to module location: `../docs/`), 
  `DEFAULT_CHUNK_SIZE=1200`, `DEFAULT_CHUNK_OVERLAP=200`, 
  `DEFAULT_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"`, `DEFAULT_DB_NAME="ai_me"`
- `DEFAULT_DOC_ROOT` uses `__file__` to compute path relative to module, ensuring correct path regardless of cwd
- Main method: `data_manager.setup_vectorstore(include_local, include_github, github_repos, reset)`
- Granular methods available:
  - Loading: `load_local_documents()`, `load_github_documents(repos)`
  - Processing: `process_documents(docs)`, `chunk_documents(docs)`
  - Vectorstore: `get_embeddings()`, `create_vectorstore(chunks, reset)`
  - Complete: `setup_vectorstore()` (does everything)
- Automatically adds metadata, fixes GitHub links, and creates queryable vectorstore
- Used by both `app.py` and notebooks for consistency

### Async-First Architecture
- All agent operations are async (`async def chat`, `Runner.run`, `get_local_info`)
- MCP servers require async context: `async with MCPServerStdio(...)`
- Lazy initialization pattern for MCP servers (`ensure_mcp_servers()`)

### Vectorstore Pattern
```python
# ChromaDB uses EphemeralClient (in-memory, fast startup)
# Collection dropped/recreated on each app start
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    client=chromadb.EphemeralClient(),
    collection_name="ai_me"
)
```

### Agent Tool Definition
```python
from agents import function_tool

@function_tool
async def get_local_info(query: str) -> str:
    """Docstring becomes tool description for LLM."""
    # Implementation
```

### Document Loading Convention
- Local: `docs/` directory with glob patterns like `["*.md"]` - personal content not yet published or development purposes
- Remote: GitHub repos via `GitLoader` (e.g., `Neosofia/corporate`) filtered by path (`"website" in file_path`)
- Link rewriting: Baseless links get GitHub URL prefix for proper references based on the repo

## Integration Points

- **Pydantic**: Type-safe configuration with validation (v2.0+)
- **Groq API**: Non-standard OpenAI-compatible endpoint (`base_url="https://api.groq.com/openai/v1"`)
- **Hugging Face**: Deployment target and potentially model source
- **Docker**: Required for GitHub MCP server (mounted socket in docker-compose)
- **LangChain**: Document loading and chunking only (not for agents)
- **OpenAI Agents SDK**: Main agentic framework (`openai-agents` package, not `langchain`)

## Common Gotchas

1. **Model naming**: Always use `"openai/openai/gpt-oss-120b"` for Groq - this is the standard model across all agents
2. **uv vs pip**: Project uses `uv` for lock files; `requirements.txt` generated for Gradio deploy only. Would love to move fully to `uv` but Gradio deploy requires `requirements.txt`
3. **ChromaDB persistence**: EphemeralClient means vectorstore rebuilt on restart
4. **MCP server lifecycle**: Must `await server.connect()` after initialization
5. **Notebooks vs app.py**: Notebooks have active MCP servers for testing; `app.py` has them disabled due to undesired loop behavior with current agent prompts
6. **Hugging Face Spaces**: For some reason the python packages on huggingface spaces are slightly out of date (e.g. `networkx` 3.4.2 vs 3.5). If you hit weird dependency issues during `gradio deploy`, pin the versions in `src/requirements.txt` accordingly.

## File Organization

- `src/config.py` - **Centralized configuration class** (environment, models, prompts, constants)
- `src/data.py` - **Centralized data pipeline** (loading, processing, chunking, vectorstore)
- `src/app.py` - Production Gradio application (imports `config` and `data`)
- `src/notebooks/experiments.ipynb` - Development sandbox with MCP servers enabled
- `docs/` - Local markdown content for RAG during development (will migrate to public repositories based on testing outcomes)
- `pyproject.toml` - uv-managed dependencies
- `Dockerfile` - Includes Docker CLI for MCP server containers
- `docker-compose.yaml` - Dev environment with volume mounts
