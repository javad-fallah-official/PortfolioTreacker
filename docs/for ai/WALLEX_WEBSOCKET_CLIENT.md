# Wallex WebSocket Client - Deep Reference for AI

This document details the structure and behavior of the WebSocket client implemented in wallex/socket.py.

## Overview

- Provides real-time data streaming via socket.io from Wallex.
- Supports subscription to multiple channels (trades, orderbook, ticker, market cap).
- Dispatches incoming messages to user-defined callbacks.
- Handles reconnection logic and resubscription on connect.

## Core Class: WallexWebSocketClient (synchronous)

Constructor
- `__init__(config: WallexConfig)`
  - Stores config values: ws_url, timeouts, reconnection attempts/delays.
  - Creates a `socketio.Client` with reconnection options.
  - Initializes internal state:
    - `_connected` boolean flag
    - `_lock` for thread-safe state changes
    - `_subscriptions`: set of channel strings
    - `_callbacks`: dict[channel] -> callback function
    - `executor` or thread-based dispatch for non-blocking callback execution
  - Calls `_setup_event_handlers()`

Event Handlers
- `_setup_event_handlers()` registers:
  - `connect`: mark connected, resubscribe to saved channels.
  - `disconnect`: mark disconnected.
  - `connect_error`: raise or log a `WallexConnectionError`.
  - `Broadcaster` (or exchange-specific event): main data pipe. Parses message, finds channel, and dispatches to registered callback in a background thread to avoid blocking the socket thread.
  - `error`: converts messages to `WallexWebSocketError` and surfaces/logs.

Connection Lifecycle
- `connect(timeout: float | None = None)`
  - Computes URL from config (testnet vs. prod) if not provided.
  - Calls `sio.connect(url, transports=['websocket'], wait_timeout=timeout)`.
  - Sets `_connected=True` if success; raises specific exceptions on failure.
- `disconnect()`
  - Gracefully disconnects and marks state; optionally clears subscriptions.

Subscription Internals
- `_subscribe_channel(channel: str, callback: Callable)`
  - Ensures connection (connects on-demand if not connected).
  - Stores callback in `_callbacks[channel]` and adds to `_subscriptions`.
  - Emits subscribe payload via `sio.emit('subscribe', {channel})` (actual payload format aligns with exchange protocol).
  - On error, removes stored subscription and raises `WallexWebSocketError`.

Public Subscription Helpers
- `subscribe_trades(symbol: str, callback)` -> subscribes to trades channel for given symbol.
- `subscribe_orderbook(symbol: str, side: Literal['bids','asks','both'], callback)` -> subscribes to depth updates.
- `subscribe_ticker(symbol: str, callback)` -> realtime ticker.
- `subscribe_market_cap(symbol: str | None, callback)` -> global or symbol-specific.

Callback Execution
- `_execute_callback(callback, channel, data)`
  - Wraps user callback in try/except.
  - Logs exceptions to avoid crashing the socket thread.

Resubscription Strategy
- On `connect`, iterates `_subscriptions` and re-emits subscribe messages to restore state after reconnects.

## Async Variant (if present)

- `WallexAsyncWebSocketClient` mirrors the sync client but uses `socketio.AsyncClient`.
- Async `connect`, `disconnect`, and `subscribe_*` methods use `await` and ensure callbacks can be coroutines.

## Error Handling

- Raises `WallexWebSocketError` for protocol/messages issues.
- Raises `WallexConnectionError` for connectivity problems.
- Timeouts surface as `WallexTimeoutError` when applicable.

## Extension Strategy

- To add a new channel:
  1) Define a channel name/builder in `wallex/types.py` (WallexWebSocketChannels).
  2) Add a `subscribe_<channel>` method that constructs the channel string and calls `_subscribe_channel`.
  3) Update event dispatching if message format differs.

## Notes

- User callbacks should be quick; offload heavy work to your own thread pool to keep up with message rates.
- Consider debouncing orderbook updates if throughput is high.
- Honor backoff settings from config to avoid connection storms.