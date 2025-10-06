"""
Configuration management for ai-me application.
Centralizes environment variables, API clients, and application defaults.
"""
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_export_api_key


class MCPServerParams(BaseModel):
    """Type-safe MCP server parameters."""
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


class Config(BaseSettings):
    """Central configuration class for ai-me application with Pydantic validation."""
    
    # Environment Variables (from .env) - Required
    openai_api_key: str = Field(
        ..., description="OpenAI API key for tracing"
    )
    groq_api_key: str = Field(
        ..., description="Groq API key for LLM"
    )
    github_token: str = Field(
        ...,
        alias="github_personal_access_token",
        description="GitHub PAT",
    )
    
    # Optional Environment Variables
    bot_full_name: str = Field(
        default="Ben Young",
        description="Full name of the bot persona",
    )
    
    # Model Configuration
    model: str = Field(
        default="openai/openai/gpt-oss-120b",
        description="LLM model identifier",
    )
    
    # Document Loading
    doc_load_local: List[str] = Field(
        default=["**/*.md"],
        description="Glob patterns for local docs",
    )
    github_repos: List[str] = Field(
        default=["Neosofia/corporate", "byoung/me", "byoung/ai-me"],
        description="GitHub repos to load (format: owner/repo)",
    )
    
    # Agent Configuration
    agent_name: str = Field(
        default="ai_me",
        description="Name of the primary agent",
    )
    agent_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace embedding model",
    )
    
    # API Clients (excluded from Pydantic validation, set in model_post_init)
    openai_client: Optional[AsyncOpenAI] = Field(
        default=None,
        exclude=True,
        description="Groq OpenAI client",
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,  # Allow alias population
        extra="ignore",  # Ignore extra fields in .env
    )
    
    @property
    def mcp_github_params(self) -> MCPServerParams:
        """Generate MCP GitHub server parameters."""
        return MCPServerParams(
            command="docker",
            args=[
                "run", "-i", "--rm",
                "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/github/github-mcp-server"
            ],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token}
        )
    
    @property
    def mcp_time_params(self) -> MCPServerParams:
        """Generate MCP time server parameters."""
        return MCPServerParams(
            command="uvx",
            args=["mcp-server-time", "--local-timezone=Etc/UTC"],
            env=None
        )
    
    @property
    def mcp_params_list(self) -> List[Dict[str, Any]]:
        """MCP servers disabled by default (infinite loop issues)."""
        # Return empty list; change to enable:
        # [self.mcp_github_params.model_dump(), self.mcp_time_params.model_dump()]
        return []
    
    @property
    def agent_prompt(self) -> str:
        """Generate agent prompt template."""
        return f"""
You're acting as somebody who personifying {self.bot_full_name} and must follow these rules:
 * If the user asks a question, use the get_local_info tool to gather more info
 * Say you don't know if the get local info tool returns weak or no relevant info
 * don't offer follow up questions, just answer the question
 * Add inline references using shorthand links like '[1](link)' if they contain https://github.com
"""
    
    def model_post_init(self, __context) -> None:
        """Initialize after Pydantic validation."""
        # Set tokenizer parallelism
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Initialize Groq client for LLM operations
        self.openai_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.groq_api_key
        )
        set_default_openai_client(self.openai_client)
        
        # Set tracing API key AFTER setting default client
        print("Setting tracing export API key for agents.")
        set_tracing_export_api_key(self.openai_api_key)
    



def _load_config() -> Config:
    """Load configuration from environment variables using BaseSettings."""
    # BaseSettings automatically loads from .env file
    return Config()


# Global config instance (can be imported and used directly)
config = _load_config()
