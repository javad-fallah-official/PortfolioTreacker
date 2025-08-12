#!/usr/bin/env python3
"""
Test script to check Wallex market data for price information
"""

import os
import json
from dotenv import load_dotenv
from wallex import WallexClient

# Load environment variables
load_dotenv()

def test_market_data():
    """Test market data to see price information"""
    try:
        # Initialize client
        api_key = os.getenv('WALLEX_API_KEY')
        if not api_key:
            print("❌ WALLEX_API_KEY not found in .env file")
            return
        
        client = WallexClient(api_key=api_key)
        
        print("🔍 Testing Wallex market data...")
        
        # Test markets endpoint
        print("\n📊 Getting markets data...")
        markets_response = client.get_markets()
        
        if markets_response.get('success'):
            markets_data = markets_response.get('result', {})
            print(f"✅ Found {len(markets_data)} markets")
            
            # Show first few markets
            market_items = list(markets_data.items())[:3]
            for symbol, market_info in market_items:
                print(f"\n🏷️ Market: {symbol}")
                print(json.dumps(market_info, indent=2, ensure_ascii=False))
        else:
            print("❌ Failed to get markets data")
            print(json.dumps(markets_response, indent=2, ensure_ascii=False))
        
        # Test specific market stats (BTC/IRT)
        print("\n💰 Getting BTC/IRT market stats...")
        btc_stats = client.get_market_stats('BTCIRT')
        
        if btc_stats.get('success'):
            stats_data = btc_stats.get('result', {})
            print("✅ BTC/IRT market stats:")
            print(json.dumps(stats_data, indent=2, ensure_ascii=False))
        else:
            print("❌ Failed to get BTC/IRT stats")
            print(json.dumps(btc_stats, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_market_data()