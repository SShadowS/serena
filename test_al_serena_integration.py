#!/usr/bin/env python
"""Test AL Language Server integration with Serena."""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path to import serena modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from solidlsp.ls import SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig, Language
from solidlsp.logging import TestLogger
from solidlsp.solid_settings import SolidLSPSettings

async def test_al_integration():
    """Test AL Language Server through Serena's infrastructure."""
    
    # Set up paths
    test_repo = Path("test/resources/repos/al/test_repo").resolve()
    os.environ["AL_EXTENSION_PATH"] = str(Path("ms-dynamics-smb.al-16.0.1743592").resolve())
    
    print("=" * 60)
    print("AL Language Server - Serena Integration Test")
    print("=" * 60)
    print(f"Test Repository: {test_repo}")
    print(f"AL Extension: {os.environ['AL_EXTENSION_PATH']}")
    print("=" * 60)
    
    # Create configuration
    config = LanguageServerConfig(
        code_language=Language.AL,
        language_server_command_override=None,
        enable_code_search=True
    )
    
    # Create logger
    logger = TestLogger()
    
    # Create settings
    settings = SolidLSPSettings()
    
    # Create language server instance
    print("\n1. Creating AL Language Server instance...")
    ls = SolidLanguageServer.create(
        config=config,
        logger=logger,
        repository_root_path=str(test_repo),
        solidlsp_settings=settings
    )
    
    if not ls:
        print("[ERROR] Failed to create language server")
        return False
    
    print(f"[SUCCESS] Created {type(ls).__name__}")
    
    try:
        # Start the language server
        print("\n2. Starting language server...")
        await ls.start()
        print("[SUCCESS] Language server started")
        
        # Test file operations
        test_file = test_repo / "src" / "Tables" / "Customer.Table.al"
        print(f"\n3. Testing file: {test_file.name}")
        
        # Get symbols overview
        print("\n4. Getting symbols overview...")
        symbols = await ls.get_symbols_overview(str(test_file))
        
        if symbols:
            print(f"[SUCCESS] Found {len(symbols)} symbols:")
            for symbol in symbols[:10]:  # First 10
                print(f"  - {symbol.get('name', '?')} ({symbol.get('kind', '?')})")
        else:
            print("[WARNING] No symbols found")
        
        # Find specific symbol
        print("\n5. Finding symbol 'TEST Customer'...")
        found_symbols = await ls.find_symbol(
            symbol_query="TEST Customer",
            file_path=str(test_file)
        )
        
        if found_symbols:
            print(f"[SUCCESS] Found {len(found_symbols)} matching symbols")
            for sym in found_symbols:
                print(f"  - {sym.get('name', '?')} at line {sym.get('location', {}).get('start_line', '?')}")
        else:
            print("[WARNING] Symbol not found")
        
        # Test workspace symbols
        print("\n6. Testing workspace symbols...")
        workspace_symbols = await ls.find_symbol(
            symbol_query="Customer",
            file_path=None  # Search entire workspace
        )
        
        if workspace_symbols:
            print(f"[SUCCESS] Found {len(workspace_symbols)} workspace symbols containing 'Customer'")
            for sym in workspace_symbols[:5]:
                print(f"  - {sym.get('name', '?')} in {sym.get('file_path', '?')}")
        else:
            print("[WARNING] No workspace symbols found")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Stop the language server
        print("\n7. Stopping language server...")
        try:
            await ls.stop()
            print("[SUCCESS] Language server stopped")
        except Exception as e:
            print(f"[WARNING] Error stopping server: {e}")

async def main():
    """Main entry point."""
    success = await test_al_integration()
    
    print("\n" + "=" * 60)
    if success:
        print("TEST RESULT: PASSED")
        print("AL Language Server integration is working!")
    else:
        print("TEST RESULT: FAILED")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)