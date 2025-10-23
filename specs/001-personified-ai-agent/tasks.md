# Task Breakdown: Personified AI Agent

**Feature**: Personified AI Agent  
**Branch**: `001-personified-ai-agent` | **Date**: 2025-10-23  
**Based On**: [spec.md](spec.md) | [plan.md](plan.md) | [gap-analysis.md](gap-analysis.md)

---

## Executive Summary

This document breaks down the Personified AI Agent specification into actionable, independently testable tasks organized by user story priority.

**Total Tasks**: 28  
**Phases**: 3 (Setup, Foundational, User Stories)

### MVP Scope (Recommended)
- **Phase 1**: Setup & infrastructure
- **Phase 2**: Foundational (document pipeline, agent core)
- **Phase 3**: User Story 1 (Core chat with expertise)

**Estimated MVP Timeline**: 1-2 weeks with full team  
**Full Scope Timeline**: 3-4 weeks including optional features

---

## Phase 1: Setup & Infrastructure

**Goal**: Establish project foundation, environment, and tooling.  
**Timeline**: 1-2 days  
**Acceptance**: All dependencies installed, test environment running

### Setup Tasks

- [x] T001 Verify Python 3.12+ environment and uv package manager installed
- [x] T002 Create `.env` file with required environment variables (OPENAI_API_KEY, GROQ_API_KEY, GITHUB_PERSONAL_ACCESS_TOKEN, BOT_FULL_NAME, etc.)
- [x] T003 Run `uv sync` to install project dependencies from pyproject.toml
- [x] T004 Verify pytest-asyncio testing framework is installed and functional
- [x] T005 Create test data fixtures directory with sample markdown files in `test_data/`
- [x] T006 [P] Configure logging (console + optional Loki) in `src/config.py`
- [x] T007 Verify git branch `001-personified-ai-agent` is active and ready

**Test Criteria**:
- ✅ `uv --version` shows valid version
- ✅ `.env` file exists with all required keys
- ✅ `uv run pytest src/test.py --collect-only` shows 7+ tests collected
- ✅ Logger output shows both console and (if configured) Loki handlers

---

## Phase 2: Foundational Components (Blocking Prerequisites)

**Goal**: Implement core infrastructure that all user stories depend on.  
**Timeline**: 3-5 days  
**Dependencies**: Phase 1 complete

### Document Pipeline (FR-002)

- [x] T008 [P] Create `DataManager` class in `src/data.py` to load markdown documents from local `docs/` directory
- [x] T009 [P] Implement intelligent two-stage document chunking: header-aware splitting + size-based fallback in `src/data.py`
- [x] T010 [P] Integrate HuggingFace sentence-transformers embeddings for document vectors in `src/data.py`
- [x] T011 [P] Create ephemeral ChromaDB vectorstore initialization in `src/data.py` with in-memory storage
- [x] T012 Implement GitHub repository loading in `src/data.py` using GitHub API (conditional on GITHUB_PERSONAL_ACCESS_TOKEN)
- [x] T013 Implement relative GitHub link rewriting (convert `/resume.md` → `https://github.com/owner/repo/blob/main/resume.md`) in `src/data.py`
- [x] T014 Create `process_documents()` function in `src/data.py` to orchestrate load → chunk → embed → store pipeline
- [x] T015 Add error handling for individual document failures in `src/data.py` (log and continue on load errors)

**Test Criteria**:
- ✅ `test_rear_knowledge_contains_it245()` passes (knowledge retrieval works)
- ✅ `test_github_relative_links_converted_to_absolute_urls()` passes (Test 7)
- ✅ Vector store has 5+ chunks for sample documents
- ✅ Embeddings dimensionality is 384 (sentence-transformers default)

### Configuration & Logging (FR-012, Constitution VII)

- [x] T016 Implement `Config` Pydantic BaseSettings in `src/config.py` with environment variable loading
- [x] T017 Add optional Grafana Loki integration to `src/config.py` for remote logging with session context
- [x] T018 [P] Create structured JSON logger in `src/config.py` that tags all logs with `session_id` and `application=ai-me`
- [x] T019 [P] Add Unicode normalization table for output cleanliness in `src/agent.py` (Constitution IX)

