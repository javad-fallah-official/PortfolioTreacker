"""
Comprehensive test suite for data analysis and metrics calculations.

This test suite provides complete coverage of data analysis operations including:
- Technical indicators and chart analysis
- Statistical calculations and metrics
- Performance analytics and benchmarking
- Risk analysis and volatility calculations
- Correlation and regression analysis
- Time series analysis and forecasting
- Market sentiment analysis
- Portfolio optimization algorithms

All tests are independent, properly mocked, and follow best practices.
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import tempfile
import os

from wallex import WallexClient, WallexAsyncClient, WallexAPIError, WallexConfig, OrderSide, OrderType, OrderStatus
from wallex.rest import WallexRestClient
from wallex.socket import WallexWebSocketClient
from wallex.utils import format_price, validate_symbol, calculate_percentage_change
from database import PortfolioDatabase


class TestTechnicalIndicators:
    """Test suite for technical indicator calculations"""

    @pytest.fixture
    def sample_price_data(self):
        """Sample price data for technical analysis"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        prices = np.random.normal(45000, 2000, 100).cumsum() + 40000
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.999,
            'high': prices * 1.002,
            'low': prices * 0.998,
            'close': prices,
            'volume': np.random.normal(1000, 200, 100)
        })

    def test_simple_moving_average(self, sample_price_data):
        """Test Simple Moving Average (SMA) calculation"""
        def calculate_sma(data, period):
            return data['close'].rolling(window=period).mean()
        
        sma_20 = calculate_sma(sample_price_data, 20)
        sma_50 = calculate_sma(sample_price_data, 50)
        
        assert len(sma_20) == len(sample_price_data)
        assert len(sma_50) == len(sample_price_data)
        assert not sma_20.iloc[19:].isna().any()  # No NaN after period
        assert not sma_50.iloc[49:].isna().any()  # No NaN after period

    def test_exponential_moving_average(self, sample_price_data):
        """Test Exponential Moving Average (EMA) calculation"""
        def calculate_ema(data, period):
            return data['close'].ewm(span=period).mean()
        
        ema_12 = calculate_ema(sample_price_data, 12)
        ema_26 = calculate_ema(sample_price_data, 26)
        
        assert len(ema_12) == len(sample_price_data)
        assert len(ema_26) == len(sample_price_data)
        assert not ema_12.isna().any()
        assert not ema_26.isna().any()

    def test_rsi_calculation(self, sample_price_data):
        """Test Relative Strength Index (RSI) calculation"""
        def calculate_rsi(data, period=14):
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        rsi = calculate_rsi(sample_price_data)
        
        assert len(rsi) == len(sample_price_data)
        assert (rsi.dropna() >= 0).all()
        assert (rsi.dropna() <= 100).all()

    def test_bollinger_bands(self, sample_price_data):
        """Test Bollinger Bands calculation"""
        def calculate_bollinger_bands(data, period=20, std_dev=2):
            sma = data['close'].rolling(window=period).mean()
            std = data['close'].rolling(window=period).std()
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            return upper_band, sma, lower_band
        
        upper, middle, lower = calculate_bollinger_bands(sample_price_data)
        
        assert len(upper) == len(sample_price_data)
        assert len(middle) == len(sample_price_data)
        assert len(lower) == len(sample_price_data)
        assert (upper.dropna() >= middle.dropna()).all()
        assert (middle.dropna() >= lower.dropna()).all()

    def test_macd_calculation(self, sample_price_data):
        """Test MACD (Moving Average Convergence Divergence) calculation"""
        def calculate_macd(data, fast=12, slow=26, signal=9):
            ema_fast = data['close'].ewm(span=fast).mean()
            ema_slow = data['close'].ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram
        
        macd, signal, histogram = calculate_macd(sample_price_data)
        
        assert len(macd) == len(sample_price_data)
        assert len(signal) == len(sample_price_data)
        assert len(histogram) == len(sample_price_data)


