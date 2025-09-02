# AL Language Server Custom Commands Implementation Guide

## Overview
This document provides detailed implementation guidance for each AL-specific LSP command discovered during investigation.

## Architecture Analysis

### Current Request Flow
1. **SolidLanguageServer** → calls `_send_definition_request()` 
2. **LanguageServerRequest** → calls `definition()` method
3. **SolidLanguageServerHandler** → calls `send_request("textDocument/definition", params)`
4. **LSP Protocol** → sends standard LSP request to server

### Required Modifications for Custom Commands
To support AL's custom commands, we need to:
1. Override methods in `ALLanguageServer` class
2. Add custom request methods to send AL-specific commands
3. Handle custom responses appropriately

## Custom Command Implementations

### 1. al/gotodefinition - Custom Go-To Definition

**Current Issue**: AL server returns `definitionProvider: false` and doesn't respond to standard `textDocument/definition`

**Implementation**:
```python
# In ALLanguageServer class
def _send_definition_request(self, definition_params: DefinitionParams) -> Definition | list[LocationLink] | None:
    """Override to use AL's custom gotodefinition command"""
    # Convert standard params to AL format
    al_params = {
        "textDocument": definition_params["textDocument"],
        "position": definition_params["position"]
    }
    
    # Use custom AL command instead of standard LSP
    return self.handler.send_request("al/gotodefinition", al_params)

def request_definition(self, relative_file_path: str, line: int, column: int) -> list[ls_types.Location]:
    """Override the parent's request_definition to use AL's custom method"""
    # Ensure file is open first (AL requirement)
    with self.open_file(relative_file_path):
        # Call parent implementation which will use our overridden _send_definition_request
        return super().request_definition(relative_file_path, line, column)
```

**Testing**: Verify go-to-definition works with AL objects like tables, pages, codeunits

### 2. al/hasProjectClosureLoadedRequest - Project Load Status

**Purpose**: Check if AL project dependencies and symbols are fully loaded

**Implementation**:
```python
def check_project_loaded(self) -> bool:
    """Check if AL project closure is fully loaded"""
    try:
        response = self.handler.send_request("al/hasProjectClosureLoadedRequest", {})
        return response.get("loaded", False) if isinstance(response, dict) else False
    except Exception as e:
        self.logger.log(f"Failed to check project load status: {e}", logging.WARNING)
        return False

def _wait_for_project_load(self, timeout: int = 30) -> bool:
    """Wait for project to be fully loaded"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if self.check_project_loaded():
            self.logger.log("AL project fully loaded", logging.INFO)
            return True
        time.sleep(0.5)
    
    self.logger.log("Timeout waiting for AL project to load", logging.WARNING)
    return False

# Add to _post_initialize_al_workspace()
def _post_initialize_al_workspace(self):
    # ... existing code ...
    
    # Wait for project to be loaded before proceeding
    if not self._wait_for_project_load():
        self.logger.log("Proceeding despite project not fully loaded", logging.WARNING)
    
    # ... rest of initialization ...
```

### 3. al/setActiveWorkspace - Workspace Management

**Purpose**: Set the active workspace when multiple workspaces exist

**Implementation**:
```python
def set_active_workspace(self, workspace_uri: str | None = None) -> None:
    """Set the active AL workspace"""
    if workspace_uri is None:
        workspace_uri = Path(self.repository_root_path).resolve().as_uri()
    
    params = {
        "workspaceUri": workspace_uri
    }
    
    try:
        self.handler.send_request("al/setActiveWorkspace", params)
        self.logger.log(f"Set active workspace to: {workspace_uri}", logging.INFO)
    except Exception as e:
        self.logger.log(f"Failed to set active workspace: {e}", logging.WARNING)

# Add to start() method
def start(self) -> None:
    super().start()
    # Set this workspace as active after starting
    self.set_active_workspace()
```

### 4. al/activeProjectLoaded - Project Load Notification

**Purpose**: Notification sent when project is fully loaded (no response expected)

