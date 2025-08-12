# Wallex REST Client - Deep Reference for AI

This document details the structure and behavior of the REST client implemented in wallex/rest.py.

Targets: <mcfile name="rest.py" path="c:\Users\jack\Documents\GitHub\PortfolioTreacker\wallex\rest.py"></mcfile>

## Overview

- Provides a typed, retry-capable interface to Wallex HTTP API.
- Centralizes request building, authentication, error handling, and JSON parsing.

## Core Class: WallexRestClient

Constructor
- `__init__(config: WallexConfig)`
  - Stores the provided configuration.
  - Creates a requests.Session with:
    - Base headers including Content-Type, User-Agent, and optional API key header.
    - Timeouts derived from config.
    - SSL verification flag and proxies if configured.
  - Sets internal retry/backoff parameters from config: max_retries, retry_delay.

Internal Request Method
- `_make_request(method, endpoint, params=None, data=None, authenticated=False)`
  - Validates that API key exists when `authenticated=True`; otherwise raises authentication error.
  - Builds full URL using base_url + endpoint.
  - Applies query params (filters None), serializes body for POST/PUT/PATCH.
  - Handles retries with exponential backoff (based on max_retries, retry_delay).
  - Network errors: timeout, connection, general request exceptions are retried and then mapped to custom exceptions.
  - Response handling:
    - Non-2xx: parses JSON if possible; 429 mapped to rate limit exception with Retry-After; other codes mapped via exceptions.handle_http_error.
    - 2xx: parses JSON. If the JSON carries an error/success flag, uses exceptions.create_exception_from_response to raise detailed errors.
  - Returns parsed JSON payload for successful calls.

Convenience Helpers
- URL/path constants come from types.WallexEndpoints; avoid hardcoding paths.
- Query building uses utils.build_query_string conventions when helpful.

## Public Endpoints (no auth)

- `get_markets()`
  - Returns list of markets/instruments supported.
- `get_market_stats(symbol)`
  - Returns 24h statistics for a given symbol.
- `get_orderbook(symbol, limit=None)`
  - Returns bids/asks at depth (limit optional by API).
- `get_trades(symbol, limit=50)`
  - Recent public trades for symbol.
- `get_klines(symbol, interval, start=None, end=None, limit=None)`
  - Historical OHLCV; supports time window and pagination by limit.
- `get_currencies()`
  - Returns currency metadata supported by the exchange.

## Authenticated Endpoints (require API key)

- `get_account_info()`
  - Account-level metadata and permissions.
- `get_balances()`
  - All currency balances for the account.
- `get_balance(currency)`
  - Single currency balance.
- `create_order(symbol, side, type, quantity, price=None, time_in_force=None, client_order_id=None, ...)`
  - Places a new order; supports market/limit types and TIF where applicable.
- `get_orders(symbol=None, status=None, limit=None, ...)`
  - Queries open/closed orders optionally filtered.
- `get_order(order_id=None, client_order_id=None)`
  - Fetch single order by id or client id.
- `cancel_order(order_id=None, client_order_id=None)`
  - Cancel a specific order.
- `cancel_all_orders(symbol=None)`
  - Bulk cancel by symbol.

Notes
- Methods follow consistent pattern of parameter validation, calling `_make_request`, and returning JSON.
- For fields like symbol/side/type, values and validation align with wallex/types.py Literals.

## Error Handling

- Uses exceptions.WallexAPIError and specialized subclasses.
- HTTP 429 triggers WallexRateLimitError with backoff hint when available.
- API payload error codes are mapped via ERROR_CODE_MAPPING to produce specific exceptions (e.g., insufficient funds, invalid symbol).
- Network issues raise WallexNetworkError or WallexTimeoutError with context.

## Rate Limiting and Retries

- Respects config.max_retries and config.retry_delay for transient failures.
- Exponential backoff pattern reduces pressure on the API during errors.
- Consider tuning in WallexConfig based on deployment environment.

## Security Considerations

- API key is never logged.
- Sensitive headers are applied only when needed.
- SSL verification is enabled by default unless disabled explicitly in config.

## Extension Strategy

- Add new endpoint path constant to wallex/types.py.
- Implement thin wrapper method in this class calling `_make_request`.
- If authentication rules differ, set `authenticated=True` accordingly.
- Add parameter validation using types and utils validators where appropriate.