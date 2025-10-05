# ai-me

An agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The agent learns from personal docs and public GitHub repos to answer questions and maintain context about a person's work, writing, and expertise.

Deployed as a Gradio chatbot on Hugging Face Spaces.

## Architecture Overview

### Core Design

**Data Pipeline** → **Agent System** → **Chat Interface**

1. **Data Pipeline** (`src/data.py`)
   - Loads markdown from local `docs/` and public GitHub repos
   - Chunks with LangChain, embeds with HuggingFace sentence-transformers
   - Stores in ephemeral ChromaDB vectorstore

2. **Agent System** (OpenAI Agents SDK)
   - Primary agent personifies a real person using RAG
   - Queries vectorstore via async `get_local_info` tool
   - Uses Groq API (`openai/openai/gpt-oss-120b`) for LLM inference
   - OpenAI API for tracing/debugging only

3. **UI Layer** (Gradio)
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
# Install dependencies
uv sync

# Create .env with required keys:
OPENAI_API_KEY=<for tracing>
GROQ_API_KEY=<primary LLM provider>
GITHUB_PERSONAL_ACCESS_TOKEN=<for loading GitHub repos>
```

**Note**: A Git pre-commit hook is installed at `.git/hooks/pre-commit` that automatically clears all notebook outputs before committing. This keeps the repository clean and reduces diff noise.

### Running Locally

```bash
# Production app
cd src
python app.py  # Launches Gradio on default port

# Experiments (notebooks)
docker-compose up notebooks
# Access Jupyter at localhost:7861
```

## Deployment

```bash
cd src
uv export --no-dev --no-hashes --format requirements-txt > requirements.txt
gradio deploy
```

**Automatic CI/CD**: Push to `main` triggers GitHub Actions workflow that deploys to Hugging Face Spaces via Gradio CLI.

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
  ├── app.py                 # Production Gradio app
  └── notebooks/
      └── experiments.ipynb  # Development sandbox with MCP servers

docs/                        # Local markdown for RAG (development)
.github/
  ├── copilot-instructions.md  # Detailed implementation guide for AI
  └── workflows/
      └── update_space.yml     # CI/CD to Hugging Face
```

## Notes

- **MCP Integration**: GitHub and Time MCP servers implemented but disabled in production due to loop issues with current prompts. Fully functional in notebooks for experimentation.
- **Data Sources**: Currently uses local `docs/` for development. Will migrate to public repos after testing.
- **Model Choice**: Groq's `gpt-oss-120b` provides good quality with fast, free inference.

---

For detailed implementation patterns, code conventions, and AI assistant context, see [`.github/copilot-instructions.md`](.github/copilot-instructions.md).