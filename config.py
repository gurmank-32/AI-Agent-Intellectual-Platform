from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SMTP_EMAIL: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[str] = None

    LEGAL_DISCLAIMER: str = (
        "⚠️ This tool is for informational purposes only. It is not legal advice. "
        "Consult qualified legal counsel before making decisions."
    )

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_smtp(self) -> bool:
        return bool(
            self.SMTP_EMAIL
            and self.SMTP_PASSWORD
            and self.SMTP_HOST
            and self.SMTP_PORT
        )


settings = Settings()

# Canonical, stable import path used across the app.
LEGAL_DISCLAIMER: str = settings.LEGAL_DISCLAIMER

