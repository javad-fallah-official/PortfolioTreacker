"""
Wallex Configuration Module

This module handles configuration management for the Wallex library.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class WallexConfig:
    """
    Configuration class for Wallex API client
    
    Attributes:
        base_url: Base URL for Wallex API
        api_key: API key for authenticated endpoints
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        retry_delay: Delay between retries in seconds
        rate_limit: Maximum requests per minute
        testnet: Whether to use testnet environment
        log_level: Logging level
        user_agent: Custom user agent string
    """
    base_url: str = "https://api.wallex.ir"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: int = 1200
    testnet: bool = False
    log_level: str = "INFO"
    user_agent: str = "Wallex-Python-Client/1.0.0"
    
    # WebSocket specific settings
    ws_url: Optional[str] = None
    ws_timeout: int = 60
    ws_reconnect: bool = True
    ws_reconnect_attempts: int = 0  # 0 = infinite
    ws_reconnect_delay: float = 1.0
    ws_reconnect_delay_max: float = 5.0
    
    # Additional settings
    verify_ssl: bool = True
    proxy: Optional[Dict[str, str]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup"""
        # Set WebSocket URL if not provided
        if self.ws_url is None:
            if self.testnet:
                self.ws_url = "wss://testnet-api.wallex.ir"
            else:
                self.ws_url = "wss://api.wallex.ir"
        
        # Load from environment variables if not set
        self._load_from_env()
        
        # Validate configuration
        self._validate()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        env_mappings = {
            'WALLEX_API_KEY': 'api_key',
            'WALLEX_BASE_URL': 'base_url',
            'WALLEX_WS_URL': 'ws_url',
            'WALLEX_TIMEOUT': ('timeout', int),
            'WALLEX_MAX_RETRIES': ('max_retries', int),
            'WALLEX_RETRY_DELAY': ('retry_delay', float),
            'WALLEX_RATE_LIMIT': ('rate_limit', int),
            'WALLEX_TESTNET': ('testnet', lambda x: x.lower() in ('true', '1', 'yes')),
            'WALLEX_LOG_LEVEL': 'log_level',
            'WALLEX_USER_AGENT': 'user_agent',
            'WALLEX_WS_TIMEOUT': ('ws_timeout', int),
            'WALLEX_VERIFY_SSL': ('verify_ssl', lambda x: x.lower() in ('true', '1', 'yes')),
        }
        
        for env_var, config_attr in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if isinstance(config_attr, tuple):
                    attr_name, converter = config_attr
                    # Only set from environment if current value is the default
                    current_value = getattr(self, attr_name)
                    default_value = self.__dataclass_fields__[attr_name].default
                    if current_value == default_value:
                        try:
                            setattr(self, attr_name, converter(env_value))
                        except (ValueError, TypeError):
                            pass  # Keep default value if conversion fails
                else:
                    # Only set from environment if current value is the default
                    current_value = getattr(self, config_attr)
                    default_value = self.__dataclass_fields__[config_attr].default
                    if current_value == default_value:
                        setattr(self, config_attr, env_value)
    
    def _validate(self):
        """Validate configuration values"""
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        
        if self.retry_delay < 0:
            raise ValueError("Retry delay must be non-negative")
        
        if self.rate_limit <= 0:
            raise ValueError("Rate limit must be positive")
        
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("Base URL must start with http:// or https://")
        
        if self.ws_url and not self.ws_url.startswith(('ws://', 'wss://')):
            raise ValueError("WebSocket URL must start with ws:// or wss://")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'WallexConfig':
        """
        Load configuration from a file
        
        Args:
            config_path: Path to configuration file (JSON or TOML)
            
        Returns:
            WallexConfig instance
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        if config_file.suffix.lower() == '.json':
            import json
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        elif config_file.suffix.lower() == '.toml':
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib
            
            with open(config_file, 'rb') as f:
                config_data = tomllib.load(f)
        else:
            raise ValueError("Configuration file must be JSON or TOML format")
        
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> 'WallexConfig':
        """
        Create configuration from environment variables only
        
        Returns:
            WallexConfig instance
        """
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary
        
        Returns:
            Configuration as dictionary
        """
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    def update(self, **kwargs):
        """
        Update configuration with new values
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")
        
        # Re-validate after update
        self._validate()
    
    def copy(self) -> 'WallexConfig':
        """
        Create a copy of the configuration
        
        Returns:
            New WallexConfig instance
        """
        return WallexConfig(**self.to_dict())


# Default configuration instance
default_config = WallexConfig()


def get_config() -> WallexConfig:
    """
    Get the default configuration instance
    
    Returns:
        Default WallexConfig instance
    """
    return default_config


def set_config(config: WallexConfig):
    """
    Set the default configuration instance
    
    Args:
        config: New default configuration
    """
    global default_config
    default_config = config


def load_config_from_file(config_path: str) -> WallexConfig:
    """
    Load configuration from file and set as default
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Loaded configuration
    """
    config = WallexConfig.from_file(config_path)
    set_config(config)
    return config