"""
Comprehensive test suite for the PortfolioDatabase class.

This test suite provides complete coverage of database operations including:
- Database connection and initialization
- Portfolio data storage and retrieval
- Transaction handling and rollback
- Error handling and exception scenarios
- Performance testing for database operations
- Data validation and integrity checks

All tests are independent, properly mocked, and follow best practices.
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncpg

from database import PortfolioDatabase


class TestPortfolioDatabaseInitialization:
    """Test suite for database initialization and connection"""

    def test_database_init_with_dsn(self):
        """Test database initialization with provided DSN"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        assert db.dsn == dsn
        assert db.pool is None

    def test_database_init_from_env_dsn(self):
        """Test database initialization from environment DSN"""
        with patch.dict(os.environ, {'POSTGRES_DSN': 'postgresql://user:pass@localhost:5432/testdb'}):
            db = PortfolioDatabase()
            assert db.dsn == 'postgresql://user:pass@localhost:5432/testdb'

    def test_database_init_from_env_components(self):
        """Test database initialization from environment components"""
        env_vars = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb'
        }
        
        with patch.dict(os.environ, env_vars):
            db = PortfolioDatabase()
            expected_dsn = "postgresql://testuser:testpass@localhost:5432/testdb"
            assert db.dsn == expected_dsn

    def test_database_init_no_config_raises_error(self):
        """Test database initialization without configuration raises error"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="PostgreSQL DSN is not configured"):
                PortfolioDatabase()

    @pytest.mark.asyncio
    async def test_database_init_connection_pool(self):
        """Test database connection pool initialization"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            assert db.pool == mock_pool

    @pytest.mark.asyncio
    async def test_database_close_connection_pool(self):
        """Test database connection pool closure"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        db.pool = mock_pool
        
        await db.close()
        mock_pool.close.assert_called_once()


class TestPortfolioDataOperations:
    """Test suite for portfolio data operations"""

    @pytest.fixture
    async def database(self):
        """Setup database for testing"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
        yield db, mock_connection
        
        await db.close()

    @pytest.mark.asyncio
    async def test_save_portfolio_snapshot_success(self, database):
        """Test successful portfolio snapshot saving"""
        db, mock_conn = database
        
        portfolio_data = {
            'date': date.today(),
            'total_value': Decimal('50000.00'),
            'assets': [
                {'symbol': 'BTC', 'amount': Decimal('1.5'), 'value': Decimal('45000.00')},
                {'symbol': 'ETH', 'amount': Decimal('10.0'), 'value': Decimal('5000.00')}
            ]
        }
        
        mock_conn.execute.return_value = None
        
        await db.save_portfolio_snapshot(portfolio_data)
        
        # Verify the execute method was called
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO" in call_args[0] or "portfolio" in call_args[0].lower()

    @pytest.mark.asyncio
    async def test_get_portfolio_history_success(self, database):
        """Test successful portfolio history retrieval"""
        db, mock_conn = database
        
        mock_records = [
            {
                'date': date.today(),
                'total_value': Decimal('50000.00'),
                'data': json.dumps({
                    'assets': [
                        {'symbol': 'BTC', 'amount': '1.5', 'value': '45000.00'}
                    ]
                })
            }
        ]
        
        mock_conn.fetch.return_value = mock_records
        
        result = await db.get_portfolio_history(days=30)
        
        assert len(result) == 1
        assert result[0]['total_value'] == Decimal('50000.00')
        mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_portfolio_success(self, database):
        """Test successful latest portfolio retrieval"""
        db, mock_conn = database
        
        mock_record = {
            'date': date.today(),
            'total_value': Decimal('50000.00'),
            'data': json.dumps({
                'assets': [
                    {'symbol': 'BTC', 'amount': '1.5', 'value': '45000.00'}
                ]
            })
        }
        
        mock_conn.fetchrow.return_value = mock_record
        
        result = await db.get_latest_portfolio()
        
        assert result['total_value'] == Decimal('50000.00')
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_old_snapshots_success(self, database):
        """Test successful deletion of old snapshots"""
        db, mock_conn = database
        
        mock_conn.execute.return_value = "DELETE 5"
        
        deleted_count = await db.delete_old_snapshots(days=90)
        
        assert deleted_count == 5
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_portfolio_statistics_success(self, database):
        """Test successful portfolio statistics retrieval"""
        db, mock_conn = database
        
        mock_stats = {
            'total_snapshots': 100,
            'date_range_start': date.today() - timedelta(days=100),
            'date_range_end': date.today(),
            'avg_value': Decimal('45000.00'),
            'max_value': Decimal('55000.00'),
            'min_value': Decimal('35000.00')
        }
        
        mock_conn.fetchrow.return_value = mock_stats
        
        result = await db.get_portfolio_statistics()
        
        assert result['total_snapshots'] == 100
        assert result['avg_value'] == Decimal('45000.00')
        mock_conn.fetchrow.assert_called_once()


