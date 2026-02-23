"""
Configuration management for Fluency AI Research Agent.

Loads configuration from environment variables with sensible defaults.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


def _load_dotenv():
    """Load .env file - uses python-dotenv if available, otherwise manual loading."""
    env_path = Path(__file__).parent / ".env"

    # Try python-dotenv first
    try:
        from dotenv import load_dotenv
        if env_path.exists():
            load_dotenv(env_path)
            return
    except ImportError:
        pass  # python-dotenv not installed

    # Fallback: manually parse .env file
    if env_path.exists():
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        # Only set if not already in environment
                        if key and key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass  # If we can't read .env, continue with environment variables


# Load .env file on module import
_load_dotenv()


# Model routing for cost optimization
# Sonnet for complex reasoning, Haiku for data gathering
AGENT_MODELS = {
    # Complex reasoning - use Opus for nuanced judgment
    "Synthesis": "claude-opus-4-20250514",
    "ImplementationRisk": "claude-opus-4-20250514",
    "ExecutiveBrief": "claude-opus-4-20250514",
    "BriefRefiner": "claude-opus-4-20250514",
    # Data gathering agents - use Sonnet
    "Discovery": "claude-sonnet-4-20250514",
    "RegulatoryRisk": "claude-sonnet-4-20250514",
    # All agents use Sonnet 4 for web_search support
    # TODO: Use cheaper model for agents without web_search when Haiku supports it
    "default": "claude-sonnet-4-20250514",
}


def get_model_for_agent(agent_name: str) -> str:
    """Get the appropriate model for an agent based on its complexity."""
    return AGENT_MODELS.get(agent_name, AGENT_MODELS["default"])


# Agent-specific tool call limits to prevent over-fetching
# Lower limits = fewer API calls, faster execution
AGENT_TOOL_LIMITS = {
    "Discovery": 25,        # Needs more calls to build comprehensive URL bank
    "Synthesis": 5,         # Mostly pure reasoning, minimal tools
    "ExecutiveBrief": 5,    # Pure reasoning
    "BriefRefiner": 5,      # Pure reasoning
    "Security": 10,         # Focused research
    "TechStack": 12,        # Needs crt_sh + marketplace checks
    "Strategic": 10,        # News fetching
    "JobPostings": 10,      # Job board scraping
    "CustomerReviews": 8,   # Review site scraping
    "RegulatoryRisk": 12,   # Multiple regulatory database checks
    "StakeholderIntel": 10, # LinkedIn + leadership pages
    "LinkedInIntel": 8,     # LinkedIn focused
    "OperationalCulture": 8,
    "ShadowIT": 8,
    "LocalRegulations": 8,
    "Procurement": 8,
    "ImplementationRisk": 8,
    "Financials": 10,       # SEC filings
    "default": 12,          # Reasonable default
}


def get_tool_limit_for_agent(agent_name: str) -> int:
    """Get the appropriate tool call limit for an agent."""
    return AGENT_TOOL_LIMITS.get(agent_name, AGENT_TOOL_LIMITS["default"])


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # API Configuration
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    model: str = field(default_factory=lambda: os.environ.get("MODEL", "claude-sonnet-4-20250514"))

    # Output Configuration
    output_dir: str = field(default_factory=lambda: os.environ.get("OUTPUT_DIR", "results"))

    # Logging Configuration
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    log_format: str = field(
        default_factory=lambda: os.environ.get(
            "LOG_FORMAT",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )

    # Rate Limiting
    max_retries: int = field(default_factory=lambda: int(os.environ.get("MAX_RETRIES", "5")))
    initial_backoff: int = field(default_factory=lambda: int(os.environ.get("INITIAL_BACKOFF", "30")))
    agent_delay: int = field(default_factory=lambda: int(os.environ.get("AGENT_DELAY", "30")))

    # Verbose output (for CLI)
    verbose: bool = field(default_factory=lambda: os.environ.get("VERBOSE", "").lower() in ("true", "1", "yes"))

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            self.log_level = "INFO"
        self.log_level = self.log_level.upper()

    def get_log_level(self) -> int:
        """Get the logging level as an integer."""
        return getattr(logging, self.log_level, logging.INFO)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config):
    """Set the global configuration instance."""
    global _config
    _config = config
