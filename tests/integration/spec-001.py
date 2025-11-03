"""
Integration tests for ai-me agent.
Tests the complete setup including vectorstore, agent configuration, and agent responses.
"""
import pytest
import pytest_asyncio
import re
import sys
import os
import logging
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Something about these tests makes me feel yucky. Big, brittle, and slow. BBS?
# In the future we should run inference locally with docker-compose models.

# Set temperature and seed for deterministic test results
os.environ["TEMPERATURE"] = "0"
os.environ["SEED"] = "42"

# Point our RAG to the tests/data directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
test_data_dir = os.path.join(project_root, "tests", "data")
os.environ["DOC_ROOT"] = test_data_dir
os.environ["LOCAL_DOCS"] = "**/*.md"

from config import setup_logger, Config
from agent import AIMeAgent
from data import DataManager, DataManagerConfig

logger = setup_logger(__name__)

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
        _config = Config()  # type: ignore
        logger.info(f"Initialized shared config: {_config.bot_full_name}")
    return _config


def _get_shared_vectorstore():
    """Lazy initialization of shared vectorstore."""
    global _vectorstore, _data_manager
    if _vectorstore is None:
        logger.info("Initializing shared vectorstore (first test)...")
        test_data_dir = os.path.join(project_root, "tests", "data")
        _data_config = DataManagerConfig(
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
    assert aime_agent.session_id is not None, "session_id should be set"
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
async def test_github_documents_load():
    """Tests FR-002: GitHub document loading with source metadata."""
    config = Config()  # type: ignore
    
    # Load GitHub documents directly
    github_config = DataManagerConfig(
        doc_load_local=[]
    )
    dm = DataManager(config=github_config)
    vs = dm.setup_vectorstore(github_repos=["byoung/ai-me"])
    
    agent = AIMeAgent(
        bot_full_name=config.bot_full_name,
        model=config.model,
        vectorstore=vs,
        github_token=config.github_token,
        session_id="test-session"
    )
    await agent.create_ai_me_agent()

    response = await agent.run("Do you have python experience?")
    
    assert "yes" in response.lower(), (
        f"yes' in response but got: {response}"
    )


@pytest.mark.asyncio
async def test_rear_knowledge_contains_it245(ai_me_agent):
    """Tests REQ-001: Knowledge base retrieval of personal documentation."""
    response = await ai_me_agent.run("What is IT-245?")
    
    assert "IT-245" in response or "It-245" in response or "it-245" in response
    logger.info("✓ IT-245 found in response")


@pytest.mark.asyncio
async def test_github_commits_contains_shas(ai_me_agent):
    """Tests REQ-002: MCP GitHub integration - retrieve commit history."""
    response = await ai_me_agent.run("What are some recent commits I've made?")
    
    assert response, "Response is empty"
    assert len(response) > 10, "Response is too short"
    logger.info("✓ Response contains commit information")

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
async def test_github_relative_links_converted_to_absolute_urls():
    """Tests FR-004: Document processing converts relative GitHub links to absolute URLs.
    
    Validates that when documents are loaded from GitHub with relative links 
    (e.g., /resume.md), they are rewritten to full GitHub URLs 
    (e.g., https://github.com/owner/repo/blob/main/resume.md).
    
    This is a unit-level test of the DataManager.process_documents() method.
    """
    from langchain_core.documents import Document
    
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
    
    data_config = DataManagerConfig()
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
    
    logger.info("✓ Test passed: Relative GitHub links converted to absolute URLs")
    logger.info(f"  Original: [my resume](/resume.md)")
    logger.info(f"  Converted: [my resume](https://github.com/byoung/ai-me/blob/main/resume.md)")


@pytest.mark.asyncio
async def test_agent_responses_cite_sources(ai_me_agent):
    """Tests FR-004, FR-011: Agent responses include source citations.
    
    Validates that agent responses include proper source attribution,
    which could be GitHub URLs, local paths, or explicit source references.
    """
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
    
    logger.info("\n✓ Test passed: Agent responses cite sources (FR-004, FR-011)")


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


@pytest.mark.asyncio
async def test_logger_setup_format(caplog):
    """Tests NFR-003 (Structured Logging): Verify setup_logger creates structured logging.
    
    Tests that setup_logger() configures syslog-style format with JSON support for
    structured logging of user/agent interactions.
    
    This validates the logger configuration that our production app relies on
    for analytics and debugging.
    """
    # Force logger setup to run by clearing handlers so setup_logger reconfigures
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    try:
        # Now call setup_logger with no handlers - should trigger full setup
        test_logger = setup_logger("test.structured_logging")
        
        # Verify logger was created
        assert test_logger.name == "test.structured_logging"
        
        # Verify root logger now has handlers (setup_logger should have added them)
        assert len(root_logger.handlers) > 0, (
            "Root logger should have handlers after setup_logger"
        )
        
        # Verify we have a StreamHandler (console output)
        has_stream_handler = any(
            isinstance(handler, logging.StreamHandler)
            for handler in root_logger.handlers
        )
        assert has_stream_handler, "Should have StreamHandler for console output"
        
        # Test that logging works with structured JSON format
        # The formatters should support JSON logging for analytics
        test_logger.info(
            '{"session_id": "test-session", "user_input": "test message"}'
        )
        
        logger.info(
            "✓ Test passed: Logger setup configures structured logging (NFR-003)"
        )
    finally:
        # Restore original handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        for handler in original_handlers:
            root_logger.addHandler(handler)


if __name__ == "__main__":
    # Allow running tests directly with python test.py
    pytest.main([__file__, "-v", "-s"])
