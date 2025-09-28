# Portfolio Tracker

A sophisticated cryptocurrency portfolio tracking system built around the Wallex exchange API.

## 🚀 Quick Start

This project provides a comprehensive solution for tracking cryptocurrency portfolios with real-time data, historical analysis, and web-based visualization.

### Key Features

- **Real-time Market Data** - WebSocket integration for live price updates
- **Portfolio Tracking** - Historical balance and performance tracking
- **Web Dashboard** - Beautiful, responsive web interface
- **Modular Design** - Use only the components you need
- **Comprehensive API** - Full REST and WebSocket client library

## 📚 Documentation

All project documentation has been organized into a comprehensive structure:

**[📖 View Complete Documentation →](./documentation/README.md)**

### Quick Links

- **[🚀 Getting Started](./documentation/01-getting-started/project-overview.md)** - Project overview and setup
- **[📖 API Reference](./documentation/02-api-reference/)** - Complete API documentation
- **[🛠️ Development Guide](./documentation/03-development/contributing.md)** - Contributing guidelines
- **[🔧 Technical Details](./documentation/04-technical-details/)** - Architecture and implementation
- **[📋 Project Info](./documentation/05-project-info/)** - Changelog and project status

## 🏗️ Project Structure

```
PortfolioTreacker/
├── wallex/                 # Core Wallex API library
├── documentation/          # Organized documentation
├── templates/             # Web UI templates
├── tests/                 # Comprehensive test suite
├── suggestions/           # Enhancement suggestions
├── wallet_ui.py          # FastAPI web interface
├── database.py           # SQLite database layer
└── examples_modular.py   # Usage examples
```

## 🛠️ Technology Stack

- **Backend**: Python 3.8+, FastAPI, SQLite
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **APIs**: Wallex Exchange API, CoinGecko API
- **Testing**: pytest with async support

### Async Usage

```python
import asyncio
from wallex import WallexAsyncClient, WallexConfig

async def main():
    config = WallexConfig(testnet=True)
    client = WallexAsyncClient(config)
    
    # Concurrent requests
    markets, stats = await asyncio.gather(
        client.get_markets(),
        client.get_market_stats("BTCIRT")
    )
    
    print(f"Markets: {len(markets['result']['markets'])}")
    print(f"BTC Stats: {stats}")

asyncio.run(main())
```

### WebSocket Streaming

```python
from wallex import WallexClient, WallexConfig

def on_trade_update(data):
    print(f"New trade: {data}")

def on_orderbook_update(data):
    print(f"Orderbook update: {data}")

config = WallexConfig(testnet=True)
client = WallexClient(config)

# Connect WebSocket
client.connect_websocket()

# Subscribe to real-time data
client.subscribe_trades("BTCIRT", on_trade_update)
client.subscribe_orderbook("BTCIRT", on_orderbook_update)

# Keep connection alive
try:
    client.websocket.wait()
except KeyboardInterrupt:
    client.disconnect_websocket()
```

## Modular Usage

The library is designed with modularity in mind. You can use individual components:

### REST Client Only

```python
from wallex.rest import WallexRestClient, create_rest_client
from wallex.config import WallexConfig

# Method 1: Direct instantiation
config = WallexConfig(testnet=True)
rest_client = WallexRestClient(config)
markets = rest_client.get_markets()

# Method 2: Factory function
rest_client = create_rest_client(testnet=True)
markets = rest_client.get_markets()

# Method 3: Convenience functions
from wallex.rest import get_markets, get_orderbook
markets = get_markets(testnet=True)
orderbook = get_orderbook("BTCIRT", testnet=True)
```

### WebSocket Client Only

```python
from wallex.socket import WallexWebSocketClient
from wallex.config import WallexConfig

config = WallexConfig(testnet=True)
ws_client = WallexWebSocketClient(config)

def handle_trades(data):
    print(f"Trade: {data}")

ws_client.connect()
ws_client.subscribe_trades("BTCIRT", handle_trades)
ws_client.wait()
```

### Configuration Management

```python
from wallex.config import WallexConfig

# From environment variables
config = WallexConfig.from_env()

# From file
config = WallexConfig.from_file("config.json")

# Manual configuration
config = WallexConfig(
    api_key="your_key",
    secret_key="your_secret",
    base_url="https://api.wallex.ir",
    websocket_url="wss://ws.wallex.ir",
    testnet=False,
    timeout=30,
    max_retries=3
)
```

### Utility Functions

```python
from wallex.utils import validate_symbol, format_price, get_timestamp

# Validate trading symbols
is_valid = validate_symbol("BTCIRT")  # True
is_valid = validate_symbol("INVALID")  # False

# Format prices
formatted = format_price(1234.5678, precision=2)  # "1234.57"

# Get current timestamp
timestamp = get_timestamp()  # Current Unix timestamp
```

