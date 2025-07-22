#!/usr/bin/env python3
"""
FastAPI Web UI for Wallex Wallet Balance Display
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, List
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from wallex import WallexClient
from database import PortfolioDatabase

# Load environment variables
load_dotenv()

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
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            return self.client.get_account_info()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")
    
    async def get_balances(self) -> Dict:
        """Get wallet balances"""
        try:
            return self.client.get_balances()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get balances: {str(e)}")
    
    async def get_fallback_prices(self, missing_assets: list, usdt_to_tmn_rate: float) -> Dict:
        """Get prices from CoinGecko for assets not available on Wallex"""
        fallback_prices = {}
        
        # Asset symbol mapping for CoinGecko API
        coingecko_mapping = {
            'BAT': 'basic-attention-token',
            'IMX': 'immutable-x',
            'OPUL': 'opulous',
            'ORAI': 'oraichain-token',
            'PENGU': 'pudgy-penguins',
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
                            print(f"✅ Fetched fallback price for {asset}: ${usd_price}")
                        else:
                            print(f"⚠️ No price data found for {asset} ({coingecko_id})")
                else:
                    print(f"⚠️ CoinGecko API request failed: {response.status_code}")
            
        except Exception as e:
            print(f"⚠️ Error fetching fallback prices: {e}")
        
        return fallback_prices

    async def get_market_prices(self) -> Dict:
        """Get market prices for USD and IRR conversion"""
        try:
            markets_response = self.client.get_markets()
            if not markets_response.get('success'):
                return {}
            
            symbols = markets_response.get('result', {}).get('symbols', {})
            
            # Get USDT/TMN rate for USD to IRR conversion
            usdt_tmn_data = symbols.get('USDTTMN', {})
            usdt_to_tmn_rate = float(usdt_tmn_data.get('stats', {}).get('lastPrice', 0))
            
            # Build price mapping for each asset
            prices = {
                'USDT_TO_TMN': usdt_to_tmn_rate,
                'markets': {}
            }
            
            for symbol, market_data in symbols.items():
                stats = market_data.get('stats', {})
                last_price = float(stats.get('lastPrice', 0))
                
                if symbol.endswith('TMN'):
                    # Direct TMN price
                    asset = symbol.replace('TMN', '')
                    prices['markets'][asset] = {
                        'tmn_price': last_price,
                        'usd_price': last_price / usdt_to_tmn_rate if usdt_to_tmn_rate > 0 else 0
                    }
                elif symbol.endswith('USDT'):
                    # USDT price, convert to TMN
                    asset = symbol.replace('USDT', '')
                    if asset not in prices['markets']:
                        prices['markets'][asset] = {}
                    prices['markets'][asset]['usd_price'] = last_price
                    prices['markets'][asset]['tmn_price'] = last_price * usdt_to_tmn_rate
            
            return prices
            
        except Exception as e:
            print(f"Error getting market prices: {e}")
            return {}

    async def get_formatted_balances(self) -> Dict:
        """Get formatted balance data for UI"""
        try:
            balances_response = await self.get_balances()
            account_response = await self.get_account_info()
            market_prices = await self.get_market_prices()
            
            if not balances_response.get('success'):
                raise HTTPException(status_code=500, detail="Failed to retrieve balances")
            
            # The API returns: {"success": true, "result": {"balances": {...}}}
            result_data = balances_response.get('result', {})
            balances_data = result_data.get('balances', {})
            account_data = account_response.get('result', {}) if account_response.get('success') else {}
            
            # Identify assets with balances that are missing price data
            missing_assets = []
            usdt_to_tmn_rate = market_prices.get('USDT_TO_TMN', 0)
            
            for asset_name, balance_data in balances_data.items():
                if isinstance(balance_data, dict):
                    free = float(balance_data.get('value', 0))
                    if free > 0 and asset_name not in market_prices.get('markets', {}):
                        missing_assets.append(asset_name)
            
            # Get fallback prices for missing assets
            fallback_prices = {}
            if missing_assets:
                print(f"🔍 Fetching fallback prices for {len(missing_assets)} assets: {missing_assets}")
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
                    free = float(balance_data.get('value', 0))
                    total = free  # We're not showing locked anymore
                    total_assets_count += 1
                    
                    # Calculate USD and IRR values
                    usd_value = 0.0
                    irr_value = 0.0
                    
                    if total > 0 and asset_name in market_prices.get('markets', {}):
                        price_data = market_prices['markets'][asset_name]
                        usd_price = float(price_data.get('usd_price', 0))
                        tmn_price = float(price_data.get('tmn_price', 0))
                        usd_value = total * usd_price
                        irr_value = total * tmn_price
                    
                    # Ensure values are proper floats and handle any potential None values
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
                        total_usd_value += usd_value
                        total_irr_value += irr_value
                    
                    assets.append({
                        'asset': balance_data.get('asset', asset_name),
                        'fa_name': balance_data.get('faName', asset_name),
                        'free': free,
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
            success = self.db.save_portfolio_snapshot(portfolio_data)
            
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
            history = self.db.get_portfolio_history(days)
            stats = self.db.get_portfolio_stats()
            
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
            stats = self.db.get_portfolio_stats()
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
            coin_data = self.db.get_coin_profit_comparison(days)
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

# Initialize wallet service
try:
    wallet_service = WalletService()
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    print("Please add your WALLEX_API_KEY to the .env file")
    wallet_service = None

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    if not wallet_service:
        return HTMLResponse(
            content="<h1>Configuration Error</h1><p>Please add your WALLEX_API_KEY to the .env file</p>",
            status_code=500
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
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    return await wallet_service.get_formatted_balances()

@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    """Portfolio tracking page"""
    if not wallet_service:
        return HTMLResponse(
            content="<h1>Configuration Error</h1><p>Please add your WALLEX_API_KEY to the .env file</p>",
            status_code=500
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
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    result = await wallet_service.save_portfolio_snapshot()
    return JSONResponse(content=result)

@app.get("/api/portfolio/history")
async def get_portfolio_history(days: int = 30):
    """Get portfolio history from database"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    result = await wallet_service.get_portfolio_history(days)
    return JSONResponse(content=result)

@app.get("/api/portfolio/stats")
async def get_portfolio_stats():
    """Get portfolio statistics"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    result = await wallet_service.get_portfolio_stats()
    return JSONResponse(content=result)

@app.get("/api/portfolio/coins")
async def get_coin_profit_comparison(days: int = 30):
    """Get individual coin profit/loss comparison"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    result = await wallet_service.get_coin_profit_comparison(days)
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
        
        # Get USDT to TMN rate first
        if 'USDTTMN' in symbols:
            usdt_to_tmn_rate = float(symbols['USDTTMN'].get('stats', {}).get('lastPrice', 0))
        
        for symbol, market_data in symbols.items():
            stats = market_data.get('stats', {})
            
            # Extract asset information
            base_asset = market_data.get('baseAsset', '')
            quote_asset = market_data.get('quoteAsset', '')
            base_asset_fa = market_data.get('faBaseAsset', base_asset)
            quote_asset_fa = market_data.get('faQuoteAsset', quote_asset)
            
            # Price information
            last_price = float(stats.get('lastPrice', 0))
            price_change = float(stats.get('priceChange', 0))
            price_change_percent = float(stats.get('priceChangePercent', 0))
            
            # Volume information
            volume = float(stats.get('volume', 0))
            quote_volume = float(stats.get('quoteVolume', 0))
            
            # High/Low prices
            high_price = float(stats.get('highPrice', 0))
            low_price = float(stats.get('lowPrice', 0))
            
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
                "bid_price": float(stats.get('bidPrice', 0)),
                "ask_price": float(stats.get('askPrice', 0)),
                "open_price": float(stats.get('openPrice', 0)),
                "prev_close_price": float(stats.get('prevClosePrice', 0)),
                "weighted_avg_price": float(stats.get('weightedAvgPrice', 0))
            }
            
            markets_data.append(market_info)
        
        # Sort by volume (descending)
        markets_data.sort(key=lambda x: x['quote_volume_24h'], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "data": markets_data,
            "total_markets": len(markets_data),
            "usdt_to_tmn_rate": usdt_to_tmn_rate,
            "last_updated": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error fetching live market data: {e}")
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
        print(f"Error fetching market details for {symbol}: {e}")
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
        
        # Identify assets with balances that are missing price data
        missing_assets = []
        usdt_to_tmn_rate = market_prices.get('USDT_TO_TMN', 0)
        
        for asset_name, balance_data in balances_data.items():
            if isinstance(balance_data, dict):
                free = float(balance_data.get('value', 0))
                if free > 0 and asset_name not in market_prices.get('markets', {}):
                    missing_assets.append(asset_name)
        
        # Get fallback prices for missing assets
        if missing_assets:
            print(f"🔍 Debug: Fetching fallback prices for {len(missing_assets)} assets: {missing_assets}")
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
                free = float(balance_data.get('value', 0))
                
                if free > 0:  # Only include assets with balance
                    asset_debug = {
                        "asset": asset_name,
                        "balance": free,
                        "usd_value": 0,
                        "price_data_available": asset_name in market_prices.get('markets', {}),
                        "usd_price": 0,
                        "price_source": "wallex"
                    }
                    
                    if asset_name in market_prices.get('markets', {}):
                        price_data = market_prices['markets'][asset_name]
                        usd_price = float(price_data.get('usd_price', 0))
                        usd_value = free * usd_price
                        
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
            "expected_total": 535.02,
            "actual_total": round(total_usd, 2),
            "difference": round(535.02 - total_usd, 2)
        }
        
        return debug_info
        
    except Exception as e:
        return {"error": f"Debug calculation failed: {str(e)}"}

@app.get("/api/debug/simple")
async def debug_simple():
    """Simple debug endpoint showing just the total"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    try:
        data = await wallet_service.get_formatted_balances()
        return {
            "total_usd": data['balances']['total_usd_value'],
            "total_irr": data['balances']['total_irr_value'],
            "assets_with_balance": data['balances']['assets_with_balance'],
            "last_updated": data['balances']['last_updated']
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting Wallex Wallet Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8000")
    print("🔄 API endpoints:")
    print("   - GET /api/balances - Get balance data")
    print("   - GET /api/refresh - Refresh balance data")
    
    uvicorn.run(
        "wallet_ui:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )