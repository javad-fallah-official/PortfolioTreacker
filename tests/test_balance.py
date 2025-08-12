#!/usr/bin/env python3
"""
Simple test script to retrieve account balances using Wallex API
"""

import os
import json
import logging
from dotenv import load_dotenv
from wallex import WallexClient
from wallex.exceptions import WallexError, WallexAuthenticationError


def main():
    """Main function to test balance retrieval"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    # Get API key from environment
    api_key = os.getenv('WALLEX_API_KEY')
    
    if not api_key:
        logger.error("WALLEX_API_KEY not found in .env file")
        logger.info("Please add your API key to .env file: WALLEX_API_KEY=your_actual_api_key_here")
        return
    
    logger.info("API Key loaded from .env file")
    
    try:
        # Initialize Wallex client
        logger.info("Initializing Wallex client...")
        client = WallexClient(api_key=api_key)
        
        # Test 1: Get account information
        logger.info("Getting account information...")
        account_info = client.get_account_info()
        logger.info("Account info retrieved successfully")
        logger.debug(json.dumps(account_info, indent=2, ensure_ascii=False))
        
        # Test 2: Get all balances
        logger.info("Getting all account balances...")
        balances = client.get_balances()
        logger.info("Balances retrieved successfully")
        logger.debug(json.dumps(balances, indent=2, ensure_ascii=False))
        
        # Test 3: Display non-zero balances in a nice format
        logger.info("Non-zero balances summary:")
        
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
                header = f"{'Asset':>8} {'Persian Name':>15} {'Total':>15} {'Free':>15} {'Locked':>15}"
                logger.info(header)
                logger.info('-' * len(header))
                for balance in non_zero_balances:
                    logger.info(f"{balance['asset']:>6}: {balance['fa_name']:>15} {balance['total']:>15.8f} {balance['free']:>15.8f} {balance['locked']:>15.8f}")
                logger.info(f"Total assets with balance: {len(non_zero_balances)}")
            else:
                logger.info("No balances found or all balances are zero")
        else:
            logger.warning("Unexpected balance data format")
        
        logger.info("Balance test completed successfully!")
        
    except WallexAuthenticationError as e:
        logger.error(f"Authentication Error: {e}")
        logger.info("Please check your API key in the .env file")
        
    except WallexError as e:
        logger.error(f"Wallex API Error: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        logger.info("Please check your internet connection and API key")


if __name__ == "__main__":
    main()