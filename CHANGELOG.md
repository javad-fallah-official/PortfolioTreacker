# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### Added
- Initial release of Wallex Python Client
- Complete REST API client implementation
- WebSocket client for real-time data
- Support for all Wallex API endpoints:
  - Market data (markets, order book, trades, currencies)
  - Account management (profile, balances)
  - Order management (create, cancel, history)
  - Wallet operations (deposits, withdrawals)
- WebSocket subscriptions for:
  - Real-time trades
  - Order book updates
  - Ticker data
  - Market cap updates
- Comprehensive type hints and error handling
- Rate limiting support
- Authentication with API key and secret
- Utility functions for common operations
- Extensive examples and documentation
- Support for Python 3.8+

### Features
- Async/await support for all operations
- Automatic signature generation for authenticated requests
- Built-in error handling and retry logic
- Configurable timeouts and rate limits
- Order book management utilities
- Portfolio monitoring helpers
- Market analysis tools

### Security
- Secure API key and secret handling
- HMAC SHA256 signature generation
- No credentials stored in logs
- Input validation and sanitization

## [Unreleased]

### Planned
- Advanced order types (stop-loss, take-profit)
- Streaming data aggregation
- Historical data analysis tools
- Paper trading mode
- Performance optimizations
- Additional WebSocket channels
- Webhook support
- Database integration helpers