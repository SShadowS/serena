#!/usr/bin/env python
"""Test AL Language Server LSP communication."""
import json
import subprocess
import os
import sys
from pathlib import Path

def create_lsp_message(content):
    """Create a properly formatted LSP message."""
    content_str = json.dumps(content)
    content_bytes = content_str.encode('utf-8')
    header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
    return header.encode('utf-8') + content_bytes

def test_al_lsp():
    """Test basic AL Language Server communication."""
    # Path to AL extension
    extension_path = Path("ms-dynamics-smb.al-16.0.1743592")
    
    # Determine platform
    if sys.platform == "win32":
        lsp_exe = extension_path / "bin" / "win32" / "Microsoft.Dynamics.Nav.EditorServices.Host.exe"
    elif sys.platform == "linux":
        lsp_exe = extension_path / "bin" / "linux" / "Microsoft.Dynamics.Nav.EditorServices.Host"
    elif sys.platform == "darwin":
        lsp_exe = extension_path / "bin" / "darwin" / "Microsoft.Dynamics.Nav.EditorServices.Host"
    else:
        print(f"Unsupported platform: {sys.platform}")
        return False
    
    if not lsp_exe.exists():
        print(f"LSP executable not found: {lsp_exe}")
        return False
    
    print(f"Testing AL Language Server: {lsp_exe}")
    print(f"Platform: {sys.platform}")
    
    # Create initialize request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": os.getpid(),
            "rootUri": f"file:///{Path.cwd()}",
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": True,
                        "willSave": True,
                        "willSaveWaitUntil": True,
                        "didSave": True
                    }
                }
            }
        }
    }
    
    # Start language server process
    try:
        # For Windows, ensure we use the correct shell behavior
        if sys.platform == "win32":
            # Use shell=False and pass as list for Windows
            process = subprocess.Popen(
                [str(lsp_exe)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
        else:
            process = subprocess.Popen(
                [str(lsp_exe)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        # Send initialize request
        message = create_lsp_message(initialize_request)
        print(f"\nSending initialize request...")
        process.stdin.write(message)
        process.stdin.flush()
        
        # Read response header
        print("Reading response...")
        header = b""
        while b"\r\n\r\n" not in header:
            byte = process.stdout.read(1)
            if not byte:
                print("No response received")
                break
            header += byte
        
        if header:
            # Parse content length
            content_length = 0
            for line in header.split(b"\r\n"):
                if line.startswith(b"Content-Length: "):
                    content_length = int(line[16:])
                    break
            
            # Read response body
            if content_length > 0:
                response_bytes = process.stdout.read(content_length)
                response = json.loads(response_bytes.decode('utf-8'))
                
                print("\nInitialize Response:")
                print(json.dumps(response, indent=2))
                
                # Check if initialization was successful
                if "result" in response:
                    print("\n✅ LSP initialization successful!")
                    print(f"Server capabilities: {list(response['result'].get('capabilities', {}).keys())}")
                    return True
                elif "error" in response:
                    print(f"\n❌ LSP initialization failed: {response['error']}")
                    return False
        
        # Terminate process
        process.terminate()
        
    except Exception as e:
        print(f"Error testing LSP: {e}")
        return False
    
    return False

if __name__ == "__main__":
    success = test_al_lsp()
    sys.exit(0 if success else 1)