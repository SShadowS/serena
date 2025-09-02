# AL Language Server Flow Analysis

## Required Flow (from ALLSP.md)

### 1. Initialization Sequence
```json
1. Initialize with full capabilities
   - hierarchicalDocumentSymbolSupport: true
   - symbolKind valueSet: [1-26]
   - workspaceFolders support

2. Send initialized notification

3. Set active workspace (al/setActiveWorkspace)
   - workspacePath parameter required

4. Configure workspace (workspace/didChangeConfiguration)
   - AL-specific settings structure

5. Wait for project loaded (al/projectLoadedStatusChanged)
```

### 2. File Opening Pattern
```json
1. Send textDocument/didOpen with:
   - uri: file:///path/to/file.al
   - languageId: "al"
   - version: 1
   - text: <FULL FILE CONTENT>

2. Wait for processing

3. Request textDocument/documentSymbol
   - textDocument.uri must match opened file

4. Receive actual AL symbols (not just file symbols)

5. Send textDocument/didClose (optional cleanup)
```

## Current Implementation Analysis

### ✅ What We're Doing Right

1. **ALLanguageServer._get_initialize_params()**
   - Comprehensive capabilities including hierarchicalDocumentSymbolSupport
   - WorkspaceFolders configuration
   - Full symbolKind valueSet [1-26]

2. **ALLanguageServer._post_initialize_al_workspace()**
   - Sends workspace/didChangeConfiguration
   - Attempts al/setActiveWorkspace
   - Opens app.json
   - Waits for project loading

3. **File Content in didOpen**
   - Both request_document_symbols() and request_full_symbol_tree() read file content
   - Include content in textDocument/didOpen

### ❌ Potential Issues

1. **URI Format Consistency**
   - We use `file_path.as_uri()` which creates `file:///C:/path` on Windows
   - Parent method might use different URI format
   - Need to ensure URI in didOpen matches URI in documentSymbol request

2. **Timing Issues**
   - We wait 0.1s after didOpen, but AL server might need more time
   - Project loading might not be complete even after waiting

3. **Parent Method Call**
   - After opening file, we call `super().request_document_symbols()`
   - Parent might not use the same URI we opened
   - Parent might send its own didOpen with different content/version

4. **Missing Workspace Setup**
   - AL server might require actual .alpackages or dependencies
   - May need specific project structure beyond just app.json

## Critical Gap: URI Mismatch

The most likely issue is **URI format mismatch**:

```python
# In our override:
file_uri = file_path.as_uri()  # Creates: file:///C:/Users/.../file.al

# Parent method might use:
# - Different path separators
# - Different URI encoding
# - Relative vs absolute paths
```

## Debugging Steps

1. **Log Exact URIs**
   - Log URI sent in didOpen
   - Log URI parent method uses for documentSymbol
   - Compare for exact match

2. **Monitor LSP Traffic**
   - Enable verbose LSP logging
   - Check exact messages sent/received
   - Verify server acknowledgments

3. **Test Manual Symbol Request**
   - After didOpen, manually send documentSymbol with exact same URI
   - Skip parent method to eliminate variables

## Recommended Fixes

### Fix 1: Direct LSP Request (Skip Parent)
```python
def request_document_symbols(self, relative_file_path: str, include_body: bool = False):
    # Open file with content
    file_uri = abs_path.as_uri()
    self.lsp_client.didOpen({...})
    
    # Direct LSP request instead of super()
    response = self.lsp_client.request(
        "textDocument/documentSymbol",
        {"textDocument": {"uri": file_uri}}
    )
    
    # Process response ourselves
    return self._process_symbols(response)
```

### Fix 2: Override URI Resolution
```python
def _get_file_uri(self, relative_path: str) -> str:
    """Ensure consistent URI format."""
    abs_path = Path(self.repository_root_path) / relative_path
    # Normalize path and create URI
    uri = abs_path.resolve().as_uri()
    return uri.replace('\\', '/')  # Ensure forward slashes
```

### Fix 3: Extended Wait Time
```python
# After didOpen, wait longer for indexing
time.sleep(1.0)  # Instead of 0.1
```

### Fix 4: Verify File Recognition
```python
# After didOpen, check if server recognized the file
diagnostics = self.lsp_client.get_diagnostics(file_uri)
if diagnostics is not None:
    # Server processed the file
    proceed with symbol request
```

## Next Steps

1. **Implement direct LSP request** - Bypass parent method to control exact request format
2. **Add comprehensive logging** - Log all URIs and responses
3. **Test with simple AL file** - Use minimal file to reduce variables
4. **Monitor server logs** - Check AL server's own logs for errors
5. **Try alternative approaches** - Such as workspace/symbol instead of textDocument/documentSymbol

## Conclusion

The core issue appears to be that while we're following the general pattern from ALLSP.md, there's likely a mismatch in the exact URI format or timing between our didOpen and the symbol request. The AL server is very particular about the exact format and sequence, and even small discrepancies can cause it to return empty results.