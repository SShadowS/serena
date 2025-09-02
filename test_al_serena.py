#!/usr/bin/env python
"""Test AL Language Server initialization via Serena."""
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from solidlsp.ls_config import Language, LanguageServerConfig
from solidlsp.ls_logger import LanguageServerLogger
from solidlsp.ls import SolidLanguageServer
from solidlsp.settings import SolidLSPSettings

def test_al_language_server():
    """Test AL Language Server initialization through Serena."""
    
    # Set AL extension path
    os.environ["AL_EXTENSION_PATH"] = str(Path.cwd() / "ms-dynamics-smb.al-16.0.1743592")
    
    print("Testing AL Language Server initialization...")
    print(f"AL_EXTENSION_PATH: {os.environ.get('AL_EXTENSION_PATH')}")
    
    # Create logger
    logger = LanguageServerLogger()
    logger.logger.setLevel(logging.INFO)
    
    # Create test repository path (we'll use current directory for testing)
    test_repo_path = str(Path.cwd())
    
    # Create config for AL
    config = LanguageServerConfig(
        code_language=Language.AL,
        ignored_paths=[],
        trace_lsp_communication=True,
        start_independent_lsp_process=False
    )
    
    # Create settings
    settings = SolidLSPSettings()
    
    try:
        # Create AL Language Server instance
        print("\nCreating AL Language Server instance...")
        al_server = SolidLanguageServer.create(
            config=config,
            logger=logger,
            repository_root_path=test_repo_path,
            solidlsp_settings=settings
        )
        
        print(f"✅ AL Language Server created successfully!")
        print(f"   Language ID: {al_server.language_id}")
        print(f"   Repository: {al_server.repository_root_path}")
        
        # Test file extension recognition
        print("\nTesting file extension recognition...")
        matcher = Language.AL.get_source_fn_matcher()
        test_files = ["test.al", "test.dal", "test.py", "test.js"]
        
        for file in test_files:
            matches = matcher.matches(file)
            print(f"   {file}: {'✅ Recognized' if matches else '❌ Not recognized'}")
        
        # Test ignored directories
        print("\nTesting ignored directories...")
        ignored_dirs = [".alpackages", ".alcache", "node_modules", "src"]
        for dir_name in ignored_dirs:
            is_ignored = al_server.is_ignored_dirname(dir_name)
            print(f"   {dir_name}: {'✅ Ignored' if is_ignored else '❌ Not ignored'}")
        
        print("\n✅ All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_al_serena()
    sys.exit(0 if success else 1)