# Integration Guide: LinkedIn Profile Extractor ↔ Personified AI Agent

**Document**: Integration roadmap between Spec 002 (LinkedIn Extractor) and Spec 001 (Personified AI Agent)  
**Date**: October 24, 2025  
**Status**: Reference Documentation

---

## High-Level Workflow

```
User's LinkedIn Profile
        ↓
 [Spec 002: LinkedIn Profile Extractor Tool]
   (Playwright browser automation + manual login)
        ↓
 Generated Markdown Files (Profile.md, Experience.md, etc.)
        ↓
 User Review & Edit (privacy/accuracy gate)
        ↓
 Manual Upload to GitHub Repository (byoung/me, etc.)
        ↓
 [Spec 001: Personified AI Agent]
   (DataManager loads GitHub repo via RAG)
        ↓
 Agent Knowledge Base Enhanced
        ↓
 User Chat: "Tell me about your experience..."
 Agent Response: [Sourced from LinkedIn profile markdown]
```

---

## Data Flow

### Spec 002 Output Format

LinkedIn Extractor produces:

```
linkedin-profile/
├── extraction_report.json
├── Profile.md               # Name, headline, location, about
├── Experience.md            # Job history
├── Education.md             # Schools, degrees
├── Skills.md                # Skills + endorsements
├── Recommendations.md       # Recommendations
├── Connections.md           # Connections list
└── Activity.md              # Posts, articles
```

### Spec 001 Input Format

Personified AI Agent expects:

- Markdown files in `docs/` directory (local) or GitHub repository (remote)
- Files organized by topic/section (exactly what Spec 002 produces)
- Metadata: filename, creation date, source (included in extraction_report.json)
- Markdown syntax: valid UTF-8, proper heading hierarchy

**Result**: Perfect format compatibility. No transformation needed.

---

## Integration Steps

### Step 1: Extract LinkedIn Data (Spec 002)

```bash
cd ~/projects/ai-me
python -m linkedin_extractor extract --output-dir ./linkedin-profile
# User logs in manually → files generated → review files
```

**Output**: 7 markdown files + extraction_report.json in `./linkedin-profile/`

---

### Step 2: Review & Validate

User reviews files locally, edits for privacy/accuracy:

```bash
# Open in editor
code ./linkedin-profile/

# Edit files as needed, delete sensitive info, verify accuracy
# Example edits:
# - Remove specific company names if desired
# - Condense connections list to key contacts
# - Remove draft posts or old activity
```

---

### Step 3: Upload to Documentation Repository

User uploads files to their documentation repo (e.g., `byoung/me`):

```bash
cd ~/repos/byoung-me  # (or wherever your docs repo is)

# Copy or move reviewed files
cp -r ~/projects/ai-me/linkedin-profile/*.md ./

# Commit and push
git add *.md
git commit -m "Update LinkedIn profile: $(date +%Y-%m-%d)"
git push origin main
```

---

### Step 4: Configure AI-Me to Ingest

Update `.env` to include LinkedIn profile repo:

```bash
# .env
GITHUB_REPOS=byoung/me,byoung/other-docs  # Add your repo
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx
```

Or, if files are already in local `docs/` directory:

```bash
# Just move files to docs/
cp ~/linkedin-profile/*.md ./docs/
```

---

### Step 5: Restart AI-Me

AI-Me's `DataManager` will reload documents on next startup:

```bash
# If running locally:
python -m gradio src/app.py

# If deployed on Spaces, trigger redeploy or restart
```

---

### Step 6: Verify Integration

Test that agent has access to LinkedIn profile data:

**Test Chat**:
- User: "Tell me about your work experience"
- Agent Response: [Cites Experience.md from LinkedIn extractor]

**Verification**:
- Agent uses first-person ("I worked at...")
- Agent cites specific companies/dates from LinkedIn profile
- Agent maintains authentic voice

---

## Data Mapping: LinkedIn → Markdown → Agent

| LinkedIn Source | Markdown File | Agent Uses For | Example Question |
|-----------------|---------------|----------------|------------------|
| Profile section | Profile.md | Personalization, headline context | "What's your professional background?" |
| Experience | Experience.md | Job history, expertise domains | "Tell me about your experience with X" |
| Education | Education.md | Academic background, credentials | "Where did you study?" |
| Skills + Endorsements | Skills.md | Domain expertise ranking | "What are your top skills?" |
| Recommendations | Recommendations.md | Social proof, validation | "What do others say about you?" |
| Connections | Connections.md | Network context, collaboration history | "Tell me about your network" |
| Activity/Posts | Activity.md | Recent thinking, current interests | "What are you focused on lately?" |

---

## File Format Examples

### Profile.md (from Spec 002 → consumed by Spec 001)

```markdown
# LinkedIn Profile

**Name**: Ben Young  
**Headline**: AI Agent Architect | Full-Stack Engineer  
**Location**: San Francisco, CA  

## Summary

Experienced AI/ML engineer with 10+ years building production systems...

[Rest of profile]
```

**Agent uses**: First-person synthesis of profile summary in responses

---

### Experience.md (from Spec 002 → consumed by Spec 001)

