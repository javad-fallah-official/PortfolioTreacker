#!/usr/bin/env python3
"""
Quick test script for Wallex Python Client

This script performs basic tests to ensure the client is working correctly.
"""

import asyncio
import sys
import logging
import pytest
from wallex import WallexClient, WallexConfig
from wallex.types import CommonSymbols

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_basic_functionality():
    """Test basic client functionality"""
    logger.info("Testing Wallex Python Client")
    logger.info("=" * 50)
    
    # Test 1: Client initialization
    logger.info("Test 1: Client initialization")
    try:
        client = WallexClient()
        logger.info("   Client created successfully")
    except Exception as e:
        logger.error(f"   Failed to create client: {e}")
        return False
    
    # Test 2: Configuration
    logger.info("Test 2: Configuration")
    try:
        config = WallexConfig(
            api_key="test_key",
            base_url="https://api.wallex.ir"
        )
        client_with_config = WallexClient(config)
        logger.info("   Configuration works correctly")
    except Exception as e:
        logger.error(f"   Configuration failed: {e}")
        return False
    
    # Test 3: Type imports
    logger.info("Test 3: Type imports")
    try:
        from wallex.types import OrderSide, OrderType
        from wallex.utils import validate_symbol, format_price
        logger.info("   All types and utilities imported successfully")
    except Exception as e:
        logger.error(f"   Import failed: {e}")
        return False
    
    # Test 4: Utility functions
    logger.info("Test 4: Utility functions")
    try:
        from wallex.utils import validate_symbol, format_price
        
        # Test symbol validation
        assert validate_symbol("BTCUSDT") == True
        assert validate_symbol("invalid") == False
        
        # Test price formatting
        formatted = format_price(123.456789, 2)
        assert formatted == "123.46"
        
        logger.info("   Utility functions work correctly")
    except Exception as e:
        logger.error(f"   Utility test failed: {e}")
        return False
    
    # Test 5: WebSocket client initialization
    logger.info("Test 5: WebSocket client")
    try:
        ws_client = client.websocket
        logger.info("   WebSocket client accessible")
    except Exception as e:
        logger.error(f"   WebSocket client failed: {e}")
        return False
    
    logger.info("All basic tests passed!")
    logger.info("Next steps:")
    logger.info("   1. Set up API credentials in .env file")
    logger.info("   2. Run examples.py for live API testing")
    logger.info("   3. Check README.md for detailed usage")
    
    return True


def main():
    """Main test function"""
    try:
        success = asyncio.run(test_basic_functionality())
        if success:
            logger.info("Wallex Python Client is ready to use!")
            sys.exit(0)
        else:
            logger.error("Some tests failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()