"""
Configuration management for ai-me application.
Centralizes environment variables, API clients, and application defaults.
"""
import os
import logging
import socket
from typing import Optional, List, Union
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_export_api_key
from logging_loki import LokiHandler
from dotenv import load_dotenv

# Load .env file early so logger setup can access environment variables
load_dotenv()


def setup_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger with consistent syslog-style formatting.
    
    Implements NFR-003 (Structured Logging).
    
    Multi-line messages will have continuation lines indented for readability.
    
    Log level can be controlled via LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR).
    Defaults to INFO if not set.
    
    Remote logging to Grafana Loki can be enabled by setting:
    - LOKI_URL: Grafana Loki endpoint (e.g., https://logs-prod-us-central1.grafana.net)
    - LOKI_USERNAME: Grafana Cloud username (typically a number)
    - LOKI_PASSWORD: Grafana Cloud API key
    
    Format: <timestamp> <hostname> <process>[<pid>]: <level> <message>
    Example: Oct 20 14:30:45 hostname python[12345]: INFO Message here
             Oct 20 14:30:45 hostname python[12345]:      continuation line
    
    Args:
        name: The name of the logger (typically __name__ from the calling module)
    
    Returns:
        A configured logger instance
    """
    # Configure root logger if not already configured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        # Get log level from environment variable, default to INFO
        log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_name, logging.INFO)
        
        # Custom formatter that indents multi-line messages
        fmt = '%(asctime)s %(hostname)s %(name)s[%(process)d]: %(levelname)s %(message)s'
        formatter = logging.Formatter(fmt, datefmt='%b %d %H:%M:%S')
        original_format = formatter.format
        formatter.format = lambda record: (
            lambda s: s if '\n' not in s else 
            '\n'.join([s.split('\n')[0]] + [' ' * (s.index(': ') + 2) + line 
                      for line in s.split('\n')[1:]])
        )(original_format(record))
        
        # Console handler (always present)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        # Add hostname to records via filter on handler
        console_handler.addFilter(
            lambda record: setattr(record, 'hostname', socket.gethostname()) or True
        )
        root_logger.addHandler(console_handler)
        
        # Grafana Loki handler (optional, for remote logging)
        loki_url = os.getenv('LOKI_URL')
        loki_username = os.getenv('LOKI_USERNAME')
        loki_password = os.getenv('LOKI_PASSWORD')
        
        if loki_url and loki_username and loki_password:
            try:
                # Create async queue for non-blocking logging
                log_queue = Queue(maxsize=1000)  # Buffer up to 1000 log messages
                
                # Loki handler processes logs from queue in background thread
                loki_tags = {
                    "application": "ai-me",
                    "environment": os.getenv('ENV', 'production'),
                }
                loki_handler = LokiHandler(
                    url=f"{loki_url}/loki/api/v1/push",
                    tags=loki_tags,
                    auth=(loki_username, loki_password),
                    version="1",
                )
                # Prevent Loki errors from propagating and causing logging loops
                loki_handler.handleError = lambda record: None
                
                # QueueListener processes logs asynchronously in background
                queue_listener = QueueListener(
                    log_queue,
                    loki_handler,
                    respect_handler_level=True,
                )
                queue_listener.start()
                
                # QueueHandler sends logs to queue without blocking
                queue_handler = QueueHandler(log_queue)
                root_logger.addHandler(queue_handler)
                
                root_logger.info(f"Grafana Loki logging enabled: {loki_url} (tags: {loki_tags})")
            except Exception as e:
                root_logger.warning(f"Failed to setup Grafana Loki logging: {e}")
        else:
            missing = []
            if not loki_url:
                missing.append("LOKI_URL")
            if not loki_username:
                missing.append("LOKI_USERNAME")
            if not loki_password:
                missing.append("LOKI_PASSWORD")
            if missing:
                root_logger.info(f"Loki logging disabled (missing: {', '.join(missing)})")
        
        root_logger.setLevel(log_level)
    
    logger = logging.getLogger(name)
    return logger

# Initialize module-level logger
logger = setup_logger(__name__)

class Config(BaseSettings):
    """Central configuration class for ai-me application with Pydantic validation."""
    
    # Environment Variables (from .env) - Required
    openai_api_key: SecretStr = Field(..., 
        description="OpenAI API key for tracing")
    groq_api_key: SecretStr = Field(..., 
        description="Groq API key for inference")
    github_token: Optional[SecretStr] = Field(
        default=None,
        alias="GITHUB_PERSONAL_ACCESS_TOKEN",
        description="GitHub PAT for MCP servers (optional, not needed for testing)")

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
    github_repos: Union[str, List[str]] = Field(
        default="",
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
        env_ignore_empty=True,  # Ignore empty env vars
        # Explicitly read from environment variables first, then .env file
        # This ensures GitHub Actions and other CI environments work
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
        logger.info("Setting tracing export API key for agents.")
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
        """Return string representation of Config with secrets hidden.
        
        DEBUG: Debug utility for logging/debugging configuration state.
        """
        return self._safe_repr()
    
    def __str__(self) -> str:
        """Return human-readable string representation of Config with secrets hidden.
        
        DEBUG: Debug utility for logging/debugging configuration state.
        """
        return self._safe_repr()
