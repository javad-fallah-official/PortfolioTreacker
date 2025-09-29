"""
Comprehensive test suite for API operations

This test suite provides complete coverage of API operations including:
- REST API client functionality
- Market data retrieval and processing
- Error handling and exception scenarios
- Rate limiting and throttling
- Data validation and sanitization
- Edge cases and boundary conditions

All tests are independent, properly mocked, and follow best practices.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from wallex import WallexClient, WallexAsyncClient, WallexConfig, WallexAPIError
from wallex.rest import WallexRestClient
from wallex.utils import validate_symbol, format_price


class TestWallexRestClient:
    """Test suite for REST API client operations"""

    @pytest.fixture
    def rest_client(self, sample_config):
        """Setup REST client for testing"""
        config = WallexConfig(
            api_key=sample_config['api_key'],
            base_url="https://api.wallex.ir",
            timeout=30
        )
        return WallexRestClient(config)

    @pytest.mark.asyncio
    async def test_get_markets_success(self, rest_client, mock_api_success_response):
        """Test successful markets retrieval"""
        mock_response = {
            "result": [
                {"symbol": "BTCIRT", "baseAsset": "BTC", "quoteAsset": "IRT"},
                {"symbol": "ETHIRT", "baseAsset": "ETH", "quoteAsset": "IRT"}
            ]
        }
        
        with patch.object(rest_client, '_make_request', return_value=mock_response):
            markets = await rest_client.get_markets()
            
            assert isinstance(markets, dict)
            assert "result" in markets
            assert len(markets["result"]) == 2
            assert markets["result"][0]["symbol"] == "BTCIRT"

    @pytest.mark.asyncio
    async def test_get_ticker_success(self, rest_client):
        """Test successful ticker retrieval"""
        mock_response = {
            "result": {
                "symbol": "BTCIRT",
                "price": "1500000000",
                "change": "2.5",
                "volume": "100.5"
            }
        }
        
        with patch.object(rest_client, '_make_request', return_value=mock_response):
            ticker = await rest_client.get_ticker("BTCIRT")
            
            assert ticker["result"]["symbol"] == "BTCIRT"
            assert ticker["result"]["price"] == "1500000000"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, rest_client):
        """Test API error handling"""
        with patch.object(rest_client, '_make_request', side_effect=WallexAPIError("API Error", 400)):
            with pytest.raises(WallexAPIError):
                await rest_client.get_markets()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, rest_client):
        """Test rate limiting behavior"""
        with patch.object(rest_client, '_make_request', side_effect=WallexAPIError("Rate limit exceeded", 429)):
            with pytest.raises(WallexAPIError) as exc_info:
                await rest_client.get_markets()
            
            assert exc_info.value.status_code == 429

    def test_request_validation(self, rest_client):
        """Test request parameter validation"""
        # Test symbol validation
        assert validate_symbol("BTCIRT") is True
        assert validate_symbol("") is False
        assert validate_symbol(None) is False
        
        # Test amount validation
        assert validate_amount(Decimal("100.5")) is True
        assert validate_amount(Decimal("0")) is False
        assert validate_amount(Decimal("-10")) is False


class TestMarketDataOperations:
    """Test suite for market data operations"""

    @pytest.fixture
    def async_client(self, sample_config):
        """Setup async client for testing"""
        config = WallexConfig(
            api_key=sample_config['api_key'],
            base_url="https://api.wallex.ir"
        )
        return WallexAsyncClient(config)

    @pytest.mark.asyncio
    async def test_get_orderbook_success(self, async_client):
        """Test successful orderbook retrieval"""
        mock_orderbook = {
            "result": {
                "asks": [["1500000000", "0.1"], ["1500100000", "0.2"]],
                "bids": [["1499900000", "0.15"], ["1499800000", "0.25"]]
            }
        }
        
        with patch.object(async_client.rest, 'get_orderbook', return_value=mock_orderbook):
            orderbook = await async_client.get_orderbook("BTCIRT")
            
            assert "result" in orderbook
            assert "asks" in orderbook["result"]
            assert "bids" in orderbook["result"]
            assert len(orderbook["result"]["asks"]) == 2

    @pytest.mark.asyncio
    async def test_get_trades_success(self, async_client):
        """Test successful trades retrieval"""
        mock_trades = {
            "result": [
                {
                    "id": "12345",
                    "price": "1500000000",
                    "quantity": "0.1",
                    "time": "2024-01-01T12:00:00Z",
                    "isBuyerMaker": True
                }
            ]
        }
        
        with patch.object(async_client.rest, 'get_trades', return_value=mock_trades):
            trades = await async_client.get_trades("BTCIRT")
            
            assert "result" in trades
            assert len(trades["result"]) == 1
            assert trades["result"][0]["id"] == "12345"

    @pytest.mark.asyncio
    async def test_invalid_symbol_error(self, async_client):
        """Test error handling for invalid symbols"""
        with patch.object(async_client.rest, 'get_ticker', side_effect=WallexAPIError("Invalid symbol", 400)):
            with pytest.raises(WallexAPIError):
                await async_client.get_ticker("INVALID")


class TestUtilityFunctions:
    """Test suite for utility functions"""

    def test_format_price(self):
        """Test price formatting utility"""
        assert format_price(Decimal("1500000000")) == "1,500,000,000"
        assert format_price(Decimal("0.00001")) == "0.00001"
        assert format_price(Decimal("0")) == "0"

    def test_validate_symbol(self):
        """Test symbol validation utility"""
        # Valid symbols
        assert validate_symbol("BTCIRT") is True
        assert validate_symbol("ETHUSDT") is True
        
        # Invalid symbols
        assert validate_symbol("") is False
        assert validate_symbol("BTC") is False  # Too short
        assert validate_symbol("BTCIRTEXTRA") is False  # Too long
        assert validate_symbol("btcirt") is False  # Lowercase
        assert validate_symbol("BTC-IRT") is False  # Invalid characters

    def test_validate_amount(self):
        """Test amount validation utility"""
        # Valid amounts
        assert validate_amount(Decimal("100")) is True
        assert validate_amount(Decimal("0.001")) is True
        assert validate_amount(Decimal("1000000")) is True
        
        # Invalid amounts
        assert validate_amount(Decimal("0")) is False
        assert validate_amount(Decimal("-10")) is False
        assert validate_amount(None) is False


class TestErrorScenarios:
    """Test suite for error scenarios and edge cases"""

    @pytest.fixture
    def client_with_invalid_config(self):
        """Setup client with invalid configuration"""
        config = WallexConfig(
            api_key="",  # Invalid empty API key
            base_url="invalid_url",
            timeout=-1
        )
        return WallexAsyncClient(config)

    @pytest.mark.asyncio
    async def test_network_timeout(self, sample_config):
        """Test network timeout handling"""
        config = WallexConfig(
            api_key=sample_config['api_key'],
            timeout=0.001  # Very short timeout
        )
        client = WallexAsyncClient(config)
        
        with patch('aiohttp.ClientSession.get', side_effect=asyncio.TimeoutError()):
            with pytest.raises(WallexAPIError):
                await client.get_markets()

    @pytest.mark.asyncio
    async def test_connection_error(self, sample_config):
        """Test connection error handling"""
        config = WallexConfig(
            api_key=sample_config['api_key'],
            base_url="https://nonexistent.api.com"
        )
        client = WallexAsyncClient(config)
        
        with patch('aiohttp.ClientSession.get', side_effect=ConnectionError("Connection failed")):
            with pytest.raises(WallexAPIError):
                await client.get_markets()

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, async_client):
        """Test handling of invalid JSON responses"""
        with patch.object(async_client.rest, '_make_request', return_value="invalid json"):
            with pytest.raises(WallexAPIError):
                await async_client.get_markets()

    def test_configuration_validation(self):
        """Test configuration parameter validation"""
        # Valid configuration
        config = WallexConfig(api_key="valid_key")
        assert config.api_key == "valid_key"
        
        # Invalid configurations should raise appropriate errors
        with pytest.raises(ValueError):
            WallexConfig(api_key="", timeout=-1)


class TestPerformanceScenarios:
    """Test suite for performance-related scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client):
        """Test handling of concurrent API requests"""
        mock_response = {"result": {"symbol": "BTCIRT", "price": "1500000000"}}
        
        with patch.object(async_client.rest, 'get_ticker', return_value=mock_response):
            # Make multiple concurrent requests
            tasks = [async_client.get_ticker("BTCIRT") for _ in range(10)]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 10
            for result in results:
                assert result["result"]["symbol"] == "BTCIRT"

    @pytest.mark.asyncio
    async def test_request_retry_logic(self, async_client):
        """Test request retry logic on failures"""
        # Mock first call to fail, second to succeed
        mock_response = {"result": {"symbol": "BTCIRT"}}
        
        with patch.object(async_client.rest, '_make_request') as mock_request:
            mock_request.side_effect = [
                WallexAPIError("Temporary error", 500),
                mock_response
            ]
            
            # Should retry and eventually succeed
            result = await async_client.get_ticker("BTCIRT")
            assert result["result"]["symbol"] == "BTCIRT"
            assert mock_request.call_count == 2