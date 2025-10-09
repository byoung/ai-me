"""
Configuration management for ai-me application.
Centralizes environment variables, API clients, and application defaults.
"""
import os
from typing import Optional, List, Union
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_export_api_key

class Config(BaseSettings):
    """Central configuration class for ai-me application with Pydantic validation."""
    
    # Environment Variables (from .env) - Required
    openai_api_key: SecretStr = Field(..., 
        description="OpenAI API key for tracing")
    groq_api_key: SecretStr = Field(..., 
        description="Groq API key for inference")
    github_token: SecretStr = Field(...,
        alias="github_personal_access_token",
        description="GitHub PAT")

    bot_full_name: str = Field(
        default="AI ME -- set BOT_FULL_NAME in .env file", 
        description="Full name of the bot persona")
    app_name: str = Field(
        default="MeBot -- set APP_NAME in .env file",
        description="Name of the primary agent")
    model: str = Field(
        default="openai/openai/gpt-oss-120b",
        description="LLM model identifier")
    temperature: float = Field(
        default=1.0,
        description="LLM temperature for sampling (0.0-2.0, default 1.0)")
    doc_load_local: List[str] = Field(
        default=["**/*.md"],
        description="Glob patterns for local docs")
    github_repos: Union[str, List[str]] = Field(
        description="GitHub repos to load (format: owner/repo), comma-separated in .env")
    
    @field_validator("github_repos", mode="after")
    @classmethod
    def parse_github_repos(cls, v):
        """Parse comma-separated string from environment variable."""
        if isinstance(v, str):
            # Handle empty string
            if not v.strip():
                return []
            return [repo.strip() for repo in v.split(",") if repo.strip()]
        # Already a list
        return v
        
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
    
    def model_post_init(self, __context) -> None:
        """Initialize after Pydantic validation."""
        # Set tokenizer parallelism
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Initialize Groq client for LLM operations
        self.openai_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.groq_api_key.get_secret_value(),
            default_query={"temperature": self.temperature}
        )
        set_default_openai_client(self.openai_client)
        
        # Set tracing API key AFTER setting default client
        print("Setting tracing export API key for agents.")
        set_tracing_export_api_key(self.openai_api_key.get_secret_value())
    
    def _safe_repr(self) -> str:
        """Helper to generate string representation excluding sensitive fields."""
        lines = ["Config:"]
        for field_name in type(self).model_fields:
            value = getattr(self, field_name, None)
            # Check if the actual value is a SecretStr instance
            display = "<hidden>" if isinstance(value, SecretStr) else repr(value)
            lines.append(f"  {field_name}: {display}")
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return self._safe_repr()
    
    def __str__(self) -> str:
        return self._safe_repr()
