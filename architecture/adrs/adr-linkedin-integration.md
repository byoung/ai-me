# ADR-001: Human-in-the-Loop Browser Automation for Third-Party Data Ingestion

**Status**: Accepted

**Date**: 2025-10-24

## Context

External services like LinkedIn do not provide sanctioned public APIs for personal profile data extraction. Previous research evaluated three integration approaches:
1. **Programmatic MCP/API integrations** — No official LinkedIn MCP server exists; third-party options are immature or unavailable
2. **Third-party data-gathering services** (Apify, Anysite) — Require sharing user credentials, violate Terms of Service, pose security and privacy risks
3. **Human-in-the-loop browser automation** — Respects ToS, maintains user control, verifies data accuracy and privacy before ingestion

## Decision

We will implement data ingestion for LinkedIn and other services without sanctioned public APIs exclusively through **human-in-the-loop browser automation** (Playwright). This approach:
- Requires the user to authenticate interactively (human provides credentials directly to LinkedIn, not to our tool)
- Extracts only publicly-visible profile content (profile, experience, education, skills, recommendations, connections, activity)
- Scope is limited to the user that manually logs in
- Mandates human review of all extracted content for accuracy and privacy compliance before ingestion into markdown documentation
- Explicitly prohibits use of third-party credential-sharing services that scrape on a user's behalf

This policy applies retroactively to LinkedIn and prospectively to any future external services lacking a publicly available API.

## Consequences

**Positive:**
- Maintains compliance with LinkedIn Terms of Service
- Protects user security (credentials never shared with third parties)
- Enables human verification of data accuracy and privacy
- Establishes reusable pattern for similar external data sources
- Respects user agency and control over their data

**Negative:**
- Requires user manual effort (browser interaction, file review)
- Tool development complexity (Playwright orchestration, markdown formatting)
- Cannot be fully automated or scheduled
- Slower than direct API access (if available)

## Compliance

This decision instantiates Constitution Principle X (External Data Integration Policy) and establishes binding guidance for all future data ingestion tools.
