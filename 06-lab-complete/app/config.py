"""Production config: 12-factor settings from environment variables."""
import logging
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    allowed_origins: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    def validate(self):
        logger = logging.getLogger(__name__)
        if self.environment == "production" and self.agent_api_key == "dev-key-change-me":
            raise ValueError("AGENT_API_KEY must be set in production.")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set; using mock LLM")
        return self


settings = Settings().validate()
