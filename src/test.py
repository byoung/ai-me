"""
Integration tests for ai-me agent.
Tests the complete setup including vectorstore, agent configuration, and agent responses.
"""
import pytest
import pytest_asyncio
import re
import sys
import os

# Something about these tests makes me feel yucky. Big, brittle, and slow. BBS?
# Couple ideas to make them better:
# - Improve app configuration to avoid directory and globbing gymnastics
# - One agent per test to avoid state carryover once we have memory
# - In the future we should run inference locally with docker-compose
# - figure out to make LLMs behave like humans by using "normal" utf8 symbols

# Set temperature to 0 for deterministic test results
os.environ["TEMPERATURE"] = "0"

# Set GITHUB_REPOS to empty to avoid loading any remote repos during tests
os.environ["GITHUB_REPOS"] = ""

# Point our RAG to the test_data directory (project root)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
test_data_dir = os.path.join(project_root, "test_data")
os.environ["DOC_ROOT"] = test_data_dir
os.environ["LOCAL_DOCS"] = "**/*.md"


# Add src directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import setup_logger

logger = setup_logger(__name__)# Add src directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import setup_logger

logger = setup_logger(__name__)

from config import Config
from agent import AIMeAgent
from data import DataManager, DataManagerConfig


@pytest_asyncio.fixture(scope="module")
async def ai_me_agent():
    """
    Setup fixture for ai-me agent with vectorstore.
    This fixture is module-scoped to avoid reinitializing the agent for each test.
    Returns the AIMeAgent instance (not the Agent) so tests can use the run() method.
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
        github_repos=config.github_repos,
        doc_root=test_data_dir  # Use test_data directory instead of default docs/
    )
    data_manager = DataManager(config=data_config)
    vectorstore = data_manager.setup_vectorstore()
    logger.info(f"Vectorstore setup complete with {vectorstore._collection.count()} documents")
    
    # Initialize agent config with vectorstore
    agent_config = AIMeAgent(
        bot_full_name=config.bot_full_name,
        model=config.model,
        vectorstore=vectorstore,
        github_token=config.github_token
    )
    
    # Create the agent (without MCP servers for faster testing - tests 1 and 3 only need vectorstore)
    # Temperature is controlled via config.temperature (default 1.0, or set TEMPERATURE in .env)
    logger.info("Creating ai-me agent...")
    await agent_config.create_ai_me_agent(
        agent_config.agent_prompt, 
        mcp_params=[]  # Empty list disables MCP servers
    )
    logger.info("Agent created successfully")
    logger.info("Note: MCP servers disabled for these tests (only vectorstore RAG is needed)")
    logger.info(f"Note: Temperature set to {config.temperature} (from config)")
    
    # Return the agent_config instance so tests can use agent_config.run()
    return agent_config


@pytest.mark.asyncio
async def test_rear_knowledge_contains_it245(ai_me_agent):
    """
    Test 1: Verify that asking about ReaR returns information containing IT-245.
    This tests that the agent can retrieve and return specific technical information.
    """
    query = "What do you know about ReaR?"
    logger.info(f"\n{'='*60}\nTest 1: {query}\n{'='*60}")
    
    logger.info("Running agent query...")
    response = await ai_me_agent.run(query, max_turns=30)
    
    logger.info(f"Response:\n{response}\n{'='*60}")
    
    # Assert that IT-245 appears in the response (handle both regular and Unicode hyphens)
    # LLMs love fancy typography: regular hyphen '-' (U+002D) vs non-breaking hyphen '‑' (U+2011)
    assert "IT-245" in response or "IT‑245" in response, (
        f"Expected 'IT-245' in response but got: {response}"
    )
    logger.info("✓ Test passed: Response contains 'IT-245'")


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires MCP servers - not configured in test fixture. Run manually if needed.")
async def test_github_commits_contains_shas(ai_me_agent):
    """
    Test 2: Verify that asking about recent commits returns commit SHAs.
    This tests the agent's integration with GitHub MCP server.
    NOTE: This test is skipped by default as it requires MCP servers which slow down testing.
    """
    query = "Give me a summary of all the commits you've made in the last week"
    logger.info(f"\n{'='*60}\nTest 2: {query}\n{'='*60}")
    
    response = await ai_me_agent.run(query, max_turns=30)
    
    logger.info(f"Response:\n{response}\n{'='*60}")
    
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
    """
    Test 3: Verify that asking about an unknown person returns a negative response.
    This tests that the agent properly indicates when it doesn't have information.
    """
    query = "who is slartibartfast?"
    logger.info(f"\n{'='*60}\nTest 3: {query}\n{'='*60}")
    
    response_raw = await ai_me_agent.run(query, max_turns=30)
    response = response_raw.lower()  # Convert to lowercase for matching
    
    logger.info(f"Response:\n{response}\n{'='*60}")
    
    # Check for negative indicators (wasn't, could not, don't know, no information, etc.)
    # LLMs use smart quotes: regular apostrophe "'" (U+0027) vs right single quote "'" (U+2019)
    negative_indicators = [
        "wasn't", "could not", "couldn't", "don't know", "do not know", 
        "no information", "not familiar", "don't have", "do not have",
        "not found", "unable to find", "don't have any", "do not have any",
        "no data", "no records"
    ]
    
    # Normalize response by replacing various apostrophe types with standard apostrophe
    # Also normalize Unicode spaces and other whitespace characters
    normalized_response = response.replace("'", "'").replace("'", "'").replace("\u2019", "'")
    normalized_response = normalized_response.replace('\u00a0', ' ')  # non-breaking space
    normalized_response = ' '.join(normalized_response.split())  # normalize all whitespace
    
    found_indicator = any(indicator in normalized_response for indicator in negative_indicators)
    logger.info(f"Found negative indicator: {found_indicator}")
    assert found_indicator, (
        f"Expected response to contain a negative indicator (wasn't/could not/etc.) "
        f"but got: {response}"
    )
    logger.info(f"✓ Test passed: Response contains negative indicator")


@pytest.mark.asyncio
async def test_carol_knowledge_contains_product(ai_me_agent):
    """
    Test 4: Verify that asking about Carol returns information containing 'product'.
    This tests that the agent can retrieve team member information and their roles.
    """
    query = "Do you know Carol?"
    response_raw = await ai_me_agent.run(query, max_turns=30)
    response = response_raw.lower()  # Convert to lowercase for matching
    
    logger.info(f"Response:\n{response}\n{'='*60}")
    
    # Assert that 'product' appears in the response (Carol is Product Owner)
    assert "product" in response, (
        f"Expected 'product' in response but got: {response}"
    )
    logger.info("✓ Test passed: Response contains 'product'")


if __name__ == "__main__":
    # Allow running tests directly with python test.py
    pytest.main([__file__, "-v", "-s"])
