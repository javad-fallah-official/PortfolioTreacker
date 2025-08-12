import asyncio
import os
import logging
from dotenv import load_dotenv
from wallex import WallexClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_wallex_api():
    api_key = os.getenv('WALLEX_API_KEY')
    if not api_key:
        logger.error('No API key found')
        return
    
    client = WallexClient(api_key)
    response = client.get_markets()
    
    if response.get('success'):
        symbols = response.get('result', {}).get('symbols', {})
        logger.info('=== Sample Market Data ===')
        
        # Show first 3 markets with their stats
        count = 0
        for symbol, data in symbols.items():
            if count >= 3:
                break
            stats = data.get('stats', {})
            logger.info(f'Symbol: {symbol}')
            logger.info(f'  Last Price: {stats.get("lastPrice", "N/A")}')
            logger.info(f'  Price Change %: {stats.get("priceChangePercent", "N/A")}')
            logger.info(f'  Volume 24h: {stats.get("volume", "N/A")}')
            logger.info(f'  High 24h: {stats.get("highPrice", "N/A")}')
            logger.info(f'  Low 24h: {stats.get("lowPrice", "N/A")}')
            logger.info(f'  Quote Volume: {stats.get("quoteVolume", "N/A")}')
            logger.info('---')
            count += 1
    else:
        logger.error(f'Failed to get market data: {response}')

if __name__ == "__main__":
    asyncio.run(test_wallex_api())