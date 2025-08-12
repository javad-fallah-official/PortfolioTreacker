# Portfolio Tracker - Complete Project Documentation for AI

## Project Overview

This is a comprehensive cryptocurrency portfolio tracking application built around the Wallex cryptocurrency exchange API. The project provides both a Python library for interacting with Wallex and a web-based dashboard for visualizing portfolio data.

## Project Structure

```
PortfolioTreacker/
├── wallex/                    # Core Wallex API client library
│   ├── __init__.py           # Package initialization and exports
│   ├── client.py             # Main client classes (sync/async)
│   ├── config.py             # Configuration management
│   ├── exceptions.py         # Custom exception classes
│   ├── rest.py               # REST API client implementation
│   ├── socket.py             # WebSocket client implementation
│   ├── types.py              # Type definitions and constants
│   └── utils.py              # Utility functions
├── database.py               # SQLite database operations for portfolio tracking
├── wallet_ui.py              # FastAPI web application for dashboard
├── examples_modular.py       # Usage examples for the library
├── templates/                # HTML templates for web dashboard
│   ├── dashboard.html        # Main dashboard template
│   ├── live_prices.html      # Live prices page template
│   └── portfolio.html        # Portfolio view template
├── tests/                    # Test suite
├── suggestions/              # Performance and enhancement suggestions
├── docs/                     # Documentation
└── pyproject.toml           # Project configuration and dependencies
```

## Main Components

### 1. Wallex Library (`wallex/`)
A modular Python library for interacting with the Wallex cryptocurrency exchange:
- **REST API Client**: Full implementation of Wallex REST endpoints
- **WebSocket Client**: Real-time data streaming (sync and async)
- **Configuration Management**: Flexible configuration system
- **Type Definitions**: Comprehensive type hints and constants
- **Error Handling**: Custom exception hierarchy
- **Utilities**: Helper functions for common operations

### 2. Database Layer (`database.py`)
SQLite-based portfolio tracking system:
- Daily portfolio snapshots
- Asset balance tracking
- Historical data analysis
- Portfolio statistics and comparisons

### 3. Web Dashboard (`wallet_ui.py`)
FastAPI-based web application providing:
- Real-time portfolio visualization
- Asset balance monitoring
- Historical performance charts
- Live price tracking
- Responsive dashboard interface

### 4. Frontend Templates (`templates/`)
Modern HTML templates with:
- Responsive design
- Interactive charts (Chart.js)
- Real-time data updates
- Mobile-friendly interface

## Key Features

### Library Features
- **Modular Design**: Use only what you need (REST-only, WebSocket-only, or combined)
- **Async Support**: Full async/await support for high-performance applications
- **Configuration Flexibility**: Environment variables, files, or programmatic configuration
- **Comprehensive Error Handling**: Specific exceptions for different error types
- **Type Safety**: Full type hints throughout the codebase
- **Rate Limiting**: Built-in rate limiting and retry mechanisms

### Dashboard Features
- **Portfolio Overview**: Total value in USD and IRR
- **Asset Breakdown**: Individual asset balances and values
- **Historical Tracking**: Daily portfolio snapshots with trend analysis
- **Live Prices**: Real-time price updates from Wallex API
- **Performance Metrics**: Profit/loss calculations and percentage changes
- **Chart Visualizations**: Interactive charts for portfolio composition and trends

### Database Features
- **Automated Snapshots**: Daily portfolio data capture
- **Historical Analysis**: Track portfolio performance over time
- **Asset Tracking**: Individual asset balance and value history
- **Statistics**: Portfolio summary statistics and metrics
- **Data Integrity**: Unique constraints and foreign key relationships

## Technology Stack

- **Backend**: Python 3.8+, FastAPI
- **Database**: SQLite with optimized queries
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **API Client**: Requests (sync), aiohttp potential (async)
- **WebSocket**: python-socketio
- **Configuration**: Environment variables, TOML/JSON files
- **Testing**: pytest with comprehensive test coverage

## Usage Patterns

### As a Library
```python
from wallex import WallexClient

# Simple usage
client = WallexClient(api_key="your_key")
balances = client.get_balances()

# Advanced usage with custom config
from wallex import WallexConfig
config = WallexConfig(testnet=True, timeout=60)
client = WallexClient(config=config)
```

### As a Web Application
```bash
# Run the dashboard
python wallet_ui.py
# Access at http://localhost:8000
```

### Database Operations
```python
from database import PortfolioDatabase

db = PortfolioDatabase()
# Automatically saves daily snapshots
db.save_portfolio_snapshot(portfolio_data)
# Query historical data
history = db.get_portfolio_history(days=30)
```

## Development Philosophy

1. **Modularity**: Each component can be used independently
2. **Type Safety**: Comprehensive type hints for better IDE support
3. **Error Resilience**: Graceful error handling with informative messages
4. **Performance**: Efficient database queries and API usage
5. **User Experience**: Clean, responsive web interface
6. **Maintainability**: Clear code structure and comprehensive documentation

## Future Enhancements

The `suggestions/` folder contains detailed enhancement proposals for:
- Caching and performance optimization
- Enhanced error handling
- Security improvements
- Testing framework expansion
- Configuration management improvements

This project serves as both a practical portfolio tracking tool and a well-structured example of modern Python application development with web interfaces.