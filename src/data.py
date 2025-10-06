"""
Document loading, processing, and vectorstore management for ai-me application.
Handles loading from local directories and GitHub repositories, chunking,
and creating ChromaDB vectorstores.
"""
import os
from typing import List, Optional, Callable
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    GitLoader,
)
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings
import shutil

class DataManager:
    """
    Consolidated document loading, processing, and vectorstore management.
    
    Handles the complete data pipeline from loading documents to creating
    a queryable vectorstore. Configuration parameters have sensible defaults
    and can be overridden as needed.
    """
    
    # Class-level configuration defaults
    # Compute doc_root relative to this file's parent directory
    DEFAULT_DOC_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "docs")
    ) + "/"
    DEFAULT_CHUNK_SIZE = 1200
    DEFAULT_CHUNK_OVERLAP = 200
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
            github_repos: List of GitHub repos (format: owner/repo)
                         (default: [])
            doc_root: Root directory for local documents 
                     (default: ./docs/)
            chunk_size: Character chunk size for splitting 
                       (default: 1200)
            chunk_overlap: Character overlap between chunks 
                          (default: 200)
            embedding_model: HuggingFace embedding model name
                            (default: sentence-transformers/all-MiniLM-L6-v2)
            db_name: ChromaDB collection name 
                    (default: "ai_me")
        """
        self.doc_load_local = doc_load_local
        self.github_repos = github_repos or []
        self.doc_root = doc_root or self.DEFAULT_DOC_ROOT
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or self.DEFAULT_CHUNK_OVERLAP
        self.embedding_model = (
            embedding_model or self.DEFAULT_EMBEDDING_MODEL
        )
        self.db_name = db_name or self.DEFAULT_DB_NAME
        
        # Derived properties
        self.doc_type = os.path.basename(self.doc_root)
        
        # Internal state
        self._vectorstore: Optional[Chroma] = None
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
    
    def load_local_documents(self) -> List[Document]:
        """
        Load documents from local directory.
        
        Returns:
            List of loaded documents (empty list if directory not found)
        """
        print(f"Loading local documents from: {self.doc_root}")
        
        # Check if directory exists first
        if not os.path.exists(self.doc_root):
            print(
                f"Warning: Directory not found: {self.doc_root}"
                f" - skipping local documents"
            )
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
    
    def load_github_documents(
        self,
        repos: List[str] = None,
        file_filter: Optional[Callable[[str], bool]] = None
    ) -> List[Document]:
        """
        Load documents from GitHub repositories.
        
        Args:
            repos: List of repos (owner/repo format). 
                   Defaults to github_repos from init
            file_filter: Optional filter function for files.
                        Defaults to .md files in website/ paths
        
        Returns:
            List of loaded documents from all repos
        """
        if repos is None:
            repos = self.github_repos
        
        if file_filter is None:
            file_filter = lambda fp: fp.endswith(".md")
        
        all_docs = []
        # Clean up tmp directory before loading
        tmp_dir = "./tmp"

        if os.path.exists(tmp_dir):
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
        Process documents by adding metadata and fixing links.
        
        Args:
            docs: List of documents to process
        
        Returns:
            List of processed documents
        """
        processed = []
        for doc in docs:
            print(f"Processing: {doc.metadata['source']}")
            doc.metadata["doc_type"] = self.doc_type
            
            # Fix baseless links to point to GitHub (if from a GitHub repo)
            if "github_repo" in doc.metadata:
                repo = doc.metadata["github_repo"]
                # Replace relative paths like /website/ or /docs/ 
                # with full GitHub URLs
                import re
                # Find patterns like /path/ at start of line or after spaces
                doc.page_content = re.sub(
                    r'(\s|^)(/[a-zA-Z0-9_-]+/)',
                    rf'\1https://github.com/{repo}/tree/main\2',
                    doc.page_content
                )
                            
            processed.append(doc)
        
        return processed
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks for better retrieval.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents
        """
        print(f"Chunking {len(documents)} documents...")
        
        text_splitter = CharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separator="\n"
        )
        
        chunks = text_splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks")
        return chunks
    
    def load_and_process_all(
        self,
        include_local: bool = True,
        include_github: bool = True,
        github_repos: List[str] = None
    ) -> List[Document]:
        """
        Load, process, and chunk all documents.
        
        Args:
            include_local: Whether to load local documents
            include_github: Whether to load GitHub documents
            github_repos: Optional list of specific repos to load
        
        Returns:
            List of processed and chunked documents
        """
        all_docs = []
        
        if include_local:
            all_docs.extend(self.load_local_documents())
        
        if include_github:
            all_docs.extend(self.load_github_documents(repos=github_repos))
        
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
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model
            )
        return self._embeddings
    
    def create_vectorstore(
        self,
        chunks: List[Document],
        reset: bool = True
    ) -> Chroma:
        """
        Create ChromaDB vectorstore from document chunks.
        
        Args:
            chunks: List of document chunks to store
            reset: If True, drop existing collection before creating
        
        Returns:
            Chroma vectorstore instance
        """
        embeddings = self.get_embeddings()
        
        # Use EphemeralClient for faster in-memory storage
        chroma_client = chromadb.EphemeralClient(
            Settings(anonymized_telemetry=False)
        )
        
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
    
    def setup_vectorstore(
        self,
        include_local: bool = True,
        include_github: bool = True,
        github_repos: List[str] = None,
        reset: bool = True
    ) -> Chroma:
        """
        Complete pipeline: load, process, chunk, and create vectorstore.
        
        Args:
            include_local: Whether to load local documents
            include_github: Whether to load GitHub documents
            github_repos: Optional list of specific repos to load
            reset: If True, drop existing collection before creating
        
        Returns:
            Chroma vectorstore instance ready for queries
        """
        print("Setting up vectorstore...")
        chunks = self.load_and_process_all(
            include_local=include_local,
            include_github=include_github,
            github_repos=github_repos
        )
        return self.create_vectorstore(chunks, reset=reset)
    
    @property
    def vectorstore(self) -> Optional[Chroma]:
        """Get the current vectorstore instance."""
        return self._vectorstore
