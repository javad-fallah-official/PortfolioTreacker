#!/usr/bin/env python3
"""
Comprehensive Wallex account test script
"""

import os
import json
from dotenv import load_dotenv
from wallex import WallexClient
from wallex.exceptions import WallexError, WallexAuthenticationError

def main():
    """Main function to test various account endpoints"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv('WALLEX_API_KEY')
    
    if not api_key:
        print("❌ Error: WALLEX_API_KEY not found in .env file")
        return
    
    print("🔑 API Key loaded successfully")
    
    try:
        # Initialize Wallex client
        client = WallexClient(api_key=api_key)
        
        print("\n" + "="*60)
        print("🏦 WALLEX ACCOUNT SUMMARY")
        print("="*60)
        
        # Test 1: Account Information
        print("\n👤 Account Information:")
        print("-" * 30)
        try:
            account_info = client.get_account_info()
            if account_info.get('success'):
                result = account_info.get('result', {})
                print(f"📧 Email: {result.get('email', 'N/A')}")
                print(f"📱 Mobile: {result.get('mobile', 'N/A')}")
                print(f"🆔 User ID: {result.get('id', 'N/A')}")
                print(f"✅ Verified: {result.get('is_verified', False)}")
                print(f"🔐 2FA Enabled: {result.get('two_factor_enabled', False)}")
            else:
                print("⚠️  Could not retrieve account info")
        except Exception as e:
            print(f"❌ Error getting account info: {e}")
        
        # Test 2: Balance Summary
        print("\n💰 Balance Summary:")
        print("-" * 30)
        try:
            balances = client.get_balances()
            if balances.get('success') and 'result' in balances:
                total_assets = 0
                non_zero_count = 0
                
                for asset_name, balance_data in balances['result'].items():
                    if isinstance(balance_data, dict):
                        free = float(balance_data.get('value', 0))
                        locked = float(balance_data.get('locked', 0))
                        total = free + locked
                        total_assets += 1
                        
                        if total > 0:
                            non_zero_count += 1
                            fa_name = balance_data.get('faName', asset_name)
                            print(f"💎 {asset_name:>8}: {total:>15.8f} ({fa_name})")
                
                print(f"\n📊 Total supported assets: {total_assets}")
                print(f"💰 Assets with balance: {non_zero_count}")
                
                if non_zero_count == 0:
                    print("💸 All balances are currently zero")
                    
        except Exception as e:
            print(f"❌ Error getting balances: {e}")
        
        # Test 3: Recent Orders (if any)
        print("\n📋 Recent Orders:")
        print("-" * 30)
        try:
            orders = client.get_orders(limit=5)
            if orders.get('success') and 'result' in orders:
                order_list = orders['result']
                if isinstance(order_list, list) and order_list:
                    print(f"📈 Found {len(order_list)} recent orders:")
                    for order in order_list[:3]:  # Show first 3
                        symbol = order.get('symbol', 'N/A')
                        side = order.get('side', 'N/A')
                        status = order.get('status', 'N/A')
                        print(f"   🔸 {symbol} - {side} - {status}")
                else:
                    print("📭 No recent orders found")
            else:
                print("⚠️  Could not retrieve orders")
        except Exception as e:
            print(f"❌ Error getting orders: {e}")
        
        # Test 4: Available Markets (sample)
        print("\n🏪 Available Markets (sample):")
        print("-" * 30)
        try:
            markets = client.get_markets()
            if markets.get('success') and 'result' in markets:
                market_list = markets['result']
                if isinstance(market_list, list):
                    print(f"📊 Total markets available: {len(market_list)}")
                    print("🔝 Top 5 markets:")
                    for market in market_list[:5]:
                        if isinstance(market, dict):
                            symbol = market.get('symbol', 'N/A')
                            base = market.get('baseAsset', 'N/A')
                            quote = market.get('quoteAsset', 'N/A')
                            print(f"   💱 {symbol}: {base}/{quote}")
                else:
                    print("⚠️  Unexpected market data format")
        except Exception as e:
            print(f"❌ Error getting markets: {e}")
        
        print("\n" + "="*60)
        print("✅ Account test completed successfully!")
        print("="*60)
        
    except WallexAuthenticationError as e:
        print(f"\n❌ Authentication Error: {e}")
        print("Please check your API key in the .env file")
        
    except WallexError as e:
        print(f"\n❌ Wallex API Error: {e}")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == "__main__":
    main()