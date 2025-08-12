# Web UI Layer - Detailed Documentation for AI

This document explains the FastAPI web UI implementation in wallet_ui.py.

## wallet_ui.py

- Purpose: Provide a web interface for viewing wallet balances and portfolio data using FastAPI.
- Imports: FastAPI, Request, Jinja2Templates, StaticFiles, database, uvicorn, asyncio, aiohttp, logging, wallex client components.

### Core Architecture

The service is built as a modular service class that integrates with the Wallex API and CoinGecko for price data.

### Class: WalletService

#### `__init__(self, api_key, testnet=False)`
- Creates WallexClient with provided API key and testnet flag
- Initializes internal state tracking
- Sets up aiohttp ClientSession for external API calls

#### `async def get_account_info(self)`
- Calls `client.get_account_info()` via REST API
- Returns account information or None on failure
- Logs exceptions but continues gracefully

#### `async def get_balances(self)`
- Retrieves all balances from Wallex via `client.get_balances()`
- Filters to non-zero balances and adds USD values
- For each balance:
  - Attempts to get price from Wallex market data
  - Falls back to CoinGecko if Wallex doesn't have price
  - Calculates total USD value
- Returns list of enriched balance dictionaries

#### `async def get_fallback_price(self, symbol)`
- Maps common symbols to CoinGecko IDs (BTC->bitcoin, ETH->ethereum, etc.)
- Makes HTTP GET to CoinGecko API for current USD price
- Returns price or 0 on failure
- Includes error handling for network issues

#### `async def get_24h_data(self, symbol)`
- Similar to price lookup but fetches 24h change data
- Uses CoinGecko for price change percentage
- Returns change data or default values on failure

### FastAPI Application Setup

#### Application Instance
```python
app = FastAPI(title="Wallex Wallet Dashboard", version="1.0.0")
```

#### Template and Static File Configuration
- Uses Jinja2Templates with "templates" directory
- Serves static files from "static" directory at "/static" path

#### Dependency Injection
- `get_wallet_service()`: Creates WalletService instance
  - Reads API key from environment variable "WALLEX_API_KEY"
  - Uses testnet mode if "WALLEX_TESTNET" is set
  - Raises HTTPException if API key missing

### API Endpoints

#### `GET /` - Dashboard Page
- Renders main dashboard HTML template
- Passes request object to template for context
- Template: "dashboard.html"

#### `GET /api/balances` - Balance Data API
- Async endpoint that uses WalletService to get enriched balances
- Returns JSON array of balance objects
- Each balance includes: currency, balance, price_usd, value_usd, change_24h
- Error handling returns 500 with error details

#### `GET /api/account` - Account Info API
- Returns account information from Wallex API
- Simple proxy to WalletService.get_account_info()
- Returns JSON object or 500 on error

### Error Handling Strategy

- Service methods use try/except with logging for external API failures
- API endpoints catch service exceptions and return appropriate HTTP status codes
- Graceful degradation: missing prices default to 0 rather than failing entirely
- Connection pooling via aiohttp for efficient external API calls

### Environment Configuration

Required environment variables:
- `WALLEX_API_KEY`: Your Wallex API key
- `WALLEX_TESTNET` (optional): Set to use testnet endpoints

### Development Server

The file includes a `if __name__ == "__main__"` block that:
- Runs uvicorn server on localhost:8000
- Enables auto-reload for development
- Configures logging level

### Integration Points

- Wallex Python client for exchange API access
- CoinGecko API for fallback price data and 24h statistics
- SQLite database (if using database.py features - potential extension)
- Frontend via Jinja2 templates and static files

### Performance Considerations

- Uses async/await throughout for non-blocking I/O
- aiohttp ClientSession for connection pooling
- Caches could be added for frequently accessed price data
- Rate limiting considerations for CoinGecko API (currently not implemented)

### Extension Ideas

- Add WebSocket support for real-time balance updates
- Implement caching layer for price data
- Add user authentication and multi-user support
- Integrate with database.py for historical portfolio tracking
- Add more chart types and visualization options