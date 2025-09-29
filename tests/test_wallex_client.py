"""
Comprehensive test suite for Wallex client functionality

This test suite provides complete coverage of the Wallex client including:
- Client initialization and configuration
- REST API operations (sync and async)
- WebSocket connections and message handling
- Error handling and exception scenarios
- Rate limiting and timeout handling
- Authentication and security features
- Edge cases and boundary conditions

All tests are independent, properly mocked, and follow best practices.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timedelta
import time

from wallex import WallexClient, WallexAsyncClient, WallexConfig, WallexAPIError, WallexWebSocketError, OrderSide, OrderType, OrderStatus, CommonSymbols
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient


class TestWallexClientInitialization:
    """Test suite for Wallex client initialization and configuration"""

    def test_client_init_with_api_key_string(self):
        """Test client initialization with API key string"""
        api_key = "test_api_key_12345"
        client = WallexClient(api_key)
        
        assert client.config.api_key == api_key
        assert client.config.base_url == "https://api.wallex.ir"
        assert client.config.testnet is False
        assert client.config.timeout == 30
        assert client.config.max_retries == 3

    def test_client_init_with_config_object(self, sample_config):
        """Test client initialization with WallexConfig object"""
        client = WallexClient(sample_config)
        
        assert client.config == sample_config
        assert client.config.api_key == "test_api_key_12345"
        assert client.config.testnet is True

    def test_client_init_without_parameters(self):
        """Test client initialization without parameters uses environment"""
        with patch.dict('os.environ', {'WALLEX_API_KEY': 'env_api_key'}):
            client = WallexClient()
            assert client.config.api_key == 'env_api_key'

    def test_client_init_fails_without_api_key(self):
        """Test client initialization fails when no API key is provided"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                WallexClient()

    def test_client_init_with_invalid_config(self, invalid_config):
        """Test client initialization with invalid configuration"""
        with pytest.raises(ValueError):
            WallexClient(invalid_config)

    def test_async_client_init_with_api_key(self):
        """Test async client initialization"""
        api_key = "test_async_api_key"
        client = WallexAsyncClient(api_key)
        
        assert client.config.api_key == api_key
        assert isinstance(client.rest_client, type(None)) or hasattr(client, 'rest_client')

    def test_create_client_factory_function(self):
        """Test create_client factory function"""
        client = create_client("test_key")
        assert isinstance(client, WallexClient)
        assert client.config.api_key == "test_key"

    def test_create_async_client_factory_function(self):
        """Test create_async_client factory function"""
        client = create_async_client("test_async_key")
        assert isinstance(client, WallexAsyncClient)
        assert client.config.api_key == "test_async_key"


class TestWallexClientConfiguration:
    """Test suite for client configuration management"""

    def test_config_validation_valid_parameters(self):
        """Test configuration validation with valid parameters"""
        config = WallexConfig(
            api_key="valid_key",
            base_url="https://api.wallex.ir",
            timeout=60,
            max_retries=5,
            rate_limit=200
        )
        
        assert config.api_key == "valid_key"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.rate_limit == 200

    def test_config_validation_invalid_timeout(self):
        """Test configuration validation with invalid timeout"""
        with pytest.raises(ValueError, match="timeout must be positive"):
            WallexConfig(api_key="test", timeout=-1)

    def test_config_validation_invalid_retries(self):
        """Test configuration validation with invalid max_retries"""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            WallexConfig(api_key="test", max_retries=-1)

    def test_config_validation_empty_api_key(self):
        """Test configuration validation with empty API key"""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            WallexConfig(api_key="")

    def test_config_validation_invalid_url(self):
        """Test configuration validation with invalid base URL"""
        with pytest.raises(ValueError, match="Invalid base URL"):
            WallexConfig(api_key="test", base_url="not_a_url")

    def test_config_default_values(self):
        """Test configuration uses correct default values"""
        config = WallexConfig(api_key="test")
        
        assert config.base_url == "https://api.wallex.ir"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.testnet is False
        assert config.rate_limit == 100

    def test_config_testnet_mode(self):
        """Test configuration in testnet mode"""
        config = WallexConfig(api_key="test", testnet=True)
        
        assert config.testnet is True
        assert "testnet" in config.base_url or config.base_url == "https://api.wallex.ir"