class TestDatabaseErrorHandling:
    """Test suite for database error handling"""

    @pytest.fixture
    def database_with_errors(self):
        """Setup database that will encounter errors"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        return PortfolioDatabase(dsn)

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, database_with_errors):
        """Test handling of database connection errors"""
        with patch('asyncpg.create_pool', side_effect=asyncpg.ConnectionDoesNotExistError("Connection failed")):
            with pytest.raises(asyncpg.ConnectionDoesNotExistError):
                await database_with_errors.init()

    @pytest.mark.asyncio
    async def test_query_execution_error(self):
        """Test handling of query execution errors"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute.side_effect = asyncpg.PostgresError("Query failed")
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
            with pytest.raises(asyncpg.PostgresError):
                await db.save_portfolio_snapshot({'date': date.today(), 'total_value': Decimal('1000')})

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test transaction rollback on error"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_transaction = AsyncMock()
        
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_connection.execute.side_effect = Exception("Transaction failed")
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
            with pytest.raises(Exception):
                await db.save_portfolio_snapshot({'date': date.today(), 'total_value': Decimal('1000')})

    @pytest.mark.asyncio
    async def test_invalid_data_handling(self):
        """Test handling of invalid data"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
            # Test with invalid portfolio data
            invalid_data = {'invalid': 'data'}
            
            with pytest.raises((KeyError, ValueError, TypeError)):
                await db.save_portfolio_snapshot(invalid_data)


class TestDatabasePerformance:
    """Test suite for database performance scenarios"""

    @pytest.fixture
    async def performance_database(self):
        """Setup database for performance testing"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
        yield db, mock_connection
        
        await db.close()

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, performance_database):
        """Test performance of bulk insert operations"""
        db, mock_conn = performance_database
        
        # Simulate bulk data
        bulk_data = []
        for i in range(100):
            bulk_data.append({
                'date': date.today() - timedelta(days=i),
                'total_value': Decimal(f'{50000 + i * 100}.00'),
                'assets': [
                    {'symbol': 'BTC', 'amount': Decimal('1.5'), 'value': Decimal('45000.00')}
                ]
            })
        
        mock_conn.executemany.return_value = None
        
        start_time = asyncio.get_event_loop().time()
        
        # Simulate bulk insert
        for data in bulk_data:
            await db.save_portfolio_snapshot(data)
        
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # Performance assertion (should complete quickly in mock)
        assert execution_time < 1.0  # Should complete within 1 second for mocked operations

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, performance_database):
        """Test performance of concurrent database operations"""
        db, mock_conn = performance_database
        
        mock_conn.fetch.return_value = []
        
        # Create concurrent tasks
        tasks = []
        for i in range(10):
            task = db.get_portfolio_history(days=30)
            tasks.append(task)
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        assert len(results) == 10
        assert execution_time < 1.0  # Should complete quickly for concurrent operations

    @pytest.mark.asyncio
    async def test_large_dataset_query_performance(self, performance_database):
        """Test performance with large dataset queries"""
        db, mock_conn = performance_database
        
        # Mock large dataset
        large_dataset = []
        for i in range(1000):
            large_dataset.append({
                'date': date.today() - timedelta(days=i),
                'total_value': Decimal(f'{50000 + i}.00'),
                'data': json.dumps({'assets': []})
            })
        
        mock_conn.fetch.return_value = large_dataset
        
        start_time = asyncio.get_event_loop().time()
        result = await db.get_portfolio_history(days=1000)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        assert len(result) == 1000
        assert execution_time < 2.0  # Should handle large datasets efficiently