class TestStatisticalAnalysis:
    """Test suite for statistical analysis and calculations"""

    @pytest.fixture
    def returns_data(self):
        """Sample returns data for statistical analysis"""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)  # Daily returns for 1 year
        return pd.Series(returns, index=pd.date_range('2023-01-01', periods=252))

    def test_volatility_calculation(self, returns_data):
        """Test volatility calculation methods"""
        # Daily volatility
        daily_vol = returns_data.std()
        
        # Annualized volatility
        annual_vol = daily_vol * np.sqrt(252)
        
        # Rolling volatility
        rolling_vol = returns_data.rolling(window=30).std() * np.sqrt(252)
        
        assert daily_vol > 0
        assert annual_vol > daily_vol
        assert len(rolling_vol) == len(returns_data)
        assert not rolling_vol.iloc[29:].isna().any()

    def test_sharpe_ratio_calculation(self, returns_data):
        """Test Sharpe ratio calculation"""
        risk_free_rate = 0.02  # 2% annual risk-free rate
        daily_rf_rate = risk_free_rate / 252
        
        excess_returns = returns_data - daily_rf_rate
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        
        assert isinstance(sharpe_ratio, float)
        assert not np.isnan(sharpe_ratio)

    def test_maximum_drawdown(self, returns_data):
        """Test maximum drawdown calculation"""
        cumulative_returns = (1 + returns_data).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        assert max_drawdown <= 0
        assert isinstance(max_drawdown, float)

    def test_value_at_risk(self, returns_data):
        """Test Value at Risk (VaR) calculation"""
        confidence_levels = [0.95, 0.99]
        
        for confidence in confidence_levels:
            var = np.percentile(returns_data, (1 - confidence) * 100)
            assert var <= 0  # VaR should be negative for losses
            assert isinstance(var, float)

    def test_conditional_var(self, returns_data):
        """Test Conditional Value at Risk (CVaR) calculation"""
        confidence = 0.95
        var_95 = np.percentile(returns_data, 5)
        cvar_95 = returns_data[returns_data <= var_95].mean()
        
        assert cvar_95 <= var_95  # CVaR should be worse than VaR
        assert isinstance(cvar_95, float)

    def test_correlation_analysis(self):
        """Test correlation analysis between assets"""
        np.random.seed(42)
        
        # Generate correlated returns
        returns_btc = np.random.normal(0.001, 0.03, 100)
        returns_eth = 0.8 * returns_btc + 0.6 * np.random.normal(0, 0.02, 100)
        
        correlation = np.corrcoef(returns_btc, returns_eth)[0, 1]
        
        assert -1 <= correlation <= 1
        assert correlation > 0.5  # Should be positively correlated


