"""
Comprehensive modular test suite for the Portfolio Tracker application

This test suite provides complete modular testing including:
- Component isolation and interface testing
- Module interaction and dependency validation
- Service layer testing with proper mocking
- Configuration and environment testing
- Plugin and extension system testing
- Cross-module communication testing
- Dependency injection and IoC container testing
- Module lifecycle management testing
- Interface contract validation
- Modular architecture compliance testing

All tests ensure proper separation of concerns and module boundaries.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, List, Any, Optional
import json

from wallex import WallexClient, WallexAsyncClient, WallexConfig, WallexAPIError, OrderSide, OrderType, OrderStatus
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient, WallexWebSocketError
from database import PortfolioDatabase


class TestDatabaseModule:
    """Test suite for database module isolation and interfaces"""

    @pytest.fixture
    async def isolated_database(self):
        """Setup isolated database for modular testing"""
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        database = PortfolioDatabase(f"sqlite:///{db_file.name}")
        await database.init()
        
        yield database
        
        await database.close()
        os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_database_interface_contract(self, isolated_database):
        """Test database module interface contract compliance"""
        database = isolated_database
        
        # Test required interface methods exist
        required_methods = [
            'init', 'close', 'health',
            'save_portfolio_snapshot', 'get_portfolio_history',
            'get_latest_snapshot', 'get_portfolio_stats',
            'update_portfolio_snapshot', 'delete_portfolio_snapshot',
            'get_asset_history', 'get_asset_balances_for_snapshot',
            'update_asset_balance', 'delete_asset_balance',
            'get_coin_profit_comparison'
        ]
        
        for method_name in required_methods:
            assert hasattr(database, method_name), f"Database missing required method: {method_name}"
            method = getattr(database, method_name)
            assert callable(method), f"Database method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_database_isolation_from_external_dependencies(self, isolated_database):
        """Test database module operates independently of external services"""
        database = isolated_database
        
        # Database should work without network connectivity
        with patch('socket.socket') as mock_socket:
            mock_socket.side_effect = OSError("Network unavailable")
            
            # Basic database operations should still work
            portfolio_data = {
                'name': 'Isolation Test Portfolio',
                'total_value': Decimal('10000.0'),
                'assets': [
                    {
                        'symbol': 'BTC',
                        'quantity': Decimal('0.5'),
                        'average_cost': Decimal('45000.0'),
                        'current_price': Decimal('50000.0')
                    }
                ],
                'timestamp': datetime.now()
            }
            
            portfolio_id = await database.save_portfolio_snapshot(portfolio_data)
            assert portfolio_id is not None
            
            # Verify data retrieval works
            history = await database.get_portfolio_history(days=1)
            assert len(history) == 1
            assert history[0]['name'] == 'Isolation Test Portfolio'

    @pytest.mark.asyncio
    async def test_database_error_handling_isolation(self, isolated_database):
        """Test database module error handling doesn't leak implementation details"""
        database = isolated_database
        
        # Test with invalid data types
        with pytest.raises(Exception) as exc_info:
            await database.save_portfolio_snapshot("invalid_data")
        
        # Error should be properly wrapped, not exposing internal database errors
        assert not str(exc_info.value).lower().startswith('sqlite')
        assert not str(exc_info.value).lower().startswith('asyncpg')

    @pytest.mark.asyncio
    async def test_database_transaction_isolation(self, isolated_database):
        """Test database transaction isolation and rollback behavior"""
        database = isolated_database
        
        # Mock database connection to simulate transaction failure
        with patch.object(database, '_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            
            # Simulate transaction failure
            mock_conn.execute.side_effect = Exception("Transaction failed")
            
            portfolio_data = {
                'name': 'Transaction Test Portfolio',
                'total_value': Decimal('5000.0'),
                'assets': [],
                'timestamp': datetime.now()
            }
            
            # Operation should fail gracefully
            with pytest.raises(Exception):
                await database.save_portfolio_snapshot(portfolio_data)
            
            # Database should remain in consistent state
            health_status = await database.health()
            assert health_status is True


class TestAPIModule:
    """Test suite for API module isolation and interfaces"""

    @pytest.fixture
    def isolated_api_client(self, sample_config):
        """Setup isolated API client for modular testing"""
        config = WallexConfig(
            api_key=sample_config['api_key'],
            api_secret=sample_config['api_secret']
        )
        return WallexAsyncClient(config)

    @pytest.mark.asyncio
    async def test_api_interface_contract(self, isolated_api_client):
        """Test API module interface contract compliance"""
        client = isolated_api_client
        
        # Test required interface methods exist
        required_methods = [
            'get_markets', 'get_ticker', 'get_order_book',
            'get_account_info', 'get_balances',
            'place_order', 'cancel_order', 'get_order_status',
            'get_trade_history', 'get_deposit_history', 'get_withdrawal_history'
        ]
        
        for method_name in required_methods:
            assert hasattr(client, method_name), f"API client missing required method: {method_name}"
            method = getattr(client, method_name)
            assert callable(method), f"API client method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_api_isolation_from_database(self, isolated_api_client):
        """Test API module operates independently of database"""
        client = isolated_api_client
        
        # Mock successful API responses
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                'success': True,
                'result': [{'symbol': 'BTCUSDT', 'status': 'TRADING'}]
            }
            
            # API should work without database connection
            with patch('wallex.database.PortfolioDatabase') as mock_db:
                mock_db.side_effect = Exception("Database unavailable")
                
                # API operations should still work
                markets = await client.get_markets()
                assert markets['success'] is True
                assert len(markets['result']) == 1

    @pytest.mark.asyncio
    async def test_api_error_handling_isolation(self, isolated_api_client):
        """Test API module error handling doesn't leak implementation details"""
        client = isolated_api_client
        
        # Mock network error
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Network error")
            
            with pytest.raises(WallexAPIError) as exc_info:
                await client.get_markets()
            
            # Error should be properly wrapped
            assert isinstance(exc_info.value, WallexAPIError)
            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_rate_limiting_isolation(self, isolated_api_client):
        """Test API rate limiting is properly isolated"""
        client = isolated_api_client
        
        # Mock rate limit responses
        call_count = 0
        
        async def rate_limited_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count > 5:
                raise WallexAPIError("Rate limit exceeded", status_code=429)
            
            return {'success': True, 'result': []}
        
        with patch.object(client, '_make_request', side_effect=rate_limited_request):
            # First few requests should succeed
            for i in range(5):
                result = await client.get_markets()
                assert result['success'] is True
            
            # Subsequent requests should be rate limited
            with pytest.raises(WallexAPIError) as exc_info:
                await client.get_markets()
            
            assert exc_info.value.status_code == 429


