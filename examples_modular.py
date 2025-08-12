#!/usr/bin/env python3
"""
Wallex Python Client - Modular Examples

This file demonstrates how to use the new modular Wallex library.
"""

import asyncio
import os
import logging
from wallex import WallexClient, WallexConfig, create_client, create_async_client
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexAsyncWebSocketClient
from wallex.config import WallexConfig
from wallex.types import OrderSide, OrderType, TimeInForce
from wallex.utils import validate_symbol, format_price, calculate_percentage_change

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Example of basic library usage"""
    logger.info("=== Basic Usage Example ===")
    
    # Create client with default configuration
    client = create_client()
    
    # Get market data
    try:
        markets = client.get_markets()
        logger.info(f"Found {len(markets)} markets")
        
        # Get specific market stats
        if markets:
            symbol = markets[0]['symbol']
            stats = client.get_market_stats(symbol)
            logger.info(f"Market stats for {symbol}: {stats}")
            
    except Exception as e:
        logger.error(f"Error: {e}")


def example_rest_only():
    """Example using only REST API"""
    logger.info("\n=== REST API Only Example ===")
    
    # Create REST client only
    config = WallexConfig()
    rest_client = WallexRestClient(config)
    
    try:
        # Get currencies
        currencies = rest_client.get_currencies()
        logger.info(f"Available currencies: {len(currencies)}")
        
        # Get order book
        orderbook = rest_client.get_orderbook("BTCUSDT")
        logger.info(f"Order book for BTCUSDT: {len(orderbook.get('bids', []))} bids, {len(orderbook.get('asks', []))} asks")
        
    except Exception as e:
        logger.error(f"Error: {e}")


def example_websocket_sync():
    """Example using synchronous WebSocket"""
    logger.info("\n=== Synchronous WebSocket Example ===")
    
    config = WallexConfig()
    ws_client = WallexWebSocketClient(config)
    
    def on_message(data):
        logger.info(f"Received: {data}")
    
    def on_error(error):
        logger.error(f"WebSocket error: {error}")
    
    try:
        # Set event handlers
        ws_client.on_message = on_message
        ws_client.on_error = on_error
        
        # Connect and subscribe
        ws_client.connect()
        ws_client.subscribe_trades("BTCUSDT")
        
        logger.info("WebSocket connected and subscribed to BTCUSDT trades")
        logger.info("Press Ctrl+C to stop...")
        
        # Keep connection alive for a short time
        import time
        time.sleep(5)
        
    except KeyboardInterrupt:
        logger.info("Stopping WebSocket...")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_client.disconnect()


async def example_websocket_async():
    """Example using asynchronous WebSocket"""
    logger.info("\n=== Asynchronous WebSocket Example ===")
    
    config = WallexConfig()
    ws_client = WallexAsyncWebSocketClient(config)
    
    async def on_message(data):
        logger.info(f"Async received: {data}")
    
    async def on_error(error):
        logger.error(f"Async WebSocket error: {error}")
    
    try:
        # Set event handlers
        ws_client.on_message = on_message
        ws_client.on_error = on_error
        
        # Connect and subscribe
        await ws_client.connect()
        await ws_client.subscribe_ticker("BTCUSDT")
        
        logger.info("Async WebSocket connected and subscribed to BTCUSDT ticker")
        
        # Keep connection alive for a short time
        await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"Async WebSocket error: {e}")
    finally:
        await ws_client.disconnect()


def example_full_client():
    """Example using full client with both REST and WebSocket"""
    logger.info("\n=== Full Client Example ===")
    
    # Create client with custom configuration
    config = WallexConfig(
        api_key=os.getenv("WALLEX_API_KEY", ""),
        testnet=True
    )
    
    client = WallexClient(config)
    
    def on_trade(data):
        logger.info(f"Trade update: {data}")
    
    try:
        # REST API calls
        markets = client.get_markets()
        logger.info(f"Markets: {len(markets)}")
        
        # WebSocket setup
        client.websocket.on_message = on_trade
        client.websocket.connect()
        client.websocket.subscribe_trades("BTCUSDT")
        
        logger.info("Full client example running...")
        
        # Simulate some activity
        import time
        time.sleep(3)
        
    except Exception as e:
        logger.error(f"Full client error: {e}")
    finally:
        if client.websocket.is_connected:
            client.websocket.disconnect()


async def example_async_client():
    """Example using async client"""
    logger.info("\n=== Async Client Example ===")
    
    config = WallexConfig()
    client = create_async_client(config)
    
    async def on_message(data):
        logger.info(f"Async client message: {data}")
    
    try:
        # REST API calls (these would be async in a real async client)
        markets = client.get_markets()
        logger.info(f"Async client markets: {len(markets)}")
        
        # WebSocket
        client.websocket.on_message = on_message
        await client.websocket.connect()
        await client.websocket.subscribe_market_cap("BTCUSDT")
        
        logger.info("Async client running...")
        await asyncio.sleep(3)
        
    except Exception as e:
        logger.error(f"Async client error: {e}")
    finally:
        if client.websocket.is_connected:
            await client.websocket.disconnect()


def example_utilities():
    """Example using utility functions"""
    logger.info("\n=== Utilities Example ===")
    
    # Symbol validation
    symbols = ["BTCUSDT", "invalid", "ETHUSDT", ""]
    for symbol in symbols:
        is_valid = validate_symbol(symbol)
        logger.info(f"Symbol '{symbol}' is valid: {is_valid}")
    
    # Price formatting
    prices = [1234.56789, 0.00012345, 100.0]
    for price in prices:
        formatted = format_price(price, precision=4)
        logger.info(f"Price {price} formatted: {formatted}")
    
    # Percentage calculation
    old_price = 100.0
    new_price = 105.5
    change = calculate_percentage_change(old_price, new_price)
    logger.info(f"Price change from {old_price} to {new_price}: {change:.2f}%")


def example_configuration():
    """Example of different configuration methods"""
    logger.info("\n=== Configuration Example ===")
    
    # Method 1: Default configuration
    config1 = WallexConfig()
    logger.info(f"Default config: testnet={config1.testnet}")
    
    # Method 2: Custom configuration
    config2 = WallexConfig(
        api_key="your_api_key",
        testnet=True,
        timeout=30,
        max_retries=5
    )
    logger.info(f"Custom config: timeout={config2.timeout}, retries={config2.max_retries}")
    
    # Method 3: From environment variables
    config3 = WallexConfig.from_env()
    logger.info(f"Env config: base_url={config3.base_url}")
    
    # Method 4: Update existing configuration
    config4 = config1.copy()
    config4.update(testnet=True, timeout=60)
    logger.info(f"Updated config: testnet={config4.testnet}, timeout={config4.timeout}")


def main():
    """Run all examples"""
    logger.info("Wallex Python Client - Modular Examples")
    logger.info("=" * 50)
    
    # Basic examples
    example_basic_usage()
    example_rest_only()
    example_utilities()
    example_configuration()
    
    # WebSocket examples (commented out to avoid connection issues in demo)
    # example_websocket_sync()
    # example_full_client()
    
    # Async examples
    # asyncio.run(example_websocket_async())
    # asyncio.run(example_async_client())
    
    logger.info("\n" + "=" * 50)
    logger.info("Examples completed!")


if __name__ == "__main__":
    main()