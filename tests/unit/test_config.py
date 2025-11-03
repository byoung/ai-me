"""
Unit tests for config.py Config and DataManagerConfig classes.

Tests configuration validation, Pydantic models, and environment variable parsing
in isolation without requiring full application setup.
"""
import logging

from config import Config


def test_config_github_repos_parsing():
    """Tests NFR-002 (Type-Safe Configuration): Config.parse_github_repos validator.
    
    Validates that the field validator correctly parses comma-separated repository
    strings from environment variables, including edge cases like empty strings and
    pre-parsed lists. Ensures configuration is validated via Pydantic with strict
    typing and no silent failures.
    """
    # Test empty string
    result = Config.parse_github_repos("")
    assert result == [], "Empty string should parse to empty list"
    
    # Test single repo
    result = Config.parse_github_repos("owner/repo")
    assert result == ["owner/repo"], "Single repo should parse correctly"
    
    # Test multiple repos with spaces
    result = Config.parse_github_repos("owner1/repo1, owner2/repo2 , owner3/repo3")
    assert result == ["owner1/repo1", "owner2/repo2", "owner3/repo3"], (
        "Multiple repos with spaces should parse and strip correctly"
    )
    
    # Test already a list
    result = Config.parse_github_repos(["owner/repo"])
    assert result == ["owner/repo"], "Already a list should pass through"
