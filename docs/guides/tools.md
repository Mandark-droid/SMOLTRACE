# Agent Tools

SMOLTRACE ships a set of custom tools that are always available, plus a large catalog of optional production-ready tools you can enable per run with `--enable-tools` (space-separated).

## Default Tools (always available)

| Tool | Class | Description |
|------|-------|-------------|
| `get_weather` | WeatherTool | Weather lookups (custom) |
| `calculator` | CalculatorTool | Arithmetic and math (custom) |
| `get_current_time` | TimeTool | Current time (custom) |

## Enabling Optional Tools

```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools google_search visit_webpage \
  --search-provider serper \
  --agent-type tool \
  --enable-otel
```

Use `--working-directory` to restrict file, text, and system tools to a specific directory (defaults to the current directory).

## Web & Research Tools

| Tool | Description |
|------|-------------|
| `google_search` | GoogleSearchTool with configurable providers (Serper, Brave, DuckDuckGo). Requires an API key for `serper`/`brave`, or use `duckduckgo`. |
| `duckduckgo_search` | DuckDuckGoSearchTool (official smolagents version). |
| `visit_webpage` | VisitWebpageTool — extract and read web page content. |
| `wikipedia_search` | WikipediaSearchTool (requires `pip install wikipedia-api`). |

Select the search backend for `google_search` with `--search-provider` (`serper`, `brave`, or `duckduckgo`; default `duckduckgo`). For `serper`, set `SERPER_API_KEY`.

## Code & Computation

| Tool | Description |
|------|-------------|
| `python_interpreter` | PythonInterpreterTool — safe Python code execution. |

## File System Tools (Phase 1)

Enable file operations for GAIA-style tasks and SWE/DevOps/SRE benchmarks.

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with UTF-8/latin-1 encoding support (10MB limit). |
| `write_file` | Write or append to files with automatic parent-directory creation. |
| `list_directory` | List directory contents with optional glob pattern filtering. |
| `search_files` | Search by filename (glob patterns) or file content (grep-like). |

```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file write_file list_directory search_files \
  --working-directory /path/to/workspace \
  --agent-type both \
  --enable-otel
```

**Details:**

- **`read_file`** — supports UTF-8, latin-1, ASCII encodings; 10MB size limit; path-traversal prevention (restricted to the working directory).
- **`write_file`** — automatic parent-directory creation; `write` (overwrite) or `append` modes; system-directory protection (blocks `/etc/`, `C:\Windows\`, etc.); UTF-8 default.
- **`list_directory`** — optional glob pattern (e.g. `*.py`, `*.json`); shows type, size, modification time.
- **`search_files`** — search types `name` (glob) or `content` (grep-like); configurable max-results (default 100); recursive.

## Text Processing Tools (Phase 2)

Advanced text processing for log analysis, data processing, and SRE tasks.

| Tool | Description |
|------|-------------|
| `grep` | Pattern matching with regex, context lines, case-insensitive search, invert match, count-only. |
| `sed` | Stream editing: substitution (`s/pattern/replacement/`), deletion (`/pattern/d`), line selection (`Np`). |
| `sort` | Sort lines alphabetically or numerically, with unique/reverse/case-insensitive options. |
| `head_tail` | View the first or last N lines of a file (default 10). |

```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file grep sed sort head_tail \
  --working-directory ./logs \
  --agent-type both \
  --enable-otel
```

**Use cases:** log analysis (find errors with `grep`, clean formats with `sed`, organize with `sort`), data processing, SRE tasks, and DevOps workflows.

## Process & System Tools (Phase 3)

Process management and system interaction for SRE, DevOps, and monitoring tasks.

| Tool | Description |
|------|-------------|
| `ps` | List running processes with filtering (name) and sorting (CPU, memory, PID, name). |
| `kill` | Terminate processes by PID, with safety checks for system processes. |
| `env` | Get/set/list environment variables with filtering. |
| `which` | Find executable locations in PATH (cross-platform). |
| `curl` | HTTP requests (GET, POST, PUT, DELETE, HEAD, PATCH) with headers and body. |
| `ping` | Network connectivity checks with RTT statistics and packet loss. |

```bash
# Full SRE/DevOps toolkit
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools ps kill env which curl ping grep sed sort \
  --agent-type both \
  --enable-otel
```

## Other Tools

| Tool | Description |
|------|-------------|
| `user_input` | UserInputTool — interactive user input during execution. |

## Security Features

- All file, text, and system tools are restricted to `--working-directory`.
- Path-traversal prevention (`../` blocked).
- System-directory blacklist for write operations.
- File-size limits to prevent memory exhaustion.
- `ps` and `which` are read-only; `kill` protects system processes; `env` only affects the current process; `curl` validates URLs and enforces timeouts; `ping` enforces count/timeout limits.
