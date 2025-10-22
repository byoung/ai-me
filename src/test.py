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

# Something about these tests makes me feel yucky. Big, brittle, and slow. BBS?
# Couple ideas to make them better:
# - Improve app configuration to avoid directory and globbing gymnastics
# - In the future we should run inference locally with docker-compose
# - figure out how to make LLMs behave like humans by using "normal" utf8 symbols

# Set temperature to 0 for deterministic test results
os.environ["TEMPERATURE"] = "0"

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


@pytest_asyncio.fixture(scope="function")
async def ai_me_agent():
    """
    Setup fixture for ai-me agent with vectorstore.
    This fixture is function-scoped so each test gets a clean agent instance.
    Returns the AIMeAgent instance (not the Agent) so tests can use the run() method.
    Automatically cleans up MCP servers after each test.
    """
    # Initialize configuration
    # In GitHub Actions, env vars are set directly (no .env file)
    # Locally, Config will read from .env file automatically
    config = Config()
    
    # Get test_data directory path
    test_data_dir = os.path.join(project_root, "test_data")
    
    # Initialize data manager and vectorstore with test data
    logger.info(f"Setting up vectorstore with test data from {test_data_dir}...")
    data_config = DataManagerConfig(
        github_repos=[],  # Empty list - no remote repos for tests
        doc_root=test_data_dir  # Use test_data directory instead of default docs/
    )
    data_manager = DataManager(config=data_config)
    vectorstore = data_manager.setup_vectorstore()
    logger.info(f"Vectorstore setup complete with {vectorstore._collection.count()} documents")
    
    # Initialize agent config with vectorstore
    aime_agent = AIMeAgent(
        bot_full_name=config.bot_full_name,
        model=config.model,
        vectorstore=vectorstore,
        github_token=config.github_token,
        session_id="test-session-12345678"  # Fake session ID for test logging
    )
    
    # Create the agent WITH MCP servers enabled for full integration testing
    # Temperature is controlled via config.temperature (default 1.0, or set TEMPERATURE in .env)
    logger.info("Creating ai-me agent...")
    await aime_agent.create_ai_me_agent(
        aime_agent.agent_prompt, 
        mcp_params=[
            aime_agent.mcp_github_params,
            aime_agent.mcp_time_params,
            aime_agent.get_mcp_memory_params(aime_agent.session_id),
        ]
    )
    logger.info("Agent created successfully")
    logger.info("Note: MCP servers enabled (GitHub + Time + Memory)")
    logger.info(f"Note: Temperature set to {config.temperature} (from config)")
    
    # Yield the agent for the test
    yield aime_agent
    
    # Cleanup after test completes
    logger.info("Cleaning up MCP servers...")
    await aime_agent.cleanup()


@pytest.mark.asyncio
async def test_rear_knowledge_contains_it245(ai_me_agent):
    """
    Test 1: Verify that asking about ReaR returns information containing IT-245.
    This tests that the agent can retrieve and return specific technical information.
    """
    response = await ai_me_agent.run("What do you know about ReaR?")
    
    assert "IT-245" in response, f"Expected 'IT-245' in response but got: {response}"
    logger.info("✓ Test passed: Response contains 'IT-245'")


@pytest.mark.asyncio
async def test_github_commits_contains_shas(ai_me_agent):
    """
    Test 2: Verify that asking about recent commits returns commit SHAs.
    This tests the agent's integration with GitHub MCP server.
    The query explicitly specifies a repo to test MCP tool calling.
    """
    query = "List the 3 most recent commits in the byoung/ai-me repository"
    logger.info(f"\n{'='*60}\nTest 2: {query}\n{'='*60}")
    
    response = await ai_me_agent.run(query)
    
    # Look for git SHA patterns (7-40 character hex strings)
    # Git SHAs are typically 7+ characters when abbreviated, 40 when full
    sha_pattern = re.compile(r'\b[0-9a-f]{7,40}\b', re.IGNORECASE)
    shas_found = sha_pattern.findall(response)
    
    assert len(shas_found) > 0, (
        f"Expected to find commit SHAs in response but found none. Response: {response}"
    )
    logger.info(f"✓ Test passed: Found {len(shas_found)} commit SHA(s): {shas_found}")


@pytest.mark.asyncio
async def test_unknown_person_contains_negative_response(ai_me_agent):
    """Test 3: Verify that asking about an unknown person returns a negative response."""    
    response = await ai_me_agent.run("who is slartibartfast?")
    
    negative_indicators = [
        "wasn't", "could not", "couldn't", "don't know", "do not know", 
        "no information", "not familiar", "don't have", "do not have",
        "not found", "unable to find", "don't have any", "do not have any",
        "no data", "no records"
    ]
    
    found_indicator = any(indicator in response.lower() for indicator in negative_indicators)
    assert found_indicator, (
        f"Expected response to contain a negative indicator but got: {response}"
    )
    logger.info(f"✓ Test passed: Response contains negative indicator")


@pytest.mark.asyncio
async def test_carol_knowledge_contains_product(ai_me_agent):
    """Test 4: Verify that asking about Carol returns information containing 'product'."""
    response_raw = await ai_me_agent.run("Do you know Carol?")
    response = response_raw.lower()  # Convert to lowercase for matching
    
    # Assert that 'product' appears in the response (Carol is Product Owner)
    assert "product" in response, (
        f"Expected 'product' in response but got: {response}"
    )
    logger.info("✓ Test passed: Response contains 'product'")


@pytest.mark.asyncio
async def test_mcp_time_server_returns_current_date(ai_me_agent):
    """Test 5: Verify that the MCP time server returns the current date."""
    
    response = await ai_me_agent.run("What is today's date?")
    
    # Check for current date in various formats (ISO or natural language)
    now = datetime.now()
    expected_date, current_year, current_month, current_day = (
        now.strftime("%Y-%m-%d"), str(now.year), now.strftime("%B"), str(now.day)
    )
    
    # Accept either ISO format or natural language date
    has_date = (expected_date in response or 
                (current_year in response and current_month in response and current_day in response))
    
    assert has_date, (
        f"Expected response to contain current date ({expected_date} or {current_month} {current_day}, {current_year}) "
        f"but got: {response}"
    )
    logger.info(f"✓ Test passed: Response contains current date")


@pytest.mark.asyncio
async def test_mcp_memory_server_remembers_favorite_color(ai_me_agent):
    """Test 6: Verify that the MCP memory server persists information across interactions."""

    await ai_me_agent.run("My favorite color is chartreuse.")
    response2 = await ai_me_agent.run("What's my favorite color?")
    
    # Check that the agent remembers the color
    assert "chartreuse" in response2.lower(), (
        f"Expected agent to remember favorite color 'chartreuse' but got: {response2}"
    )
    logger.info("✓ Test passed: Agent remembered favorite color 'chartreuse' across interactions")


if __name__ == "__main__":
    # Allow running tests directly with python test.py
    pytest.main([__file__, "-v", "-s"])