**Implementation**:
```python
def _handle_active_project_loaded(self, params: dict) -> None:
    """Handle notification that active project has loaded"""
    self.logger.log("Received activeProjectLoaded notification", logging.INFO)
    self._project_loaded = True
    
    # Trigger any pending operations waiting for project load
    if hasattr(self, '_pending_on_load'):
        for callback in self._pending_on_load:
            try:
                callback()
            except Exception as e:
                self.logger.log(f"Error in project load callback: {e}", logging.ERROR)
        self._pending_on_load.clear()

# Register notification handler in __init__
def __init__(self, ...):
    super().__init__(...)
    self._project_loaded = False
    self._pending_on_load = []
    # Note: Would need to extend handler to support custom notifications
```

### 5. al/didChangeActiveDocument - Document Tracking

**Purpose**: Notify AL server when active document changes for optimization

**Implementation**:
```python
def notify_active_document_changed(self, file_path: str) -> None:
    """Notify AL server that active document has changed"""
    absolute_path = Path(self.repository_root_path) / file_path
    document_uri = absolute_path.resolve().as_uri()
    
    params = {
        "textDocument": {
            "uri": document_uri
        }
    }
    
    try:
        # This is a notification, not a request (no response expected)
        self.handler.send_notification("al/didChangeActiveDocument", params)
        self._active_document = file_path
    except Exception as e:
        self.logger.log(f"Failed to notify active document change: {e}", logging.WARNING)

# Override open_file to track active document
@contextmanager
def open_file(self, relative_file_path: str):
    """Override to notify AL of active document changes"""
    with super().open_file(relative_file_path):
        # Notify AL that this is now the active document
        self.notify_active_document_changed(relative_file_path)
        yield
```

### 6. al/refreshExplorerObjects - Object Explorer Refresh

**Purpose**: Trigger refresh of AL Object Explorer (VS Code specific)

**Implementation**:
```python
def refresh_explorer_objects(self) -> None:
    """Request refresh of AL Object Explorer"""
    try:
        self.handler.send_request("al/refreshExplorerObjects", {})
        self.logger.log("Triggered AL Object Explorer refresh", logging.DEBUG)
    except Exception as e:
        self.logger.log(f"Failed to refresh explorer objects: {e}", logging.WARNING)
        # Non-critical, as this is mainly for VS Code UI

# Call after operations that change object structure
def after_symbolic_edit(self):
    """Hook called after symbolic edits"""
    self.refresh_explorer_objects()
```

### 7. al/progressNotification - Progress Tracking

**Purpose**: Receive progress updates for long-running operations

**Implementation**:
```python
def _handle_progress_notification(self, params: dict) -> None:
    """Handle AL progress notifications"""
    operation = params.get("operation", "Unknown")
    progress = params.get("progress", 0)
    message = params.get("message", "")
    
    self.logger.log(
        f"AL Progress: {operation} - {progress}% - {message}", 
        logging.INFO
    )
    
    # Store for status queries
    if not hasattr(self, '_operation_progress'):
        self._operation_progress = {}
    
    self._operation_progress[operation] = {
        "progress": progress,
        "message": message,
        "timestamp": time.time()
    }
    
    # Clean up completed operations
    if progress >= 100:
        self._operation_progress.pop(operation, None)

def get_operation_progress(self, operation: str = None) -> dict:
    """Get progress of AL operations"""
    if not hasattr(self, '_operation_progress'):
        return {}
    
    if operation:
        return self._operation_progress.get(operation, {})
    return self._operation_progress.copy()
```

## Integration Requirements

### 1. Extend LSP Handler
The `SolidLanguageServerHandler` needs extensions to support:
- Custom request methods (already supports via `send_request`)
- Custom notification sending (needs `send_notification` method)
- Custom notification handling (needs callback registration)

### 2. Add Notification Support
```python
# In SolidLanguageServerHandler
def send_notification(self, method: str, params: dict | None = None) -> None:
    """Send a notification to the language server (no response expected)"""
    self._send_payload(make_notification(method, params))
    self._log(f"Sent notification: {method}")

def register_notification_handler(self, method: str, handler: Callable) -> None:
    """Register handler for custom notifications from server"""
    if not hasattr(self, '_custom_notification_handlers'):
        self._custom_notification_handlers = {}
    self._custom_notification_handlers[method] = handler
```

