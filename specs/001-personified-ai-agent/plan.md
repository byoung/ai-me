# Implementation Plan: Personified AI Agent

**Branch**: `001-personified-ai-agent` | **Date**: 2025-10-23 | **Spec**: [spec.md](spec.md)  
**Gap Analysis**: [gap-analysis.md](gap-analysis.md)  
**Input**: Feature specification from `specs/001-personified-ai-agent/spec.md`

## Summary

The Personified AI Agent is a production-ready implementation (~85% spec compliant) that enables users to interact with an AI agent representing a real person's knowledge, experience, and philosophies. The agent retrieves information from a public GitHub repository of markdown documentation and responds in first-person perspective with accurate, sourced information.

**Current Implementation Status**: Core features working; enhancements needed for success metrics framework, LinkedIn integration (optional), and improved error handling.

**Recommended Action**: This specification formalizes existing implementation. Use it to:
1. Close gaps in success metrics measurement
2. Improve error handling and user experience
3. Add optional LinkedIn tool integration
4. Document and formalize conflict resolution logging

## Technical Context

**Language/Version**: Python 3.12+ (via `uv` package manager)  
**Primary Dependencies**: 
- OpenAI Agents SDK (agent orchestration, async patterns)
- LangChain (document loading, chunking, embeddings)
- ChromaDB (ephemeral vector storage)
- Gradio (chat UI framework)
- Pydantic (type-safe configuration)

**Storage**: 
- ChromaDB (in-memory, ephemeral - rebuilt on restart)
- Session-scoped memory files (MCP memory server)
- GitHub repository (markdown documentation source)

**Testing**: pytest-asyncio (function-scoped fixtures, async testing)  
**Target Platform**: Hugging Face Spaces (Gradio deployment), Linux/Docker  
**Project Type**: Web application (single project with backend API + frontend chat UI)  
**Performance Goals**: 
- <5 seconds response time (SC-005)
- 10+ concurrent users independently (SC-006)
- <100ms per vector search query

**Constraints**: 
- No hardcoded knowledge (RAG-first)
- No shared mutable state (per-session isolation)
- No blocking operations (async throughout)
- Temperature=1.0 default (natural responses); 0.0 for tests (determinism)

**Scale/Scope**: Single agent per deployment, supports unlimited concurrent sessions (Gradio session_hash keying)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Current Status | Compliance | Notes |
|-----------|----------------|-----------|-------|
| **I. Async-First** | ✅ Compliant | 100% | All I/O async; no blocking in hot path |
| **II. RAG-First** | ✅ Compliant | 100% | All responses from retrieved documents; no hardcoded knowledge |
| **III. Type-Safe Config** | ✅ Compliant | 100% | Pydantic BaseSettings; SecretStr for sensitive values |
| **IV. Session Isolation** | ✅ Compliant | 100% | Per-session agents; MCP servers isolated per session |
| **V. Test-First Development** | ⚠️ Partial | 70% | Working integration tests; missing success metrics validation |
| **VI. Strict Import Organization** | ✅ Compliant | 100% | PEP 8 followed; imports organized properly |
| **VII. Observability & Logging** | ✅ Compliant | 100% | Structured logging; session context on all logs; optional Loki |
| **VIII. Persona Consistency** | ✅ Compliant | 100% | First-person perspective; employer transparency explicit |
| **IX. Output Cleanliness** | ✅ Compliant | 100% | Unicode normalization applied to all responses |

**Gate Status**: ✅ **PASS** - All core principles met. V (testing) partially complete; gaps are measurement, not functionality.

## Project Structure

### Documentation (this feature)

```text
specs/001-personified-ai-agent/
├── spec.md              # Feature specification (finalized)
├── plan.md              # This file (implementation strategy)
├── gap-analysis.md      # Gap analysis: spec vs implementation
├── research.md          # [TODO] Phase 0: Research findings
├── data-model.md        # [TODO] Phase 1: Data model & entities
├── quickstart.md        # [TODO] Phase 1: Developer quickstart
├── contracts/           # [TODO] Phase 1: API contracts (OpenAPI)
│   └── agent-api.yaml
├── checklists/
│   └── requirements.md   # Quality checklist (finalized)
└── tasks.md             # [TODO] Phase 2: Task breakdown
```

### Source Code (repository root)

