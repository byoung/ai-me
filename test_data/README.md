# Test Data Directory

This directory contains controlled test data for RAG (Retrieval Augmented Generation) testing in the ai-me project.

## Purpose

These markdown files provide known content for deterministic testing of:
1. Document loading and chunking (from local files)
2. Vector embeddings and storage (ChromaDB)
3. Retrieval quality (similarity search)
4. Agent response accuracy (RAG output validation)

## Files

| File | Purpose | Key Content | Used By Tests |
|------|---------|-------------|---------------|
| **rear_info.md** | ReaR disaster recovery info | Project ID: IT-245 | test_rear_knowledge_contains_it245 |
| **projects.md** | Project listings | IT-245, IT-300, APP-101, DATA-500 | General project queries |
| **team_info.md** | Team structure (fictional) | Alice, Bob, Carol + departments | Person/team queries |
| **faq.md** | FAQ with tech stack, workflows | IT-245 references, dev processes | General knowledge queries |
| **README.md** | This documentation | Test data guide | - |

## Statistics

- **Total Files**: 5 markdown files
- **Total Chunks**: ~38 (after splitting with CharacterTextSplitter)
- **Chunk Size**: 2500 characters (default)
- **Chunk Overlap**: 0 characters (default)
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2

## Usage in Tests

The test suite (`src/test.py`) automatically uses this directory:

```python
# Configuration in src/test.py
os.environ["GITHUB_REPOS"] = ""  # Disable GitHub loading
test_data_dir = os.path.join(project_root, "test_data")

# DataManager initialization
data_manager = DataManager(
    doc_load_local=["**/*.md"],
    github_repos=[],
    doc_root=test_data_dir  # Points to this directory
)
```

## Test Cases

### ✅ Test 1: ReaR Knowledge (IT-245)
**Query**: "What do you know about ReaR?"

**Source**: `rear_info.md`

**Validates**:
- Document retrieval works correctly
- Agent finds and extracts specific project information
- Response contains "IT-245" identifier

**Expected Output**: Response mentions ReaR, disaster recovery, and IT-245 project.

### ⏭️ Test 2: GitHub Commits (Skipped)
**Note**: Requires MCP servers (disabled for test speed).

### ✅ Test 3: Unknown Person (Negative Test)
**Query**: "Who is slartibartfast?"

**Source**: None (intentionally missing)

**Validates**:
- Agent handles missing information gracefully
- No hallucination or fabricated responses
- Proper "don't have information" response

**Expected Output**: Response contains negative indicators like "don't have", "no information", etc.

## Benefits vs. Loading from GitHub

| Aspect | Test Data Directory | GitHub Loading |
|--------|-------------------|----------------|
| **Speed** | ~10 seconds total | Minutes per test run |
| **Network** | None required | API calls needed |
| **Determinism** | Fully controlled | May change over time |
| **Setup** | Already included | Requires GitHub token |
| **Isolation** | Completely isolated | External dependency |

## Key Implementation Details

### Local Document Metadata

Unlike GitHub documents, local documents have simplified metadata:

```python
# GitHub documents have:
doc.metadata['github_repo'] = 'owner/repo'
doc.metadata['file_path'] = 'path/to/file.md'

# Local documents have:
doc.metadata['source'] = '/full/path/to/file.md'
# NO github_repo field
```

The `get_local_info` tool in `src/agent.py` was updated to handle both cases.

### Unicode Handling

Test assertions handle Unicode variants:

- **Hyphens**: `IT-245` (regular) vs `IT‑245` (non-breaking)
- **Apostrophes**: `don't` (regular) vs `don't` (smart quote)
- **Spaces**: Regular space vs non-breaking space (`\u00a0`)

## Adding New Test Data

To add new test content:

1. **Create markdown file** in this directory:
   ```bash
   touch test_data/my_topic.md
   # Add relevant content with known facts
   ```

2. **Add test case** in `src/test.py`:
   ```python
   @pytest.mark.asyncio
   async def test_my_topic_knowledge(ai_me_agent):
       query = "What do you know about [topic]?"
       result = await Runner.run(ai_me_agent, query, max_turns=30)
       assert "[expected_content]" in result.final_output
   ```

3. **Document** in this README

4. **Verify** chunks created:
   ```bash
   uv run pytest src/test.py -v -s | grep "Created.*chunks"
   ```

## Maintenance Guidelines

### What TO Include

✅ Fictional but realistic data
✅ Specific identifiers for testing (e.g., IT-245)
✅ Structured markdown with clear headings
✅ Cross-references between documents
✅ Both positive and negative test cases

### What NOT to Include

❌ Real personal information or PII
❌ Sensitive company data
❌ Large binary files or images
❌ External dependencies
❌ Dynamic/time-sensitive content

## Troubleshooting

### "Vectorstore setup complete with 0 documents"
**Cause**: Files not loading from test_data directory

**Fix**: Verify `doc_root` parameter and file patterns

### "Expected 'IT-245' in response but got..."
**Cause**: LLM used Unicode non-breaking hyphen

**Fix**: Test already handles both variants, check for other formatting

### Test execution is slow (> 30 seconds)
**Cause**: May be loading from GitHub instead of test_data

**Fix**: Verify `GITHUB_REPOS=""` in test environment setup

## Performance Benchmarks

Measured on M1 MacBook Pro:

- **Vectorstore Setup**: 2-3 seconds (includes embedding model loading)
- **Test 1 (ReaR)**: 3-4 seconds (includes LLM calls)
- **Test 3 (Unknown)**: 3-4 seconds
- **Total Runtime**: ~10 seconds for all passing tests

Compare to production setup with GitHub repos: 2-5 minutes

## Future Enhancements

- [ ] Add more domain-specific test documents
- [ ] Create test cases for multi-document synthesis
- [ ] Add edge cases (empty files, malformed markdown)
- [ ] Performance regression tests
- [ ] Quality metrics (retrieval precision/recall)

For more details, see `/TESTING.md` in the project root.
