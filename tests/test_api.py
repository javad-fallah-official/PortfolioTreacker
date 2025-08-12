import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    response = requests.get("http://localhost:8000/api/live-prices/markets")
    data = response.json()
    
    if data.get('success'):
        markets = data.get('data', [])[:3]  # First 3 markets
        logger.info("=== Live Markets API Response ===")
        for market in markets:
            logger.info(f"Symbol: {market.get('symbol', 'N/A')}")
            logger.info(f"  Price Change %: {market.get('price_change_percent', 'N/A')}")
            logger.info(f"  Volume 24h: {market.get('volume_24h', 'N/A')}")
            logger.info(f"  High 24h: {market.get('high_24h', 'N/A')}")
            logger.info(f"  Low 24h: {market.get('low_24h', 'N/A')}")
            logger.info('---')
    else:
        logger.error(f"API Error: {data.get('error', 'Unknown error')}")
        
except Exception as e:
    logger.error(f"Error: {e}")