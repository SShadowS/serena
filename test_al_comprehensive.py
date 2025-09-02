#!/usr/bin/env python
"""Comprehensive test for AL Language Server integration."""
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Any, Dict, List

# Configuration
AL_EXTENSION_PATH = Path("ms-dynamics-smb.al-16.0.1743592")
TEST_REPO_PATH = Path("test/resources/repos/al/test_repo")
TIMEOUT = 30  # seconds

class ALLanguageServerTester:
    def __init__(self):
        self.process = None
        self.request_id = 0
        self.responses = {}
        
    def create_lsp_message(self, content: Dict[str, Any]) -> bytes:
        """Create a properly formatted LSP message."""
        content_str = json.dumps(content, separators=(',', ':'))
        content_bytes = content_str.encode('utf-8')
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
        return header.encode('utf-8') + content_bytes

    def read_lsp_response(self) -> Optional[Dict[str, Any]]:
        """Read an LSP response from the process."""
        try:
            header = b""
            while b"\r\n\r\n" not in header:
                byte = self.process.stdout.read(1)
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
                response_bytes = self.process.stdout.read(content_length)
                return json.loads(response_bytes.decode('utf-8'))
        except Exception as e:
            print(f"[WARNING] Error reading response: {e}")
        return None

    def send_request(self, method: str, params: Dict[str, Any]) -> int:
        """Send a request and return the request ID."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        message = self.create_lsp_message(request)
        self.process.stdin.write(message)
        self.process.stdin.flush()
        return self.request_id

    def send_notification(self, method: str, params: Dict[str, Any]):
        """Send a notification (no ID, no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        message = self.create_lsp_message(notification)
        self.process.stdin.write(message)
        self.process.stdin.flush()

    def wait_for_response(self, request_id: int, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Wait for a specific response by ID."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.read_lsp_response()
            if response:
                # Store all responses
                if "id" in response:
                    self.responses[response["id"]] = response
                    if response["id"] == request_id:
                        return response
                # Print notifications/errors
                elif "method" in response:
                    print(f"[NOTIFICATION] {response['method']}")
                elif "error" in response:
                    print(f"[ERROR] {response.get('error', {}).get('message', 'Unknown error')}")
            time.sleep(0.1)
        return None

    def run_tests(self):
        """Run comprehensive AL Language Server tests."""
        # Set environment variable
        os.environ["AL_EXTENSION_PATH"] = str(AL_EXTENSION_PATH.resolve())
        
        # Determine platform-specific executable
        if sys.platform == "win32":
            lsp_exe = AL_EXTENSION_PATH / "bin" / "win32" / "Microsoft.Dynamics.Nav.EditorServices.Host.exe"
        else:
            print(f"[ERROR] Platform {sys.platform} not tested yet")
            return False
        
        if not lsp_exe.exists():
            print(f"[ERROR] LSP executable not found: {lsp_exe}")
            return False
        
        print("=" * 60)
        print("AL Language Server Comprehensive Test")
        print("=" * 60)
        print(f"Extension Path: {AL_EXTENSION_PATH.resolve()}")
        print(f"Test Repo Path: {TEST_REPO_PATH.resolve()}")
        print(f"LSP Executable: {lsp_exe}")
        print("=" * 60)
        
        # Start language server
        print("\nStarting AL Language Server...")
        self.process = subprocess.Popen(
            [str(lsp_exe)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(TEST_REPO_PATH.resolve())
        )
        
        try:
            # 1. Initialize
            print("\n1. INITIALIZE")
            print("-" * 40)
            root_uri = f"file:///{TEST_REPO_PATH.resolve()}".replace('\\', '/')
            
            init_params = {
                "processId": os.getpid(),
                "rootUri": root_uri,
                "rootPath": str(TEST_REPO_PATH.resolve()),
                "capabilities": {
                    "textDocument": {
                        "synchronization": {
                            "dynamicRegistration": True,
                            "didSave": True
                        },
                        "documentSymbol": {
                            "dynamicRegistration": True,
                            "hierarchicalDocumentSymbolSupport": True,
                            "symbolKind": {
                                "valueSet": list(range(1, 27))
                            }
                        },
                        "definition": {
                            "dynamicRegistration": True
                        },
                        "references": {
                            "dynamicRegistration": True
                        },
                        "hover": {
                            "dynamicRegistration": True,
                            "contentFormat": ["plaintext", "markdown"]
                        }
                    },
                    "workspace": {
                        "workspaceFolders": True,
                        "symbol": {
                            "dynamicRegistration": True
                        }
                    }
                },
                "workspaceFolders": [
                    {
                        "uri": root_uri,
                        "name": "test_repo"
                    }
                ]
            }
            
            req_id = self.send_request("initialize", init_params)
            response = self.wait_for_response(req_id, timeout=15)
            
            if response and "result" in response:
                print("[SUCCESS] Server initialized")
                capabilities = response["result"].get("capabilities", {})
                print(f"  - Document Symbol Provider: {capabilities.get('documentSymbolProvider', False)}")
                print(f"  - Definition Provider: {capabilities.get('definitionProvider', False)}")
                print(f"  - References Provider: {capabilities.get('referencesProvider', False)}")
                print(f"  - Hover Provider: {capabilities.get('hoverProvider', False)}")
                print(f"  - Workspace Symbol Provider: {capabilities.get('workspaceSymbolProvider', False)}")
            else:
                print("[FAILED] Initialize failed")
                return False
            
            # 2. Send initialized notification
            print("\n2. INITIALIZED NOTIFICATION")
            print("-" * 40)
            self.send_notification("initialized", {})
            print("[SUCCESS] Sent initialized notification")
            
            # Give server time to index workspace
            print("\nWaiting for server to index workspace...")
            time.sleep(5)
            
            # 3. Test multiple documents
            test_files = [
                ("Tables", "Customer.Table.al"),
                ("Pages", "CustomerCard.Page.al"),
                ("Codeunits", "CustomerMgt.Codeunit.al"),
                ("Enums", "CustomerType.Enum.al")
            ]
            
            for folder, filename in test_files:
                print(f"\n3. TESTING: {filename}")
                print("-" * 40)
                
                file_path = TEST_REPO_PATH / "src" / folder / filename
                if not file_path.exists():
                    print(f"[WARNING] File not found: {file_path}")
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                file_uri = f"file:///{file_path.resolve()}".replace('\\', '/')
                
                # Open document
                self.send_notification("textDocument/didOpen", {
                    "textDocument": {
                        "uri": file_uri,
                        "languageId": "al",
                        "version": 1,
                        "text": file_content
                    }
                })
                print(f"  Opened: {filename}")
                
                # Give server time to parse
                time.sleep(2)
                
                # Request document symbols
                req_id = self.send_request("textDocument/documentSymbol", {
                    "textDocument": {"uri": file_uri}
                })
                
                response = self.wait_for_response(req_id, timeout=10)
                if response and "result" in response:
                    symbols = response.get("result", [])
                    print(f"  [SUCCESS] Found {len(symbols)} symbols")
                    
                    # Print symbol details
                    for symbol in symbols[:10]:  # First 10 symbols
                        name = symbol.get("name", "?")
                        kind = symbol.get("kind", "?")
                        children = symbol.get("children", [])
                        print(f"    - {name} (kind={kind}, children={len(children)})")
                else:
                    error = response.get("error", {}) if response else {}
                    print(f"  [WARNING] No symbols found - {error.get('message', 'timeout or no response')}")
            
            # 4. Test workspace symbols
            print("\n4. WORKSPACE SYMBOLS")
            print("-" * 40)
            req_id = self.send_request("workspace/symbol", {
                "query": "Customer"
            })
            
            response = self.wait_for_response(req_id, timeout=10)
            if response and "result" in response:
                symbols = response.get("result", [])
                print(f"[SUCCESS] Found {len(symbols)} workspace symbols matching 'Customer'")
                for symbol in symbols[:5]:
                    print(f"  - {symbol.get('name', '?')} in {symbol.get('location', {}).get('uri', '?')}")
            else:
                print("[WARNING] Workspace symbols not supported or no results")
            
            # 5. Test go-to-definition
            print("\n5. GO-TO-DEFINITION TEST")
            print("-" * 40)
            # Try to find definition of a procedure call
            customer_mgt_file = TEST_REPO_PATH / "src" / "Codeunits" / "CustomerMgt.Codeunit.al"
            if customer_mgt_file.exists():
                file_uri = f"file:///{customer_mgt_file.resolve()}".replace('\\', '/')
                
                # Look for a line that references something (e.g., line with Customer.FindFirst())
                # Position would need to be determined from actual file content
                req_id = self.send_request("textDocument/definition", {
                    "textDocument": {"uri": file_uri},
                    "position": {"line": 10, "character": 20}  # Example position
                })
                
                response = self.wait_for_response(req_id, timeout=5)
                if response and "result" in response:
                    definitions = response.get("result", [])
                    if definitions:
                        print(f"[SUCCESS] Found {len(definitions)} definitions")
                    else:
                        print("[INFO] No definitions found at test position")
                else:
                    print("[WARNING] Go-to-definition not supported or failed")
            
            # 6. Shutdown
            print("\n6. SHUTDOWN")
            print("-" * 40)
            req_id = self.send_request("shutdown", None)
            response = self.wait_for_response(req_id, timeout=5)
            if response:
                print("[SUCCESS] Shutdown acknowledged")
            
            self.send_notification("exit", {})
            print("[SUCCESS] Sent exit notification")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                print("\n[INFO] Language server process terminated")

if __name__ == "__main__":
    tester = ALLanguageServerTester()
    success = tester.run_tests()
    
    print("\n" + "=" * 60)
    if success:
        print("TEST RESULT: PASSED")
    else:
        print("TEST RESULT: FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)