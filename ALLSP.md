# AL Language Server Integration for Serena

## Investigation Summary

This document contains the findings from investigating the Microsoft AL Language extension for adding AL language support to Serena.

## AL Language Overview

AL is the programming language for Microsoft Dynamics 365 Business Central development. It's used for creating business logic, data structures, and UI components in the Business Central ERP system.

### Key Language Features
- **Object-oriented** with codeunits, tables, pages, reports
- **Strong typing** with built-in types and custom enums
- **Extension-based** development model
- **Event-driven** architecture with publishers and subscribers
- **Built-in database integration**

## Available Resources

### 1. Language Server Executable

The VS Code extension (`ms-dynamics-smb.al-16.0.1743592`) contains platform-specific AL Language Server executables:

**Windows:**
- Path: `ms-dynamics-smb.al-16.0.1743592/bin/win32/Microsoft.Dynamics.Nav.EditorServices.Host.exe`
- Supporting DLLs and configuration files included

**Linux:**
- Path: `ms-dynamics-smb.al-16.0.1743592/bin/linux/Microsoft.Dynamics.Nav.EditorServices.Host`
- Native Linux binary with dependencies

**macOS (Darwin):**
- Path: `ms-dynamics-smb.al-16.0.1743592/bin/darwin/Microsoft.Dynamics.Nav.EditorServices.Host`
- Native macOS binary with dependencies

### 2. Supporting Tools

The extension includes additional AL development tools:

- **alc** - AL Compiler
  - `alc.exe` (Windows) / `alc` (Linux/macOS)
  - Compiles AL code to .app packages
  
- **aldoc** - AL Documentation Generator
  - `aldoc.exe` (Windows) / `aldoc` (Linux/macOS)
  - Generates documentation from AL code
  
- **altool** - AL Development Tool
  - `altool.exe` (Windows) / `altool` (Linux/macOS)
  - Various AL development utilities

### 3. Language Configuration

From `package.json` analysis:

```json
{
  "languages": [{
    "id": "al",
    "extensions": [".al", ".dal"],
    "aliases": ["AL"],
    "configuration": "./al.configuration.json",
    "semanticHighlighting": true
  }]
}
```

**File Extensions:** `.al`, `.dal`
**Language ID:** `al`
**Features:** Semantic highlighting, snippets, debugging, formatting

### 4. AL Language Constructs

Based on snippets and templates found:

- **Tables** - Data structures with fields and keys
- **Pages** - UI components (Card, List, Document)
- **Codeunits** - Business logic containers
- **Reports** - Data processing and output
- **Queries** - Data retrieval definitions
- **Enums** - Enumeration types
- **Interfaces** - Contract definitions
- **Control Add-ins** - Custom UI controls
- **Entitlements** - Permission definitions
- **Profiles** - Role configurations
- **XMLPorts** - Data import/export definitions
- **Table/Page/Report Extensions** - Extending existing objects

## Implementation Plan for Serena

### 1. Create AL Language Server Class

Create `src/solidlsp/language_servers/al_language_server.py`:

```python
import os
import platform
import shutil
from pathlib import Path
from typing import override

from solidlsp.ls import SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig
from solidlsp.ls_logger import LanguageServerLogger
from solidlsp.lsp_protocol_handler.server import ProcessLaunchInfo


class ALLanguageServer(SolidLanguageServer):
    """
    Language server implementation for AL (Microsoft Dynamics 365 Business Central).
    """
    
    def __init__(self, config: LanguageServerConfig, logger: LanguageServerLogger, repository_root_path: str):
        cmd = self._get_language_server_command(logger)
        
        super().__init__(
            config,
            logger,
            repository_root_path,
            ProcessLaunchInfo(cmd=cmd, cwd=repository_root_path),
            "al",  # Language ID for LSP
        )
    
    def _get_language_server_command(self, logger: LanguageServerLogger) -> list[str]:
        """Get the command to start the AL language server."""
        # Check if AL extension path is configured
        al_extension_path = os.environ.get("AL_EXTENSION_PATH")
        
        if not al_extension_path:
            # Try to find the extension in common locations
            al_extension_path = self._find_al_extension()
        
        if not al_extension_path:
            raise RuntimeError(
                "AL Language Server not found. Please set AL_EXTENSION_PATH environment variable "
                "to the VS Code AL extension directory (ms-dynamics-smb.al-*)"
            )
        
        # Determine platform-specific executable
        system = platform.system()
        if system == "Windows":
            executable = os.path.join(al_extension_path, "bin", "win32", "Microsoft.Dynamics.Nav.EditorServices.Host.exe")
        elif system == "Linux":
            executable = os.path.join(al_extension_path, "bin", "linux", "Microsoft.Dynamics.Nav.EditorServices.Host")
        elif system == "Darwin":
            executable = os.path.join(al_extension_path, "bin", "darwin", "Microsoft.Dynamics.Nav.EditorServices.Host")
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
        
        if not os.path.exists(executable):
            raise RuntimeError(f"AL Language Server executable not found at: {executable}")
        
        # The AL Language Server uses stdio for communication
        return [executable, "--stdio"]
    
    def _find_al_extension(self) -> str | None:
        """Try to find AL extension in common VS Code extension locations."""
        # Common VS Code extension paths
        home = Path.home()
        possible_paths = [
            home / ".vscode" / "extensions",
            home / ".vscode-server" / "extensions",
            home / ".vscode-insiders" / "extensions",
        ]
        
        if platform.system() == "Windows":
            possible_paths.extend([
                Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "extensions",
                Path(os.environ.get("APPDATA", "")) / "Code - Insiders" / "User" / "extensions",
            ])
        
        for base_path in possible_paths:
            if base_path.exists():
                # Look for AL extension directories
                for item in base_path.iterdir():
                    if item.is_dir() and item.name.startswith("ms-dynamics-smb.al-"):
                        return str(item)
        
        return None
    
    @override
    def is_ignored_dirname(self, dirname: str) -> bool:
        """Define AL-specific directories to ignore."""
        al_ignore = {
            ".alpackages",  # AL package cache
            ".alcache",     # AL compiler cache
            ".altemplates", # AL templates
            ".snapshots",   # Test snapshots
            "out",          # Compiled output
            ".vscode",      # VS Code settings
        }
        return super().is_ignored_dirname(dirname) or dirname in al_ignore
```

