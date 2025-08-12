"""
Integration Tests for Wallex Python Client

This module contains integration tests that test the interaction between
different components of the library.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import json
import logging

from wallex import WallexClient, WallexAsyncClient, WallexConfig
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexAsyncWebSocketClient
from wallex.exceptions import WallexAPIError, WallexWebSocketError, WallexValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class TestClientIntegration:
    """Integration tests for the main client classes"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(
            api_key="test_key",
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
        
        # Test that client properly delegates to REST client
        markets = client.get_markets()
        
        assert markets is not None
        assert mock_get.called
        
        # Verify the request was made with correct parameters
        mock_get.assert_called_once()
        
        # Check that configuration is properly passed
        assert client.config.api_key == "test_key"
        assert client.config.testnet == True
    
    @patch('wallex.socket.socketio.Client')
    def test_client_websocket_integration(self, mock_socketio, config):
        """Test integration between main client and WebSocket client"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # Test WebSocket connection through main client
        callback = Mock()
        
        # Mock successful connection
        mock_sio.connected = True
        client.websocket.is_connected = True
        
        # Test subscription through main client
        client.subscribe_trades("BTCIRT", callback)
        
        # Verify WebSocket client was called
        assert "BTCIRT@trade" in client.websocket.subscriptions
        assert client.websocket.callbacks["BTCIRT@trade"] == callback
    
    @pytest.mark.asyncio
    @patch('wallex.socket.socketio.AsyncClient')
    async def test_async_client_integration(self, mock_async_socketio, config):
        """Test async client integration"""
        mock_sio = Mock()
        mock_async_socketio.return_value = mock_sio
        
        client = WallexAsyncClient(config)
        
        # Test that async client maintains same interface
        assert hasattr(client, 'rest')
        assert hasattr(client, 'websocket')
        
        # Test configuration propagation
        assert client.config.api_key == "test_key"
        assert client.config.testnet == True
    
    @patch('wallex.rest.requests.Session.get')
    @patch('wallex.socket.socketio.Client')
    def test_full_client_workflow(self, mock_socketio, mock_get, config, mock_rest_response):
        """Test complete client workflow with both REST and WebSocket"""
        mock_get.return_value = mock_rest_response
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # Step 1: Get market data via REST
        markets = client.get_markets()
        assert markets is not None
        
        # Step 2: Setup WebSocket
        callback = Mock()
        mock_sio.connected = True
        client.websocket.is_connected = True
        
        # Step 3: Subscribe to real-time updates
        client.subscribe_trades("BTCIRT", callback)
        
        # Verify both components work together
        assert mock_get.called
        assert "BTCIRT@trade" in client.websocket.subscriptions


class TestErrorHandlingIntegration:
    """Test error handling across components"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(
            api_key="test_key",
            testnet=True
        )
    
    @patch('wallex.rest.requests.Session.get')
    def test_rest_error_propagation(self, mock_get, config):
        """Test that REST errors are properly propagated through main client"""
        # Mock API error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "message": "Invalid symbol"
        }
        mock_get.return_value = mock_response
        
        client = WallexClient(config)
        
        with pytest.raises(WallexValidationError):
            client.get_markets()
    
    @patch('wallex.socket.socketio.Client')
    def test_websocket_error_handling(self, mock_socketio, config):
        """Test WebSocket error handling in integrated client"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        # Mock connection failure
        mock_sio.connect.side_effect = Exception("Connection failed")
        
        client = WallexClient(config)
        
        with pytest.raises(WallexWebSocketError):
            client.websocket.connect()


class TestConcurrencyIntegration:
    """Test concurrent operations"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(
            api_key="test_key",
            testnet=True
        )
    
    @patch('wallex.rest.requests.Session.get')
    def test_concurrent_rest_operations(self, mock_get, config):
        """Test concurrent REST operations"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "success": True,
            "result": {"data": "test"}
        }
        mock_get.return_value = mock_response
        
        client = WallexClient(config)
        
        # Simulate concurrent requests
        import threading
        results = []
        errors = []
        
        def make_request():
            try:
                result = client.get_markets()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(results) == 5
        assert len(errors) == 0
    
    @patch('wallex.socket.socketio.Client')
    def test_concurrent_websocket_subscriptions(self, mock_socketio, config):
        """Test concurrent WebSocket subscriptions"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # Mock connection
        mock_sio.connected = True
        client.websocket.is_connected = True
        
        # Subscribe to multiple symbols concurrently
        symbols = ["BTCIRT", "ETHIRT", "LTCIRT"]
        callbacks = []
        
        for symbol in symbols:
            callback = Mock()
            callbacks.append(callback)
            client.subscribe_trades(symbol, callback)
        
        # Verify all subscriptions were registered
        expected_channels = {f"{symbol}@trade" for symbol in symbols}
        assert expected_channels.issubset(client.websocket.subscriptions)


class TestDataFlowIntegration:
    """Test data flow between components"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(
            api_key="test_key",
            testnet=True
        )
    
    @patch('wallex.rest.requests.Session.get')
    def test_market_data_flow(self, mock_get, config):
        """Test market data retrieval and processing"""
        # Mock market data response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "markets": [
                    {
                        "symbol": "BTCIRT",
                        "baseAsset": "BTC",
                        "quoteAsset": "IRT",
                        "status": "TRADING"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        client = WallexClient(config)
        markets = client.get_markets()
        
        assert markets["success"] == True
        assert "result" in markets
        assert "markets" in markets["result"]
        assert len(markets["result"]["markets"]) > 0
    
    @patch('wallex.socket.socketio.Client')
    def test_realtime_data_flow(self, mock_socketio, config):
        """Test real-time data handling through WebSocket"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexClient(config)
        
        # Setup callback to capture data
        received_data = []
        
        def data_handler(channel, data):
            received_data.append((channel, data))
        
        # Mock connection and subscription
        mock_sio.connected = True
        client.websocket.is_connected = True
        
        # Subscribe to trades
        client.subscribe_trades("BTCIRT", data_handler)
        
        # Simulate incoming data
        test_data = {
            "symbol": "BTCIRT",
            "price": "50000.00",
            "quantity": "0.1",
            "side": "buy"
        }
        
        # Trigger the callback directly (simulating WebSocket message)
        callback = client.websocket.callbacks["BTCIRT@trade"]
        callback("BTCIRT@trade", test_data)
        
        # Verify data was processed
        assert len(received_data) == 1
        assert received_data[0][0] == "BTCIRT@trade"
        assert received_data[0][1] == test_data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])