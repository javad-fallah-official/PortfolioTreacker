"""
Wallex - A comprehensive Python library for Wallex cryptocurrency exchange

This package provides a modular interface to the Wallex API and WebSocket services.

Modules:
    - client: Main client interface
    - rest: REST API client
    - socket: WebSocket client for real-time data
    - types: Type definitions and constants
    - utils: Utility functions
    - exceptions: Custom exceptions
    - config: Configuration management
"""

__version__ = "1.0.0"
__author__ = "Wallex Python Client Team"
__email__ = "support@example.com"
__license__ = "MIT"

# Import main classes for easy access
from .client import WallexClient, WallexAsyncClient, create_client, create_async_client
from .config import WallexConfig
from .exceptions import WallexAPIError, WallexWebSocketError
from .types import OrderSide, OrderType, OrderStatus, CommonSymbols

# Import submodules
from . import rest
from . import socket
from . import utils
from . import types

__all__ = [
    # Main classes
    "WallexClient",
    "WallexAsyncClient",
    "create_client",
    "create_async_client",
    "WallexConfig", 
    "WallexAPIError",
    "WallexWebSocketError",
    
    # Types
    "OrderSide",
    "OrderType", 
    "OrderStatus",
    "CommonSymbols",
    
    # Submodules
    "rest",
    "socket",
    "utils",
    "types",
]

# Package metadata
__package_info__ = {
    "name": "wallex",
    "version": __version__,
    "description": "A comprehensive Python library for Wallex cryptocurrency exchange",
    "author": __author__,
    "author_email": __email__,
    "license": __license__,
    "url": "https://github.com/wallex/wallex-python-client",
    "keywords": ["wallex", "cryptocurrency", "trading", "api", "websocket"],
}