# AI-Me Success Metrics & Measurement Framework

## Overview

This document defines the Loki queries and measurement methodology for the 8 success criteria (SC-001 through SC-008). Each query is designed to be run against Grafana Loki to measure real-world agent performance in production.

**Prerequisites**:
- Grafana Loki integration enabled in `src/config.py` (set `LOKI_ENABLED=true`)
- Application logging all operations with session context and structured JSON
- Deployment has been running for sufficient time to collect data

---

## SC-001: Persona Consistency

**Definition**: Agent maintains first-person perspective consistently across all responses.

**Loki Query**:
```loki
{job="ai-me"} | json | line_format "{{.message}}" 
| regex "(?i)(^|\s)(i\s|i'm|i've|i'll|my\s|me\s)" 
| stats count() by session_id
```

**Measurement**:
- ✅ **PASS**: >95% of responses from a single session use first-person pronouns
- ❌ **FAIL**: <90% of responses maintain first-person perspective

**Interpretation**:
- Count responses per session that contain first-person language
- Calculate percentage of total responses per session
- Aggregate across sessions; target is >95% average

---

## SC-002: Factual Accuracy via Source Attribution

**Definition**: 100% of substantive responses include source attribution to knowledge base documents.

**Loki Query**:
```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)(https://github\.com/|source:|per my|as mentioned in|according to)"
| stats count() as attributed_responses by session_id
| line_format "session_id={{.session_id}} attribution_rate={{.attributed_responses}}"
```

**Measurement**:
- ✅ **PASS**: ≥95% of substantive responses include source links/citations
- ❌ **FAIL**: <90% include attribution

**Interpretation**:
- Filter out "I don't have documentation" knowledge gap responses (those are meta, not factual claims)
- Count responses that cite sources (GitHub URLs, document names, etc.)
- Non-substantive responses (e.g., greetings) can be excluded from denominator

---

## SC-003: In-Scope Answers

**Definition**: Agent provides substantive answers to questions within documentation scope and acknowledges knowledge gaps for out-of-scope questions.

**Loki Query** (Part A - Substantive Responses):
```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "^.{50,}" 
| stats count() as substantive_count by session_id
```

**Loki Query** (Part B - Knowledge Gaps):
```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)(i don't have|no documentation|not familiar|i'm not sure|not in my documentation)"
| stats count() as gap_count by session_id
```

**Measurement**:
- ✅ **PASS**: ≥90% of responses are either substantive (>50 chars) OR acknowledge a knowledge gap
- ❌ **FAIL**: >10% of responses are evasive/empty

**Interpretation**:
- Substantive: responses >50 characters showing genuine knowledge
- Knowledge gaps: explicit acknowledgment of documentation limits
- Combined, these two categories should represent >90% of all responses

---

## SC-004: Knowledge Gap Handling

**Definition**: When documentation doesn't cover a topic, agent explicitly acknowledges this using consistent language patterns.

**Loki Query**:
```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)(i don't have|i'm not sure|i don't have any documentation|not familiar with|not covered in my documentation)"
| stats count() as gap_responses by session_id
```

**Measurement**:
- ✅ **PASS**: All knowledge gap responses use consistent language from the pattern above
- ❌ **FAIL**: Gap responses use inconsistent or unclear language

**Interpretation**:
- Consistency in knowledge gap messaging improves user experience
- Pattern represents established "graceful failure" language
- Count should increase over time as more knowledge gaps are encountered

---

## SC-005: Response Latency

**Definition**: 95% of responses complete within 5 seconds (SLA target).

**Loki Query**:
```loki
{job="ai-me"} | json 
| line_format "{{.latency_ms}}" 
| __error__="" 
| stats count() as total, count(latency_ms < 5000) as under_5s by session_id
```

**Measurement**:
- ✅ **PASS**: ≥95% of responses have latency < 5000ms
- ⚠️ **WARN**: 90-95% under 5s (acceptable but monitor)
- ❌ **FAIL**: <90% under 5s

**Interpretation**:
- Latency includes full round-trip: RAG retrieval + LLM inference + output
- Some variation expected due to document complexity and network
- Latency >5s may indicate vectorstore performance or LLM queue issues

---

## SC-006: Concurrent User Support

**Definition**: System supports ≥10 concurrent user sessions with consistent performance.

**Loki Query**:
```loki
{job="ai-me"} | json 
| stats count(distinct(session_id)) as concurrent_sessions
```

**Measurement**:
- ✅ **PASS**: Peak concurrent_sessions ≥10 with no degradation
- ⚠️ **WARN**: Peak 5-10 concurrent sessions, latency increases <20%
- ❌ **FAIL**: <5 concurrent sessions OR latency spikes >20% at peak

**Interpretation**:
- This query returns the number of unique session_ids in recent logs
- Run across a time window (e.g., last 1 hour) to find peak concurrency
- Compare latencies at low concurrency vs peak concurrency to measure degradation

---

## SC-007: Error Handling Quality

**Definition**: 100% of error messages are user-friendly with zero Python tracebacks exposed.

**Loki Query**:
```loki
{job="ai-me"} | json error_type!="" 
| line_format "{{.message}}" 
| regex "(?i)(traceback|File \".*\"|NameError|TypeError|ValueError|Traceback \(most)"
| stats count() as python_errors
```

