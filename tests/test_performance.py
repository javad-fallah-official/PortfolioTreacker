"""
Performance and Load Tests for Wallex Python Client

This module contains performance tests to ensure the library can handle
high-throughput scenarios and concurrent operations.
"""

import pytest
import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import statistics

from wallex import WallexClient, WallexAsyncClient, WallexConfig
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexAsyncWebSocketClient


class TestPerformance:
    """Performance tests for the Wallex library"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return WallexConfig(testnet=True, timeout=10)
    
    @pytest.fixture
    def mock_response(self):
        """Mock successful response"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "success": True,
            "result": {"data": "test"}
        }
        return mock_response
    
    @patch('wallex.rest.requests.Session.get')
    def test_rest_client_throughput(self, mock_get, config, mock_response):
        """Test REST client throughput"""
        mock_get.return_value = mock_response
        client = WallexRestClient(config)
        
        # Measure time for 100 requests
        start_time = time.time()
        for _ in range(100):
            client.get_markets()
        end_time = time.time()
        
        duration = end_time - start_time
        requests_per_second = 100 / duration
        
        print(f"REST throughput: {requests_per_second:.2f} requests/second")
        assert requests_per_second > 50  # Should handle at least 50 req/s
    
    @patch('wallex.rest.requests.Session.get')
    def test_concurrent_rest_requests(self, mock_get, config, mock_response):
        """Test concurrent REST requests"""
        mock_get.return_value = mock_response
        client = WallexRestClient(config)
        
        def make_request():
            return client.get_markets()
        
        # Test with 10 concurrent threads
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in as_completed(futures)]
        end_time = time.time()
        
        duration = end_time - start_time
        assert len(results) == 50
        assert all(result["success"] for result in results)
        
        print(f"Concurrent requests completed in {duration:.2f} seconds")
        assert duration < 5.0  # Should complete within 5 seconds
    
    @pytest.mark.asyncio
    @patch('wallex.rest.requests.Session.get')
    async def test_async_client_performance(self, mock_get, config, mock_response):
        """Test async client performance"""
        mock_get.return_value = mock_response
        client = WallexAsyncClient(config)
        
        async def make_request():
            return client.get_markets()
        
        # Test 100 concurrent async requests
        start_time = time.time()
        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        requests_per_second = 100 / duration
        
        print(f"Async throughput: {requests_per_second:.2f} requests/second")
        assert len(results) == 100
        assert all(result["success"] for result in results)
        assert requests_per_second > 100  # Async should be faster
    
    def test_memory_usage_stability(self, config):
        """Test memory usage doesn't grow excessively"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create and destroy many clients
        for _ in range(100):
            client = WallexClient(config)
            # Simulate some operations
            _ = str(client)
            del client
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 50MB)
        assert memory_growth < 50 * 1024 * 1024
        print(f"Memory growth: {memory_growth / 1024 / 1024:.2f} MB")
    
    @patch('wallex.socket.socketio.Client')
    def test_websocket_connection_performance(self, mock_socketio, config):
        """Test WebSocket connection performance"""
        mock_sio = Mock()
        mock_socketio.return_value = mock_sio
        
        client = WallexWebSocketClient(config)
        
        # Measure connection time
        start_time = time.time()
        for _ in range(10):
            client.connect()
            client.disconnect()
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        print(f"Average WebSocket connect/disconnect time: {avg_time:.3f} seconds")
        assert avg_time < 0.1  # Should be very fast with mocked socket
    
    @patch('wallex.rest.requests.Session.get')
    def test_error_handling_performance(self, mock_get, config):
        """Test performance when handling errors"""
        # Mock error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_get.return_value = mock_response
        
        client = WallexRestClient(config)
        
        start_time = time.time()
        error_count = 0
        for _ in range(50):
            try:
                client.get_markets()
            except Exception:
                error_count += 1
        end_time = time.time()
        
        duration = end_time - start_time
        errors_per_second = error_count / duration
        
        print(f"Error handling rate: {errors_per_second:.2f} errors/second")
        assert error_count == 50  # All should fail
        assert errors_per_second > 20  # Should handle errors quickly


class TestLoadTesting:
    """Load testing scenarios"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(testnet=True, max_retries=1, timeout=5)
    
    @patch('wallex.rest.requests.Session.get')
    def test_sustained_load(self, mock_get, config):
        """Test sustained load over time"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True, "result": {}}
        mock_get.return_value = mock_response
        
        client = WallexRestClient(config)
        
        # Run for 30 seconds with continuous requests
        start_time = time.time()
        request_count = 0
        response_times = []
        
        while time.time() - start_time < 5:  # Run for 5 seconds in test
            req_start = time.time()
            try:
                client.get_markets()
                request_count += 1
                response_times.append(time.time() - req_start)
            except Exception as e:
                print(f"Request failed: {e}")
            
            time.sleep(0.01)  # Small delay between requests
        
        total_duration = time.time() - start_time
        avg_response_time = statistics.mean(response_times) if response_times else 0
        requests_per_second = request_count / total_duration
        
        print(f"Sustained load results:")
        print(f"  Duration: {total_duration:.2f} seconds")
        print(f"  Total requests: {request_count}")
        print(f"  Requests/second: {requests_per_second:.2f}")
        print(f"  Average response time: {avg_response_time:.4f} seconds")
        
        assert request_count > 100  # Should handle many requests
        assert avg_response_time < 0.1  # Response time should be reasonable
    
    @pytest.mark.asyncio
    async def test_websocket_subscription_load(self, config):
        """Test WebSocket with many subscriptions"""
        with patch('wallex.socket.socketio.AsyncClient') as mock_socketio:
            mock_sio = Mock()
            mock_socketio.return_value = mock_sio
            
            client = WallexAsyncWebSocketClient(config)
            
            # Subscribe to many channels
            symbols = [f"SYMBOL{i}" for i in range(100)]
            
            start_time = time.time()
            for symbol in symbols:
                await client.subscribe_trades(symbol, lambda data: None)
            end_time = time.time()
            
            subscription_time = end_time - start_time
            subscriptions_per_second = len(symbols) / subscription_time
            
            print(f"WebSocket subscription performance:")
            print(f"  Subscriptions: {len(symbols)}")
            print(f"  Time: {subscription_time:.2f} seconds")
            print(f"  Rate: {subscriptions_per_second:.2f} subscriptions/second")
            
            assert len(client.subscriptions) == len(symbols)
            assert subscriptions_per_second > 50  # Should be fast


class TestStressTests:
    """Stress tests to find breaking points"""
    
    @pytest.fixture
    def config(self):
        return WallexConfig(testnet=True, timeout=1, max_retries=1)
    
    def test_client_creation_stress(self, config):
        """Test creating many client instances"""
        clients = []
        start_time = time.time()
        
        try:
            for i in range(1000):
                client = WallexClient(config)
                clients.append(client)
                
                if i % 100 == 0:
                    print(f"Created {i} clients...")
        except Exception as e:
            print(f"Failed at {len(clients)} clients: {e}")
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        print(f"Created {len(clients)} clients in {creation_time:.2f} seconds")
        print(f"Rate: {len(clients) / creation_time:.2f} clients/second")
        
        # Cleanup
        del clients
        
        assert len(clients) >= 500  # Should handle at least 500 clients
    
    @patch('wallex.rest.requests.Session.get')
    def test_rapid_fire_requests(self, mock_get, config):
        """Test rapid-fire requests without delays"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"success": True, "result": {}}
        mock_get.return_value = mock_response
        
        client = WallexRestClient(config)
        
        # Fire requests as fast as possible
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        for _ in range(500):
            try:
                client.get_markets()
                success_count += 1
            except Exception:
                error_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        total_requests = success_count + error_count
        
        print(f"Rapid-fire results:")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Rate: {total_requests / duration:.2f} requests/second")
        
        # Most requests should succeed
        success_rate = success_count / total_requests
        assert success_rate > 0.9  # At least 90% success rate


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])