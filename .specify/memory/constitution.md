# AI-Me Constitution

A personified AI agent application that creates agentic versions of real people using RAG (Retrieval Augmented Generation) over markdown documentation, deployed as a Gradio chatbot on Hugging Face Spaces.

## Core Principles

### I. Async-First Architecture

All agent operations and external I/O must be async-native. No blocking operations in the hot path. This ensures responsive UI and scalable deployments on cloud platforms.
- Agent execution flows are asynchronous end-to-end
- External services (MCP servers, vectorstore, APIs) initialized asynchronously
- Session-scoped agent instances prevent cross-session state contamination

### II. RAG-First Data Pipeline

All intelligence derives from document retrieval, not training data or hardcoded knowledge. This ensures accuracy, verifiability, and the ability to update agent knowledge by updating documents.
- Documents sourced from local and remote sources (GitHub repos)
- Intelligent chunking preserves document structure for better retrieval
- Retrieved documents provide context and source attribution for all responses

### III. Type-Safe Configuration with Pydantic

All configuration validated via Pydantic with strict typing. No string-based config, no runtime surprises, no silent failures.
- Centralized configuration management with defaults
- Secrets handled securely with restricted access
- Immutable config pattern prevents accidental mutations of shared state

### IV. Session Isolation & Resource Management

Each user session gets its own agent instance with isolated resources. Explicit resource cleanup prevents leaks and shutdown errors.
- Per-session agent instances keyed by unique session identifier
- Session-specific resources (memory, temp files) isolated and cleaned up
- Explicit cleanup lifecycle prevents resource contention

### V. Test Driven Development (NON-NEGOTIABLE)

All features validated by tests before integration. Code without tests is code without specifications.
- Tests validate all agent behavior changes and refactorings
- Test data isolated from production configuration
- Tests should isolate all external dependencies. NOTE: Inference can not be isolated until we can run larger models like gpt-oss-120b on commodity hardware.

### VI. Clear Code Organization

Code is organized and readable. Imports follow a consistent structure. Lines are concise without sacrificing clarity.
- Imports organized top-of-file: standard library → third-party → local
- Each import group separated by blank line
- Code formatted for readability and maintainability

### VII. Observability First

All operations observable through structured logging. Logs provide context for debugging and auditing.
- Operations logged with session context and structured data
- Retrieval and tool execution visible in logs for debugging
- Optional integration with centralized logging for production insights

### VIII. Persona Consistency

The agent represents a real person with clear identity. All responses maintain first-person perspective and relationship transparency.
- Agent refers to self by name and maintains consistent identity
- Professional relationships clearly indicated
- Tone is personable, friendly, and authentic

### IX. Unicode Normalization & Output Cleanliness

All agent responses normalized for clean, consistent output across platforms.
- Special characters normalized to ASCII equivalents
- Output cleaned before returning to user
- Output links should work

### X. External Data Integration Policy

For external services that do not provide a sanctioned public API (for example: LinkedIn), AI‑Me will perform data ingestion only via a human-in-the-loop browser automation process that requires interactive user authentication. Extracted content must be limited to publicly-visible information, reviewed by the human operator for accuracy and privacy before ingestion, and must never be collected via third-party services that require users to share credentials or that perform scraping on a user's behalf.

### XI. Full Requirements Traceability

All software must maintain complete traceability between requirements, implementation, and tests. No gaps are permitted in the traceability matrix.
- **Every requirement** must map to one or more implementation/design blocks in code (via docstrings linking requirement IDs)
- **Every implementation block** must belong to at least one requirement (no code without a requirement)
- **Every test** must validate one or more requirements (no tests without requirement linkage)
- Requirements assigned unique identifiers (e.g., `REQ-001`, `FR-001`, `NFR-001`) in all specification documents
- Implementation functions/methods document their requirement IDs in docstrings (e.g., `"""Implements REQ-001: ..."""`)
- Test functions document which requirements they validate in docstrings (e.g., `"""Tests REQ-001: ..."""`)
- Validation tooling should spot-check traceability; maintainers verify before code review
- This ensures: (a) no implemented features lack requirements, (b) no requirements go unimplemented, (c) all features are tested, (d) the system behaves exactly as specified—nothing more, nothing less

