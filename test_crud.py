#!/usr/bin/env python3

import asyncio
import aiohttp
import json

async def test_crud_operations():
    """Test CRUD operations for the database API"""
    base_url = "http://127.0.0.1:8000/api/database"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Get snapshots
        print("\n=== Testing GET snapshots ===")
        async with session.get(f"{base_url}/snapshots") as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            if data.get('success'):
                snapshots = data.get('snapshots', [])
                print(f"Found {len(snapshots)} snapshots")
                if snapshots:
                    snapshot_id = snapshots[0]['id']
                    print(f"First snapshot ID: {snapshot_id}")
            else:
                print(f"Error: {data.get('error')}")
        
        # Test 2: Update snapshot
        if 'snapshot_id' in locals():
            print(f"\n=== Testing PUT snapshot {snapshot_id} ===")
            update_data = {
                "total_usd_value": 1500.0,
                "total_irr_value": 75000000.0,
                "total_assets": 10,
                "assets_with_balance": 8,
                "account_email": "test@example.com"
            }
            async with session.put(
                f"{base_url}/snapshot/{snapshot_id}",
                json=update_data
            ) as resp:
                data = await resp.json()
                print(f"Status: {resp.status}")
                print(f"Response: {data}")
        
        # Test 3: Get assets
        print("\n=== Testing GET assets ===")
        async with session.get(f"{base_url}/assets") as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            if data.get('success'):
                assets = data.get('assets', [])
                print(f"Found {len(assets)} assets")
                if assets:
                    asset_id = assets[0]['id']
                    print(f"First asset ID: {asset_id}")
                    print(f"Asset name: {assets[0].get('asset_name')}")
            else:
                print(f"Error: {data.get('error')}")
        
        # Test 4: Update asset
        if 'asset_id' in locals():
            print(f"\n=== Testing PUT asset {asset_id} ===")
            update_data = {
                "usd_value": 800.0,
                "irr_value": 40000000.0
            }
            async with session.put(
                f"{base_url}/asset/{asset_id}",
                json=update_data
            ) as resp:
                data = await resp.json()
                print(f"Status: {resp.status}")
                print(f"Response: {data}")

if __name__ == "__main__":
    asyncio.run(test_crud_operations())