**Test Criteria**:
- ✅ Logger output contains `session_id` in all messages
- ✅ Loki handler configured when LOKI_URL + credentials present
- ✅ Unicode normalization converts special characters to ASCII

### MCP Server Setup (FR-009, FR-010)

- [x] T020 Implement `setup_mcp_servers()` method in `src/agent.py` to initialize Time and Memory tools
- [x] T021 Create `get_mcp_time_params()` function to return Time server parameters
- [x] T022 Create `get_mcp_memory_params(session_id)` function to return session-scoped Memory server parameters
- [x] T023 [P] Create `get_mcp_github_params()` function to return GitHub server parameters (conditional on GitHub PAT)
- [x] T024 Implement exception handling in `setup_mcp_servers()` for tool connection failures with session-scoped logging
- [x] T025 [P] Create error handler that returns user-friendly messages when MCP servers fail (FR-012)

**Test Criteria**:
- ✅ `test_tool_integration_github_mcp()` passes (GitHub tool works when PAT set)
- ✅ Time tool returns current date/time in responses
- ✅ Memory tool persists attributes within session (resets on new session)
- ✅ Tool failures return user-friendly error messages, not tracebacks

---

## Phase 3: User Story 1 - Chat with Personified Agent About Expertise (Priority: P1)

**Goal**: Implement core chat functionality with authentic persona and RAG.  
**Timeline**: 4-6 days  
**Dependencies**: Phase 2 complete  
**Independent Tests**:
- User can ask about person's expertise and get first-person responses
- Agent retrieves correct information from knowledge base
- Agent maintains authentic voice/persona throughout conversation

### RAG Tool & Agent Core (FR-002, FR-003, FR-004)

- [x] T026 [US1] Create `get_local_info_tool()` in `src/agent.py` that queries vectorstore for relevant documents
- [x] T027 [US1] Implement source attribution in RAG responses: format retrieved docs with links/references in `src/agent.py`
- [x] T028 [US1] Implement catch-all exception handler in `src/agent.py` that catches tool failures and returns user-friendly messages (FR-012)

### Agent Creation & Prompting (FR-003, Constitution VIII)

- [x] T029 [US1] Create `create_ai_me_agent()` method in `src/agent.py` with system prompt emphasizing first-person perspective and authentic voice
- [x] T030 [US1] Add error handling for agent initialization failures with session context logging
- [x] T031 [US1] Implement `run()` method in `src/agent.py` that executes agent with OpenAI Agents SDK and applies Unicode normalization (Constitution IX)

### Chat UI (FR-001, FR-005, FR-007)

- [x] T032 [US1] Create Gradio chat interface in `src/app.py` with message input and output display
- [x] T033 [US1] Implement session management in `src/app.py` using Gradio's `session_hash` for per-user isolation (FR-007)
- [x] T034 [US1] Create session-scoped agent instances dict in `src/app.py` keyed by session_id
- [x] T035 [US1] Implement conversation history storage in `src/app.py` within session (FR-005)
- [x] T036 [US1] Add error handling in chat endpoint to return friendly messages on failures (FR-012)

### Integration & Testing (US1 acceptance)

- [x] T037 [US1] Update `src/test.py` to add test for User Story 1: `test_user_story_1_chat_about_expertise()`
- [x] T038 [US1] [P] Add quality assertions to test: response in first-person, knowledge-grounded, authentic voice
- [x] T039 [US1] Manually verify: Open chat, ask "What is your experience with [topic]?", verify response is first-person and accurate

**Test Criteria** (User Story 1):
- ✅ `test_user_story_1_chat_about_expertise()` passes
- ✅ Chat interface responds to user input
- ✅ Responses use first-person perspective ("I built...", "My experience includes...")
- ✅ Responses cite sources from knowledge base
- ✅ Response time < 5 seconds (SC-005)

---

## Phase 4: User Story 2 - Interact Across Multiple Conversation Topics (Priority: P2)

**Goal**: Enable multi-topic conversations with consistent persona.  
**Timeline**: 2-3 days  
**Dependencies**: Phase 3 (User Story 1) complete  
**Independent Tests**:
- Agent maintains first-person perspective across multiple questions
- Agent shows topic awareness (different answers for different topics)
- Agent gracefully handles questions about undocumented topics

