"""
Wallex WebSocket Client Module

This module provides WebSocket functionality for real-time data streaming from Wallex.
"""

import socketio
import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import WallexConfig, get_config
from .exceptions import WallexWebSocketError, WallexConnectionError, WallexTimeoutError
from .types import WallexWebSocketChannels


class WallexWebSocketClient:
    """
    Wallex WebSocket Client
    
    Implements WebSocket connections for real-time data streaming.
    """
    
    def __init__(self, config: Optional[WallexConfig] = None):
        """
        Initialize WebSocket client
        
        Args:
            config: Configuration object, uses default if None
        """
        self.config = config or get_config()
        self.sio = socketio.Client(
            reconnection=self.config.ws_reconnect,
            reconnection_attempts=self.config.ws_reconnect_attempts,
            reconnection_delay=self.config.ws_reconnect_delay,
            reconnection_delay_max=self.config.ws_reconnect_delay_max,
            randomization_factor=0.5,
            logger=False,
            engineio_logger=False
        )
        
        self.subscriptions: Set[str] = set()
        self.callbacks: Dict[str, Callable] = {}
        self.is_connected = False
        self.connection_lock = threading.Lock()
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup default event handlers"""
        
        @self.sio.event
        def connect():
            """Handle connection event"""
            with self.connection_lock:
                self.is_connected = True
            logging.info("Connected to Wallex WebSocket")
            
            # Re-subscribe to channels after reconnection
            for channel in self.subscriptions:
                try:
                    self.sio.emit('subscribe', {'channel': channel})
                except Exception as e:
                    logging.error(f"Failed to re-subscribe to {channel}: {e}")
        
        @self.sio.event
        def disconnect():
            """Handle disconnection event"""
            with self.connection_lock:
                self.is_connected = False
            logging.info("Disconnected from Wallex WebSocket")
        
        @self.sio.event
        def connect_error(data):
            """Handle connection error event"""
            with self.connection_lock:
                self.is_connected = False
            logging.error(f"WebSocket connection error: {data}")
        
        @self.sio.on('Broadcaster')
        def on_broadcaster(channel, data):
            """Handle incoming data from subscribed channels"""
            if channel in self.callbacks:
                try:
                    # Execute callback in a separate thread to avoid blocking
                    callback = self.callbacks[channel]
                    threading.Thread(
                        target=self._execute_callback,
                        args=(callback, channel, data),
                        daemon=True
                    ).start()
                except Exception as e:
                    logging.error(f"Error setting up callback for channel {channel}: {e}")
        
        @self.sio.on('error')
        def on_error(data):
            """Handle error event"""
            logging.error(f"WebSocket error: {data}")
    
    def _execute_callback(self, callback: Callable, channel: str, data: Any):
        """
        Execute callback function safely
        
        Args:
            callback: Callback function to execute
            channel: Channel name
            data: Data received from channel
        """
        try:
            callback(channel, data)
        except Exception as e:
            logging.error(f"Error in callback for channel {channel}: {e}")
    
    def connect(self, timeout: Optional[int] = None) -> bool:
        """
        Connect to Wallex WebSocket server
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully, False otherwise
            
        Raises:
            WallexWebSocketError: If connection fails
        """
        if self.is_connected:
            return True
        
        timeout = timeout or self.config.ws_timeout
        
        try:
            # Use WebSocket URL from config
            ws_url = self.config.ws_url or self.config.base_url.replace('https://', 'wss://').replace('http://', 'ws://')
            
            self.sio.connect(
                ws_url,
                transports=['websocket'],
                wait_timeout=timeout
            )
            
            # Wait a moment for connection to stabilize
            time.sleep(0.5)
            
            with self.connection_lock:
                if not self.is_connected:
                    raise WallexWebSocketError("Connection established but not confirmed")
            
            return True
            
        except socketio.exceptions.ConnectionError as e:
            raise WallexConnectionError(f"Failed to connect to WebSocket: {e}")
        except Exception as e:
            raise WallexWebSocketError(f"Unexpected error during connection: {e}")
    
    def disconnect(self):
        """Disconnect from WebSocket server"""
        try:
            if self.sio.connected:
                self.sio.disconnect()
            
            with self.connection_lock:
                self.is_connected = False
            
            # Clear subscriptions and callbacks
            self.subscriptions.clear()
            self.callbacks.clear()
            
        except Exception as e:
            logging.error(f"Error during disconnect: {e}")
    
    def _subscribe_channel(self, channel: str, callback: Callable[[str, Dict], None]):
        """
        Internal method to subscribe to a channel
        
        Args:
            channel: Channel name
            callback: Callback function
        """
        if not self.is_connected:
            raise WallexWebSocketError("Not connected to WebSocket server")
        
        self.subscriptions.add(channel)
        self.callbacks[channel] = callback
        
        try:
            self.sio.emit('subscribe', {'channel': channel})
        except Exception as e:
            # Remove from subscriptions if emit fails
            self.subscriptions.discard(channel)
            self.callbacks.pop(channel, None)
            raise WallexWebSocketError(f"Failed to subscribe to {channel}: {e}")
    
    def subscribe_trades(self, symbol: str, callback: Callable[[str, Dict], None]):
        """
        Subscribe to trade updates for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            callback: Callback function to handle trade data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        channel = f"{symbol}@trade"
        self._subscribe_channel(channel, callback)
    
    def subscribe_orderbook(self, symbol: str, callback: Callable[[str, Dict], None]):
        """
        Subscribe to order book updates for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            callback: Callback function to handle order book data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        # Subscribe to both buy and sell depth
        buy_channel = f"{symbol}@buyDepth"
        sell_channel = f"{symbol}@sellDepth"
        
        self._subscribe_channel(buy_channel, callback)
        self._subscribe_channel(sell_channel, callback)
    
    def subscribe_ticker(self, symbol: str, callback: Callable[[str, Dict], None]):
        """
        Subscribe to ticker updates for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            callback: Callback function to handle ticker data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        channel = f"{symbol}@ticker"
        self._subscribe_channel(channel, callback)
    
    def subscribe_market_cap(self, symbol: str, callback: Callable[[str, Dict], None]):
        """
        Subscribe to market cap updates for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            callback: Callback function to handle market cap data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        channel = f"{symbol}@marketCap"
        self._subscribe_channel(channel, callback)
    
    def subscribe_kline(self, symbol: str, interval: str, callback: Callable[[str, Dict], None]):
        """
        Subscribe to kline/candlestick updates for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            interval: Kline interval (e.g., '1m', '5m', '1h', '1d')
            callback: Callback function to handle kline data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        channel = f"{symbol}@kline_{interval}"
        self._subscribe_channel(channel, callback)
    
    def subscribe_all_tickers(self, callback: Callable[[str, Dict], None]):
        """
        Subscribe to all ticker updates
        
        Args:
            callback: Callback function to handle ticker data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        channel = "!ticker@arr"
        self._subscribe_channel(channel, callback)
    
    def subscribe_all_market_caps(self, callback: Callable[[str, Dict], None]):
        """
        Subscribe to all market cap updates
        
        Args:
            callback: Callback function to handle market cap data
            
        Raises:
            WallexWebSocketError: If subscription fails
        """
        channel = "!marketCap@arr"
        self._subscribe_channel(channel, callback)
    
    def unsubscribe(self, channel: str):
        """
        Unsubscribe from a specific channel
        
        Args:
            channel: Channel name to unsubscribe from
        """
        if channel in self.subscriptions:
            self.subscriptions.remove(channel)
            self.callbacks.pop(channel, None)
            
            if self.is_connected:
                try:
                    self.sio.emit('unsubscribe', {'channel': channel})
                except Exception as e:
                    logging.error(f"Failed to unsubscribe from {channel}: {e}")
    
    def unsubscribe_symbol(self, symbol: str):
        """
        Unsubscribe from all channels for a specific symbol
        
        Args:
            symbol: Trading symbol
        """
        channels_to_remove = [
            channel for channel in self.subscriptions 
            if channel.startswith(f"{symbol}@")
        ]
        
        for channel in channels_to_remove:
            self.unsubscribe(channel)
    
    def unsubscribe_all(self):
        """Unsubscribe from all channels"""
        channels_to_remove = list(self.subscriptions)
        for channel in channels_to_remove:
            self.unsubscribe(channel)
    
    def get_subscriptions(self) -> List[str]:
        """
        Get list of current subscriptions
        
        Returns:
            List of subscribed channel names
        """
        return list(self.subscriptions)
    
    def is_subscribed(self, channel: str) -> bool:
        """
        Check if subscribed to a specific channel
        
        Args:
            channel: Channel name
            
        Returns:
            True if subscribed, False otherwise
        """
        return channel in self.subscriptions
    
    def wait_for_connection(self, timeout: int = 10) -> bool:
        """
        Wait for connection to be established
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if connected, False if timeout
        """
        start_time = time.time()
        while not self.is_connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        return self.is_connected
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class WallexAsyncWebSocketClient:
    """
    Async version of Wallex WebSocket Client
    
    Provides async/await interface for WebSocket operations.
    """
    
    def __init__(self, config: Optional[WallexConfig] = None):
        """
        Initialize async WebSocket client
        
        Args:
            config: Configuration object, uses default if None
        """
        self.config = config or get_config()
        self.sio = socketio.AsyncClient(
            reconnection=self.config.ws_reconnect,
            reconnection_attempts=self.config.ws_reconnect_attempts,
            reconnection_delay=self.config.ws_reconnect_delay,
            reconnection_delay_max=self.config.ws_reconnect_delay_max,
            logger=False,
            engineio_logger=False
        )
        
        self.subscriptions: Set[str] = set()
        self.callbacks: Dict[str, Callable] = {}
        self.is_connected = False
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup async event handlers"""
        
        @self.sio.event
        async def connect():
            """Handle connection event"""
            self.is_connected = True
            logging.info("Connected to Wallex WebSocket (async)")
            
            # Re-subscribe to channels after reconnection
            for channel in self.subscriptions:
                try:
                    await self.sio.emit('subscribe', {'channel': channel})
                except Exception as e:
                    logging.error(f"Failed to re-subscribe to {channel}: {e}")
        
        @self.sio.event
        async def disconnect():
            """Handle disconnection event"""
            self.is_connected = False
            logging.info("Disconnected from Wallex WebSocket (async)")
        
        @self.sio.event
        async def connect_error(data):
            """Handle connection error event"""
            self.is_connected = False
            logging.error(f"WebSocket connection error (async): {data}")
        
        @self.sio.on('Broadcaster')
        async def on_broadcaster(channel, data):
            """Handle incoming data from subscribed channels"""
            if channel in self.callbacks:
                try:
                    callback = self.callbacks[channel]
                    if asyncio.iscoroutinefunction(callback):
                        await callback(channel, data)
                    else:
                        callback(channel, data)
                except Exception as e:
                    logging.error(f"Error in async callback for channel {channel}: {e}")
    
    async def connect(self, timeout: Optional[int] = None) -> bool:
        """
        Connect to Wallex WebSocket server (async)
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
            
        Raises:
            WallexWebSocketError: If connection fails
        """
        if self.is_connected:
            return True
        
        timeout = timeout or self.config.ws_timeout
        
        try:
            ws_url = self.config.ws_url or self.config.base_url.replace('https://', 'wss://').replace('http://', 'ws://')
            
            await self.sio.connect(
                ws_url,
                transports=['websocket'],
                wait_timeout=timeout
            )
            
            # Wait for connection confirmation
            await asyncio.sleep(0.5)
            
            if not self.is_connected:
                raise WallexWebSocketError("Connection established but not confirmed")
            
            return True
            
        except Exception as e:
            raise WallexWebSocketError(f"Failed to connect to WebSocket: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket server (async)"""
        try:
            if self.sio.connected:
                await self.sio.disconnect()
            
            self.is_connected = False
            self.subscriptions.clear()
            self.callbacks.clear()
            
        except Exception as e:
            logging.error(f"Error during async disconnect: {e}")
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """Subscribe to trade updates (async)"""
        channel = f"{symbol}@trade"
        self.subscriptions.add(channel)
        self.callbacks[channel] = callback
        
        if self.is_connected:
            await self.sio.emit('subscribe', {'channel': channel})
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable):
        """Subscribe to order book updates (async)"""
        buy_channel = f"{symbol}@buyDepth"
        sell_channel = f"{symbol}@sellDepth"
        
        self.subscriptions.add(buy_channel)
        self.subscriptions.add(sell_channel)
        self.callbacks[buy_channel] = callback
        self.callbacks[sell_channel] = callback
        
        if self.is_connected:
            await self.sio.emit('subscribe', {'channel': buy_channel})
            await self.sio.emit('subscribe', {'channel': sell_channel})
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# Convenience functions
def create_websocket_client(config: Optional[WallexConfig] = None) -> WallexWebSocketClient:
    """
    Create a new WebSocket client instance
    
    Args:
        config: Configuration object
        
    Returns:
        WallexWebSocketClient instance
    """
    return WallexWebSocketClient(config)


def create_async_websocket_client(config: Optional[WallexConfig] = None) -> WallexAsyncWebSocketClient:
    """
    Create a new async WebSocket client instance
    
    Args:
        config: Configuration object
        
    Returns:
        WallexAsyncWebSocketClient instance
    """
    return WallexAsyncWebSocketClient(config)