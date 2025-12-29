import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Determine project root and env path
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

class Config(BaseSettings):
    headless: bool = Field(default=False)
    concurrency: int = Field(default=6)
    max_retries: int = Field(default=3)
    user_agents: str = Field(default="")
    
    proxy_server: Optional[str] = Field(default=None)
    proxy_list: str = Field(default="")  # Comma-separated list of proxies
    @property
    def proxy_strict_mode(self) -> bool:
        """Always return True to enforce strict proxy usage as required by delivery standards."""
        return True
    
    request_timeout_seconds: float = Field(default=30.0)
    navigation_timeout_ms: int = Field(default=45000)
    scroll_delay_ms: int = Field(default=600)
    max_scrolls: int = Field(default=8)
    video_limit_per_locale: int = Field(default=200)
    top_k: int = Field(default=10)
    output_dir: str = Field(default="out")
    youtube_api_key: str = Field(default="")
    
    # Database settings (Supabase)
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    use_database: bool = Field(default=False)
    
    # Dashboard settings
    dashboard_webhook_url: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

    @property
    def user_agents_list(self) -> List[str]:
        if not self.user_agents:
            return []
        return [ua.strip() for ua in self.user_agents.split(",") if ua.strip()]

def get_config() -> Config:
    return Config()
