# API Documentation

This document provides detailed API documentation for the Wallex Python Client.

## Table of Contents

1. [Configuration](#configuration)
2. [REST API](#rest-api)
3. [WebSocket API](#websocket-api)
4. [Client Classes](#client-classes)
5. [Utility Functions](#utility-functions)
6. [Type Definitions](#type-definitions)
7. [Error Handling](#error-handling)

## Configuration

### WallexConfig

The `WallexConfig` class manages all configuration options for the Wallex client.

```python
class WallexConfig:
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        websocket_url: Optional[str] = None,
        testnet: bool = False,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        rate_limit: int = 100,
        debug: bool = False
    )
```

#### Parameters

- **api_key** (`str`, optional): Your Wallex API key for authenticated requests
- **secret_key** (`str`, optional): Your Wallex secret key for request signing
- **base_url** (`str`, optional): Custom REST API base URL
- **websocket_url** (`str`, optional): Custom WebSocket URL
- **testnet** (`bool`): Use testnet endpoints (default: `False`)
- **timeout** (`int`): Request timeout in seconds (default: `30`)
- **max_retries** (`int`): Maximum retry attempts for failed requests (default: `3`)
- **retry_delay** (`float`): Delay between retries in seconds (default: `1.0`)
- **rate_limit** (`int`): Requests per minute limit (default: `100`)
- **debug** (`bool`): Enable debug logging (default: `False`)

#### Class Methods

```python
@classmethod
def from_env(cls) -> 'WallexConfig'
```
Load configuration from environment variables.

```python
@classmethod
def from_file(cls, file_path: str) -> 'WallexConfig'
```
Load configuration from a JSON file.

#### Environment Variables

- `WALLEX_API_KEY`: API key
- `WALLEX_SECRET_KEY`: Secret key
- `WALLEX_BASE_URL`: REST API base URL
- `WALLEX_WEBSOCKET_URL`: WebSocket URL
- `WALLEX_TESTNET`: Use testnet (true/false)
- `WALLEX_TIMEOUT`: Request timeout
- `WALLEX_MAX_RETRIES`: Maximum retries
- `WALLEX_RATE_LIMIT`: Rate limit
- `WALLEX_DEBUG`: Debug mode (true/false)

## REST API

### WallexRestClient

The main REST API client for interacting with Wallex endpoints.

```python
class WallexRestClient:
    def __init__(self, config: WallexConfig)
```

### Public Endpoints

#### get_markets()

Get all available trading markets.

```python
def get_markets(self) -> Dict[str, Any]
```

**Returns:**
```json
{
    "success": true,
    "result": {
        "markets": [
            {
                "symbol": "BTCIRT",
                "baseAsset": "BTC",
                "quoteAsset": "IRT",
                "status": "TRADING",
                "minQty": "0.00001",
                "maxQty": "1000",
                "stepSize": "0.00001",
                "tickSize": "1000"
            }
        ]
    }
}
```

#### get_market_stats(symbol)

Get 24-hour statistics for a specific market.

```python
def get_market_stats(self, symbol: str) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`): Trading pair symbol (e.g., "BTCIRT")

**Returns:**
```json
{
    "success": true,
    "result": {
        "symbol": "BTCIRT",
        "priceChange": "1000000",
        "priceChangePercent": "2.5",
        "weightedAvgPrice": "41000000",
        "prevClosePrice": "40000000",
        "lastPrice": "41000000",
        "bidPrice": "40950000",
        "askPrice": "41050000",
        "openPrice": "40000000",
        "highPrice": "42000000",
        "lowPrice": "39500000",
        "volume": "125.5",
        "quoteVolume": "5142500000",
        "openTime": 1640995200000,
        "closeTime": 1641081599999,
        "count": 1250
    }
}
```

#### get_orderbook(symbol)

Get the order book for a specific market.

```python
def get_orderbook(self, symbol: str) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`): Trading pair symbol

**Returns:**
```json
{
    "success": true,
    "result": {
        "symbol": "BTCIRT",
        "bids": [
            ["40950000", "0.5"],
            ["40900000", "1.2"]
        ],
        "asks": [
            ["41050000", "0.8"],
            ["41100000", "2.1"]
        ]
    }
}
```

#### get_trades(symbol)

Get recent trades for a specific market.

```python
def get_trades(self, symbol: str) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`): Trading pair symbol

#### get_klines(symbol, resolution, from_time, to_time)

Get candlestick/kline data.

```python
def get_klines(
    self,
    symbol: str,
    resolution: str,
    from_time: int,
    to_time: int
) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`): Trading pair symbol
- **resolution** (`str`): Time interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
- **from_time** (`int`): Start timestamp
- **to_time** (`int`): End timestamp

#### get_currencies()

Get all supported currencies.

```python
def get_currencies(self) -> Dict[str, Any]
```

### Authenticated Endpoints

#### get_account()

Get account information.

```python
def get_account(self) -> Dict[str, Any]
```

**Requires:** API key and secret

#### get_balances()

Get account balances.

```python
def get_balances(self) -> Dict[str, Any]
```

**Requires:** API key and secret

#### place_order(symbol, side, type, quantity, price)

Place a new order.

```python
def place_order(
    self,
    symbol: str,
    side: str,
    type: str,
    quantity: str,
    price: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`): Trading pair symbol
- **side** (`str`): Order side ("BUY" or "SELL")
- **type** (`str`): Order type ("LIMIT", "MARKET")
- **quantity** (`str`): Order quantity
- **price** (`str`, optional): Order price (required for LIMIT orders)

**Requires:** API key and secret

#### cancel_order(order_id)

Cancel an existing order.

```python
def cancel_order(self, order_id: str) -> Dict[str, Any]
```

**Parameters:**
- **order_id** (`str`): Order ID to cancel

**Requires:** API key and secret

#### get_orders(symbol, status)

Get orders with optional filtering.

```python
def get_orders(
    self,
    symbol: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`, optional): Filter by trading pair
- **status** (`str`, optional): Filter by order status

**Requires:** API key and secret

#### get_order(order_id)

Get details of a specific order.

```python
def get_order(self, order_id: str) -> Dict[str, Any]
```

**Parameters:**
- **order_id** (`str`): Order ID

**Requires:** API key and secret

#### get_trades_history(symbol)

Get trade history.

```python
def get_trades_history(self, symbol: Optional[str] = None) -> Dict[str, Any]
```

**Parameters:**
- **symbol** (`str`, optional): Filter by trading pair

**Requires:** API key and secret

#### get_deposits()

Get deposit history.

```python
def get_deposits(self) -> Dict[str, Any]
```

**Requires:** API key and secret

#### get_withdrawals()

Get withdrawal history.

```python
def get_withdrawals(self) -> Dict[str, Any]
```

**Requires:** API key and secret

#### withdraw(currency, amount, address)

Create a withdrawal request.

```python
def withdraw(
    self,
    currency: str,
    amount: str,
    address: str,
    **kwargs
) -> Dict[str, Any]
```

**Parameters:**
- **currency** (`str`): Currency to withdraw
- **amount** (`str`): Withdrawal amount
- **address** (`str`): Destination address

**Requires:** API key and secret

### Convenience Functions

```python
def create_rest_client(**kwargs) -> WallexRestClient
def get_markets(**kwargs) -> Dict[str, Any]
def get_market_stats(symbol: str, **kwargs) -> Dict[str, Any]
def get_orderbook(symbol: str, **kwargs) -> Dict[str, Any]
def get_trades(symbol: str, **kwargs) -> Dict[str, Any]
```

## WebSocket API

### WallexWebSocketClient

Synchronous WebSocket client for real-time data.

```python
class WallexWebSocketClient:
    def __init__(self, config: WallexConfig)
```

#### Methods

```python
def connect(self) -> None
def disconnect(self) -> None
def subscribe_trades(self, symbol: str, callback: Callable) -> None
def subscribe_orderbook(self, symbol: str, callback: Callable) -> None
def subscribe_klines(self, symbol: str, resolution: str, callback: Callable) -> None
def subscribe_market_stats(self, symbol: str, callback: Callable) -> None
def unsubscribe(self, channel: str) -> None
def wait(self) -> None
```

### WallexAsyncWebSocketClient

Asynchronous WebSocket client for real-time data.

```python
class WallexAsyncWebSocketClient:
    def __init__(self, config: WallexConfig)
```

#### Methods

```python
async def connect(self) -> None
async def disconnect(self) -> None
async def subscribe_trades(self, symbol: str, callback: Callable) -> None
async def subscribe_orderbook(self, symbol: str, callback: Callable) -> None
async def subscribe_klines(self, symbol: str, resolution: str, callback: Callable) -> None
async def subscribe_market_stats(self, symbol: str, callback: Callable) -> None
async def unsubscribe(self, channel: str) -> None
```

### WebSocket Events

#### Trade Updates

```python
def on_trade_update(data):
    # data structure:
    {
        "symbol": "BTCIRT",
        "price": "41000000",
        "quantity": "0.5",
        "timestamp": 1641081600000,
        "side": "BUY"
    }
```

#### Orderbook Updates

```python
def on_orderbook_update(data):
    # data structure:
    {
        "symbol": "BTCIRT",
        "bids": [["40950000", "0.5"]],
        "asks": [["41050000", "0.8"]],
        "timestamp": 1641081600000
    }
```

## Client Classes

### WallexClient

Main synchronous client that combines REST and WebSocket functionality.

```python
class WallexClient:
    def __init__(self, config: Optional[WallexConfig] = None)
    
    # REST API methods (delegated to WallexRestClient)
    def get_markets(self) -> Dict[str, Any]
    def get_market_stats(self, symbol: str) -> Dict[str, Any]
    # ... all REST methods
    
    # WebSocket methods
    def connect_websocket(self) -> None
    def disconnect_websocket(self) -> None
    def subscribe_trades(self, symbol: str, callback: Callable) -> None
    # ... all WebSocket methods
```

### WallexAsyncClient

Main asynchronous client for high-performance applications.

```python
class WallexAsyncClient:
    def __init__(self, config: Optional[WallexConfig] = None)
    
    # Async REST API methods
    async def get_markets(self) -> Dict[str, Any]
    async def get_market_stats(self, symbol: str) -> Dict[str, Any]
    # ... all REST methods as async
```

### Factory Functions

```python
def create_client(**kwargs) -> WallexClient
def create_async_client(**kwargs) -> WallexAsyncClient
```

## Utility Functions

### Symbol Validation

```python
def validate_symbol(symbol: str) -> bool
```

Validate if a symbol follows the correct format.

### Price Formatting

```python
def format_price(price: Union[str, float], precision: int = 8) -> str
```

Format price with specified precision.

### Timestamp Utilities

```python
def get_timestamp() -> int
```

Get current Unix timestamp in milliseconds.

### Common Symbols

```python
class CommonSymbols:
    BTCIRT = "BTCIRT"
    ETHIRT = "ETHIRT"
    LTCIRT = "LTCIRT"
    # ... more symbols
```

## Type Definitions

### Enums

```python
class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"

class KlineInterval(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
```

## Error Handling

### Exception Classes

```python
class WallexError(Exception):
    """Base exception for all Wallex errors"""

class WallexAPIError(WallexError):
    """API-related errors"""
    def __init__(self, message: str, status_code: int = None, details: dict = None)

class WallexWebSocketError(WallexError):
    """WebSocket-related errors"""

class WallexConfigError(WallexError):
    """Configuration-related errors"""

class WallexAuthenticationError(WallexAPIError):
    """Authentication-related errors"""

class WallexRateLimitError(WallexAPIError):
    """Rate limit exceeded errors"""
```

### Error Response Format

```json
{
    "success": false,
    "error": {
        "code": 400,
        "message": "Invalid symbol",
        "details": {
            "symbol": "INVALID"
        }
    }
}
```

### Handling Errors

```python
from wallex.exceptions import WallexAPIError, WallexWebSocketError

try:
    client = WallexClient(config)
    result = client.get_markets()
except WallexAPIError as e:
    print(f"API Error: {e}")
    print(f"Status Code: {e.status_code}")
    print(f"Details: {e.details}")
except WallexWebSocketError as e:
    print(f"WebSocket Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Rate Limiting

The client automatically handles rate limiting:

- Default limit: 100 requests per minute
- Automatic retry with exponential backoff
- Configurable retry attempts and delays
- Rate limit headers are respected

## Authentication

For authenticated endpoints, you need to provide API credentials:

1. **API Key**: Your Wallex API key
2. **Secret Key**: Your Wallex secret key

The client automatically handles:
- Request signing
- Timestamp generation
- Header formatting

## Testnet Support

Enable testnet mode for development and testing:

```python
config = WallexConfig(testnet=True)
```

This automatically switches to testnet endpoints:
- REST API: `https://testnet-api.wallex.ir`
- WebSocket: `wss://testnet-ws.wallex.ir`

## Best Practices

1. **Use async client for high-throughput applications**
2. **Enable testnet during development**
3. **Implement proper error handling**
4. **Use connection pooling for multiple requests**
5. **Monitor rate limits**
6. **Keep API credentials secure**
7. **Use WebSocket for real-time data**
8. **Validate symbols before making requests**