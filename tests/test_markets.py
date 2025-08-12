#!/usr/bin/env python3
"""
Test script to check Wallex market data for price information
"""

import os
import json
import logging
from dotenv import load_dotenv
from wallex import WallexClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_market_data():
    """Test market data to see price information"""
    try:
        # Initialize client
        api_key = os.getenv('WALLEX_API_KEY')
        if not api_key:
            logger.error("WALLEX_API_KEY not found in .env file")
            return
        
        client = WallexClient(api_key=api_key)
        
        logger.info("Testing Wallex market data...")
        
        # Test markets endpoint
        logger.info("Getting markets data...")
        markets_response = client.get_markets()
        
        if markets_response.get('success'):
            markets_data = markets_response.get('result', {})
            logger.info(f"Found {len(markets_data)} markets")
            
            # Show first few markets
            market_items = list(markets_data.items())[:3]
            for symbol, market_info in market_items:
                logger.info(f"Market: {symbol}")
                logger.debug(json.dumps(market_info, indent=2, ensure_ascii=False))
        else:
            logger.error("Failed to get markets data")
            logger.debug(json.dumps(markets_response, indent=2, ensure_ascii=False))
        
        # Test specific market stats (BTC/IRT)
        logger.info("Getting BTC/IRT market stats...")
        btc_stats = client.get_market_stats('BTCIRT')
        
        if btc_stats.get('success'):
            stats_data = btc_stats.get('result', {})
            logger.info("BTC/IRT market stats:")
            logger.debug(json.dumps(stats_data, indent=2, ensure_ascii=False))
        else:
            logger.error("Failed to get BTC/IRT stats")
            logger.debug(json.dumps(btc_stats, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_market_data()