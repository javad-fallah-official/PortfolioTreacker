"""
Integration Tests for Wallex Python Client

This module contains integration tests that test the interaction between
different components of the library.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import json

from wallex import WallexClient, WallexAsyncClient, WallexConfig
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexAsyncWebSocketClient
from wallex.exceptions import WallexAPIError, WallexWebSocketError


class TestClientIntegration:
    """Integration tests for the main client classes"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(
            api_key="test_key",
            secret_key="test_secret",
            testnet=True
        )
    
    @pytest.fixture
    def mock_rest_response(self):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "markets": [
                    {"symbol": "BTCIRT", "baseAsset": "BTC", "quoteAsset": "IRT"}
                ]
            }
        }
        return mock_response
    
    @patch('wallex.rest.requests.Session.get')
    def test_client_rest_integration(self, mock_get, config, mock_rest_response):
        """Test integration between main client and REST client"""
        mock_get.return_value = mock_rest_response
        
        client = WallexClient(config)
        
        # Test that main client delegates to REST client
        result = client.get_markets()
        
        assert result["success"] is True
        assert "markets" in result["result"]
        mock_get.assert_called_once()
    
    @patch('wallex.socket.socketio.Client')
    def test_client_websocket_integration(self, mock_socketio, config):
        """Test integration between main client and WebSocket client"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # Test WebSocket connection through main client
        client.connect_websocket()
        
        assert client.websocket is not None
        mock_sio.connect.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('wallex.rest.requests.Session.get')
    async def test_async_client_integration(self, mock_get, config, mock_rest_response):
        """Test async client integration"""
        mock_get.return_value = mock_rest_response
        
        client = WallexAsyncClient(config)
        
        # Test async operations
        result = await client.get_markets()
        
        assert result["success"] is True
        assert "markets" in result["result"]
    
    @patch('wallex.rest.requests.Session.get')
    @patch('wallex.socket.socketio.Client')
    def test_full_client_workflow(self, mock_socketio, mock_get, config, mock_rest_response):
        """Test complete client workflow"""
        mock_get.return_value = mock_rest_response
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # 1. Get market data
        markets = client.get_markets()
        assert markets["success"] is True
        
        # 2. Connect WebSocket
        client.connect_websocket()
        assert client.websocket is not None
        
        # 3. Subscribe to updates
        callback = Mock()
        client.subscribe_trades("BTCIRT", callback)
        
        # 4. Simulate receiving data
        mock_sio.emit.assert_called()
        
        # 5. Disconnect
        client.disconnect_websocket()
        mock_sio.disconnect.assert_called()


class TestErrorHandlingIntegration:
    """Test error handling across components"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(testnet=True, max_retries=2)
    
    @patch('wallex.rest.requests.Session.get')
    def test_rest_error_propagation(self, mock_get, config):
        """Test error propagation from REST to main client"""
        # Mock error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_get.return_value = mock_response
        
        client = WallexClient(config)
        
        with pytest.raises(WallexAPIError) as exc_info:
            client.get_markets()
        
        assert "Invalid request" in str(exc_info.value)
    
    @patch('wallex.socket.socketio.Client')
    def test_websocket_error_propagation(self, mock_socketio, config):
        """Test WebSocket error propagation"""
        mock_sio = Mock()
        mock_sio.connect.side_effect = Exception("Connection failed")
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        with pytest.raises(WallexWebSocketError):
            client.connect_websocket()
    
    @patch('wallex.rest.requests.Session.get')
    def test_retry_mechanism_integration(self, mock_get, config):
        """Test retry mechanism across components"""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.ok = False
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {"error": "Server error"}
        
        mock_response_success = Mock()
        mock_response_success.ok = True
        mock_response_success.json.return_value = {"success": True, "result": {}}
        
        mock_get.side_effect = [mock_response_fail, mock_response_success]
        
        client = WallexClient(config)
        result = client.get_markets()
        
        assert result["success"] is True
        assert mock_get.call_count == 2  # Should retry once


