"""
Wallex Exceptions Module

This module defines custom exceptions for the Wallex library.
"""

from typing import Optional, Dict, Any


class WallexError(Exception):
    """Base exception class for all Wallex-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message='{self.message}', error_code='{self.error_code}')"


class WallexAPIError(WallexError):
    """Exception raised for API-related errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None,
                 error_code: Optional[str] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, response_data)
        self.status_code = status_code
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.status_code:
            return f"HTTP {self.status_code}: {base_msg}"
        return base_msg


class WallexWebSocketError(WallexError):
    """Exception raised for WebSocket-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None,
                 connection_state: Optional[str] = None):
        super().__init__(message, error_code)
        self.connection_state = connection_state


class WallexAuthenticationError(WallexAPIError):
    """Exception raised for authentication-related errors"""
    pass


class WallexPermissionError(WallexAPIError):
    """Exception raised for permission-related errors"""
    pass


class WallexRateLimitError(WallexAPIError):
    """Exception raised when rate limits are exceeded"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None,
                 limit: Optional[int] = None, remaining: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining


class WallexValidationError(WallexError):
    """Exception raised for validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None):
        super().__init__(message)
        self.field = field
        self.value = value


class WallexNetworkError(WallexError):
    """Exception raised for network-related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class WallexTimeoutError(WallexNetworkError):
    """Exception raised for timeout errors"""
    pass


class WallexConnectionError(WallexNetworkError):
    """Exception raised for connection errors"""
    pass


class WallexConfigurationError(WallexError):
    """Exception raised for configuration-related errors"""
    pass


class WallexOrderError(WallexAPIError):
    """Exception raised for order-related errors"""
    
    def __init__(self, message: str, order_id: Optional[str] = None,
                 symbol: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.symbol = symbol


class WallexInsufficientFundsError(WallexOrderError):
    """Exception raised when there are insufficient funds for an operation"""
    pass


class WallexMarketClosedError(WallexAPIError):
    """Exception raised when trying to trade on a closed market"""
    
    def __init__(self, message: str, symbol: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.symbol = symbol


class WallexSymbolNotFoundError(WallexAPIError):
    """Exception raised when a trading symbol is not found"""
    
    def __init__(self, message: str, symbol: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.symbol = symbol


# Error code mappings
ERROR_CODE_MAPPING = {
    # Authentication errors
    "INVALID_API_KEY": WallexAuthenticationError,
    "INVALID_SIGNATURE": WallexAuthenticationError,
    "INVALID_TIMESTAMP": WallexAuthenticationError,
    "API_KEY_EXPIRED": WallexAuthenticationError,
    
    # Permission errors
    "INSUFFICIENT_PERMISSIONS": WallexPermissionError,
    "IP_NOT_WHITELISTED": WallexPermissionError,
    
    # Rate limit errors
    "RATE_LIMIT_EXCEEDED": WallexRateLimitError,
    "TOO_MANY_REQUESTS": WallexRateLimitError,
    
    # Validation errors
    "INVALID_PARAMETER": WallexValidationError,
    "MISSING_PARAMETER": WallexValidationError,
    "INVALID_SYMBOL": WallexSymbolNotFoundError,
    
    # Order errors
    "INSUFFICIENT_BALANCE": WallexInsufficientFundsError,
    "ORDER_NOT_FOUND": WallexOrderError,
    "INVALID_ORDER_TYPE": WallexOrderError,
    "INVALID_ORDER_SIDE": WallexOrderError,
    "MIN_NOTIONAL": WallexOrderError,
    "MAX_POSITION": WallexOrderError,
    
    # Market errors
    "MARKET_CLOSED": WallexMarketClosedError,
    "SYMBOL_NOT_FOUND": WallexSymbolNotFoundError,
    "TRADING_DISABLED": WallexMarketClosedError,
}


def create_exception_from_response(response_data: Dict[str, Any], 
                                 status_code: Optional[int] = None) -> WallexError:
    """
    Create appropriate exception from API response
    
    Args:
        response_data: Response data from API
        status_code: HTTP status code
        
    Returns:
        Appropriate exception instance
    """
    error_code = response_data.get('code', response_data.get('error_code'))
    message = response_data.get('message', response_data.get('error', 'Unknown error'))
    
    # Get exception class based on error code
    exception_class = ERROR_CODE_MAPPING.get(error_code, WallexAPIError)
    
    # Create exception with appropriate parameters
    if issubclass(exception_class, WallexAPIError):
        return exception_class(
            message=message,
            status_code=status_code,
            error_code=error_code,
            response_data=response_data
        )
    else:
        return exception_class(
            message=message,
            error_code=error_code,
            response_data=response_data
        )


def handle_http_error(status_code: int, response_data: Optional[Dict[str, Any]] = None) -> WallexAPIError:
    """
    Handle HTTP errors and create appropriate exceptions
    
    Args:
        status_code: HTTP status code
        response_data: Response data if available
        
    Returns:
        Appropriate exception instance
    """
    response_data = response_data or {}
    
    if status_code == 400:
        return WallexValidationError("Bad Request")
    elif status_code == 401:
        return WallexAuthenticationError("Unauthorized", status_code=status_code, response_data=response_data)
    elif status_code == 403:
        return WallexPermissionError("Forbidden", status_code=status_code, response_data=response_data)
    elif status_code == 404:
        return WallexAPIError("Not Found", status_code=status_code, response_data=response_data)
    elif status_code == 429:
        retry_after = response_data.get('retry_after')
        return WallexRateLimitError(
            "Rate limit exceeded", 
            status_code=status_code,
            retry_after=retry_after,
            response_data=response_data
        )
    elif status_code >= 500:
        return WallexAPIError("Server Error", status_code=status_code, response_data=response_data)
    else:
        return WallexAPIError(f"HTTP Error {status_code}", status_code=status_code, response_data=response_data)