#!/usr/bin/env python
"""Test AL Language Server with Serena infrastructure."""

import os
import sys
import time
from pathlib import Path

# Set up environment
os.environ["AL_EXTENSION_PATH"] = str(Path("ms-dynamics-smb.al-16.0.1743592").resolve())
sys.path.insert(0, str(Path("src").resolve()))

from solidlsp.ls_config import LanguageServerConfig, Language
from solidlsp.ls_logger import LanguageServerLogger
from solidlsp.language_servers.al_language_server import ALLanguageServer
from solidlsp.settings import SolidLSPSettings

class TestLogger(LanguageServerLogger):
    def log(self, message: str, level: int = 0):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

def test_al_server():
    """Test AL Language Server."""
    print("=" * 60)
    print("Testing AL Language Server with Serena")
    print("=" * 60)
    
    test_repo = Path("test/resources/repos/al/test_repo").resolve()
    print(f"Test repository: {test_repo}")
    print(f"AL extension: {os.environ['AL_EXTENSION_PATH']}")
    
    # Create configuration
    config = LanguageServerConfig(
        code_language=Language.AL
    )
    
    # Create logger
    logger = TestLogger()
    
    # Create settings
    settings = SolidLSPSettings()
    
    try:
        # Create language server
        print("\n1. Creating AL Language Server instance...")
        ls = ALLanguageServer(
            config=config,
            logger=logger,
            repository_root_path=str(test_repo),
            solidlsp_settings=settings
        )
        print("   SUCCESS: Language server created")
        
        # Start the server
        print("\n2. Starting language server...")
        ls.start()
        print("   SUCCESS: Server started")
        
        # Wait a bit for initialization
        print("\n3. Waiting for initialization...")
        time.sleep(5)
        
        # Try to get symbols from a file
        test_file = test_repo / "src" / "Tables" / "Customer.Table.al"
        if test_file.exists():
            print(f"\n4. Opening file: {test_file.name}")
            
            # Open the file
            with ls.open_file(str(test_file.relative_to(test_repo))):
                print("   File opened in language server")
                
                # Request document symbols
                print("\n5. Requesting document symbols...")
                symbols = ls.request_document_symbols(str(test_file.relative_to(test_repo)))
                
                if symbols and symbols[0]:
                    print(f"   SUCCESS: Found {len(symbols[0])} symbols")
                    for sym in symbols[0][:5]:
                        name = sym.get("name", "?")
                        kind = sym.get("kind", "?")
                        print(f"     - {name} (kind={kind})")
                else:
                    print("   WARNING: No symbols found")
        
        # Try full symbol tree
        print("\n6. Requesting full symbol tree...")
        try:
            full_tree = ls.request_full_symbol_tree()
            if full_tree:
                print(f"   Found symbols in {len(full_tree)} files")
                for file_path, syms in list(full_tree.items())[:2]:
                    print(f"     {file_path}: {len(syms)} symbols")
            else:
                print("   WARNING: No symbol tree returned")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Stop the server
        print("\n7. Stopping server...")
        ls.stop()
        print("   SUCCESS: Server stopped")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_al_server()
    
    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED")
    else:
        print("TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)