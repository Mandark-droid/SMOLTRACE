# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.5] - 2025-11-01

### Added - Ops Benchmark Sample Data Generator (2025-11-01)

**Feature: Automated Sample Data Setup for Operations Benchmark**

Created comprehensive sample data generation system for the ops benchmark to support evaluation of infrastructure operations and SRE/DevOps tasks.

**New Script**: `setup_ops_sample_data.py`
- Generates realistic sample data for all 24 ops benchmark test cases
- Creates 10 directories with appropriate files:
  - `logs/` - Application and system logs (app.log, mysql-slow.log, access.log, service logs)
  - `metrics/` - Performance metrics (CPU, memory, disk, database, API, cache, traffic)
  - `config/` - Configuration files (nginx.conf, database.yml, .env.production, certificates)
  - `k8s/` - Kubernetes deployment configurations
  - `deployments/` - Deployment history and changelogs
  - `backups/` - Backup manifests
  - `security/` - Security scan results
  - `billing/` - Cloud cost data (AWS)
  - `storage/` - Storage inventory
  - `state/` - Service state information

**Sample Data Features**:
- Realistic log entries with timestamps, error patterns, and rate spikes
- JSON metrics with time-series data points
- Complete configuration files matching ops benchmark tasks
- All file paths match benchmark task expectations (e.g., `./logs/app.log`, `./metrics/cpu_metrics.json`)

**Usage**:
```bash
# Generate sample data in default ops_sample directory
python setup_ops_sample_data.py

# Generate in custom directory
python setup_ops_sample_data.py my_custom_dir

# Run ops benchmark with sample data
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-ops-benchmark \
  --enable-tools read_file write_file list_directory search_files \
  --working-directory ./ops_sample \
  --agent-type both \
  --enable-otel
```

**Git Integration**:
- Added `ops_sample/` to `.gitignore` (sample data not committed)
- Script can be committed and run by any user to generate their own sample data

**Files Modified**:
- `setup_ops_sample_data.py` (NEW) - 774 lines of sample data generation logic
- `.gitignore` - Added `ops_sample/` directory exclusion
- `README.md` - Added ops sample data setup documentation

**Impact**:
- ✅ Ops benchmark evaluations work out of the box with sample data
- ✅ No more "Directory not found: ./metrics" errors
- ✅ Realistic data enables proper agent testing and debugging
- ✅ Users can regenerate or customize sample data as needed

---

### Fixed - Test Coverage Improvements (2025-11-01)

**Achievement: 88.93% Test Coverage (Up from 84.76%)**

Added 30 comprehensive tests targeting previously uncovered code paths in core.py, tools.py, and otel.py.

**New Test Files**:
- `tests/test_coverage_improvements.py` (13 tests)
  - run_evaluation with verbose mode
  - extract_traces with cost calculator handling
  - InMemorySpanExporter attribute conversion
  - Metrics force flush verification
  - Test subset filtering

- `tests/test_final_coverage_push.py` (17 tests)
  - Multiple agent types with verbose output
  - Enhanced trace info creation
  - Token aggregation in traces
  - Tool success tests (list_directory, file_search, grep, sed, sort, head_tail)
  - Extract metrics exception handling

**Coverage Results**:
- Overall: 88.93% (up from 84.76%, +4.17%)
- core.py: 92% (up from 80%, +12%)
- tools.py: 84% (up from 81%, +3%)
- utils.py: 94% (up from 89%, +5%)
- Test suite: 408 passed, 7 skipped, 0 failures

**Testing**:
- All tests use pytest-mock for comprehensive mocking
- Pre-commit hooks passed (black, isort, ruff)
- Build artifacts generated successfully

**Files Modified**:
- `tests/test_coverage_improvements.py` (NEW) - 358 lines
- `tests/test_final_coverage_push.py` (NEW) - 351 lines
- `pyproject.toml` - Version bumped to 0.0.5

---

### Added - Phase 3: Process & System Tools (2025-10-30)

**Feature: System Interaction and Process Management for SRE/DevOps Workflows**

Implemented 6 system-level tools enabling process management, environment variable operations, executable discovery, HTTP requests, and network diagnostics. These tools complete the SRE/DevOps toolkit alongside Phases 1-2.

**New Process & System Tools** (enabled via `--enable-tools`):

1. **`ps`**: List running processes with filtering and sorting
   - Filter by process name (case-insensitive substring match)
   - Sort by CPU usage, memory usage, PID, or name
   - Configurable result limit (default: 50, max: 500)
   - Returns PID, name, CPU%, memory%, status for each process
   - Cross-platform support via psutil library

2. **`kill`**: Terminate processes by PID with safety checks
   - Protected system processes (PID 0, 1, init, systemd, launchd, etc.)
   - Prevents self-termination (current Python process)
   - Graceful termination (SIGTERM) by default
   - Force kill option (SIGKILL) with `force=True`
   - Waits for confirmation with 2-second timeout
   - Cross-platform support (Linux, macOS, Windows)

3. **`env`**: Environment variable operations
   - Get specific variable value: `action='get', name='VAR_NAME'`
   - Set variable (affects current process): `action='set', name='VAR', value='...'`
   - List all variables: `action='list'`
   - Filter listing by pattern: `action='list', filter_pattern='PATH'`
   - Truncates long values (>80 chars) for readability
   - Sorted output for easy scanning

4. **`which`**: Find executable locations in PATH
   - Searches PATH environment variable for executables
   - Cross-platform support (Linux, macOS, Windows)
   - Returns first match by default
   - All matches mode: `all_matches=True`
   - Handles Windows extensions (.exe, .bat, .cmd, .com)
   - Uses shutil.which for reliable discovery