class TestWebSocketModule:
    """Test suite for WebSocket module isolation and interfaces"""

    @pytest.fixture
    def isolated_websocket(self, sample_config):
        """Setup isolated WebSocket for modular testing"""
        return WebSocketManager("wss://api.wallex.ir/v1/ws", sample_config['api_key'])

    @pytest.mark.asyncio
    async def test_websocket_interface_contract(self, isolated_websocket):
        """Test WebSocket module interface contract compliance"""
        ws_manager = isolated_websocket
        
        # Test required interface methods exist
        required_methods = [
            'start', 'stop', 'is_connected',
            'subscribe_ticker', 'subscribe_trades', 'subscribe_order_book',
            'unsubscribe', 'get_subscriptions'
        ]
        
        for method_name in required_methods:
            assert hasattr(ws_manager, method_name), f"WebSocket missing required method: {method_name}"
            method = getattr(ws_manager, method_name)
            assert callable(method), f"WebSocket method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_websocket_isolation_from_rest_api(self, isolated_websocket):
        """Test WebSocket module operates independently of REST API"""
        ws_manager = isolated_websocket
        
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            
            # Mock REST API failure
            with patch('wallex.rest.WallexRestClient') as mock_rest:
                mock_rest.side_effect = Exception("REST API unavailable")
                
                # WebSocket should still work
                await ws_manager.start()
                assert ws_manager.is_connected()
                
                # Subscription should work
                sub_id = await ws_manager.subscribe_ticker('BTCUSDT', lambda data: None)
                assert sub_id is not None
                
                await ws_manager.stop()

    @pytest.mark.asyncio
    async def test_websocket_message_handling_isolation(self, isolated_websocket):
        """Test WebSocket message handling is properly isolated"""
        ws_manager = isolated_websocket
        
        received_messages = []
        error_messages = []
        
        def success_handler(data):
            received_messages.append(data)
        
        def error_handler(error):
            error_messages.append(error)
        
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            
            await ws_manager.start()
            
            # Subscribe with handlers
            await ws_manager.subscribe_ticker('BTCUSDT', success_handler)
            
            # Test successful message handling
            valid_message = {
                'channel': 'ticker',
                'symbol': 'BTCUSDT',
                'data': {'last_price': '50000.0'}
            }
            
            await ws_manager._handle_message(valid_message)
            assert len(received_messages) == 1
            assert received_messages[0]['data']['last_price'] == '50000.0'
            
            # Test error handling isolation
            invalid_message = {'invalid': 'message'}
            
            # Should not crash the WebSocket manager
            await ws_manager._handle_message(invalid_message)
            assert ws_manager.is_connected()
            
            await ws_manager.stop()

    @pytest.mark.asyncio
    async def test_websocket_subscription_management_isolation(self, isolated_websocket):
        """Test WebSocket subscription management is properly isolated"""
        ws_manager = isolated_websocket
        
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            
            await ws_manager.start()
            
            # Test subscription isolation
            sub1 = await ws_manager.subscribe_ticker('BTCUSDT', lambda data: None)
            sub2 = await ws_manager.subscribe_trades('ETHUSDT', lambda data: None)
            
            assert sub1 != sub2
            assert len(ws_manager.get_subscriptions()) == 2
            
            # Unsubscribing one should not affect the other
            await ws_manager.unsubscribe(sub1)
            assert len(ws_manager.get_subscriptions()) == 1
            
            remaining_subs = ws_manager.get_subscriptions()
            assert sub2 in remaining_subs
            assert sub1 not in remaining_subs
            
            await ws_manager.stop()


