from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings and environment variable validation.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Polymarket V3 Credentials
    poly_key_id: Optional[str] = Field(None, alias="POLYMARKET_KEY_ID")
    poly_secret_key: Optional[SecretStr] = Field(None, alias="POLYMARKET_SECRET_KEY")
    poly_passphrase: Optional[SecretStr] = Field(None, alias="POLYMARKET_PASSPHRASE")
    
    # Global Trading Controls
    max_daily_loss: float = Field(5.0, description="Max daily loss percentage")
    default_strategy: str = "negative_risk"
    log_level: str = "INFO"
    
    # Wallet Settings (L1)
    private_key: Optional[SecretStr] = Field(None, alias="PRIVATE_KEY")

settings = Settings()