class TestConfigurationIntegration:
    """Test configuration integration across components"""
    
    def test_config_propagation_to_rest(self):
        """Test configuration propagation to REST client"""
        config = WallexConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://custom.api.com",
            timeout=30,
            max_retries=5
        )
        
        client = WallexClient(config)
        rest_client = client.rest
        
        assert rest_client.config.api_key == "test_key"
        assert rest_client.config.base_url == "https://custom.api.com"
        assert rest_client.config.timeout == 30
        assert rest_client.config.max_retries == 5
    
    def test_config_propagation_to_websocket(self):
        """Test configuration propagation to WebSocket client"""
        config = WallexConfig(
            api_key="test_key",
            websocket_url="wss://custom.ws.com",
            testnet=False
        )
        
        with patch('wallex.socket.socketio.Client') as mock_socketio:
            client = WallexClient(config)
            client.connect_websocket()
            
            ws_client = client.websocket
            assert ws_client.config.websocket_url == "wss://custom.ws.com"
            assert ws_client.config.testnet is False
    
    def test_testnet_configuration_integration(self):
        """Test testnet configuration across all components"""
        config = WallexConfig(testnet=True)
        client = WallexClient(config)
        
        # Check that testnet URLs are used
        assert "testnet" in client.rest.config.base_url.lower() or "test" in client.rest.config.base_url.lower()
        
        with patch('wallex.socket.socketio.Client'):
            client.connect_websocket()
            ws_config = client.websocket.config
            assert ws_config.testnet is True


class TestDataFlowIntegration:
    """Test data flow between components"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(testnet=True)
    
    @patch('wallex.rest.requests.Session.get')
    @patch('wallex.socket.socketio.Client')
    def test_rest_to_websocket_data_flow(self, mock_socketio, mock_get, config):
        """Test data flow from REST to WebSocket"""
        # Mock REST response with market data
        mock_rest_response = Mock()
        mock_rest_response.ok = True
        mock_rest_response.json.return_value = {
            "success": True,
            "result": {
                "markets": [
                    {"symbol": "BTCIRT", "baseAsset": "BTC", "quoteAsset": "IRT"}
                ]
            }
        }
        mock_get.return_value = mock_rest_response
        
        # Mock WebSocket
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # 1. Get markets from REST
        markets = client.get_markets()
        symbols = [market["symbol"] for market in markets["result"]["markets"]]
        
        # 2. Connect WebSocket and subscribe to those markets
        client.connect_websocket()
        
        for symbol in symbols:
            client.subscribe_trades(symbol, lambda data: None)
        
        # Verify WebSocket subscriptions were made
        assert mock_sio.emit.call_count == len(symbols)
    
    @pytest.mark.asyncio
    @patch('wallex.socket.socketio.AsyncClient')
    async def test_websocket_data_processing(self, mock_socketio, config):
        """Test WebSocket data processing integration"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexAsyncWebSocketClient(config)
        
        # Track received data
        received_data = []
        
        def data_handler(data):
            received_data.append(data)
        
        await client.subscribe_trades("BTCIRT", data_handler)
        
        # Simulate receiving WebSocket data
        test_data = {
            "symbol": "BTCIRT",
            "price": "50000",
            "quantity": "0.1",
            "timestamp": 1234567890
        }
        
        # Trigger the callback manually (simulating WebSocket event)
        if client.subscriptions.get("trades_BTCIRT"):
            client.subscriptions["trades_BTCIRT"](test_data)
        
        assert len(received_data) == 1
        assert received_data[0] == test_data


class TestConcurrencyIntegration:
    """Test concurrent operations integration"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(testnet=True)
    
    @pytest.mark.asyncio
    @patch('wallex.rest.requests.Session.get')
    async def test_concurrent_rest_operations(self, mock_get, config):
        """Test concurrent REST operations"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True, "result": {}}
        mock_get.return_value = mock_response
        
        client = WallexAsyncClient(config)
        
        # Run multiple operations concurrently
        tasks = [
            client.get_markets(),
            client.get_market_stats("BTCIRT"),
            client.get_orderbook("BTCIRT"),
            client.get_trades("BTCIRT")
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 4
        assert all(result["success"] for result in results)
        assert mock_get.call_count == 4
    
    @pytest.mark.asyncio
    @patch('wallex.socket.socketio.AsyncClient')
    async def test_concurrent_websocket_subscriptions(self, mock_socketio, config):
        """Test concurrent WebSocket subscriptions"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexAsyncWebSocketClient(config)
        
        symbols = ["BTCIRT", "ETHIRT", "LTCIRT"]
        callbacks = [Mock() for _ in symbols]
        
        # Subscribe to multiple symbols concurrently
        tasks = [
            client.subscribe_trades(symbol, callback)
            for symbol, callback in zip(symbols, callbacks)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all subscriptions were made
        assert len(client.subscriptions) == len(symbols)
        for symbol in symbols:
            assert f"trades_{symbol}" in client.subscriptions


if __name__ == '__main__':
    pytest.main([__file__, '-v'])