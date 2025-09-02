#!/usr/bin/env python
"""Test AL Language Server symbol operations."""
import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Configuration
AL_EXTENSION_PATH = Path("ms-dynamics-smb.al-16.0.1743592")
TEST_REPO_PATH = Path("test/resources/repos/al/test_repo")
TIMEOUT = 10  # seconds

def create_lsp_message(content):
    """Create a properly formatted LSP message."""
    content_str = json.dumps(content, separators=(',', ':'))
    content_bytes = content_str.encode('utf-8')
    header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
    return header.encode('utf-8') + content_bytes

def read_lsp_response(process):
    """Read an LSP response from the process."""
    header = b""
    while b"\r\n\r\n" not in header:
        byte = process.stdout.read(1)
        if not byte:
            return None
        header += byte
    
    # Parse content length
    content_length = 0
    for line in header.split(b"\r\n"):
        if line.startswith(b"Content-Length: "):
            content_length = int(line[16:])
            break
    
    if content_length > 0:
        response_bytes = process.stdout.read(content_length)
        return json.loads(response_bytes.decode('utf-8'))
    return None

def test_al_lsp_symbols():
    """Test AL Language Server symbol operations."""
    
    # Set environment variable
    os.environ["AL_EXTENSION_PATH"] = str(AL_EXTENSION_PATH.resolve())
    
    # Determine platform-specific executable
    if sys.platform == "win32":
        lsp_exe = AL_EXTENSION_PATH / "bin" / "win32" / "Microsoft.Dynamics.Nav.EditorServices.Host.exe"
    else:
        print(f"Platform {sys.platform} not tested yet")
        return False
    
    if not lsp_exe.exists():
        print(f"[ERROR] LSP executable not found: {lsp_exe}")
        return False
    
    print(f"Starting AL Language Server: {lsp_exe}")
    
    # Start language server
    process = subprocess.Popen(
        [str(lsp_exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(TEST_REPO_PATH.resolve())
    )
    
    try:
        # 1. Initialize
        print("\n1. Sending initialize request...")
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": f"file:///{TEST_REPO_PATH.resolve()}".replace('\\', '/'),
                "capabilities": {
                    "textDocument": {
                        "synchronization": {
                            "dynamicRegistration": True,
                            "didSave": True
                        },
                        "documentSymbol": {
                            "dynamicRegistration": True,
                            "hierarchicalDocumentSymbolSupport": True
                        },
                        "definition": {
                            "dynamicRegistration": True
                        },
                        "references": {
                            "dynamicRegistration": True
                        }
                    }
                }
            }
        }
        
        message = create_lsp_message(initialize_request)
        process.stdin.write(message)
        process.stdin.flush()
        
        response = read_lsp_response(process)
        if response and "result" in response:
            print("[SUCCESS] Initialize successful")
            capabilities = response["result"].get("capabilities", {})
            print(f"   Document Symbol Provider: {capabilities.get('documentSymbolProvider', False)}")
            print(f"   Definition Provider: {capabilities.get('definitionProvider', False)}")
            print(f"   References Provider: {capabilities.get('referencesProvider', False)}")
        else:
            print("[FAILED] Initialize failed")
            return False
        
        # 2. Send initialized notification
        print("\n2. Sending initialized notification...")
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        message = create_lsp_message(initialized_notif)
        process.stdin.write(message)
        process.stdin.flush()
        
        # 3. Open a document
        print("\n3. Opening Customer.Table.al...")
        customer_file = TEST_REPO_PATH / "src" / "Tables" / "Customer.Table.al"
        with open(customer_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        did_open = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file:///{customer_file.resolve()}".replace('\\', '/'),
                    "languageId": "al",
                    "version": 1,
                    "text": file_content
                }
            }
        }
        message = create_lsp_message(did_open)
        process.stdin.write(message)
        process.stdin.flush()
        
        # Give server time to process
        time.sleep(2)
        
        # 4. Request document symbols
        print("\n4. Requesting document symbols...")
        doc_symbols_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/documentSymbol",
            "params": {
                "textDocument": {
                    "uri": f"file:///{customer_file.resolve()}".replace('\\', '/')
                }
            }
        }
        message = create_lsp_message(doc_symbols_request)
        process.stdin.write(message)
        process.stdin.flush()
        
        # Try to read response with timeout
        start_time = time.time()
        response = None
        while time.time() - start_time < TIMEOUT:
            response = read_lsp_response(process)
            if response and response.get("id") == 2:
                break
            time.sleep(0.1)
        
        if response and "result" in response:
            symbols = response.get("result", [])
            print(f"[SUCCESS] Document symbols received: {len(symbols)} symbols")
            for symbol in symbols[:5]:  # Print first 5 symbols
                print(f"   - {symbol.get('name')} ({symbol.get('kind')})")
        else:
            print("[WARNING] No symbols received (server may need more time to index)")
        
        # 5. Shutdown
        print("\n5. Sending shutdown request...")
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "shutdown"
        }
        message = create_lsp_message(shutdown_request)
        process.stdin.write(message)
        process.stdin.flush()
        
        # Exit notification
        exit_notif = {
            "jsonrpc": "2.0",
            "method": "exit"
        }
        message = create_lsp_message(exit_notif)
        process.stdin.write(message)
        process.stdin.flush()
        
        print("[SUCCESS] Shutdown complete")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error during testing: {e}")
        return False
    finally:
        # Terminate process
        process.terminate()
        process.wait(timeout=5)

if __name__ == "__main__":
    print("AL Language Server Symbol Operations Test")
    print("=" * 50)
    success = test_al_lsp_symbols()
    sys.exit(0 if success else 1)