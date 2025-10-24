# Feature Specification: LinkedIn Profile Data Extractor

**Feature Branch**: `002-linkedin-profile-extractor`  
**Created**: 2025-10-24  
**Status**: Draft (Clarification Complete)  
**Input**: User description: "A tool that walks through LinkedIn, allows users to login (human in the loop), then extracts user profile data (profile, experience, connections, etc.) into markdown files. Users can review files for accuracy/privacy and upload to their markdown repo for RAG ingestion."

## Clarifications

### Session 2025-10-24

- Q: Should this be a separate feature spec or integrated into spec 001? → A: Create separate spec (`specs/002-linkedin-profile-extractor/spec.md`) for clean separation of concerns
- Q: What authentication mechanism for LinkedIn? → A: Browser automation with Playwright for manual login; respects ToS, user-controlled
- Q: What LinkedIn data to extract? → A: Full profile (connections, endorsements, activity feed) with human review gate for privacy/legal before upload
- Q: What markdown output structure? → A: Hierarchical by section (Profile.md, Experience.md, Education.md, Skills.md, Recommendations.md, Connections.md, Activity.md)
- Q: How is tool delivered and integrated? → A: Standalone Python CLI tool; users run locally, review output, manually upload to GitHub repo

## Overview & Context

### Problem Statement

Users who want to create an AI agent representing themselves (via the Personified AI Agent, spec 001) need accurate, current profile data from LinkedIn. Currently, they must manually create markdown documentation of their professional background. This tool automates the extraction of LinkedIn profile data into markdown files, which users can review for accuracy and privacy, then upload to their documentation repository for RAG ingestion.

### Solution Overview

**LinkedIn Profile Data Extractor** is a standalone Python CLI tool that:
1. Opens a Playwright browser and navigates to LinkedIn
2. Requires manual user login (human-in-the-loop for authentication and consent)
3. Automatically navigates LinkedIn sections (Profile, Experience, Education, Skills, Recommendations, Connections, Activity)
4. Extracts structured data from each section
5. Converts data to hierarchical markdown files
6. Outputs files to a local directory for user review
7. User reviews files for accuracy and privacy, then manually uploads to their documentation repository

### Key Differentiators

- **Privacy-First**: Browser-based extraction respects LinkedIn ToS; human review gate ensures user control over what data is shared
- **No API Complexity**: Avoids LinkedIn API authentication, approval workflows, and data restrictions
- **User-Controlled**: Users decide what to include/exclude before uploading
- **Integrates with RAG**: Output markdown files are designed for ingestion by the Personified AI Agent
- **Standalone**: Separate tool; doesn't complicate main AI-Me application

### Target Users

- Individuals creating an AI agent representing themselves
- Users who want to keep profile data current with minimal manual effort
- Users who prefer reviewing data before sharing with AI systems

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract LinkedIn Profile to Markdown (Priority: P1)

A user runs the CLI tool, authenticates with LinkedIn, and extracts their profile data into markdown files. The tool creates organized, well-structured markdown files that accurately represent their LinkedIn profile.

**Why this priority**: Core value proposition—tool must successfully extract LinkedIn data without manual intervention after login.

**Independent Test**: Can be fully tested by running the tool, logging in, navigating profile extraction, and verifying output markdown files match LinkedIn source data.

**Acceptance Scenarios**:

1. **Given** a user runs `python -m linkedin_extractor extract --output-dir ./profile-data`, **When** the tool opens a browser and waits for login, **Then** the user can complete LinkedIn authentication manually
2. **Given** the user is logged into LinkedIn, **When** the tool navigates profile sections, **Then** it successfully extracts profile data without crashes or incomplete captures
3. **Given** extraction completes, **When** the tool outputs markdown files to the specified directory, **Then** files are well-formatted and match LinkedIn source content
4. **Given** output files exist, **When** the user reviews them, **Then** the data is accurate, complete, and useful for RAG ingestion

---

### User Story 2 - Review & Validate Extracted Data (Priority: P1)

User reviews the generated markdown files for accuracy and privacy concerns, ensuring the data is suitable for uploading to their documentation repository.

**Why this priority**: Human-in-the-loop validation ensures accuracy and prevents unintended data sharing.

**Independent Test**: Can be fully tested by reviewing output files and verifying they match LinkedIn source and contain no unexpected data.

**Acceptance Scenarios**:

1. **Given** markdown files are extracted, **When** the user reviews them, **Then** all sections are present and readable
2. **Given** the user finds inaccurate or sensitive data, **When** they can easily edit the markdown files, **Then** they can remove/modify entries before upload
3. **Given** files are validated, **When** the user prepares to upload, **Then** they understand exactly what data will be shared with their AI agent

---

### User Story 3 - Upload Reviewed Files to Documentation Repository (Priority: P2)

