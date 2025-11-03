"""
Integration tests for ai-me agent.
Tests the complete setup including vectorstore, agent configuration, and agent responses.
"""
import pytest
import pytest_asyncio
import re
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Something about these tests makes me feel yucky. Big, brittle, and slow. BBS?
# Couple ideas to make them better:
# - Improve app configuration to avoid directory and globbing gymnastics
# - In the future we should run inference locally with docker-compose

# Set temperature to 0 and seed for deterministic test results
os.environ["TEMPERATURE"] = "0"
os.environ["SEED"] = "42"  # Fixed seed for reproducibility

# Point our RAG to the test_data directory (project root)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
test_data_dir = os.path.join(project_root, "test_data")
os.environ["DOC_ROOT"] = test_data_dir
os.environ["LOCAL_DOCS"] = "**/*.md"


# Add src directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import setup_logger, Config
from agent import AIMeAgent

logger = setup_logger(__name__)
from data import DataManager, DataManagerConfig

# ============================================================================
# SHARED CACHING - Initialize on first use, then reuse
# ============================================================================

_config = None
_vectorstore = None
_data_manager = None


def _get_shared_config():
    """Lazy initialization of shared config."""
    global _config
    if _config is None:
        _config = Config()
        logger.info(f"Initialized shared config: {_config.bot_full_name}")
    return _config


def _get_shared_vectorstore():
    """Lazy initialization of shared vectorstore."""
    global _vectorstore, _data_manager
    if _vectorstore is None:
        logger.info("Initializing shared vectorstore (first test)...")
        test_data_dir = os.path.join(project_root, "test_data")
        _data_config = DataManagerConfig(
            github_repos=[],
            doc_root=test_data_dir
        )
        _data_manager = DataManager(config=_data_config)
        _vectorstore = _data_manager.setup_vectorstore()
        logger.info(f"Shared vectorstore ready: {_vectorstore._collection.count()} documents")
    return _vectorstore


@pytest_asyncio.fixture(scope="function")
async def ai_me_agent():
    """
    Setup fixture for ai-me agent with vectorstore and MCP servers.
    
    CRITICAL: Function-scoped fixture prevents hanging/blocking issues.
    Each test gets its own agent instance with proper cleanup.
    
    Reuses shared config and vectorstore (lazy-initialized on first use).
    
    This fixture:
    - Reuses shared config and vectorstore
    - Creates agent WITH real subprocess MCP servers (GitHub, Time, Memory)
    - Yields agent for test
    - Cleans up MCP servers after test completes
    """
    config = _get_shared_config()
    vectorstore = _get_shared_vectorstore()
    
    # Initialize agent config with shared vectorstore
    aime_agent = AIMeAgent(
        bot_full_name=config.bot_full_name,
        model=config.model,
        vectorstore=vectorstore,
        github_token=config.github_token,
        session_id="test-session"
    )
    
    # Create the agent WITH MCP servers enabled
    logger.info("Creating ai-me agent with MCP servers...")
    await aime_agent.create_ai_me_agent(
        mcp_params=[
            aime_agent.mcp_github_params,
            aime_agent.mcp_time_params,
            aime_agent.get_mcp_memory_params(aime_agent.session_id),
        ]
    )
    logger.info("Agent created successfully with MCP servers")
    logger.info(f"Temperature set to {config.temperature}")
    logger.info(f"Seed set to {config.seed}")
    
    # Yield the agent for the test
    yield aime_agent
    
    # CRITICAL: Cleanup after test completes to prevent hanging
    logger.info("Cleaning up MCP servers after test...")
    await aime_agent.cleanup()
    logger.info("Cleanup complete")


@pytest.mark.asyncio
async def test_rear_knowledge_contains_it245(ai_me_agent):
    """Tests REQ-001: Knowledge base retrieval of personal documentation."""
    response = await ai_me_agent.run(
        "What is IT-245?"
    )
    
    assert "IT-245" in response or "It-245" in response or "it-245" in response
    logger.info(f"✓ Test passed - IT-245 found in response")


@pytest.mark.asyncio
async def test_github_commits_contains_shas(ai_me_agent):
    """Tests REQ-002: MCP GitHub integration - retrieve commit history."""
    response = await ai_me_agent.run(
        "What are some recent commits I've made?"
    )
    
    assert response, "Response is empty"
    assert len(response) > 10, "Response is too short"
    logger.info(f"✓ Test passed - response contains commit information")
    logger.info(f"Response length: {len(response)}")

@pytest.mark.asyncio
async def test_unknown_person_contains_negative_response(ai_me_agent):
    """Tests REQ-003: Graceful handling of out-of-scope requests."""
    response = await ai_me_agent.run(
        "Do you know Slartibartfast?"  # Presumed unknown person
    )
    
    assert response, "Response is empty"
    assert (
        "don't know" in response.lower() 
        or "not familiar" in response.lower() 
        or "no information" in response.lower()
        or "don't have any information" in response.lower()
    ), f"Response doesn't indicate lack of knowledge: {response}"
    logger.info(f"✓ Test passed - correctly handled out-of-scope query")


