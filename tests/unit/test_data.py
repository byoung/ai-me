"""
Unit tests for data.py DataManager class.

Tests individual methods of the DataManager and DataManagerConfig in isolation,
without requiring external APIs or full integration setup.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from data import DataManager, DataManagerConfig


class TestLoadLocalDocuments:
    """Tests for DataManager.load_local_documents() method.
    
    Implements FR-002 (Knowledge Retrieval): Document loading from local filesystem.
    """

    def test_load_local_documents_missing_directory(self):
        """Tests FR-002: Handle missing doc_root gracefully.
        
        When doc_root directory doesn't exist, load_local_documents should
        return empty list and log warning instead of raising exception.
        """
        # Create config pointing to non-existent directory
        config = DataManagerConfig(doc_root="/nonexistent/path/xyz")
        dm = DataManager(config=config)
        
        # Should return empty list, not raise exception
        docs = dm.load_local_documents()
        
        assert docs == [], "Expected empty list for missing directory"
        assert isinstance(docs, list), "Expected list return type"

    def test_load_local_documents_valid_directory(self):
        """Tests FR-002: Load documents from existing directory.
        
        When doc_root exists, load_local_documents should return loaded documents.
        Uses tests/data directory which contains sample markdown files.
        """
        # Use test data directory
        test_data_dir = str(Path(__file__).parent.parent / "data")
        config = DataManagerConfig(doc_root=test_data_dir)
        dm = DataManager(config=config)
        
        # Should load documents
        docs = dm.load_local_documents()
        
        assert isinstance(docs, list), "Expected list return type"
        assert len(docs) > 0, "Expected to find documents in tests/data"
        
        # Verify documents have required metadata
        for doc in docs:
            assert "source" in doc.metadata, "Document should have source metadata"
            assert doc.page_content, "Document should have content"

    def test_load_local_documents_multiple_glob_patterns(self):
        """Tests FR-002: Load documents using multiple glob patterns (lines 81-83).
        
        Tests the for loop iteration over multiple glob patterns in load_local_documents.
        This covers lines 81-83 where patterns are iterated and loaded.
        """
        # Use test data directory
        test_data_dir = str(Path(__file__).parent.parent / "data")
        
        # Create config with multiple glob patterns
        config = DataManagerConfig(
            doc_root=test_data_dir,
            doc_load_local=["*.md", "**/*.md"]  # Multiple patterns
        )
        dm = DataManager(config=config)
        
        # Should load documents from all patterns
        docs = dm.load_local_documents()
        
        assert isinstance(docs, list), "Expected list return type"
        assert len(docs) > 0, "Expected to find documents with multiple patterns"
        
        # Verify all patterns were processed (should have more docs due to overlap)
        assert len(docs) >= 3, "Expected at least 3 docs from test data"


class TestCreateVectorstore:
    """Tests for DataManager.create_vectorstore() method.
    
    Implements FR-002 (Knowledge Retrieval): Vectorstore creation with edge cases.
    """

    def test_create_vectorstore_rejects_empty_chunks(self):
        """Tests FR-002: Reject empty chunks with clear error message.
        
        When no documents are provided, create_vectorstore should raise
        ValueError with a clear message about how to configure document sources.
        This prevents silent failures and provides actionable guidance.
        """
        config = DataManagerConfig()
        dm = DataManager(config=config)
        
        # Should raise ValueError with clear message
        with pytest.raises(ValueError) as exc_info:
            dm.create_vectorstore(chunks=[], reset=True)
        
        error_message = str(exc_info.value)
        assert "No documents loaded" in error_message, "Should explain the problem"
        assert "GITHUB_REPOS" in error_message, "Should mention GITHUB_REPOS"
        assert "docs/local-testing/" in error_message, "Should mention local docs path"


class TestProcessDocuments:
    """Tests for DataManager.process_documents() method.
    
    Implements FR-004 (Source Attribution): Converting relative GitHub links
    to absolute URLs in markdown documents.
    """

    def test_process_documents_converts_relative_links_to_absolute(self):
        """Tests FR-004: Relative GitHub links converted to absolute URLs.
        
        Verifies that process_documents rewrites relative links like /path/file.md
        to absolute GitHub URLs like https://github.com/owner/repo/blob/main/path/file.md
        """
        # Create a sample document with relative GitHub links
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
        
        config = DataManagerConfig()
        dm = DataManager(config=config)
        
        # Process the document
        processed_docs = dm.process_documents([sample_doc])
        
        assert len(processed_docs) == 1, "Expected 1 processed document"
        processed_content = processed_docs[0].page_content
        
        # Verify relative links were converted to absolute GitHub URLs
        assert "https://github.com/byoung/ai-me/blob/main/resume.md" in processed_content, (
            f"Expected absolute URL for /resume.md in: {processed_content}"
        )
        assert "https://github.com/byoung/ai-me/blob/main/projects.md" in processed_content, (
            f"Expected absolute URL for /projects.md in: {processed_content}"
        )

    def test_process_documents_preserves_non_github_docs(self):
        """Tests FR-004: Non-GitHub documents are preserved unchanged.
        
        Documents without github_repo metadata should pass through unchanged.
        """
        # Create a document without github_repo metadata
        sample_doc = Document(
            page_content="[my resume](/resume.md)",
            metadata={
                "source": "local://docs/about.md"
            }
        )
        
        config = DataManagerConfig()
        dm = DataManager(config=config)
        
        # Process the document
        processed_docs = dm.process_documents([sample_doc])
        
        assert len(processed_docs) == 1, "Expected 1 processed document"
        # Content should be unchanged (no github_repo in metadata)
        assert processed_docs[0].page_content == "[my resume](/resume.md)", (
            "Non-GitHub document should not be modified"
        )

    def test_process_documents_handles_markdown_with_anchors(self):
        """Tests FR-004: Markdown links with anchor fragments are preserved.
        
        Links like [text](/file.md#section) should preserve the anchor in the URL.
        """
        sample_doc = Document(
            page_content="See [section](/docs/guide.md#installation) for details.",
            metadata={
                "source": "github://user/repo/README.md",
                "github_repo": "user/repo"
            }
        )
        
        config = DataManagerConfig()
        dm = DataManager(config=config)
        
        processed_docs = dm.process_documents([sample_doc])
        processed_content = processed_docs[0].page_content
        
        # Verify anchor is preserved in the URL
        assert "https://github.com/user/repo/blob/main/docs/guide.md#installation" in processed_content, (
            f"Expected anchor preserved in URL in: {processed_content}"
        )
