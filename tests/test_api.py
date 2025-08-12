import requests
import json

try:
    response = requests.get("http://localhost:8000/api/live-prices/markets")
    data = response.json()
    
    if data.get('success'):
        markets = data.get('data', [])[:3]  # First 3 markets
        print("=== Live Markets API Response ===")
        for market in markets:
            print(f'Symbol: {market.get("symbol", "N/A")}')
            print(f'  Price Change %: {market.get("price_change_percent", "N/A")}')
            print(f'  Volume 24h: {market.get("volume_24h", "N/A")}')
            print(f'  High 24h: {market.get("high_24h", "N/A")}')
            print(f'  Low 24h: {market.get("low_24h", "N/A")}')
            print('---')
    else:
        print('API Error:', data.get('error', 'Unknown error'))
        
except Exception as e:
    print(f"Error: {e}")