User uploads the reviewed and validated markdown files to their documentation repository (e.g., `byoung/me` GitHub repo), making them available for RAG ingestion by the Personified AI Agent.

**Why this priority**: Completes the workflow; enables RAG ingestion and agent knowledge base updates.

**Independent Test**: Can be fully tested by uploading files to a test repository and verifying they're accessible for RAG pipeline ingestion.

**Acceptance Scenarios**:

1. **Given** validated markdown files exist locally, **When** the user uploads them to their documentation repository, **Then** they're stored in a location where the RAG pipeline can find them
2. **Given** files are uploaded, **When** the Personified AI Agent's DataManager loads documents, **Then** the LinkedIn profile data is available for retrieval

---

### Edge Cases

- What happens if LinkedIn changes UI/layout while extraction is in progress?
- How does the tool handle LinkedIn rate limiting or blocking?
- What if a user has restricted privacy settings preventing certain data extraction?
- How should the tool handle missing data (e.g., user has no connections, endorsements, or activity)?
- What happens if the browser session times out during extraction?
- How are special characters, emojis, or non-ASCII text in profile data handled in markdown output?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tool MUST open a Playwright browser window and navigate to LinkedIn.com
- **FR-002**: Tool MUST require manual user login (human-in-the-loop authentication); tool waits for successful login before proceeding
- **FR-003**: Tool MUST extract data from LinkedIn profile section: name, headline, location, about/summary, profile photo URL, open to work status
- **FR-004**: Tool MUST extract data from LinkedIn experience section: job titles, companies, dates, descriptions, current/past employment status
- **FR-005**: Tool MUST extract data from LinkedIn education section: school names, degrees, fields of study, graduation dates, activities
- **FR-006**: Tool MUST extract data from LinkedIn skills section: skill names and endorsement counts
- **FR-007**: Tool MUST extract data from LinkedIn recommendations section: recommender names, titles, companies, recommendation text
- **FR-008**: Tool MUST extract data from LinkedIn connections section: connection names, titles, companies (publicly visible data only)
- **FR-009**: Tool MUST extract data from LinkedIn activity/posts section: recent posts, comments, articles (publicly visible content only)
- **FR-010**: Tool MUST convert extracted data into hierarchical markdown files per section (Profile.md, Experience.md, Education.md, Skills.md, Recommendations.md, Connections.md, Activity.md)
- **FR-011**: Tool MUST output markdown files to a user-specified directory (via CLI flag `--output-dir`)
- **FR-012**: Tool MUST handle extraction errors gracefully with user-friendly error messages
- **FR-013**: Tool MUST validate that extracted data matches source LinkedIn content (structural verification, no data loss)
- **FR-014**: Tool MUST include metadata in markdown files: extraction timestamp, source URL, data completeness notes
- **FR-015**: Tool MUST respect LinkedIn Terms of Service: browser-based extraction with manual login, human-in-the-loop consent
- **FR-016**: Tool MUST allow user review and manual editing of markdown files before upload
- **FR-017**: Tool MUST include documentation for uploading files to a GitHub repository for RAG ingestion

### Key Entities

- **LinkedInProfile**: Represents extracted user profile data (name, headline, location, summary, photo URL, open-to-work status)
- **LinkedInExperience**: Represents job history entries (company, title, dates, description, employment type)
- **LinkedInEducation**: Represents education entries (school, degree, field of study, graduation date, activities)
- **LinkedInSkill**: Represents skill entry (skill name, endorsement count)
- **LinkedInRecommendation**: Represents recommendation (recommender name/title/company, recommendation text, date)
- **LinkedInConnection**: Represents connection entry (name, title, company, connection URL)
- **LinkedInActivity**: Represents activity/post entry (timestamp, content, engagement metrics)
- **ExtractionSession**: Represents a single extraction run (session ID, timestamp start/end, browser state, error log)
- **MarkdownOutput**: Represents generated markdown file (section name, file path, content, metadata)

### Non-Functional Requirements

#### Performance (SC-005)

- **SC-P-001**: Profile extraction completes within 5 minutes (typical user with moderate activity/connections)
- **SC-P-002**: Markdown file generation completes within 10 seconds after extraction
- **SC-P-003**: Tool memory usage stays below 500MB during extraction

#### Reliability & Error Handling (SC-007)

- **SC-R-001**: Tool handles LinkedIn UI changes gracefully (element not found) with informative error messages
- **SC-R-002**: Tool handles rate limiting from LinkedIn (429 status) with retry logic and user notification
- **SC-R-003**: Tool handles network timeouts with automatic retry (up to 3 attempts) and clear error reporting
- **SC-R-004**: Tool handles incomplete data extraction (missing sections) and reports completeness in metadata
- **SC-R-005**: Browser session timeout is handled with user prompt to re-login

#### Security & Privacy (SC-002, SC-007)

- **SC-S-001**: Tool runs locally; LinkedIn credentials are never stored or transmitted to external services
- **SC-S-002**: Tool respects LinkedIn ToS: browser-based extraction, manual login, user consent required
- **SC-S-003**: Tool only extracts publicly visible data (respects privacy settings)
- **SC-S-004**: Markdown output is saved only to user-specified local directory (no automatic cloud upload)
- **SC-S-005**: Tool includes clear warnings about data sensitivity in generated markdown files

#### Usability (SC-008)

- **SC-U-001**: CLI interface is intuitive with clear help text (`--help` flag)
- **SC-U-002**: Error messages are user-friendly and actionable (not technical stack traces)
- **SC-U-003**: Output markdown files are human-readable and easy to edit before upload
- **SC-U-004**: Tool provides clear guidance on next steps (review, edit, upload to repo)

#### Observability

- **SC-O-001**: Tool logs extraction progress (sections processed, data counts, timestamps) to console
- **SC-O-002**: Tool generates extraction report in output directory (extraction_report.json) with metadata and summary

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Extracted LinkedIn data is accurate and matches source profile (100% sample verification by user review)
- **SC-002**: All publicly visible LinkedIn data is successfully extracted without requiring manual re-entry (100% completeness per user evaluation)
- **SC-003**: Generated markdown files are valid, well-formatted, and immediately usable for RAG ingestion (0 markdown syntax errors)
- **SC-004**: Users can review extracted data and identify/edit sensitive information before upload (human-in-the-loop gate functional)
- **SC-005**: Profile extraction completes in under 5 minutes for typical user (measured across 3+ user trials)
- **SC-006**: Tool handles LinkedIn UI changes and rate limiting without crashing (resilient error handling tested)
- **SC-007**: All tool failures result in user-friendly error messages, not technical stack traces (100% user-friendly errors)
- **SC-008**: Users report that generated files are immediately useful for their documentation repository (qualitative feedback)

### Assumptions

- Users have active LinkedIn accounts with visible profile data
- Users are comfortable installing Python CLI tool and running commands locally
- Users have git/GitHub account and can manually upload markdown files to their documentation repository
- LinkedIn UI is relatively stable (tool may require maintenance if LinkedIn significantly changes UI)
- Users accept that extraction is browser-based and requires active session (no headless-only extraction for privacy/ToS reasons)
- Generated markdown files will be reviewed by users before sharing with AI systems
- Users understand the data extracted is limited to publicly visible LinkedIn content

---

## Data Model

### Markdown Output Structure

Each extraction session generates the following files in the output directory:

```
output_dir/
├── extraction_report.json          # Metadata: extraction timestamp, session info, data completeness
├── Profile.md                      # Profile summary, headline, location, about, photo
├── Experience.md                   # Job history with dates, companies, descriptions
├── Education.md                    # Schools, degrees, fields of study, graduation dates
├── Skills.md                       # Skills list with endorsement counts
├── Recommendations.md              # Recommendations with recommender info and text
├── Connections.md                  # Connections list (names, titles, companies)
└── Activity.md                     # Recent posts, comments, articles
```

### File Format Example (Profile.md)

```markdown
# LinkedIn Profile

**Extracted**: 2025-10-24 14:30:00 UTC  
**Source**: https://www.linkedin.com/in/byoung/  
**Status**: Complete

## Summary

- **Name**: Ben Young
- **Headline**: AI Agent Architect | Full-Stack Engineer
- **Location**: San Francisco, CA
- **Open to Work**: Yes (seeking AI/ML roles)

## About

[Profile summary text...]

## Profile Photo

[URL to profile photo if publicly available]
```

---

## Technical Constraints & Architecture

### Technology Stack

- **Language**: Python 3.12+ (matching AI-Me project standards via `uv`)
- **Browser Automation**: Playwright (cross-platform, supports multiple browsers, respects ToS)
- **Package Manager**: `uv` (matches AI-Me project standards)
- **Output Format**: Markdown files + JSON metadata
- **Delivery**: Standalone CLI tool (separate from main Gradio app)
- **Execution Environment**: User's local machine (not cloud-deployed)

### Implementation Notes

1. **Browser-Based Extraction**: Uses Playwright to automate browser navigation, respecting LinkedIn ToS by requiring manual login
2. **No API Integration**: Avoids LinkedIn API authentication complexity and approval requirements
3. **Human-in-the-Loop**: User must manually authenticate and consent to extraction before proceeding
4. **Local Execution**: All extraction happens on user's machine; no credentials or data transmitted externally
5. **Manual Upload**: Users manually upload reviewed files to their GitHub repo (no automated Git push)
6. **RAG Integration**: Output markdown follows existing document structure for seamless RAG ingestion by Personified AI Agent

### Out of Scope

- Automated scheduled extraction (GitHub Actions, webhooks, cron jobs) — future enhancement
- Cloud-based execution or deployment
- Integration with main Gradio app (separate standalone tool)
- LinkedIn API integration (browser-based extraction only)
- Encrypted credential storage (user responsible for LinkedIn security)
- Multi-user or SaaS deployment

---

## Integration with Personified AI Agent (Spec 001)

### Workflow

1. **Extract**: User runs LinkedIn extractor CLI → generates markdown files
2. **Review**: User reviews files locally, edits for privacy/accuracy
3. **Upload**: User uploads files to their documentation repository (e.g., `byoung/me`)
4. **Ingest**: Personified AI Agent's `DataManager` loads files via GitHub (if `GITHUB_REPOS` includes the repo)
5. **Use**: Agent has access to LinkedIn profile data for better context and responses

### Documentation Structure Compatibility

LinkedIn extractor output (Profile.md, Experience.md, etc.) follows the same markdown document structure expected by the Personified AI Agent's RAG pipeline. No additional transformation needed.

---

## Deployment & Usage

### Installation

```bash
# Clone repo (or install from package)
git clone https://github.com/byoung/ai-me.git
cd ai-me

# Install dependencies
uv sync

# Run extractor
python -m linkedin_extractor extract --output-dir ./linkedin-profile
```

### CLI Interface

```bash
python -m linkedin_extractor extract --output-dir PATH [OPTIONS]

Options:
  --output-dir PATH              Directory to save markdown files (required)
  --headless                     Run browser in headless mode (not recommended; requires session)
  --wait-time SECONDS            Wait time for page loads (default: 10)
  --extract-connections          Include full connections list (slower; may hit rate limits)
  --extract-activity             Include recent activity/posts (slower; requires scrolling)
  --help                         Show help text
```

### Usage Example

```bash
# Basic extraction
python -m linkedin_extractor extract --output-dir ~/linkedin-profile

# Full extraction with connections and activity
python -m linkedin_extractor extract --output-dir ~/linkedin-profile --extract-connections --extract-activity
```

### Post-Extraction Workflow

1. **Review Files**: User opens markdown files in editor, verifies accuracy
2. **Edit**: User removes/modifies sensitive information as needed
3. **Upload to Repo**: User commits and pushes files to their documentation repository
4. **Configure AI-Me**: Add repo to `GITHUB_REPOS` environment variable if not already included
5. **Verify**: Next conversation with AI-Me agent will use LinkedIn profile data in responses

---

## Testing Strategy

### Unit Tests

- Markdown generation (correct format, no syntax errors)
- Data extraction parsing (LinkedIn HTML → structured data)
- File I/O operations (output directory creation, file writing)
- Error message formatting (user-friendly, no stack traces)

### Integration Tests

- End-to-end extraction session (login → extract → file output)
- Handle LinkedIn rate limiting
- Handle LinkedIn UI changes (missing elements)
- Browser timeout recovery

### Manual Testing

- User trial with real LinkedIn account (verify data accuracy)
- Review generated markdown files for completeness
- Upload to documentation repo and verify RAG ingestion

---

## Success Metrics (How We Know We're Done)

| Metric | Target | How We Measure |
|--------|--------|----------------|
| **Data Accuracy** | 100% of extracted data matches LinkedIn source | User review of generated files vs. LinkedIn profile |
| **Completeness** | 90%+ of available LinkedIn data extracted | Count of extracted data points vs. completeness report |
| **Markdown Quality** | 0 syntax errors in output | Markdown validation tool |
| **Extraction Time** | <5 minutes for typical user | Timer from login to file output |
| **Error Handling** | 100% user-friendly error messages | No stack traces in output |
| **Privacy Compliance** | Only publicly visible data extracted | User audit of generated files |
| **RAG Integration** | Files immediately usable for RAG ingestion | Upload to repo and verify agent knowledge access |
| **Ease of Use** | Users can extract data without technical support | Qualitative feedback / support ticket volume |

---

## Future Enhancements (Phase B - Not in MVP)

- Scheduled extraction (GitHub Actions trigger)
- Multi-profile extraction (extract multiple users' data)
- Incremental updates (extract only changed sections)
- LinkedIn API integration (once ToS allows)
- Cloud deployment (Hugging Face Spaces as web UI)
- Automated Git push with review/approval workflow
- Encrypted credential storage for batch jobs
- Data diff/versioning (track profile changes over time)

---

**Spec Status**: ✅ Ready for Phase 0-1 Design  
**Next Steps**: 
1. Create detailed data model and markdown schema
2. Create implementation plan with Playwright-specific architecture
3. Generate task breakdown for development

