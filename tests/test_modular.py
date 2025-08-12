#!/usr/bin/env python3
"""
Simple test to verify the modular Wallex library structure
"""

def test_imports():
    """Test that all modules can be imported correctly"""
    print("Testing imports...")
    
    # Test main package imports
    try:
        from wallex import WallexClient, WallexConfig, create_client, create_async_client
        print("✓ Main package imports successful")
    except ImportError as e:
        print(f"✗ Main package import failed: {e}")
        return False
    
    # Test submodule imports
    try:
        from wallex.rest import WallexRestClient
        from wallex.socket import WallexWebSocketClient, WallexAsyncWebSocketClient
        from wallex.config import WallexConfig
        from wallex.types import OrderSide, OrderType, CommonSymbols
        from wallex.utils import validate_symbol, format_price
        from wallex.exceptions import WallexError, WallexAPIError
        print("✓ Submodule imports successful")
    except ImportError as e:
        print(f"✗ Submodule import failed: {e}")
        return False
    
    return True


def test_basic_functionality():
    """Test basic functionality without making API calls"""
    print("\nTesting basic functionality...")
    
    try:
        from wallex import WallexClient, WallexConfig
        from wallex.utils import validate_symbol, format_price
        
        # Test configuration
        config = WallexConfig(testnet=True)
        print(f"✓ Configuration created: testnet={config.testnet}")
        
        # Test client creation
        client = WallexClient(config)
        print("✓ Client created successfully")
        
        # Test utility functions
        is_valid = validate_symbol("BTCUSDT")
        print(f"✓ Symbol validation: BTCUSDT is valid = {is_valid}")
        
        formatted = format_price(1234.5678, precision=2)
        print(f"✓ Price formatting: 1234.5678 -> {formatted}")
        
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False


def test_modular_access():
    """Test accessing modules individually"""
    print("\nTesting modular access...")
    
    try:
        # Test REST module
        from wallex.rest import WallexRestClient
        from wallex.config import WallexConfig
        
        config = WallexConfig()
        rest_client = WallexRestClient(config)
        print("✓ REST client created independently")
        
        # Test WebSocket module
        from wallex.socket import WallexWebSocketClient
        
        ws_client = WallexWebSocketClient(config)
        print("✓ WebSocket client created independently")
        
        # Test types module
        from wallex.types import OrderSide, OrderType
        
        print(f"✓ Types accessible: OrderSide.BUY = {OrderSide.__args__[0] if hasattr(OrderSide, '__args__') else 'BUY'}")
        
        return True
        
    except Exception as e:
        print(f"✗ Modular access test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Wallex Modular Library Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_basic_functionality,
        test_modular_access
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The modular library is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)