#!/usr/bin/env python3
"""
FastAPI Web UI for Wallex Wallet Balance Display
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional

# Load environment variables first, before importing any modules that need them
from dotenv import load_dotenv
load_dotenv()  # Make sure .env is loaded before WallexClient and PortfolioDatabase imports

from wallex import WallexClient
from wallex.exceptions import WallexAuthenticationError
from database import PortfolioDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wallex Wallet Dashboard", description="View your Wallex wallet balances")

# Create templates directory if it doesn't exist
import pathlib
templates_dir = pathlib.Path("templates")
templates_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="templates")

class WalletService:
    """Service to handle wallet operations"""
    
    def __init__(self):
        self.api_key = os.getenv('WALLEX_API_KEY')
        if not self.api_key:
            raise ValueError("WALLEX_API_KEY not found in environment variables")
        self.client = WallexClient(self.api_key)
        self.db = PortfolioDatabase()  # Initialize database

    async def init(self) -> None:
        """Initialize async database pool/schema."""
        try:
            await self.db.init()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            return self.client.get_account_info()
        except WallexAuthenticationError as e:
            raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")

    async def get_balances(self) -> Dict:
        """Get wallet balances"""
        try:
            return self.client.get_balances()
        except WallexAuthenticationError as e:
            raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get balances: {str(e)}")
    
    async def get_fallback_prices(self, missing_assets: list, usdt_to_tmn_rate: float) -> Dict:
        """Get prices from CoinGecko for assets not available on Wallex"""
        fallback_prices = {}
        
        # Asset symbol mapping for CoinGecko API
        coingecko_mapping = {
            'AGLD': 'adventure-gold',
            'BAT': 'basic-attention-token',
            'BTTC': 'bittorrent-chain',
            'CVC': 'civic',
            'IMX': 'immutable-x',
            'OPUL': 'opulous',
            'ORAI': 'oraichain-token',
            'PENGU': 'pudgy-penguins',
            'RBTC': 'rootstock',  # Note: RBTC might have incorrect pricing, needs verification
            'RENDER': 'render-token',
            'RSR': 'reserve-rights-token',
            'WOO': 'woo-network',
            'TMN': None  # TMN is Iranian Toman, set to 1 USD = 87757 TMN (approximate)
        }
        
        try:
            import requests
            
            # Handle TMN separately (Iranian Toman)
            if 'TMN' in missing_assets:
                fallback_prices['TMN'] = {
                    'usd_price': 1.0 / usdt_to_tmn_rate if usdt_to_tmn_rate > 0 else 0,
                    'tmn_price': 1.0
                }
            
            # Get CoinGecko IDs for the missing assets
            coingecko_ids = []
            asset_to_id_map = {}
            
            for asset in missing_assets:
                if asset in coingecko_mapping and coingecko_mapping[asset]:
                    # Skip RBTC due to incorrect pricing from CoinGecko
                    if asset == 'RBTC':
                        logger.warning(f"Skipping {asset} due to potential pricing issues")
                        continue
                    
                    coingecko_id = coingecko_mapping[asset]
                    coingecko_ids.append(coingecko_id)
                    asset_to_id_map[coingecko_id] = asset
            
            if coingecko_ids:
                # Fetch prices from CoinGecko
                ids_str = ','.join(coingecko_ids)
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
                
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    price_data = response.json()
                    
                    for coingecko_id, asset in asset_to_id_map.items():
                        if coingecko_id in price_data and 'usd' in price_data[coingecko_id]:
                            usd_price = float(price_data[coingecko_id]['usd'])
                            fallback_prices[asset] = {
                                'usd_price': usd_price,
                                'tmn_price': usd_price * usdt_to_tmn_rate
                            }
                            logger.info(f"Fetched fallback price for {asset}: ${usd_price}")
                        else:
                            logger.warning(f"No price data found for {asset} ({coingecko_id})")
                else:
                    logger.warning(f"CoinGecko API request failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error fetching fallback prices: {e}")
        
        return fallback_prices

    async def get_fallback_24h_data(self, assets_list: list) -> Dict:
        """Get 24h market data from CoinGecko for assets missing this data"""
        fallback_24h_data = {}
        
        # Asset symbol mapping for CoinGecko API
        coingecko_mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'USDT': 'tether',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'XRP': 'ripple',
            'DOGE': 'dogecoin',
            'TON': 'the-open-network',
            'BONK': 'bonk',
            'FLOKI': 'floki',
            'NOT': 'notcoin',
            'PEPE': 'pepe',
            'BAT': 'basic-attention-token',
            'IMX': 'immutable-x',
            'OPUL': 'opulous',
            'ORAI': 'oraichain-token',
            'PENGU': 'pudgy-penguins',
            'RENDER': 'render-token',
            'RSR': 'reserve-rights-token',
            'WOO': 'woo-network'
        }
        
        try:
            import requests
            
            # Get CoinGecko IDs for the assets
            coingecko_ids = []
            asset_to_id_map = {}
            
            for asset in assets_list:
                if asset in coingecko_mapping:
                    coingecko_id = coingecko_mapping[asset]
                    coingecko_ids.append(coingecko_id)
                    asset_to_id_map[coingecko_id] = asset
            
            if coingecko_ids:
                # Fetch 24h market data from CoinGecko
                ids_str = ','.join(coingecko_ids)
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
                
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    price_data = response.json()
                    
                    for coingecko_id, asset in asset_to_id_map.items():
                        if coingecko_id in price_data:
                            data = price_data[coingecko_id]
                            fallback_24h_data[asset] = {
                                'price_change_percent_24h': data.get('usd_24h_change', 0),
                                'volume_24h': data.get('usd_24h_vol', 0),
                                'current_price': data.get('usd', 0)
                            }
                            logger.info(f"Fetched 24h data for {asset}: {data.get('usd_24h_change', 0):.2f}% change")
                        else:
                            logger.warning(f"No 24h data found for {asset} ({coingecko_id})")
                else:
                    logger.warning(f"CoinGecko 24h API request failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error fetching fallback 24h data: {e}")
        
        return fallback_24h_data

    async def get_market_prices(self) -> Dict:
        """Get market prices for USD and IRR conversion"""
        try:
            markets_response = self.client.get_markets()
            if not markets_response.get('success'):
                return {'USDT_TO_TMN': 0, 'markets': {}}
            
            symbols = markets_response.get('result', {}).get('symbols', {})

            # Helper to safely parse floats from API (handles None, '', '-')
            def safe_float(value, default=0.0):
                try:
                    if value is None:
                        return default
                    if isinstance(value, str) and value.strip() in ('', '-'):
                        return default
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            # Get USDT/TMN rate for USD to IRR conversion
            usdt_tmn_data = symbols.get('USDTTMN', {})
            usdt_to_tmn_rate = safe_float(usdt_tmn_data.get('stats', {}).get('lastPrice', 0))
            
            # Build price mapping for each asset
            prices = {
                'USDT_TO_TMN': usdt_to_tmn_rate,
                'markets': {}
            }
            
            for symbol, market_data in symbols.items():
                stats = market_data.get('stats', {})
                last_price = safe_float(stats.get('lastPrice', 0))

                base_asset = market_data.get('baseAsset')
                quote_asset = market_data.get('quoteAsset')

                # Fallback to parsing from symbol if base/quote not provided
                if not base_asset or not quote_asset:
                    if symbol.endswith('TMN'):
                        base_asset = symbol[:-3]
                        quote_asset = 'TMN'
                    elif symbol.endswith('USDT'):
                        base_asset = symbol[:-4]
                        quote_asset = 'USDT'

                if not base_asset or not quote_asset:
                    continue

                # Initialize entry
                if base_asset not in prices['markets']:
                    prices['markets'][base_asset] = {}

                if quote_asset == 'TMN':
                    # Direct TMN price
                    prices['markets'][base_asset]['tmn_price'] = last_price
                    prices['markets'][base_asset]['usd_price'] = (
                        last_price / usdt_to_tmn_rate if usdt_to_tmn_rate > 0 else 0
                    )
                elif quote_asset == 'USDT':
                    # USDT price, convert to TMN
                    prices['markets'][base_asset]['usd_price'] = last_price
                    prices['markets'][base_asset]['tmn_price'] = last_price * usdt_to_tmn_rate
                else:
                    # Unsupported quote, skip
                    continue

            # Ensure USDT asset itself has a mapping
            if 'USDT' not in prices['markets']:
                prices['markets']['USDT'] = {
                    'usd_price': 1.0,
                    'tmn_price': usdt_to_tmn_rate
                }
            else:
                prices['markets']['USDT'].setdefault('usd_price', 1.0)
                prices['markets']['USDT'].setdefault('tmn_price', usdt_to_tmn_rate)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting market prices: {e}")
            return {'USDT_TO_TMN': 0, 'markets': {}}

    async def get_formatted_balances(self) -> Dict:
        """Get formatted balance data for UI"""
        try:
            balances_response = await self.get_balances()
            account_response = await self.get_account_info()
            market_prices = await self.get_market_prices()

            # Ensure market_prices has expected structure
            if not isinstance(market_prices, dict):
                market_prices = {}
            market_prices.setdefault('USDT_TO_TMN', 0)
            market_prices.setdefault('markets', {})

            # helper
            def safe_float(value, default=0.0):
                try:
                    if value is None:
                        return default
                    if isinstance(value, str) and value.strip() in ('', '-'):
                        return default
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            if not balances_response.get('success'):
                raise HTTPException(status_code=500, detail="Failed to retrieve balances")
            
            # The API returns: {"success": true, "result": {"balances": {...}}}
            result_data = balances_response.get('result', {})
            balances_data = result_data.get('balances', {})
            account_data = account_response.get('result', {}) if account_response.get('success') else {}
            
            # Identify assets with balances that are missing or zero price data
            missing_assets = []
            usdt_to_tmn_rate = market_prices.get('USDT_TO_TMN', 0)
            
            for asset_name, balance_data in balances_data.items():
                if isinstance(balance_data, dict):
                    free = safe_float(balance_data.get('value', 0))
                    locked = safe_float(balance_data.get('locked', 0))
                    total_balance = free + locked
                    if total_balance > 0:
                        price_data = market_prices.get('markets', {}).get(asset_name)
                        usd_p = safe_float(price_data.get('usd_price', 0)) if price_data else 0
                        tmn_p = safe_float(price_data.get('tmn_price', 0)) if price_data else 0
                        if (price_data is None) or (usd_p <= 0 and tmn_p <= 0):
                            missing_assets.append(asset_name)
            
            # Get fallback prices for missing assets
            fallback_prices = {}
            if missing_assets:
                logger.info(f"Fetching fallback prices for {len(missing_assets)} assets: {missing_assets}")
                fallback_prices = await self.get_fallback_prices(missing_assets, usdt_to_tmn_rate)
                # Merge fallback prices into market prices
                market_prices['markets'].update(fallback_prices)
            
            # Process balances
            assets = []
            total_assets_count = 0
            non_zero_count = 0
            total_usd_value = 0
            total_irr_value = 0
            
            for asset_name, balance_data in balances_data.items():
                if isinstance(balance_data, dict):
                    free = safe_float(balance_data.get('value', 0))
                    locked = safe_float(balance_data.get('locked', 0))
                    total = free + locked
                    total_assets_count += 1
                    
                    # Calculate USD and IRR values
                    usd_value = 0.0
                    irr_value = 0.0
                    
                    price_data = market_prices.get('markets', {}).get(asset_name)
                    if total > 0 and price_data:
                        usd_price = safe_float(price_data.get('usd_price', 0))
                        tmn_price = safe_float(price_data.get('tmn_price', 0))
                        usd_value = total * usd_price
                        irr_value = total * tmn_price
                    
                    # Ensure values are proper floats
                    try:
                        usd_value = float(usd_value) if usd_value is not None else 0.0
                        irr_value = float(irr_value) if irr_value is not None else 0.0
                    except (ValueError, TypeError):
                        usd_value = 0.0
                        irr_value = 0.0
                    
                    # Include all assets, but mark which have balance
                    has_balance = total > 0
                    if has_balance:
                        non_zero_count += 1
                    
                    # Always include USD value in total calculation (even for zero balance assets)
                    total_usd_value += usd_value
                    total_irr_value += irr_value
                    
                    assets.append({
                        'asset': balance_data.get('asset', asset_name),
                        'fa_name': balance_data.get('faName', asset_name),
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'usd_value': usd_value,
                        'irr_value': irr_value,
                        'has_balance': has_balance,
                        'icon_url': balance_data.get('asset_svg_icon', ''),
                        'is_fiat': balance_data.get('fiat', False),
                        'is_digital_gold': balance_data.get('is_digital_gold', False)
                    })
            
            # Sort: assets with balance first, then alphabetically
            assets.sort(key=lambda x: (not x['has_balance'], x['asset']))
            
            return {
                'account': {
                    'email': account_data.get('email', 'N/A'),
                    'user_id': account_data.get('id', 'N/A'),
                    'is_verified': account_data.get('is_verified', False),
                    'two_factor_enabled': account_data.get('two_factor_enabled', False)
                },
                'balances': {
                    'assets': assets,
                    'total_assets': total_assets_count,
                    'assets_with_balance': non_zero_count,
                    'total_usd_value': total_usd_value,
                    'total_irr_value': total_irr_value,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing balances: {str(e)}")

    async def save_portfolio_snapshot(self) -> Dict:
        """Save current portfolio data to database"""
        try:
            portfolio_data = await self.get_formatted_balances()
            success = await self.db.save_portfolio_snapshot(portfolio_data)
            
            return {
                'success': success,
                'message': 'Portfolio snapshot saved successfully' if success else 'Failed to save portfolio snapshot',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error saving portfolio snapshot: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_portfolio_history(self, days: int = 30) -> Dict:
        """Get portfolio history from database"""
        try:
            history = await self.db.get_portfolio_history(days)
            stats = await self.db.get_portfolio_stats()
            
            return {
                'success': True,
                'history': history,
                'stats': stats
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error retrieving portfolio history: {str(e)}",
                'history': [],
                'stats': {}
            }
    
    async def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        try:
            stats = await self.db.get_portfolio_stats()
            return {
                'success': True,
                'data': stats
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error retrieving portfolio stats: {str(e)}",
                'data': {}
            }
    
    async def get_coin_profit_comparison(self, days: int = 30) -> Dict:
        """Get profit/loss comparison for individual coins"""
        try:
            coin_data = await self.db.get_coin_profit_comparison(days)
            return {
                'success': True,
                'data': coin_data,
                'total_coins': len(coin_data),
                'days_analyzed': days
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error retrieving coin profit comparison: {str(e)}",
                'data': [],
                'total_coins': 0,
                'days_analyzed': days
            }
    
    async def get_coin_percentage_series(self, days: int = 30) -> Dict:
        """Get per-coin percentage change time series over the last N days."""
        try:
            latest = await self.db.get_latest_snapshot()
            if not latest:
                return {
                    'success': True,
                    'labels': [],
                    'datasets': [],
                    'summary': [],
                    'days': days,
                    'total_coins': 0
                }
            assets = await self.db.get_asset_balances_for_snapshot(latest['date'])
            coins = [a for a in assets if not a.get('is_fiat', False) and float(a.get('usd_value', 0) or 0) > 0]
            # Build common date labels from portfolio history (ascending)
            history = await self.db.get_portfolio_history(days)
            labels = [h['date'] for h in reversed(history)] if history else []
            datasets = []
            summary = []
            for a in coins:
                symbol = a.get('symbol') or a.get('asset_name')
                if not symbol:
                    continue
                asset_history = await self.db.get_asset_history(symbol, days)
                if not asset_history:
                    continue
                asc_hist = list(reversed(asset_history))
                date_to_value = {entry['date']: float(entry['usd_value'] or 0) for entry in asc_hist}
                baseline = None
                for d in labels:
                    v = date_to_value.get(d)
                    if v and v > 0:
                        baseline = v
                        break
                if baseline is None or baseline <= 0:
                    continue
                data = []
                latest_pct = None
                for d in labels:
                    v = date_to_value.get(d)
                    if v is None:
                        data.append(None)
                    else:
                        pct = ((v - baseline) / baseline) * 100.0
                        data.append(pct)
                        latest_pct = pct
                if all(v is None for v in data):
                    continue
                datasets.append({
                    'label': symbol,
                    'data': data
                })
                summary.append({
                    'symbol': symbol,
                    'profit_loss_percentage': float(latest_pct or 0.0)
                })
            return {
                'success': True,
                'labels': labels,
                'datasets': datasets,
                'summary': summary,
                'days': days,
                'total_coins': len(summary)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error retrieving coin percentage series: {str(e)}",
                'labels': [],
                'datasets': [],
                'summary': [],
                'days': days,
                'total_coins': 0
            }

# Initialize wallet service
try:
    wallet_service = WalletService()
except ValueError as e:
    logger.error(f"Configuration Error: {e}")
    logger.error("Please configure your .env with WALLEX_API_KEY and PostgreSQL connection (POSTGRES_DSN or POSTGRES_HOST/PORT/USER/PASSWORD/DB).")
    wallet_service = None

@app.on_event("startup")
async def on_startup():
    """Initialize async resources (DB pool)."""
    if wallet_service:
        try:
            await wallet_service.init()
            logger.info("WalletService initialized successfully")
        except Exception as e:
            logger.error(f"Startup initialization failed: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    """Gracefully close async resources (DB pool)."""
    try:
        if wallet_service and getattr(wallet_service, 'db', None):
            db = wallet_service.db
            pool = getattr(db, 'pool', None)
            if pool is not None:
                await pool.close()
                logger.info("Database pool closed")
    except Exception as e:
        logger.warning(f"Error during shutdown cleanup: {e}")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    if not wallet_service:
        return HTMLResponse(
            content="<h1>Configuration Error</h1><p>Please add your WALLEX_API_KEY to the .env file</p>",
            status_code=401
        )
    
    try:
        data = await wallet_service.get_formatted_balances()
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "data": data
        })
    except HTTPException as e:
        return HTMLResponse(
            content=f"<h1>Error</h1><p>{e.detail}</p>",
            status_code=e.status_code
        )

@app.get("/api/balances")
async def api_balances():
    """API endpoint for balance data"""
    if not wallet_service:
        raise HTTPException(status_code=401, detail="Wallet service not configured")
    
    return await wallet_service.get_formatted_balances()

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    """Portfolio tracking page"""
    if not wallet_service:
        return HTMLResponse(
            content="<h1>Configuration Error</h1><p>Please add your WALLEX_API_KEY to the .env file</p>",
            status_code=401
        )
    
    try:
        # Get portfolio history and stats
        history_result = await wallet_service.get_portfolio_history(30)
        stats_result = await wallet_service.get_portfolio_stats()
        
        return templates.TemplateResponse("portfolio.html", {
            "request": request,
            "history": history_result.get('history', []) if history_result.get('success') else [],
            "stats": stats_result.get('data', {}) if stats_result.get('success') else {}
        })
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Error loading portfolio page: {str(e)}</p>",
            status_code=500
        )

@app.post("/api/portfolio/save")
async def save_portfolio():
    """Save current portfolio snapshot to database"""
    if not wallet_service:
        raise HTTPException(status_code=401, detail="Wallet service not configured")
    
    result = await wallet_service.save_portfolio_snapshot()
    return JSONResponse(content=result)

@app.get("/api/portfolio/history")
async def get_portfolio_history(days: int = 30):
    """Get portfolio history from database"""
    if not wallet_service:
        raise HTTPException(status_code=401, detail="Wallet service not configured")
    
    result = await wallet_service.get_portfolio_history(days)
    return JSONResponse(content=result)

@app.get("/api/portfolio/stats")
async def get_portfolio_stats():
    """Get portfolio statistics"""
    if not wallet_service:
        raise HTTPException(status_code=401, detail="Wallet service not configured")
    
    result = await wallet_service.get_portfolio_stats()
    return JSONResponse(content=result)

@app.get("/api/portfolio/coins")
async def get_coin_profit_comparison(days: int = 30):
    """Get individual coin profit/loss comparison"""
    if not wallet_service:
        raise HTTPException(status_code=401, detail="Wallet service not configured")
    
    result = await wallet_service.get_coin_profit_comparison(days)
    return JSONResponse(content=result)

@app.get("/api/portfolio/coins/series")
async def get_coin_percentage_series(days: int = 30):
    """Get per-coin percentage change time series"""
    if not wallet_service:
        raise HTTPException(status_code=401, detail="Wallet service not configured")
    result = await wallet_service.get_coin_percentage_series(days)
    return JSONResponse(content=result)

@app.get("/live-prices", response_class=HTMLResponse)
async def live_prices_page(request: Request):
    """Live price monitoring page"""
    if not wallet_service:
        return HTMLResponse(
            content="<h1>Configuration Error</h1><p>Please add your WALLEX_API_KEY to the .env file</p>",
            status_code=500
        )
    
    return templates.TemplateResponse("live_prices.html", {
        "request": request
    })

@app.get("/api/live-prices/markets")
async def get_live_markets():
    """Get all market data with live prices"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    try:
        # Get market data from Wallex
        markets_response = wallet_service.client.get_markets()
        
        if not markets_response.get('success'):
            return JSONResponse(content={
                "success": False,
                "error": "Failed to fetch market data"
            })
        
        symbols = markets_response.get('result', {}).get('symbols', {})
        
        # Process market data
        markets_data = []
        usdt_to_tmn_rate = 0
        
        # Helper function to safely convert to float
        def safe_float(value, default=0):
            try:
                if value is None or value == '' or value == '-':
                    return default
                return float(value)
            except (ValueError, TypeError):
                return default
        
        # Get USDT to TMN rate first
        if 'USDTTMN' in symbols:
            usdt_to_tmn_rate = safe_float(symbols['USDTTMN'].get('stats', {}).get('lastPrice', 0))
        
        # Collect all base assets for fallback 24h data
        base_assets = set()
        for symbol, market_data in symbols.items():
            base_asset = market_data.get('baseAsset', '')
            if base_asset:
                base_assets.add(base_asset)
        
        # Get fallback 24h data from CoinGecko
        logger.info(f"Fetching 24h data for {len(base_assets)} assets from CoinGecko...")
        fallback_24h_data = await wallet_service.get_fallback_24h_data(list(base_assets))
        
        for symbol, market_data in symbols.items():
            stats = market_data.get('stats', {})
            
            # Extract asset information
            base_asset = market_data.get('baseAsset', '')
            quote_asset = market_data.get('quoteAsset', '')
            base_asset_fa = market_data.get('faBaseAsset', base_asset)
            quote_asset_fa = market_data.get('faQuoteAsset', quote_asset)
            
            # Price information
            last_price = safe_float(stats.get('lastPrice', 0))
            price_change = safe_float(stats.get('priceChange', 0))
            price_change_percent = safe_float(stats.get('priceChangePercent', 0))
            
            # Volume information
            volume = safe_float(stats.get('volume', 0))
            quote_volume = safe_float(stats.get('quoteVolume', 0))
            
            # High/Low prices
            high_price = safe_float(stats.get('highPrice', 0))
            low_price = safe_float(stats.get('lowPrice', 0))
            
            # Use fallback 24h data if Wallex data is missing/zero
            if base_asset in fallback_24h_data and (price_change_percent == 0 or volume == 0):
                fallback_data = fallback_24h_data[base_asset]
                if price_change_percent == 0:
                    price_change_percent = safe_float(fallback_data.get('price_change_percent_24h', 0))
                if volume == 0:
                    # Convert USD volume to base asset volume (approximate)
                    usd_volume = safe_float(fallback_data.get('volume_24h', 0))
                    current_price_usd = safe_float(fallback_data.get('current_price', 0))
                    if current_price_usd > 0:
                        volume = usd_volume / current_price_usd
                        quote_volume = usd_volume
                
                # Estimate high/low prices if missing (using current price ± change)
                if high_price == 0 or low_price == 0:
                    current_price_usd = safe_float(fallback_data.get('current_price', 0))
                    change_percent = safe_float(fallback_data.get('price_change_percent_24h', 0))
                    if current_price_usd > 0 and change_percent != 0:
                        # Convert USD price to local currency
                        if quote_asset == 'USDT':
                            current_price_local = current_price_usd
                        elif quote_asset == 'TMN' and usdt_to_tmn_rate > 0:
                            current_price_local = current_price_usd * usdt_to_tmn_rate
                        else:
                            current_price_local = last_price
                        
                        # Estimate high/low (this is approximate)
                        if high_price == 0:
                            high_price = current_price_local * (1 + abs(change_percent) / 100)
                        if low_price == 0:
                            low_price = current_price_local * (1 - abs(change_percent) / 100)
            
            # Calculate USD price if possible
            usd_price = 0
            if quote_asset == 'USDT':
                usd_price = last_price
            elif quote_asset == 'TMN' and usdt_to_tmn_rate > 0:
                usd_price = last_price / usdt_to_tmn_rate
            
            market_info = {
                "symbol": symbol,
                "base_asset": base_asset,
                "quote_asset": quote_asset,
                "base_asset_fa": base_asset_fa,
                "quote_asset_fa": quote_asset_fa,
                "last_price": last_price,
                "usd_price": round(usd_price, 8) if usd_price > 0 else None,
                "price_change": price_change,
                "price_change_percent": round(price_change_percent, 2),
                "volume_24h": volume,
                "quote_volume_24h": quote_volume,
                "high_24h": high_price,
                "low_24h": low_price,
                "bid_price": safe_float(stats.get('bidPrice', 0)),
                "ask_price": safe_float(stats.get('askPrice', 0)),
                "open_price": safe_float(stats.get('openPrice', 0)),
                "prev_close_price": safe_float(stats.get('prevClosePrice', 0)),
                "weighted_avg_price": safe_float(stats.get('weightedAvgPrice', 0)),
                "data_source": "wallex_coingecko" if base_asset in fallback_24h_data else "wallex"
            }
            
            markets_data.append(market_info)
        
        # Sort by volume (descending)
        markets_data.sort(key=lambda x: x['quote_volume_24h'], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "data": markets_data,
            "total_markets": len(markets_data),
            "usdt_to_tmn_rate": usdt_to_tmn_rate,
            "fallback_data_used": len(fallback_24h_data),
            "last_updated": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching live market data: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })

@app.get("/api/live-prices/market/{symbol}")
async def get_market_details(symbol: str):
    """Get detailed information for a specific market"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    try:
        # Get specific market stats
        market_stats = wallet_service.client.get_market_stats(symbol)
        
        if not market_stats.get('success'):
            return JSONResponse(content={
                "success": False,
                "error": f"Failed to fetch data for {symbol}"
            })
        
        return JSONResponse(content={
            "success": True,
            "data": market_stats.get('result', {}),
            "symbol": symbol,
            "last_updated": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching market details for {symbol}: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        })

@app.get("/api/refresh")
async def api_refresh():
    """API endpoint to refresh balance data"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    return await wallet_service.get_formatted_balances()

@app.get("/api/debug/balance-calculation")
async def debug_balance_calculation():
    """Debug endpoint to show detailed balance calculation breakdown"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    try:
        # Get raw data
        balances_response = await wallet_service.get_balances()
        market_prices = await wallet_service.get_market_prices()
        
        if not balances_response.get('success'):
            return {"error": "Failed to retrieve balances"}
        
        result_data = balances_response.get('result', {})
        balances_data = result_data.get('balances', {})
        
        # helper
        def safe_float(value, default=0.0):
            try:
                if value is None:
                    return default
                if isinstance(value, str) and value.strip() in ('', '-'):
                    return default
                return float(value)
            except (ValueError, TypeError):
                return default
        
        # Identify assets with balances that are missing or zero price data
        missing_assets = []
        usdt_to_tmn_rate = market_prices.get('USDT_TO_TMN', 0)
        
        for asset_name, balance_data in balances_data.items():
            if isinstance(balance_data, dict):
                free = safe_float(balance_data.get('value', 0))
                locked = safe_float(balance_data.get('locked', 0))
                total_balance = free + locked
                if total_balance > 0:
                    price_data = market_prices.get('markets', {}).get(asset_name)
                    usd_p = safe_float(price_data.get('usd_price', 0)) if price_data else 0
                    tmn_p = safe_float(price_data.get('tmn_price', 0)) if price_data else 0
                    if (price_data is None) or (usd_p <= 0 and tmn_p <= 0):
                        missing_assets.append(asset_name)
        
        # Get fallback prices for missing assets
        if missing_assets:
            logger.debug(f"Debug: Fetching fallback prices for {len(missing_assets)} assets: {missing_assets}")
            fallback_prices = await wallet_service.get_fallback_prices(missing_assets, usdt_to_tmn_rate)
            # Merge fallback prices into market prices
            market_prices['markets'].update(fallback_prices)
        
        debug_info = {
            "total_usd_calculated": 0,
            "usdt_to_tmn_rate": usdt_to_tmn_rate,
            "assets_with_balance": [],
            "fallback_assets_found": len(missing_assets),
            "calculation_summary": {}
        }
        
        total_usd = 0
        
        # Only show assets with balance > 0
        for asset_name, balance_data in balances_data.items():
            if isinstance(balance_data, dict):
                free = safe_float(balance_data.get('value', 0))
                locked = safe_float(balance_data.get('locked', 0))
                total_balance = free + locked
                
                if total_balance > 0:  # Only include assets with balance
                    asset_debug = {
                        "asset": asset_name,
                        "free_balance": free,
                        "locked_balance": locked,
                        "total_balance": total_balance,
                        "usd_value": 0,
                        "price_data_available": asset_name in market_prices.get('markets', {}),
                        "usd_price": 0,
                        "price_source": "wallex"
                    }
                    
                    if asset_name in market_prices.get('markets', {}):
                        price_data = market_prices['markets'][asset_name]
                        usd_price = safe_float(price_data.get('usd_price', 0))
                        usd_value = total_balance * usd_price
                        
                        # Determine price source
                        price_source = "fallback" if asset_name in missing_assets else "wallex"
                        
                        asset_debug.update({
                            "usd_value": round(usd_value, 6),
                            "usd_price": round(usd_price, 6),
                            "price_source": price_source
                        })
                        
                        total_usd += usd_value
                    
                    debug_info["assets_with_balance"].append(asset_debug)
        
        debug_info["total_usd_calculated"] = round(total_usd, 2)
        debug_info["calculation_summary"] = {
            "assets_count": len(debug_info["assets_with_balance"]),
            "total_usd_value": round(total_usd, 2),
            "fallback_assets_used": len(missing_assets)
        }
        
        return debug_info
        
    except Exception as e:
        return {"error": f"Debug calculation failed: {str(e)}"}

@app.get("/api/debug/simple")
async def debug_simple():
    """Simple debug endpoint"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    try:
        account_info = await wallet_service.get_account_info()
        balances = await wallet_service.get_balances()
        return {
            'success': True,
            'account_email': account_info.get('result', {}).get('email', 'N/A'),
            'total_assets': len(balances.get('result', {}).get('balances', {})),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/api/export/non-zero-currencies")
async def export_non_zero_currencies():
    """Export non-zero currencies as JSON in USD"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not initialized")
    
    try:
        # Get formatted balances - this returns the data directly, not wrapped in success/data
        balances_data = await wallet_service.get_formatted_balances()
        
        # Filter non-zero currencies and format for export
        non_zero_currencies = []
        balances = balances_data.get('balances', {}).get('assets', [])
        
        for balance in balances:
            usd_value = balance.get('usd_value', 0)
            if usd_value > 0:  # Only include currencies with non-zero USD value
                currency_data = {
                    'symbol': balance.get('asset', ''),
                    'name': balance.get('fa_name', balance.get('asset', '')),
                    'amount': balance.get('total', 0),
                    'usd_value': usd_value,
                    'is_fiat': balance.get('is_fiat', False),
                    'is_digital_gold': balance.get('is_digital_gold', False)
                }
                non_zero_currencies.append(currency_data)
        
        # Sort by USD value (highest first)
        non_zero_currencies.sort(key=lambda x: x['usd_value'], reverse=True)
        
        # Create export data with metadata
        # Use the same total as displayed on dashboard
        dashboard_total = balances_data.get('balances', {}).get('total_usd_value', 0)
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_currencies': len(non_zero_currencies),
            'total_usd_value': dashboard_total,  # Use dashboard's total calculation
            'currencies': non_zero_currencies
        }
        
        return JSONResponse(content=export_data)
        
    except Exception as e:
        logger.error(f"Error exporting non-zero currencies: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/health")
async def health():
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    try:
        db_health = await wallet_service.db.health()
        env_keys = {
            'WALLEX_API_KEY': bool(os.getenv('WALLEX_API_KEY')),
            'POSTGRES_DSN': bool(os.getenv('POSTGRES_DSN')),
            'POSTGRES_HOST': bool(os.getenv('POSTGRES_HOST')),
            'POSTGRES_PORT': bool(os.getenv('POSTGRES_PORT')),
            'POSTGRES_USER': bool(os.getenv('POSTGRES_USER')),
            'POSTGRES_PASSWORD': bool(os.getenv('POSTGRES_PASSWORD')),
            'POSTGRES_DB': bool(os.getenv('POSTGRES_DB')),
        }
        return {
            'success': True,
            'db': db_health,
            'env_keys_present': env_keys,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/api/debug/portfolio-snapshots")
async def debug_portfolio_snapshots():
    """Debug endpoint to check portfolio snapshot data"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    try:
        # Get portfolio history and stats
        history_result = await wallet_service.get_portfolio_history(30)
        
        # Analyze the data
        snapshots_with_assets = 0
        snapshots_without_assets = 0
        total_snapshots = len(history_result.get('history', []))
        
        for snapshot in history_result.get('history', []):
            if snapshot.get('assets_with_balance', 0) > 0:
                snapshots_with_assets += 1
            else:
                snapshots_without_assets += 1
        
        # Check if coin performance can work
        coin_data = await wallet_service.get_coin_profit_comparison(30)
        has_meaningful_data = any(
            coin.get('profit_loss_percentage', 0) != 0 
            for coin in coin_data.get('data', [])
        )
        
        return {
            'success': True,
            'analysis': {
                'total_snapshots': total_snapshots,
                'snapshots_with_asset_data': snapshots_with_assets,
                'snapshots_without_asset_data': snapshots_without_assets,
                'has_meaningful_performance_data': has_meaningful_data,
                'issue_explanation': (
                    'Individual Coin Performance appears empty because most historical snapshots '
                    'do not contain individual asset balance data. Only portfolio totals were saved '
                    'for historical dates. To see coin performance, you need to save snapshots '
                    'regularly that include individual asset data.'
                ) if snapshots_without_assets > 0 else 'Portfolio tracking is working correctly.',
                'recommendation': (
                    'Save new portfolio snapshots daily using the "Save Today\'s Snapshot" button '
                    'or enable auto-save to build historical asset-level data for performance tracking.'
                ) if snapshots_without_assets > 0 else 'Continue regular snapshot saving.'
            },
            'recent_snapshots': history_result.get('history', [])[:5],  # Show last 5
            'stats': history_result.get('stats', {}),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/database", response_class=HTMLResponse)
async def database_view(request: Request):
    """Database view page"""
    return templates.TemplateResponse("database.html", {"request": request})

@app.get("/api/database/snapshots")
async def get_database_snapshots():
    """Get all portfolio snapshots for database view"""
    try:
        snapshots = await wallet_service.db.get_portfolio_history(days=365)  # Get all snapshots
        
        return {
            'success': True,
            'snapshots': snapshots,
            'total_count': len(snapshots)
        }
    except Exception as e:
        logger.error(f"Error fetching database snapshots: {e}")
        return {
            'success': False,
            'error': str(e),
            'snapshots': []
        }

@app.get("/api/database/assets")
async def get_database_assets():
    """Get asset balances from latest snapshot for database view"""
    try:
        # Get the latest snapshot
        latest_snapshot = await wallet_service.db.get_latest_snapshot()
        
        if not latest_snapshot:
            return {
                'success': False,
                'error': 'No snapshots found',
                'assets': []
            }
        
        # Get asset balances for the latest snapshot
        assets = await wallet_service.db.get_asset_balances_for_snapshot(latest_snapshot['date'])
        
        return {
            'success': True,
            'assets': assets,
            'snapshot_date': latest_snapshot['date'],
            'total_count': len(assets)
        }
    except Exception as e:
        logger.error(f"Error fetching database assets: {e}")
        return {
            'success': False,
            'error': str(e),
            'assets': []
        }

@app.put("/api/database/snapshot/{snapshot_id}")
async def update_snapshot(snapshot_id: str, request: Request):
    """Update a portfolio snapshot record"""
    try:
        data = await request.json()
        
        # Validate required fields
        allowed_fields = ['total_usd_value', 'total_irr_value', 'total_assets', 'assets_with_balance', 'account_email']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return {
                'success': False,
                'error': 'No valid fields provided for update'
            }
        
        # Update the snapshot in database
        success = await wallet_service.db.update_portfolio_snapshot(int(snapshot_id), update_data)
        
        if success:
            return {
                'success': True,
                'message': 'Snapshot updated successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to update snapshot'
            }
            
    except Exception as e:
        logger.error(f"Error updating snapshot {snapshot_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.put("/api/database/asset/{asset_id}")
async def update_asset(asset_id: str, request: Request):
    """Update an asset balance record"""
    try:
        data = await request.json()
        logger.info(f"Received data for asset {asset_id}: {data}")
        
        # Validate required fields
        allowed_fields = ['asset_name', 'asset_fa_name', 'free_amount', 'total_amount', 'usd_value', 'irr_value', 'has_balance', 'is_fiat', 'is_digital_gold']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        logger.info(f"Raw data received: {data}")
        logger.info(f"Allowed fields: {allowed_fields}")
        logger.info(f"Filtered update_data: {update_data}")
        logger.info(f"Data keys: {list(data.keys())}")
        logger.info(f"Matching keys: {[k for k in data.keys() if k in allowed_fields]}")
        
        if not update_data:
            return {
                'success': False,
                'error': 'No valid fields provided for update'
            }
        
        # Convert string values to appropriate types
        for field in ['free_amount', 'total_amount', 'usd_value', 'irr_value']:
            if field in update_data:
                try:
                    update_data[field] = float(update_data[field])
                except (ValueError, TypeError):
                    return {
                        'success': False,
                        'error': f'Invalid value for {field}: must be a number'
                    }
        
        for field in ['has_balance', 'is_fiat', 'is_digital_gold']:
            if field in update_data:
                update_data[field] = bool(update_data[field])
        
        # Update the asset in database
        success = await wallet_service.db.update_asset_balance(int(asset_id), update_data)
        
        if success:
            return {
                'success': True,
                'message': 'Asset updated successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to update asset'
            }
            
    except Exception as e:
        logger.error(f"Error updating asset {asset_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.delete("/api/database/snapshot/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    """Delete a portfolio snapshot record"""
    try:
        success = await wallet_service.db.delete_portfolio_snapshot(int(snapshot_id))
        
        if success:
            return {
                'success': True,
                'message': 'Snapshot deleted successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to delete snapshot or snapshot not found'
            }
            
    except Exception as e:
        logger.error(f"Error deleting snapshot {snapshot_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.delete("/api/database/asset/{asset_id}")
async def delete_asset(asset_id: str):
    """Delete an asset balance record"""
    try:
        success = await wallet_service.db.delete_asset_balance(int(asset_id))
        
        if success:
            return {
                'success': True,
                'message': 'Asset deleted successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to delete asset or asset not found'
            }
            
    except Exception as e:
        logger.error(f"Error deleting asset {asset_id}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.get("/api/reversals")
async def list_reversals(snapshot_id: Optional[int] = None, asset_name: Optional[str] = None, only_active: bool = True):
    try:
        # Default to latest snapshot if not provided
        if snapshot_id is None:
            latest = await wallet_service.db.get_latest_snapshot()
            snapshot_id = latest.get('id') if latest else None
        reversals = await wallet_service.db.list_transaction_reversals(snapshot_id=snapshot_id, asset_name=asset_name, only_active=only_active)
        return {"success": True, "data": reversals}
    except Exception as e:
        logger.error(f"Error listing reversals: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/reversals")
async def create_reversal(payload: Dict = Body(...)):
    try:
        # Validation
        reversal_type = payload.get('reversal_type')
        asset_name = payload.get('asset_name')
        amount_usd = float(payload.get('amount_usd', 0))
        confirm = bool(payload.get('confirm', False))
        reason = payload.get('reason')
        created_by = payload.get('created_by')
        snapshot_id = payload.get('snapshot_id')
        asset_id = payload.get('asset_id')

        if not confirm:
            return {"success": False, "error": "Confirmation required to create reversal."}
        if reversal_type not in ("buy", "sell"):
            return {"success": False, "error": "Invalid reversal_type. Must be 'buy' or 'sell'."}
        if not asset_name or amount_usd <= 0:
            return {"success": False, "error": "asset_name required and amount_usd must be > 0."}

        # Default snapshot_id and created_by
        if snapshot_id is None or created_by is None:
            latest = await wallet_service.db.get_latest_snapshot()
            if latest:
                snapshot_id = snapshot_id or latest.get('id')
                created_by = created_by or latest.get('account_email') or "system"
            else:
                created_by = created_by or "system"

        reversal = await wallet_service.db.create_transaction_reversal(
            snapshot_id=snapshot_id,
            asset_id=asset_id,
            asset_name=asset_name,
            reversal_type=reversal_type,
            amount_usd=amount_usd,
            reason=reason,
            created_by=created_by
        )
        return {"success": True, "data": reversal}
    except Exception as e:
        logger.error(f"Error creating reversal: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/reversals/{reversal_id}/undo")
async def undo_reversal(reversal_id: int, payload: Dict = Body(...)):
    try:
        confirm = bool(payload.get('confirm', False))
        if not confirm:
            return {"success": False, "error": "Confirmation required to undo reversal."}
        undone = await wallet_service.db.undo_transaction_reversal(reversal_id)
        if not undone:
            return {"success": False, "error": "Reversal not found or already inactive."}
        return {"success": True}
    except Exception as e:
        logger.error(f"Error undoing reversal {reversal_id}: {e}")
        return {"success": False, "error": str(e)}

        

if __name__ == "__main__":
    logger.info("Starting Wallex Wallet Dashboard...")
    logger.info("Dashboard will be available at: http://localhost:8000")
    logger.info("API endpoints:")
    logger.info("   - GET /api/balances - Get balance data")
    logger.info("   - GET /api/refresh - Refresh balance data")

    uvicorn.run(
        "wallet_ui:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )