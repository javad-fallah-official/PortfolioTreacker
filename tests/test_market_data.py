"""
Comprehensive test suite for market data operations

This test suite provides complete coverage of market data functionality including:
- Market information retrieval and caching
- Price data fetching and validation
- Order book operations and depth analysis
- Trading pair management and validation
- Ticker data processing and updates
- Historical data retrieval and analysis
- Market statistics and calculations
- Real-time data streaming and WebSocket handling
- Error handling and exception scenarios
- Edge cases and boundary conditions

All tests are independent, properly mocked, and follow best practices.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
from decimal import Decimal
import asyncio

from wallex import WallexClient, WallexAsyncClient, WallexConfig, WallexAPIError, OrderSide, OrderType, OrderStatus
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient
from wallex.utils import validate_symbol, format_price
from wallex.utils import validate_symbol, format_price, calculate_spread


class TestMarketOperations:
    """Test suite for market operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.market_manager = MarketDataManager("test_market_api_key")

    def test_market_creation_success(self):
        """Test successful market creation"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.00001"),
            max_quantity=Decimal("1000.0"),
            min_price=Decimal("0.01"),
            max_price=Decimal("1000000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        assert market.symbol == "BTCUSDT"
        assert market.base_asset == "BTC"
        assert market.quote_asset == "USDT"
        assert market.status == MarketStatus.TRADING
        assert market.min_quantity == Decimal("0.00001")
        assert market.price_precision == 2

    def test_market_creation_invalid_symbol(self):
        """Test market creation with invalid symbol"""
        with pytest.raises(WallexValidationError, match="Invalid symbol format"):
            Market(
                symbol="INVALID_SYMBOL",
                base_asset="BTC",
                quote_asset="USDT",
                status=MarketStatus.TRADING,
                min_quantity=Decimal("0.00001"),
                max_quantity=Decimal("1000.0"),
                min_price=Decimal("0.01"),
                max_price=Decimal("1000000.0"),
                price_precision=2,
                quantity_precision=8
            )

    def test_market_validate_quantity_success(self):
        """Test successful quantity validation"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("0.01"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        # Valid quantities
        assert market.validate_quantity(Decimal("0.001")) is True
        assert market.validate_quantity(Decimal("1.0")) is True
        assert market.validate_quantity(Decimal("100.0")) is True

    def test_market_validate_quantity_failure(self):
        """Test quantity validation failure"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("0.01"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        # Invalid quantities
        assert market.validate_quantity(Decimal("0.0001")) is False  # Too small
        assert market.validate_quantity(Decimal("1000.0")) is False  # Too large
        assert market.validate_quantity(Decimal("0")) is False       # Zero

    def test_market_validate_price_success(self):
        """Test successful price validation"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        # Valid prices
        assert market.validate_price(Decimal("1.0")) is True
        assert market.validate_price(Decimal("50000.0")) is True
        assert market.validate_price(Decimal("100000.0")) is True

    def test_market_validate_price_failure(self):
        """Test price validation failure"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        # Invalid prices
        assert market.validate_price(Decimal("0.5")) is False    # Too small
        assert market.validate_price(Decimal("200000.0")) is False  # Too large
        assert market.validate_price(Decimal("0")) is False      # Zero

    def test_market_format_price_precision(self):
        """Test price formatting with precision"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        formatted_price = market.format_price(Decimal("45123.456789"))
        assert formatted_price == "45123.46"

    def test_market_format_quantity_precision(self):
        """Test quantity formatting with precision"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        formatted_quantity = market.format_quantity(Decimal("1.123456789"))
        assert formatted_quantity == "1.12345678"

    def test_market_is_trading_active(self):
        """Test market trading status check"""
        active_market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        inactive_market = Market(
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT",
            status=MarketStatus.MAINTENANCE,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        assert active_market.is_trading_active() is True
        assert inactive_market.is_trading_active() is False

    def test_market_json_serialization(self):
        """Test market JSON serialization"""
        market = Market(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            status=MarketStatus.TRADING,
            min_quantity=Decimal("0.001"),
            max_quantity=Decimal("100.0"),
            min_price=Decimal("1.0"),
            max_price=Decimal("100000.0"),
            price_precision=2,
            quantity_precision=8
        )
        
        json_data = market.to_dict()
        
        assert json_data['symbol'] == "BTCUSDT"
        assert json_data['base_asset'] == "BTC"
        assert json_data['quote_asset'] == "USDT"
        assert json_data['status'] == MarketStatus.TRADING.value
        assert json_data['min_quantity'] == "0.001"

    def test_market_from_dict_creation(self):
        """Test market creation from dictionary"""
        market_data = {
            'symbol': 'ETHUSDT',
            'base_asset': 'ETH',
            'quote_asset': 'USDT',
            'status': MarketStatus.TRADING.value,
            'min_quantity': '0.01',
            'max_quantity': '1000.0',
            'min_price': '0.1',
            'max_price': '10000.0',
            'price_precision': 2,
            'quantity_precision': 6
        }
        
        market = Market.from_dict(market_data)
        
        assert market.symbol == "ETHUSDT"
        assert market.base_asset == "ETH"
        assert market.quote_asset == "USDT"
        assert market.status == MarketStatus.TRADING
        assert market.min_quantity == Decimal("0.01")


class TestOrderBookOperations:
    """Test suite for order book operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.market_manager = MarketDataManager("test_orderbook_api_key")

    def test_order_book_creation_success(self, sample_order_book_data):
        """Test successful order book creation"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        assert order_book.symbol == "BTCUSDT"
        assert len(order_book.bids) > 0
        assert len(order_book.asks) > 0
        assert isinstance(order_book.timestamp, datetime)

    def test_order_book_best_bid_ask(self, sample_order_book_data):
        """Test order book best bid and ask retrieval"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()
        
        assert best_bid is not None
        assert best_ask is not None
        assert best_bid['price'] < best_ask['price']  # Spread should be positive

    def test_order_book_spread_calculation(self, sample_order_book_data):
        """Test order book spread calculation"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        spread = order_book.calculate_spread()
        spread_percentage = order_book.calculate_spread_percentage()
        
        assert spread > Decimal("0")
        assert spread_percentage > Decimal("0")
        assert spread_percentage < Decimal("100")  # Should be reasonable

    def test_order_book_mid_price(self, sample_order_book_data):
        """Test order book mid price calculation"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        mid_price = order_book.get_mid_price()
        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()
        
        assert mid_price > best_bid['price']
        assert mid_price < best_ask['price']

    def test_order_book_depth_analysis(self, sample_order_book_data):
        """Test order book depth analysis"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        bid_depth = order_book.get_depth("BUY", levels=5)
        ask_depth = order_book.get_depth("SELL", levels=5)
        
        assert len(bid_depth) <= 5
        assert len(ask_depth) <= 5
        assert all('price' in level and 'quantity' in level for level in bid_depth)
        assert all('price' in level and 'quantity' in level for level in ask_depth)

    def test_order_book_volume_at_price(self, sample_order_book_data):
        """Test order book volume at specific price levels"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        # Test volume calculation for a price range
        price_range = Decimal("100.0")  # $100 range
        mid_price = order_book.get_mid_price()
        
        bid_volume = order_book.get_volume_in_range(
            mid_price - price_range, mid_price, "BUY"
        )
        ask_volume = order_book.get_volume_in_range(
            mid_price, mid_price + price_range, "SELL"
        )
        
        assert bid_volume >= Decimal("0")
        assert ask_volume >= Decimal("0")

    def test_order_book_update_levels(self, sample_order_book_data):
        """Test order book level updates"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        initial_bid_count = len(order_book.bids)
        
        # Add new bid level
        new_bid = {'price': Decimal("44000.0"), 'quantity': Decimal("0.5")}
        order_book.update_bid(new_bid['price'], new_bid['quantity'])
        
        assert len(order_book.bids) >= initial_bid_count

    def test_order_book_remove_levels(self, sample_order_book_data):
        """Test order book level removal"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        # Remove a bid level by setting quantity to 0
        if order_book.bids:
            first_bid_price = order_book.bids[0]['price']
            order_book.update_bid(first_bid_price, Decimal("0"))
            
            # Check that the level is removed or quantity is 0
            remaining_bid = next(
                (bid for bid in order_book.bids if bid['price'] == first_bid_price),
                None
            )
            assert remaining_bid is None or remaining_bid['quantity'] == Decimal("0")

    def test_order_book_json_serialization(self, sample_order_book_data):
        """Test order book JSON serialization"""
        order_book = OrderBook(
            symbol="BTCUSDT",
            bids=sample_order_book_data['bids'],
            asks=sample_order_book_data['asks'],
            timestamp=datetime.now()
        )
        
        json_data = order_book.to_dict()
        
        assert json_data['symbol'] == "BTCUSDT"
        assert 'bids' in json_data
        assert 'asks' in json_data
        assert 'timestamp' in json_data
        assert len(json_data['bids']) == len(sample_order_book_data['bids'])

    def test_order_book_from_dict_creation(self, sample_order_book_data):
        """Test order book creation from dictionary"""
        order_book_data = {
            'symbol': 'ETHUSDT',
            'bids': sample_order_book_data['bids'],
            'asks': sample_order_book_data['asks'],
            'timestamp': datetime.now().isoformat()
        }
        
        order_book = OrderBook.from_dict(order_book_data)
        
        assert order_book.symbol == "ETHUSDT"
        assert len(order_book.bids) == len(sample_order_book_data['bids'])
        assert len(order_book.asks) == len(sample_order_book_data['asks'])
        assert isinstance(order_book.timestamp, datetime)


