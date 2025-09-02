#!/usr/bin/env python
"""Diagnostic test for AL Language Server."""
import os
import sys
import subprocess
import threading
from pathlib import Path

AL_EXTENSION_PATH = Path("ms-dynamics-smb.al-16.0.1743592")
TEST_REPO_PATH = Path("test/resources/repos/al/test_repo")

def read_output(pipe, name):
    """Read output from a pipe."""
    try:
        for line in iter(pipe.readline, b''):
            if line:
                print(f"[{name}] {line.decode('utf-8', errors='replace').rstrip()}")
    except Exception as e:
        print(f"[{name} ERROR] {e}")

def test_server_startup():
    """Test if the AL Language Server starts properly."""
    os.environ["AL_EXTENSION_PATH"] = str(AL_EXTENSION_PATH.resolve())
    
    if sys.platform == "win32":
        lsp_exe = AL_EXTENSION_PATH / "bin" / "win32" / "Microsoft.Dynamics.Nav.EditorServices.Host.exe"
    else:
        print(f"Platform {sys.platform} not supported")
        return False
    
    if not lsp_exe.exists():
        print(f"LSP executable not found: {lsp_exe}")
        return False
    
    print(f"Starting: {lsp_exe}")
    print(f"Working directory: {TEST_REPO_PATH.resolve()}")
    print(f"AL Extension: {AL_EXTENSION_PATH.resolve()}")
    print("-" * 60)
    
    # Try starting with --help first
    print("\n1. Testing with --help flag:")
    try:
        result = subprocess.run(
            [str(lsp_exe), "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(TEST_REPO_PATH.resolve())
        )
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("Help command timed out")
    except Exception as e:
        print(f"Error running help: {e}")
    
    print("\n2. Testing normal startup (will run for 5 seconds):")
    
    # Start the server normally
    process = subprocess.Popen(
        [str(lsp_exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(TEST_REPO_PATH.resolve())
    )
    
    # Create threads to read stdout and stderr
    stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "STDOUT"))
    stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "STDERR"))
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    
    stdout_thread.start()
    stderr_thread.start()
    
    # Wait for a bit
    import time
    time.sleep(5)
    
    print("\n3. Terminating server...")
    process.terminate()
    
    try:
        process.wait(timeout=5)
        print(f"Process terminated with code: {process.returncode}")
    except subprocess.TimeoutExpired:
        print("Process didn't terminate, killing...")
        process.kill()
    
    return True

if __name__ == "__main__":
    print("AL Language Server Diagnostic")
    print("=" * 60)
    test_server_startup()