# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Essential Commands (use these exact commands):**
- `uv run poe format` - Format code (RUFF: `ruff check --fix` + `ruff format`) - ONLY allowed formatting command
- `uv run poe type-check` - Run `ty` type checking - ONLY allowed type checking command
- `uv run poe test` - Run tests (language tests auto-skip when their toolchain/LS is unavailable)
- `uv run poe test -m "python or go"` - Run specific language tests
- `uv run poe test -m al` - Run AL tests
- `uv run poe lint` - Check code style without fixing (`ruff format --check` + `ruff check`)

**Test Markers:**
Tests are selected by pytest marker (one per language). Common markers:
- `python`, `go`, `java`, `typescript`, `csharp`, `rust`, `php`, `ruby`, `swift`, `bash`, `al`
- `snapshot` - for symbolic editing operation tests
- Full list of markers is in `pyproject.toml` (`[tool.pytest.ini_options]`)
- Which language tests actually run is decided at collection time by `test/conftest.py`
  (`language_tests_enabled`): a language auto-skips when its compiler/language server is missing.

**Project Management:**
- `uv run serena start-mcp-server` - Start MCP server from project root
- `uv run serena project index` - Index project for faster tool performance (auto-creates `project.yml`)
- `uv run serena config edit` - Edit global Serena configuration

**Always run format, type-check, and test before completing any task.**

## Architecture Overview

Serena is a dual-layer coding agent toolkit:

### Core Components

**1. SerenaAgent (`src/serena/agent.py`)**
- Central orchestrator managing projects, tools, and user interactions
- Coordinates language servers, memory persistence, and MCP server interface
- Manages tool registry and context/mode configurations

**2. SolidLanguageServer (`src/solidlsp/ls.py`)**  
- Unified wrapper around Language Server Protocol (LSP) implementations
- Provides language-agnostic interface for symbol operations
- Handles caching, error recovery, and multiple language server lifecycle

**3. Tool System (`src/serena/tools/`)**
- **file_tools.py** - File system operations, search, regex replacements
- **symbol_tools.py** - Language-aware symbol finding, navigation, editing
- **memory_tools.py** - Project knowledge persistence and retrieval
- **config_tools.py** - Project activation, mode switching
- **workflow_tools.py** - Onboarding and meta-operations

**4. Configuration System (`src/serena/config/`)**
- **Contexts** - Define tool sets for different environments (desktop-app, agent, ide-assistant)
- **Modes** - Operational patterns (planning, editing, interactive, one-shot)
- **Projects** - Per-project settings and language server configs

### Language Support Architecture

Each supported language has:
1. **Language Server Implementation** in `src/solidlsp/language_servers/`
2. **Runtime Dependencies** - Automatic language server downloads when needed
3. **Test Repository** in `test/resources/repos/<language>/`
4. **Test Suite** in `test/solidlsp/<language>/`

### Memory & Knowledge System

- **Markdown-based storage** in `.serena/memories/` directories
- **Project-specific knowledge** persistence across sessions
- **Contextual retrieval** based on relevance
- **Onboarding support** for new projects

## Development Patterns

### Adding New Languages
1. Create language server class in `src/solidlsp/language_servers/`
2. Add to Language enum in `src/solidlsp/ls_config.py` 
3. Update factory method in `src/solidlsp/ls.py`
4. Create test repository in `test/resources/repos/<language>/`
5. Write test suite in `test/solidlsp/<language>/`
6. Add pytest marker to `pyproject.toml`

### Adding New Tools
1. Inherit from `Tool` base class in `src/serena/tools/tools_base.py`
2. Implement required methods and parameter validation
3. Register in appropriate tool registry
4. Add to context/mode configurations

### Testing Strategy
- Language-specific tests use pytest markers
- Symbolic editing operations have snapshot tests
- Integration tests in `test_serena_agent.py`
- Test repositories provide realistic symbol structures

## Configuration Hierarchy

Configuration is loaded from (in order of precedence):
1. Command-line arguments to `serena start-mcp-server`
2. Project-specific `.serena/project.yml`
3. User config `~/.serena/serena_config.yml`
4. Active modes and contexts

## Key Implementation Notes

- **Symbol-based editing** - Uses LSP for precise code manipulation
- **Caching strategy** - Reduces language server overhead
- **Error recovery** - Automatic language server restart on crashes
- **Multi-language support** - 40+ languages with LSP integration (including AL)
- **MCP protocol** - Exposes tools to AI agents via Model Context Protocol
- **Async operation** - Non-blocking language server interactions

## Working with the Codebase

- Project uses Python 3.11 with `uv` for dependency management
- Strict typing with `ty`, formatted with `ruff`
- Language servers run as separate processes with LSP communication
- Memory system enables persistent project knowledge
- Context/mode system allows workflow customization

## AL Language Server Development

When working on AL Language Server features:
- **Keep changes isolated** to AL-specific files (`al_language_server.py`, `test_al_basic.py`, etc.)
- **Avoid modifying generic Serena files** like `ls.py`, `ls_types.py`, or base classes
- If a fix seems to require changes to generic files, first explore AL-specific solutions (e.g., override methods, normalize inputs at AL layer)
- AL tests are in `test/solidlsp/al/` with marker `@pytest.mark.al`

## GitHub PR Operations

**Reading PR review comments:**
```bash
gh api repos/oraios/serena/pulls/<PR_NUMBER>/comments
```

This returns JSON with all review comments including:
- `body` - the comment text
- `path` - file path the comment is on
- `line` / `original_line` - line number
- `user.login` - who wrote it
- `in_reply_to_id` - if it's a reply to another comment