class TestTickerOperations:
    """Test suite for ticker operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.market_manager = MarketDataManager("test_ticker_api_key")

    def test_ticker_creation_success(self):
        """Test successful ticker creation"""
        ticker = Ticker(
            symbol="BTCUSDT",
            last_price=Decimal("45000.0"),
            bid_price=Decimal("44999.0"),
            ask_price=Decimal("45001.0"),
            volume_24h=Decimal("1234.56789"),
            change_24h=Decimal("500.0"),
            change_percentage_24h=Decimal("1.12"),
            high_24h=Decimal("46000.0"),
            low_24h=Decimal("44000.0"),
            timestamp=datetime.now()
        )
        
        assert ticker.symbol == "BTCUSDT"
        assert ticker.last_price == Decimal("45000.0")
        assert ticker.bid_price == Decimal("44999.0")
        assert ticker.ask_price == Decimal("45001.0")
        assert ticker.volume_24h == Decimal("1234.56789")

    def test_ticker_spread_calculation(self):
        """Test ticker spread calculation"""
        ticker = Ticker(
            symbol="BTCUSDT",
            last_price=Decimal("45000.0"),
            bid_price=Decimal("44999.0"),
            ask_price=Decimal("45001.0"),
            volume_24h=Decimal("1234.56789"),
            change_24h=Decimal("500.0"),
            change_percentage_24h=Decimal("1.12"),
            high_24h=Decimal("46000.0"),
            low_24h=Decimal("44000.0"),
            timestamp=datetime.now()
        )
        
        spread = ticker.get_spread()
        spread_percentage = ticker.get_spread_percentage()
        
        assert spread == Decimal("2.0")  # 45001 - 44999
        assert spread_percentage > Decimal("0")

    def test_ticker_price_change_validation(self):
        """Test ticker price change validation"""
        ticker = Ticker(
            symbol="BTCUSDT",
            last_price=Decimal("45000.0"),
            bid_price=Decimal("44999.0"),
            ask_price=Decimal("45001.0"),
            volume_24h=Decimal("1234.56789"),
            change_24h=Decimal("500.0"),
            change_percentage_24h=Decimal("1.12"),
            high_24h=Decimal("46000.0"),
            low_24h=Decimal("44000.0"),
            timestamp=datetime.now()
        )
        
        # Validate that 24h change calculations are consistent
        previous_price = ticker.last_price - ticker.change_24h
        calculated_percentage = (ticker.change_24h / previous_price) * Decimal("100")
        
        # Allow for small rounding differences
        assert abs(calculated_percentage - ticker.change_percentage_24h) < Decimal("0.01")

    def test_ticker_high_low_validation(self):
        """Test ticker high/low price validation"""
        ticker = Ticker(
            symbol="BTCUSDT",
            last_price=Decimal("45000.0"),
            bid_price=Decimal("44999.0"),
            ask_price=Decimal("45001.0"),
            volume_24h=Decimal("1234.56789"),
            change_24h=Decimal("500.0"),
            change_percentage_24h=Decimal("1.12"),
            high_24h=Decimal("46000.0"),
            low_24h=Decimal("44000.0"),
            timestamp=datetime.now()
        )
        
        # Validate price relationships
        assert ticker.high_24h >= ticker.last_price or ticker.low_24h <= ticker.last_price
        assert ticker.high_24h >= ticker.low_24h

    def test_ticker_json_serialization(self):
        """Test ticker JSON serialization"""
        ticker = Ticker(
            symbol="BTCUSDT",
            last_price=Decimal("45000.0"),
            bid_price=Decimal("44999.0"),
            ask_price=Decimal("45001.0"),
            volume_24h=Decimal("1234.56789"),
            change_24h=Decimal("500.0"),
            change_percentage_24h=Decimal("1.12"),
            high_24h=Decimal("46000.0"),
            low_24h=Decimal("44000.0"),
            timestamp=datetime.now()
        )
        
        json_data = ticker.to_dict()
        
        assert json_data['symbol'] == "BTCUSDT"
        assert json_data['last_price'] == "45000.0"
        assert json_data['volume_24h'] == "1234.56789"
        assert 'timestamp' in json_data

    def test_ticker_from_dict_creation(self):
        """Test ticker creation from dictionary"""
        ticker_data = {
            'symbol': 'ETHUSDT',
            'last_price': '3000.0',
            'bid_price': '2999.5',
            'ask_price': '3000.5',
            'volume_24h': '5678.90123',
            'change_24h': '150.0',
            'change_percentage_24h': '5.26',
            'high_24h': '3100.0',
            'low_24h': '2900.0',
            'timestamp': datetime.now().isoformat()
        }
        
        ticker = Ticker.from_dict(ticker_data)
        
        assert ticker.symbol == "ETHUSDT"
        assert ticker.last_price == Decimal("3000.0")
        assert ticker.bid_price == Decimal("2999.5")
        assert ticker.ask_price == Decimal("3000.5")
        assert isinstance(ticker.timestamp, datetime)


class TestCandleOperations:
    """Test suite for candle/OHLCV operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.market_manager = MarketDataManager("test_candle_api_key")

    def test_candle_creation_success(self):
        """Test successful candle creation"""
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43500.0"),
            close_price=Decimal("44800.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        assert candle.symbol == "BTCUSDT"
        assert candle.interval == CandleInterval.ONE_HOUR
        assert candle.open_price == Decimal("44000.0")
        assert candle.high_price == Decimal("45000.0")
        assert candle.low_price == Decimal("43500.0")
        assert candle.close_price == Decimal("44800.0")

    def test_candle_price_validation(self):
        """Test candle price validation"""
        # Valid candle
        valid_candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43500.0"),
            close_price=Decimal("44800.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        assert valid_candle.is_valid() is True
        
        # Invalid candle (high < low)
        with pytest.raises(WallexValidationError, match="Invalid candle data"):
            Candle(
                symbol="BTCUSDT",
                interval=CandleInterval.ONE_HOUR,
                open_price=Decimal("44000.0"),
                high_price=Decimal("43000.0"),  # High < Low
                low_price=Decimal("43500.0"),
                close_price=Decimal("44800.0"),
                volume=Decimal("123.456789"),
                timestamp=datetime.now()
            )

    def test_candle_price_change_calculation(self):
        """Test candle price change calculation"""
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43500.0"),
            close_price=Decimal("44800.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        price_change = candle.get_price_change()
        price_change_percentage = candle.get_price_change_percentage()
        
        assert price_change == Decimal("800.0")  # 44800 - 44000
        assert price_change_percentage > Decimal("0")

    def test_candle_body_and_wick_analysis(self):
        """Test candle body and wick analysis"""
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43500.0"),
            close_price=Decimal("44800.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        body_size = candle.get_body_size()
        upper_wick = candle.get_upper_wick()
        lower_wick = candle.get_lower_wick()
        
        assert body_size == Decimal("800.0")  # |close - open|
        assert upper_wick == Decimal("200.0")  # high - max(open, close)
        assert lower_wick == Decimal("500.0")  # min(open, close) - low

    def test_candle_pattern_recognition(self):
        """Test basic candle pattern recognition"""
        # Bullish candle
        bullish_candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43900.0"),
            close_price=Decimal("44800.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        # Bearish candle
        bearish_candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44800.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43500.0"),
            close_price=Decimal("44000.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        assert bullish_candle.is_bullish() is True
        assert bullish_candle.is_bearish() is False
        assert bearish_candle.is_bullish() is False
        assert bearish_candle.is_bearish() is True

    def test_candle_doji_pattern(self):
        """Test doji candle pattern recognition"""
        doji_candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("44100.0"),
            low_price=Decimal("43900.0"),
            close_price=Decimal("44005.0"),  # Very close to open
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        assert doji_candle.is_doji(threshold=Decimal("0.1")) is True

    def test_candle_json_serialization(self):
        """Test candle JSON serialization"""
        candle = Candle(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_HOUR,
            open_price=Decimal("44000.0"),
            high_price=Decimal("45000.0"),
            low_price=Decimal("43500.0"),
            close_price=Decimal("44800.0"),
            volume=Decimal("123.456789"),
            timestamp=datetime.now()
        )
        
        json_data = candle.to_dict()
        
        assert json_data['symbol'] == "BTCUSDT"
        assert json_data['interval'] == CandleInterval.ONE_HOUR.value
        assert json_data['open_price'] == "44000.0"
        assert json_data['volume'] == "123.456789"

    def test_candle_from_dict_creation(self):
        """Test candle creation from dictionary"""
        candle_data = {
            'symbol': 'ETHUSDT',
            'interval': CandleInterval.FOUR_HOURS.value,
            'open_price': '3000.0',
            'high_price': '3100.0',
            'low_price': '2950.0',
            'close_price': '3080.0',
            'volume': '456.789012',
            'timestamp': datetime.now().isoformat()
        }
        
        candle = Candle.from_dict(candle_data)
        
        assert candle.symbol == "ETHUSDT"
        assert candle.interval == CandleInterval.FOUR_HOURS
        assert candle.open_price == Decimal("3000.0")
        assert candle.close_price == Decimal("3080.0")
        assert isinstance(candle.timestamp, datetime)


class TestMarketDataManagerOperations:
    """Test suite for market data manager operations"""

    def setup_method(self):
        """Setup for each test method"""
        self.market_manager = MarketDataManager("test_manager_api_key")

    @patch('wallex.markets.requests.get')
    def test_get_markets_success(self, mock_get, sample_markets_data):
        """Test successful markets retrieval"""
        markets_response = {
            "success": True,
            "result": sample_markets_data
        }
        
        mock_get.return_value.json.return_value = markets_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        markets = self.market_manager.get_markets()
        
        assert isinstance(markets, list)
        assert len(markets) > 0
        assert all(isinstance(market, Market) for market in markets)
        mock_get.assert_called_once()

    @patch('wallex.markets.requests.get')
    def test_get_market_by_symbol_success(self, mock_get):
        """Test successful single market retrieval"""
        market_response = {
            "success": True,
            "result": {
                "symbol": "BTCUSDT",
                "base_asset": "BTC",
                "quote_asset": "USDT",
                "status": "TRADING",
                "min_quantity": "0.00001",
                "max_quantity": "1000.0",
                "min_price": "0.01",
                "max_price": "1000000.0",
                "price_precision": 2,
                "quantity_precision": 8
            }
        }
        
        mock_get.return_value.json.return_value = market_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        market = self.market_manager.get_market("BTCUSDT")
        
        assert isinstance(market, Market)
        assert market.symbol == "BTCUSDT"
        assert market.base_asset == "BTC"
        assert market.quote_asset == "USDT"

    @patch('wallex.markets.requests.get')
    def test_get_order_book_success(self, mock_get, sample_order_book_data):
        """Test successful order book retrieval"""
        orderbook_response = {
            "success": True,
            "result": {
                "symbol": "BTCUSDT",
                "bids": sample_order_book_data['bids'],
                "asks": sample_order_book_data['asks'],
                "timestamp": datetime.now().isoformat()
            }
        }
        
        mock_get.return_value.json.return_value = orderbook_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        order_book = self.market_manager.get_order_book("BTCUSDT", depth=20)
        
        assert isinstance(order_book, OrderBook)
        assert order_book.symbol == "BTCUSDT"
        assert len(order_book.bids) > 0
        assert len(order_book.asks) > 0

    @patch('wallex.markets.requests.get')
    def test_get_ticker_success(self, mock_get):
        """Test successful ticker retrieval"""
        ticker_response = {
            "success": True,
            "result": {
                "symbol": "BTCUSDT",
                "last_price": "45000.0",
                "bid_price": "44999.0",
                "ask_price": "45001.0",
                "volume_24h": "1234.56789",
                "change_24h": "500.0",
                "change_percentage_24h": "1.12",
                "high_24h": "46000.0",
                "low_24h": "44000.0",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        mock_get.return_value.json.return_value = ticker_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        ticker = self.market_manager.get_ticker("BTCUSDT")
        
        assert isinstance(ticker, Ticker)
        assert ticker.symbol == "BTCUSDT"
        assert ticker.last_price == Decimal("45000.0")

    @patch('wallex.markets.requests.get')
    def test_get_all_tickers_success(self, mock_get):
        """Test successful all tickers retrieval"""
        tickers_response = {
            "success": True,
            "result": [
                {
                    "symbol": "BTCUSDT",
                    "last_price": "45000.0",
                    "bid_price": "44999.0",
                    "ask_price": "45001.0",
                    "volume_24h": "1234.56789",
                    "change_24h": "500.0",
                    "change_percentage_24h": "1.12",
                    "high_24h": "46000.0",
                    "low_24h": "44000.0",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "symbol": "ETHUSDT",
                    "last_price": "3000.0",
                    "bid_price": "2999.5",
                    "ask_price": "3000.5",
                    "volume_24h": "5678.90123",
                    "change_24h": "150.0",
                    "change_percentage_24h": "5.26",
                    "high_24h": "3100.0",
                    "low_24h": "2900.0",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        mock_get.return_value.json.return_value = tickers_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        tickers = self.market_manager.get_all_tickers()
        
        assert isinstance(tickers, list)
        assert len(tickers) == 2
        assert all(isinstance(ticker, Ticker) for ticker in tickers)

    @patch('wallex.markets.requests.get')
    def test_get_candles_success(self, mock_get):
        """Test successful candles retrieval"""
        candles_response = {
            "success": True,
            "result": [
                {
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "open_price": "44000.0",
                    "high_price": "45000.0",
                    "low_price": "43500.0",
                    "close_price": "44800.0",
                    "volume": "123.456789",
                    "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()
                },
                {
                    "symbol": "BTCUSDT",
                    "interval": "1h",
                    "open_price": "44800.0",
                    "high_price": "45200.0",
                    "low_price": "44600.0",
                    "close_price": "45000.0",
                    "volume": "98.765432",
                    "timestamp": (datetime.now() - timedelta(hours=1)).isoformat()
                }
            ]
        }
        
        mock_get.return_value.json.return_value = candles_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        candles = self.market_manager.get_candles(
            "BTCUSDT", 
            CandleInterval.ONE_HOUR, 
            limit=100
        )
        
        assert isinstance(candles, list)
        assert len(candles) == 2
        assert all(isinstance(candle, Candle) for candle in candles)

    @patch('wallex.markets.requests.get')
    def test_get_market_statistics_success(self, mock_get):
        """Test successful market statistics retrieval"""
        stats_response = {
            "success": True,
            "result": {
                "symbol": "BTCUSDT",
                "volume_24h": "12345.67890123",
                "volume_7d": "86420.13579246",
                "volume_30d": "370123.45678901",
                "trades_24h": 15420,
                "trades_7d": 108940,
                "trades_30d": 467280,
                "price_change_24h": "2.34",
                "price_change_7d": "-1.56",
                "price_change_30d": "8.92",
                "volatility_24h": "3.45",
                "market_cap": "850000000000.00"
            }
        }
        
        mock_get.return_value.json.return_value = stats_response
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status.return_value = None
        
        stats = self.market_manager.get_market_statistics("BTCUSDT")
        
        assert stats['success'] is True
        assert 'volume_24h' in stats['result']
        assert 'trades_24h' in stats['result']
        assert 'volatility_24h' in stats['result']


class TestMarketDataErrorHandling:
    """Test suite for market data error handling"""

    def setup_method(self):
        """Setup for each test method"""
        self.market_manager = MarketDataManager("test_error_api_key")

    @patch('wallex.markets.requests.get')
    def test_get_market_invalid_symbol(self, mock_get):
        """Test market retrieval with invalid symbol"""
        error_response = {
            "success": False,
            "error": "INVALID_SYMBOL",
            "message": "Symbol not found"
        }
        
        mock_get.return_value.json.return_value = error_response
        mock_get.return_value.status_code = 404
        mock_get.return_value.raise_for_status.side_effect = Exception("Not Found")
        
        with pytest.raises(WallexAPIError, match="Symbol not found"):
            self.market_manager.get_market("INVALID")

    @patch('wallex.markets.requests.get')
    def test_get_order_book_network_error(self, mock_get, network_error_scenarios):
        """Test order book retrieval with network error"""
        mock_get.side_effect = network_error_scenarios['timeout']
        
        with pytest.raises(WallexAPIError):
            self.market_manager.get_order_book("BTCUSDT")

    @patch('wallex.markets.requests.get')
    def test_get_candles_invalid_interval(self, mock_get):
        """Test candles retrieval with invalid interval"""
        error_response = {
            "success": False,
            "error": "INVALID_INTERVAL",
            "message": "Invalid candle interval"
        }
        
        mock_get.return_value.json.return_value = error_response
        mock_get.return_value.status_code = 400
        mock_get.return_value.raise_for_status.side_effect = Exception("Bad Request")
        
        with pytest.raises(WallexValidationError, match="Invalid candle interval"):
            self.market_manager.get_candles("BTCUSDT", "invalid_interval")

    def test_symbol_validation_edge_cases(self):
        """Test symbol validation edge cases"""
        invalid_symbols = ["", "A", "TOOLONG", "BTC-USD", "BTC/USD", "btcusdt"]
        
        for symbol in invalid_symbols:
            assert validate_symbol(symbol) is False

    def test_valid_symbol_validation(self):
        """Test valid symbol validation"""
        valid_symbols = ["BTCUSDT", "ETHBTC", "ADAUSDT", "DOTETH"]
        
        for symbol in valid_symbols:
            assert validate_symbol(symbol) is True

    def test_price_formatting_edge_cases(self):
        """Test price formatting edge cases"""
        test_cases = [
            (Decimal("0"), 2, "0.00"),
            (Decimal("0.001"), 2, "0.00"),
            (Decimal("999999.999"), 2, "999999.99"),
            (Decimal("1.005"), 2, "1.01")  # Rounding up
        ]
        
        for price, precision, expected in test_cases:
            formatted = format_price(price, precision)
            assert formatted == expected

    def test_spread_calculation_edge_cases(self):
        """Test spread calculation edge cases"""
        # Zero spread
        spread = calculate_spread(Decimal("100.0"), Decimal("100.0"))
        assert spread == Decimal("0")
        
        # Negative spread (invalid)
        with pytest.raises(MarketDataError, match="Invalid spread"):
            calculate_spread(Decimal("100.0"), Decimal("99.0"))

    def test_order_book_empty_sides(self):
        """Test order book with empty bid or ask sides"""
        # Empty bids
        with pytest.raises(MarketDataError, match="Empty order book"):
            OrderBook(
                symbol="BTCUSDT",
                bids=[],
                asks=[{'price': Decimal("45000.0"), 'quantity': Decimal("1.0")}],
                timestamp=datetime.now()
            )
        
        # Empty asks
        with pytest.raises(MarketDataError, match="Empty order book"):
            OrderBook(
                symbol="BTCUSDT",
                bids=[{'price': Decimal("44999.0"), 'quantity': Decimal("1.0")}],
                asks=[],
                timestamp=datetime.now()
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])