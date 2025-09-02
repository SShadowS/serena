#!/usr/bin/env python
"""Quick test of AL Language Server initialization."""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set AL extension path
os.environ["AL_EXTENSION_PATH"] = str(Path("ms-dynamics-smb.al-16.0.1743592").resolve())

from solidlsp.ls_config import LanguageServerConfig, Language
from solidlsp.ls_logger import LanguageServerLogger
from solidlsp.language_servers.al_language_server import ALLanguageServer
from solidlsp.settings import SolidLSPSettings

class SimpleLogger(LanguageServerLogger):
    def log(self, msg: str, level: int = 0):
        print(f"[LOG {level}] {msg}")

async def test_al():
    """Test AL Language Server startup."""
    print("Creating AL Language Server...")
    
    config = LanguageServerConfig(
        code_language=Language.AL
    )
    
    logger = SimpleLogger()
    
    settings = SolidLSPSettings()
    
    test_repo = Path("test/resources/repos/al/test_repo").resolve()
    
    try:
        # Create AL Language Server
        ls = ALLanguageServer(
            config=config,
            logger=logger,
            repository_root_path=str(test_repo),
            solidlsp_settings=settings
        )
        
        print(f"Repository: {test_repo}")
        print(f"Starting server...")
        
        # Start with a timeout
        start_task = asyncio.create_task(ls.start())
        await asyncio.wait_for(start_task, timeout=30)
        
        print("Server started successfully!")
        
        # Try to get symbols
        test_file = test_repo / "src" / "Tables" / "Customer.Table.al"
        if test_file.exists():
            print(f"\nGetting symbols from {test_file.name}...")
            symbols = await ls.get_symbols_overview(str(test_file))
            print(f"Found {len(symbols) if symbols else 0} symbols")
            
            if symbols:
                for sym in symbols[:5]:
                    print(f"  - {sym.get('name', '?')}")
        
        # Stop server
        print("\nStopping server...")
        await ls.stop()
        print("Server stopped.")
        
        return True
        
    except asyncio.TimeoutError:
        print("ERROR: Server startup timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_al())
    sys.exit(0 if success else 1)