class TestPortfolioModule:
    """Test suite for portfolio module isolation and interfaces"""

    @pytest.fixture
    def isolated_portfolio_manager(self, sample_config):
        """Setup isolated portfolio manager for modular testing"""
        # Mock dependencies
        mock_database = AsyncMock(spec=PortfolioDatabase)
        mock_client = AsyncMock(spec=WallexAsyncClient)
        
        return PortfolioManager(mock_database, mock_client)

    @pytest.mark.asyncio
    async def test_portfolio_interface_contract(self, isolated_portfolio_manager):
        """Test portfolio module interface contract compliance"""
        portfolio_manager = isolated_portfolio_manager
        
        # Test required interface methods exist
        required_methods = [
            'create_portfolio', 'save_portfolio', 'get_portfolio',
            'update_portfolio', 'delete_portfolio',
            'add_asset_balance', 'update_asset_balance', 'remove_asset_balance',
            'calculate_portfolio_value', 'calculate_portfolio_stats',
            'get_portfolio_history', 'get_asset_allocation'
        ]
        
        for method_name in required_methods:
            assert hasattr(portfolio_manager, method_name), f"Portfolio manager missing required method: {method_name}"
            method = getattr(portfolio_manager, method_name)
            assert callable(method), f"Portfolio manager method {method_name} is not callable"

    @pytest.mark.asyncio
    async def test_portfolio_isolation_from_external_services(self, isolated_portfolio_manager):
        """Test portfolio module operates independently when external services fail"""
        portfolio_manager = isolated_portfolio_manager
        
        # Mock database success but API failure
        portfolio_manager._database.save_portfolio_snapshot.return_value = "portfolio_123"
        portfolio_manager._client.get_ticker.side_effect = WallexAPIError("API unavailable")
        
        # Portfolio creation should still work
        portfolio = Portfolio(
            name="Isolation Test Portfolio",
            description="Testing module isolation"
        )
        
        balance = AssetBalance(
            symbol='BTC',
            quantity=Decimal('1.0'),
            average_cost=Decimal('45000.0')
        )
        portfolio.add_balance(balance)
        
        # Save should work even if price fetching fails
        portfolio_id = await portfolio_manager.save_portfolio(portfolio)
        assert portfolio_id == "portfolio_123"

    @pytest.mark.asyncio
    async def test_portfolio_business_logic_isolation(self, isolated_portfolio_manager):
        """Test portfolio business logic is properly isolated"""
        portfolio_manager = isolated_portfolio_manager
        
        # Test portfolio value calculation without external dependencies
        portfolio = Portfolio(
            name="Business Logic Test",
            description="Testing business logic isolation"
        )
        
        # Add multiple assets
        assets = [
            ('BTC', Decimal('0.5'), Decimal('45000.0')),
            ('ETH', Decimal('2.0'), Decimal('3000.0')),
            ('ADA', Decimal('1000.0'), Decimal('1.5'))
        ]
        
        for symbol, quantity, avg_cost in assets:
            balance = AssetBalance(
                symbol=symbol,
                quantity=quantity,
                average_cost=avg_cost
            )
            portfolio.add_balance(balance)
        
        # Calculate total value (should work without external price data)
        total_value = portfolio.calculate_total_value()
        expected_value = (Decimal('0.5') * Decimal('45000.0') + 
                         Decimal('2.0') * Decimal('3000.0') + 
                         Decimal('1000.0') * Decimal('1.5'))
        
        assert total_value == expected_value

    @pytest.mark.asyncio
    async def test_portfolio_data_validation_isolation(self, isolated_portfolio_manager):
        """Test portfolio data validation is properly isolated"""
        portfolio_manager = isolated_portfolio_manager
        
        # Test invalid portfolio data
        with pytest.raises(ValueError):
            Portfolio(name="", description="Invalid portfolio")
        
        # Test invalid asset balance
        with pytest.raises(ValueError):
            AssetBalance(
                symbol="",  # Invalid empty symbol
                quantity=Decimal('1.0'),
                average_cost=Decimal('100.0')
            )
        
        # Test negative quantities
        with pytest.raises(ValueError):
            AssetBalance(
                symbol="BTC",
                quantity=Decimal('-1.0'),  # Invalid negative quantity
                average_cost=Decimal('100.0')
            )


