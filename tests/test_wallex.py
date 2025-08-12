import asyncio
import os
from dotenv import load_dotenv
from wallex import WallexClient

# Load environment variables
load_dotenv()

async def test_wallex_api():
    api_key = os.getenv('WALLEX_API_KEY')
    if not api_key:
        print('No API key found')
        return
    
    client = WallexClient(api_key)
    response = client.get_markets()
    
    if response.get('success'):
        symbols = response.get('result', {}).get('symbols', {})
        print('=== Sample Market Data ===')
        
        # Show first 3 markets with their stats
        count = 0
        for symbol, data in symbols.items():
            if count >= 3:
                break
            stats = data.get('stats', {})
            print(f'Symbol: {symbol}')
            print(f'  Last Price: {stats.get("lastPrice", "N/A")}')
            print(f'  Price Change %: {stats.get("priceChangePercent", "N/A")}')
            print(f'  Volume 24h: {stats.get("volume", "N/A")}')
            print(f'  High 24h: {stats.get("highPrice", "N/A")}')
            print(f'  Low 24h: {stats.get("lowPrice", "N/A")}')
            print(f'  Quote Volume: {stats.get("quoteVolume", "N/A")}')
            print('---')
            count += 1
    else:
        print('Failed to get market data:', response)

if __name__ == "__main__":
    asyncio.run(test_wallex_api())