### 3. Testing Strategy

**Unit Tests**:
- Mock AL server responses for each custom command
- Verify parameter transformation
- Test error handling

**Integration Tests**:
```python
@pytest.mark.al
def test_al_custom_gotodefinition():
    """Test AL's custom go-to-definition"""
    server = create_al_server()
    server.start()
    
    # Test go-to on table reference
    location = server.request_definition("CustomerMgt.al", 10, 15)
    assert location[0]["relativePath"] == "Customer.Table.al"

@pytest.mark.al  
def test_al_project_load_status():
    """Test project load checking"""
    server = create_al_server()
    server.start()
    
    # Should eventually report loaded
    assert server._wait_for_project_load(timeout=60)
    assert server.check_project_loaded()
```

## Phase 1 Implementation Status

### COMPLETED ✅
1. **`al/gotodefinition`** - Implemented as override of `_send_definition_request()`
   - Uses AL's custom command with fallback to standard LSP
   - Working with all existing tests

2. **`al/hasProjectClosureLoadedRequest`** - Implemented project load checking
   - `check_project_loaded()` method checks server status
   - `_wait_for_project_load()` waits for full initialization
   - Integrated into `_post_initialize_al_workspace()`

3. **`al/setActiveWorkspace`** - Implemented workspace management
   - `set_active_workspace()` method with server status checks
   - **NOTE**: Removed automatic call from `start()` method due to potential initialization issues
   - **IMPORTANT**: May need to revert this change and call it manually for multi-workspace scenarios

### Known Issues from Phase 1:
- **setActiveWorkspace timing**: Automatic workspace setting during start() caused hanging tests
  - Current: Only manual calls to `set_active_workspace()`
  - May need: Delayed automatic call after full initialization

## Implementation Priority

1. **High Priority** (Required for basic functionality):
   - ✅ `al/gotodefinition` - Essential for navigation - COMPLETED
   - ✅ `al/hasProjectClosureLoadedRequest` - Required for reliable operations - COMPLETED  
   - ⚠️ `al/setActiveWorkspace` - Needed for multi-workspace scenarios - COMPLETED (with timing notes)

2. **Medium Priority** (Enhances reliability):
   - `al/didChangeActiveDocument` - Improves performance
   - `al/activeProjectLoaded` - Better initialization handling

3. **Low Priority** (Nice to have):
   - `al/refreshExplorerObjects` - UI-specific
   - `al/progressNotification` - User feedback

## Migration Path

### Phase 1: Basic Custom Commands (Current)
- Implement `al/gotodefinition` override
- Add project load checking
- Test with existing test suite

### Phase 2: Enhanced Integration
- Add notification support to handler
- Implement active document tracking
- Add progress notifications

### Phase 3: Full Feature Parity
- Complete all custom commands
- Add comprehensive error handling
- Performance optimizations

## Error Handling Considerations

1. **Graceful Fallback**: If custom command fails, try standard LSP equivalent
2. **Timeout Handling**: Custom commands may have different timeout requirements
3. **Version Compatibility**: Some commands may not exist in older AL versions
4. **Error Recovery**: Automatic retry with exponential backoff for transient failures

## Performance Optimizations

1. **Caching**: Cache project load status to avoid repeated checks
2. **Batching**: Batch multiple operations when possible
3. **Lazy Loading**: Only send `didChangeActiveDocument` when necessary
4. **Background Operations**: Use threading for non-critical notifications

## Conclusion

Implementing AL's custom commands requires:
1. Method overrides in `ALLanguageServer` class
2. Extensions to the LSP handler for notifications
3. Careful error handling and fallback strategies
4. Comprehensive testing of each custom command

The implementation can be done incrementally, starting with the most critical commands (`al/gotodefinition` and project loading) and gradually adding the remaining features.