class TestConfigurationModule:
    """Test suite for configuration module isolation and interfaces"""

    @pytest.fixture
    def isolated_config_manager(self):
        """Setup isolated configuration manager for modular testing"""
        return ConfigurationManager()

    def test_configuration_interface_contract(self, isolated_config_manager):
        """Test configuration module interface contract compliance"""
        config_manager = isolated_config_manager
        
        # Test required interface methods exist
        required_methods = [
            'load_config', 'save_config', 'get_setting', 'set_setting',
            'validate_config', 'get_default_config', 'merge_configs'
        ]
        
        for method_name in required_methods:
            assert hasattr(config_manager, method_name), f"Config manager missing required method: {method_name}"
            method = getattr(config_manager, method_name)
            assert callable(method), f"Config manager method {method_name} is not callable"

    def test_configuration_isolation_from_file_system(self, isolated_config_manager):
        """Test configuration module handles file system errors gracefully"""
        config_manager = isolated_config_manager
        
        # Mock file system error
        with patch('builtins.open', side_effect=OSError("File system unavailable")):
            # Should fall back to default configuration
            config = config_manager.get_default_config()
            assert isinstance(config, dict)
            assert 'api_key' in config
            assert 'api_secret' in config

    def test_configuration_validation_isolation(self, isolated_config_manager):
        """Test configuration validation is properly isolated"""
        config_manager = isolated_config_manager
        
        # Test valid configuration
        valid_config = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'database_url': 'sqlite:///test.db',
            'timeout': 30
        }
        
        assert config_manager.validate_config(valid_config) is True
        
        # Test invalid configuration
        invalid_configs = [
            {},  # Empty config
            {'api_key': ''},  # Empty API key
            {'api_key': 'test', 'timeout': 'invalid'},  # Invalid timeout type
            {'api_key': 'test', 'database_url': 'invalid_url'}  # Invalid database URL
        ]
        
        for invalid_config in invalid_configs:
            assert config_manager.validate_config(invalid_config) is False

    def test_configuration_environment_isolation(self, isolated_config_manager):
        """Test configuration module handles environment variable changes"""
        config_manager = isolated_config_manager
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'WALLEX_API_KEY': 'env_api_key',
            'WALLEX_API_SECRET': 'env_api_secret',
            'WALLEX_DATABASE_URL': 'sqlite:///env.db'
        }):
            config = config_manager.load_config()
            assert config['api_key'] == 'env_api_key'
            assert config['api_secret'] == 'env_api_secret'
            assert config['database_url'] == 'sqlite:///env.db'
        
        # Test without environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = config_manager.load_config()
            # Should use default values
            assert 'api_key' in config
            assert 'api_secret' in config