```markdown
# Experience

## AI Agent Architect @ TechCorp (2023-2025)
- Led design of autonomous agent systems
- Built RAG pipeline with 99.9% uptime
- Mentored 5 engineers on AI architecture

## Senior Engineer @ StartupXYZ (2020-2023)
- ...
```

**Agent uses**: Specific job responsibilities when answering experience questions

---

## Configuration Examples

### For GitHub-Based Ingestion

```bash
# .env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxx
GITHUB_REPOS=byoung/me,byoung/projects

# AI-Me will load:
# - https://github.com/byoung/me/blob/main/*.md
# - https://github.com/byoung/projects/blob/main/*.md
```

Then upload LinkedIn profile markdown to `byoung/me` repo:

```bash
# Repository structure
byoung/me/
├── Profile.md          # from LinkedIn extractor
├── Experience.md       # from LinkedIn extractor
├── Education.md        # from LinkedIn extractor
├── resume.md           # manual or pre-existing
├── projects.md         # manual
└── README.md
```

---

### For Local File Ingestion

```bash
# .env (no GitHub token needed)
GITHUB_REPOS=""  # empty, or omit

# Move LinkedIn profile files to local docs/
cp ~/linkedin-profile/*.md ~/projects/ai-me/docs/

# Restart AI-Me
# DataManager will load from docs/ automatically
```

---

## Data Privacy & Consent

### What Users Control

1. **Extraction**: User manually logs into LinkedIn (no credentials stored)
2. **Review**: User reviews generated markdown before upload
3. **Filtering**: User can delete/edit sensitive information in markdown
4. **Upload**: User chooses where to upload (GitHub public repo, local, etc.)
5. **Sharing**: User decides whether to use data with AI agent

### What's Extracted

Only **publicly visible** LinkedIn data:
- Profile summary (as shown on profile page)
- Published experience/jobs
- Education (if public)
- Skills (if public)
- Recommendations (if public)
- Connections names/titles (if publicly shown)
- Published posts/activity (if public)

### Privacy Best Practices

1. Review markdown files before upload
2. Remove sensitive information (specific salary, internal projects, etc.)
3. Edit connections list if desired (Spec 002 allows truncation)
4. Use private GitHub repo if prefer (not shared publicly)
5. Set `GITHUB_REPOS` to private repo URL in AI-Me config

---

## Troubleshooting Integration

### Problem: Agent doesn't cite LinkedIn data

**Diagnosis**:
1. Verify markdown files uploaded to GitHub repo
2. Verify GitHub repo URL is in `GITHUB_REPOS` env var
3. Verify `GITHUB_PERSONAL_ACCESS_TOKEN` is set
4. Restart AI-Me app
5. Check logs: `DataManager.load_remote_documents()` should show documents loaded

**Solution**:
```bash
# Test data loading
python -c "from src.data import DataManager, DataManagerConfig; 
config = DataManagerConfig(); 
dm = DataManager(config=config); 
docs = dm.load_local_documents(); 
print(f'Loaded {len(docs)} documents')"
```

---

### Problem: LinkedIn markdown syntax errors

**Diagnosis**:
1. Validate markdown: `markdown-lint *.md`
2. Check for special characters, emojis, Unicode issues

**Solution**:
- Spec 002 includes Unicode normalization (Constitution IX)
- User should review markdown files before upload
- Re-run extraction if needed

---

### Problem: Data accuracy issues in agent responses

**Diagnosis**:
1. Verify extracted data matches LinkedIn profile
2. Verify markdown reflects accurate representation of LinkedIn
3. Check vector search is retrieving correct documents

**Solution**:
- User reviews extracted markdown before upload
- Manual editing of markdown files allowed
- Test specific queries: "What company did you work at?" → should cite Experience.md

---

## Future Enhancements

### Phase B: Spec 002 Enhancements

- Scheduled extraction (sync profile changes monthly)
- Data versioning (track profile evolution)
- Diff report (what changed since last extraction)
- LinkedIn API integration (if ToS allows in future)

### Phase B: Spec 001 Integration Enhancements

- Automatic GitHub sync (reload documents on push webhook)
- LinkedIn data freshness indicator ("Profile data from X days ago")
- Dedicated LinkedIn context in agent prompt
- LinkedIn-specific queries: "Show me recent posts" → cite Activity.md

### Joint Enhancement: Documentation Sync Tool

- Tool to automatically sync markdown updates to GitHub
- Dashboard showing which LinkedIn data is in agent's knowledge base
- User audit trail: "Last synced: date"

---

## Success Criteria for Integration

✅ **Extraction**: LinkedIn data → markdown files ≥90% accuracy  
✅ **Review**: User can edit files before upload  
✅ **Upload**: Files accessible to AI-Me DataManager  
✅ **Retrieval**: Agent retrieves correct LinkedIn data for queries  
✅ **Response**: Agent cites LinkedIn profile in first-person responses  
✅ **Accuracy**: Sample responses match LinkedIn source data (100%)

---

## Reference

- **Spec 001**: Personified AI Agent → `/specs/001-personified-ai-agent/spec.md`
- **Spec 002**: LinkedIn Profile Extractor → `/specs/002-linkedin-profile-extractor/spec.md`
- **Constitution**: `/specify/memory/constitution.md` (Principles: RAG-First, Session Isolation, Type-Safe, Async-First)