## Technology Stack Constraints

- **Python**: 3.12+ only (via `requires-python = "~=3.12.0"`)
- **Package Manager**: `uv` exclusively (not pip)
- **LLM Provider**: Groq `openai/openai/gpt-oss-120b` (primary), OpenAI API (tracing only)
- **VectorDB**: ChromaDB ephemeral (in-memory, no persistence)
- **Embeddings**: HuggingFace sentence-transformers
- **Framework**: OpenAI Agents SDK with async support
- **UI**: Gradio with Hugging Face Spaces deployment
- **MCP Servers**: GitHub, Time, Memory (optional per session)

## Development Workflow

1. **Environment Setup**:
   - Create `.env` with required keys: `OPENAI_API_KEY`, `GROQ_API_KEY`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `BOT_FULL_NAME`, `APP_NAME`, `GITHUB_REPOS`
   - Run `uv sync` to install dependencies
   - Setup pre-commit hook to auto-clear notebook outputs

2. **Local Development**:
   - Use `docs/` directory for markdown (won't deploy unless pushed to GitHub repo)
   - Test locally: `uv run src/app.py` (Gradio on port 7860)
   - Run tests: `uv run pytest src/test.py -v`
   - Edit notebooks then validate changes don't break tests

3. **Docker/Notebook Development**:
   - Build: `docker compose build notebooks`
   - Run: `docker compose up notebooks`
   - Attach via Dev Containers extension for IDE integration

4. **Deployment**:
   - Push to `main` triggers GitHub Actions CI/CD
   - CI runs tests with `GROQ_API_KEY` and `OPENAI_API_KEY`
   - CD deploys to Hugging Face Spaces via Gradio CLI with all required env vars

## Code Organization

- `src/config.py` - Pydantic BaseSettings, all configuration
- `src/data.py` - DataManager class, complete document pipeline
- `src/agent.py` - AIMeAgent class, MCP setup, agent creation
- `src/app.py` - Gradio interface, session management
- `src/test.py` - Integration tests with pytest-asyncio
- `src/notebooks/experiments.ipynb` - Development sandbox (test all APIs here first)
- `docs/` - Local markdown for RAG development
- `test_data/` - Test fixtures and sample data
- `.github/copilot-instructions.md` - Detailed AI assistant guidance
- `.specify/` - Spec-Driven Development templates and memory

## Non-Negotiables

1. **No hardcoded knowledge** - Everything comes from RAG
2. **No shared mutable state** - Session-scoped instances only
3. **No blocking operations** - Async throughout
4. **No untested refactorings** - Run tests first
5. **No outdated notebooks** - Sync with code changes
6. **No unstructured logs** - JSON for machines, readable for humans
7. **No credential leaks** - .gitignore and .dockerignore files to help prevent secret slips. Never build secrets into a dockerfile!
8. **No notebook outputs in GIT** - you must clean up the code
9. **No traceability gaps** - Every requirement, implementation, and test must be linked and documented
10. **No unspecified code** - Every function must serve at least one requirement

## Architectural Decision Records (ADRs)

All major architectural decisions are documented in `architecture/adrs/`. ADRs provide detailed context, tradeoffs, and compliance notes that elaborate on constitution principles:

- **ADR-001**: Human-in-the-loop Browser Automation for Third-Party Data Ingestion — Instantiates Principle X (External Data Integration Policy)

Reference ADRs when evaluating PRs, designing new integrations, or proposing architecture changes.

## Governance

This constitution supersedes all other practices and is the single source of truth for architectural decisions. All PRs and feature requests must verify compliance with these principles. Code review must check:
- Async-first patterns are used
- Type safety via Pydantic validation
- Session isolation maintained
- Tests pass and notebooks updated
- Imports organized per PEP 8
- Observability (logging) present
- Output cleanliness (Unicode normalization)
- External data integration policy adherence
- Architectural decisions documented in `architecture/adrs/`
- Requirements traceability matrix is complete (every requirement has implementation + tests)

**Version**: 1.1.0 | **Ratified**: 2025-10-23 | **Last Amended**: 2025-10-24