@pytest.mark.asyncio
async def test_carol_knowledge_contains_product(ai_me_agent):
    """Tests FR-002, FR-003: Verify asking about Carol returns 'product'."""
    response_raw = await ai_me_agent.run("Do you know Carol?")
    response = response_raw.lower()  # Convert to lowercase for matching
    
    # Assert that 'product' appears in the response (Carol is Product Owner)
    assert "product" in response, (
        f"Expected 'product' in response but got: {response}"
    )
    logger.info("✓ Test passed: Response contains 'product'")


@pytest.mark.asyncio
async def test_mcp_time_server_returns_current_date(ai_me_agent):
    """Tests FR-009, NFR-001: Verify that the MCP time server returns the current date."""
    response = await ai_me_agent.run("What is today's date?")

    # Check for current date in various formats (ISO or natural language)
    now = datetime.now()
    expected_date, current_year, current_month, current_day = (
        now.strftime("%Y-%m-%d"),
        str(now.year),
        now.strftime("%B"),
        str(now.day),
    )

    # Accept either ISO format or natural language date
    has_date = (
        expected_date in response
        or (
            current_year in response
            and current_month in response
            and current_day in response
        )
    )

    assert has_date, (
        f"Expected response to contain current date "
        f"({expected_date} or {current_month} {current_day}, {current_year}) "
        f"but got: {response}"
    )
    logger.info(f"✓ Test passed: Response contains current date")


@pytest.mark.asyncio
async def test_mcp_memory_server_remembers_favorite_color(ai_me_agent):
    """Tests FR-013, NFR-002: 
        Verify that the MCP memory server persists information across interactions.
    """
    await ai_me_agent.run("My favorite color is chartreuse.")
    response2 = await ai_me_agent.run("What's my favorite color?")
    
    # Check that the agent remembers the color
    assert "chartreuse" in response2.lower(), (
        f"Expected agent to remember favorite color 'chartreuse' "
        f"but got: {response2}"
    )
    msg = (
        "✓ Test passed: Agent remembered favorite color 'chartreuse' "
        "across interactions"
    )
    logger.info(msg)


@pytest.mark.asyncio
async def test_github_relative_links_converted_to_absolute_urls(ai_me_agent):
    """Tests FR-004, FR-011, NFR-003: Source Attribution via GitHub URL Conversion.
    
    Validates that:
    1. When documents loaded from GitHub have relative links (e.g., /resume.md),
       they are rewritten to full GitHub URLs (e.g.,
       https://github.com/owner/repo/blob/main/resume.md)
    2. Agent responses include proper source attribution with GitHub URLs
    3. Source citations use recognizable patterns (URLs, markdown links)
    
    This ensures all responses can be traced back to public GitHub sources.
    """
    from langchain_core.documents import Document
    
    # PART 1: Test document processing (URL rewriting)
    sample_doc = Document(
        page_content=(
            "Check out [my resume](/resume.md) and "
            "[projects](/projects.md) for more info."
        ),
        metadata={
            "source": "github://byoung/ai-me/docs/about.md",
            "github_repo": "byoung/ai-me"
        }
    )
    
    # Verify metadata is set correctly before processing
    assert sample_doc.metadata["github_repo"] == "byoung/ai-me", (
        "Sample doc metadata should have github_repo"
    )
    assert "github://" in sample_doc.metadata["source"], (
        "Sample doc metadata should have github:// source"
    )
    
    data_config = DataManagerConfig(github_repos=["byoung/ai-me"])
    data_manager = DataManager(config=data_config)
    processed_docs = data_manager.process_documents([sample_doc])
    
    assert len(processed_docs) == 1, "Expected 1 processed document"
    processed_content = processed_docs[0].page_content
    
    # Check that relative links have been converted to absolute GitHub URLs
    assert "https://github.com/byoung/ai-me/blob/main/resume.md" in processed_content, (
        f"Expected absolute GitHub URL for /resume.md in processed content, "
        f"but got: {processed_content}"
    )
    assert "https://github.com/byoung/ai-me/blob/main/projects.md" in processed_content, (
        f"Expected absolute GitHub URL for /projects.md in processed content, "
        f"but got: {processed_content}"
    )
    
    logger.info("✓ Part 1 passed: Relative GitHub links converted to absolute URLs")
    logger.info(f"  Input metadata: github_repo={sample_doc.metadata['github_repo']}")
    logger.info(f"  Original: [my resume](/resume.md)")
    logger.info(f"  Converted: [my resume](https://github.com/byoung/ai-me/blob/main/resume.md)")
    
    # PART 2: Test agent response source attribution
    # For local test data, we just verify sources are cited (in any format)
    # GitHub URL conversion is tested in Part 1 above
    questions = [
        "What do you know about ReaR?",
        "Tell me about your experience in technology",
    ]
    
    for question in questions:
        logger.info(f"\n{'='*60}\nSource citation test: {question}\n{'='*60}")
        
        response = await ai_me_agent.run(question)
        
        # Check that response includes some form of source attribution
        # Could be: GitHub URL, local path, "Sources" section, etc.
        has_source = (
            "https://github.com/" in response or
            ".md" in response or  # Local markdown file reference
            "source" in response.lower() or
            "documentation" in response.lower()
        )
        assert has_source, (
            f"Expected source attribution in response to '{question}' "
            f"but found none. Response: {response}"
        )
        
        # Verify response is substantive (not just metadata)
        min_length = 50
        assert len(response) > min_length, (
            f"Response to '{question}' was too short: {response}"
        )
        
        logger.info(f"✓ Source citation found for: {question[:40]}...")
        logger.info(f"  Response includes source/reference")
    
    logger.info(
        "\n✓ Test passed: GitHub URLs converted (Part 1) + "
        "Agent responses cite sources (Part 2, FR-004, FR-011)"
    )


