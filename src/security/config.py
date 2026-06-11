from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

class Settings(BaseSettings):
    # L1 Auth (Polygon Wallet)
    PRIVATE_KEY: SecretStr = Field(..., description="EVM Private Key for Gnosis Safe / Signing")
    
    # L2 Auth (Polymarket API Credentials)
    POLYMARKET_API_KEY: str = Field(..., description="Polymarket API Key")
    POLYMARKET_API_SECRET: SecretStr = Field(..., description="Polymarket API Secret")
    POLYMARKET_API_PASSPHRASE: SecretStr = Field(..., description="Polymarket API Passphrase")
    
    # Environment Configuration
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # External APIs
    FINNHUB_API_KEY: SecretStr = Field(..., description="API Key for real-time news")
    
    # Strategy Config
    DAILY_DRAWDOWN_LIMIT: float = 0.10  # 10% max loss per day
    MAX_POSITION_SIZE: float = 20.0     # $20 per trade for bootstrap
    GLOBAL_KILL_SWITCH: bool = False    # Emergency halt
    
    # Gnosis Safe / Signature Config
    SIGNATURE_TYPE: int = 2             # 0=EOA, 1=Magic, 2=Gnosis Safe
    SAFE_ADDRESS: Optional[str] = Field(None, description="The address of your Gnosis Safe")
    
    # Path to persistent state (for drawdown tracking)
    STATE_FILE: str = "logs/state.json"
    
    # Discord Integration
    DISCORD_TOKEN: Optional[str] = Field(None, alias="DISCORD_TOKEN")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='ignore')

def get_settings() -> Settings:
    return Settings()
