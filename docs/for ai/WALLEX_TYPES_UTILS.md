# Wallex Types and Utils - Deep Reference for AI

This document details the definitions in wallex/types.py and helper functions in wallex/utils.py to speed up reasoning and changes.

## wallex/types.py

- Purpose: Centralize type aliases, enums, constants, and structured response shapes used throughout the Wallex client.

### Literal Type Aliases
- `OrderSide`: 'BUY' | 'SELL'
- `OrderType`: 'MARKET' | 'LIMIT'
- `OrderStatus`: 'NEW' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELED' | 'REJECTED' | 'EXPIRED'
- `TimeInForce`: 'GTC' | 'IOC' | 'FOK'
- `KlineInterval`: e.g., '1m', '5m', '15m', '1h', '4h', '1d'

These are used for parameter validation and function signatures across the REST client and higher-level client wrappers.

### Endpoint Constants: WallexEndpoints
- `BASE_URL`, optionally `TESTNET_BASE_URL`
- Paths: markets, market stats, orderbook, trades, klines, currencies, account, balances, order CRUD, etc.
- Rationale: avoid magic strings; update here to reflect API changes.

### WebSocket Channels: WallexWebSocketChannels
- Static methods or constants to construct channel names for:
  - `trades(symbol)`
  - `orderbook(symbol, side)`
  - `ticker(symbol)`
  - `market_cap([symbol])`

### Structured Types (TypedDict)
- `Market`: { symbol, base, quote, ... }
- `MarketStats`: { lastPrice, highPrice, lowPrice, volume, priceChangePercent, ... }
- `OrderBookEntry`: { price, quantity }
- `Trade`: { id, price, quantity, side, timestamp }
- `Order`: { id, symbol, side, type, status, price, quantity, executedQty, cummulativeQuoteQty, timeInForce, ... }
- `Balance`: { currency, free, locked, total }
- `AccountInfo`: { makerCommission, takerCommission, permissions, ... }

These types reflect shape of JSON payloads and help with editor assistance and correctness.

### Error and Limits
- `WallexErrorCodes`: Named integer/string codes mapped by the API to business errors.
- `WallexRateLimits`: Suggested or enforced request rates per endpoint family.
- `CommonSymbols`: Handy symbol constants (e.g., BTCUSDT, ETHUSDT).

## wallex/utils.py

- Purpose: Reusable helpers for signing, validation, formatting, parsing, math, and time conversions.

### Security and Signing
- `generate_signature(secret_key: str, query_string: str) -> str`
  - Uses HMAC-SHA256(signature=HMAC(secret_key, query_string))
  - Returns lowercase hex digest used in authenticated requests when required by API.

### Time
- `get_timestamp() -> int`
  - Current epoch milliseconds.
- `convert_timestamp_to_datetime(ms: int) -> datetime`
  - Converts ms since epoch to timezone-aware datetime.

### Query and Serialization
- `build_query_string(params: dict) -> str`
  - Filters out None values; sorts keys; URL-encodes values; returns `key=value&...` string.
- `parse_json_response(text: str) -> Any`
  - Safe JSON parse with descriptive error on failure (includes snippet of payload).

### Validation
- `validate_symbol(symbol: str) -> str`
  - Ensures proper format; may normalize case.
- `validate_api_key(key: str) -> None`
  - Basic checks on length/charset; raises on invalid.
- `validate_secret_key(key: str) -> None`
  - Similar to API key validation.
- `is_valid_interval(interval: str) -> bool`
  - Checks against allowed intervals from types.KlineInterval.

### Formatting and Math
- `format_price(price: float, decimals: int=8) -> str`
  - Formats price with fixed decimals; trims trailing zeros if implemented.
- `format_quantity(qty: float, decimals: int=8) -> str`
  - Formats quantity with fixed decimals.
- `calculate_order_value(price: float, quantity: float) -> float`
  - price * quantity
- `calculate_percentage_change(old: float, new: float) -> float`
  - Returns percent change; handles zero division safely.

### Misc
- `sanitize_symbol(symbol: str) -> str`
  - Removes separators like '-' or '_' to match exchange format.
- `chunk_list(items: list, size: int) -> list[list]`
  - Splits list into chunks of fixed size for batched operations.

Notes for AI
- When adding new request methods, prefer using `build_query_string` and timestamp helpers to maintain consistency.
- Keep symbol normalization in one place (`sanitize_symbol`/`validate_symbol`) to avoid discrepancies across components.
- Ensure signature generation matches server expectations exactly; never log secrets or signatures.