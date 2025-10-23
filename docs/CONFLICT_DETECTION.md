# Conflict Detection & Resolution Framework

## Overview

This document describes the design and implementation of conflict detection in the AI-Me agent, specifically for FR-011 (Multi-Source Conflict Resolution). When the agent retrieves information from multiple sources that contradict each other, it must:

1. **Detect** semantic conflicts (contradictions, ambiguities)
2. **Log** the conflict with full context for auditing
3. **Acknowledge** the conflict to the user
4. **Resolve** by presenting both perspectives or indicating uncertainty

---

## What Constitutes a Conflict?

A **conflict** occurs when:

### Type 1: Direct Contradiction
Two retrieved documents state opposite facts about the same subject.

**Example**:
- Document A: "I worked at Company X for 5 years"
- Document B: "I worked at Company X for 3 years"

### Type 2: Ambiguous/Unclear Information
Retrieved information is vague or contradicts the user's expectations.

**Example**:
- User asks: "How many years of Python experience do you have?"
- Retrieved docs mention: "Python" and "10 years" but the connection isn't explicit

### Type 3: Incomplete Coverage
Multiple documents cover the same topic incompletely, requiring disambiguation.

**Example**:
- Document A: "Worked on backend APIs"
- Document B: "Worked on deployment infrastructure"
- User asks: "What tech stack have you worked with?" (requires synthesizing both)

---

## Detection Strategy

### Level 1: Semantic Detection (LLM-Based)

The agent uses its instruction prompt to identify conflicts. The prompt includes guidelines on conflict handling.

### Level 2: Pattern Matching (Regex-Based)

Loki queries identify responses containing conflict indicators:

```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)(conflicting|contradict|not sure|unclear|conflicting information|different sources suggest|one source says|another source says|both|however|but|though)"
```

### Level 3: Structured Logging

All conflict incidents are logged with:
- Session ID
- User query
- Retrieved documents with sources
- Identified conflict type
- Agent's resolution approach
- User satisfaction (if collected via follow-up)

---

## Loki Queries for Conflict Monitoring

### Query 1: Find All Conflict Indicators

```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)(conflicting|contradict|not sure|unclear)"
| stats count() by session_id
```

**Measurement**:
- Expected: Conflicts relatively rare (unless knowledge base is contradictory)
- Investigation trigger: >10% of conversations contain conflict indicators

### Query 2: Find Unresolved Conflicts

```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)(conflicting.*unknown|contradict.*not sure|unclear.*can.?t.*determine)"
| stats count() as unresolved_conflicts
```

**Measurement**:
- Goal: Minimize unresolved conflicts (acknowledge but present both sides)
- Alert if: unresolved_conflicts > 0 (indicates poor conflict handling)

### Query 3: Conflict Resolution Pattern

```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)((according to|per my|source.*says).*but.*(according to|per my|source.*says))"
| stats count() as pairwise_conflicts
```

**Measurement**:
- Good pattern: Shows agent is presenting both sides with attribution
- Target: ≥80% of detected conflicts include pairwise attribution

### Query 4: Source Attribution in Conflict Context

```loki
{job="ai-me"} | json 
| line_format "{{.message}}" 
| regex "(?i)conflicting" 
| regex "https://github.com/" 
| stats count() as attributed_conflicts
```

**Measurement**:
- Goal: 100% of conflicts include source citations
- Alert if: attributed_conflicts < (total conflicts * 0.95)

---

## Conflict Resolution Flowchart

```
User asks question
        ↓
Agent calls get_local_info_tool()
        ↓
Multiple documents retrieved
        ↓
    Are they conflicting?
        ↓
    YES ──→ DETECT CONFLICT
        ↓   - What's the contradiction?
        ↓   - Why might it exist?
        ↓
        ├─→ Direct contradiction (different facts)
        │   └─→ Cite both sources, indicate uncertainty, choose most likely
        │
        ├─→ Ambiguous (unclear connection)
        │   └─→ Acknowledge ambiguity, provide context
        │
        └─→ Incomplete (multiple partial truths)
            └─→ Synthesize both perspectives
        ↓
    ACKNOWLEDGE to user
        ├─→ "I found conflicting information..."
        ├─→ Cite both sources with URLs
        └─→ Explain discrepancy or ask for clarification
        ↓
    RESPOND to user
        └─→ Include full source attribution
        
    NO ──→ RESPOND normally
            ├─→ Include source citations
            └─→ Single clear answer
```

