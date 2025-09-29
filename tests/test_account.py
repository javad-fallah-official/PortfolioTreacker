#!/usr/bin/env python3
"""
Comprehensive Wallex account test script
"""

import os
import json
import logging
from dotenv import load_dotenv
from wallex import WallexClient
from wallex import WallexAPIError


def main():
    """Main function to test various account endpoints"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    # Get API key from environment
    api_key = os.getenv('WALLEX_API_KEY')
    
    if not api_key:
        logger.error("WALLEX_API_KEY not found in .env file")
        return
    
    logger.info("API Key loaded successfully")
    
    try:
        # Initialize Wallex client
        client = WallexClient(api_key=api_key)
        
        logger.info("="*60)
        logger.info("WALLEX ACCOUNT SUMMARY")
        logger.info("="*60)
        
        # Test 1: Account Information
        logger.info("Account Information:")
        logger.info("-" * 30)
        try:
            account_info = client.get_account_info()
            if account_info.get('success'):
                result = account_info.get('result', {})
                logger.info(f"Email: {result.get('email', 'N/A')}")
                logger.info(f"Mobile: {result.get('mobile', 'N/A')}")
                logger.info(f"User ID: {result.get('id', 'N/A')}")
                logger.info(f"Verified: {result.get('is_verified', False)}")
                logger.info(f"2FA Enabled: {result.get('two_factor_enabled', False)}")
            else:
                logger.warning("Could not retrieve account info")
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
        
        # Test 2: Balance Summary
        logger.info("Balance Summary:")
        logger.info("-" * 30)
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
                            logger.info(f"{asset_name:>8}: {total:>15.8f} ({fa_name})")
                
                logger.info(f"Total supported assets: {total_assets}")
                logger.info(f"Assets with balance: {non_zero_count}")
                
                if non_zero_count == 0:
                    logger.info("All balances are currently zero")
                    
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
        
        # Test 3: Recent Orders (if any)
        logger.info("Recent Orders:")
        logger.info("-" * 30)
        try:
            orders = client.get_orders(limit=5)
            if orders.get('success') and 'result' in orders:
                order_list = orders['result']
                if isinstance(order_list, list) and order_list:
                    logger.info(f"Found {len(order_list)} recent orders:")
                    for order in order_list[:3]:  # Show first 3
                        symbol = order.get('symbol', 'N/A')
                        side = order.get('side', 'N/A')
                        status = order.get('status', 'N/A')
                        logger.info(f"   {symbol} - {side} - {status}")
                else:
                    logger.info("No recent orders found")
            else:
                logger.warning("Could not retrieve orders")
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
        
        # Test 4: Available Markets (sample)
        logger.info("Available Markets (sample):")
        logger.info("-" * 30)
        try:
            markets = client.get_markets()
            if markets.get('success') and 'result' in markets:
                market_list = markets['result']
                if isinstance(market_list, list):
                    logger.info(f"Total markets available: {len(market_list)}")
                    logger.info("Top 5 markets:")
                    for market in market_list[:5]:
                        if isinstance(market, dict):
                            symbol = market.get('symbol', 'N/A')
                            base = market.get('baseAsset', 'N/A')
                            quote = market.get('quoteAsset', 'N/A')
                            logger.info(f"   {symbol}: {base}/{quote}")
                else:
                    logger.warning("Unexpected market data format")
        except Exception as e:
            logger.error(f"Error getting markets: {e}")
        
        logger.info("="*60)
        logger.info("Account test completed successfully!")
        logger.info("="*60)
        
    except WallexAuthenticationError as e:
        logger.error(f"Authentication Error: {e}")
        logger.info("Please check your API key in the .env file")
        
    except WallexError as e:
        logger.error(f"Wallex API Error: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")

if __name__ == "__main__":
    main()