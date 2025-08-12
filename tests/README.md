# Tests

This directory contains all test files for the Portfolio Tracker application.

## Test Structure

- `test_api.py` - API endpoint tests
- `test_client.py` - Client functionality tests  
- `test_wallex.py` - Wallex API integration tests
- `test_markets.py` - Market data tests
- `test_balance.py` - Balance calculation tests
- `test_account.py` - Account management tests
- `test_modular.py` - Modular library tests
- `test_integration.py` - Integration tests
- `test_performance.py` - Performance tests

## Running Tests

### Run all tests:
```bash
uv run pytest tests/
```

### Run specific test file:
```bash
uv run pytest tests/test_api.py
```

### Run with verbose output:
```bash
uv run pytest tests/ -v
```

### Run performance tests:
```bash
uv run pytest tests/test_performance.py -v
```

## Test Configuration

The `conftest.py` file contains shared test fixtures and configuration for all tests.