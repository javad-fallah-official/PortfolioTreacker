"""
Wallex REST API Client Module

This module provides a comprehensive REST API client for Wallex cryptocurrency exchange.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from .config import WallexConfig, get_config
from .exceptions import (
    WallexAPIError, WallexAuthenticationError, WallexRateLimitError,
    WallexValidationError, WallexNetworkError, WallexTimeoutError,
    create_exception_from_response, handle_http_error
)
from .utils import generate_signature, get_timestamp, build_query_string


class WallexRestClient:
    """
    Wallex REST API Client
    
    Implements all available REST API endpoints for Wallex cryptocurrency exchange.
    """
    
    def __init__(self, config: Optional[WallexConfig] = None):
        """
        Initialize REST client
        
        Args:
            config: Configuration object, uses default if None
        """
        self.config = config or get_config()
        self.session = requests.Session()
        self.session.timeout = self.config.timeout
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': self.config.user_agent,
            **self.config.headers
        })
        
        if self.config.api_key:
            self.session.headers.update({
                'X-API-Key': self.config.api_key
            })
        
        # Configure SSL verification
        self.session.verify = self.config.verify_ssl
        
        # Configure proxy if provided
        if self.config.proxy:
            self.session.proxies.update(self.config.proxy)
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None, authenticated: bool = False) -> Dict:
        """
        Make HTTP request to Wallex API with error handling and retries
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            authenticated: Whether authentication is required
            
        Returns:
            API response data
            
        Raises:
            WallexAPIError: For API-related errors
            WallexNetworkError: For network-related errors
        """
        url = f"{self.config.base_url}{endpoint}"
        
        if authenticated and not self.config.api_key:
            raise WallexAuthenticationError("API key required for authenticated endpoints")
        
        for attempt in range(self.config.max_retries):
            try:
                # Prepare request arguments
                request_kwargs = {
                    'timeout': self.config.timeout,
                    'verify': self.config.verify_ssl
                }
                
                if params:
                    request_kwargs['params'] = params
                
                if data:
                    request_kwargs['json'] = data
                
                # Make the request
                if method.upper() == 'GET':
                    response = self.session.get(url, **request_kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, **request_kwargs)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, **request_kwargs)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, **request_kwargs)
                elif method.upper() == 'PATCH':
                    response = self.session.patch(url, **request_kwargs)
                else:
                    raise WallexValidationError(f"Unsupported HTTP method: {method}")
                
                # Handle HTTP errors
                if not response.ok:
                    try:
                        error_data = response.json()
                    except json.JSONDecodeError:
                        error_data = {'message': response.text}
                    
                    if response.status_code == 429:
                        retry_after = response.headers.get('Retry-After')
                        raise WallexRateLimitError(
                            "Rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None,
                            status_code=response.status_code,
                            response_data=error_data
                        )
                    else:
                        raise handle_http_error(response.status_code, error_data)
                
                # Parse JSON response
                try:
                    result = response.json()
                    
                    # Check for API-level errors
                    if not result.get('success', True):
                        raise create_exception_from_response(result, response.status_code)
                    
                    return result
                    
                except json.JSONDecodeError:
                    raise WallexAPIError(f"Invalid JSON response: {response.text}")
                
            except requests.exceptions.Timeout:
                if attempt == self.config.max_retries - 1:
                    raise WallexTimeoutError(f"Request timed out after {self.config.max_retries} attempts")
                time.sleep(self.config.retry_delay * (2 ** attempt))
                
            except requests.exceptions.ConnectionError as e:
                if attempt == self.config.max_retries - 1:
                    raise WallexNetworkError(f"Connection failed after {self.config.max_retries} attempts", e)
                time.sleep(self.config.retry_delay * (2 ** attempt))
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise WallexNetworkError(f"Request failed after {self.config.max_retries} attempts: {str(e)}", e)
                time.sleep(self.config.retry_delay * (2 ** attempt))
        
        raise WallexNetworkError("Maximum retries exceeded")
    
    # Market Data Endpoints
    
    def get_markets(self) -> Dict:
        """
        Get list of all available markets and their information
        
        Returns:
            Dictionary containing market information
        """
        return self._make_request('GET', '/v1/markets')
    
    def get_market_stats(self, symbol: str) -> Dict:
        """
        Get market statistics for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            
        Returns:
            Dictionary containing market statistics
        """
        return self._make_request('GET', f'/v1/markets/{symbol}')
    
    def get_orderbook(self, symbol: str) -> Dict:
        """
        Get order book for a specific market
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            
        Returns:
            Dictionary containing order book data
        """
        return self._make_request('GET', '/v1/depth', params={'symbol': symbol})
    
    def get_trades(self, symbol: str, limit: Optional[int] = None) -> Dict:
        """
        Get recent trades for a specific market
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            limit: Maximum number of trades to return
            
        Returns:
            Dictionary containing recent trades
        """
        params = {'symbol': symbol}
        if limit:
            params['limit'] = limit
        return self._make_request('GET', '/v1/trades', params=params)
    
    def get_klines(self, symbol: str, resolution: str, from_time: Optional[int] = None, 
                   to_time: Optional[int] = None) -> Dict:
        """
        Get candlestick/kline data for a specific market
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            resolution: Time resolution (e.g., '1', '5', '15', '30', '60', '240', '1D')
            from_time: Start time (Unix timestamp)
            to_time: End time (Unix timestamp)
            
        Returns:
            Dictionary containing kline data
        """
        params = {
            'symbol': symbol,
            'resolution': resolution
        }
        if from_time:
            params['from'] = from_time
        if to_time:
            params['to'] = to_time
        return self._make_request('GET', '/v1/udf/history', params=params)
    
    def get_currencies(self) -> Dict:
        """
        Get list of all supported currencies
        
        Returns:
            Dictionary containing currency information
        """
        return self._make_request('GET', '/v1/currencies')
    
    # Account Endpoints (Authenticated)
    
    def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Dictionary containing account information
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        return self._make_request('GET', '/v1/account/profile', authenticated=True)
    
    def get_balances(self) -> Dict:
        """
        Get account balances
        
        Returns:
            Dictionary containing account balances
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        return self._make_request('GET', '/v1/account/balances', authenticated=True)
    
    def get_balance(self, currency: str) -> Dict:
        """
        Get balance for a specific currency
        
        Args:
            currency: Currency code (e.g., 'BTC', 'IRT')
            
        Returns:
            Dictionary containing currency balance
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        return self._make_request('GET', f'/v1/account/balances/{currency}', authenticated=True)
    
    # Order Management Endpoints (Authenticated)
    
    def create_order(self, symbol: str, side: str, order_type: str, quantity: float,
                    price: Optional[float] = None, client_order_id: Optional[str] = None) -> Dict:
        """
        Create a new order
        
        Args:
            symbol: Trading symbol (e.g., 'BTCIRT')
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('LIMIT' or 'MARKET')
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            client_order_id: Custom order ID
            
        Returns:
            Dictionary containing order information
            
        Raises:
            WallexAuthenticationError: If API key is not provided
            WallexValidationError: If parameters are invalid
        """
        data = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(quantity)
        }
        
        if price:
            data['price'] = str(price)
        
        if client_order_id:
            data['clientOrderId'] = client_order_id
            
        return self._make_request('POST', '/v1/account/orders', data=data, authenticated=True)
    
    def get_orders(self, symbol: Optional[str] = None, status: Optional[str] = None,
                  limit: Optional[int] = None) -> Dict:
        """
        Get list of orders
        
        Args:
            symbol: Filter by trading symbol
            status: Filter by order status
            limit: Maximum number of orders to return
            
        Returns:
            Dictionary containing orders list
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        if status:
            params['status'] = status
        if limit:
            params['limit'] = limit
            
        return self._make_request('GET', '/v1/account/orders', params=params, authenticated=True)
    
    def get_order(self, order_id: str) -> Dict:
        """
        Get specific order by ID
        
        Args:
            order_id: Order ID
            
        Returns:
            Dictionary containing order information
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        return self._make_request('GET', f'/v1/account/orders/{order_id}', authenticated=True)
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel a specific order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Dictionary containing cancellation result
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        return self._make_request('DELETE', f'/v1/account/orders/{order_id}', authenticated=True)
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict:
        """
        Cancel all orders or all orders for a specific symbol
        
        Args:
            symbol: Optional symbol to filter cancellation
            
        Returns:
            Dictionary containing cancellation result
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request('DELETE', '/v1/account/orders', params=params, authenticated=True)
    
    def get_order_history(self, symbol: Optional[str] = None, limit: Optional[int] = None,
                         start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict:
        """
        Get order history
        
        Args:
            symbol: Filter by trading symbol
            limit: Maximum number of orders to return
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            
        Returns:
            Dictionary containing order history
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        if limit:
            params['limit'] = limit
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._make_request('GET', '/v1/account/orders/history', params=params, authenticated=True)
    
    def get_trade_history(self, symbol: Optional[str] = None, limit: Optional[int] = None,
                         start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict:
        """
        Get trade history
        
        Args:
            symbol: Filter by trading symbol
            limit: Maximum number of trades to return
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            
        Returns:
            Dictionary containing trade history
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        if limit:
            params['limit'] = limit
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._make_request('GET', '/v1/account/trades', params=params, authenticated=True)
    
    # Wallet Endpoints (Authenticated)
    
    def get_deposit_address(self, currency: str, network: Optional[str] = None) -> Dict:
        """
        Get deposit address for a currency
        
        Args:
            currency: Currency code (e.g., 'BTC', 'ETH')
            network: Network name (optional)
            
        Returns:
            Dictionary containing deposit address
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {'currency': currency}
        if network:
            params['network'] = network
        return self._make_request('GET', '/v1/account/deposit/address', params=params, authenticated=True)
    
    def get_deposit_history(self, currency: Optional[str] = None, limit: Optional[int] = None,
                           start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict:
        """
        Get deposit history
        
        Args:
            currency: Filter by currency
            limit: Maximum number of deposits to return
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            
        Returns:
            Dictionary containing deposit history
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {}
        if currency:
            params['currency'] = currency
        if limit:
            params['limit'] = limit
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._make_request('GET', '/v1/account/deposits', params=params, authenticated=True)
    
    def withdraw(self, currency: str, amount: float, address: str, network: Optional[str] = None,
                memo: Optional[str] = None) -> Dict:
        """
        Withdraw cryptocurrency
        
        Args:
            currency: Currency code (e.g., 'BTC', 'ETH')
            amount: Withdrawal amount
            address: Destination address
            network: Network name (optional)
            memo: Memo/tag for withdrawal (optional)
            
        Returns:
            Dictionary containing withdrawal result
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        data = {
            'currency': currency,
            'amount': str(amount),
            'address': address
        }
        
        if network:
            data['network'] = network
        if memo:
            data['memo'] = memo
            
        return self._make_request('POST', '/v1/account/withdraw', data=data, authenticated=True)
    
    def get_withdrawal_history(self, currency: Optional[str] = None, limit: Optional[int] = None,
                              start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict:
        """
        Get withdrawal history
        
        Args:
            currency: Filter by currency
            limit: Maximum number of withdrawals to return
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            
        Returns:
            Dictionary containing withdrawal history
            
        Raises:
            WallexAuthenticationError: If API key is not provided
        """
        params = {}
        if currency:
            params['currency'] = currency
        if limit:
            params['limit'] = limit
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._make_request('GET', '/v1/account/withdrawals', params=params, authenticated=True)


# Convenience functions for quick access
def create_rest_client(config: Optional[WallexConfig] = None) -> WallexRestClient:
    """
    Create a new REST client instance
    
    Args:
        config: Configuration object
        
    Returns:
        WallexRestClient instance
    """
    return WallexRestClient(config)


def get_markets() -> Dict:
    """Quick function to get market data without authentication"""
    client = create_rest_client()
    return client.get_markets()


def get_market_stats(symbol: str) -> Dict:
    """Quick function to get market statistics for a symbol"""
    client = create_rest_client()
    return client.get_market_stats(symbol)


def get_orderbook(symbol: str) -> Dict:
    """Quick function to get order book for a symbol"""
    client = create_rest_client()
    return client.get_orderbook(symbol)


def get_trades(symbol: str, limit: Optional[int] = None) -> Dict:
    """Quick function to get recent trades for a symbol"""
    client = create_rest_client()
    return client.get_trades(symbol, limit)