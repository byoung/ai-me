"""
Document loading, processing, and vectorstore management for ai-me application. Handles loading
from local directories and GitHub repositories, chunking, and creating ChromaDB vector stores.
"""
import os
import re
import shutil
from typing import List, Optional, Callable

from pydantic import BaseModel, Field
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    GitLoader,
)
from langchain_text_splitters import MarkdownTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings

from config import setup_logger

logger = setup_logger(__name__)

class DataManagerConfig(BaseModel):
    """Configuration for DataManager with Pydantic validation."""
    
    doc_load_local: List[str] = Field(
        default=["**/*.md"], description="Glob patterns for local docs (e.g., ['*.md'])")
    github_repos: List[str] = Field(
        default=[], description="List of GitHub repos (format: owner/repo)")
    doc_root: str = Field(
        default=(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), "..", "docs", "local-testing"
                )
            )
            + "/"
        ),
        description="Root directory for local documents (development/testing only)"
    )
    chunk_size: int = Field(
        default=2500, description="Character chunk size for splitting")
    chunk_overlap: int = Field(
        default=0, description="Character overlap between chunks")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace embedding model name")
    db_name: str = Field(
        default="ai_me", description="ChromaDB collection name")

class DataManager:
    """
    Consolidated document loading, processing, and vectorstore management. Handles the complete
    data pipeline from loading documents to creating a queryable vectorstore. Configuration
    parameters have sensible defaults and can be overridden as needed.
    """
    
    def __init__(self, config: DataManagerConfig):
        """
        Initialize data manager with configuration.
        
        Implements FR-002 (Knowledge Retrieval).
        
        Args:
            config: DataManagerConfig instance with all settings
        """
        self.config = config
        
        # Internal state
        self.vectorstore: Optional[Chroma] = None
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
    
    def load_local_documents(self) -> List[Document]:
        """
        Load documents from local directory. Returns empty list if directory not found.
        
        Implements FR-002 (Knowledge Retrieval).
        """
        logger.info(f"Loading local documents from: {self.config.doc_root}")
        
        # Check if directory exists first
        if not os.path.exists(self.config.doc_root):
            logger.info(
                f"Warning: Directory not found: {self.config.doc_root} - "
                f"skipping local documents"
            )
            return []
        
        all_documents = []
        
        # Iterate over all glob patterns
        for pattern in self.config.doc_load_local:
            try:
                logger.info(f"  Loading pattern: {pattern}")
                loader = DirectoryLoader(
                    self.config.doc_root,
                    glob=pattern,
                    loader_cls=TextLoader,
                    loader_kwargs={'encoding': 'utf-8'}
                )
                documents = loader.load()
                logger.info(f"    Found {len(documents)} documents")
                all_documents.extend(documents)
            except Exception as e:  # pragma: no cover
                logger.info(
                    f"  Error loading pattern {pattern}: {e}"
                    f" - skipping this pattern"
                )
                continue
        
        logger.info(f"Loaded {len(all_documents)} total local documents.")
        return all_documents
    
    def load_github_documents(self, repos: List[str] = None,
        file_filter: Optional[Callable[[str], bool]] = None, cleanup_tmp: bool = True
    ) -> List[Document]:
        """
        Load documents from GitHub repositories.
        
        Implements FR-002 (Knowledge Retrieval), FR-010 (Optional Tools - GitHub).
        
        Args:
            repos: List of repos (owner/repo format). Defaults to github_repos from init.
            file_filter: Optional filter function for files. If None, uses default filter
                excluding README, CONTRIBUTING, CODE_OF_CONDUCT, and SECURITY files.
            cleanup_tmp: If True, remove tmp directory before loading.
        
        Returns:
            List of loaded documents from all repos.
        """
        if repos is None:
            repos = self.config.github_repos
        
        # Default filter excludes common documentation files that degrade RAG quality
        if file_filter is None:
            def file_filter(fp: str) -> bool:
                """Default filter excludes contributing docs to preserve RAG quality.
                
                Implements FR-002 (Knowledge Retrieval): Filters out common boilerplate
                files (README, CONTRIBUTING, etc.) that aren't representative of
                personified agent knowledge.
                """
                basename = os.path.basename(fp).lower()
                # Exclude common boilerplate that doesn't represent agent's knowledge
                excluded = {"readme.md", "contributing.md", "code_of_conduct.md",
                           "security.md"}
                return basename not in excluded
        
        all_docs = []
        # Clean up tmp directory before loading
        tmp_dir = "./tmp"

        if os.path.exists(tmp_dir) and cleanup_tmp:
            logger.info(f"Cleaning up existing tmp directory: {tmp_dir}")
            shutil.rmtree(tmp_dir)

        logger.info(f"Loading GitHub documents from {len(repos)} repos {repos}")
        for repo in repos:
            logger.info(f"Loading GitHub repo: {repo}")
            try:
                # Clone repo using GitLoader (even though it doesn't load files)
                repo_path = f"{tmp_dir}/{repo}"
                loader = GitLoader(
                    clone_url=f"https://github.com/{repo}",
                    repo_path=repo_path,
                    branch="main",
                )
                # GitLoader.load() doesn't return files, but it clones the repo
                # so we use DirectoryLoader to actually load the markdown files
                loader.load()
                
                # Now use DirectoryLoader to load markdown files from the cloned repo
                directory_loader = DirectoryLoader(
                    repo_path,
                    glob="**/*.md",
                    loader_cls=TextLoader,
                    loader_kwargs={'encoding': 'utf-8'}
                )
                docs = directory_loader.load()
                
                # Apply filter (default or custom) to exclude irrelevant files
                docs = [doc for doc in docs if file_filter(doc.metadata['source'])]
                
                # Add repo metadata to each document
                for doc in docs:
                    doc.metadata["github_repo"] = repo
                
                logger.info(f"  Loaded {len(docs)} documents from {repo}")
                all_docs.extend(docs)
            except Exception as e:
                logger.info(f"  Error loading repo {repo}: {e} - skipping")
                continue
        
        logger.info(f"Loaded {len(all_docs)} total GitHub documents.")
        return all_docs
    
    def process_documents(self, docs: List[Document]) -> List[Document]:
        """
        Hydrate links in markdown documents to point to GitHub.
        
        Implements FR-004 (Source Attribution).
        
        Args:
            docs: List of documents to process
        
        Returns:
            List of processed documents
        """
        processed = []
        for doc in docs:
            logger.info(f"Processing: {doc.metadata['source']}")
            
            # Fix baseless links to point to GitHub (if from a GitHub repo)
            if "github_repo" in doc.metadata:
                repo = doc.metadata["github_repo"]
                # First pass: fix absolute paths like /website/ or /docs/
                # typically used in short links
                doc.page_content = re.sub(r'(\s|^)(/[a-zA-Z0-9_-]+/)',
                    rf'\1https://github.com/{repo}/tree/main\2', doc.page_content)
                # Second pass: fix inline markdown links like [text](/path/file.md)
                doc.page_content = re.sub(r'\[([^\]]+)\]\((/[^)]+\.md(?:#[^)]+)?)\)',
                    rf'[\1](https://github.com/{repo}/blob/main\2)', doc.page_content)
                            
            processed.append(doc)
        
        return processed
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks for better retrieval. Uses header-based splitting to
        preserve document structure, then further splits by size if needed.
        
        Implements FR-002 (Knowledge Retrieval).
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents with both original metadata and header metadata
        """
        logger.info(f"Chunking {len(documents)} documents...")
        
        # Define headers to split on (h1, h2, h3)
        headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
        header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, 
            strip_headers=False)
        
        all_chunks = []
        chunk_index = 0  # Track chunk number across all documents
        for doc in documents:
            # Split by headers first - this returns Documents with header metadata
            header_chunks = header_splitter.split_text(doc.page_content)
            
            # Convert to Documents and preserve original metadata + add header metadata
            for chunk in header_chunks:
                # Create new Document with combined metadata
                merged_metadata = {**doc.metadata, **chunk.metadata}
                merged_metadata['chunk_index'] = chunk_index  # Add global chunk index
                chunk_index += 1
                new_doc = Document(
                    page_content=chunk.page_content,
                    metadata=merged_metadata,
                )
                all_chunks.append(new_doc)
        
        # Optional: Further split large chunks if they exceed size limit
        size_splitter = MarkdownTextSplitter(chunk_size=self.config.chunk_size)
        final_chunks = size_splitter.split_documents(all_chunks)
        
        # Re-index after size splitting to maintain sequential chunk indices
        for i, chunk in enumerate(final_chunks):
            chunk.metadata['chunk_index'] = i
        
        logger.info(f"Created {len(final_chunks)} chunks")
        return final_chunks
    
    def load_and_process_all(self, github_repos: List[str] = None) -> List[Document]:
        """
        Load, process, and chunk all documents. Automatically loads local documents
        if doc_load_local is set, and GitHub documents if github_repos (or
        self.config.github_repos) is set.

        Implements FR-002 (Knowledge Retrieval).

        Args:
            github_repos: Optional list of specific repos to load. Uses
                self.config.github_repos if None.

        Returns:
            List of processed and chunked documents.
        """
        all_docs = []
        
        # Load local documents if patterns are configured
        if self.config.doc_load_local:
            all_docs.extend(self.load_local_documents())
        
        # Load GitHub documents if repos are configured
        repos_to_load = github_repos if github_repos is not None else self.config.github_repos
        if repos_to_load:
            all_docs.extend(self.load_github_documents(repos=repos_to_load))
        
        processed_docs = self.process_documents(all_docs)
        chunks = self.chunk_documents(processed_docs)
        
        return chunks
    
    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """
        Get or create embeddings model.
        
        Implements FR-002 (Knowledge Retrieval).
        
        Returns:
            HuggingFace embeddings instance
        """
        if self._embeddings is None:
            logger.info(f"Loading embeddings model: {self.config.embedding_model}")
            self._embeddings = HuggingFaceEmbeddings(model_name=self.config.embedding_model)
        return self._embeddings
    
    def create_vectorstore(self, chunks: List[Document], reset: bool = True) -> Chroma:
        """
        Create ChromaDB vectorstore from document chunks.
        
        Implements FR-002 (Knowledge Retrieval)
        
        Args:
            chunks: List of document chunks to store.
            reset: If True, drop existing collection before creating.
        
        Returns:
            Chroma vectorstore instance.
        """
        embeddings = self.get_embeddings()
        
        # Use EphemeralClient for faster in-memory storage
        chroma_client = chromadb.EphemeralClient(Settings(anonymized_telemetry=False))
        
        # Drop existing collection if requested
        if reset:  # pragma: no cover
            try:
                chroma_client.delete_collection(self.config.db_name)
                logger.info(f"Dropped existing collection: {self.config.db_name}")
            except Exception:  # pragma: no cover
                pass  # Collection doesn't exist yet
        
        logger.info(f"Creating vectorstore with {len(chunks)} chunks...")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            client=chroma_client,
            collection_name=self.config.db_name,
        )
        
        count = vectorstore._collection.count()
        logger.info(f"Vectorstore created with {count} documents")
        
        self.vectorstore = vectorstore
        return vectorstore
    
    def setup_vectorstore(
        self, github_repos: List[str] = None, reset: bool = True
    ) -> Chroma:
        """
        Complete pipeline: load, process, chunk, and create vectorstore. Automatically
        loads local documents if doc_load_local is set, and GitHub documents if
        github_repos is specified.

        Implements FR-002 (Knowledge Retrieval).

        Args:
            github_repos: Optional list of specific repos to load. Uses
                self.config.github_repos if None.
            reset: If True, drop existing collection before creating.

        Returns:
            Chroma vectorstore instance ready for queries.
        """
        logger.info("Setting up vectorstore...")
        chunks = self.load_and_process_all(github_repos=github_repos)
        return self.create_vectorstore(chunks, reset=reset)
    
    def show_docs_for_file(self, filename: str):  # pragma: no cover
        """
        Retrieve and print chunks from the vectorstore whose metadata['file_path'] ends with the
        given filename. Returns a list of (doc_id, metadata, document).
        
        DEBUG TOOL: Utility/debugging function - no corresponding FR/NFR.
        """
        all_docs = self.vectorstore.get()
        logger.info(f"Searching for chunks from file: {filename}")

        ids = all_docs.get("ids", [])
        metadatas = all_docs.get("metadatas", [])
        documents = all_docs.get("documents", [])

        matched = [
            (doc_id, metadata, doc)
            for doc_id, metadata, doc in zip(ids, metadatas, documents)
            if metadata.get("file_path", "").endswith(filename)
        ]

        logger.info(f"Found {len(matched)} chunks from {filename}:\n")
        for i, (doc_id, metadata, content) in enumerate(matched, 1):
            logger.info("=" * 100)
            logger.info(f"CHUNK {i}")
            logger.info(f"Metadata: {metadata}")
            logger.info("=" * 100)
            logger.info(content)
            logger.info("")
