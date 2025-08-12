#!/usr/bin/env python3
"""
Quick test script for Wallex Python Client

This script performs basic tests to ensure the client is working correctly.
"""

import asyncio
import sys
import pytest
from wallex import WallexClient, WallexConfig
from wallex.types import CommonSymbols


@pytest.mark.asyncio
async def test_basic_functionality():
    """Test basic client functionality"""
    print("🚀 Testing Wallex Python Client")
    print("=" * 50)
    
    # Test 1: Client initialization
    print("✅ Test 1: Client initialization")
    try:
        client = WallexClient()
        print("   ✓ Client created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")
        return False
    
    # Test 2: Configuration
    print("✅ Test 2: Configuration")
    try:
        config = WallexConfig(
            api_key="test_key",
            base_url="https://api.wallex.ir"
        )
        client_with_config = WallexClient(config)
        print("   ✓ Configuration works correctly")
    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        return False
    
    # Test 3: Type imports
    print("✅ Test 3: Type imports")
    try:
        from wallex.types import OrderSide, OrderType
        from wallex.utils import validate_symbol, format_price
        print("   ✓ All types and utilities imported successfully")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 4: Utility functions
    print("✅ Test 4: Utility functions")
    try:
        from wallex.utils import validate_symbol, format_price
        
        # Test symbol validation
        assert validate_symbol("BTCUSDT") == True
        assert validate_symbol("invalid") == False
        
        # Test price formatting
        formatted = format_price(123.456789, 2)
        assert formatted == "123.46"
        
        print("   ✓ Utility functions work correctly")
    except Exception as e:
        print(f"   ❌ Utility test failed: {e}")
        return False
    
    # Test 5: WebSocket client initialization
    print("✅ Test 5: WebSocket client")
    try:
        ws_client = client.websocket
        print("   ✓ WebSocket client accessible")
    except Exception as e:
        print(f"   ❌ WebSocket client failed: {e}")
        return False
    
    print("\n🎉 All basic tests passed!")
    print("\n📋 Next steps:")
    print("   1. Set up API credentials in .env file")
    print("   2. Run examples.py for live API testing")
    print("   3. Check README.md for detailed usage")
    
    return True


def main():
    """Main test function"""
    try:
        success = asyncio.run(test_basic_functionality())
        if success:
            print("\n✅ Wallex Python Client is ready to use!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()