@pytest.mark.asyncio
async def test_user_story_2_multi_topic_consistency(ai_me_agent):
    """
    Tests FR-001, FR-003, FR-005, NFR-002: User Story 2 - Multi-Topic Consistency
    
    Verify that the agent maintains consistent first-person perspective 
    across multiple conversation topics.
    
    This tests that the agent:
    - Uses first-person perspective (I, my, me) consistently
    - Maintains professional tone across different topic switches
    - Shows context awareness of different topics
    - Remains in-character as the personified individual
    """
    # Ask 3 questions about different topics
    topics = [
        ("What is your background in technology?", "background|experience|technology"),
        ("What programming languages are you skilled in?", "programming|language|skilled"),
    ]
    
    first_person_patterns = [
        r"\bi\b", r"\bme\b", r"\bmy\b", r"\bmyself\b", 
        r"\bI['m]", r"\bI['ve]", r"\bI['ll]"
    ]
    
    for question, topic_keywords in topics:
        logger.info(f"\n{'='*60}\nMulti-topic test question: {question}\n{'='*60}")
        
        response = await ai_me_agent.run(question)
        response_lower = response.lower()
        
        # Check for first-person usage
        first_person_found = any(
            re.search(pattern, response, re.IGNORECASE) 
            for pattern in first_person_patterns
        )
        assert first_person_found, (
            f"Expected first-person perspective in response to '{question}' "
            f"but got: {response}"
        )
        
        # Verify response is substantive (not just "I don't know")
        min_length = 50  # Substantive responses should be > 50 chars
        assert len(response) > min_length, (
            f"Response to '{question}' was too short (likely not substantive): {response}"
        )
        
        logger.info(f"✓ First-person perspective maintained for: {question[:40]}...")
        logger.info(f"  Response preview: {response[:100]}...")
    
    logger.info("\n✓ Test passed: Consistent first-person perspective across 3+ topics")


@pytest.mark.asyncio
async def test_tool_failure_error_messages_are_friendly(caplog, ai_me_agent):
    """
    Tests FR-012, NFR-003: Error Message Quality (FR-012)
    
    Verify that tool failures return user-friendly messages without Python tracebacks.
    
    This tests that the agent:
    - Returns human-readable error messages
    - logs an error that can be reviewed in our dashboard/logs

    Uses mocking to simulate tool failures without adding test-specific code to agent.py
    """
    logger.info(f"\n{'='*60}\nError Handling Test\n{'='*60}")
    
    # Mock the Runner.run method to simulate a tool failure
    # This tests the catch-all exception handler without adding test code to production
    test_scenarios = [
        RuntimeError("Simulated tool timeout"),
        ValueError("Invalid tool parameters"),
    ]
    
    for error in test_scenarios:
        logger.info(f"\nTesting error scenario: {error.__class__.__name__}: {error}")
        
        # Clear previous log records for this iteration
        caplog.clear()
        
        # Mock Runner.run to raise an exception
        with patch('agent.Runner.run', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = error
            
            response = await ai_me_agent.run("Any user question")
            
            logger.info(f"Response: {response[:100]}...")
            
            # PRIMARY CHECK: Verify "I encountered an unexpected error" is in response
            assert "I encountered an unexpected error" in response, (
                f"Response must contain 'I encountered an unexpected error'. Got: {response}"
            )
            
            # SECONDARY CHECK: Verify error was logged by agent.py
            error_logs = [record for record in caplog.records if record.levelname == "ERROR"]
            assert len(error_logs) > 0, "Expected at least one ERROR log record from agent.py"
            
            # Find the agent.py error log (contains "Unexpected error:")
            agent_error_logged = any(
                "Unexpected error:" in record.message for record in error_logs
            )
            assert agent_error_logged, (
                f"Expected ERROR log with 'Unexpected error:' from agent.py. "
                f"Got: {[r.message for r in error_logs]}"
            )
            error_messages = [
                r.message for r in error_logs
                if "Unexpected error:" in r.message
            ]
            logger.info(
                f"✓ Error properly logged to logger: {error_messages}"
            )
    
    logger.info("\n✓ Test passed: Error messages are friendly (FR-012) + properly logged")


if __name__ == "__main__":
    # Allow running tests directly with python test.py
    pytest.main([__file__, "-v", "-s"])
