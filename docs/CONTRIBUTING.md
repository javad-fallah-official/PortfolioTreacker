# Contributing to Wallex Python Client

Thank you for your interest in contributing to the Wallex Python Client! This document provides guidelines and information for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contributing Guidelines](#contributing-guidelines)
5. [Code Style](#code-style)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Issue Reporting](#issue-reporting)
10. [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow:

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome newcomers and help them get started
- **Be collaborative**: Work together to improve the project
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone has different skill levels

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/your-username/wallex-python-client.git
cd wallex-python-client
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/original-repo/wallex-python-client.git
```

## Development Setup

### Using uv (Recommended)

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Verify Setup

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check
uv run mypy wallex

# Run examples
uv run examples_modular.py
```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

1. **Bug fixes**: Fix issues in the codebase
2. **Feature additions**: Add new functionality
3. **Documentation improvements**: Enhance docs, examples, or comments
4. **Performance optimizations**: Improve speed or memory usage
5. **Test improvements**: Add or improve test coverage
6. **Code quality**: Refactoring, type hints, etc.

### Before You Start

1. **Check existing issues**: Look for related issues or discussions
2. **Create an issue**: For significant changes, create an issue first
3. **Discuss your approach**: Get feedback before implementing
4. **Keep changes focused**: One feature/fix per pull request

### Branch Naming

Use descriptive branch names:

```bash
# Feature branches
git checkout -b feature/add-websocket-reconnection
git checkout -b feature/improve-error-handling

# Bug fix branches
git checkout -b fix/rest-client-timeout
git checkout -b fix/websocket-connection-leak

# Documentation branches
git checkout -b docs/api-reference-update
git checkout -b docs/contributing-guide
```

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Quotes**: Double quotes for strings
- **Imports**: Organized with isort
- **Type hints**: Required for all public APIs

### Formatting Tools

We use automated formatting tools:

```bash
# Format code
uv run black wallex/
uv run isort wallex/

# Check formatting
uv run black --check wallex/
uv run isort --check-only wallex/

# Lint code
uv run ruff check wallex/
uv run mypy wallex/
```

### Code Structure

#### File Organization

```python
"""Module docstring describing the purpose."""

# Standard library imports
import asyncio
import json
from typing import Dict, List, Optional

# Third-party imports
import requests
import socketio

# Local imports
from .config import WallexConfig
from .exceptions import WallexAPIError
from .types import OrderSide, OrderType
```

#### Class Structure

```python
class ExampleClass:
    """Class docstring with description and examples.
    
    Args:
        config: Configuration object
        timeout: Request timeout in seconds
        
    Example:
        >>> client = ExampleClass(config)
        >>> result = client.method()
    """
    
    def __init__(self, config: WallexConfig, timeout: int = 30) -> None:
        self.config = config
        self.timeout = timeout
        self._session = requests.Session()
    
    def public_method(self, param: str) -> Dict[str, Any]:
        """Public method with full documentation.
        
        Args:
            param: Description of parameter
            
        Returns:
            Dictionary containing the result
            
        Raises:
            WallexAPIError: If the API request fails
        """
        return self._private_method(param)
    
    def _private_method(self, param: str) -> Dict[str, Any]:
        """Private method with minimal documentation."""
        # Implementation
        pass
```

#### Function Documentation

```python
def utility_function(
    symbol: str,
    price: float,
    precision: int = 8
) -> str:
    """Format price with specified precision.
    
    Args:
        symbol: Trading pair symbol
        price: Price value to format
        precision: Number of decimal places (default: 8)
        
    Returns:
        Formatted price string
        
    Example:
        >>> format_price("BTCIRT", 1234.5678, 2)
        "1234.57"
    """
    return f"{price:.{precision}f}"
```

### Type Hints

Use comprehensive type hints:

```python
from typing import Dict, List, Optional, Union, Callable, Any

# Function signatures
def process_data(
    data: List[Dict[str, Any]],
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Union[str, int, float]]:
    pass

# Class attributes
class Client:
    config: WallexConfig
    session: requests.Session
    subscriptions: Dict[str, Callable]
```

## Testing

### Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_wallex.py           # Main test suite
├── test_integration.py      # Integration tests
├── test_performance.py      # Performance tests
└── test_specific_module.py  # Module-specific tests
```

### Writing Tests

#### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch

from wallex.rest import WallexRestClient
from wallex.config import WallexConfig
from wallex.exceptions import WallexAPIError


class TestWallexRestClient:
    """Test suite for WallexRestClient."""
    
    @pytest.fixture
    def config(self):
        """Test configuration fixture."""
        return WallexConfig(testnet=True)
    
    @pytest.fixture
    def client(self, config):
        """Client fixture."""
        return WallexRestClient(config)
    
    @patch('wallex.rest.requests.Session.get')
    def test_get_markets_success(self, mock_get, client):
        """Test successful markets retrieval."""
        # Arrange
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "success": True,
            "result": {"markets": []}
        }
        mock_get.return_value = mock_response
        
        # Act
        result = client.get_markets()
        
        # Assert
        assert result["success"] is True
        assert "markets" in result["result"]
        mock_get.assert_called_once()
    
    @patch('wallex.rest.requests.Session.get')
    def test_get_markets_error(self, mock_get, client):
        """Test markets retrieval error handling."""
        # Arrange
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_get.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(WallexAPIError) as exc_info:
            client.get_markets()
        
        assert "Bad request" in str(exc_info.value)
```

#### Integration Tests

```python
@pytest.mark.integration
class TestClientIntegration:
    """Integration tests for client components."""
    
    @patch('wallex.rest.requests.Session.get')
    @patch('wallex.socket.socketio.Client')
    def test_full_workflow(self, mock_socketio, mock_get, config):
        """Test complete client workflow."""
        # Setup mocks
        mock_get.return_value = self.mock_success_response()
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        # Test workflow
        client = WallexClient(config)
        
        # REST operations
        markets = client.get_markets()
        assert markets["success"] is True
        
        # WebSocket operations
        client.connect_websocket()
        client.subscribe_trades("BTCIRT", lambda data: None)
        client.disconnect_websocket()
        
        # Verify calls
        mock_get.assert_called()
        mock_sio.connect.assert_called()
        mock_sio.disconnect.assert_called()
```

#### Async Tests

```python
@pytest.mark.asyncio
class TestAsyncClient:
    """Test suite for async client."""
    
    async def test_async_operations(self, config):
        """Test async client operations."""
        client = WallexAsyncClient(config)
        
        with patch('wallex.rest.requests.Session.get') as mock_get:
            mock_get.return_value = self.mock_success_response()
            
            # Test concurrent operations
            results = await asyncio.gather(
                client.get_markets(),
                client.get_market_stats("BTCIRT")
            )
            
            assert len(results) == 2
            assert all(r["success"] for r in results)
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=wallex --cov-report=html

# Run specific test categories
uv run pytest -m "not integration"  # Skip integration tests
uv run pytest -m "integration"      # Only integration tests
uv run pytest tests/test_rest.py    # Specific file

# Run with verbose output
uv run pytest -v -s

# Run performance tests
uv run pytest tests/test_performance.py -v
```

### Test Coverage

Maintain high test coverage:

- **Minimum**: 90% overall coverage
- **Target**: 95%+ coverage
- **Critical paths**: 100% coverage for error handling

```bash
# Generate coverage report
uv run pytest --cov=wallex --cov-report=html
open htmlcov/index.html  # View report
```

## Documentation

### Docstring Style

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int = 10) -> bool:
    """Brief description of the function.
    
    Longer description if needed. Can span multiple lines
    and include examples or additional context.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter with default value
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: If param1 is empty
        TypeError: If param2 is not an integer
        
    Example:
        >>> result = example_function("test", 20)
        >>> print(result)
        True
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    return len(param1) > param2
```

### README Updates

When adding features, update the README:

1. Add to feature list if applicable
2. Update usage examples
3. Add to API reference section
4. Update installation instructions if needed

### API Documentation

Update `docs/API.md` for:

- New endpoints or methods
- Parameter changes
- Response format changes
- New configuration options

### Examples

Update `examples_modular.py` for:

- New features
- Best practices
- Common use cases

## Pull Request Process

### Before Submitting

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run the full test suite**:
   ```bash
   uv run pytest
   uv run ruff check
   uv run mypy wallex
   ```

3. **Update documentation** if needed

4. **Add tests** for new functionality

### Pull Request Template

```markdown
## Description

Brief description of changes made.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Integration tests pass

## Checklist

- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] Corresponding changes to documentation made
- [ ] No new warnings introduced
```

### Review Process

1. **Automated checks**: CI/CD pipeline runs tests and linting
2. **Code review**: Maintainers review the code
3. **Feedback**: Address any requested changes
4. **Approval**: Get approval from maintainers
5. **Merge**: Maintainer merges the PR

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment:**
- OS: [e.g. Windows 10, Ubuntu 20.04]
- Python version: [e.g. 3.9.7]
- Library version: [e.g. 2.0.0]

**Additional context**
Add any other context about the problem here.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions.

**Additional context**
Add any other context or screenshots about the feature request here.
```

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with new version
3. **Run full test suite**
4. **Update documentation** if needed
5. **Create release PR**
6. **Tag release** after merge
7. **Publish to PyPI**

### Changelog Format

```markdown
## [2.1.0] - 2024-01-15

### Added
- New WebSocket reconnection feature
- Support for additional order types

### Changed
- Improved error handling for rate limits
- Updated default timeout values

### Fixed
- Fixed memory leak in WebSocket client
- Corrected timestamp handling in async client

### Deprecated
- Old configuration method (will be removed in v3.0.0)
```

## Getting Help

If you need help with contributing:

1. **Check existing issues** and discussions
2. **Read the documentation** thoroughly
3. **Ask questions** in GitHub Discussions
4. **Join our community** channels (if available)

## Recognition

Contributors are recognized in:

- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **GitHub contributors** page

Thank you for contributing to the Wallex Python Client! 🎉