## API Reference

### REST API Methods

#### Public Endpoints
- `get_markets()` - Get all available markets
- `get_market_stats(symbol)` - Get 24h statistics for a market
- `get_orderbook(symbol)` - Get order book for a symbol
- `get_trades(symbol)` - Get recent trades for a symbol
- `get_klines(symbol, resolution, from_time, to_time)` - Get candlestick data
- `get_currencies()` - Get all supported currencies

#### Authenticated Endpoints
- `get_account()` - Get account information
- `get_balances()` - Get account balances
- `place_order(symbol, side, type, quantity, price)` - Place a new order
- `cancel_order(order_id)` - Cancel an order
- `get_orders(symbol, status)` - Get orders
- `get_order(order_id)` - Get specific order
- `get_trades_history(symbol)` - Get trade history
- `get_deposits()` - Get deposit history
- `get_withdrawals()` - Get withdrawal history
- `withdraw(currency, amount, address)` - Create withdrawal

### WebSocket Events

#### Public Channels
- `subscribe_trades(symbol, callback)` - Subscribe to trade updates
- `subscribe_orderbook(symbol, callback)` - Subscribe to orderbook updates
- `subscribe_klines(symbol, resolution, callback)` - Subscribe to kline updates
- `subscribe_market_stats(symbol, callback)` - Subscribe to 24h stats

#### Private Channels (requires authentication)
- `subscribe_orders(callback)` - Subscribe to order updates
- `subscribe_balances(callback)` - Subscribe to balance updates

### Configuration Options

```python
WallexConfig(
    api_key: str = None,           # API key for authenticated requests
    secret_key: str = None,        # Secret key for request signing
    base_url: str = None,          # REST API base URL
    websocket_url: str = None,     # WebSocket URL
    testnet: bool = False,         # Use testnet endpoints
    timeout: int = 30,             # Request timeout in seconds
    max_retries: int = 3,          # Maximum retry attempts
    retry_delay: float = 1.0,      # Delay between retries
    rate_limit: int = 100,         # Requests per minute limit
    debug: bool = False            # Enable debug logging
)
```

## Error Handling

The library provides specific exceptions for different error types:

```python
from wallex.exceptions import WallexAPIError, WallexWebSocketError

try:
    client = WallexClient(config)
    result = client.get_markets()
except WallexAPIError as e:
    print(f"API Error: {e}")
    print(f"Status Code: {e.status_code}")
    print(f"Error Details: {e.details}")
except WallexWebSocketError as e:
    print(f"WebSocket Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Testing

The library includes a comprehensive test suite:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=wallex --cov-report=html

# Run specific test categories
uv run pytest tests/test_rest.py          # REST API tests
uv run pytest tests/test_socket.py        # WebSocket tests
uv run pytest tests/test_integration.py   # Integration tests
uv run pytest tests/test_performance.py   # Performance tests

# Run with verbose output
uv run pytest -v -s
```

## Examples

Check out the `examples_modular.py` file for comprehensive usage examples:

```bash
uv run examples_modular.py
```

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/your-repo/wallex-python-client.git
cd wallex-python-client

# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run linting
uv run ruff check
uv run mypy wallex
```

### Project Structure

```
wallex-python-client/
├── wallex/                 # Main package
│   ├── __init__.py        # Package exports
│   ├── client.py          # Main client classes
│   ├── config.py          # Configuration management
│   ├── rest.py            # REST API client
│   ├── socket.py          # WebSocket client
│   ├── utils.py           # Utility functions
│   ├── types.py           # Type definitions
│   └── exceptions.py      # Custom exceptions
├── tests/                 # Test suite
│   ├── conftest.py        # Test configuration
│   ├── test_wallex.py     # Main test file
│   ├── test_integration.py # Integration tests
│   └── test_performance.py # Performance tests
├── examples_modular.py    # Usage examples
├── test_modular.py        # Module verification
├── pyproject.toml         # Project configuration
└── README.md             # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Run the test suite (`uv run pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@wallex.ir
- 📖 Documentation: [https://docs.wallex.ir](https://docs.wallex.ir)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/wallex-python-client/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-repo/wallex-python-client/discussions)

## Changelog

### v2.0.0 (Latest)
- ✨ Complete modular architecture
- 🚀 Added async support
- 🔒 Enhanced type safety
- 🛡️ Improved error handling
- 📊 WebSocket streaming support
- 🧪 Comprehensive test suite

### v1.0.0
- 🎉 Initial release
- 📡 Basic REST API support
- ⚙️ Configuration management

---

**Made with ❤️ for the Wallex community**