### 2. Register AL Language

Update `src/solidlsp/ls_config.py`:

```python
class Language(str, Enum):
    # ... existing languages ...
    AL = "al"
    
    def get_source_fn_matcher(self) -> FilenameMatcher:
        match self:
            # ... existing cases ...
            case self.AL:
                return FilenameMatcher("*.al", "*.dal")
```

### 3. Update Language Server Factory

In `src/solidlsp/ls.py`:

```python
@classmethod
def create(cls, config: LanguageServerConfig, logger: LanguageServerLogger, repository_root_path: str) -> "SolidLanguageServer":
    match config.code_language:
        # ... existing cases ...
        case Language.AL:
            from solidlsp.language_servers.al_language_server import ALLanguageServer
            return ALLanguageServer(config, logger, repository_root_path)
```

### 4. Test Repository Structure

Create test repository at `test/resources/repos/al/test_repo/`:

```
test/resources/repos/al/test_repo/
├── app.json                           # Project configuration
├── .gitignore                        # Ignore build artifacts
├── src/
│   ├── Tables/
│   │   └── Customer.Table.al        # Customer table definition
│   ├── Pages/
│   │   ├── CustomerCard.Page.al     # Customer card page
│   │   └── CustomerList.Page.al     # Customer list page
│   ├── Codeunits/
│   │   ├── CustomerMgt.Codeunit.al  # Customer management logic
│   │   └── SalesCalc.Codeunit.al    # Sales calculations
│   ├── Enums/
│   │   └── CustomerType.Enum.al     # Customer type enumeration
│   ├── Interfaces/
│   │   └── IPaymentProcessor.al     # Payment processor interface
│   └── TableExtensions/
│       └── ItemExt.TableExt.al      # Item table extension
```

### 5. Test Suite Requirements

Create `test/solidlsp/al/test_al_basic.py` with tests for:

1. **Symbol Finding:**
   - Tables, fields, keys
   - Pages, actions, controls
   - Codeunits, procedures, triggers
   - Enums, interfaces

2. **Reference Finding:**
   - Table field references in pages
   - Procedure calls across codeunits
   - Enum value usage
   - Interface implementations

3. **Cross-file Operations:**
   - Table references in pages
   - Codeunit calls from other codeunits
   - Shared enum usage

4. **Symbol Manipulation:**
   - Replace procedure body
   - Insert new procedures
   - Add fields to tables

### 6. Configuration Considerations

#### Environment Variables
- `AL_EXTENSION_PATH` - Path to VS Code AL extension directory

#### Project Configuration (app.json)
```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "name": "Test AL Project",
  "publisher": "Test Publisher",
  "version": "1.0.0.0",
  "runtime": "12.0",
  "target": "Cloud"
}
```

### 7. Dependencies and Requirements

- **VS Code AL Extension** must be installed
- **.NET Runtime** (included in extension)
- **Business Central license** (for full functionality, not required for LSP)

## AL Language Server Operational Model

### Key Differences from Other Language Servers

The AL Language Server has a unique operational model that differs from most other language servers:

1. **Explicit File Opening Required**
   - Files MUST be opened via `textDocument/didOpen` notification before requesting symbols
   - Without opening files first, symbol requests return only directory/namespace symbols
   - This is different from servers like TypeScript/Python that can provide symbols without file opening

