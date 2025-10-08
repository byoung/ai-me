"""
Document loading, processing, and vectorstore management for ai-me application. Handles loading
from local directories and GitHub repositories, chunking, and creating ChromaDB vector stores.
"""
import os
from typing import List, Optional, Callable
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
import shutil
import re

class DataManager:
    """
    Consolidated document loading, processing, and vectorstore management. Handles the complete
    data pipeline from loading documents to creating a queryable vectorstore. Configuration
    parameters have sensible defaults and can be overridden as needed.
    """
    
    # Class-level configuration defaults. Compute doc_root relative to this file's parent dir.
    DEFAULT_DOC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs")) + "/"
    DEFAULT_CHUNK_SIZE = 2500
    DEFAULT_CHUNK_OVERLAP = 0
    DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_DB_NAME = "ai_me"
    
    def __init__(
        self,
        doc_load_local: List[str],
        github_repos: List[str] = None,
        doc_root: str = None,
        chunk_size: int = None,
        chunk_overlap: int = None,
        embedding_model: str = None,
        db_name: str = None,
    ):
        """
        Initialize data manager with configuration.
        
        Args:
            doc_load_local: Glob patterns for local docs (e.g., ["*.md"])
            github_repos: List of GitHub repos (format: owner/repo) (default: [])
            doc_root: Root directory for local documents (default: ./docs/)
            chunk_size: Character chunk size for splitting (default: 1200)
            chunk_overlap: Character overlap between chunks (default: 200)
            embedding_model: HuggingFace model (default: sentence-transformers/all-MiniLM-L6-v2)
            db_name: ChromaDB collection name (default: "ai_me")
        """
        self.doc_load_local = doc_load_local
        self.github_repos = github_repos or []
        self.doc_root = doc_root or self.DEFAULT_DOC_ROOT
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or self.DEFAULT_CHUNK_OVERLAP
        self.embedding_model = embedding_model or self.DEFAULT_EMBEDDING_MODEL
        self.db_name = db_name or self.DEFAULT_DB_NAME
        
        # Internal state
        self._vectorstore: Optional[Chroma] = None
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
    
    def load_local_documents(self) -> List[Document]:
        """
        Load documents from local directory. Returns empty list if directory not found.
        """
        print(f"Loading local documents from: {self.doc_root}")
        
        # Check if directory exists first
        if not os.path.exists(self.doc_root):
            print(f"Warning: Directory not found: {self.doc_root} - skipping local documents")
            return []
        
        all_documents = []
        
        # Iterate over all glob patterns
        for pattern in self.doc_load_local:
            try:
                print(f"  Loading pattern: {pattern}")
                loader = DirectoryLoader(
                    self.doc_root,
                    glob=pattern,
                    loader_cls=TextLoader,
                    loader_kwargs={'encoding': 'utf-8'}
                )
                documents = loader.load()
                print(f"    Found {len(documents)} documents")
                all_documents.extend(documents)
            except Exception as e:
                print(
                    f"  Error loading pattern {pattern}: {e}"
                    f" - skipping this pattern"
                )
                continue
        
        print(f"Loaded {len(all_documents)} total local documents.")
        return all_documents
    
    def load_github_documents(self, repos: List[str] = None,
        file_filter: Optional[Callable[[str], bool]] = None, cleanup_tmp: bool = True
    ) -> List[Document]:
        """
        Load documents from GitHub repositories.
        
        Args:
            repos: List of repos (owner/repo format). Defaults to github_repos from init.
            file_filter: Optional filter function for files. Defaults to .md files.
            cleanup_tmp: If True, remove tmp directory before loading.
        
        Returns:
            List of loaded documents from all repos.
        """
        if repos is None:
            repos = self.github_repos
        
        if file_filter is None:
            def file_filter(fp: str) -> bool:
                fp_lower = fp.lower()
                basename = os.path.basename(fp).lower()
                keep = (fp_lower.endswith(".md") and 
                    basename not in ["contributing.md", "code_of_conduct.md", "security.md", 
                                     "readme.md"])
                return keep
        
        all_docs = []
        # Clean up tmp directory before loading
        tmp_dir = "./tmp"

        if os.path.exists(tmp_dir) and cleanup_tmp:
            print(f"Cleaning up existing tmp directory: {tmp_dir}")
            shutil.rmtree(tmp_dir)

        print(f"Loading GitHub documents from {len(repos)} repos {repos}")
        for repo in repos:
            print(f"Loading GitHub repo: {repo}")
            try:
                loader = GitLoader(
                    clone_url=f"https://github.com/{repo}",
                    repo_path=f"{tmp_dir}/{repo}",
                    file_filter=file_filter,
                    branch="main",
                )
                docs = loader.load()
                
                # Add repo metadata to each document
                for doc in docs:
                    doc.metadata["github_repo"] = repo
                
                print(f"  Loaded {len(docs)} documents from {repo}")
                all_docs.extend(docs)
            except Exception as e:
                print(f"  Error loading repo {repo}: {e} - skipping")
                continue
        
        print(f"Loaded {len(all_docs)} total GitHub documents.")
        return all_docs
    
    def process_documents(self, docs: List[Document]) -> List[Document]:
        """
        Hydrate links in markdown documents to point to GitHub.
        
        Args:
            docs: List of documents to process
        
        Returns:
            List of processed documents
        """
        processed = []
        for doc in docs:
            print(f"Processing: {doc.metadata['source']}")
            
            # Fix baseless links to point to GitHub (if from a GitHub repo)
            if "github_repo" in doc.metadata:
                repo = doc.metadata["github_repo"]
                # First pass: fix absolute paths like /website/ or /docs/ typically used in short links
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
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents with both original metadata and header metadata
        """
        print(f"Chunking {len(documents)} documents...")
        
        # Define headers to split on (h1, h2, h3)
        headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
        header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, 
            strip_headers=False)
        
        all_chunks = []
        for doc in documents:
            # Split by headers first - this returns Documents with header metadata
            header_chunks = header_splitter.split_text(doc.page_content)
            
            # Convert to Documents and preserve original metadata + add header metadata
            for chunk in header_chunks:
                # Create new Document with combined metadata
                new_doc = Document(
                    page_content=chunk.page_content,
                    metadata={**doc.metadata, **chunk.metadata}  # Merge original + header metadata
                )
                all_chunks.append(new_doc)
        
        # Optional: Further split large chunks if they exceed size limit
        size_splitter = MarkdownTextSplitter(chunk_size=DataManager.DEFAULT_CHUNK_SIZE)
        final_chunks = size_splitter.split_documents(all_chunks)
        
        print(f"Created {len(final_chunks)} chunks")
        return final_chunks
    
    def load_and_process_all(self, github_repos: List[str] = None) -> List[Document]:
        """
        Load, process, and chunk all documents. Automatically loads local documents if 
        doc_load_local is set, and GitHub documents if github_repos (or self.github_repos) is set.
        
        Args:
            github_repos: Optional list of specific repos to load. Uses self.github_repos if None.
        
        Returns:
            List of processed and chunked documents.
        """
        all_docs = []
        
        # Load local documents if patterns are configured
        if self.doc_load_local:
            all_docs.extend(self.load_local_documents())
        
        # Load GitHub documents if repos are configured
        repos_to_load = github_repos if github_repos is not None else self.github_repos
        if repos_to_load:
            all_docs.extend(self.load_github_documents(repos=repos_to_load))
        
        processed_docs = self.process_documents(all_docs)
        chunks = self.chunk_documents(processed_docs)
        
        return chunks
    
    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """
        Get or create embeddings model.
        
        Returns:
            HuggingFace embeddings instance
        """
        if self._embeddings is None:
            print(f"Loading embeddings model: {self.embedding_model}")
            self._embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        return self._embeddings
    
    def create_vectorstore(self, chunks: List[Document], reset: bool = True) -> Chroma:
        """
        Create ChromaDB vectorstore from document chunks.
        
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
        if reset:
            try:
                chroma_client.delete_collection(self.db_name)
                print(f"Dropped existing collection: {self.db_name}")
            except Exception:
                pass  # Collection doesn't exist yet
        
        print(f"Creating vectorstore with {len(chunks)} chunks...")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            client=chroma_client,
            collection_name=self.db_name,
        )
        
        count = vectorstore._collection.count()
        print(f"Vectorstore created with {count} documents")
        
        self._vectorstore = vectorstore
        return vectorstore
    
    def setup_vectorstore(self, github_repos: List[str] = None, reset: bool = True) -> Chroma:
        """
        Complete pipeline: load, process, chunk, and create vectorstore. Automatically loads local
        documents if doc_load_local is set, and GitHub documents if github_repos is specified.
        
        Args:
            github_repos: Optional list of specific repos to load. Uses self.github_repos if None.
            reset: If True, drop existing collection before creating.
        
        Returns:
            Chroma vectorstore instance ready for queries.
        """
        print("Setting up vectorstore...")
        chunks = self.load_and_process_all(github_repos=github_repos)
        return self.create_vectorstore(chunks, reset=reset)
    
    def show_docs_for_file(self, filename: str):
        """
        Retrieve and print chunks from the vectorstore whose metadata['file_path'] ends with the
        given filename. Returns a list of (doc_id, metadata, document).
        """
        all_docs = self._vectorstore.get()
        print(f"Searching for chunks from file: {filename}")

        ids = all_docs.get("ids", [])
        metadatas = all_docs.get("metadatas", [])
        documents = all_docs.get("documents", [])

        matched = [
            (doc_id, metadata, doc)
            for doc_id, metadata, doc in zip(ids, metadatas, documents)
            if metadata.get("file_path", "").endswith(filename)
        ]

        print(f"Found {len(matched)} chunks from {filename}:\n")
        for i, (doc_id, metadata, content) in enumerate(matched, 1):
            print("=" * 100)
            print(f"CHUNK {i}")
            print(f"Metadata: {metadata}")
            print("=" * 100)
            print(content)
            print()

    @property
    def vectorstore(self) -> Optional[Chroma]:
        """Get the current vectorstore instance."""
        return self._vectorstore