---

## Finding Conflicts: Loki Queries

### Query to Find Reported Conflicts

```loki
{job="ai-me"} 
| json 
| message =~ "(?i)(conflicting|contradict|not sure|unclear|uncertain|conflicting information)" 
| session_id != ""
| line_format "{{.timestamp}} [{{.session_id}}] {{.message}}"
```

**How to use** (in Grafana Loki):
1. Open Grafana instance configured with Loki
2. Go to Explore → Loki
3. Copy the query above into the query field
4. Adjust regex pattern to match your conflict keywords
5. Filter results by date range or session ID
6. Results show all sessions where agent reported uncertainty

### Alternative: Find Specific Topics

```loki
{job="ai-me"} 
| json 
| message =~ "(?i)(Python.*(?:conflicting|contradict|not sure|unclear))" 
| session_id != ""
```

### Alternative: Analyze by Session

```loki
{job="ai-me"} 
| json 
| message =~ "(?i)(conflicting|contradict|not sure|unclear)" 
| stats count() by session_id
```

---

## Integration Points

### Agent System Prompt

The agent prompt (in `src/agent.py`) includes guidance on uncertainty and conflict acknowledgment.

### Logging Configuration

Loki integration configured in `src/config.py`:

```python
# Environment variables (optional Loki setup):
LOKI_URL=https://logs-prod-us-central1.grafana.net
LOKI_USERNAME=<grafana-cloud-username>
LOKI_PASSWORD=<grafana-cloud-api-key>
```

All logs automatically tagged with:
- `application: "ai-me"`
- `session_id: "<user-session-id>"`
- `level: "INFO|WARNING|ERROR"`

### Session Metadata

Each session log includes:
- `session_id`: Unique user session identifier
- `timestamp`: ISO 8601 datetime
- `message`: Full agent response or interaction
- `hostname`: Where the agent ran
- `process_id`: Python process ID

---

## Human Review Workflow

### Steps to Review Conflicts

1. **Run Loki query** (see above) during specified date range
2. **Identify sessions** with potential conflicts
3. **Examine responses** in full context:
   - What was the user question?
   - What conflicting sources were presented?
   - How did agent acknowledge uncertainty?
4. **Validate or correct** documentation:
   - Is one source outdated? Update it.
   - Is the conflict real but unresolved? Note in docs.
   - Is the agent confused? Improve documentation clarity.

---

## Metrics & Monitoring

### Metrics to Track

```python
# Useful queries for monitoring
queries = {
    "conflicts_per_week": (
        '{job="ai-me"} | json | message =~ "(?i)(conflicting|not sure)" '
        '| stats count() by week'
    ),
    "high_conflict_topics": (
        '{job="ai-me"} | json | message =~ "(?i)(conflicting|not sure)" '
        '| stats count() by message | sort by count desc | limit 10'
    ),
    "conflict_free_sessions": (
        '{job="ai-me"} | json | session_id != "" '
        '| count()'
    ),
}
```

### What These Mean

- **conflicts_per_week**: Trend - are conflicts increasing? Decreasing?
- **high_conflict_topics**: Which topics need documentation cleanup?
- **conflict_free_sessions**: What % of sessions have no conflicts?

---

## Future Enhancements

1. **Automated conflict detection**: Add explicit contradiction detection in RAG tool
2. **Conflict metrics**: Track "conflict rate" as success criterion
3. **Conflict resolution workflow**: UI for humans to resolve conflicts
4. **Documentation versioning**: Track which doc version caused the conflict
5. **Semantic deduplication**: Detect conceptual duplicates in knowledge base

---

## Related Files

- `src/agent.py`: System prompt with conflict guidance
- `src/config.py`: Loki logging configuration (optional setup)
- `.github/copilot-instructions.md`: RAG principles
- `.specify/memory/constitution.md`: Observability principle (VII)

---

**Status**: ✅ Implemented via pragmatic LLM-based approach  
**Verification**: Run Loki queries to monitor conflicts  
**Next Review**: Monthly analysis of conflict queries to identify documentation gaps