### Conversation Context (FR-005, FR-006)

- [x] T040 [US2] Enhance conversation history in `src/app.py` to include full message context per session
- [x] T041 [US2] Update agent prompt in `src/agent.py` to include conversation context for multi-turn awareness
- [x] T042 [US2] Implement graceful "knowledge gap" responses in agent prompt when documentation doesn't cover topic (FR-006)
- [x] T043 [US2] Add persona consistency assertions to agent prompt: maintain first-person, stay in character
- [x] T044 [US2] Create test `test_user_story_2_multi_topic_consistency()` that verifies consistent voice across 3+ questions on different topics
- [ ] T045 [US2] Manually verify: Ask 3+ questions on different topics, check that persona remains consistent

**Test Criteria** (User Story 2):
- ✅ `test_user_story_2_multi_topic_consistency()` passes
- ✅ All responses use consistent first-person perspective
- ✅ Knowledge gap questions return explicit "I don't have documentation on that" pattern
- ✅ Follow-up questions show conversation awareness

---

## Phase 5: User Story 3 - Access Sourced Information with Attribution (Priority: P2)

**Goal**: Implement and verify source attribution for all responses.  
**Timeline**: 2-3 days  
**Dependencies**: Phase 3 (User Story 1) + source attribution from T027 complete  
**Independent Tests**:
- Responses contain source references (document names, links)
- Multiple sources get appropriate attribution
- Source links are valid and functional

### Source Attribution (FR-004)

- [x] T046 [US3] Enhance `get_local_info_tool()` in `src/agent.py` to include relevance scores and source metadata in response
- [x] T047 [US3] Format source information as inline citations in `src/agent.py` (e.g., "Per my resume..." or "As mentioned in my projects documentation...")
- [x] T048 [US3] Convert relative GitHub links to absolute URLs in source citations (verify Test 7: T013 prerequisite)

### Source Quality & Testing (SC-002)

- [x] T049 [US3] Create test `test_user_story_3_source_attribution()` that verifies all responses contain source references
- [ ] T050 [US3] Add assertion: sourced information exists in knowledge base (SC-002: 100% factual accuracy)
- [ ] T051 [US3] Manually verify: Ask 3+ questions, check that responses cite specific sources

**Test Criteria** (User Story 3):
- ✅ `test_user_story_3_source_attribution()` passes
- ✅ All responses include source document names/links
- ✅ Source links are valid (200 status for GitHub links)
- ✅ No response contains information not in knowledge base

---

## Phase 6: Cross-Cutting Concerns & Success Metrics

**Goal**: Implement measurement, logging, and monitoring for success criteria.  
**Timeline**: 3-5 days  
**Dependencies**: User Story 1-3 complete

### Success Metrics Framework (SC-001-SC-008)

- [x] T052 [P] Create Loki queries documentation in `docs/SUCCESS_METRICS.md` for measuring each SC criterion
- [x] T053 [P] Document Loki query for SC-005 (response latency): query logs for `timestamp_diff < 5000`
- [x] T054 [P] Document Loki query for SC-006 (concurrent users): count unique `session_id` values
- [x] T055 [P] Document Loki query for SC-007 (error handling): find logs with "user-friendly message" pattern
- [x] T056 Document Loki query for SC-001 (persona consistency): find first-person language patterns
- [x] T057 Document Loki query for SC-002 (factual accuracy): find responses with source attribution
- [x] T058 Document Loki query for SC-003 (in-scope answers): classify responses as "substantive" vs "knowledge gap"
- [x] T059 Document Loki query for SC-004 (knowledge gap handling): verify "I don't have documentation" pattern

### Conflict Detection & Logging (FR-011)

