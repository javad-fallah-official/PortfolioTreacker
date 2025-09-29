"""
Comprehensive test configuration for pytest

This module provides shared fixtures, utilities, and configuration for all tests
in the PortfolioTracker project. It includes fixtures for database testing,
API mocking, and common test data.
"""

import pytest
import asyncio
import sys
import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import project modules
from wallex import WallexConfig, WallexAPIError, WallexWebSocketError, OrderSide, OrderType, OrderStatus
from database import PortfolioDatabase


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config():
    """Sample WallexConfig for testing"""
    return WallexConfig(
        api_key="test_api_key_12345",
        base_url="https://api.wallex.ir",
        testnet=True,
        timeout=30,
        max_retries=3,
        rate_limit=100
    )


@pytest.fixture
def invalid_config():
    """Invalid configuration for error testing"""
    return WallexConfig(
        api_key="",  # Invalid empty API key
        base_url="invalid_url",
        timeout=-1,  # Invalid timeout
        max_retries=-1  # Invalid retries
    )


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_database_pool():
    """Mock asyncpg connection pool for database testing"""
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    
    # Setup connection acquisition
    mock_pool.acquire.return_value = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None
    
    # Setup transaction context
    mock_txn = MagicMock()
    mock_conn.transaction.return_value = MagicMock(return_value=mock_txn)
    
    return mock_pool, mock_conn


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing"""
    return {
        'account': {
            'email': 'test@example.com',
            'user_id': '12345'
        },
        'balances': {
            'total_usd_value': 1500.75,
            'total_irr_value': 75000000.0,
            'total_assets': 5,
            'assets_with_balance': 3,
            'assets': [
                {
                    'asset': 'BTC',
                    'fa_name': 'Bitcoin',
                    'free': 0.1,
                    'total': 0.1,
                    'usd_value': 500.0,
                    'irr_value': 25000000.0,
                    'has_balance': True,
                    'is_fiat': False,
                    'is_digital_gold': False
                },
                {
                    'asset': 'ETH',
                    'fa_name': 'Ethereum',
                    'free': 2.5,
                    'total': 3.0,
                    'usd_value': 750.0,
                    'irr_value': 37500000.0,
                    'has_balance': True,
                    'is_fiat': False,
                    'is_digital_gold': False
                },
                {
                    'asset': 'USDT',
                    'fa_name': 'Tether',
                    'free': 250.0,
                    'total': 250.0,
                    'usd_value': 250.75,
                    'irr_value': 12500000.0,
                    'has_balance': True,
                    'is_fiat': True,
                    'is_digital_gold': False
                }
            ]
        }
    }


@pytest.fixture
def sample_asset_balances():
    """Sample asset balance records for testing"""
    return [
        {
            'id': 1,
            'snapshot_id': 1,
            'asset_name': 'BTC',
            'asset_fa_name': 'Bitcoin',
            'free_amount': 0.5,
            'total_amount': 0.6,
            'usd_value': 600.0,
            'irr_value': 30000000.0,
            'has_balance': True,
            'is_fiat': False,
            'is_digital_gold': False
        },
        {
            'id': 2,
            'snapshot_id': 1,
            'asset_name': 'USDT',
            'asset_fa_name': 'Tether',
            'free_amount': 100.0,
            'total_amount': 100.0,
            'usd_value': 100.0,
            'irr_value': 5000000.0,
            'has_balance': True,
            'is_fiat': True,
            'is_digital_gold': False
        }
    ]


# ============================================================================
# API Response Fixtures
# ============================================================================

@pytest.fixture
def mock_api_success_response():
    """Mock successful API response"""
    return {
        "success": True,
        "result": {
            "data": "test_data",
            "timestamp": 1234567890,
            "symbols": {
                "BTCUSDT": {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "stats": {
                        "lastPrice": "45000.00",
                        "priceChangePercent": "2.5",
                        "volume": "1234.56",
                        "highPrice": "46000.00",
                        "lowPrice": "44000.00",
                        "quoteVolume": "55000000.00"
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_api_error_response():
    """Mock error API response"""
    return {
        "success": False,
        "error": {
            "code": 400,
            "message": "Bad request",
            "details": "Invalid parameters provided"
        }
    }


@pytest.fixture
def mock_websocket_message():
    """Mock WebSocket message for testing"""
    return {
        "method": "ticker",
        "params": {
            "symbol": "BTCUSDT",
            "price": "45000.00",
            "volume": "1234.56",
            "timestamp": 1234567890
        }
    }


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def portfolio_history_generator():
    """Generator for portfolio history test data"""
    def generate_history(days: int = 30) -> List[Dict]:
        history = []
        base_date = date.today()
        
        for i in range(days):
            test_date = base_date - timedelta(days=i)
            history.append({
                'id': i + 1,
                'date': test_date,
                'timestamp': datetime.combine(test_date, datetime.min.time()),
                'total_usd_value': 1000.0 + (i * 10),
                'total_irr_value': 50000000.0 + (i * 500000),
                'total_assets': 5,
                'assets_with_balance': 3,
                'account_email': 'test@example.com'
            })
        
        return history
    
    return generate_history


@pytest.fixture
def market_data_generator():
    """Generator for market data test scenarios"""
    def generate_markets(count: int = 10) -> Dict:
        markets = {}
        symbols = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK', 'UNI', 'AAVE', 'COMP', 'MKR', 'SNX']
        
        for i, symbol in enumerate(symbols[:count]):
            markets[f"{symbol}USDT"] = {
                "symbol": f"{symbol}USDT",
                "baseAsset": symbol,
                "quoteAsset": "USDT",
                "stats": {
                    "lastPrice": f"{1000 + i * 100}.00",
                    "priceChangePercent": f"{-5 + i}",
                    "volume": f"{100 + i * 10}.00",
                    "highPrice": f"{1100 + i * 100}.00",
                    "lowPrice": f"{900 + i * 100}.00",
                    "quoteVolume": f"{1000000 + i * 100000}.00"
                }
            }
        
        return {"symbols": markets}
    
    return generate_markets


# ============================================================================
# Error Simulation Fixtures
# ============================================================================

@pytest.fixture
def database_error_scenarios():
    """Common database error scenarios for testing"""
    return {
        'connection_timeout': Exception("connection timeout"),
        'pool_exhausted': Exception("connection pool exhausted"),
        'constraint_violation': Exception("unique constraint violation"),
        'foreign_key_error': Exception("foreign key constraint fails"),
        'syntax_error': Exception("syntax error in SQL statement"),
        'permission_denied': Exception("permission denied for table"),
        'connection_lost': Exception("server closed the connection unexpectedly"),
        'deadlock': Exception("deadlock detected")
    }


@pytest.fixture
def network_error_scenarios():
    """Common network error scenarios for testing"""
    return {
        'timeout': Exception("Request timeout"),
        'connection_refused': Exception("Connection refused"),
        'dns_failure': Exception("DNS resolution failed"),
        'ssl_error': Exception("SSL certificate verification failed"),
        'rate_limit': Exception("Rate limit exceeded"),
        'server_error': Exception("Internal server error")
    }


# ============================================================================
# Utility Functions
# ============================================================================

@pytest.fixture
def assert_helpers():
    """Helper functions for common assertions"""
    class AssertHelpers:
        @staticmethod
        def assert_portfolio_structure(portfolio_data: Dict):
            """Assert portfolio data has correct structure"""
            assert 'account' in portfolio_data
            assert 'balances' in portfolio_data
            assert 'email' in portfolio_data['account']
            assert 'total_usd_value' in portfolio_data['balances']
            assert 'assets' in portfolio_data['balances']
            
        @staticmethod
        def assert_asset_structure(asset_data: Dict):
            """Assert asset data has correct structure"""
            required_fields = ['asset', 'free', 'total', 'usd_value', 'has_balance']
            for field in required_fields:
                assert field in asset_data, f"Missing required field: {field}"
                
        @staticmethod
        def assert_api_response_structure(response: Dict):
            """Assert API response has correct structure"""
            assert 'success' in response
            if response['success']:
                assert 'result' in response
            else:
                assert 'error' in response
    
    return AssertHelpers()


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_metrics():
    """Performance metrics collection for testing"""
    class PerformanceMetrics:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.memory_usage = []
            
        def start_timer(self):
            import time
            self.start_time = time.time()
            
        def stop_timer(self):
            import time
            self.end_time = time.time()
            
        def get_duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
            
        def record_memory(self):
            import psutil
            process = psutil.Process()
            self.memory_usage.append(process.memory_info().rss)
    
    return PerformanceMetrics()


# ============================================================================
# Test Environment Setup
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically setup test environment for each test"""
    # Set test environment variables
    test_env = {
        'TESTING': 'true',
        'LOG_LEVEL': 'DEBUG',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'test_portfolio',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_pass'
    }
    
    with patch.dict(os.environ, test_env):
        yield