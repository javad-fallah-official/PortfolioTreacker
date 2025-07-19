"""
Performance Optimization Suggestions for Portfolio Tracker
=========================================================

This file contains comprehensive performance optimization strategies for your cryptocurrency portfolio application.
"""

import asyncio
import time
import functools
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import json
import redis
from dataclasses import dataclass
import logging

# Configure performance logging
perf_logger = logging.getLogger('performance')
perf_logger.setLevel(logging.INFO)

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    endpoint: str
    execution_time: float
    timestamp: datetime
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None

class PerformanceMonitor:
    """Monitor and track application performance"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.slow_query_threshold = 1.0  # seconds
    
    def track_execution_time(self, func_name: str):
        """Decorator to track function execution time"""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    execution_time = time.time() - start_time
                    self._log_performance(func_name, execution_time)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    execution_time = time.time() - start_time
                    self._log_performance(func_name, execution_time)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def _log_performance(self, func_name: str, execution_time: float):
        """Log performance metrics"""
        metric = PerformanceMetrics(
            endpoint=func_name,
            execution_time=execution_time,
            timestamp=datetime.now()
        )
        self.metrics.append(metric)
        
        if execution_time > self.slow_query_threshold:
            perf_logger.warning(
                f"Slow execution detected: {func_name} took {execution_time:.2f}s"
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.metrics:
            return {}
        
        by_endpoint = {}
        for metric in self.metrics:
            if metric.endpoint not in by_endpoint:
                by_endpoint[metric.endpoint] = []
            by_endpoint[metric.endpoint].append(metric.execution_time)
        
        summary = {}
        for endpoint, times in by_endpoint.items():
            summary[endpoint] = {
                'avg_time': sum(times) / len(times),
                'max_time': max(times),
                'min_time': min(times),
                'call_count': len(times)
            }
        
        return summary


class CacheManager:
    """Intelligent caching system"""
    
    def __init__(self, use_redis: bool = False):
        self.use_redis = use_redis
        self.local_cache = {}
        self.cache_ttl = {}
        
        if use_redis:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
                self.redis_client.ping()
            except:
                self.use_redis = False
                perf_logger.warning("Redis not available, falling back to local cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.use_redis:
            try:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
            except:
                pass
        
        # Check local cache
        if key in self.local_cache:
            if key in self.cache_ttl and time.time() > self.cache_ttl[key]:
                del self.local_cache[key]
                del self.cache_ttl[key]
                return None
            return self.local_cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL"""
        if self.use_redis:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except:
                pass
        
        # Local cache
        self.local_cache[key] = value
        self.cache_ttl[key] = time.time() + ttl
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries"""
        if pattern:
            keys_to_remove = [k for k in self.local_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.local_cache[key]
                if key in self.cache_ttl:
                    del self.cache_ttl[key]
        else:
            self.local_cache.clear()
            self.cache_ttl.clear()


class DatabaseOptimizer:
    """Database performance optimization"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_pool = []
        self.pool_size = 5
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Initialize database connection pool"""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            conn.execute("PRAGMA cache_size=10000")  # Larger cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            self.connection_pool.append(conn)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get connection from pool"""
        if self.connection_pool:
            return self.connection_pool.pop()
        else:
            # Create new connection if pool is empty
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._optimize_connection(conn)
            return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return connection to pool"""
        if len(self.connection_pool) < self.pool_size:
            self.connection_pool.append(conn)
        else:
            conn.close()
    
    def _optimize_connection(self, conn: sqlite3.Connection):
        """Apply optimization settings to connection"""
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
    
    def create_indexes(self):
        """Create performance indexes"""
        conn = self.get_connection()
        try:
            # Index for portfolio snapshots by timestamp
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp 
                ON portfolio_snapshots(timestamp)
            """)
            
            # Index for asset balances by snapshot_id
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_snapshot 
                ON asset_balances(snapshot_id)
            """)
            
            # Composite index for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_symbol_snapshot 
                ON asset_balances(symbol, snapshot_id)
            """)
            
            conn.commit()
        finally:
            self.return_connection(conn)
    
    def analyze_database(self):
        """Analyze database for query optimization"""
        conn = self.get_connection()
        try:
            conn.execute("ANALYZE")
            conn.commit()
        finally:
            self.return_connection(conn)


class AsyncAPIClient:
    """Optimized async API client for Wallex"""
    
    def __init__(self, max_concurrent_requests: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.session = None
        self.request_cache = CacheManager()
    
    async def __aenter__(self):
        import aiohttp
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, url: str, cache_key: str = None, cache_ttl: int = 60):
        """Make optimized API request with caching"""
        # Check cache first
        if cache_key:
            cached_result = self.request_cache.get(cache_key)
            if cached_result:
                return cached_result
        
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    result = await response.json()
                    
                    # Cache successful responses
                    if cache_key and response.status == 200:
                        self.request_cache.set(cache_key, result, cache_ttl)
                    
                    return result
            except Exception as e:
                perf_logger.error(f"API request failed: {e}")
                raise