```text
ai-me/
├── src/
│   ├── __init__.py
│   ├── agent.py         # ✅ AIMeAgent class, MCP setup, RAG tool
│   ├── app.py           # ✅ Gradio UI, session management
│   ├── data.py          # ✅ Document loading, chunking, vectorstore
│   ├── config.py        # ✅ Pydantic configuration
│   ├── test.py          # ✅ Integration tests
│   ├── notebooks/
│   │   └── experiments.ipynb  # Development sandbox
│   └── static/
│       ├── style.css    # Custom Gradio styling
│       └── scroll.js    # UI scroll behavior
│
├── docs/                # ✅ Local markdown documentation (RAG source)
│   └── *.md            # Dynamically loaded based on config
│
├── test_data/          # ✅ Test fixtures
│   ├── projects.md
│   ├── team.md
│   └── README.md
│
├── .specify/           # ✅ Spec Kit configuration
│   ├── memory/
│   │   └── constitution.md    # Project principles
│   └── scripts/        # Spec Kit scripts
│
├── .github/
│   ├── copilot-instructions.md  # AI assistant guidance
│   └── prompts/        # Spec Kit prompts
│
├── pyproject.toml      # ✅ Project config (uv)
├── Dockerfile          # ✅ Docker build
├── docker-compose.yaml # ✅ Local development
├── README.md           # ✅ Project overview
├── TESTING.md          # ✅ Test setup guide
└── RETROFIT_COMPLETE.md # ✅ Retrofit documentation
```

**Structure Decision**: Single project with backend (Python) + frontend (Gradio). All code in `src/` with clear separation:
- `agent.py`: Agent orchestration and MCP server setup
- `app.py`: Chat UI and session lifecycle
- `data.py`: Document pipeline (load, chunk, embed, store)
- `config.py`: Type-safe configuration and logging
- `test.py`: Integration testing with async fixtures

## Gap Analysis Summary

From [gap-analysis.md](gap-analysis.md):

**Compliance**: ~85% ✅

**Fully Implemented**:
- ✅ Chat interface (FR-001)
- ✅ Knowledge base retrieval (FR-002, with admin-configurable GitHub repos)
- ✅ First-person persona (FR-003)
- ✅ Conversation history (FR-005)
- ✅ Knowledge gap handling (FR-006)
- ✅ Session isolation (FR-007)
- ✅ Output normalization (FR-008)
- ✅ Time & Memory tools (FR-009)
- ✅ GitHub tool conditional activation (FR-010)

**Partially Implemented** (working but needs enhancement):
- ⚠️ Source attribution (FR-004): Works but not measured
- ⚠️ Conflict logging (FR-011): Partial (no formal log)
- ⚠️ Tool failure handling (FR-012): Basic error handling, needs user-friendly messages
- ⚠️ Success metrics framework (SC-001-SC-008): we store user/agent interactions plus logging in Loki, but need queries to create a dashboard.

**Not Implemented**:
- ❌ LinkedIn tool (FR-010 optional): No implementation

## Phase 0: Research (TODO)

**Purpose**: Resolve technical unknowns identified in gap analysis.

**Research Tasks**:
1. **LinkedIn Tool Integration** (FR-010-LinkedIn)
   - Investigate LinkedIn MCP server availability
   - Document authentication requirements (API token, OAuth)
   - Estimate implementation effort
   
2. **Success Metrics Framework** (SC-001-SC-008)
   - Telemetry collection approach (logs, metrics, events)
   - Survey infrastructure for user perception (SC-001, SC-008)
   - Load testing framework for concurrency (SC-006)
   - Accuracy validation test suite design (SC-002)

3. **Conflict Detection & Logging** (FR-011)
   - Best practices for contradiction detection
   - Log schema design for conflict tracking
   - Human review workflow

**Deliverable**: `research.md` with decisions and rationale

## Phase 1: Design & Contracts (TODO)

**Purpose**: Formalize data models, APIs, and implementation contracts.

**Design Tasks**:

1. **Data Model** (`data-model.md`):
   - Formalize Key Entities from spec (PersonProfile, ConversationSession, Message, etc.)
   - Define relationships and validation rules
   - Model conflict tracking and user attributes

2. **API Contracts** (`contracts/`):
   - OpenAPI schema for agent endpoints (existing: chat, warmup, status)
   - Request/response models for tool calls
   - Error response formats

3. **Developer Quickstart** (`quickstart.md`):
   - How to run locally
   - How to configure documents (GitHub repos, local files)
   - How to configure tools (GitHub PAT, LinkedIn token)
   - How to run tests and measure success

4. **Agent Context Update** (Copilot context):
   - Run update-agent-context.sh to inject new technology decisions
   - Update context for future AI-assisted development

**Deliverables**: data-model.md, contracts/agent-api.yaml, quickstart.md

## Phase 2: Task Breakdown (TODO)

**Purpose**: Create actionable task list from design.

**Generated by**: `/speckit.tasks` command

**Expected Output**: `tasks.md` with prioritized, estimated tasks:
- Priority groupings (P0: blocking, P1: core, P2: nice-to-have)
- Effort estimates (t-shirt sizing: xs/s/m/l/xl)
- Dependencies between tasks
- Test criteria for each task

## Enhancement Roadmap

Based on gap analysis, recommended implementation order:

