# Wallex Python Package - Detailed Documentation for AI

This document explains each file, class, and key function in the wallex/ package, line-by-line oriented where meaningful.

## wallex/__init__.py

- Module docstring: Describes the package purpose and modules included.
- `__version__`, `__author__`, `__email__`, `__license__`: Package metadata constants.
- Imports primary classes for easy access at package level:
  - `WallexClient`, `WallexAsyncClient`, `create_client`, `create_async_client` from client.py
  - `WallexConfig` from config.py
  - Exceptions and type aliases from exceptions.py and types.py
- Imports submodules for explicit export.
- `__all__`: Controls what public API is exposed when doing `from wallex import *`.
- `__package_info__`: Structured metadata useful for tooling or introspection.

Purpose: Provide a clean import surface so users can do `from wallex import WallexClient, WallexConfig`.

## wallex/config.py

- Module docstring: Configuration management for the Wallex library.
- Imports: os, dataclasses, typing, Path.
- `@dataclass class WallexConfig`:
  - Attributes with defaults: `base_url`, `api_key`, `timeout`, `max_retries`, `retry_delay`, `rate_limit`, `testnet`, `log_level`, `user_agent`, WebSocket settings, SSL/proxy/headers.
  - `__post_init__`:
    - Ensures `ws_url` is set based on `testnet` when not provided.
    - Loads environment variables via `_load_from_env`.
    - Validates values via `_validate`.
  - `_load_from_env`: Maps environment variables to config fields with proper type conversions.
  - `_validate`: Ensures numeric fields are positive and URLs have correct schemes.
  - `from_file(config_path)`: Loads JSON or TOML config files into a WallexConfig instance.
  - `from_env()`: Shortcut to create config using environment variables.
  - `to_dict()`: Serializes dataclass fields to dict.
  - `update(**kwargs)`: Updates fields and revalidates; raises on unknown keys.
  - `copy()`: Returns a deep copy via constructor with `to_dict()`.
- Module-level defaults:
  - `default_config = WallexConfig()` creates a global default instance.
  - `get_config()` returns `default_config`.
  - `set_config(config)` replaces `default_config`.
  - `load_config_from_file(path)` loads and sets default config.

Purpose: Centralized, validated configuration for both REST and WebSocket clients with environment support.

## wallex/exceptions.py

- Module docstring: Custom exceptions hierarchy.
- Base `WallexError(Exception)`: Holds `message`, optional `error_code`, and `response_data`. Custom `__str__` and `__repr__`.
- `WallexAPIError(WallexError)`: Adds `status_code` and custom `__str__` that includes HTTP code.
- Specialized exceptions: `WallexWebSocketError`, `WallexAuthenticationError`, `WallexPermissionError`, `WallexRateLimitError`, `WallexValidationError`, `WallexNetworkError`, `WallexTimeoutError`, `WallexConnectionError`, `WallexConfigurationError`, `WallexOrderError`, `WallexInsufficientFundsError`, `WallexMarketClosedError`, `WallexSymbolNotFoundError`.
- `ERROR_CODE_MAPPING`: Maps API error codes to exception classes.
- `create_exception_from_response(response_data, status_code)`: Chooses exception type from mapping; attaches status code and response context.
- `handle_http_error(status_code, response_data)`: Converts HTTP codes to exceptions with appropriate context.

Purpose: Consistent, rich error modeling allowing precise exception handling by callers.

## wallex/types.py

- Module docstring: Type definitions and constants.
- Type aliases using `Literal`: `OrderSide`, `OrderType`, `OrderStatus`, `TimeInForce`, `KlineInterval`.
- `WallexEndpoints`: Constants for REST endpoints; `BASE_URL` and path fragments to avoid string duplication in client code.
- `WallexWebSocketChannels`: Static helpers to build channel names for WebSocket subscriptions.
- TypedDicts: `MarketStats`, `Market`, `OrderBookEntry`, `Trade`, `Order`, `Balance`, `AccountInfo` describing response shapes.
- `WallexErrorCodes`, `WallexRateLimits`: Named constants for business rules and constraints.
- `CommonSymbols`: Useful predefined symbols.

Purpose: Strong typing and centralized constants help maintain consistency and enable IDE assistance.

## wallex/utils.py

- Module docstring: Utility helpers.
- `generate_signature(secret_key, query_string)`: Returns HMAC-SHA256 signature hex digest.
- `get_timestamp()`: Current epoch in milliseconds.
- `build_query_string(params)`: Filters None values, sorts keys, urlencodes.
- Validators: `validate_symbol`, `validate_api_key`, `validate_secret_key`.
- Formatters: `format_price`, `format_quantity`.
- Parsers: `parse_json_response` with error handling.
- Math helpers: `calculate_order_value`, `calculate_percentage_change`.
- Misc: `is_valid_interval`, `convert_timestamp_to_datetime`, `sanitize_symbol`, `chunk_list`.

Purpose: Reusable building blocks for request creation, validation, formatting, and calculations.

## wallex/rest.py

