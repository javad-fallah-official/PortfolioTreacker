"""
Wallex API Utilities

This module contains utility functions for the Wallex client.
"""

import hashlib
import hmac
import time
import urllib.parse
from typing import Dict, Any, Optional
import json


def generate_signature(secret_key: str, query_string: str) -> str:
    """
    Generate HMAC SHA256 signature for Wallex API requests
    
    Args:
        secret_key: API secret key
        query_string: Query string to sign
        
    Returns:
        Hex encoded signature
    """
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def get_timestamp() -> int:
    """
    Get current timestamp in milliseconds
    
    Returns:
        Current timestamp in milliseconds
    """
    return int(time.time() * 1000)


def build_query_string(params: Dict[str, Any]) -> str:
    """
    Build query string from parameters
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        URL encoded query string
    """
    # Remove None values
    filtered_params = {k: v for k, v in params.items() if v is not None}
    
    # Sort parameters by key
    sorted_params = sorted(filtered_params.items())
    
    # URL encode
    return urllib.parse.urlencode(sorted_params)


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        
    Returns:
        True if valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Symbol should be uppercase and contain only letters
    return symbol.isupper() and symbol.isalpha() and len(symbol) >= 6


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format
    
    Args:
        api_key: API key string
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key or not isinstance(api_key, str):
        return False
    
    # API key should be at least 32 characters
    return len(api_key) >= 32


def validate_secret_key(secret_key: str) -> bool:
    """
    Validate secret key format
    
    Args:
        secret_key: Secret key string
        
    Returns:
        True if valid, False otherwise
    """
    if not secret_key or not isinstance(secret_key, str):
        return False
    
    # Secret key should be at least 32 characters
    return len(secret_key) >= 32


def format_price(price: float, precision: int = 8) -> str:
    """
    Format price with specified precision
    
    Args:
        price: Price value
        precision: Number of decimal places
        
    Returns:
        Formatted price string
    """
    return f"{price:.{precision}f}".rstrip('0').rstrip('.')


def format_quantity(quantity: float, precision: int = 8) -> str:
    """
    Format quantity with specified precision
    
    Args:
        quantity: Quantity value
        precision: Number of decimal places
        
    Returns:
        Formatted quantity string
    """
    return f"{quantity:.{precision}f}".rstrip('0').rstrip('.')


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Parse JSON response with error handling
    
    Args:
        response_text: JSON response text
        
    Returns:
        Parsed JSON data
        
    Raises:
        ValueError: If JSON is invalid
    """
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e}")


def calculate_order_value(price: float, quantity: float) -> float:
    """
    Calculate total order value
    
    Args:
        price: Order price
        quantity: Order quantity
        
    Returns:
        Total order value
    """
    return price * quantity


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0
    
    return ((new_value - old_value) / old_value) * 100


def is_valid_interval(interval: str) -> bool:
    """
    Check if kline interval is valid
    
    Args:
        interval: Kline interval string
        
    Returns:
        True if valid, False otherwise
    """
    valid_intervals = [
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "6h", "8h", "12h",
        "1d", "3d", "1w", "1M"
    ]
    return interval in valid_intervals


def convert_timestamp_to_datetime(timestamp: int) -> str:
    """
    Convert timestamp to readable datetime string
    
    Args:
        timestamp: Unix timestamp in milliseconds
        
    Returns:
        Formatted datetime string
    """
    import datetime
    dt = datetime.datetime.fromtimestamp(timestamp / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def sanitize_symbol(symbol: str) -> str:
    """
    Sanitize trading symbol
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Sanitized symbol in uppercase
    """
    if not symbol:
        return ""
    
    return symbol.upper().strip()


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Split list into chunks of specified size
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_order_book_updates(current_book: Dict, update: Dict) -> Dict:
    """
    Merge order book updates
    
    Args:
        current_book: Current order book state
        update: Order book update
        
    Returns:
        Updated order book
    """
    result = current_book.copy()
    
    # Update bids
    if 'bids' in update:
        if 'bids' not in result:
            result['bids'] = []
        
        for bid in update['bids']:
            price, quantity = bid
            # Remove existing bid at this price
            result['bids'] = [b for b in result['bids'] if b[0] != price]
            # Add new bid if quantity > 0
            if float(quantity) > 0:
                result['bids'].append(bid)
        
        # Sort bids by price (descending)
        result['bids'].sort(key=lambda x: float(x[0]), reverse=True)
    
    # Update asks
    if 'asks' in update:
        if 'asks' not in result:
            result['asks'] = []
        
        for ask in update['asks']:
            price, quantity = ask
            # Remove existing ask at this price
            result['asks'] = [a for a in result['asks'] if a[0] != price]
            # Add new ask if quantity > 0
            if float(quantity) > 0:
                result['asks'].append(ask)
        
        # Sort asks by price (ascending)
        result['asks'].sort(key=lambda x: float(x[0]))
    
    return result


def calculate_spread(order_book: Dict) -> Optional[float]:
    """
    Calculate bid-ask spread from order book
    
    Args:
        order_book: Order book data
        
    Returns:
        Spread value or None if not available
    """
    if not order_book.get('bids') or not order_book.get('asks'):
        return None
    
    best_bid = float(order_book['bids'][0][0])
    best_ask = float(order_book['asks'][0][0])
    
    return best_ask - best_bid


def calculate_mid_price(order_book: Dict) -> Optional[float]:
    """
    Calculate mid price from order book
    
    Args:
        order_book: Order book data
        
    Returns:
        Mid price or None if not available
    """
    if not order_book.get('bids') or not order_book.get('asks'):
        return None
    
    best_bid = float(order_book['bids'][0][0])
    best_ask = float(order_book['asks'][0][0])
    
    return (best_bid + best_ask) / 2


class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """
        Check if a request can be made
        
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        return len(self.requests) < self.max_requests
    
    def add_request(self):
        """Record a new request"""
        self.requests.append(time.time())
    
    def wait_time(self) -> float:
        """
        Get time to wait before next request
        
        Returns:
            Wait time in seconds
        """
        if self.can_make_request():
            return 0.0
        
        now = time.time()
        oldest_request = min(self.requests)
        return self.time_window - (now - oldest_request)