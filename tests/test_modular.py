#!/usr/bin/env python3
"""
Simple test to verify the modular Wallex library structure
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported correctly"""
    logger.info("Testing imports...")
    
    # Test main package imports
    try:
        from wallex import WallexClient, WallexConfig, create_client, create_async_client
        logger.info("Main package imports successful")
    except ImportError as e:
        logger.error(f"Main package import failed: {e}")
        assert False, f"Main package import failed: {e}"
    
    # Test submodule imports
    try:
        from wallex.rest import WallexRestClient
        from wallex.socket import WallexWebSocketClient, WallexAsyncWebSocketClient
        from wallex.config import WallexConfig
        from wallex.types import OrderSide, OrderType, CommonSymbols
        from wallex.utils import validate_symbol, format_price
        from wallex.exceptions import WallexError, WallexAPIError
        logger.info("Submodule imports successful")
    except ImportError as e:
        logger.error(f"Submodule import failed: {e}")
        assert False, f"Submodule import failed: {e}"
    
    assert True


def test_basic_functionality():
    """Test basic functionality without making API calls"""
    logger.info("Testing basic functionality...")
    
    try:
        from wallex import WallexClient, WallexConfig
        from wallex.utils import validate_symbol, format_price
        
        # Test configuration
        config = WallexConfig(testnet=True)
        logger.info(f"Configuration created: testnet={config.testnet}")
        
        # Test client creation
        client = WallexClient(config)
        logger.info("Client created successfully")
        
        # Test utility functions
        is_valid = validate_symbol("BTCUSDT")
        logger.info(f"Symbol validation: BTCUSDT is valid = {is_valid}")
        
        formatted = format_price(1234.5678, precision=2)
        logger.info(f"Price formatting: 1234.5678 -> {formatted}")
        
        assert True
        
    except Exception as e:
        logger.error(f"Basic functionality test failed: {e}")
        assert False, f"Basic functionality test failed: {e}"


def test_modular_access():
    """Test accessing modules individually"""
    logger.info("Testing modular access...")
    
    try:
        # Test REST module
        from wallex.rest import WallexRestClient
        from wallex.config import WallexConfig
        
        config = WallexConfig()
        rest_client = WallexRestClient(config)
        logger.info("REST client created independently")
        
        # Test WebSocket module
        from wallex.socket import WallexWebSocketClient
        
        ws_client = WallexWebSocketClient(config)
        logger.info("WebSocket client created independently")
        
        # Test types module
        from wallex.types import OrderSide, OrderType
        
        logger.info(f"Types accessible: OrderSide.BUY = {OrderSide.__args__[0] if hasattr(OrderSide, '__args__') else 'BUY'}")
        
        assert True
        
    except Exception as e:
        logger.error(f"Modular access test failed: {e}")
        assert False


def main():
    """Run all tests"""
    logger.info("Wallex Modular Library Test")
    logger.info("=" * 40)
    
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
    
    logger.info("=" * 40)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("All tests passed! The modular library is working correctly.")
        return True
    else:
        logger.error("Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)