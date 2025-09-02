# AL Language Server Custom LSP Commands

This document captures the custom LSP commands used by the AL Language Server that extend beyond the standard Language Server Protocol specification.

## Discovery Source
These commands were discovered through analyzing VS Code LSP traces during AL development sessions.

## Custom Commands

### Navigation Commands

#### `al/gotodefinition`
- **Purpose**: Custom go-to-definition implementation
- **Replaces**: Standard `textDocument/definition`
- **Note**: AL server sets `definitionProvider: false` in capabilities and uses this custom method instead
- **Request Format**:
```json
{
  "textDocument": {
    "uri": "file:///path/to/file.al"
  },
  "position": {
    "line": 11,
    "character": 34
  }
}
```
- **Response**: Returns location(s) for the definition

### Project Management Commands

#### `al/hasProjectClosureLoadedRequest`
- **Purpose**: Checks if the AL project closure has been fully loaded
- **Usage**: Called during initialization to verify project readiness
- **Response**: Boolean indicating load status

#### `al/setActiveWorkspace`
- **Purpose**: Sets the active workspace for the AL Language Server
- **Parameters**: Workspace URI
- **Usage**: Called when switching between workspaces or projects

#### `al/activeProjectLoaded`
- **Type**: Notification (no response expected)
- **Purpose**: Indicates that the active project has been fully loaded
- **Usage**: Sent after project initialization completes

### Document Tracking Commands

#### `al/didChangeActiveDocument`
- **Type**: Notification
- **Purpose**: Notifies the server when the active document changes in the editor
- **Parameters**: Document URI of the newly active document
- **Usage**: Helps AL server track focus and optimize operations for the active file

### UI Integration Commands

#### `al/refreshExplorerObjects`
- **Purpose**: Triggers a refresh of the AL Object Explorer
- **Usage**: Called after changes that affect the object tree structure
- **Note**: Specific to AL extension's object explorer feature

### Progress Tracking

#### `al/progressNotification`
- **Type**: Notification
- **Purpose**: Provides progress updates for long-running operations
- **Parameters**: Progress details including operation name and completion percentage
- **Usage**: Used for operations like compilation, publishing, downloading symbols

## Implementation Considerations

When integrating AL Language Server with tools like Serena, consider:

1. **Go-To-Definition**: Must use `al/gotodefinition` instead of standard LSP method
2. **Project Loading**: Should check `al/hasProjectClosureLoadedRequest` before performing operations
3. **Active Document**: Consider sending `al/didChangeActiveDocument` when switching files programmatically
4. **Workspace Management**: May need to call `al/setActiveWorkspace` when working with multiple AL projects

## Standard LSP Methods Still Used

Despite custom commands, AL still uses many standard LSP methods:
- `textDocument/didOpen`
- `textDocument/didChange` 
- `textDocument/didSave`
- `textDocument/documentSymbol`
- `textDocument/references`
- `textDocument/hover`
- `textDocument/signatureHelp`
- `textDocument/completion`
- `textDocument/codeLens`
- `textDocument/semanticTokens`
- `textDocument/inlayHint`
- `textDocument/documentHighlight`
- `workspace/didChangeConfiguration`

## Notes

- AL's approach of using custom commands alongside standard LSP creates a hybrid protocol
- This may be due to AL's specific requirements for Business Central development
- Future versions might migrate more features to standard LSP methods
- When standard methods return unexpected results (like `definitionProvider: false`), check for custom alternatives

## References

- VS Code AL Language Extension
- Microsoft Dynamics 365 Business Central
- Language Server Protocol Specification