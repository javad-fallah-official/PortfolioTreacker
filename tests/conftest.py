"""
Test configuration for pytest
"""

import pytest
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    from wallex.config import WallexConfig
    return WallexConfig(
        api_key="test_api_key",
        secret_key="test_secret_key",
        testnet=True,
        timeout=30,
        max_retries=3
    )

@pytest.fixture
def mock_api_response():
    """Mock API response for testing"""
    return {
        "success": True,
        "result": {
            "data": "test_data",
            "timestamp": 1234567890
        }
    }

@pytest.fixture
def mock_error_response():
    """Mock error response for testing"""
    return {
        "success": False,
        "error": {
            "code": 400,
            "message": "Bad request"
        }
    }