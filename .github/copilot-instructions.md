# AI-Me Project: Copilot Instructions

## Project Overview

This is a personal AI agent application that creates an agentic version of real people using RAG (Retrieval Augmented Generation) over markdown documentation. The app is deployed as a Gradio chatbot interface on Hugging Face Spaces.

## Architecture & Development Principles

For comprehensive architectural principles, code organization, and development patterns, see the authoritative source: **[`.specify/memory/constitution.md`](../.specify/memory/constitution.md)**

The constitution covers:
- **I. Async-First Architecture** - async operations, MCP servers, session management
- **II. RAG-First Data Pipeline** - document loading, chunking, vectorstore strategy
- **III. Type-Safe Configuration** - Pydantic models, immutable config pattern
- **IV. Session Isolation & MCP Management** - per-session agents, cleanup patterns
- **V. Test-First Development** - testing requirements, notebook synchronization
- **VI. Strict Import Organization** - PEP 8, 98-character line limit, formatting
- **VII. GitHub Tool Restrictions** - rate limits, search filters
- **VIII. Observability & Logging** - structured JSON logs, optional Loki integration
- **IX. Persona Consistency** - first-person perspective, employer transparency
- **X. Unicode Normalization** - output cleanliness

## Quick Development Checklist

- Run tests after refactoring: `uv run pytest tests/ -v`
- Always update notebooks when changing function signatures
- Use `uv` for all code execution (never `pip` directly, never manually activate venv)
- Use `uv run` to execute scripts and commands, never bare `python` or shell activation
- **NEVER use `tail`, `head`, `grep`, or similar output filters** — show full output always so you can see everything that's happening
- See `TESTING.md` for detailed test setup

## Common Gotchas & Reminders

1. **Model naming quirk**: OpenAI and Groq use verbose naming, so default is `"openai/openai/gpt-oss-120b"`
2. **VPN blocks Groq API**: If tests/app fail with 403 errors, disconnect from VPN
3. **ChromaDB is ephemeral**: Using EphemeralClient means vectorstore rebuilds on each restart (stateless by design)
4. **Package manager**: Use `uv` exclusively for this project; don't use `pip` directly
