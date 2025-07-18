"""
Wallex API Types and Constants

This module contains type definitions and constants used throughout the Wallex client.
"""

from typing import Dict, List, Optional, Union, Literal, TypedDict
from enum import Enum


# Order sides
OrderSide = Literal["BUY", "SELL"]

# Order types
OrderType = Literal["LIMIT", "MARKET"]

# Order status
OrderStatus = Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]

# Time in force
TimeInForce = Literal["GTC", "IOC", "FOK"]

# Kline intervals
KlineInterval = Literal["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]


class WallexEndpoints:
    """Wallex API endpoints"""
    
    # Base URL
    BASE_URL = "https://api.wallex.ir"
    
    # Market data endpoints
    MARKETS = "/v1/markets"
    MARKET_STATS = "/v1/markets/{symbol}"
    ORDERBOOK = "/v1/depth"
    TRADES = "/v1/trades"
    KLINES = "/v1/udf/history"
    CURRENCIES = "/v1/currencies"
    
    # Account endpoints
    ACCOUNT_INFO = "/v1/account/profile"
    BALANCES = "/v1/account/balances"
    BALANCE = "/v1/account/balances/{currency}"
    
    # Order endpoints
    ORDERS = "/v1/account/orders"
    ORDER = "/v1/account/orders/{order_id}"
    ORDER_HISTORY = "/v1/account/orders/history"
    TRADE_HISTORY = "/v1/account/trades"
    
    # Wallet endpoints
    DEPOSIT_ADDRESS = "/v1/account/deposit/address"
    DEPOSITS = "/v1/account/deposits"
    WITHDRAW = "/v1/account/withdraw"
    WITHDRAWALS = "/v1/account/withdrawals"


class WallexWebSocketChannels:
    """Wallex WebSocket channel formats"""
    
    @staticmethod
    def trades(symbol: str) -> str:
        """Get trades channel for symbol"""
        return f"{symbol}@trade"
    
    @staticmethod
    def buy_depth(symbol: str) -> str:
        """Get buy depth channel for symbol"""
        return f"{symbol}@buyDepth"
    
    @staticmethod
    def sell_depth(symbol: str) -> str:
        """Get sell depth channel for symbol"""
        return f"{symbol}@sellDepth"
    
    @staticmethod
    def ticker(symbol: str) -> str:
        """Get ticker channel for symbol"""
        return f"{symbol}@ticker"
    
    @staticmethod
    def market_cap(symbol: str) -> str:
        """Get market cap channel for symbol"""
        return f"{symbol}@marketCap"


# Type definitions for API responses

class MarketStats(TypedDict):
    """Market statistics type"""
    bidPrice: str
    askPrice: str
    lastPrice: str
    lastQty: str
    lastTradeSide: OrderSide
    bidVolume: str
    askVolume: str
    bidCount: int
    askCount: int
    direction: Dict[str, int]


class Market(TypedDict):
    """Market information type"""
    symbol: str
    baseAsset: str
    baseAssetPrecision: int
    quoteAsset: str
    quotePrecision: int
    faName: str
    faBaseAsset: str
    faQuoteAsset: str
    stepSize: int
    tickSize: int
    minQty: float
    minNotional: float
    stats: MarketStats
    createdAt: str


class OrderBookEntry(TypedDict):
    """Order book entry type"""
    price: str
    quantity: str


class Trade(TypedDict):
    """Trade information type"""
    id: int
    price: str
    qty: str
    quoteQty: str
    time: int
    isBuyerMaker: bool


class Order(TypedDict):
    """Order information type"""
    symbol: str
    orderId: str
    orderListId: int
    clientOrderId: str
    price: str
    origQty: str
    executedQty: str
    cummulativeQuoteQty: str
    status: OrderStatus
    timeInForce: TimeInForce
    type: OrderType
    side: OrderSide
    stopPrice: str
    icebergQty: str
    time: int
    updateTime: int
    isWorking: bool
    origQuoteOrderQty: str


class Balance(TypedDict):
    """Balance information type"""
    asset: str
    free: str
    locked: str


class AccountInfo(TypedDict):
    """Account information type"""
    makerCommission: int
    takerCommission: int
    buyerCommission: int
    sellerCommission: int
    canTrade: bool
    canWithdraw: bool
    canDeposit: bool
    updateTime: int
    accountType: str
    balances: List[Balance]


# Error codes
class WallexErrorCodes:
    """Wallex API error codes"""
    
    # General errors
    UNKNOWN_ERROR = -1000
    DISCONNECTED = -1001
    UNAUTHORIZED = -1002
    TOO_MANY_REQUESTS = -1003
    UNEXPECTED_RESP = -1006
    TIMEOUT = -1007
    UNKNOWN_ORDER_COMPOSITION = -1014
    TOO_MANY_ORDERS = -1015
    SERVICE_SHUTTING_DOWN = -1016
    UNSUPPORTED_OPERATION = -1020
    INVALID_TIMESTAMP = -1021
    INVALID_SIGNATURE = -1022
    
    # Request errors
    ILLEGAL_CHARS = -1100
    TOO_MANY_PARAMETERS = -1101
    MANDATORY_PARAM_EMPTY_OR_MALFORMED = -1102
    UNKNOWN_PARAM = -1103
    UNREAD_PARAMETERS = -1104
    PARAM_EMPTY = -1105
    PARAM_NOT_REQUIRED = -1106
    
    # Order errors
    NEW_ORDER_REJECTED = -2010
    CANCEL_REJECTED = -2011
    NO_SUCH_ORDER = -2013
    BAD_API_KEY_FMT = -2014
    REJECTED_MBX_KEY = -2015
    NO_TRADING_WINDOW = -2016


# Rate limits
class WallexRateLimits:
    """Wallex API rate limits"""
    
    # Request weights
    WEIGHT_1 = 1
    WEIGHT_5 = 5
    WEIGHT_10 = 10
    WEIGHT_20 = 20
    WEIGHT_50 = 50
    
    # Limits per minute
    REQUEST_LIMIT_PER_MINUTE = 1200
    ORDER_LIMIT_PER_SECOND = 10
    ORDER_LIMIT_PER_DAY = 200000


# Common symbols
class CommonSymbols:
    """Common trading symbols on Wallex"""
    
    # Major pairs
    BTCUSDT = "BTCUSDT"
    ETHUSDT = "ETHUSDT"
    BNBUSDT = "BNBUSDT"
    ADAUSDT = "ADAUSDT"
    DOTUSDT = "DOTUSDT"
    LINKUSDT = "LINKUSDT"
    LTCUSDT = "LTCUSDT"
    XRPUSDT = "XRPUSDT"
    
    # Iranian Rial pairs
    BTCTMN = "BTCTMN"
    ETHTMN = "ETHTMN"
    USDTTMN = "USDTTMN"


# Network types for deposits/withdrawals
class Networks:
    """Supported networks for deposits and withdrawals"""
    
    BITCOIN = "BTC"
    ETHEREUM = "ETH"
    BINANCE_SMART_CHAIN = "BSC"
    TRON = "TRX"
    POLYGON = "MATIC"
    AVALANCHE = "AVAX"
    ARBITRUM = "ARBITRUM"
    OPTIMISM = "OPTIMISM"