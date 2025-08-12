# Examples and Usage Patterns - Deep Reference for AI

This document explains the examples and usage patterns demonstrated in examples_modular.py to understand intended client usage.

## examples_modular.py

- Purpose: Demonstrate different ways to use the Wallex Python client library.
- Structure: Modular examples that can be run independently based on user needs.

### Basic Usage Example
- `basic_usage_example()`: Simplest instantiation and data retrieval.
  - Creates WallexClient with API key only.
  - Fetches markets, market stats for BTCUSDT, and account balances.
  - Demonstrates basic error handling pattern.

### REST-Only Example
- `rest_only_example()`: Shows how to use just the REST API without WebSocket.
  - Direct instantiation of WallexRestClient with minimal config.
  - Fetches orderbook, recent trades, klines data.
  - Pattern for when real-time data not needed.

### WebSocket Examples
- `websocket_example_sync()`: Demonstrates real-time data subscriptions.
  - Shows subscribe to trades, orderbook, ticker.
  - Callback functions to handle incoming messages.
  - Connection management (connect/disconnect).
  - Shows keeping connection alive with time.sleep.

- `websocket_example_async()`: Async version using WallexAsyncClient.
  - Similar subscriptions but with async/await pattern.
  - Uses asyncio.sleep instead of time.sleep.

### Full Client Examples
- `full_client_example()`: Uses both REST and WebSocket through unified WallexClient.
  - Gets account info via REST.
  - Subscribes to real-time market data via WebSocket.
  - Shows how unified client manages both protocols.

- `async_client_example()`: Async version of full client usage.
  - Similar pattern but with async context managers and await.

### Utility Functions Example
- `utility_functions_example()`: Demonstrates helper functions from utils.py.
  - Signature generation for authenticated requests.
  - Query string building.
  - Timestamp operations.
  - Validation functions.

### Configuration Examples
- `configuration_example()`: Various ways to configure the client.
  - Environment-based configuration using `WallexConfig.from_env()`.
  - File-based configuration using `WallexConfig.from_file()`.
  - Manual configuration creation.
  - Configuration updates and validation.

### Main Function
- `main()`: Orchestrates which examples to run.
  - Basic usage and configuration are enabled by default.
  - REST-only and utility examples enabled.
  - WebSocket and async examples commented out (require setup).

## Key Usage Patterns for AI

### Configuration Priority
1. Environment variables (WALLEX_API_KEY, etc.)
2. Configuration files (.json or .toml)
3. Direct instantiation with parameters

### Error Handling Strategy
- Always wrap client calls in try/except blocks.
- Catch specific exceptions from wallex.exceptions for fine-grained handling.
- Log errors appropriately for debugging.

### REST vs WebSocket Decision Tree
- REST: For one-time data fetches, account management, order placement.
- WebSocket: For real-time market data, live order updates, continuous monitoring.
- Full Client: When you need both in same application.

### Callback Patterns
- WebSocket callbacks should be lightweight and fast.
- Offload heavy processing to separate threads/tasks.
- Always handle exceptions within callbacks to avoid disconnections.

### Connection Management
- WebSocket connections should be explicitly managed (connect/disconnect).
- Use context managers when available for automatic cleanup.
- Handle reconnection scenarios gracefully.

### Performance Considerations
- Use async clients for high-throughput applications.
- Batch operations when possible (e.g., multiple symbol subscriptions).
- Configure appropriate timeouts and retry policies.

### Security Best Practices
- Never hardcode API keys in source files.
- Use environment variables or secure configuration files.
- Enable SSL verification (default behavior).
- Be cautious with logging to avoid exposing sensitive data.

### Testing and Development
- Use testnet configuration for development/testing.
- Start with basic examples before adding complexity.
- Test error scenarios (invalid symbols, network issues, etc.).

## Extension Patterns

When extending the client:
1. Follow the established error handling patterns.
2. Add new examples to demonstrate new features.
3. Update configuration schema if new settings needed.
4. Maintain backward compatibility in public APIs.