2. **Initialization Sequence**
   - Standard LSP initialize/initialized handshake
   - AL-specific `al/setActiveWorkspace` request to set the active project
   - Workspace configuration via `workspace/didChangeConfiguration`
   - Wait for `al/projectLoadedStatusChanged` notification indicating project is ready

3. **Symbol Discovery Pattern**
   ```
   1. Send textDocument/didOpen for target file
   2. Request textDocument/documentSymbol for that file
   3. Receive detailed symbol tree including all AL constructs
   4. Send textDocument/didClose when done with file
   ```

4. **Workspace Symbol Limitations**
   - `workspace/symbol` returns limited results without file opening
   - Full symbol tree discovery requires opening each file individually
   - The `.alcache` directory contains indexed symbols but LSP doesn't expose them directly

### Working VS Code Initialization Example

From VS Code trace analysis, the proper initialization sequence is:

```json
// 1. Initialize request with full capabilities
{
  "method": "initialize",
  "params": {
    "capabilities": {
      "textDocument": {
        "documentSymbol": {
          "hierarchicalDocumentSymbolSupport": true,
          "symbolKind": {"valueSet": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]}
        }
      }
    }
  }
}

// 2. Initialized notification
{"method": "initialized"}

// 3. Set active workspace (AL-specific)
{
  "method": "al/setActiveWorkspace",
  "params": {"workspacePath": "/path/to/project"}
}

// 4. Configure workspace
{
  "method": "workspace/didChangeConfiguration",
  "params": {
    "settings": {
      "al": {
        "enableCodeAnalysis": false,
        "codeAnalyzers": [],
        "backgroundCodeAnalysis": false
      }
    }
  }
}

// 5. Open file before requesting symbols
{
  "method": "textDocument/didOpen",
  "params": {
    "textDocument": {
      "uri": "file:///path/to/file.al",
      "languageId": "al",
      "version": 1,
      "text": "... file content ..."
    }
  }
}

// 6. Now can request symbols
{
  "method": "textDocument/documentSymbol",
  "params": {"textDocument": {"uri": "file:///path/to/file.al"}}
}
```

### Symbol Response Example

When files are properly opened, AL Language Server returns detailed symbols:

```json
{
  "name": "Codeunit 50001 PaymentProcessorImpl",
  "kind": 5,  // Class
  "range": {...},
  "children": [
    {
      "name": "ProcessPayment(Customer: Record 50000 \"TEST Customer\"): Boolean",
      "kind": 12,  // Function
      "detail": "procedure"
    }
  ]
}
```

## Known Challenges

1. **License Requirements:** Some AL Language Server features may require Business Central license
2. **Version Compatibility:** Different BC versions may require different AL extension versions
3. **Extension Path Discovery:** Need robust method to locate VS Code extension
4. **Platform-specific Binaries:** Must handle Windows, Linux, macOS separately
5. **File Opening Requirement:** AL Language Server requires files to be explicitly opened via `textDocument/didOpen` before providing symbols
6. **Workspace Initialization:** AL requires specific initialization sequence with `al/setActiveWorkspace` and workspace configuration

## Implementation Implications for Serena

### Required Adaptations

1. **Override `request_full_symbol_tree()` in ALLanguageServer**
   - Must open each file before requesting symbols
   - Iterate through all `.al` files in the repository
   - Send `textDocument/didOpen` for each file
   - Request `textDocument/documentSymbol` for each opened file
   - Aggregate results into unified symbol tree
   - Close files after symbol extraction

2. **Implement AL-specific initialization in `_start_server()`**
   - Send standard initialize/initialized
   - Send `al/setActiveWorkspace` with repository path
   - Send `workspace/didChangeConfiguration` with AL settings
   - Wait for `al/projectLoadedStatusChanged` or timeout

3. **Handle file content in `textDocument/didOpen`**
   - AL server requires actual file content in didOpen notification
   - Read file content before sending didOpen
   - Include proper languageId ("al") and version

4. **Test Framework Adjustments**
   - Tests must open files before requesting symbols
   - Cannot rely on workspace-level symbol discovery alone
   - Need to verify symbols are returned after file opening

## Next Steps

1. Implement `ALLanguageServer` class with proper file opening logic
2. Override `request_full_symbol_tree()` to handle AL's requirements
3. Add AL-specific initialization sequence
4. Create comprehensive test repository with AL code samples
5. Write test suite that opens files before symbol requests
6. Add pytest marker for AL tests
7. Update documentation (README.md, CHANGELOG.md)
8. Test on all supported platforms
9. Consider auto-download mechanism for AL extension

## References

- [AL Language Documentation](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/developer/devenv-dev-overview)
- [AL Language Extension GitHub](https://github.com/microsoft/al)
- [VS Code AL Extension](https://marketplace.visualstudio.com/items?itemName=ms-dynamics-smb.al)