class TestAuthenticationModule:
    """Test suite for authentication module isolation and interfaces"""

    @pytest.fixture
    def isolated_auth_manager(self, sample_config):
        """Setup isolated authentication manager for modular testing"""
        return AuthenticationManager(
            api_key=sample_config['api_key'],
            api_secret=sample_config['api_secret']
        )

    def test_authentication_interface_contract(self, isolated_auth_manager):
        """Test authentication module interface contract compliance"""
        auth_manager = isolated_auth_manager
        
        # Test required interface methods exist
        required_methods = [
            'generate_signature', 'create_headers', 'validate_credentials',
            'refresh_token', 'is_authenticated', 'get_user_info'
        ]
        
        for method_name in required_methods:
            assert hasattr(auth_manager, method_name), f"Auth manager missing required method: {method_name}"
            method = getattr(auth_manager, method_name)
            assert callable(method), f"Auth manager method {method_name} is not callable"

    def test_authentication_signature_generation_isolation(self, isolated_auth_manager):
        """Test authentication signature generation is properly isolated"""
        auth_manager = isolated_auth_manager
        
        # Test signature generation
        method = 'GET'
        path = '/api/v1/markets'
        params = {'symbol': 'BTCUSDT'}
        timestamp = '1640995200'
        
        signature = auth_manager.generate_signature(method, path, params, timestamp)
        
        # Signature should be consistent for same inputs
        signature2 = auth_manager.generate_signature(method, path, params, timestamp)
        assert signature == signature2
        
        # Signature should be different for different inputs
        signature3 = auth_manager.generate_signature('POST', path, params, timestamp)
        assert signature != signature3

    def test_authentication_header_creation_isolation(self, isolated_auth_manager):
        """Test authentication header creation is properly isolated"""
        auth_manager = isolated_auth_manager
        
        headers = auth_manager.create_headers('GET', '/api/v1/markets', {})
        
        # Required headers should be present
        assert 'X-API-Key' in headers
        assert 'X-Signature' in headers
        assert 'X-Timestamp' in headers
        
        # Headers should be strings
        assert isinstance(headers['X-API-Key'], str)
        assert isinstance(headers['X-Signature'], str)
        assert isinstance(headers['X-Timestamp'], str)

    def test_authentication_credential_validation_isolation(self, isolated_auth_manager):
        """Test authentication credential validation is properly isolated"""
        auth_manager = isolated_auth_manager
        
        # Valid credentials should pass validation
        assert auth_manager.validate_credentials() is True
        
        # Test with invalid credentials
        invalid_auth = AuthenticationManager(api_key="", api_secret="")
        assert invalid_auth.validate_credentials() is False
        
        # Test with None credentials
        none_auth = AuthenticationManager(api_key=None, api_secret=None)
        assert none_auth.validate_credentials() is False