- Module docstring: REST API client implementation.
- Imports: requests, json, time, typing, datetime, config, exceptions, utils.
- `class WallexRestClient`:
  - `__init__(config)`: Creates `requests.Session`, sets timeouts, headers (Content-Type, User-Agent, API key), SSL verify, proxies.
  - `_make_request(method, endpoint, params, data, authenticated)`: Core request method with retries and exponential backoff. Handles:
    - Missing API key on authenticated endpoints (raises WallexAuthenticationError)
    - HTTP verbs (GET/POST/PUT/DELETE/PATCH)
    - Non-OK responses: parses JSON, maps 429 to WallexRateLimitError (with Retry-After), otherwise delegates to `handle_http_error`
    - Parses JSON, checks API-level `success` flag and uses `create_exception_from_response`
    - Catches timeouts, connection, general request exceptions; retries up to `max_retries` with backoff; raises specific exceptions on final failure
  - Market data methods: `get_markets`, `get_market_stats(symbol)`, `get_orderbook(symbol)`, `get_trades(symbol, limit)`, `get_klines(...)`, `get_currencies()` that call `_make_request` with proper endpoints and params.
  - Authenticated endpoints: `get_account_info`, `get_balances`, `get_balance(currency)`, `create_order(...)`, `get_orders`, `get_order(order_id)`, `cancel_order(order_id)`, `cancel_all_orders(symbol)` etc. (continue in file).

Purpose: Reliable, typed, and well-structured client to interact with all Wallex REST endpoints.

## wallex/socket.py

- Module docstring: WebSocket client implementation (synchronous and async variants in file).
- Imports: python-socketio, asyncio, logging, time, typing, datetime, threading, ThreadPoolExecutor, config, exceptions, types.
- `class WallexWebSocketClient` (sync):
  - `__init__(config)`: Initializes `socketio.Client` with reconnection settings from config. Sets up subscription sets and callback map, connection state and lock, and calls `_setup_event_handlers()`.
  - `_setup_event_handlers()`: Registers handlers for `connect`, `disconnect`, `connect_error`, `Broadcaster` (data events), and `error`.
    - On `connect`: sets state, re-subscribes to stored channels.
    - On `Broadcaster`: dispatches to stored callbacks in separate threads to avoid blocking.
  - `_execute_callback(callback, channel, data)`: Safe execution with try/except.
  - `connect(timeout)`: Derives `ws_url` from config if not provided, connects with websocket transport, confirms connection with small delay and state check; raises specific exceptions on failure.
  - `disconnect()`: Cleanly disconnects, clears subscriptions and callbacks.
  - `_subscribe_channel(channel, callback)`: Ensures connection, records subscription, emits subscribe event; cleans up on failure.
  - Public subscribe helpers: `subscribe_trades`, `subscribe_orderbook` (both sides), `subscribe_ticker`, `subscribe_market_cap`.

Purpose: Robust, reconnect-capable WebSocket client with callback-based channel subscription API.

## wallex/client.py

- Module docstring: Main client interface combining REST and WebSocket.
- Imports: typing, logging, WallexConfig, WallexRestClient, WallexWebSocketClient, WallexAsyncWebSocketClient, exceptions.
- `class WallexClient` (sync):
  - `__init__(api_key, config, **kwargs)`: Starts with `get_config().copy()` when no config; overlays api_key and any known kwargs onto config; warns on unknown kwargs; initializes `self.rest` and `self.websocket`; tracks `_ws_connected`.
  - `is_websocket_connected` property: proxy for websocket connection state.
  - `connect_websocket(timeout)`, `disconnect_websocket()`: Manage WS lifecycle with logging on errors.
  - Convenience wrappers around `WallexRestClient` for markets, trades, currencies, account, balances, orders CRUD, and cancel methods.
  - WebSocket subscription convenience methods that auto-connect if needed and forward to websocket client.
  - Context manager support: closes websocket on exit when connected.
  - `update_config(**kwargs)`: Applies updates via `config.update`, recreates REST client, rebuilds WebSocket client, and disconnects/reconnects as needed; raises WallexConfigurationError on failure.
  - `get_config()`: Returns dictionary via `config.to_dict()`.
- `class WallexAsyncClient`: Mirrors sync client with async websocket; constructs rest same way. (Async REST methods would be similar if implemented).

Purpose: One-stop interface exposing both REST and WebSocket with simple method names for consumers.

## External Interfaces

- Environment variables (e.g., WALLEX_API_KEY, WALLEX_BASE_URL) influence config.
- HTTP endpoints as defined in `types.WallexEndpoints`.
- WebSocket channels as defined in `types.WallexWebSocketChannels`.

## Notes for AI

- When modifying functionality, prefer updating constants in types.py to avoid scattering strings.
- Respect validation and retries defined in rest.py; do not duplicate request logic.
- For new endpoints, add path in types.py, then thin wrapper method in rest.py calling `_make_request`.
- For new WebSocket channels, add builder in types.py, then a `subscribe_*` method in socket.py using `_subscribe_channel`.
- For configuration changes, extend WallexConfig with new fields and update `_load_from_env`/`_validate`.
- Maintain exception usage by leveraging `create_exception_from_response` and `handle_http_error`.