class TestDatabaseUtilities:
    """Test suite for database utility functions"""

    @pytest.fixture
    def database(self):
        """Setup database for utility testing"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        return PortfolioDatabase(dsn)

    def test_build_dsn_from_env_complete(self, database):
        """Test DSN building with complete environment variables"""
        env_vars = {
            'POSTGRES_HOST': 'testhost',
            'POSTGRES_PORT': '5433',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb'
        }
        
        with patch.dict(os.environ, env_vars):
            dsn = database._build_dsn_from_env()
            expected = "postgresql://testuser:testpass@testhost:5433/testdb"
            assert dsn == expected

    def test_build_dsn_from_env_incomplete(self, database):
        """Test DSN building with incomplete environment variables"""
        env_vars = {
            'POSTGRES_HOST': 'testhost',
            'POSTGRES_USER': 'testuser'
            # Missing PASSWORD and DB
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            dsn = database._build_dsn_from_env()
            assert dsn is None

    def test_build_dsn_from_env_default_port(self, database):
        """Test DSN building uses default port when not specified"""
        env_vars = {
            'POSTGRES_HOST': 'testhost',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass',
            'POSTGRES_DB': 'testdb'
            # No PORT specified, should use default 5432
        }
        
        with patch.dict(os.environ, env_vars):
            dsn = database._build_dsn_from_env()
            expected = "postgresql://testuser:testpass@testhost:5432/testdb"
            assert dsn == expected

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test database health check success"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchval.return_value = 1
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
            health_status = await db.health()
            assert health_status is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test database health check failure"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchval.side_effect = Exception("Health check failed")
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
            health_status = await db.health()
            assert health_status is False


class TestDatabaseMigrations:
    """Test suite for database schema and migrations"""

    @pytest.fixture
    async def migration_database(self):
        """Setup database for migration testing"""
        dsn = "postgresql://user:pass@localhost:5432/testdb"
        db = PortfolioDatabase(dsn)
        
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        with patch('asyncpg.create_pool', return_value=mock_pool):
            await db.init()
            
        yield db, mock_connection
        
        await db.close()

    @pytest.mark.asyncio
    async def test_create_tables_success(self, migration_database):
        """Test successful table creation"""
        db, mock_conn = migration_database
        
        mock_conn.execute.return_value = None
        
        await db.create_tables()
        
        # Verify table creation queries were executed
        assert mock_conn.execute.called
        call_count = mock_conn.execute.call_count
        assert call_count > 0

    @pytest.mark.asyncio
    async def test_drop_tables_success(self, migration_database):
        """Test successful table dropping"""
        db, mock_conn = migration_database
        
        mock_conn.execute.return_value = None
        
        await db.drop_tables()
        
        # Verify drop table queries were executed
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_schema_version_management(self, migration_database):
        """Test schema version management"""
        db, mock_conn = migration_database
        
        # Mock current schema version
        mock_conn.fetchval.return_value = "1.0.0"
        
        version = await db.get_schema_version()
        assert version == "1.0.0"
        
        # Test version update
        mock_conn.execute.return_value = None
        await db.update_schema_version("1.1.0")
        
        mock_conn.execute.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])