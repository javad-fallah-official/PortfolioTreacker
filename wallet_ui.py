#!/usr/bin/env python3
"""
FastAPI Web UI for Wallex Wallet Balance Display
"""

import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uvicorn

from wallex import WallexClient
from wallex.exceptions import WallexError, WallexAuthenticationError

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
        self.client = WallexClient(api_key=self.api_key)
    
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

@app.get("/api/refresh")
async def api_refresh():
    """API endpoint to refresh balance data"""
    if not wallet_service:
        raise HTTPException(status_code=500, detail="Wallet service not configured")
    
    return await wallet_service.get_formatted_balances()

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