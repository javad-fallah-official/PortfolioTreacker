#!/usr/bin/env python3
"""
Simple test script to retrieve account balances using Wallex API
"""

import os
import json
from dotenv import load_dotenv
from wallex import WallexClient
from wallex.exceptions import WallexError, WallexAuthenticationError

def main():
    """Main function to test balance retrieval"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv('WALLEX_API_KEY')
    
    if not api_key:
        print("❌ Error: WALLEX_API_KEY not found in .env file")
        print("Please add your API key to .env file:")
        print("WALLEX_API_KEY=your_actual_api_key_here")
        return
    
    print("🔑 API Key loaded from .env file")
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
    
    try:
        # Initialize Wallex client
        print("\n📡 Initializing Wallex client...")
        client = WallexClient(api_key=api_key)
        
        # Test 1: Get account information
        print("\n👤 Getting account information...")
        account_info = client.get_account_info()
        print("✅ Account info retrieved successfully:")
        print(json.dumps(account_info, indent=2, ensure_ascii=False))
        
        # Test 2: Get all balances
        print("\n💰 Getting all account balances...")
        balances = client.get_balances()
        print("✅ Balances retrieved successfully:")
        print(json.dumps(balances, indent=2, ensure_ascii=False))
        
        # Test 3: Display non-zero balances in a nice format
        print("\n📊 Non-zero balances summary:")
        print("-" * 50)
        
        if 'result' in balances and isinstance(balances['result'], dict):
            non_zero_balances = []
            
            # Handle the dictionary format where keys are asset names
            for asset_name, balance_data in balances['result'].items():
                if isinstance(balance_data, dict):
                    asset = balance_data.get('asset', asset_name)
                    free = float(balance_data.get('value', 0))
                    locked = float(balance_data.get('locked', 0))
                    total = free + locked
                    fa_name = balance_data.get('faName', asset)
                    
                    if total > 0:
                        non_zero_balances.append({
                            'asset': asset,
                            'fa_name': fa_name,
                            'free': free,
                            'locked': locked,
                            'total': total
                        })
            
            if non_zero_balances:
                print(f"{'Asset':>8} {'Persian Name':>15} {'Total':>15} {'Free':>15} {'Locked':>15}")
                print("-" * 80)
                for balance in non_zero_balances:
                    print(f"💎 {balance['asset']:>6}: {balance['fa_name']:>15} {balance['total']:>15.8f} {balance['free']:>15.8f} {balance['locked']:>15.8f}")
                
                print(f"\n🎯 Total assets with balance: {len(non_zero_balances)}")
            else:
                print("💸 No balances found or all balances are zero")
        else:
            print("⚠️  Unexpected balance data format")
        
        print("\n✅ Balance test completed successfully!")
        
    except WallexAuthenticationError as e:
        print(f"\n❌ Authentication Error: {e}")
        print("Please check your API key in the .env file")
        
    except WallexError as e:
        print(f"\n❌ Wallex API Error: {e}")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("Please check your internet connection and API key")

if __name__ == "__main__":
    main()