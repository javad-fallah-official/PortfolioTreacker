"""
Wallex Main Client Module

This module provides the main client interface that combines REST and WebSocket functionality.
"""

from typing import Optional, Dict, Any
import logging

from .config import WallexConfig, get_config
from .rest import WallexRestClient
from .socket import WallexWebSocketClient, WallexAsyncWebSocketClient
from .exceptions import WallexError, WallexConfigurationError


class WallexClient:
    """
    Main Wallex Client
    
    Combines REST API and WebSocket functionality in a single interface.
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[WallexConfig] = None, **kwargs):
        """
        Initialize Wallex client
        
        Args:
            api_key: API key for authenticated endpoints or WallexConfig if passed positionally
            config: Configuration object (optional)
            **kwargs: Additional configuration parameters
        """
        # Support passing WallexConfig as first positional argument
        if isinstance(api_key, WallexConfig) and config is None:
            config = api_key
            api_key = None
        
        # Create or update configuration
        if config is None:
            config = get_config().copy()
        
        # Update config with provided parameters
        if api_key:
            config.api_key = api_key
        
        # Update config with any additional kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logging.warning(f"Unknown configuration parameter: {key}")
        
        self.config = config
        
        # Initialize REST and WebSocket clients
        self.rest = WallexRestClient(self.config)
        self.websocket = WallexWebSocketClient(self.config)
        
        # Track connection state
        self._ws_connected = False
    
    @property
    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket.is_connected
    
    def connect_websocket(self, timeout: Optional[int] = None) -> bool:
        """
        Connect to WebSocket server
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        try:
            result = self.websocket.connect(timeout)
            self._ws_connected = result
            return result
        except Exception as e:
            logging.error(f"Failed to connect WebSocket: {e}")
            return False
    
    def disconnect_websocket(self):
        """Disconnect from WebSocket server"""
        try:
            self.websocket.disconnect()
            self._ws_connected = False
        except Exception as e:
            logging.error(f"Error disconnecting WebSocket: {e}")
    
    # REST API convenience methods
    
    def get_markets(self) -> Dict:
        """Get list of all available markets"""
        return self.rest.get_markets()
    
    def get_market_stats(self, symbol: str) -> Dict:
        """Get market statistics for a symbol"""
        return self.rest.get_market_stats(symbol)
    
    def get_orderbook(self, symbol: str) -> Dict:
        """Get order book for a symbol"""
        return self.rest.get_orderbook(symbol)
    
    def get_trades(self, symbol: str, limit: Optional[int] = None) -> Dict:
        """Get recent trades for a symbol"""
        return self.rest.get_trades(symbol, limit)
    
    def get_currencies(self) -> Dict:
        """Get list of supported currencies"""
        return self.rest.get_currencies()
    
    def get_account_info(self) -> Dict:
        """Get account information (requires API key)"""
        return self.rest.get_account_info()
    
    def get_balances(self) -> Dict:
        """Get account balances (requires API key)"""
        return self.rest.get_balances()
    
    def get_balance(self, currency: str) -> Dict:
        """Get balance for specific currency (requires API key)"""
        return self.rest.get_balance(currency)
    
    def create_order(self, symbol: str, side: str, order_type: str, quantity: float,
                    price: Optional[float] = None, **kwargs) -> Dict:
        """Create a new order (requires API key)"""
        return self.rest.create_order(symbol, side, order_type, quantity, price, **kwargs)
    
    def get_orders(self, **kwargs) -> Dict:
        """Get list of orders (requires API key)"""
        return self.rest.get_orders(**kwargs)
    
    def get_order(self, order_id: str) -> Dict:
        """Get specific order (requires API key)"""
        return self.rest.get_order(order_id)
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel specific order (requires API key)"""
        return self.rest.cancel_order(order_id)
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict:
        """Cancel all orders (requires API key)"""
        return self.rest.cancel_all_orders(symbol)
    
    # WebSocket convenience methods
    
    def subscribe_trades(self, symbol: str, callback):
        """Subscribe to trade updates"""
        if not self.is_websocket_connected:
            self.connect_websocket()
        self.websocket.subscribe_trades(symbol, callback)
    
    def subscribe_orderbook(self, symbol: str, callback):
        """Subscribe to order book updates"""
        if not self.is_websocket_connected:
            self.connect_websocket()
        self.websocket.subscribe_orderbook(symbol, callback)
    
    def subscribe_ticker(self, symbol: str, callback):
        """Subscribe to ticker updates"""
        if not self.is_websocket_connected:
            self.connect_websocket()
        self.websocket.subscribe_ticker(symbol, callback)
    
    def subscribe_market_cap(self, symbol: str, callback):
        """Subscribe to market cap updates"""
        if not self.is_websocket_connected:
            self.connect_websocket()
        self.websocket.subscribe_market_cap(symbol, callback)
    
    def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        self.websocket.unsubscribe(channel)
    
    def unsubscribe_all(self):
        """Unsubscribe from all channels"""
        self.websocket.unsubscribe_all()
    
    # Context manager support
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.is_websocket_connected:
            self.disconnect_websocket()
    
    # Configuration management
    
    def update_config(self, **kwargs):
        """
        Update client configuration
        
        Args:
            **kwargs: Configuration parameters to update
        """
        try:
            self.config.update(**kwargs)
            
            # Recreate clients with new config
            self.rest = WallexRestClient(self.config)
            
            # Disconnect and recreate WebSocket client if connected
            if self.is_websocket_connected:
                self.disconnect_websocket()
                self.websocket = WallexWebSocketClient(self.config)
            else:
                self.websocket = WallexWebSocketClient(self.config)
                
        except Exception as e:
            raise WallexConfigurationError(f"Failed to update configuration: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration as dictionary"""
        return self.config.to_dict()


