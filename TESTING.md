# Integration Tests

## Overview

The test suite (`src/test.py`) validates the ai-me agent system including:
- Vectorstore setup and document loading
- Agent configuration and initialization
- RAG (Retrieval Augmented Generation) functionality
- Basic agent response quality and accuracy

## Running Tests

### Prerequisites

1. Ensure environment variables are set in `.env` file at project root:
   ```bash
   OPENAI_API_KEY=<your-openai-key>     # For tracing
   GROQ_API_KEY=<your-groq-key>         # For LLM inference
   GH_PERSONAL_ACCESS_TOKEN=<token> # For GitHub integration (optional for tests)
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

### Run All Tests

From project root:
```bash
# All tests
uv run pytest src/test.py -v

# With detailed output
uv run pytest src/test.py -v -s

# Specific test
uv run pytest src/test.py::test_rear_knowledge_contains_it245 -v
```

## Test Architecture

### Fixture: `ai_me_agent`

**Scope**: Module (shared across all tests in the file)

**Purpose**: Creates a single agent instance that is reused across all tests to avoid expensive reinitialization.

**Configuration**:
- **Temperature**: Set to 0.0 for deterministic, reproducible responses
- **MCP Servers**: Disabled by default for faster test execution
- **Model**: Uses model specified in config (default: `openai/openai/gpt-oss-120b` via Groq)
- **Data Source**: `test_data/` directory (configured via `doc_root` parameter)
- **GitHub Repos**: Disabled (`GITHUB_REPOS=""`) for faster test execution

The temperature of 0 ensures that the agent's responses are consistent across test runs, making assertions more reliable.

## Future Enhancements
- [ ] Add tests for error handling and edge cases
- [ ] Add performance benchmarks
- [ ] Add tests for different document sources
- [ ] Add tests for agent memory/context management
- [ ] Add tests for multi-turn conversations
- [ ] Test with MCP servers enabled
- [ ] Add more comprehensive RAG quality tests