**Measurement**:
- ✅ **PASS**: python_errors == 0 (no raw Python tracebacks in logs)
- ❌ **FAIL**: python_errors > 0

**Loki Query** (Alternative - Positive):
```loki
{job="ai-me", error_type="tool_failure"} | json 
| line_format "{{.message}}" 
| regex "(?i)(sorry|unfortunately|unable|can't|i'm not able|let me help|instead)" 
| stats count() as friendly_errors
```

**Measurement**:
- ✅ **PASS**: friendly_errors ≥95% of all error_type="tool_failure" logs
- ❌ **FAIL**: friendly_errors <90%

**Interpretation**:
- Errors are caught and formatted before reaching logs
- User-friendly errors use conversational language
- No Python internals leaked in any response

---

## SC-008: Session Isolation

**Definition**: Each session maintains independent state; no cross-session data leakage.

**Loki Query** (Verification - Count Unique Memory Files):
```loki
{job="ai-me"} | json session_id!="" 
| stats count(distinct(session_id)) as unique_sessions, 
        count(distinct(memory_file_path)) as unique_memory_files by timestamp("1h")
| line_format "{{.timestamp}} sessions={{.unique_sessions}} memory_files={{.unique_memory_files}}"
```

**Measurement**:
- ✅ **PASS**: unique_sessions == unique_memory_files (1:1 mapping)
- ❌ **FAIL**: unique_sessions != unique_memory_files (indicates sharing)

**Loki Query** (Unit Test - Concurrent Sessions):
```bash
# Run: pytest src/test.py::test_concurrent_sessions_do_not_interfere -v
# This test simulates 5+ concurrent queries and verifies:
# - Each session gets unique session_id
# - Memory operations don't leak between sessions
# - Session-scoped resources are isolated
```

**Measurement**:
- ✅ **PASS**: Test passes with 5+ concurrent queries completing without errors
- ❌ **FAIL**: Test fails or reports cross-session data access

**Interpretation**:
- Session isolation is partially verified by tests, partially by logs
- Unique memory file per session confirms isolation by design
- Cross-session memory leaks would show as matching memory_file_path for different session_ids

---

## Running These Queries

### In Grafana

1. Open **Grafana** → **Explore** → **Loki**
2. Copy one of the Loki queries from above
3. Adjust time range (e.g., "last 24 hours")
4. Click **Run Query**
5. Interpret results per the "Measurement" criteria

### Programmatically

```python
import requests
import json

LOKI_URL = "http://localhost:3100"

def query_loki(query: str, limit: int = 100) -> dict:
    """Execute a Loki query and return results."""
    url = f"{LOKI_URL}/loki/api/v1/query_range"
    params = {
        "query": query,
        "start": int(time.time()) - 86400,  # Last 24 hours
        "end": int(time.time()),
        "limit": limit,
    }
    resp = requests.get(url, params=params)
    return resp.json()

# Example
results = query_loki('{job="ai-me"} | json | stats count() by session_id')
print(json.dumps(results, indent=2))
```

---

## Dashboard Recommendation

Create a Grafana dashboard with these 8 panels:

| Panel | Query | Description |
|-------|-------|-------------|
| SC-001 | First-person regex | % responses maintaining persona |
| SC-002 | Source attribution regex | % responses with citations |
| SC-003 | Substantive + gaps | % in-scope or gap-acknowledged |
| SC-004 | Gap consistency | Consistency of gap messages |
| SC-005 | Latency histogram | Response time distribution |
| SC-006 | Concurrent sessions | Peak concurrent user count |
| SC-007 | Python error count | Raw traceback count (target: 0) |
| SC-008 | Session isolation | 1:1 session:memory_file ratio |

---

## Interpretation Guide

**Green (Healthy)**:
- SC-001: >95% first-person
- SC-002: ≥95% attributed
- SC-003: ≥90% substantive or gap-acknowledged
- SC-004: 100% gap responses consistent
- SC-005: ≥95% under 5 seconds
- SC-006: ≥10 concurrent sessions
- SC-007: 0 Python errors
- SC-008: 1:1 session:memory_file ratio

**Yellow (Degrading)**:
- SC-001: 90-95% first-person
- SC-002: 90-95% attributed
- SC-003: 85-90% substantive/gap
- SC-004: 95-100% gap consistency
- SC-005: 90-95% under 5s
- SC-006: 5-10 concurrent sessions
- SC-007: <1% Python errors
- SC-008: Occasional mismatches (acceptable)

**Red (Critical)**:
- SC-001: <90% first-person
- SC-002: <90% attributed
- SC-003: <85% substantive/gap
- SC-004: <95% gap consistency
- SC-005: <90% under 5s
- SC-006: <5 concurrent sessions
- SC-007: >1% Python errors
- SC-008: Widespread session cross-talk

---

## Notes

- Queries assume logs are structured JSON with fields: `session_id`, `message`, `latency_ms`, `error_type`, `memory_file_path`
- Timestamps in queries use UTC
- Thresholds are aspirational; adjust based on deployment context
- Some queries require manual adjustment (e.g., regex patterns for your specific error messages)