class BatchProcessor:
    """Batch processing for database operations"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.pending_operations = []
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def add_operation(self, operation: Dict[str, Any]):
        """Add operation to batch"""
        self.pending_operations.append(operation)
        
        if len(self.pending_operations) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """Execute all pending operations"""
        if not self.pending_operations:
            return
        
        operations = self.pending_operations.copy()
        self.pending_operations.clear()
        
        # Execute in background thread
        self.executor.submit(self._execute_batch, operations)
    
    def _execute_batch(self, operations: List[Dict[str, Any]]):
        """Execute batch of operations"""
        # Group operations by type
        inserts = [op for op in operations if op['type'] == 'insert']
        updates = [op for op in operations if op['type'] == 'update']
        
        # Execute batch inserts/updates
        # Implementation depends on your specific needs


class MemoryOptimizer:
    """Memory usage optimization"""
    
    @staticmethod
    def optimize_portfolio_data(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize portfolio data structure for memory efficiency"""
        optimized = {}
        
        # Convert large numbers to appropriate types
        for key, value in portfolio_data.items():
            if isinstance(value, dict):
                optimized[key] = MemoryOptimizer.optimize_portfolio_data(value)
            elif isinstance(value, float) and value == int(value):
                optimized[key] = int(value)  # Store as int if no decimal part
            else:
                optimized[key] = value
        
        return optimized
    
    @staticmethod
    def compress_historical_data(data: List[Dict[str, Any]]) -> bytes:
        """Compress historical data for storage"""
        import gzip
        import pickle
        
        serialized = pickle.dumps(data)
        return gzip.compress(serialized)
    
    @staticmethod
    def decompress_historical_data(compressed_data: bytes) -> List[Dict[str, Any]]:
        """Decompress historical data"""
        import gzip
        import pickle
        
        decompressed = gzip.decompress(compressed_data)
        return pickle.loads(decompressed)


class LazyLoader:
    """Lazy loading for large datasets"""
    
    def __init__(self, data_source, page_size: int = 50):
        self.data_source = data_source
        self.page_size = page_size
        self.cache = {}
    
    def get_page(self, page_number: int) -> List[Dict[str, Any]]:
        """Get specific page of data"""
        if page_number in self.cache:
            return self.cache[page_number]
        
        offset = page_number * self.page_size
        data = self.data_source.get_data(offset, self.page_size)
        self.cache[page_number] = data
        
        return data
    
    def invalidate_cache(self):
        """Clear cached pages"""
        self.cache.clear()


# Performance optimization recommendations
PERFORMANCE_RECOMMENDATIONS = """
Database Optimizations:
□ Use connection pooling
□ Implement proper indexing
□ Use WAL mode for SQLite
□ Batch database operations
□ Regular ANALYZE commands

API Optimizations:
□ Implement request caching
□ Use async/await for concurrent requests
□ Add request rate limiting
□ Implement circuit breaker pattern
□ Use connection pooling

Memory Optimizations:
□ Implement lazy loading for large datasets
□ Use appropriate data types
□ Compress historical data
□ Implement memory monitoring
□ Regular garbage collection

Frontend Optimizations:
□ Implement virtual scrolling for large lists
□ Use debouncing for search inputs
□ Lazy load charts and graphs
□ Implement progressive loading
□ Use efficient state management

Caching Strategy:
□ Cache API responses
□ Cache computed values
□ Use Redis for distributed caching
□ Implement cache invalidation
□ Monitor cache hit rates

Monitoring:
□ Track response times
□ Monitor memory usage
□ Log slow queries
□ Set up performance alerts
□ Regular performance testing
"""

# Example usage in your application:
"""
# Initialize performance components
performance_monitor = PerformanceMonitor()
cache_manager = CacheManager(use_redis=True)
db_optimizer = DatabaseOptimizer("portfolio.db")

# Apply performance decorators
@performance_monitor.track_execution_time("get_portfolio_balances")
async def get_portfolio_balances():
    # Check cache first
    cached_balances = cache_manager.get("portfolio_balances")
    if cached_balances:
        return cached_balances
    
    # Fetch from API
    balances = await fetch_balances_from_api()
    
    # Cache for 5 minutes
    cache_manager.set("portfolio_balances", balances, ttl=300)
    
    return balances

# Optimize database on startup
db_optimizer.create_indexes()
db_optimizer.analyze_database()
"""