- [x] T060 Create conflict detection documentation in `docs/CONFLICT_DETECTION.md` (already exists; verify it's current)
- [x] T061 Document Loki query for finding conflicts: `message =~ "(?i)(conflicting|contradict|not sure|unclear)"`
- [x] T062 Add agent prompt guidance on acknowledging conflicts when sources disagree

### Error Message Quality (FR-012)

- [x] T063 Create test `test_tool_failure_error_messages_are_friendly()` in `src/test.py`
- [x] T064 Add assertions: error messages contain no Python tracebacks, no stack traces, human-readable language
- [x] T065 Verify all tool failures (GitHub rate limit, MCP timeout, etc.) have friendly error handling

### Load Testing (SC-006)

- [x] T066 Document manual session isolation testing in `TESTING.md` (browser-based, not pytest)
- [x] T067 Verify: Manual testing with 3+ concurrent browser tabs shows independent sessions

**Test Criteria** (Cross-Cutting):
- ✅ All success metric Loki queries documented
- ✅ `test_tool_failure_error_messages_are_friendly()` passes
- ✅ `test_concurrent_sessions_do_not_interfere()` passes with 5+ concurrent agents
- ✅ `docs/SUCCESS_METRICS.md` and `docs/CONFLICT_DETECTION.md` exist and have runnable queries

---

## Phase 7: Polish & Enhancements (Optional / Phase B)

**Goal**: Optional features and quality improvements.  
**Timeline**: 1-2 weeks  
**Dependencies**: Core features (Phases 1-6) complete

### LinkedIn Tool Integration (FR-010 LinkedIn)

- [x] T068 [DEFERRED] Research LinkedIn MCP server availability or LinkedIn API
- [x] T069 [DEFERRED] Create `get_mcp_linkedin_params()` function (conditional on LINKEDIN_API_TOKEN)
- [x] T070 [DEFERRED] Add LinkedIn tool initialization to `setup_mcp_servers()` in `src/agent.py`
- [x] T071 [DEFERRED] Create separate feature spec for LinkedIn via `/speckit.specify` (defer to own spec)

### UI Polish

- [x] T072 [DEFERRED] Review custom Gradio styling in `src/static/style.css`
- [x] T073 [DEFERRED] Enhance scroll behavior in `src/static/scroll.js` for better UX
- [x] T074 [DEFERRED] Add admin configuration UI for runtime document management

### Documentation & Quickstart (Phase 1 design artifacts)

- [x] T075 [DEFERRED] Create `docs/quickstart.md` with setup instructions, environment config, testing
- [x] T076 [DEFERRED] Create `specs/001-personified-ai-agent/data-model.md` with entity relationships
- [x] T077 [DEFERRED] Create `specs/001-personified-ai-agent/contracts/agent-api.yaml` with OpenAPI schema

---

## Task Dependencies & Execution Graph

### Critical Path (Blocking Dependencies)

```
T001-T007 (Setup)
    ↓
T008-T025 (Foundational: Document pipeline + Config + MCP)
    ↓
T026-T039 (User Story 1: Chat + RAG + UI)
    ├→ T040-T045 (User Story 2: Multi-topic)
    └→ T046-T051 (User Story 3: Source Attribution)
        ↓
T052-T067 (Success Metrics & Load Testing)
        ↓
T068-T077 (Optional Enhancements)
```

### Parallelizable Tasks (Can Run Simultaneously)

**Phase 1**:
- T001, T002, T003, T004, T005, T007 (all independent)
- T006 (parallel with others)

**Phase 2**:
- T008, T009, T010, T011 (document loading - parallel)
- T016, T017 (config setup - parallel)
- T018, T019 (logging - parallel)
- T020, T021, T022 (MCP tool params - parallel)
- T023, T024, T025 (error handling - parallel)

**Phase 3**:
- T026, T027 (RAG tool - sequential within story)
- T029, T030, T031 (agent - sequential)
- T032, T033, T034, T035, T036 (UI - sequential)

**Phase 6**:
- T052-T059 (Loki query docs - parallel)
- T063, T064, T065 (error message tests - parallel)

---

## MVP Execution Path (Recommended)

### Week 1: Minimal Viable Product
1. **Phase 1** (Setup): T001-T007 — 1 day
2. **Phase 2** (Foundational): T008-T025 — 2-3 days
3. **Phase 3** (User Story 1): T026-T039 — 2 days

**Deliverable**: Functional chat interface with knowledge retrieval, first-person persona, session isolation

### Week 2: Complete Core Specification
4. **Phase 4** (User Story 2): T040-T045 — 1 day
5. **Phase 5** (User Story 3): T046-T051 — 1 day
6. **Phase 6** (Metrics): T052-T067 — 2 days

**Deliverable**: Full specification compliance + success metrics measurement + load testing

### Week 3+: Enhancements (Optional)
7. **Phase 7** (Polish): T068-T077 — 1-2 weeks

**Deliverable**: LinkedIn integration, UI polish, comprehensive documentation

---

## Quality Gates & Acceptance Criteria

### Before Merging to `main`

- [ ] All Phase 1-6 tests passing (`uv run pytest src/test.py -v`)
- [ ] All constitution principles still satisfied (re-check after implementation)
- [ ] Code follows PEP 8 style (imports organized, 98-char line limit)
- [ ] Notebooks synchronized with code changes (no function signature drift)
- [ ] Success metrics Loki queries documented and testable
- [ ] Error messages verified as user-friendly (T063, T064)
- [ ] Load testing passing (10+ concurrent sessions independent)

### Deployment Readiness (Hugging Face Spaces)

- [ ] Dockerfile builds successfully: `docker compose build`
- [ ] Environment variables documented: `.env` template created
- [ ] Performance targets met: <5 sec response time (SC-005)
- [ ] Rate limiting handled gracefully (GitHub API)
- [ ] Logging configured (console + optional Loki)

---

## Implementation Notes

### Key Technical Decisions

1. **ChromaDB Ephemeral Storage**: Rebuilt on restart. Stateless by design for Spaces deployment.
2. **MCP Servers Per-Session**: Time, Memory, GitHub all initialized per session for isolation.
3. **Temperature=0.0 for Tests, 1.0 Default**: Determinism in tests; natural responses in production.
4. **Loki for Observability**: All metrics extracted from logs; no separate telemetry system.
5. **GitHub URL Rewriting**: Relative links converted to absolute for proper attribution.

### Constitution Compliance

All tasks maintain compliance with project constitution:
- ✅ **I. Async-First**: All external I/O async (MCP setup, document loading)
- ✅ **II. RAG-First**: No hardcoded knowledge; all from retrieved documents
- ✅ **III. Type-Safe Config**: Pydantic BaseSettings + SecretStr
- ✅ **IV. Session Isolation**: Per-session agents + MCP servers
- ✅ **V. Test-First**: Each task includes test criteria
- ✅ **VI. Import Organization**: PEP 8 throughout
- ✅ **VII. Observability**: Structured logging + Loki integration
- ✅ **VIII. Persona Consistency**: First-person prompting maintained
- ✅ **IX. Output Cleanliness**: Unicode normalization applied

---

## Success Metrics (How We Know We're Done)

| Metric | Target | How We Measure |
|--------|--------|----------------|
| **Spec Compliance** | 100% | All FR, SC implemented or deferred |
| **Test Coverage** | 7+ tests passing | `uv run pytest src/test.py -v` |
| **Response Time** | <5 seconds | Loki query: SC-005 |
| **Concurrency** | 10+ independent sessions | Load test: T066 |
| **Error Handling** | 100% user-friendly | Error message test: T063 |
| **Source Attribution** | 100% of responses | Test 7 + T049 |
| **Persona Consistency** | First-person throughout | Manual review + T038 |
| **Knowledge Gap Handling** | 100% explicit indication | T044 + SC-004 verification |

---

## File Changes Summary

**New Files Created**:
- `src/agent.py` - AIMeAgent class, MCP setup, RAG tool, run method
- `src/app.py` - Gradio chat interface, session management
- `src/data.py` - Document pipeline, vectorstore setup
- `src/config.py` - Pydantic configuration, logging setup
- `src/test.py` - Integration tests (existing + enhancements)
- `docs/SUCCESS_METRICS.md` - Loki queries for SC-001-008
- `docs/CONFLICT_DETECTION.md` - Conflict detection design + queries

**Modified Files**:
- `src/notebooks/experiments.ipynb` - Development sandbox (keep in sync)
- `pyproject.toml` - Dependencies (already complete)

**Configuration Files**:
- `.env` - Environment variables (create from template)
- `Dockerfile` - Docker build (already exists)
- `docker-compose.yaml` - Local development (already exists)

---

**Plan Status**: ✅ Ready for execution  
**Recommended Start**: Phase 1 today; Phase 2-3 in parallel  
**Expected Completion**: 2-3 weeks for MVP + core specification

