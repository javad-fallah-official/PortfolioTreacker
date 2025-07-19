# Caching and Performance Enhancements

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import hashlib
from functools import wraps

class AsyncCache:
    """Simple async cache implementation"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        return datetime.now() > entry['expires_at']
    
    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                return entry['value']
            else:
                del self.cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.now()
        }
    
    async def delete(self, key: str) -> None:
        self.cache.pop(key, None)
    
    async def clear(self) -> None:
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() if self._is_expired(entry))
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries
        }

# Cache decorator
def cached(ttl: int = 300, key_prefix: str = ""):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

# Global cache instance
cache = AsyncCache(default_ttl=300)

# Performance monitoring
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    async def track_execution_time(self, func_name: str, execution_time: float):
        if func_name not in self.metrics:
            self.metrics[func_name] = {
                'total_calls': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        metric = self.metrics[func_name]
        metric['total_calls'] += 1
        metric['total_time'] += execution_time
        metric['avg_time'] = metric['total_time'] / metric['total_calls']
        metric['min_time'] = min(metric['min_time'], execution_time)
        metric['max_time'] = max(metric['max_time'], execution_time)
    
    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics

def performance_monitor(monitor: PerformanceMonitor):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = (datetime.now() - start_time).total_seconds()
                await monitor.track_execution_time(func.__name__, execution_time)
        return wrapper
    return decorator

# Usage examples:
# @cached(ttl=60, key_prefix="balances")
# async def get_balances():
#     # Your function implementation
#     pass

# @performance_monitor(monitor_instance)
# async def expensive_operation():
#     # Your function implementation
#     pass