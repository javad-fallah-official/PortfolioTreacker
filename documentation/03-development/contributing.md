# Contributing to Wallex Python Client

Thank you for your interest in contributing to the Wallex Python Client! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)
- [API Guidelines](#api-guidelines)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a branch for your changes
5. Make your changes
6. Test your changes
7. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- UV package manager
- Git

### Setup Instructions

```bash
# Clone your fork
git clone https://github.com/yourusername/wallex-python-client.git
cd wallex-python-client

# Install dependencies
uv sync --dev

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install
```

### Environment Variables

For testing authenticated endpoints, create a `.env` file:

```bash
WALLEX_API_KEY=your_test_api_key
WALLEX_SECRET_KEY=your_test_secret_key
WALLEX_TESTNET=true  # Use testnet for development
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-endpoint`
- `fix/websocket-connection-issue`
- `docs/update-readme`
- `refactor/improve-error-handling`

### Commit Messages

Follow conventional commit format:
- `feat: add support for new trading endpoint`
- `fix: resolve WebSocket reconnection issue`
- `docs: update API documentation`
- `test: add unit tests for order management`
- `refactor: improve error handling logic`

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=wallex_client

# Run specific test file
uv run pytest tests/test_rest_client.py

# Run tests with verbose output
uv run pytest -v
```

### Test Categories

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test API interactions (requires test credentials)
3. **WebSocket Tests**: Test real-time data connections
4. **Mock Tests**: Test with simulated API responses

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names
- Include both positive and negative test cases
- Mock external API calls when appropriate
- Test error conditions and edge cases

Example test structure:

```python
import pytest
from wallex_client import WallexClient

class TestWallexClient:
    def test_get_markets_success(self):
        """Test successful market data retrieval"""
        # Test implementation
        pass
    
    def test_get_markets_api_error(self):
        """Test handling of API errors"""
        # Test implementation
        pass
```

## Submitting Changes

### Pull Request Process

1. Ensure your code follows the style guidelines
2. Add or update tests for your changes
3. Update documentation if needed
4. Ensure all tests pass
5. Update the changelog
6. Submit a pull request with a clear description

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Changelog updated
```

## Style Guidelines

### Python Code Style

We follow PEP 8 with some modifications:

```bash
# Format code
uv run black .

# Sort imports
uv run isort .

# Lint code
uv run flake8

# Type checking
uv run mypy wallex_client/
```

### Code Standards

1. **Type Hints**: Use type hints for all public functions
2. **Docstrings**: Use Google-style docstrings
3. **Error Handling**: Provide meaningful error messages
4. **Logging**: Use appropriate log levels
5. **Constants**: Use uppercase for constants

Example function:

```python
async def get_market_stats(self, symbol: str) -> Dict[str, Any]:
    """
    Get market statistics for a trading pair.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        
    Returns:
        Dictionary containing market statistics
        
    Raises:
        WallexAPIError: If API request fails
        ValueError: If symbol format is invalid
    """
    if not self._validate_symbol(symbol):
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    # Implementation
```

### Documentation Style

- Use clear, concise language
- Include code examples
- Document all parameters and return values
- Provide usage examples
- Keep documentation up to date

## API Guidelines

### Adding New Endpoints

1. Check Wallex API documentation for endpoint details
2. Add endpoint URL to `wallex_types.py`
3. Implement method in appropriate client class
4. Add type hints and error handling
5. Write comprehensive tests
6. Update documentation and examples

### WebSocket Channels

1. Add channel format to `WallexWebSocketChannels`
2. Implement subscription method
3. Add event handler support
4. Test connection and data handling
5. Document usage patterns

### Error Handling

- Use custom exception classes
- Provide detailed error messages
- Include relevant context information
- Handle rate limiting gracefully
- Log errors appropriately

### Rate Limiting

- Respect API rate limits
- Implement backoff strategies
- Provide rate limit information
- Allow configuration of limits

## Security Considerations

### API Credentials

- Never commit API keys or secrets
- Use environment variables for credentials
- Validate input parameters
- Sanitize log output

### Data Handling

- Validate all input data
- Handle sensitive information carefully
- Use secure communication protocols
- Implement proper error handling

## Documentation

### Code Documentation

- Document all public APIs
- Include usage examples
- Explain complex algorithms
- Document configuration options

### User Documentation

- Keep README up to date
- Provide clear installation instructions
- Include comprehensive examples
- Document troubleshooting steps

## Release Process

### Version Numbering

We use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist

1. Update version in `pyproject.toml`
2. Update changelog
3. Run full test suite
4. Update documentation
5. Create release tag
6. Publish to PyPI

## Getting Help

### Resources

- [Wallex API Documentation](https://api-docs.wallex.ir)
- [Python AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [WebSocket Documentation](https://websockets.readthedocs.io/)

### Contact

- Create an issue for bugs or feature requests
- Start a discussion for questions
- Contact maintainers for security issues

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to the Wallex Python Client!