5. **`curl`**: HTTP requests with full method support
   - Methods: GET, POST, PUT, DELETE, HEAD, PATCH
   - Custom headers via JSON string
   - Request body support for POST/PUT
   - Configurable timeout (default: 30s)
   - Response includes status code, headers, and body
   - Body truncation for large responses (>5000 bytes)
   - URL validation (must start with http:// or https://)
   - Uses urllib for zero external dependencies

6. **`ping`**: Network connectivity checks
   - ICMP echo requests to hostname or IP address
   - Returns RTT statistics (min/avg/max in milliseconds)
   - Packet loss percentage calculation
   - Configurable packet count (default: 4, max: 100)
   - Configurable timeout per packet (default: 5s)
   - Cross-platform support with OS-specific parsing
   - Windows: `ping -n count -w timeout_ms`
   - Linux/macOS: `ping -c count -W timeout`

**Integration with Phases 1-2**:
- System tools work seamlessly with file and text processing tools
- No `working_dir` required (system-level operations)
- Can be combined in workflows: `ps` → `kill`, `env` → `which`, `curl` → `grep`
- Enable alongside existing tools: `--enable-tools read_file grep ps env curl`

**Use Cases**:
- **SRE Monitoring**: Check process health, monitor resource usage, verify service availability
- **Incident Response**: Investigate environment issues, check connectivity, analyze running processes
- **DevOps Automation**: Call APIs with curl, verify executables, manage processes
- **System Diagnostics**: Find executable paths, analyze environment variables, test network connectivity
- **Health Checks**: Ping services, query HTTP endpoints, list system processes

**CLI Examples**:
```bash
# Process monitoring
smoltrace-eval --enable-tools ps env --agent-type both

# Network diagnostics
smoltrace-eval --enable-tools curl ping which --agent-type both

# Full SRE toolkit (all phases)
smoltrace-eval --enable-tools ps kill env which curl ping grep sed sort --agent-type both
```

**Security Features**:
- **PsTool**: Read-only process listing (no modification capabilities)
- **KillTool**: Protected PIDs (0, 1) and system processes (init, systemd, svchost.exe, etc.)
- **EnvTool**: Only affects current process environment (no system-wide changes)
- **WhichTool**: Read-only PATH search
- **CurlTool**: URL validation, timeout protection against hanging requests
- **PingTool**: Count/timeout limits to prevent abuse (max 100 packets, timeout enforcement)

**Testing**:
- 42 comprehensive tests covering all 6 tools
- Unit tests for basic functionality, edge cases, and error handling
- Security tests (protected processes, invalid inputs)
- Integration tests (ps + env, env + which combinations)
- Cross-platform tests (Windows, Linux, macOS considerations)
- Network tests (skippable with SKIP_NETWORK_TESTS=1)
- Test coverage: 100% for new Phase 3 code
- All 42 tests passing on Windows

**Technical Implementation**:
- All tools inherit from smolagents `Tool` base class
- System tools don't require `working_dir` parameter
- Uses psutil for process operations (ps, kill)
- Uses shutil.which for executable discovery
- Uses urllib for HTTP requests (zero external deps)
- Uses subprocess for ping (cross-platform command execution)
- Proper nullable parameter handling for smolagents validation
- Consistent error messages and user-friendly output

**Dependencies**:
- `psutil`: Required for ps and kill tools
- Standard library only for env, which, curl, ping (urllib, shutil, subprocess, os, re)

---

### Added - Phase 2: Text Processing Tools (2025-10-30)

**Feature: Advanced Text Processing Tools for Log Analysis and Data Processing**

Implemented 4 Unix-inspired text processing tools with regex support and stream editing capabilities, enabling sophisticated log analysis, data transformation, and SRE workflows for agentic tasks.

**New Text Processing Tools** (enabled via `--enable-tools`):

1. **`grep`**: Pattern matching with regex support
   - Full Python regex pattern matching with `re` module
   - Case-insensitive search option (`case_insensitive=True`)
   - Context lines: show N lines before/after matches (`context_before`, `context_after`)
   - Invert match: show non-matching lines (`invert_match=True`)
   - Count mode: return match count instead of full lines (`count_only=True`)
   - Line numbers with prefix notation (`:` for matches, `-` for context)
   - Gap detection: inserts `--` separator between non-contiguous context blocks
   - Invalid regex pattern handling with clear error messages

2. **`sed`**: Stream editor for text transformations
   - Substitution: `s/pattern/replacement/` (first occurrence per line by default)
   - Global substitution: `s/pattern/replacement/` with `global_replace=True`
   - Deletion: `/pattern/d` (delete all lines matching pattern)
   - Line selection: `Np` (print specific line number N)
   - Case-insensitive mode for all operations
   - Optional output to new file instead of stdout
   - Regex pattern validation with error handling
   - Supports complex replacement patterns (backreferences, groups)

3. **`sort`**: Sort file lines with multiple options
   - Alphabetical sorting (default, lexicographic order)
   - Numeric sorting: extracts leading numbers from lines with regex
   - Reverse order: `reverse=True` for descending sort
   - Unique lines: `unique=True` removes duplicate lines
   - Case-insensitive sorting: `case_insensitive=True`
   - Optional output to new file
   - Handles mixed content (numbers + text) gracefully
   - Empty line handling

4. **`head_tail`**: View first or last N lines of files
   - Head mode: view first N lines (`mode='head'`)
   - Tail mode: view last N lines (`mode='tail'`)
   - Configurable line count (default: 10)
   - Efficient for quick file previews and inspection
   - Handles files shorter than requested line count gracefully

**Integration with Phase 1**:
- All text processing tools work seamlessly with Phase 1 file tools
- Respect `--working-directory` for path restrictions
- Same security model: path traversal prevention, sandboxing
- Can be combined in workflows: `search_files` → `grep` → `sed` → `sort`

**Use Cases**:
- **Log Analysis**: Find errors with `grep`, clean formats with `sed`, organize with `sort`
- **SRE Tasks**: Analyze system logs, parse configuration files, extract metrics
- **DevOps Workflows**: Process build logs, filter test output, analyze deployments
- **Data Processing**: Transform text files, deduplicate data, extract patterns

**CLI Examples**:
```bash
# Enable text processing for log analysis
smoltrace-eval --enable-tools read_file grep sed sort head_tail --working-directory ./logs

# Combine with file tools for comprehensive workflows
smoltrace-eval --enable-tools read_file write_file search_files grep sed sort

# Text processing for SRE tasks
smoltrace-eval --enable-tools grep sed sort
```

**Testing**:
- 32 comprehensive tests covering all 4 tools
- Unit tests for basic functionality, edge cases, and error handling
- Security tests (path traversal prevention)
- Integration tests (tool combinations like grep + sed, sort + head)
- Test coverage: 84% overall, 100% for new Phase 2 code

**Technical Implementation**:
- All tools inherit from smolagents `Tool` base class
- Consistent API: `working_dir` parameter, `_validate_path()` security checks
- Registered in `file_tools_map` for dynamic loading
- Python regex (`re` module) for pattern matching
- Stream processing for memory efficiency

---

### Added - Phase 1: File System Tools (2025-10-30)

**Feature: Comprehensive File Operations for GAIA and SWE/DevOps Benchmarks**

Implemented 4 production-ready file system tools with enterprise-grade security features, enabling real-world agentic tasks like code analysis, configuration management, and file-based workflows.

**New File Tools** (enabled via `--enable-tools`):

1. **`read_file`**: Read file contents with safety checks
   - Multi-encoding support: UTF-8, latin-1, ASCII (configurable)
   - 10MB file size limit to prevent memory exhaustion
   - Path traversal prevention (restricted to working directory)
   - Returns formatted output with file metadata (size, path)

2. **`write_file`**: Write or append to files with automatic directory creation
   - Write modes: `write` (overwrite) or `append`
   - Automatic parent directory creation (`mkdir -p` behavior)
   - UTF-8 encoding (default)
   - System directory protection (blacklist for `/etc/`, `C:\Windows\`, etc.)
   - Path traversal prevention

3. **`list_directory`**: List directory contents with filtering
   - Optional glob pattern filtering (e.g., `*.py`, `*.json`)
   - Shows file type, size, modification time
   - Supports both relative and absolute paths
   - Recursive listing in subdirectories

4. **`search_files`**: Advanced file search (name + content)
   - Search types:
     - `name`: Glob pattern matching (e.g., `*.txt`, `config*.yaml`)
     - `content`: Grep-like text search with 1MB file size limit per file
   - Recursive directory traversal
   - Max results limit (default: 100, configurable up to 1000)
   - Path traversal prevention

**New CLI Argument**:
- `--working-directory PATH`: Restrict file operations to specific directory
  - Defaults to current working directory if not specified
  - Required when using file tools in production environments
  - All file paths resolved relative to this directory

**Security Features**:
- **Path Traversal Prevention**: All file tools validate paths using `Path.resolve()` and `relative_to()` checks
  - Blocks `../` sequences and absolute paths outside working directory
  - Prevents access to parent directories or system files
- **System Directory Blacklist** (write operations):
  - Unix/Linux: `/etc/`, `/sys/`, `/proc/`, `/dev/`, `/root/`, `/boot/`
  - Windows: `C:\Windows\`, `C:\Program Files\`, `C:\Program Files (x86)\`
  - macOS: `/System/`, `/Library/`
- **File Size Limits**:
  - Read operations: 10MB max to prevent memory exhaustion
  - Content search: 1MB max per file (configurable)
- **UTF-8 Text Files Only** for content search (binary files skipped with warning)

**Implementation Details**:
- Added 4 new Tool classes in `smoltrace/tools.py` (~340 lines)
- Extended `get_smolagents_optional_tools()` to handle file tools with `working_dir` parameter
- Updated `get_all_tools()` signature to accept and pass `working_dir`
- Parameter chain: CLI → main.py → core.py → initialize_agent() → get_all_tools() → tools
- All file tools inherit security validation from shared `_validate_path()` methods

**Test Coverage**:
- Added `tests/test_file_tools.py` with 40 comprehensive test cases
- Coverage breakdown:
  - ReadFileTool: 9 tests (basic, encoding, size limits, path traversal, nested paths)
  - WriteFileTool: 8 tests (write, append, directory creation, system protection)
  - ListDirectoryTool: 7 tests (basic, patterns, nested, path validation)
  - FileSearchTool: 9 tests (name search, content search, max results, traversal)
  - Integration: 7 tests (read-write, write-list, write-search workflows)
- All tests use temporary workspaces (pytest fixtures)
- Security tests verify path traversal blocking and system directory protection
- Overall test suite: 266 passed, 6 skipped
- Tool coverage: tools.py at 85% (up from 61%)

**Usage Examples**:

```bash
# Enable file tools for code analysis
smoltrace-eval \
  --model gpt-4 \
  --provider litellm \
  --enable-tools read_file list_directory search_files \
  --working-directory ./my_project \
  --agent-type both \
  --enable-otel

# Enable all file tools + web research
smoltrace-eval \
  --model gpt-4 \
  --provider litellm \
  --enable-tools read_file write_file visit_webpage \
  --working-directory ./workspace \
  --agent-type both \
  --enable-otel
```

**Files Modified**:
- `smoltrace/tools.py`: Added 4 file tool classes (~340 lines)
- `smoltrace/cli.py`: Added `--working-directory` argument
- `smoltrace/main.py`: Pass working_directory to run_evaluation
- `smoltrace/core.py`: Thread working_directory through to initialize_agent
- `tests/test_file_tools.py`: 40 new tests for file tools
- `README.md`: Added file tools documentation and examples
- `changelog.md`: This entry

**Impact**:
- ✅ Enables GAIA-style benchmarks (file reading, analysis, multi-step reasoning)
- ✅ Supports SWE/DevOps/SRE tasks (config management, log analysis, code search)
- ✅ Backward compatible: File tools are opt-in via `--enable-tools`
- ✅ Secure by default: Path validation, size limits, system protection
- ✅ Test coverage maintained: 80% overall (85% for tools.py)

**Roadmap (Future Phases)**:
- Phase 2: Text Processing (grep, sed, awk equivalents)
- Phase 3: Directory Operations (copy, move, delete, archive)
- Phase 4: System Info (environment vars, process info, disk usage)

### Fixed - Restored Default Tools for smoltrace-tasks Compatibility (2025-10-30)

**Critical: DuckDuckGoSearchTool and PythonInterpreterTool Now Default**

- **Problem**: After making smolagents tools optional, the default tool set only included 3 custom tools
  - Removed DuckDuckGoSearchTool and PythonInterpreterTool from defaults
  - `kshitijthakkar/smoltrace-tasks` dataset requires these tools to run
  - Tasks would fail without web search and code execution capabilities

- **Solution**: Made DuckDuckGoSearchTool and PythonInterpreterTool default tools
  - Now 5 default tools (always enabled):
    1. `WeatherTool` (custom)
    2. `CalculatorTool` (custom)
    3. `TimeTool` (custom)
    4. `DuckDuckGoSearchTool` (smolagents) - Required for web search tasks
    5. `PythonInterpreterTool` (smolagents) - Required for code execution tasks
  - These are automatically enabled without requiring `--enable-tools` flag
  - Ensures backward compatibility with existing smoltrace-tasks dataset

- **Impact**:
  - ✅ All tasks in `kshitijthakkar/smoltrace-tasks` can now run successfully
  - ✅ Web search tasks work out of the box
  - ✅ Code execution tasks work out of the box
  - ✅ No breaking changes for existing evaluations
  - ✅ Optional tools still work via `--enable-tools` (e.g., google_search, visit_webpage, wikipedia_search)

**Updated Tool Configuration:**
```python
# Default tools (always enabled):
tools = [
    WeatherTool(),          # custom
    CalculatorTool(),       # custom
    TimeTool(),             # custom
    DuckDuckGoSearchTool(), # smolagents (default)
    PythonInterpreterTool() # smolagents (default)
]

# Optional tools (enabled via --enable-tools):
# - google_search (GoogleSearchTool)
# - visit_webpage (VisitWebpageTool)
# - wikipedia_search (WikipediaSearchTool)
# - user_input (UserInputTool)
```

**Files Modified:**
- `smoltrace/tools.py` - Added DuckDuckGoSearchTool and PythonInterpreterTool to default tools
- `tests/test_tools.py` - Updated to expect 5 default tools
- `tests/test_new_features.py` - Updated all tool count assertions

**Test Results:**
- ✅ All 226 tests passing
- ✅ 87% coverage maintained
- ✅ tools.py coverage: 93%

### Added - Smolagents Tools Integration & InferenceClientModel Support (2025-10-30)

**Feature: Optional Smolagents Default Tools with API Key Management**

- **New CLI Arguments**:
  - `--enable-tools [tool1 tool2 ...]`: Enable optional smolagents.default_tools on demand
  - `--search-provider {serper,brave,duckduckgo}`: Configure GoogleSearchTool provider
  - `--parallel-workers N`: Number of parallel workers for evaluation (infrastructure ready)

- **Available Optional Tools** (via `--enable-tools`):
  - `google_search`: GoogleSearchTool with configurable providers (requires SERPER_API_KEY, BRAVE_API_KEY, or use duckduckgo)
  - `duckduckgo_search`: Official DuckDuckGoSearchTool from smolagents
  - `visit_webpage`: VisitWebpageTool - Extract and read web page content
  - `python_interpreter`: PythonInterpreterTool - Safe Python execution with authorized imports
  - `wikipedia_search`: WikipediaSearchTool (requires `pip install wikipedia-api`)
  - `user_input`: UserInputTool - Interactive user input during execution

- **Default Tools** (always enabled, no changes):
  - `get_weather`: WeatherTool (custom)
  - `calculator`: CalculatorTool (custom)
  - `get_current_time`: TimeTool (custom)
  - MCP server tools continue to work as before

- **Implementation**:
  - `tools.py`: New functions `get_smolagents_optional_tools()` and updated `get_all_tools()`
  - Graceful error handling for missing dependencies (e.g., wikipediaapi)
  - API key validation from environment variables
  - Tools only loaded when explicitly requested via `--enable-tools`

- **Environment Variables** (added to `.env.example`):
  ```bash
  SERPER_API_KEY=your_key  # For GoogleSearchTool with serper provider
  BRAVE_API_KEY=your_key   # For GoogleSearchTool with brave provider
  ```

**Feature: HuggingFace Inference API Provider Support**

- **New Provider**: `inference` (InferenceClientModel)
  - Access to HuggingFace Inference API hosted models
  - No local GPU required
  - Uses HF_TOKEN for authentication

- **New CLI Arguments**:
  - `--provider inference`: Use InferenceClientModel
  - `--hf-inference-provider PROVIDER`: Specify HF inference provider (optional)

- **Usage Example**:
  ```bash
  smoltrace-eval \
    --model meta-llama/Llama-3.1-70B-Instruct \
    --provider inference \
    --agent-type both \
    --enable-otel
  ```

- **Implementation**:
  - `core.py`: Added `elif provider == "inference"` branch in `initialize_agent()`
  - Supports all InferenceClientModel parameters
  - Compatible with HF Jobs infrastructure

**Feature: Parallel Workers Infrastructure**

- **New CLI Argument**: `--parallel-workers N` (default: 1)
- Currently infrastructure only - parameter passed through the entire stack
- Designed for future implementation of ThreadPoolExecutor-based parallel execution
- Recommended values: 8 for API models, 1 for GPU models
- Files updated: `cli.py`, `main.py`, `core.py` (signatures and parameter passing)

**Files Modified:**
- `smoltrace/tools.py`: Added `get_smolagents_optional_tools()`, updated `get_all_tools()`
- `smoltrace/core.py`: Added InferenceClientModel support, updated function signatures
- `smoltrace/cli.py`: Added `--enable-tools`, `--search-provider`, `--hf-inference-provider`, `--parallel-workers`
- `smoltrace/main.py`: Pass new parameters through to run_evaluation
- `.env.example`: Added SERPER_API_KEY and BRAVE_API_KEY

**Documentation:**
- `README.md`: Added sections for new features with examples
- `docs/NEW_FEATURES_SUMMARY.md`: Comprehensive feature documentation
- Updated CLI arguments table with new options

**Backward Compatibility:**
- ✅ 100% backward compatible
- Default tools remain unchanged (3 custom tools)
- Existing CLI commands work without modification
- New features are opt-in via CLI flags
- MCP tools continue to work as before

### Fixed - Test Suite for New Features (2025-10-30)

**Achievement: All 226 Tests Passing with 87% Coverage**

- **Problem**: New feature tests failing due to incorrect assertions and mocking
  - 4 test failures in `test_new_features.py`
  - Tool count assertions not accounting for auto-added `final_answer` tool
  - InferenceClientModel mock patching at wrong location
  - Agents automatically add `final_answer` tool to all ToolCallingAgent instances

- **Solution**: Updated test assertions to match actual behavior
  - **Tool Count Fixes** (3 tests):
    - `test_initialize_agent_with_optional_tools`: Updated from 4 to 5 tools (3 default + 1 optional + 1 final_answer)
    - `test_initialize_agent_with_search_provider`: Updated from 4 to 5 tools (3 default + 1 google_search + 1 final_answer)
    - `test_initialize_agent_without_new_parameters`: Updated from 3 to 4 tools (3 default + 1 final_answer)
    - Added verification of specific tool names in assertions (e.g., "visit_webpage", "web_search", "final_answer")

  - **Mock Patching Fix** (1 test):
    - `test_initialize_agent_inference_runtime_error`: Changed from patching `smoltrace.core.InferenceClientModel` to `smolagents.InferenceClientModel`
    - InferenceClientModel is imported dynamically inside function, requires patching at import location
    - Updated exception assertion to match actual behavior

- **Results**:
  - ✅ **All 24 tests in test_new_features.py passing**
  - ✅ **Full test suite: 226 tests passed, 6 skipped**
  - ✅ **Overall coverage: 87%** (up from 15% when running isolated tests)
  - ✅ **tools.py coverage: 97%** - excellent coverage for new features
  - ✅ **core.py coverage: 80%** - includes InferenceClientModel provider code
  - ✅ **cli.py coverage: 100%** - all new CLI arguments tested

**Test Coverage by Module:**
```
smoltrace/__init__.py    100%
smoltrace/cleanup.py      99%
smoltrace/cli.py         100%  ⭐ (all new CLI args covered)
smoltrace/core.py         80%
smoltrace/main.py         96%
smoltrace/otel.py         86%
smoltrace/tools.py        97%  ⭐ (new optional tools covered)
smoltrace/utils.py        87%
```

**Files Modified:**
- `tests/test_new_features.py` - Fixed 4 failing tests with correct assertions

**Test Classes Coverage:**
- ✅ `TestInferenceClientModelProvider` (4 tests) - InferenceClientModel provider support
- ✅ `TestOptionalSmolagentsTools` (9 tests) - Optional smolagents tools functionality
- ✅ `TestAgentInitializationWithOptionalTools` (2 tests) - Agent initialization with optional tools
- ✅ `TestParallelWorkersInfrastructure` (2 tests) - Parallel workers infrastructure
- ✅ `TestToolsWithAdditionalImports` (2 tests) - Additional imports functionality
- ✅ `TestBackwardCompatibility` (2 tests) - Backward compatibility verification
- ✅ `TestErrorHandling` (3 tests) - Error handling in new features

### Added - Dynamic Tool Detection for MCP Tools (2025-10-30)

**Feature: Automatic Detection of MCP and Custom Tools in Code Agent Execution**

- **Problem**: Previously, `extract_tools_from_code()` used hardcoded regex patterns for only 4 tools:
  - `get_weather`, `calculator`, `get_current_time`, `web_search`
  - Could not detect MCP (Model Context Protocol) server tools or any custom tools
  - Made tool usage tracking incomplete when using MCP servers

- **Solution**: Dynamic tool extraction based on available tools
  - Updated `extract_tools_from_code()` to accept `available_tools` parameter
  - Extracts tool names from tool objects (`tool.name` attribute)
  - Builds dynamic regex patterns for each available tool
  - Properly escapes special regex characters in tool names (e.g., `search.v2`)
  - Falls back to hardcoded patterns when `available_tools` is None (backward compatibility)

- **Implementation**:
  - `extract_tools_from_code(code, available_tools=None)` - accepts list of tool objects
  - `extract_tools_from_action_step(event, agent_type, debug, tracer, available_tools=None)` - passes tools through
  - `analyze_streamed_steps(agent, ...)` - extracts `agent.tools` and passes to helper functions
  - Dynamic pattern building: `pattern = rf"{re.escape(tool_name)}\s*\("`

- **Impact**:
  - ✅ MCP server tools are now properly detected in CodeAgent execution
  - ✅ Any custom tools added via `initialize_mcp_tools()` are tracked
  - ✅ Tool usage metrics in traces are complete and accurate
  - ✅ Backward compatible with existing code (fallback patterns)

**Files Modified:**
- `smoltrace/core.py`:
  - `extract_tools_from_code()` (lines 188-227) - Dynamic tool detection
  - `extract_tools_from_action_step()` (lines 272-312) - Pass available_tools
  - `analyze_streamed_steps()` (lines 230-286) - Extract agent.tools and pass through

**Testing:**
- Added 6 comprehensive tests in `tests/test_core.py`:
  - `test_extract_tools_from_code_with_available_tools()` - Multi-tool detection
  - `test_extract_tools_from_code_with_special_characters_in_tool_names()` - Regex escaping
  - `test_extract_tools_from_code_fallback_when_no_available_tools()` - Backward compatibility
  - `test_extract_tools_from_code_multiple_calls_to_same_tool()` - Multiple calls
  - `test_extract_tools_from_action_step_with_available_tools()` - Integration test
  - `test_analyze_streamed_steps_extracts_agent_tools()` - End-to-end test
- All new tests passing (197 total tests passing)

**Example Usage:**
```python
# MCP tools automatically detected in agent execution
agent = initialize_agent(
    model_name="gpt-4",
    agent_type="code",
    mcp_server_url="http://localhost:8080/sse"
)

# Agent now has default tools + MCP tools
# extract_tools_from_code() will detect all tool calls in generated code
# Including MCP tools like "database_query", "custom_search", etc.
```

### Fixed - Test Suite Mocking Issues & Coverage Improvements (2025-10-30)

**Achievement: 94.22% Test Coverage (Exceeds 90% Goal)**

- **Problem**: 5 test failures due to mock issues with dynamically imported modules
  - MCP tools tests failing: `test_initialize_mcp_tools_success`, `test_initialize_mcp_tools_connection_error`
  - DuckDuckGo search tests failing: `test_duckduckgo_search_tool_success`, `test_duckduckgo_search_tool_no_results`, `test_duckduckgo_search_tool_search_error`
  - Root cause: Real modules (`smolagents.mcp_client`, `ddgs`) were being imported instead of mocks
  - `mocker.patch()` with `create=True` wasn't working for dynamically imported modules

- **Solution**: Use `patch.dict('sys.modules', {...})` to inject mock modules
  - Import `unittest.mock.patch` directly instead of using `mocker.patch.dict`
  - Create mock module objects with `MagicMock()`
  - Inject mock modules before function execution via `patch.dict('sys.modules', {'module.name': mock_module})`
  - Properly mock context managers for `DDGS()` with `__enter__` and `__exit__`

- **Implementation**:
  - Updated all MCP tools tests to use `patch.dict` for `smolagents.mcp_client` module
  - Updated all DuckDuckGo tests to use `patch.dict` for `ddgs` module
  - Fixed ImportError simulation by clearing sys.modules and patching `__import__`
  - Ensured all exception paths are properly tested

- **Results**:
  - ✅ **202 tests passing** (6 skipped - transformers/GPU tests)
  - ✅ **0 tests failing**
  - ✅ **94.22% overall coverage** (exceeds 90% requirement)
  - ✅ `smoltrace/tools.py`: 98% coverage (up from 83%)
  - ✅ `smoltrace/cli.py`: 100% coverage
  - ✅ `smoltrace/cleanup.py`: 99% coverage

**Files Modified:**
- `tests/test_tools.py` - Fixed all 5 failing tests with proper module mocking

**Coverage by Module:**
```
smoltrace/__init__.py    100%
smoltrace/cleanup.py      99%
smoltrace/cli.py         100%
smoltrace/core.py         79%
smoltrace/main.py         96%
smoltrace/otel.py         86%
smoltrace/tools.py        98%  ⭐ (improved from 83%)
smoltrace/utils.py        87%
```

### Fixed - Cost Calculation via Post-Processing (2025-10-28)

**Critical: LLM Cost Now Calculated Correctly**

- **Root Cause**: `CostEnrichmentSpanProcessor` couldn't modify immutable `ReadableSpan` objects
  - OpenTelemetry spans become immutable (ReadableSpan) by the time `on_end()` is called
  - No `set_attribute()` method available on ReadableSpan
  - Warning: "Span 'completion' is not mutable, cannot add cost attributes"
  - Result: `total_cost_usd: 0.0` in traces despite having all necessary data (model name, token counts)

- **Solution**: Post-processing cost calculation in `extract_traces()`
  - Import `CostCalculator` from `genai_otel.cost_calculator`
  - During trace extraction, for each span with LLM data but no cost:
    - Extract model name and token counts from span attributes
    - Use `CostCalculator.calculate_granular_cost()` to calculate cost
    - Add `gen_ai.usage.cost.total` to span attributes dict
    - Aggregate cost at trace level
  - Works with both API models and local models (Ollama, HuggingFace)

- **Impact**: All datasets now have accurate cost tracking
  - ✅ Traces dataset includes per-span and total costs
  - ✅ Results dataset has per-test-case costs
  - ✅ Leaderboard dataset has accurate aggregated costs
  - ✅ TraceMind UI can display cost comparisons

- **Cost Calculation Examples**:
  - Ollama qwen2.5-coder:3b (1555 tokens) = $0.000473
  - Uses genai_otel pricing database with parameter count fallback
  - Supports all LiteLLM-supported API models with accurate pricing

**Files Modified:**
- `smoltrace/core.py` (lines 527-612) - Added post-processing cost calculation in `extract_traces()`

**Testing:**
- `test_cost_postprocess.py` - Verifies cost calculation with sample trace data
- Test passes: Cost $0.000473 calculated correctly for qwen2.5-coder:3b model
- `COST_POSTPROCESS_FIX.md` - Complete documentation

### Fixed - Missing CO2 and Power Cost Columns in Metrics Dataset (2025-10-28)

**Critical: Ensures All 13 Columns Always Present**

- **Root Cause**: Metrics with empty `dataPoints` arrays were skipped during flattening
  - CO2 and power cost are cumulative metrics that start at 0
  - If first metric batch exported before they accumulated, columns were missing entirely
  - Result: Datasets had only 11 columns instead of 13

- **Solution**: Initialize ALL expected columns with default values
  - Modified `flatten_metrics_for_hf()` to pre-initialize all 7 metric columns to 0.0
  - Columns: `co2_emissions_gco2e`, `power_cost_usd`, `gpu_utilization_percent`,
    `gpu_memory_used_mib`, `gpu_memory_total_mib`, `gpu_temperature_celsius`, `gpu_power_watts`
  - Metrics with data points overwrite defaults with actual values
  - Metrics without data points keep default 0.0

- **Impact**: Metrics dataset now ALWAYS has consistent 13-column schema
  - ✅ No more missing columns reported by users
  - ✅ Leaderboard aggregation always has source data
  - ✅ TraceMind UI can rely on consistent schema
  - ✅ CO2 and power cost start at 0.0 and increase as evaluation runs

**Files Modified:**
- `smoltrace/utils.py` (lines 422-435, 449-452) - Initialize all columns before processing metrics

**Testing:**
- Verified with 2-second test (only 5 metrics exported, but 13 columns created)
- All columns present with appropriate default or actual values

### Added - Metrics Dataset Enhancements (2025-10-27)

**Metrics Flattening & Aggregation:**

- **Metrics Dataset Now Includes All 7 GPU Metrics**:
  - `co2_emissions_gco2e` - CO2 emissions in grams CO2 equivalent
  - `power_cost_usd` - Power cost in USD
  - `gpu_utilization_percent` - GPU utilization percentage
  - `gpu_memory_used_mib` - GPU memory used in MiB
  - `gpu_memory_total_mib` - Total GPU memory in MiB
  - `gpu_temperature_celsius` - GPU temperature in Celsius
  - `gpu_power_watts` - GPU power consumption in Watts

- **Leaderboard Dataset Now Includes Environmental Metrics**:
  - `co2_emissions_g` - Total CO2 emissions aggregated from GPU metrics
  - `power_cost_total_usd` - Total power cost aggregated from GPU metrics
  - Both metrics sourced from GPU time-series data (most accurate)
  - Falls back to trace aggregates if GPU metrics unavailable

- **Enhanced `aggregate_gpu_metrics()` Function**:
  - Now extracts CO2 and power cost totals from time-series data
  - Uses max value (final cumulative reading) for CO2 and cost
  - Maintains avg/max aggregations for utilization, memory, temperature, power

**Technical Details:**
- Fixed metrics flattening pipeline to preserve all 7 metrics through flatten_metrics_for_hf()
- Updated compute_leaderboard_row() to prioritize GPU metrics over trace aggregates
- All aggregate fields now available for TraceMind UI dashboard displays

**Files Modified:**
- `smoltrace/utils.py` - Updated aggregate_gpu_metrics() and compute_leaderboard_row()
- `METRICS_FLATTENING_SUMMARY.md` - Complete documentation of flattening process

**Testing:**
- All existing tests pass with new schema
- Verified with real evaluation: kshitijthakkar/smoltrace-metrics-20251027_180902
- Dataset contains 11 rows × 13 columns with all 7 metrics

### Fixed - LLM Cost Tracking in Traces Dataset (2025-10-27)

**Critical: Cost Attributes Now Captured in Spans**

- **Root Cause:** Span processor ordering prevented cost enrichment before export
  - `SimpleSpanProcessor` was added BEFORE `CostEnrichmentSpanProcessor`
  - Spans were exported WITHOUT cost attributes
  - Result: `total_cost_usd: 0.0` in traces dataset despite token counts being present

- **Solution:** Reordered span processors in `setup_inmemory_otel()`
  - `CostEnrichmentSpanProcessor` now added FIRST
  - `SimpleSpanProcessor` added SECOND (exports spans AFTER cost enrichment)
  - genai_otel's cost calculation now runs before span export

- **Impact:** Traces dataset now includes accurate LLM usage costs
  - Span attributes include `gen_ai.usage.cost.total`
  - Trace-level `total_cost_usd` properly aggregated from span costs
  - Enables cost tracking for API models (OpenAI, Anthropic, etc.) and local models

**Technical Details:**
- Added `CostEnrichmentSpanProcessor` from genai_otel before `SimpleSpanProcessor`
- genai_otel's processor extracts model name, token counts, and calculates cost
- Cost enrichment happens in `on_end()` callback before export
- Works for all OpenInference-instrumented spans (smolagents, litellm, mcp)

**Files Modified:**
- `smoltrace/otel.py` - Fixed span processor ordering (lines 604-623)
- `COST_TRACKING_FIX_SUMMARY.md` - Complete fix documentation

**Testing:**
- Verified processor order: CostEnrichmentSpanProcessor → SimpleSpanProcessor
- Setup logs confirm: "[OK] CostEnrichmentSpanProcessor added"
- Awaiting evaluation run to confirm cost in traces dataset

### Fixed - TraceMind UI Compatibility (2025-10-27)

**Critical Dataset Structure Fixes:**

- **GPU Metrics Collection**:
  - Added `force_flush()` call before metric extraction to ensure buffered metrics are exported
  - Fixed `PeriodicExportingMetricReader` timing issue (10-second interval was causing metrics loss)
  - Added `--disable-gpu-metrics` CLI flag (replaces missing opt-in flag)
  - **GPU metrics now enabled by default for ALL local models** (`transformers` AND `ollama`)
  - Users can opt-out with `--disable-gpu-metrics` flag if desired
  - API models (`litellm`) correctly default to disabled (no local GPU)

- **Results Dataset Improvements**:
  - Extracted `trace_id`, `execution_time_ms`, `total_tokens`, `cost_usd` from `enhanced_trace_info` to top-level fields
  - These fields were trapped in JSON string, blocking UI table display and navigation
  - Renamed `test_id` → `task_id` for UI consistency

- **Leaderboard Dataset Improvements**:
  - Renamed `evaluation_date` → `timestamp` for UI consistency
  - Renamed `num_tests` → `total_tests` for UI consistency
  - Verified `run_id` and `submitted_by` fields present
  - Verified GPU aggregate metrics present

- **Traces Dataset Improvements**:
  - Fixed span status codes: numeric (0, 1, 2) → string ("UNSET", "OK", "ERROR")
  - Fixed span kind format: removed "SpanKind." prefix (e.g., "SpanKind.INTERNAL" → "INTERNAL")
  - Enables proper color-coding in TraceMind UI (red for ERROR spans)

**Files Modified:**
- `smoltrace/core.py` - Added force_flush() for metrics
- `smoltrace/cli.py` - Added --disable-gpu-metrics flag
- `smoltrace/main.py` - Smart GPU metrics default logic for local vs API models
- `smoltrace/utils.py` - Field extraction and renames
- `smoltrace/otel.py` - Span status and kind format fixes

**Testing:**
- Created `test_fixes.py` - Verifies all 5 critical fixes
- Created `verify_all_fixes.py` - Complete verification against gap analysis
- Created `test_gpu_defaults.py` - Tests GPU metrics default behavior
- All tests passing ✅

**Documentation:**
- `DATASET_GAP_ANALYSIS.md` - Complete analysis of UI vs dataset gaps
- `SMOLTRACE_FIXES_APPLIED.md` - Detailed fix documentation
- `GPU_METRICS_DEFAULT_BEHAVIOR.md` - GPU metrics behavior guide
- `METRICS_FIX_SUMMARY.md` - Critical metrics fix summary

### Changed

- **GPU metrics default behavior** (BREAKING CHANGE):
  - Previously: Only `transformers` had GPU metrics enabled by default
  - Now: ALL local models (`transformers` + `ollama`) have GPU metrics enabled by default
  - Rationale: Local models run on local hardware, should collect GPU metrics
  - Migration: If you want to disable GPU metrics, add `--disable-gpu-metrics` flag

### Added - Data Schema Improvements (2025-10-23)
- **Complete data schema overhaul with run_id support**:
  - Added `InMemoryMetricExporter` class in `smoltrace/otel.py` for capturing GPU metrics in OpenTelemetry format
  - Renamed `InMemoryMetricReaderCollector` to `TraceMetricsAggregator` for clarity
  - All datasets now include `run_id` for linking and filtering across datasets
  - Results dataset includes `test_index`, `start_time_unix_nano`, `end_time_unix_nano` fields
  - Metrics dataset restructured to OpenTelemetry `resourceMetrics` format with time-series data
  - Leaderboard includes 7 new GPU metric fields: `gpu_utilization_avg/max`, `gpu_memory_avg/max_mib`, `gpu_temperature_avg/max`, `gpu_power_avg_w`
  - Leaderboard includes `run_id`, `provider`, `submitted_by`, `successful_tests`, `failed_tests` fields

- **New CLI argument**: `--run-id` for specifying custom run identifiers (auto-generates UUID if not provided)

- **GPU metrics aggregation**: New `aggregate_gpu_metrics()` helper function in `smoltrace/utils.py`
  - Extracts time-series data from OpenTelemetry resourceMetrics
  - Computes avg and max values for utilization, memory, temperature, power

- **Sample data generation**: New `generate_sample_metrics.py` script in `MockTraceMind/sample_data/`
  - Generates GPU metrics sample (`metrics_llama31.json`)
  - Generates API metrics sample (`metrics_gpt4.json`)

- **Comprehensive documentation**:
  - `IMPLEMENTATION_PLAN.md` - Detailed implementation guide
  - `IMPLEMENTATION_COMPLETE.md` - Complete feature summary and testing guide
  - `REMAINING_IMPLEMENTATION.md` - Mid-implementation status
  - `METRICS_DATASET_FIX.md` - Post-implementation fixes documentation
  - `smoltrace_dataset_structure.md` - Updated complete schema documentation

- **Test files**:
  - `tests/test_otel_fix.py` - Verifies InMemoryMetricExporter works correctly
  - `tests/test_metrics_dataset_creation.py` - Verifies metrics dataset creation logic

### Added
- **Local JSON output option**: New `--output-format {hub,json}` CLI argument to save results locally instead of pushing to HuggingFace Hub
  - New `--output-dir` argument for specifying local output directory (default: `./smoltrace_results`)
  - Automatically creates timestamped directories with 5 JSON files: `results.json`, `traces.json`, `metrics.json`, `leaderboard_row.json`, `metadata.json`
  - Implemented `save_results_locally()` function in `smoltrace/utils.py`
- **Explicit provider selection**: New `--provider {litellm,transformers,ollama}` CLI argument
  - Supports multiple API keys: `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `TOGETHER_API_KEY`
  - Clearer error messages for missing API keys
- **OpenTelemetry integration**: Added `smoltrace/otel.py` with in-memory OTEL exporters and metrics aggregation
  - `InMemorySpanExporter` for collecting traces
  - `InMemoryMetricReaderCollector` for aggregating metrics from traces
  - Support for genai_otel_instrument auto-instrumentation
- **Tool definitions**: Added `smoltrace/tools.py` with custom tools
  - `WeatherTool`: Mock weather data for testing
  - `CalculatorTool`: Basic math calculations
  - `TimeTool`: Current time in specified timezone
  - `DuckDuckGoSearchTool`: Web search functionality
- **Cost metric**: Added `gen_ai.usage.cost.total` to metrics dataset
- **Environment file loading**: Added `.env` file loading via `python-dotenv` at CLI startup
- **Package discovery**: Added explicit package configuration in `pyproject.toml` to exclude test directories
- Added `duckduckgo-search` as main dependency
- Made `genai-otel-instrument` a default dependency (moved from optional)
- Added `avg_duration_ms`, `total_duration_ms`, and `total_cost_usd` to leaderboard metrics
- Added `gradio==6.0.0.dev0` to `requirements-dev.txt`

### Changed - Data Schema Improvements (2025-10-23)
- **Core evaluation flow** (`smoltrace/core.py`):
  - `run_evaluation()` now accepts `run_id` and `enable_gpu_metrics` parameters
  - Returns 5 values: `(all_results, trace_data, metric_data, dataset_name, run_id)`
  - Adds `run_id` and `test_index` to all results
  - `extract_traces()` now accepts `run_id` and adds it to each trace
  - `extract_metrics()` completely rewritten to return Dict with `run_id`, `resourceMetrics`, `aggregates`
  - Added comprehensive debug logging for metric extraction

- **OTEL setup** (`smoltrace/otel.py`):
  - `setup_inmemory_otel()` now accepts `run_id` and `enable_gpu_metrics` parameters
  - Returns 6 values: `(tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id)`
  - Creates Resource with run_id attribute
  - Uses `PeriodicExportingMetricReader` with 10-second intervals

- **Main evaluation flow** (`smoltrace/main.py`):
  - Updated to handle 5-value return from `run_evaluation()`
  - Auto-enables GPU metrics when provider is "transformers"
  - Displays run_id to user
  - Passes run_id to all dataset functions

- **Dataset generation** (`smoltrace/utils.py`):
  - `compute_leaderboard_row()` now accepts `metric_data` as Dict (was List)
  - Accepts `run_id` and `provider` parameters
  - Extracts HuggingFace username from token for `submitted_by` field
  - Aggregates GPU metrics and includes in leaderboard row
  - `push_results_to_hf()` now accepts `metric_data` as Dict
  - Changed condition to always create metrics dataset (even with empty resourceMetrics)
  - Pushes metrics in OpenTelemetry resourceMetrics format
  - Single row per run containing all time-series data

### Changed
- Refactored `run_evaluation` in `smoltrace/core.py` to return raw evaluation data
- Updated `push_results_to_hf` in `smoltrace/utils.py` to accept and push trace and metric data
- Updated `compute_leaderboard_row` in `smoltrace/utils.py` to include new duration and cost metrics
- Updated `run_evaluation_flow` in `smoltrace/main.py` to:
  - Pass trace and metric data to `push_results_to_hf`
  - Branch based on `--output-format` (hub vs json)
  - Remove unicode emoji characters (replaced with text markers for Windows compatibility)
- Updated `initialize_agent()` in `smoltrace/core.py` to support three providers with explicit configuration
- Enhanced `_aggregate_from_traces()` in `smoltrace/otel.py` to correctly collect metrics from span attributes

### Fixed - Data Schema Improvements (2025-10-23)
- **Critical: Fixed InMemoryMetricExporter missing attributes** (`smoltrace/otel.py`):
  - Error: `AttributeError: 'InMemoryMetricExporter' object has no attribute '_preferred_temporality'`
  - Added `_preferred_temporality` and `_preferred_aggregation` attributes required by `PeriodicExportingMetricReader`
  - Now properly implements OpenTelemetry MetricExporter interface

- **Critical: Fixed metrics dataset not being created** (`smoltrace/utils.py`):
  - Issue: Dataset wasn't created for API models because `resourceMetrics` was an empty list
  - Changed condition from `if metric_data.get("resourceMetrics"):` to `if "resourceMetrics" in metric_data:`
  - Now checks for key existence rather than truthiness
  - Dataset is always created (with empty resourceMetrics for API models, populated for GPU models)
  - Added informative logging to distinguish between GPU and API model metrics

### Fixed
- **Critical: Fixed OpenTelemetry tracer error**: `'Tracer' object has no attribute 'trace'`
  - Changed from `tracer.trace.get_current_span()` to `trace.get_current_span()` (lines 186, 227 in `core.py`)
  - Added proper import: `from opentelemetry import trace`
  - Added safety checks for span recording: `if current_span and current_span.is_recording()`
- **Critical: Fixed metrics aggregation returning all zeros**
  - Now correctly collects token counts, costs, and metrics from span attributes
  - Token counts properly captured from trace-level aggregated data
  - Test-specific metrics collected from individual spans (lines 146-242 in `otel.py`)
- **Security: Removed sensitive argument printing from CLI**
  - CLI no longer prints command-line arguments that may contain tokens
- Removed unused imports in `smoltrace/cli.py`, `smoltrace/core.py`, and `tests/test_utils.py`
- Fixed unicode encoding errors by replacing emoji characters with text markers

## [0.1.0] - YYYY-MM-DD

### Added

- Initial release of smoltrace.
