"""
Comprehensive performance test suite for the Portfolio Tracker application

This test suite provides complete performance testing including:
- Load testing for high-volume operations
- Stress testing for system limits
- Performance benchmarking and profiling
- Memory usage and leak detection
- Concurrent operation performance
- Database performance optimization
- API response time validation
- WebSocket throughput testing
- Resource utilization monitoring
- Scalability testing scenarios

All tests measure and validate performance metrics against defined thresholds.
"""

import pytest
import asyncio
import time
import psutil
import gc
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import memory_profiler
except ImportError:
    memory_profiler = None

from wallex import WallexClient, WallexAsyncClient, WallexConfig, WallexAPIError, OrderSide, OrderType, OrderStatus
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexWebSocketError
from database import PortfolioDatabase


class PerformanceMetrics:
    """Helper class for collecting and analyzing performance metrics"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_usage = []
        self.cpu_usage = []
        self.operation_times = []
        self.error_count = 0
        self.success_count = 0
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.memory_usage = [psutil.virtual_memory().percent]
        self.cpu_usage = [psutil.cpu_percent()]
    
    def record_operation(self, duration, success=True):
        """Record an operation's performance"""
        self.operation_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        self.memory_usage.append(psutil.virtual_memory().percent)
        self.cpu_usage.append(psutil.cpu_percent())
    
    def stop_monitoring(self):
        """Stop performance monitoring and calculate final metrics"""
        self.end_time = time.time()
        return self.get_summary()
    
    def get_summary(self):
        """Get performance summary"""
        total_time = self.end_time - self.start_time if self.end_time else 0
        
        return {
            'total_time': total_time,
            'total_operations': len(self.operation_times),
            'successful_operations': self.success_count,
            'failed_operations': self.error_count,
            'success_rate': self.success_count / max(1, len(self.operation_times)),
            'operations_per_second': len(self.operation_times) / max(0.001, total_time),
            'avg_operation_time': statistics.mean(self.operation_times) if self.operation_times else 0,
            'min_operation_time': min(self.operation_times) if self.operation_times else 0,
            'max_operation_time': max(self.operation_times) if self.operation_times else 0,
            'median_operation_time': statistics.median(self.operation_times) if self.operation_times else 0,
            'p95_operation_time': self._percentile(self.operation_times, 95) if self.operation_times else 0,
            'p99_operation_time': self._percentile(self.operation_times, 99) if self.operation_times else 0,
            'avg_memory_usage': statistics.mean(self.memory_usage) if self.memory_usage else 0,
            'max_memory_usage': max(self.memory_usage) if self.memory_usage else 0,
            'avg_cpu_usage': statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
            'max_cpu_usage': max(self.cpu_usage) if self.cpu_usage else 0
        }
    
    def _percentile(self, data, percentile):
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestDatabasePerformance:
    """Test suite for database performance scenarios"""

    @pytest.fixture
    async def performance_database(self):
        """Setup database for performance testing"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        database = PortfolioDatabase(f"sqlite:///{db_file.name}")
        await database.init()
        
        yield database
        
        await database.close()
        os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_bulk_portfolio_insertion_performance(self, performance_database, sample_portfolio_data):
        """Test performance of bulk portfolio insertions"""
        database = performance_database
        metrics = PerformanceMetrics()
        metrics.start_monitoring()
        
        # Test parameters
        num_portfolios = 100
        portfolios_data = []
        
        # Prepare test data
        for i in range(num_portfolios):
            portfolio_data = {
                'name': f'Performance Test Portfolio {i}',
                'total_value': Decimal('10000.0') + Decimal(str(i * 100)),
                'assets': sample_portfolio_data['assets'],
                'timestamp': datetime.now()
            }
            portfolios_data.append(portfolio_data)
        
        # Execute bulk insertions
        for portfolio_data in portfolios_data:
            start_time = time.time()
            try:
                portfolio_id = await database.save_portfolio_snapshot(portfolio_data)
                duration = time.time() - start_time
                metrics.record_operation(duration, success=portfolio_id is not None)
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_operation(duration, success=False)
            
            metrics.update_system_metrics()
        
        # Analyze results
        summary = metrics.stop_monitoring()
        
        # Performance assertions
        assert summary['success_rate'] >= 0.95  # 95% success rate
        assert summary['operations_per_second'] >= 50  # At least 50 ops/sec
        assert summary['avg_operation_time'] <= 0.1  # Average under 100ms
        assert summary['p95_operation_time'] <= 0.2  # 95th percentile under 200ms
        assert summary['max_memory_usage'] <= 80  # Memory usage under 80%

    @pytest.mark.asyncio
    async def test_concurrent_database_operations_performance(self, performance_database, sample_portfolio_data):
        """Test performance of concurrent database operations"""
        database = performance_database
        metrics = PerformanceMetrics()
        metrics.start_monitoring()
        
        # Test parameters
        num_concurrent_operations = 50
        
        async def database_operation(index):
            """Single database operation"""
            start_time = time.time()
            try:
                # Mix of different operations
                if index % 3 == 0:
                    # Insert operation
                    portfolio_data = {
                        'name': f'Concurrent Portfolio {index}',
                        'total_value': Decimal('5000.0'),
                        'assets': sample_portfolio_data['assets'][:2],  # Smaller dataset
                        'timestamp': datetime.now()
                    }
                    result = await database.save_portfolio_snapshot(portfolio_data)
                    success = result is not None
                elif index % 3 == 1:
                    # Query operation
                    result = await database.get_portfolio_history(days=7)
                    success = isinstance(result, list)
                else:
                    # Health check operation
                    result = await database.health()
                    success = isinstance(result, bool)
                
                duration = time.time() - start_time
                return duration, success
            except Exception as e:
                duration = time.time() - start_time
                return duration, False
        
        # Execute concurrent operations
        tasks = [database_operation(i) for i in range(num_concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, tuple):
                duration, success = result
                metrics.record_operation(duration, success)
            else:
                metrics.record_operation(1.0, False)  # Exception case
        
        # Analyze results
        summary = metrics.stop_monitoring()
        
        # Performance assertions
        assert summary['success_rate'] >= 0.90  # 90% success rate for concurrent ops
        assert summary['operations_per_second'] >= 25  # At least 25 ops/sec
        assert summary['avg_operation_time'] <= 0.2  # Average under 200ms
        assert summary['p99_operation_time'] <= 1.0  # 99th percentile under 1s

    @pytest.mark.asyncio
    async def test_database_query_performance(self, performance_database, sample_portfolio_data):
        """Test performance of database queries"""
        database = performance_database
        
        # Setup test data
        portfolio_ids = []
        for i in range(20):
            portfolio_data = {
                'name': f'Query Test Portfolio {i}',
                'total_value': Decimal('15000.0') + Decimal(str(i * 500)),
                'assets': sample_portfolio_data['assets'],
                'timestamp': datetime.now() - timedelta(days=i)
            }
            portfolio_id = await database.save_portfolio_snapshot(portfolio_data)
            portfolio_ids.append(portfolio_id)
        
        metrics = PerformanceMetrics()
        metrics.start_monitoring()
        
        # Test different query types
        query_operations = [
            ('get_portfolio_history', lambda: database.get_portfolio_history(days=30)),
            ('get_latest_snapshot', lambda: database.get_latest_snapshot()),
            ('get_portfolio_stats', lambda: database.get_portfolio_stats()),
            ('health_check', lambda: database.health()),
        ]
        
        # Execute queries multiple times
        for _ in range(10):  # 10 iterations of each query type
            for query_name, query_func in query_operations:
                start_time = time.time()
                try:
                    result = await query_func()
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=result is not None)
                except Exception as e:
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=False)
                
                metrics.update_system_metrics()
        
        # Analyze results
        summary = metrics.stop_monitoring()
        
        # Performance assertions
        assert summary['success_rate'] >= 0.98  # 98% success rate for queries
        assert summary['avg_operation_time'] <= 0.05  # Average under 50ms
        assert summary['p95_operation_time'] <= 0.1  # 95th percentile under 100ms

    @pytest.mark.asyncio
    async def test_database_memory_usage(self, performance_database, sample_portfolio_data):
        """Test database memory usage patterns"""
        database = performance_database
        
        # Monitor memory before operations
        initial_memory = psutil.virtual_memory().percent
        process = psutil.Process()
        initial_process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        portfolio_ids = []
        for i in range(100):
            portfolio_data = {
                'name': f'Memory Test Portfolio {i}',
                'total_value': Decimal('20000.0'),
                'assets': sample_portfolio_data['assets'] * 2,  # Double the assets
                'timestamp': datetime.now()
            }
            portfolio_id = await database.save_portfolio_snapshot(portfolio_data)
            portfolio_ids.append(portfolio_id)
            
            # Check memory every 10 operations
            if i % 10 == 0:
                current_memory = psutil.virtual_memory().percent
                current_process_memory = process.memory_info().rss / 1024 / 1024
                
                # Memory should not grow excessively
                assert current_memory - initial_memory <= 10  # Max 10% increase
                assert current_process_memory - initial_process_memory <= 100  # Max 100MB increase
        
        # Force garbage collection
        gc.collect()
        
        # Final memory check
        final_memory = psutil.virtual_memory().percent
        final_process_memory = process.memory_info().rss / 1024 / 1024
        
        # Memory should be reasonable after GC
        assert final_memory - initial_memory <= 15  # Max 15% increase after operations
        assert final_process_memory - initial_process_memory <= 150  # Max 150MB increase


class TestAPIPerformance:
    """Test suite for API performance scenarios"""

    @pytest.fixture
    def performance_client(self, sample_config):
        """Setup client for performance testing"""
        config = WallexConfig(
            api_key=sample_config['api_key'],
            api_secret=sample_config['api_secret']
        )
        return WallexAsyncClient(config)

    @pytest.mark.asyncio
    async def test_api_response_time_performance(self, performance_client):
        """Test API response time performance"""
        client = performance_client
        metrics = PerformanceMetrics()
        metrics.start_monitoring()
        
        # Mock API responses for consistent testing
        with patch.object(client, 'get_markets') as mock_get_markets, \
             patch.object(client, 'get_ticker') as mock_get_ticker, \
             patch.object(client, 'get_order_book') as mock_get_order_book:
            
            # Setup mock responses
            mock_get_markets.return_value = {
                'success': True,
                'result': [{'symbol': 'BTCUSDT', 'status': 'TRADING'}]
            }
            
            mock_get_ticker.return_value = {
                'success': True,
                'result': {'symbol': 'BTCUSDT', 'last_price': '45000.0'}
            }
            
            mock_get_order_book.return_value = {
                'success': True,
                'result': {'symbol': 'BTCUSDT', 'bids': [], 'asks': []}
            }
            
            # Add artificial delay to simulate network latency
            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.01)  # 10ms delay
                return mock_get_markets.return_value
            
            mock_get_markets.side_effect = delayed_response
            
            # Test API operations
            api_operations = [
                ('get_markets', lambda: client.get_markets()),
                ('get_ticker', lambda: client.get_ticker('BTCUSDT')),
                ('get_order_book', lambda: client.get_order_book('BTCUSDT')),
            ]
            
            # Execute operations multiple times
            for _ in range(20):  # 20 iterations
                for op_name, op_func in api_operations:
                    start_time = time.time()
                    try:
                        result = await op_func()
                        duration = time.time() - start_time
                        metrics.record_operation(duration, success=result.get('success', False))
                    except Exception as e:
                        duration = time.time() - start_time
                        metrics.record_operation(duration, success=False)
                    
                    metrics.update_system_metrics()
        
        # Analyze results
        summary = metrics.stop_monitoring()
        
        # Performance assertions
        assert summary['success_rate'] >= 0.95  # 95% success rate
        assert summary['avg_operation_time'] <= 0.1  # Average under 100ms
        assert summary['p95_operation_time'] <= 0.2  # 95th percentile under 200ms

    @pytest.mark.asyncio
    async def test_concurrent_api_requests_performance(self, performance_client):
        """Test performance of concurrent API requests"""
        client = performance_client
        metrics = PerformanceMetrics()
        metrics.start_monitoring()
        
        # Mock API for consistent testing
        with patch.object(client, 'get_markets') as mock_get_markets:
            mock_get_markets.return_value = {
                'success': True,
                'result': [{'symbol': 'BTCUSDT'}]
            }
            
            # Add small delay to simulate real API
            async def delayed_markets(*args, **kwargs):
                await asyncio.sleep(0.005)  # 5ms delay
                return mock_get_markets.return_value
            
            mock_get_markets.side_effect = delayed_markets
            
            # Execute concurrent requests
            num_concurrent = 50
            tasks = [client.get_markets() for _ in range(num_concurrent)]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Process results
            for result in results:
                if isinstance(result, dict):
                    metrics.record_operation(total_time / num_concurrent, success=result.get('success', False))
                else:
                    metrics.record_operation(total_time / num_concurrent, success=False)
        
        # Analyze results
        summary = metrics.stop_monitoring()
        
        # Performance assertions
        assert summary['success_rate'] >= 0.90  # 90% success rate for concurrent
        assert summary['operations_per_second'] >= 100  # At least 100 ops/sec
        assert total_time <= 1.0  # Total time under 1 second

    @pytest.mark.asyncio
    async def test_api_rate_limiting_performance(self, performance_client):
        """Test API rate limiting behavior"""
        client = performance_client
        
        # Mock rate-limited API
        call_count = 0
        rate_limit_threshold = 10
        
        async def rate_limited_api(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count > rate_limit_threshold:
                # Simulate rate limit error
                raise WallexAPIError("Rate limit exceeded", status_code=429)
            
            await asyncio.sleep(0.01)  # Small delay
            return {'success': True, 'result': []}
        
        with patch.object(client, 'get_markets', side_effect=rate_limited_api):
            metrics = PerformanceMetrics()
            metrics.start_monitoring()
            
            # Make requests until rate limited
            for i in range(15):  # Exceed rate limit
                start_time = time.time()
                try:
                    result = await client.get_markets()
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=True)
                except WallexAPIError as e:
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=False)
                    # Implement backoff strategy
                    await asyncio.sleep(0.1)  # 100ms backoff
            
            summary = metrics.stop_monitoring()
            
            # Verify rate limiting behavior
            assert summary['failed_operations'] > 0  # Some requests should fail
            assert summary['success_rate'] >= 0.6  # At least 60% should succeed initially


class TestWebSocketPerformance:
    """Test suite for WebSocket performance scenarios"""

    @pytest.fixture
    def performance_websocket(self, sample_config):
        """Setup WebSocket for performance testing"""
        return WebSocketManager("wss://api.wallex.ir/v1/ws", sample_config['api_key'])

    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, performance_websocket):
        """Test WebSocket message processing throughput"""
        ws_manager = performance_websocket
        metrics = PerformanceMetrics()
        
        received_messages = []
        
        def message_handler(data):
            received_messages.append(data)
        
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            
            await ws_manager.start()
            
            # Subscribe to ticker updates
            await ws_manager.subscribe_ticker('BTCUSDT', message_handler)
            
            metrics.start_monitoring()
            
            # Simulate high-frequency messages
            num_messages = 1000
            for i in range(num_messages):
                start_time = time.time()
                
                message = {
                    'channel': 'ticker',
                    'symbol': 'BTCUSDT',
                    'data': {
                        'last_price': f'{45000 + i}.0',
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                await ws_manager._handle_message(message)
                
                duration = time.time() - start_time
                metrics.record_operation(duration, success=True)
                
                if i % 100 == 0:  # Update system metrics every 100 messages
                    metrics.update_system_metrics()
            
            summary = metrics.stop_monitoring()
            
            # Performance assertions
            assert len(received_messages) == num_messages
            assert summary['operations_per_second'] >= 1000  # At least 1000 messages/sec
            assert summary['avg_operation_time'] <= 0.001  # Average under 1ms
            assert summary['p95_operation_time'] <= 0.005  # 95th percentile under 5ms
            
            await ws_manager.stop()

    @pytest.mark.asyncio
    async def test_websocket_subscription_performance(self, performance_websocket):
        """Test WebSocket subscription management performance"""
        ws_manager = performance_websocket
        metrics = PerformanceMetrics()
        
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            
            await ws_manager.start()
            
            metrics.start_monitoring()
            
            # Test bulk subscriptions
            symbols = [f'SYMBOL{i}USDT' for i in range(100)]
            subscription_ids = []
            
            for symbol in symbols:
                start_time = time.time()
                try:
                    sub_id = await ws_manager.subscribe_ticker(symbol, lambda data: None)
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=sub_id is not None)
                    subscription_ids.append(sub_id)
                except Exception as e:
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=False)
            
            # Test bulk unsubscriptions
            for sub_id in subscription_ids:
                start_time = time.time()
                try:
                    await ws_manager.unsubscribe(sub_id)
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=True)
                except Exception as e:
                    duration = time.time() - start_time
                    metrics.record_operation(duration, success=False)
            
            summary = metrics.stop_monitoring()
            
            # Performance assertions
            assert summary['success_rate'] >= 0.95  # 95% success rate
            assert summary['operations_per_second'] >= 200  # At least 200 ops/sec
            assert summary['avg_operation_time'] <= 0.01  # Average under 10ms
            
            await ws_manager.stop()


class TestSystemPerformance:
    """Test suite for overall system performance scenarios"""

    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, sample_config, sample_portfolio_data):
        """Test end-to-end system performance"""
        # Setup integrated system
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        try:
            config = WallexConfig(
                api_key=sample_config['api_key'],
                api_secret=sample_config['api_secret'],
                database_url=f"sqlite:///{db_file.name}"
            )
            
            client = WallexAsyncClient(config)
            database = PortfolioDatabase(config.database_url)
            portfolio_manager = PortfolioManager(database, client)
            
            await database.init()
            
            metrics = PerformanceMetrics()
            metrics.start_monitoring()
            
            # End-to-end workflow
            num_workflows = 20
            
            for i in range(num_workflows):
                workflow_start = time.time()
                
                try:
                    # Step 1: Create portfolio
                    portfolio = Portfolio(
                        name=f"E2E Performance Portfolio {i}",
                        description="End-to-end performance test"
                    )
                    
                    for asset_data in sample_portfolio_data['assets']:
                        balance = AssetBalance(
                            symbol=asset_data['symbol'],
                            quantity=Decimal(str(asset_data['quantity'])),
                            average_cost=Decimal(str(asset_data['average_cost']))
                        )
                        portfolio.add_balance(balance)
                    
                    # Step 2: Save portfolio
                    portfolio_id = await portfolio_manager.save_portfolio(portfolio)
                    
                    # Step 3: Retrieve portfolio
                    retrieved_portfolio = await portfolio_manager.get_portfolio(portfolio_id)
                    
                    # Step 4: Calculate statistics
                    stats = await portfolio_manager.calculate_portfolio_stats(portfolio_id)
                    
                    workflow_duration = time.time() - workflow_start
                    metrics.record_operation(workflow_duration, success=True)
                    
                except Exception as e:
                    workflow_duration = time.time() - workflow_start
                    metrics.record_operation(workflow_duration, success=False)
                
                metrics.update_system_metrics()
            
            summary = metrics.stop_monitoring()
            
            # Performance assertions
            assert summary['success_rate'] >= 0.95  # 95% success rate
            assert summary['operations_per_second'] >= 5  # At least 5 workflows/sec
            assert summary['avg_operation_time'] <= 1.0  # Average under 1 second
            assert summary['p95_operation_time'] <= 2.0  # 95th percentile under 2 seconds
            
            await database.close()
        
        finally:
            os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_stress_testing(self, sample_config, sample_portfolio_data):
        """Test system behavior under stress conditions"""
        # Setup system
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        try:
            config = WallexConfig(
                api_key=sample_config['api_key'],
                api_secret=sample_config['api_secret'],
                database_url=f"sqlite:///{db_file.name}"
            )
            
            database = PortfolioDatabase(config.database_url)
            await database.init()
            
            # Stress test parameters
            num_concurrent_operations = 100
            operation_duration = 30  # seconds
            
            metrics = PerformanceMetrics()
            metrics.start_monitoring()
            
            async def stress_operation(operation_id):
                """Single stress test operation"""
                operations_completed = 0
                start_time = time.time()
                
                while time.time() - start_time < operation_duration:
                    op_start = time.time()
                    try:
                        # Perform database operation
                        portfolio_data = {
                            'name': f'Stress Test Portfolio {operation_id}-{operations_completed}',
                            'total_value': Decimal('1000.0'),
                            'assets': sample_portfolio_data['assets'][:1],  # Single asset
                            'timestamp': datetime.now()
                        }
                        
                        portfolio_id = await database.save_portfolio_snapshot(portfolio_data)
                        
                        op_duration = time.time() - op_start
                        metrics.record_operation(op_duration, success=portfolio_id is not None)
                        operations_completed += 1
                        
                    except Exception as e:
                        op_duration = time.time() - op_start
                        metrics.record_operation(op_duration, success=False)
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.001)
                
                return operations_completed
            
            # Run stress test
            tasks = [stress_operation(i) for i in range(num_concurrent_operations)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            summary = metrics.stop_monitoring()
            
            # Analyze stress test results
            total_operations = sum(r for r in results if isinstance(r, int))
            
            # Stress test assertions
            assert summary['success_rate'] >= 0.80  # 80% success rate under stress
            assert total_operations >= 1000  # At least 1000 total operations
            assert summary['max_memory_usage'] <= 90  # Memory usage under 90%
            assert summary['max_cpu_usage'] <= 95  # CPU usage under 95%
            
            await database.close()
        
        finally:
            os.unlink(db_file.name)

    def test_memory_leak_detection(self, sample_config, sample_portfolio_data):
        """Test for memory leaks in long-running operations"""
        
        @memory_profiler.profile
        def memory_intensive_operation():
            """Memory-intensive operation for leak detection"""
            # Simulate creating many objects
            portfolios = []
            
            for i in range(1000):
                portfolio = Portfolio(
                    name=f"Memory Test Portfolio {i}",
                    description="Memory leak detection test"
                )
                
                for asset_data in sample_portfolio_data['assets']:
                    balance = AssetBalance(
                        symbol=asset_data['symbol'],
                        quantity=Decimal(str(asset_data['quantity'])),
                        average_cost=Decimal(str(asset_data['average_cost']))
                    )
                    portfolio.add_balance(balance)
                
                portfolios.append(portfolio)
                
                # Periodically clear some objects
                if i % 100 == 0:
                    portfolios = portfolios[-50:]  # Keep only last 50
                    gc.collect()
            
            return len(portfolios)
        
        # Monitor memory before operation
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run memory-intensive operation
        result = memory_intensive_operation()
        
        # Force garbage collection
        gc.collect()
        
        # Monitor memory after operation
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory leak assertions
        assert result > 0  # Operation completed
        assert memory_increase <= 50  # Memory increase under 50MB
        
        # Additional memory checks
        gc_stats = gc.get_stats()
        assert all(stat['uncollectable'] == 0 for stat in gc_stats)  # No uncollectable objects


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])