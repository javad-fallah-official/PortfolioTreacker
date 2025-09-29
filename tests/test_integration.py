"""
Comprehensive integration test suite for the Portfolio Tracker application

This test suite provides complete integration testing including:
- End-to-end workflow testing across multiple components
- Database and API integration scenarios
- WebSocket and real-time data integration
- Portfolio management workflow integration
- Error handling and recovery scenarios
- Performance and load testing integration
- Cross-component data flow validation
- Authentication and authorization integration
- Market data and trading integration
- Backup and recovery integration

All tests simulate real-world usage scenarios and validate complete workflows.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os

from wallex import WallexClient, WallexAsyncClient, WallexConfig, WallexAPIError, OrderSide, OrderType, OrderStatus
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexWebSocketError
from database import PortfolioDatabase


class TestEndToEndWorkflows:
    """Test suite for end-to-end workflow integration"""

    @pytest.fixture
    async def integrated_system(self, sample_config):
        """Setup integrated system for testing"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        # Initialize components
        config = WallexConfig(
            api_key=sample_config['api_key'],
            api_secret=sample_config['api_secret'],
            database_url=f"sqlite:///{db_file.name}",
            websocket_url="wss://api.wallex.ir/v1/ws"
        )
        
        client = WallexAsyncClient(config)
        database = PortfolioDatabase(config.database_url)
        ws_manager = WebSocketManager(config.websocket_url, config.api_key)
        portfolio_manager = PortfolioManager(database, client)
        market_manager = MarketDataManager(config.api_key)
        
        # Initialize database
        await database.init()
        
        system = {
            'config': config,
            'client': client,
            'database': database,
            'websocket': ws_manager,
            'portfolio': portfolio_manager,
            'market': market_manager,
            'db_file': db_file.name
        }
        
        yield system
        
        # Cleanup
        await database.close()
        os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_complete_portfolio_workflow(self, integrated_system, sample_portfolio_data):
        """Test complete portfolio management workflow"""
        system = integrated_system
        portfolio_manager = system['portfolio']
        database = system['database']
        
        # Step 1: Create initial portfolio
        portfolio = Portfolio(
            name="Integration Test Portfolio",
            description="Test portfolio for integration testing"
        )
        
        # Add initial balances
        for asset_data in sample_portfolio_data['assets']:
            balance = AssetBalance(
                symbol=asset_data['symbol'],
                quantity=Decimal(str(asset_data['quantity'])),
                average_cost=Decimal(str(asset_data['average_cost']))
            )
            portfolio.add_balance(balance)
        
        # Step 2: Save portfolio to database
        portfolio_id = await portfolio_manager.save_portfolio(portfolio)
        assert portfolio_id is not None
        
        # Step 3: Retrieve and validate portfolio
        retrieved_portfolio = await portfolio_manager.get_portfolio(portfolio_id)
        assert retrieved_portfolio is not None
        assert retrieved_portfolio.name == portfolio.name
        assert len(retrieved_portfolio.balances) == len(portfolio.balances)
        
        # Step 4: Update portfolio balances
        new_balance = AssetBalance(
            symbol="ADA",
            quantity=Decimal("1000.0"),
            average_cost=Decimal("0.45")
        )
        retrieved_portfolio.add_balance(new_balance)
        
        # Step 5: Save updated portfolio
        await portfolio_manager.update_portfolio(retrieved_portfolio)
        
        # Step 6: Verify update
        updated_portfolio = await portfolio_manager.get_portfolio(portfolio_id)
        assert len(updated_portfolio.balances) == len(portfolio.balances) + 1
        
        # Step 7: Calculate portfolio statistics
        stats = await portfolio_manager.calculate_portfolio_stats(portfolio_id)
        assert 'total_value' in stats
        assert 'asset_count' in stats
        assert 'allocation' in stats

    @pytest.mark.asyncio
    async def test_market_data_integration_workflow(self, integrated_system):
        """Test market data integration workflow"""
        system = integrated_system
        market_manager = system['market']
        client = system['client']
        
        with patch.object(client, 'get_markets') as mock_get_markets, \
             patch.object(client, 'get_ticker') as mock_get_ticker, \
             patch.object(client, 'get_order_book') as mock_get_order_book:
            
            # Mock market data responses
            mock_get_markets.return_value = {
                'success': True,
                'result': [
                    {
                        'symbol': 'BTCUSDT',
                        'base_asset': 'BTC',
                        'quote_asset': 'USDT',
                        'status': 'TRADING',
                        'min_quantity': '0.00001',
                        'max_quantity': '1000.0',
                        'min_price': '0.01',
                        'max_price': '1000000.0',
                        'price_precision': 2,
                        'quantity_precision': 8
                    }
                ]
            }
            
            mock_get_ticker.return_value = {
                'success': True,
                'result': {
                    'symbol': 'BTCUSDT',
                    'last_price': '45000.0',
                    'bid_price': '44999.0',
                    'ask_price': '45001.0',
                    'volume_24h': '1234.56789',
                    'change_24h': '500.0',
                    'change_percentage_24h': '1.12',
                    'high_24h': '46000.0',
                    'low_24h': '44000.0',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            mock_get_order_book.return_value = {
                'success': True,
                'result': {
                    'symbol': 'BTCUSDT',
                    'bids': [
                        {'price': '44999.0', 'quantity': '1.5'},
                        {'price': '44998.0', 'quantity': '2.0'}
                    ],
                    'asks': [
                        {'price': '45001.0', 'quantity': '1.2'},
                        {'price': '45002.0', 'quantity': '1.8'}
                    ],
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Step 1: Get available markets
            markets = await market_manager.get_markets()
            assert len(markets) > 0
            
            # Step 2: Get ticker data for a specific market
            ticker = await market_manager.get_ticker('BTCUSDT')
            assert ticker is not None
            assert ticker.symbol == 'BTCUSDT'
            
            # Step 3: Get order book data
            order_book = await market_manager.get_order_book('BTCUSDT')
            assert order_book is not None
            assert len(order_book.bids) > 0
            assert len(order_book.asks) > 0
            
            # Step 4: Validate market data consistency
            assert ticker.bid_price <= ticker.last_price <= ticker.ask_price
            assert order_book.get_best_bid()['price'] <= ticker.bid_price
            assert order_book.get_best_ask()['price'] >= ticker.ask_price

    @pytest.mark.asyncio
    async def test_websocket_integration_workflow(self, integrated_system):
        """Test WebSocket integration workflow"""
        system = integrated_system
        ws_manager = system['websocket']
        
        received_messages = []
        
        def ticker_callback(data):
            received_messages.append(('ticker', data))
        
        def orderbook_callback(data):
            received_messages.append(('orderbook', data))
        
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            mock_ws.receive_message = AsyncMock()
            
            # Step 1: Start WebSocket manager
            await ws_manager.start()
            assert ws_manager.is_running() is True
            
            # Step 2: Subscribe to ticker updates
            ticker_sub_id = await ws_manager.subscribe_ticker('BTCUSDT', ticker_callback)
            assert ticker_sub_id is not None
            
            # Step 3: Subscribe to order book updates
            orderbook_sub_id = await ws_manager.subscribe_orderbook('BTCUSDT', orderbook_callback)
            assert orderbook_sub_id is not None
            
            # Step 4: Simulate receiving messages
            ticker_message = {
                'channel': 'ticker',
                'symbol': 'BTCUSDT',
                'data': {
                    'last_price': '45100.0',
                    'volume_24h': '1250.0',
                    'change_24h': '600.0'
                }
            }
            
            orderbook_message = {
                'channel': 'orderbook',
                'symbol': 'BTCUSDT',
                'data': {
                    'bids': [{'price': '45099.0', 'quantity': '1.5'}],
                    'asks': [{'price': '45101.0', 'quantity': '1.2'}]
                }
            }
            
            await ws_manager._handle_message(ticker_message)
            await ws_manager._handle_message(orderbook_message)
            
            # Step 5: Verify callbacks were executed
            assert len(received_messages) == 2
            assert any(msg[0] == 'ticker' for msg in received_messages)
            assert any(msg[0] == 'orderbook' for msg in received_messages)
            
            # Step 6: Unsubscribe and cleanup
            await ws_manager.unsubscribe(ticker_sub_id)
            await ws_manager.unsubscribe(orderbook_sub_id)
            await ws_manager.stop()

    @pytest.mark.asyncio
    async def test_database_portfolio_integration(self, integrated_system, sample_portfolio_data):
        """Test database and portfolio integration"""
        system = integrated_system
        database = system['database']
        
        # Step 1: Create portfolio snapshot
        portfolio_data = {
            'name': 'Integration Test Portfolio',
            'total_value': Decimal('50000.0'),
            'assets': sample_portfolio_data['assets'],
            'timestamp': datetime.now()
        }
        
        snapshot_id = await database.save_portfolio_snapshot(portfolio_data)
        assert snapshot_id is not None
        
        # Step 2: Save individual asset balances
        for asset in portfolio_data['assets']:
            balance_data = {
                'portfolio_snapshot_id': snapshot_id,
                'symbol': asset['symbol'],
                'quantity': Decimal(str(asset['quantity'])),
                'value': Decimal(str(asset['value'])),
                'average_cost': Decimal(str(asset['average_cost'])),
                'timestamp': datetime.now()
            }
            
            balance_id = await database.save_asset_balance(balance_data)
            assert balance_id is not None
        
        # Step 3: Retrieve portfolio history
        history = await database.get_portfolio_history(days=30)
        assert len(history) > 0
        assert history[0]['id'] == snapshot_id
        
        # Step 4: Get asset balances for snapshot
        balances = await database.get_asset_balances_for_snapshot(snapshot_id)
        assert len(balances) == len(portfolio_data['assets'])
        
        # Step 5: Calculate portfolio statistics
        stats = await database.get_portfolio_stats()
        assert 'total_snapshots' in stats
        assert 'latest_value' in stats
        assert 'asset_count' in stats
        
        # Step 6: Update portfolio snapshot
        updated_data = portfolio_data.copy()
        updated_data['total_value'] = Decimal('55000.0')
        
        success = await database.update_portfolio_snapshot(snapshot_id, updated_data)
        assert success is True
        
        # Step 7: Verify update
        updated_snapshot = await database.get_latest_snapshot()
        assert updated_snapshot['total_value'] == Decimal('55000.0')

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integrated_system):
        """Test error handling across integrated components"""
        system = integrated_system
        client = system['client']
        database = system['database']
        ws_manager = system['websocket']
        
        # Test 1: API error handling
        with patch.object(client, 'get_markets', side_effect=WallexAPIError("API Error")):
            with pytest.raises(WallexAPIError):
                await client.get_markets()
        
        # Test 2: Database error handling
        with patch.object(database, 'save_portfolio_snapshot', side_effect=DatabaseError("DB Error")):
            with pytest.raises(DatabaseError):
                await database.save_portfolio_snapshot({})
        
        # Test 3: WebSocket error handling
        with patch.object(ws_manager, 'start', side_effect=WallexWebSocketError("WS Error")):
            with pytest.raises(WallexWebSocketError):
                await ws_manager.start()
        
        # Test 4: Recovery scenarios
        # Simulate database connection recovery
        with patch.object(database, 'health') as mock_health:
            mock_health.side_effect = [False, False, True]  # Fail twice, then succeed
            
            # Implement retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    health_status = await database.health()
                    if health_status:
                        break
                except Exception:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.1)
            
            assert health_status is True

    @pytest.mark.asyncio
    async def test_performance_integration(self, integrated_system, sample_portfolio_data):
        """Test performance across integrated components"""
        system = integrated_system
        database = system['database']
        portfolio_manager = system['portfolio']
        
        # Performance test: Bulk portfolio operations
        start_time = datetime.now()
        
        # Create multiple portfolios
        portfolio_ids = []
        for i in range(10):
            portfolio = Portfolio(
                name=f"Performance Test Portfolio {i}",
                description=f"Portfolio {i} for performance testing"
            )
            
            # Add sample balances
            for asset_data in sample_portfolio_data['assets']:
                balance = AssetBalance(
                    symbol=asset_data['symbol'],
                    quantity=Decimal(str(asset_data['quantity'])) * (i + 1),
                    average_cost=Decimal(str(asset_data['average_cost']))
                )
                portfolio.add_balance(balance)
            
            portfolio_id = await portfolio_manager.save_portfolio(portfolio)
            portfolio_ids.append(portfolio_id)
        
        creation_time = datetime.now() - start_time
        
        # Performance test: Bulk retrieval
        start_time = datetime.now()
        
        retrieved_portfolios = []
        for portfolio_id in portfolio_ids:
            portfolio = await portfolio_manager.get_portfolio(portfolio_id)
            retrieved_portfolios.append(portfolio)
        
        retrieval_time = datetime.now() - start_time
        
        # Performance test: Bulk statistics calculation
        start_time = datetime.now()
        
        all_stats = []
        for portfolio_id in portfolio_ids:
            stats = await portfolio_manager.calculate_portfolio_stats(portfolio_id)
            all_stats.append(stats)
        
        stats_time = datetime.now() - start_time
        
        # Verify performance metrics
        assert len(portfolio_ids) == 10
        assert len(retrieved_portfolios) == 10
        assert len(all_stats) == 10
        
        # Performance assertions (adjust thresholds as needed)
        assert creation_time.total_seconds() < 5.0  # Should create 10 portfolios in < 5 seconds
        assert retrieval_time.total_seconds() < 2.0  # Should retrieve 10 portfolios in < 2 seconds
        assert stats_time.total_seconds() < 3.0     # Should calculate stats in < 3 seconds

    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self, integrated_system, sample_portfolio_data):
        """Test concurrent operations across integrated components"""
        system = integrated_system
        portfolio_manager = system['portfolio']
        database = system['database']
        
        # Concurrent portfolio creation
        async def create_portfolio(index):
            portfolio = Portfolio(
                name=f"Concurrent Portfolio {index}",
                description=f"Portfolio {index} for concurrency testing"
            )
            
            for asset_data in sample_portfolio_data['assets']:
                balance = AssetBalance(
                    symbol=asset_data['symbol'],
                    quantity=Decimal(str(asset_data['quantity'])),
                    average_cost=Decimal(str(asset_data['average_cost']))
                )
                portfolio.add_balance(balance)
            
            return await portfolio_manager.save_portfolio(portfolio)
        
        # Create portfolios concurrently
        tasks = [create_portfolio(i) for i in range(5)]
        portfolio_ids = await asyncio.gather(*tasks)
        
        assert len(portfolio_ids) == 5
        assert all(pid is not None for pid in portfolio_ids)
        
        # Concurrent portfolio retrieval
        async def get_portfolio_stats(portfolio_id):
            portfolio = await portfolio_manager.get_portfolio(portfolio_id)
            stats = await portfolio_manager.calculate_portfolio_stats(portfolio_id)
            return portfolio, stats
        
        # Retrieve portfolios and stats concurrently
        tasks = [get_portfolio_stats(pid) for pid in portfolio_ids]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(len(result) == 2 for result in results)  # Each result has portfolio and stats

    @pytest.mark.asyncio
    async def test_data_consistency_integration(self, integrated_system, sample_portfolio_data):
        """Test data consistency across integrated components"""
        system = integrated_system
        database = system['database']
        portfolio_manager = system['portfolio']
        
        # Step 1: Create portfolio with known data
        portfolio = Portfolio(
            name="Consistency Test Portfolio",
            description="Portfolio for testing data consistency"
        )
        
        total_expected_value = Decimal('0')
        for asset_data in sample_portfolio_data['assets']:
            balance = AssetBalance(
                symbol=asset_data['symbol'],
                quantity=Decimal(str(asset_data['quantity'])),
                average_cost=Decimal(str(asset_data['average_cost']))
            )
            portfolio.add_balance(balance)
            total_expected_value += balance.quantity * balance.average_cost
        
        # Step 2: Save portfolio
        portfolio_id = await portfolio_manager.save_portfolio(portfolio)
        
        # Step 3: Retrieve and verify consistency
        retrieved_portfolio = await portfolio_manager.get_portfolio(portfolio_id)
        
        # Verify portfolio-level consistency
        assert retrieved_portfolio.name == portfolio.name
        assert len(retrieved_portfolio.balances) == len(portfolio.balances)
        
        # Verify balance-level consistency
        for original_balance in portfolio.balances:
            matching_balance = next(
                (b for b in retrieved_portfolio.balances if b.symbol == original_balance.symbol),
                None
            )
            assert matching_balance is not None
            assert matching_balance.quantity == original_balance.quantity
            assert matching_balance.average_cost == original_balance.average_cost
        
        # Step 4: Verify database-level consistency
        latest_snapshot = await database.get_latest_snapshot()
        assert latest_snapshot is not None
        
        snapshot_balances = await database.get_asset_balances_for_snapshot(latest_snapshot['id'])
        assert len(snapshot_balances) == len(portfolio.balances)
        
        # Verify calculated totals match
        calculated_total = sum(
            Decimal(str(balance['quantity'])) * Decimal(str(balance['average_cost']))
            for balance in snapshot_balances
        )
        
        # Allow for small rounding differences
        assert abs(calculated_total - total_expected_value) < Decimal('0.01')


class TestSystemIntegration:
    """Test suite for system-level integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_system_startup_shutdown(self, sample_config):
        """Test full system startup and shutdown sequence"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        try:
            # Step 1: Initialize all components
            config = WallexConfig(
                api_key=sample_config['api_key'],
                api_secret=sample_config['api_secret'],
                database_url=f"sqlite:///{db_file.name}",
                websocket_url="wss://api.wallex.ir/v1/ws"
            )
            
            client = WallexAsyncClient(config)
            database = PortfolioDatabase(config.database_url)
            ws_manager = WebSocketManager(config.websocket_url, config.api_key)
            portfolio_manager = PortfolioManager(database, client)
            market_manager = MarketDataManager(config.api_key)
            
            # Step 2: Start all components
            await database.init()
            
            with patch.object(ws_manager, '_websocket') as mock_ws:
                mock_ws.connect = AsyncMock()
                mock_ws.is_connected.return_value = True
                
                await ws_manager.start()
                
                # Step 3: Verify all components are operational
                assert await database.health() is True
                assert ws_manager.is_running() is True
                
                # Step 4: Perform basic operations
                portfolio = Portfolio(name="System Test Portfolio")
                portfolio_id = await portfolio_manager.save_portfolio(portfolio)
                assert portfolio_id is not None
                
                # Step 5: Shutdown all components
                await ws_manager.stop()
                await database.close()
                
                # Step 6: Verify clean shutdown
                assert ws_manager.is_running() is False
        
        finally:
            # Cleanup
            os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_system_recovery_scenarios(self, sample_config):
        """Test system recovery from various failure scenarios"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        try:
            config = WallexConfig(
                api_key=sample_config['api_key'],
                api_secret=sample_config['api_secret'],
                database_url=f"sqlite:///{db_file.name}",
                websocket_url="wss://api.wallex.ir/v1/ws"
            )
            
            database = PortfolioDatabase(config.database_url)
            await database.init()
            
            # Test 1: Database recovery after connection loss
            with patch.object(database, '_pool') as mock_pool:
                # Simulate connection loss
                mock_pool.acquire.side_effect = [Exception("Connection lost"), AsyncMock()]
                
                # Implement retry logic
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        async with database._pool.acquire() as conn:
                            break
                    except Exception:
                        if attempt == max_retries - 1:
                            raise
                        await asyncio.sleep(0.1)
            
            # Test 2: WebSocket recovery after disconnection
            ws_manager = WebSocketManager(config.websocket_url, config.api_key)
            
            with patch.object(ws_manager, '_websocket') as mock_ws:
                # Simulate connection, disconnection, and reconnection
                mock_ws.connect = AsyncMock()
                mock_ws.is_connected.side_effect = [True, False, True]
                
                await ws_manager.start()
                
                # Simulate disconnection handling
                if not ws_manager._websocket.is_connected():
                    await ws_manager._handle_reconnection()
                
                assert ws_manager._websocket.is_connected() is True
            
            await database.close()
        
        finally:
            os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_system_load_handling(self, sample_config, sample_portfolio_data):
        """Test system behavior under load"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        try:
            config = WallexConfig(
                api_key=sample_config['api_key'],
                api_secret=sample_config['api_secret'],
                database_url=f"sqlite:///{db_file.name}",
                websocket_url="wss://api.wallex.ir/v1/ws"
            )
            
            database = PortfolioDatabase(config.database_url)
            await database.init()
            
            # Load test: High-frequency portfolio operations
            async def high_frequency_operations():
                tasks = []
                
                # Create many concurrent portfolio snapshots
                for i in range(50):
                    portfolio_data = {
                        'name': f'Load Test Portfolio {i}',
                        'total_value': Decimal('10000.0') + Decimal(str(i * 100)),
                        'assets': sample_portfolio_data['assets'],
                        'timestamp': datetime.now()
                    }
                    
                    task = database.save_portfolio_snapshot(portfolio_data)
                    tasks.append(task)
                
                # Execute all operations concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Verify most operations succeeded
                successful_operations = sum(1 for result in results if not isinstance(result, Exception))
                assert successful_operations >= 45  # Allow for some failures under load
                
                return successful_operations
            
            # Run load test
            start_time = datetime.now()
            successful_ops = await high_frequency_operations()
            end_time = datetime.now()
            
            # Verify performance under load
            duration = (end_time - start_time).total_seconds()
            ops_per_second = successful_ops / duration
            
            assert ops_per_second > 10  # Should handle at least 10 operations per second
            
            await database.close()
        
        finally:
            os.unlink(db_file.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])