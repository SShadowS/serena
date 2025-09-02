# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Essential Commands (use these exact commands):**
- `uv run poe format` - Format code (BLACK + RUFF) - ONLY allowed formatting command
- `uv run poe type-check` - Run mypy type checking - ONLY allowed type checking command  
- `uv run poe test` - Run tests with default markers (excludes java/rust/erlang by default)
- `uv run poe test -m "python or go"` - Run specific language tests
- `uv run poe lint` - Check code style without fixing

**Test Markers:**
Available pytest markers for selective testing:
- `python`, `go`, `java`, `rust`, `typescript`, `php`, `csharp`, `elixir`, `terraform`, `clojure`, `swift`, `bash`, `ruby`, `ruby_solargraph`, `zig`, `lua`, `nix`, `dart`, `erlang`, `kotlin`
- `snapshot` - for symbolic editing operation tests

**Project Management:**
- `uv run serena start-mcp-server` - Start MCP server from project root
- `uv run serena project index` - Index project for faster tool performance
- `uv run serena config edit` - Edit global Serena configuration
- `uv run serena project generate-yml` - Generate project configuration

**Always run format, type-check, and test before completing any task.**

## Architecture Overview

Serena is an MCP (Model Context Protocol) server providing semantic code understanding via Language Server Protocol (LSP) integration:

### Core Components

**1. SerenaAgent (`src/serena/agent.py`)**
- Central orchestrator managing projects, tools, and user interactions
- Coordinates language servers, memory persistence, and MCP server interface
- Manages tool registry and context/mode configurations
- Handles project activation and workspace management

**2. SolidLanguageServer (`src/solidlsp/ls.py`)**  
- Unified wrapper around Language Server Protocol (LSP) implementations
- Provides language-agnostic interface for symbol operations
- Handles caching, error recovery, and multiple language server lifecycle
- Factory pattern for creating language-specific server instances

**3. Tool System (`src/serena/tools/`)**
- **file_tools.py** - File system operations, search, regex replacements
- **symbol_tools.py** - Language-aware symbol finding, navigation, editing
- **memory_tools.py** - Project knowledge persistence and retrieval
- **config_tools.py** - Project activation, mode switching
- **workflow_tools.py** - Onboarding and meta-operations
- **cmd_tools.py** - Shell command execution
- **jetbrains_tools.py** - Optional JetBrains IDE integration

**4. Configuration System (`src/serena/config/`)**
- **Contexts** (`contexts/*.yml`) - Define tool sets for different environments:
  - `desktop-app` - Claude Desktop/similar apps
  - `ide-assistant` - VSCode/Cursor/Cline integration
  - `agent` - Autonomous agent operations
  - `codex` - OpenAI Codex CLI integration
- **Modes** (`modes/*.yml`) - Operational patterns:
  - `planning`, `editing`, `interactive`, `one-shot`
  - `onboarding`, `no-onboarding`
- **Projects** (`.serena/project.yml`) - Per-project settings and language server configs

### Language Support Architecture

Each supported language has:
1. **Language Server Implementation** in `src/solidlsp/language_servers/`
   - Inherits from `SolidLanguageServer` base class
   - Handles server lifecycle and LSP communication
2. **Runtime Dependencies** - Automatic language server downloads when needed
   - Some require system installation (Go, Rust, Zig, Nix, Elixir)
   - Others auto-download (C#, TypeScript, PHP, Lua)
3. **Test Repository** in `test/resources/repos/<language>/`
   - Minimal project demonstrating language features
4. **Test Suite** in `test/solidlsp/<language>/`
   - Tests symbol finding, references, cross-file operations

### Memory & Knowledge System

- **Markdown-based storage** in `.serena/memories/` directories
- **Project-specific knowledge** persistence across sessions
- **Contextual retrieval** based on relevance
- **Onboarding support** for new projects
- **Memory operations** via `memory_tools.py`:
  - `write_memory`, `read_memory`, `list_memories`, `delete_memory`

## Development Patterns

### Adding New Languages
1. Create language server class in `src/solidlsp/language_servers/`
   - Inherit from `SolidLanguageServer`
   - Implement `_get_language_server_command()`
   - Override `is_ignored_dirname()` for language-specific ignores
2. Add to `Language` enum in `src/solidlsp/ls_config.py`
   - Define file extensions in `get_source_fn_matcher()`
3. Update factory method in `src/solidlsp/ls.py`
   - Add case to `create()` method
4. Create test repository in `test/resources/repos/<language>/`
   - Include meaningful code demonstrating language features
5. Write test suite in `test/solidlsp/<language>/`
   - Test symbol finding, references, cross-file operations
6. Add pytest marker to `pyproject.toml`
7. Update README.md with language support details

### Adding New Tools
1. Inherit from `Tool` base class in `src/serena/tools/tools_base.py`
2. Implement required methods:
   - `apply()` - Tool execution logic
   - `get_name()` - Tool identifier
   - `get_description()` - MCP-exposed description
3. Use `@dataclass` for parameter definition
4. Register in `SerenaAgent` tool registry
5. Add to context/mode configurations if optional
6. Consider adding to `included_optional_tools` list

### Testing Strategy
- **Language-specific tests** use pytest markers (e.g., `@pytest.mark.python`)
- **Symbolic editing operations** have snapshot tests using `syrupy`
- **Integration tests** in `test_serena_agent.py`
- **Test repositories** provide realistic symbol structures
- **Test coverage expectations**:
  - Symbol finding (classes, functions, methods)
  - Within-file and cross-file references
  - Symbol body replacement
  - Insert before/after operations
- **Never skip tests** except for missing dependencies or OS incompatibility

## Configuration Hierarchy

Configuration is loaded from (in order of precedence):
1. Command-line arguments to `serena start-mcp-server`
2. Project-specific `.serena/project.yml`
3. User config `~/.serena/serena_config.yml`
4. Active modes and contexts

**Key configuration files:**
- `serena_config.yml` - Global settings, project list, dashboard config
- `project.yml` - Language settings, ignored paths, project name
- Context/Mode YAML - Tool inclusion/exclusion, prompt modifications

## Key Implementation Notes

- **Symbol-based editing** - Uses LSP for precise code manipulation
- **Caching strategy** - Reduces language server overhead via `ls_handler.py`
- **Error recovery** - Automatic language server restart on crashes
- **Multi-language support** - 19+ languages with LSP integration
- **MCP protocol** - Exposes tools to AI agents via Model Context Protocol
- **Async operation** - Non-blocking language server interactions
- **Process management** - Language servers run as subprocesses
- **Dashboard** - Web UI at `localhost:24282` for logs and shutdown
- **Line endings** - Uses system-native (important for git diffs on Windows)

## Working with the Codebase

- **Python version** - Requires Python 3.11 (see `requires-python` in pyproject.toml)
- **Dependency management** - Uses `uv` package manager
- **Code quality**:
  - Strict typing with mypy (`disallow_untyped_defs = true`)
  - Formatted with black (140 char line length) + ruff
  - Extensive ruff linting rules configured
- **Architecture patterns**:
  - Language servers run as separate processes with LSP communication
  - Factory pattern for language server creation
  - Dataclasses for tool parameters
  - Async/await for concurrent operations
- **File organization**:
  - `src/serena/` - Agent and MCP server implementation
  - `src/solidlsp/` - Language server abstraction layer
  - `src/interprompt/` - Prompt templating system