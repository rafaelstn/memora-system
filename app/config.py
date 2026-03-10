from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://memora:memora@localhost:5432/memora"

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 100

    # LLM provider: "openai" ou "anthropic"
    llm_provider: str = "openai"

    anthropic_api_key: str = ""
    claude_model_fast: str = "claude-haiku-4-5-20251001"
    claude_model_deep: str = "claude-sonnet-4-6"

    openai_model_fast: str = "gpt-4.1-mini"
    openai_model_deep: str = "gpt-4.1"

    github_webhook_secret: str = ""

    # Encryption key for LLM provider API keys (Fernet)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    llm_encryption_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Auth / JWT (Supabase Auth JWT validation)
    jwt_algorithm: str = "HS256"

    usd_to_brl: float = 5.70

    # App URL (for notification links)
    app_url: str = "http://localhost:3000"

    # SMTP (for email notifications)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # CORS origins (comma-separated string from env var CORS_ORIGINS)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Master admin (plan management)
    master_admin_email: str = ""

    app_env: str = "development"
    log_level: str = "info"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