class WallexAsyncClient:
    """
    Async version of Wallex Client
    
    Provides async/await interface for both REST and WebSocket operations.
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[WallexConfig] = None, **kwargs):
        """
        Initialize async Wallex client
        
        Args:
            api_key: API key for authenticated endpoints or WallexConfig if passed positionally
            config: Configuration object (optional)
            **kwargs: Additional configuration parameters
        """
        # Support passing WallexConfig as first positional argument
        if isinstance(api_key, WallexConfig) and config is None:
            config = api_key
            api_key = None
        
        # Create or update configuration
        if config is None:
            config = get_config().copy()
        
        # Update config with provided parameters
        if api_key:
            config.api_key = api_key
        
        # Update config with any additional kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.config = config
        
        # Initialize clients
        self.rest = WallexRestClient(self.config)
        self.websocket = WallexAsyncWebSocketClient(self.config)
    
    @property
    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket.is_connected
    
    async def connect_websocket(self, timeout: Optional[int] = None) -> bool:
        """Connect to WebSocket server (async)"""
        return await self.websocket.connect(timeout)
    
    async def disconnect_websocket(self):
        """Disconnect from WebSocket server (async)"""
        await self.websocket.disconnect()
    
    # Async WebSocket methods
    
    async def subscribe_trades(self, symbol: str, callback):
        """Subscribe to trade updates (async)"""
        if not self.is_websocket_connected:
            await self.connect_websocket()
        await self.websocket.subscribe_trades(symbol, callback)
    
    async def subscribe_orderbook(self, symbol: str, callback):
        """Subscribe to order book updates (async)"""
        if not self.is_websocket_connected:
            await self.connect_websocket()
        await self.websocket.subscribe_orderbook(symbol, callback)
    
    # Async context manager
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.is_websocket_connected:
            await self.disconnect_websocket()


# Factory functions

def create_client(api_key: Optional[str] = None, **kwargs) -> WallexClient:
    """
    Create a new Wallex client instance
    
    Args:
        api_key: API key for authenticated endpoints
        **kwargs: Additional configuration parameters
        
    Returns:
        WallexClient instance
    """
    return WallexClient(api_key=api_key, **kwargs)


def create_async_client(api_key: Optional[str] = None, **kwargs) -> WallexAsyncClient:
    """
    Create a new async Wallex client instance
    
    Args:
        api_key: API key for authenticated endpoints
        **kwargs: Additional configuration parameters
        
    Returns:
        WallexAsyncClient instance
    """
    return WallexAsyncClient(api_key=api_key, **kwargs)


# Convenience functions for quick access (backward compatibility)

def get_markets() -> Dict:
    """Quick function to get market data without authentication"""
    with create_client() as client:
        return client.get_markets()


def get_market_stats(symbol: str) -> Dict:
    """Quick function to get market statistics for a symbol"""
    with create_client() as client:
        return client.get_market_stats(symbol)


def get_orderbook(symbol: str) -> Dict:
    """Quick function to get order book for a symbol"""
    with create_client() as client:
        return client.get_orderbook(symbol)


def get_trades(symbol: str, limit: Optional[int] = None) -> Dict:
    """Quick function to get recent trades for a symbol"""
    with create_client() as client:
        return client.get_trades(symbol, limit)