### Phase A: Measurement & Validation (High Priority)
1. **Success Metrics Framework**
   - ✅ Loki infrastructure ready (framework complete)
   - **TODO**: Create Loki queries for each SC criterion (SC-001 through SC-008)
   - Create dashboards to visualize metric trends
   - Design user survey for persona consistency and personalization (SC-001, SC-008)

2. **Improve Error Handling**
   - Add user-friendly error messages for tool failures (FR-012)
   - Implement retry logic for mandatory tools with exponential backoff
   - Test error paths with quality assertions

3. **Formalize Conflict Logging**
   - Detect conflicting document chunks (FR-011)
   - Create ConflictLog entity for recording
   - Structured JSON logging with session context
   - Dashboard or report view for human review

### Phase B: Optional Features (Medium Priority)
1. **LinkedIn Tool Integration** (if high value)
   - Research LinkedIn API or MCP server
   - Add conditional activation on token presence
   - Test with LinkedIn API keys

2. **Source Attribution Validation**
   - Add test assertions to verify attribution in responses
   - Create quality report on source documentation

### Phase C: Polish (Low Priority)
1. Admin UI for runtime document configuration
2. Telemetry dashboard for monitoring
3. User-facing feedback for success metric collection

---

## Complexity Tracking

> **Constitution Check passed without violations** - All core principles met

No complexity justifications needed. Implementation cleanly follows spec and constitution without additional complexity beyond original design.

---

## Key Implementation Notes

### 1. Document Configuration (FR-002 Clarification #1)
- Currently: Hardcoded local `docs/` directory + `config.github_repos` environment variable
- Future: Consider admin UI or API for runtime configuration
- Current approach sufficient and flexible for per-deployment customization

### 2. Tool Activation (FR-009-010 Clarification #2)
- **Always-on**: Time (no config), Memory (per-session, no config)
- **Conditional**: GitHub (if `GITHUB_PERSONAL_ACCESS_TOKEN` set), LinkedIn (if token set)
- **Status**: Implemented; LinkedIn tool not yet added

### 3. Conflict Resolution (FR-011 Clarification #3)
- Strategy: Vector search score prioritization
- Missing: Formal detection and logging
- Recommended: Add ConflictLog entity and structured logging

### 4. Tool Failure Handling (FR-012 Clarification #4)
- Strategy: Return user-friendly error; halt until recovery
- Current: Basic error handling exists
- Enhancement: Add retry logic for mandatory tools

### 5. Memory Scope (FR-013 Clarification #5)
- Strategy: Session-scoped user attributes (name, profession, interests, hobbies)
- Status: ✅ Implemented via MCP memory server with session-based file paths
- Privacy: Resets between sessions automatically

---

## Testing Strategy

**Existing** (`src/test.py`):
- Function-scoped fixtures (fresh agent per test)
- Temperature 0.0 for determinism
- Tests: RAG knowledge, MCP integration, error handling, quality
- Full integration (includes actual tool calls)

**Recommended Additions**:
- SC-002 accuracy validation (verify 100% factual sourcing)
- SC-005 latency monitoring (track response time)
- SC-006 load testing (10+ concurrent sessions)
- Tool failure error message quality
- Source attribution presence in responses
- Conflict detection and logging

---

## Success Criteria Alignment

| Spec | Current | Gap | Phase |
|------|---------|-----|-------|
| SC-001: 80% persona consistency (survey) | Loki framework ready | Create Loki query + survey | Phase A |
| SC-002: 100% factual accuracy | Loki framework ready | Create Loki query + validation test | Phase A |
| SC-003: 90% in-scope answers | Loki framework ready | Create Loki query + telemetry | Phase A |
| SC-004: 100% knowledge gap indication | Working + Loki ready | Create Loki query + verify | Phase A |
| SC-005: <5s response time | Loki framework ready | Create Loki query for latency analysis | Phase A |
| SC-006: 10+ concurrent users | Loki framework ready | Create Loki query for session count | Phase A |
| SC-007: Graceful tool error handling | Working + Loki ready | Create Loki query for error patterns | Phase A |
| SC-008: Memory personalization | Works + Loki ready | Create Loki query + survey | Phase A |

**Metrics Framework Status**: ✅ **Loki infrastructure complete**  
All logs are captured with session context. **Gap**: Need specific Loki queries for each SC criterion to enable metric dashboards.

---

## Recommended Next Steps

1. **Review this plan** with project stakeholders
2. **Run Phase 0 research** on LinkedIn integration and success metrics
3. **Create Phase 1 design artifacts** (data-model.md, contracts, quickstart)
4. **Run `/speckit.tasks`** to break Phase A into concrete tasks
5. **Execute Phase A tasks** to close measurement and error handling gaps
6. **Validate success criteria** with real users and telemetry

---

**Plan Status**: ✅ Ready for Phase 0 Research  
**Next Command**: `/speckit.tasks` (after Phase 0-1 complete) or `/speckit.implement` (if proceeding directly)