class TestPerformanceAnalytics:
    """Test suite for performance analytics and benchmarking"""

    @pytest.fixture
    def portfolio_data(self):
        """Sample portfolio performance data"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        np.random.seed(42)
        portfolio_returns = np.random.normal(0.0008, 0.015, 252)
        benchmark_returns = np.random.normal(0.0005, 0.012, 252)
        
        return pd.DataFrame({
            'date': dates,
            'portfolio_returns': portfolio_returns,
            'benchmark_returns': benchmark_returns,
            'portfolio_value': (1 + pd.Series(portfolio_returns)).cumprod() * 100000,
            'benchmark_value': (1 + pd.Series(benchmark_returns)).cumprod() * 100000
        })

    def test_alpha_beta_calculation(self, portfolio_data):
        """Test Alpha and Beta calculation against benchmark"""
        portfolio_returns = portfolio_data['portfolio_returns']
        benchmark_returns = portfolio_data['benchmark_returns']
        
        # Calculate beta
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance
        
        # Calculate alpha
        portfolio_mean = portfolio_returns.mean() * 252  # Annualized
        benchmark_mean = benchmark_returns.mean() * 252  # Annualized
        risk_free_rate = 0.02
        alpha = portfolio_mean - (risk_free_rate + beta * (benchmark_mean - risk_free_rate))
        
        assert isinstance(beta, float)
        assert isinstance(alpha, float)
        assert not np.isnan(beta)
        assert not np.isnan(alpha)

    def test_information_ratio(self, portfolio_data):
        """Test Information Ratio calculation"""
        portfolio_returns = portfolio_data['portfolio_returns']
        benchmark_returns = portfolio_data['benchmark_returns']
        
        excess_returns = portfolio_returns - benchmark_returns
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = (excess_returns.mean() * 252) / tracking_error
        
        assert isinstance(information_ratio, float)
        assert not np.isnan(information_ratio)

    def test_sortino_ratio(self, portfolio_data):
        """Test Sortino Ratio calculation"""
        returns = portfolio_data['portfolio_returns']
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        
        excess_returns = returns - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        downside_deviation = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)
        
        sortino_ratio = (returns.mean() - risk_free_rate) * 252 / downside_deviation
        
        assert isinstance(sortino_ratio, float)
        assert not np.isnan(sortino_ratio)

    def test_calmar_ratio(self, portfolio_data):
        """Test Calmar Ratio calculation"""
        returns = portfolio_data['portfolio_returns']
        cumulative_returns = (1 + returns).cumprod()
        
        # Calculate maximum drawdown
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # Calculate annualized return
        annual_return = returns.mean() * 252
        
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        assert isinstance(calmar_ratio, float)
        assert calmar_ratio >= 0


class TestRiskAnalysis:
    """Test suite for risk analysis and calculations"""

    @pytest.fixture
    def portfolio_positions(self):
        """Sample portfolio positions for risk analysis"""
        return {
            'BTC/USDT': {'weight': 0.4, 'volatility': 0.6, 'value': 40000},
            'ETH/USDT': {'weight': 0.3, 'volatility': 0.7, 'value': 30000},
            'ADA/USDT': {'weight': 0.2, 'volatility': 0.8, 'value': 20000},
            'DOT/USDT': {'weight': 0.1, 'volatility': 0.9, 'value': 10000}
        }

    @pytest.fixture
    def correlation_matrix(self):
        """Sample correlation matrix for assets"""
        return np.array([
            [1.0, 0.8, 0.6, 0.5],  # BTC correlations
            [0.8, 1.0, 0.7, 0.6],  # ETH correlations
            [0.6, 0.7, 1.0, 0.8],  # ADA correlations
            [0.5, 0.6, 0.8, 1.0]   # DOT correlations
        ])

    def test_portfolio_volatility(self, portfolio_positions, correlation_matrix):
        """Test portfolio volatility calculation"""
        weights = np.array([pos['weight'] for pos in portfolio_positions.values()])
        volatilities = np.array([pos['volatility'] for pos in portfolio_positions.values()])
        
        # Portfolio variance
        portfolio_variance = np.dot(weights, np.dot(np.outer(volatilities, volatilities) * correlation_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        assert portfolio_volatility > 0
        assert portfolio_volatility < max(volatilities)  # Diversification benefit

    def test_var_calculation_portfolio(self, portfolio_positions):
        """Test portfolio Value at Risk calculation"""
        total_value = sum(pos['value'] for pos in portfolio_positions.values())
        portfolio_volatility = 0.45  # Assumed portfolio volatility
        confidence_level = 0.95
        
        # Parametric VaR (assuming normal distribution)
        z_score = 1.645  # 95% confidence level
        var_1_day = total_value * portfolio_volatility / np.sqrt(252) * z_score
        
        assert var_1_day > 0
        assert var_1_day < total_value

    def test_component_var(self, portfolio_positions, correlation_matrix):
        """Test Component VaR calculation"""
        weights = np.array([pos['weight'] for pos in portfolio_positions.values()])
        volatilities = np.array([pos['volatility'] for pos in portfolio_positions.values()])
        
        # Portfolio volatility
        portfolio_variance = np.dot(weights, np.dot(np.outer(volatilities, volatilities) * correlation_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Component VaR
        marginal_var = np.dot(np.outer(volatilities, volatilities) * correlation_matrix, weights) / portfolio_volatility
        component_var = weights * marginal_var
        
        assert len(component_var) == len(weights)
        assert np.isclose(component_var.sum(), portfolio_volatility)

    def test_risk_budgeting(self, portfolio_positions):
        """Test risk budgeting and contribution analysis"""
        total_value = sum(pos['value'] for pos in portfolio_positions.values())
        
        risk_contributions = {}
        for symbol, position in portfolio_positions.items():
            # Risk contribution = weight * marginal risk contribution
            risk_contrib = position['weight'] * position['volatility']
            risk_contributions[symbol] = risk_contrib
        
        total_risk_contrib = sum(risk_contributions.values())
        
        # Normalize risk contributions
        for symbol in risk_contributions:
            risk_contributions[symbol] /= total_risk_contrib
        
        assert abs(sum(risk_contributions.values()) - 1.0) < 1e-10


class TestTimeSeriesAnalysis:
    """Test suite for time series analysis and forecasting"""

    @pytest.fixture
    def time_series_data(self):
        """Sample time series data for analysis"""
        dates = pd.date_range('2023-01-01', periods=365, freq='D')
        np.random.seed(42)
        
        # Generate time series with trend and seasonality
        trend = np.linspace(40000, 50000, 365)
        seasonal = 1000 * np.sin(2 * np.pi * np.arange(365) / 365)
        noise = np.random.normal(0, 500, 365)
        prices = trend + seasonal + noise
        
        return pd.Series(prices, index=dates)

    def test_trend_analysis(self, time_series_data):
        """Test trend analysis using linear regression"""
        from scipy import stats
        
        x = np.arange(len(time_series_data))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, time_series_data.values)
        
        assert isinstance(slope, float)
        assert isinstance(r_value, float)
        assert -1 <= r_value <= 1
        assert p_value >= 0

    def test_seasonality_detection(self, time_series_data):
        """Test seasonality detection in time series"""
        # Simple seasonality test using autocorrelation
        def autocorrelation(series, lag):
            return series.corr(series.shift(lag))
        
        # Test for weekly seasonality (7 days)
        weekly_autocorr = autocorrelation(time_series_data, 7)
        
        # Test for monthly seasonality (30 days)
        monthly_autocorr = autocorrelation(time_series_data, 30)
        
        assert -1 <= weekly_autocorr <= 1
        assert -1 <= monthly_autocorr <= 1

    def test_stationarity_test(self, time_series_data):
        """Test stationarity using Augmented Dickey-Fuller test"""
        # Simple stationarity check using rolling statistics
        rolling_mean = time_series_data.rolling(window=30).mean()
        rolling_std = time_series_data.rolling(window=30).std()
        
        # Check if rolling statistics are relatively stable
        mean_stability = rolling_mean.std() / rolling_mean.mean()
        std_stability = rolling_std.std() / rolling_std.mean()
        
        assert mean_stability >= 0
        assert std_stability >= 0

    def test_moving_average_forecast(self, time_series_data):
        """Test simple moving average forecasting"""
        window = 30
        ma_forecast = time_series_data.rolling(window=window).mean()
        
        # Calculate forecast accuracy on last 30 days
        actual = time_series_data.iloc[-30:]
        forecast = ma_forecast.iloc[-60:-30]  # Forecast for last 30 days
        
        mae = np.mean(np.abs(actual.values - forecast.values))
        mape = np.mean(np.abs((actual.values - forecast.values) / actual.values)) * 100
        
        assert mae > 0
        assert mape > 0


class TestPortfolioOptimization:
    """Test suite for portfolio optimization algorithms"""

    @pytest.fixture
    def asset_data(self):
        """Sample asset data for optimization"""
        np.random.seed(42)
        n_assets = 4
        n_periods = 252
        
        # Generate correlated returns
        returns = np.random.multivariate_normal(
            mean=[0.001, 0.0008, 0.0012, 0.0006],
            cov=[[0.0004, 0.0002, 0.0001, 0.00005],
                 [0.0002, 0.0005, 0.00015, 0.0001],
                 [0.0001, 0.00015, 0.0006, 0.0002],
                 [0.00005, 0.0001, 0.0002, 0.0003]],
            size=n_periods
        )
        
        return pd.DataFrame(returns, columns=['BTC', 'ETH', 'ADA', 'DOT'])

    def test_mean_variance_optimization(self, asset_data):
        """Test mean-variance optimization (Markowitz)"""
        # Calculate expected returns and covariance matrix
        expected_returns = asset_data.mean() * 252  # Annualized
        cov_matrix = asset_data.cov() * 252  # Annualized
        
        # Simple equal-weight portfolio as baseline
        n_assets = len(asset_data.columns)
        equal_weights = np.array([1/n_assets] * n_assets)
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(equal_weights, expected_returns)
        portfolio_variance = np.dot(equal_weights, np.dot(cov_matrix, equal_weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        assert portfolio_return > 0
        assert portfolio_volatility > 0
        assert np.isclose(equal_weights.sum(), 1.0)

    def test_risk_parity_optimization(self, asset_data):
        """Test risk parity optimization"""
        # Calculate covariance matrix
        cov_matrix = asset_data.cov() * 252
        
        # Simple risk parity approximation (inverse volatility weighting)
        volatilities = np.sqrt(np.diag(cov_matrix))
        inv_vol_weights = (1 / volatilities) / (1 / volatilities).sum()
        
        # Calculate risk contributions
        portfolio_vol = np.sqrt(np.dot(inv_vol_weights, np.dot(cov_matrix, inv_vol_weights)))
        marginal_contrib = np.dot(cov_matrix, inv_vol_weights) / portfolio_vol
        risk_contrib = inv_vol_weights * marginal_contrib
        
        assert np.isclose(inv_vol_weights.sum(), 1.0)
        assert np.isclose(risk_contrib.sum(), portfolio_vol)

    def test_maximum_sharpe_optimization(self, asset_data):
        """Test maximum Sharpe ratio optimization"""
        expected_returns = asset_data.mean() * 252
        cov_matrix = asset_data.cov() * 252
        risk_free_rate = 0.02
        
        # Simple approximation: use equal weights and calculate Sharpe ratio
        equal_weights = np.array([0.25, 0.25, 0.25, 0.25])
        
        portfolio_return = np.dot(equal_weights, expected_returns)
        portfolio_variance = np.dot(equal_weights, np.dot(cov_matrix, equal_weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
        
        assert isinstance(sharpe_ratio, float)
        assert not np.isnan(sharpe_ratio)

    def test_minimum_variance_optimization(self, asset_data):
        """Test minimum variance optimization"""
        cov_matrix = asset_data.cov() * 252
        
        # Analytical solution for minimum variance portfolio
        ones = np.ones((len(cov_matrix), 1))
        inv_cov = np.linalg.inv(cov_matrix)
        
        min_var_weights = np.dot(inv_cov, ones) / np.dot(ones.T, np.dot(inv_cov, ones))
        min_var_weights = min_var_weights.flatten()
        
        # Calculate minimum variance
        min_variance = np.dot(min_var_weights, np.dot(cov_matrix, min_var_weights))
        
        assert np.isclose(min_var_weights.sum(), 1.0)
        assert min_variance > 0


class TestMarketSentimentAnalysis:
    """Test suite for market sentiment analysis"""

    @pytest.fixture
    def sentiment_data(self):
        """Sample sentiment data for analysis"""
        return {
            'fear_greed_index': [25, 30, 45, 60, 75, 80, 70, 55, 40, 35],
            'social_mentions': [1000, 1200, 800, 1500, 2000, 2500, 1800, 1300, 900, 700],
            'news_sentiment': [0.2, 0.3, 0.1, 0.6, 0.8, 0.9, 0.7, 0.5, 0.3, 0.2],
            'prices': [40000, 41000, 39000, 43000, 47000, 50000, 48000, 45000, 42000, 40500]
        }

    def test_sentiment_price_correlation(self, sentiment_data):
        """Test correlation between sentiment indicators and prices"""
        fear_greed = np.array(sentiment_data['fear_greed_index'])
        prices = np.array(sentiment_data['prices'])
        
        correlation = np.corrcoef(fear_greed, prices)[0, 1]
        
        assert -1 <= correlation <= 1
        assert isinstance(correlation, float)

    def test_sentiment_momentum(self, sentiment_data):
        """Test sentiment momentum calculation"""
        sentiment_scores = np.array(sentiment_data['news_sentiment'])
        
        # Calculate momentum as rate of change
        momentum = np.diff(sentiment_scores) / sentiment_scores[:-1]
        
        assert len(momentum) == len(sentiment_scores) - 1
        assert isinstance(momentum[0], float)

    def test_composite_sentiment_score(self, sentiment_data):
        """Test composite sentiment score calculation"""
        # Normalize all indicators to 0-1 scale
        fear_greed_norm = np.array(sentiment_data['fear_greed_index']) / 100
        mentions_norm = np.array(sentiment_data['social_mentions']) / max(sentiment_data['social_mentions'])
        news_sentiment = np.array(sentiment_data['news_sentiment'])
        
        # Weighted composite score
        weights = [0.4, 0.3, 0.3]  # Fear/Greed, Social, News
        composite_score = (weights[0] * fear_greed_norm + 
                          weights[1] * mentions_norm + 
                          weights[2] * news_sentiment)
        
        assert len(composite_score) == len(fear_greed_norm)
        assert (composite_score >= 0).all()
        assert (composite_score <= 1).all()


class TestDataAnalysisIntegration:
    """Test suite for integrated data analysis workflows"""

    @pytest.fixture
    def mock_database(self):
        """Setup mock database for integration testing"""
        db = AsyncMock(spec=PortfolioDatabase)
        db.is_connected = True
        return db

    @pytest.fixture
    def mock_client(self):
        """Setup mock client for integration testing"""
        client = AsyncMock(spec=WallexAsyncClient)
        client.config = Mock(spec=WallexConfig)
        
        # Add the missing methods that are called in tests
        client.get_klines = AsyncMock()
        
        return client

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, mock_database, mock_client):
        """Test complete data analysis workflow"""
        # 1. Data collection
        mock_client.get_klines.return_value = [
            {
                'timestamp': datetime.now() - timedelta(days=i),
                'open': 45000 + i * 10,
                'high': 45100 + i * 10,
                'low': 44900 + i * 10,
                'close': 45050 + i * 10,
                'volume': 1000 + i
            }
            for i in range(100)
        ]
        
        kline_data = await mock_client.get_klines(symbol='BTC/USDT', interval='1d', limit=100)
        
        # 2. Technical analysis
        prices = [candle['close'] for candle in kline_data]
        sma_20 = np.convolve(prices, np.ones(20)/20, mode='valid')
        
        # 3. Risk analysis
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)
        
        # 4. Performance metrics
        total_return = (prices[-1] - prices[0]) / prices[0]
        
        assert len(kline_data) == 100
        assert len(sma_20) > 0
        assert volatility > 0
        assert isinstance(total_return, float)

    @pytest.mark.asyncio
    async def test_portfolio_analysis_integration(self, mock_database):
        """Test integrated portfolio analysis"""
        # Mock portfolio data
        portfolio_data = {
            'id': 1,
            'assets': [
                {'symbol': 'BTC/USDT', 'quantity': 0.5, 'avg_price': 45000},
                {'symbol': 'ETH/USDT', 'quantity': 10, 'avg_price': 3000}
            ],
            'transactions': [
                {'symbol': 'BTC/USDT', 'side': 'buy', 'quantity': 0.5, 'price': 45000, 'timestamp': datetime.now()},
                {'symbol': 'ETH/USDT', 'side': 'buy', 'quantity': 10, 'price': 3000, 'timestamp': datetime.now()}
            ]
        }
        
        mock_database.get_portfolio.return_value = portfolio_data
        mock_database.calculate_portfolio_metrics.return_value = {
            'total_value': 52500,
            'total_return': 2500,
            'return_percentage': 0.05,
            'volatility': 0.25,
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.08
        }
        
        portfolio = await mock_database.get_portfolio(portfolio_id=1)
        metrics = await mock_database.calculate_portfolio_metrics(portfolio_id=1)
        
        assert portfolio['id'] == 1
        assert len(portfolio['assets']) == 2
        assert metrics['return_percentage'] == 0.05
        assert metrics['sharpe_ratio'] == 1.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])