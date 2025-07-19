# Configuration Management Enhancements

from pydantic import BaseSettings, Field
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # API Configuration
    wallex_api_key: str = Field(..., env="WALLEX_API_KEY")
    wallex_base_url: str = Field("https://api.wallex.ir", env="WALLEX_BASE_URL")
    
    # Server Configuration
    host: str = Field("127.0.0.1", env="HOST")
    port: int = Field(8000, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    reload: bool = Field(True, env="RELOAD")
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(30, env="CACHE_TTL_SECONDS")
    enable_cache: bool = Field(True, env="ENABLE_CACHE")
    
    # Rate Limiting
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(60, env="RATE_LIMIT_WINDOW")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # Security
    allowed_origins: list = Field(["http://localhost:8000"], env="ALLOWED_ORIGINS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Environment-specific configurations
class DevelopmentSettings(Settings):
    debug: bool = True
    reload: bool = True
    log_level: str = "DEBUG"

class ProductionSettings(Settings):
    debug: bool = False
    reload: bool = False
    log_level: str = "WARNING"

def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()

# Usage example:
# settings = get_settings()
# app = FastAPI(debug=settings.debug)