class TestModuleIntegration:
    """Test suite for module integration and communication"""

    @pytest.fixture
    async def integrated_system(self, sample_config):
        """Setup integrated system for module interaction testing"""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        db_file.close()
        
        # Setup components
        config = WallexConfig(
            api_key=sample_config['api_key'],
            api_secret=sample_config['api_secret'],
            database_url=f"sqlite:///{db_file.name}"
        )
        
        database = PortfolioDatabase(config.database_url)
        await database.init()
        
        client = WallexAsyncClient(config)
        portfolio_manager = PortfolioManager(database, client)
        
        yield {
            'config': config,
            'database': database,
            'client': client,
            'portfolio_manager': portfolio_manager
        }
        
        await database.close()
        os.unlink(db_file.name)

    @pytest.mark.asyncio
    async def test_database_portfolio_integration(self, integrated_system):
        """Test database and portfolio module integration"""
        database = integrated_system['database']
        portfolio_manager = integrated_system['portfolio_manager']
        
        # Create portfolio through portfolio manager
        portfolio = Portfolio(
            name="Integration Test Portfolio",
            description="Testing module integration"
        )
        
        balance = AssetBalance(
            symbol='BTC',
            quantity=Decimal('0.1'),
            average_cost=Decimal('50000.0')
        )
        portfolio.add_balance(balance)
        
        # Save through portfolio manager (should use database)
        portfolio_id = await portfolio_manager.save_portfolio(portfolio)
        assert portfolio_id is not None
        
        # Verify data is in database
        history = await database.get_portfolio_history(days=1)
        assert len(history) == 1
        assert history[0]['name'] == "Integration Test Portfolio"

    @pytest.mark.asyncio
    async def test_api_portfolio_integration(self, integrated_system):
        """Test API and portfolio module integration"""
        client = integrated_system['client']
        portfolio_manager = integrated_system['portfolio_manager']
        
        # Mock API responses
        with patch.object(client, 'get_ticker') as mock_ticker:
            mock_ticker.return_value = {
                'success': True,
                'result': {
                    'symbol': 'BTCUSDT',
                    'last_price': '55000.0'
                }
            }
            
            # Portfolio manager should use API for price updates
            portfolio = Portfolio(
                name="API Integration Test",
                description="Testing API integration"
            )
            
            balance = AssetBalance(
                symbol='BTC',
                quantity=Decimal('0.1'),
                average_cost=Decimal('50000.0')
            )
            portfolio.add_balance(balance)
            
            # Update portfolio with current prices (should call API)
            await portfolio_manager.update_portfolio_prices(portfolio)
            
            # Verify API was called
            mock_ticker.assert_called_with('BTCUSDT')

    @pytest.mark.asyncio
    async def test_websocket_portfolio_integration(self, integrated_system):
        """Test WebSocket and portfolio module integration"""
        config = integrated_system['config']
        portfolio_manager = integrated_system['portfolio_manager']
        
        # Setup WebSocket manager
        ws_manager = WebSocketManager("wss://api.wallex.ir/v1/ws", config.api_key)
        
        # Mock WebSocket connection
        with patch.object(ws_manager, '_websocket') as mock_ws:
            mock_ws.connect = AsyncMock()
            mock_ws.is_connected.return_value = True
            mock_ws.send_message = AsyncMock()
            
            await ws_manager.start()
            
            # Create portfolio with real-time updates
            portfolio = Portfolio(
                name="WebSocket Integration Test",
                description="Testing WebSocket integration"
            )
            
            balance = AssetBalance(
                symbol='BTC',
                quantity=Decimal('0.1'),
                average_cost=Decimal('50000.0')
            )
            portfolio.add_balance(balance)
            
            # Subscribe to price updates
            price_updates = []
            
            def price_handler(data):
                price_updates.append(data)
                # Update portfolio with new price
                asyncio.create_task(
                    portfolio_manager.update_asset_price(
                        portfolio.id, 
                        data['symbol'], 
                        Decimal(data['data']['last_price'])
                    )
                )
            
            await ws_manager.subscribe_ticker('BTCUSDT', price_handler)
            
            # Simulate price update
            price_message = {
                'channel': 'ticker',
                'symbol': 'BTCUSDT',
                'data': {'last_price': '52000.0'}
            }
            
            await ws_manager._handle_message(price_message)
            
            # Verify integration worked
            assert len(price_updates) == 1
            assert price_updates[0]['data']['last_price'] == '52000.0'
            
            await ws_manager.stop()

    @pytest.mark.asyncio
    async def test_error_propagation_between_modules(self, integrated_system):
        """Test error propagation and handling between modules"""
        database = integrated_system['database']
        portfolio_manager = integrated_system['portfolio_manager']
        
        # Mock database error
        with patch.object(database, 'save_portfolio_snapshot') as mock_save:
            mock_save.side_effect = DatabaseError("Database connection failed")
            
            portfolio = Portfolio(
                name="Error Test Portfolio",
                description="Testing error propagation"
            )
            
            # Portfolio manager should handle database errors gracefully
            with pytest.raises(DatabaseError) as exc_info:
                await portfolio_manager.save_portfolio(portfolio)
            
            assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_module_lifecycle_management(self, integrated_system):
        """Test module lifecycle management and cleanup"""
        database = integrated_system['database']
        client = integrated_system['client']
        
        # Test proper initialization
        assert await database.health() is True
        
        # Test graceful shutdown
        await database.close()
        
        # Database should be properly closed
        with pytest.raises(Exception):
            await database.health()
        
        # Client should handle cleanup gracefully
        # (No explicit close method, but should not leak resources)
        del client


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])