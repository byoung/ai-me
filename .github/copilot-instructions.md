# AI-Me Project: Copilot Instructions

## Project Overview

This is a personal AI agent application that creates an agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The app is deployed as a Gradio chatbot interface on Hugging Face Spaces.

## Development Etiquette and Instructions

### Formatting

- Only break if the line is longer than 100 characters.
- try to keep function calls on a single line if possible.
- use the full 100 characters for comments and docstrings.
- **Always place imports at the top of the file** (following PEP 8): standard library imports first, then third-party imports, then local imports, each group separated by a blank line. Never use inline imports inside functions.

### Testing

- Always run tests after refactoring or adding features.
- **Always check and update notebooks** (`src/notebooks/experiments.ipynb`) when refactoring APIs or changing function signatures. Notebooks are just as important as test files and application code.
- **Use `uv` for all code execution** (tests, scripts, etc.). See `TESTING.md` for test commands: `uv run pytest src/test.py -v`

## Key Patterns & Conventions

### Configuration Management
- **Pydantic BaseSettings** with strict type safety and validation
- **Use immutable configuration pattern**: Prefer creating multiple config instances over mutating shared configs

**Note**: Pydantic secret fields must use `.get_secret_value()` when passed to other classes

### Async-First Architecture

- All agent operations are async (`async def chat`, `Runner.run`, `get_local_info`)
- MCP servers require async context: `async with MCPServerStdio(...)`
- Lazy initialization pattern for MCP servers (`ensure_mcp_servers()`)

### Document Loading Convention

- Local: `docs/` directory with glob patterns like `["*.md"]` - personal content not yet published or development purposes
- Remote: GITHUB_REPOS should be set to a comma separated list of public GitHub repos (e.g., `Neosofia/corporate`) - must be public for unauthenticated access
- Link rewriting: Baseless links get GitHub URL prefix for proper references based on the repo

## Common Gotchas/Reminders

1. **Model naming**: For some reason OpenAI and Groq can't agree to be concise so the default model name is `"openai/openai/gpt-oss-120b"` 
1. **uv vs pip**: Project uses `uv` for lock files; don't use `pip` directly
1. **ChromaDB persistence**: EphemeralClient means vectorstore rebuilt on restart
1. **VPN Warning**: Groq API blocks VPN connections. If tests/app fail with 403 errors, disconnect from VPN