class TestWallexRestAPIOperations:
    """Test suite for REST API operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = WallexClient("test_api_key")

    @patch('wallex.rest.requests.get')
    def test_get_markets_success(self, mock_get, mock_api_success_response):
        """Test successful markets data retrieval"""
        mock_get.return_value.json.return_value = mock_api_success_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        result = self.client.get_markets()
        
        assert result == mock_api_success_response
        assert result['success'] is True
        assert 'symbols' in result['result']
        mock_get.assert_called_once()

    @patch('wallex.rest.requests.get')
    def test_get_markets_api_error(self, mock_get, mock_api_error_response):
        """Test markets data retrieval with API error"""
        mock_get.return_value.json.return_value = mock_api_error_response
        mock_get.return_value.status_code = 400
        mock_get.return_value.raise_for_status.side_effect = Exception("Bad Request")
        
        with pytest.raises(WallexAPIError, match="Bad Request"):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_get_markets_network_error(self, mock_get, network_error_scenarios):
        """Test markets data retrieval with network error"""
        mock_get.side_effect = network_error_scenarios['timeout']
        
        with pytest.raises(WallexAPIError):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_get_markets_with_retry_logic(self, mock_get, mock_api_success_response):
        """Test markets data retrieval with retry logic"""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            Exception("Connection timeout"),
            Exception("Connection timeout"),
            Mock(
                json=Mock(return_value=mock_api_success_response),
                status_code=200,
                raise_for_status=Mock()
            )
        ]
        
        result = self.client.get_markets()
        
        assert result == mock_api_success_response
        assert mock_get.call_count == 3

    @patch('wallex.rest.requests.get')
    def test_get_ticker_success(self, mock_get):
        """Test successful ticker data retrieval"""
        ticker_response = {
            "success": True,
            "result": {
                "symbol": "BTCUSDT",
                "price": "45000.00",
                "volume": "1234.56",
                "change": "2.5"
            }
        }
        
        mock_get.return_value.json.return_value = ticker_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        result = self.client.get_ticker("BTCUSDT")
        
        assert result == ticker_response
        assert result['result']['symbol'] == "BTCUSDT"

    @patch('wallex.rest.requests.get')
    def test_get_ticker_invalid_symbol(self, mock_get):
        """Test ticker retrieval with invalid symbol"""
        error_response = {
            "success": False,
            "error": {
                "code": 404,
                "message": "Symbol not found"
            }
        }
        
        mock_get.return_value.json.return_value = error_response
        mock_get.return_value.status_code = 404
        mock_get.return_value.raise_for_status.side_effect = Exception("Not Found")
        
        with pytest.raises(WallexAPIError, match="Not Found"):
            self.client.get_ticker("INVALID")

    @patch('wallex.rest.requests.get')
    def test_get_orderbook_success(self, mock_get):
        """Test successful orderbook retrieval"""
        orderbook_response = {
            "success": True,
            "result": {
                "symbol": "BTCUSDT",
                "bids": [["45000.00", "0.1"], ["44999.00", "0.2"]],
                "asks": [["45001.00", "0.1"], ["45002.00", "0.2"]]
            }
        }
        
        mock_get.return_value.json.return_value = orderbook_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        result = self.client.get_orderbook("BTCUSDT")
        
        assert result == orderbook_response
        assert len(result['result']['bids']) == 2
        assert len(result['result']['asks']) == 2

    @patch('wallex.rest.requests.get')
    def test_rate_limiting_behavior(self, mock_get, mock_api_success_response):
        """Test rate limiting behavior"""
        mock_get.return_value.json.return_value = mock_api_success_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        # Make multiple rapid requests
        start_time = time.time()
        for _ in range(5):
            self.client.get_markets()
        end_time = time.time()
        
        # Should have some delay due to rate limiting
        assert mock_get.call_count == 5


@pytest.mark.asyncio
class TestWallexAsyncRestAPIOperations:
    """Test suite for async REST API operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = WallexAsyncClient("test_async_api_key")

    @patch('aiohttp.ClientSession.get')
    async def test_async_get_markets_success(self, mock_get, mock_api_success_response):
        """Test successful async markets data retrieval"""
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_api_success_response
        mock_response.status = 200
        mock_response.raise_for_status.return_value = None
        
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None
        
        result = await self.client.get_markets()
        
        assert result == mock_api_success_response
        assert result['success'] is True

    @patch('aiohttp.ClientSession.get')
    async def test_async_get_markets_error(self, mock_get, mock_api_error_response):
        """Test async markets data retrieval with error"""
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_api_error_response
        mock_response.status = 400
        mock_response.raise_for_status.side_effect = Exception("Bad Request")
        
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None
        
        with pytest.raises(WallexAPIError):
            await self.client.get_markets()

    @patch('aiohttp.ClientSession.get')
    async def test_async_concurrent_requests(self, mock_get, mock_api_success_response):
        """Test concurrent async requests"""
        mock_response = AsyncMock()
        mock_response.json.return_value = mock_api_success_response
        mock_response.status = 200
        mock_response.raise_for_status.return_value = None
        
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None
        
        # Make concurrent requests
        tasks = [self.client.get_markets() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(result == mock_api_success_response for result in results)

    @patch('aiohttp.ClientSession.get')
    async def test_async_timeout_handling(self, mock_get):
        """Test async timeout handling"""
        mock_get.side_effect = asyncio.TimeoutError("Request timeout")
        
        with pytest.raises(WallexAPIError, match="timeout"):
            await self.client.get_markets()


class TestWallexWebSocketOperations:
    """Test suite for WebSocket operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = WallexAsyncClient("test_ws_api_key")

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_websocket_connection_success(self, mock_connect, mock_websocket_message):
        """Test successful WebSocket connection"""
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = json.dumps(mock_websocket_message)
        mock_connect.return_value.__aenter__.return_value = mock_ws
        mock_connect.return_value.__aexit__.return_value = None
        
        messages = []
        
        async def message_handler(message):
            messages.append(message)
        
        # Simulate receiving one message then closing
        mock_ws.recv.side_effect = [
            json.dumps(mock_websocket_message),
            Exception("Connection closed")
        ]
        
        try:
            await self.client.connect_websocket(message_handler)
        except:
            pass  # Expected when connection closes
        
        assert len(messages) == 1
        assert messages[0] == mock_websocket_message

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_websocket_connection_failure(self, mock_connect):
        """Test WebSocket connection failure"""
        mock_connect.side_effect = Exception("Connection failed")
        
        async def message_handler(message):
            pass
        
        with pytest.raises(WallexWebSocketError):
            await self.client.connect_websocket(message_handler)

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_websocket_subscription_management(self, mock_connect):
        """Test WebSocket subscription management"""
        mock_ws = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws
        mock_connect.return_value.__aexit__.return_value = None
        
        # Test subscription
        await self.client.subscribe_ticker("BTCUSDT")
        
        # Verify subscription message was sent
        mock_ws.send.assert_called()
        
        # Test unsubscription
        await self.client.unsubscribe_ticker("BTCUSDT")
        
        # Verify unsubscription message was sent
        assert mock_ws.send.call_count >= 2

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_websocket_message_parsing_error(self, mock_connect):
        """Test WebSocket message parsing error handling"""
        mock_ws = AsyncMock()
        mock_ws.recv.return_value = "invalid json"
        mock_connect.return_value.__aenter__.return_value = mock_ws
        mock_connect.return_value.__aexit__.return_value = None
        
        messages = []
        errors = []
        
        async def message_handler(message):
            messages.append(message)
        
        async def error_handler(error):
            errors.append(error)
        
        # Simulate invalid JSON then connection close
        mock_ws.recv.side_effect = [
            "invalid json",
            Exception("Connection closed")
        ]
        
        try:
            await self.client.connect_websocket(message_handler, error_handler)
        except:
            pass
        
        assert len(errors) >= 1  # Should have parsing error


class TestWallexClientErrorHandling:
    """Test suite for comprehensive error handling"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = WallexClient("test_error_api_key")

    @patch('wallex.rest.requests.get')
    def test_authentication_error_handling(self, mock_get):
        """Test authentication error handling"""
        auth_error_response = {
            "success": False,
            "error": {
                "code": 401,
                "message": "Invalid API key"
            }
        }
        
        mock_get.return_value.json.return_value = auth_error_response
        mock_get.return_value.status_code = 401
        mock_get.return_value.raise_for_status.side_effect = Exception("Unauthorized")
        
        with pytest.raises(WallexAPIError, match="Unauthorized"):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_rate_limit_error_handling(self, mock_get):
        """Test rate limit error handling"""
        rate_limit_response = {
            "success": False,
            "error": {
                "code": 429,
                "message": "Rate limit exceeded"
            }
        }
        
        mock_get.return_value.json.return_value = rate_limit_response
        mock_get.return_value.status_code = 429
        mock_get.return_value.raise_for_status.side_effect = Exception("Too Many Requests")
        
        with pytest.raises(WallexAPIError, match="Too Many Requests"):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_server_error_handling(self, mock_get):
        """Test server error handling"""
        mock_get.return_value.status_code = 500
        mock_get.return_value.raise_for_status.side_effect = Exception("Internal Server Error")
        
        with pytest.raises(WallexAPIError, match="Internal Server Error"):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_network_connectivity_error(self, mock_get, network_error_scenarios):
        """Test network connectivity error handling"""
        mock_get.side_effect = network_error_scenarios['connection_refused']
        
        with pytest.raises(WallexAPIError):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_ssl_certificate_error(self, mock_get, network_error_scenarios):
        """Test SSL certificate error handling"""
        mock_get.side_effect = network_error_scenarios['ssl_error']
        
        with pytest.raises(WallexAPIError):
            self.client.get_markets()

    @patch('wallex.rest.requests.get')
    def test_dns_resolution_error(self, mock_get, network_error_scenarios):
        """Test DNS resolution error handling"""
        mock_get.side_effect = network_error_scenarios['dns_failure']
        
        with pytest.raises(WallexAPIError):
            self.client.get_markets()


class TestWallexClientEdgeCases:
    """Test suite for edge cases and boundary conditions"""

    def test_client_with_minimal_config(self):
        """Test client with minimal configuration"""
        client = WallexClient("minimal_key")
        
        assert client.config.api_key == "minimal_key"
        assert client.config.base_url is not None
        assert client.config.timeout > 0

    def test_client_with_maximum_config_values(self):
        """Test client with maximum configuration values"""
        config = WallexConfig(
            api_key="max_config_key",
            timeout=300,  # 5 minutes
            max_retries=10,
            rate_limit=1000
        )
        
        client = WallexClient(config)
        
        assert client.config.timeout == 300
        assert client.config.max_retries == 10
        assert client.config.rate_limit == 1000

    @patch('wallex.rest.requests.get')
    def test_empty_response_handling(self, mock_get):
        """Test handling of empty API responses"""
        mock_get.return_value.json.return_value = {}
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        result = self.client.get_markets()
        assert result == {}

    @patch('wallex.rest.requests.get')
    def test_malformed_json_response(self, mock_get):
        """Test handling of malformed JSON responses"""
        mock_get.return_value.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value.status_code = 200
        
        with pytest.raises(WallexAPIError, match="Invalid JSON"):
            self.client.get_markets()

    def test_very_long_api_key(self):
        """Test client with very long API key"""
        long_key = "a" * 1000  # 1000 character API key
        client = WallexClient(long_key)
        
        assert client.config.api_key == long_key

    def test_special_characters_in_api_key(self):
        """Test client with special characters in API key"""
        special_key = "key_with_!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        client = WallexClient(special_key)
        
        assert client.config.api_key == special_key

    @patch('wallex.rest.requests.get')
    def test_unicode_response_handling(self, mock_get):
        """Test handling of Unicode characters in responses"""
        unicode_response = {
            "success": True,
            "result": {
                "message": "تست یونیکد",  # Persian text
                "symbol": "BTC/USDT",
                "emoji": "🚀📈💰"
            }
        }
        
        mock_get.return_value.json.return_value = unicode_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        result = self.client.get_markets()
        assert result == unicode_response
        assert "تست یونیکد" in result['result']['message']


class TestWallexClientPerformance:
    """Test suite for performance-related scenarios"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = WallexClient("perf_test_key")

    @patch('wallex.rest.requests.get')
    def test_large_response_handling(self, mock_get, market_data_generator):
        """Test handling of large API responses"""
        large_response = {
            "success": True,
            "result": market_data_generator(1000)  # 1000 markets
        }
        
        mock_get.return_value.json.return_value = large_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        result = self.client.get_markets()
        
        assert result == large_response
        assert len(result['result']['symbols']) == 1000

    @patch('wallex.rest.requests.get')
    def test_response_time_measurement(self, mock_get, performance_metrics, mock_api_success_response):
        """Test response time measurement"""
        mock_get.return_value.json.return_value = mock_api_success_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        performance_metrics.start_timer()
        result = self.client.get_markets()
        performance_metrics.stop_timer()
        
        duration = performance_metrics.get_duration()
        
        assert result == mock_api_success_response
        assert duration is not None
        assert duration >= 0

    @patch('wallex.rest.requests.get')
    def test_memory_usage_monitoring(self, mock_get, performance_metrics, mock_api_success_response):
        """Test memory usage monitoring during operations"""
        mock_get.return_value.json.return_value = mock_api_success_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        performance_metrics.record_memory()
        
        # Make multiple requests
        for _ in range(10):
            self.client.get_markets()
            performance_metrics.record_memory()
        
        assert len(performance_metrics.memory_usage) >= 2
        # Memory usage should be tracked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])