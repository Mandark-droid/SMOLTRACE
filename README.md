<div align="center">
  <img src="https://raw.githubusercontent.com/Mandark-droid/SMOLTRACE/main/.github/images/Logo.png" alt="SMOLTRACE Logo" width="400"/>

  <h3><em>Tiny Agents. Total Visibility.</em></h3>
  <h3><em>Smol Agents. Smart Metrics.</em></h3>
</div>

# smoltrace

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://github.com/Mandark-droid/SMOLTRACE/blob/main/LICENSE)
[![PyPI version](https://badge.fury.io/py/smoltrace.svg)](https://badge.fury.io/py/smoltrace)
[![Downloads](https://static.pepy.tech/badge/smoltrace)](https://pepy.tech/project/smoltrace)
[![Downloads/Month](https://static.pepy.tech/badge/smoltrace/month)](https://pepy.tech/project/smoltrace)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Tests](https://img.shields.io/github/actions/workflow/status/Mandark-droid/SMOLTRACE/test.yml?branch=main&label=tests)](https://github.com/Mandark-droid/SMOLTRACE/actions?query=workflow%3Atest)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://huggingface.co/docs/smoltrace/en/index)

**SMOLTRACE** is a comprehensive benchmarking and evaluation framework for [Smolagents](https://huggingface.co/docs/smolagents), Hugging Face's lightweight agent library. It enables seamless testing of `ToolCallingAgent` and `CodeAgent` on custom or HF-hosted task datasets, with built-in support for OpenTelemetry (OTEL) tracing/metrics, results export to Hugging Face Datasets, and automated leaderboard updates.

Designed for reproducibility and scalability, it integrates with HF Spaces, Jobs, and the Datasets library. Evaluate your fine-tuned models, compare agent types, and contribute to community leaderboards—all in a few lines of code.

## Features

- **Zero Configuration**: Only HF_TOKEN required - automatically generates dataset names from username
- **Task Loading**: Pull evaluation tasks from HF Datasets (e.g., `kshitijthakkar/smoltrace-tasks`) or local JSON
- **Agent Benchmarking**: Run Tool and Code agents on categorized tasks (easy/medium/hard) with tool usage verification
- **Multi-Provider Support**:
  - **LiteLLM** (default): API models from OpenAI, Anthropic, Mistral, Groq, Together AI, etc.
  - **Inference**: HuggingFace Inference API (InferenceClientModel) for hosted models
  - **Transformers**: Local HuggingFace models on GPU
  - **Ollama**: Local models via Ollama server
- **OTEL Integration**: Auto-instrument with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument) for traces (spans, token counts) and metrics (CO2 emissions, power cost, GPU utilization)
- **Comprehensive Metrics**: All 7 GPU metrics tracked and aggregated in results/leaderboard:
  - Environmental: CO2 emissions (gCO2e), power cost (USD)
  - Performance: GPU utilization (%), memory usage (MiB), temperature (°C), power (W)
  - Flattened time-series format perfect for dashboards and visualization
- **Flexible Output**:
  - Push to HuggingFace Hub (4 separate datasets: results, traces, metrics, leaderboard)
  - Save locally as JSON files (5 files: results, traces, metrics, leaderboard row, metadata)
- **Dataset Cleanup**: Built-in `smoltrace-cleanup` utility to manage datasets with safety features (dry-run, confirmations, filters)
- **Leaderboard**: Aggregate metrics (success rate, tokens, CO2, cost) and auto-update shared org leaderboard
- **CLI & HF Jobs**: Run standalone or in containerized HF environments
- **Optional Smolagents Tools**: Enable production-ready tools on demand:
  - `google_search`: GoogleSearchTool with configurable providers (Serper, Brave, DuckDuckGo)
  - `visit_webpage`: Extract content from web pages for research
  - `python_interpreter`: Safe Python code execution for math/code tasks
  - `wikipedia_search`: Wikipedia search integration
  - **File System Tools** (Phase 1):
    - `read_file`: Read file contents with encoding support and size limits (10MB max)
    - `write_file`: Write or append to files with directory auto-creation
    - `list_directory`: List directory contents with optional glob patterns
    - `search_files`: Search for files by name (glob) or content (grep-like)
  - **Text Processing Tools** (Phase 2):
    - `grep`: Pattern matching with regex, context lines, case-insensitive search
    - `sed`: Stream editing with substitution, deletion, and line selection
    - `sort`: Sort lines alphabetically or numerically with unique/reverse options
    - `head_tail`: View first/last N lines of files for quick inspection
  - **Process & System Tools** (Phase 3 - NEW):
    - `ps`: List running processes with filtering and sorting (CPU, memory, name)
    - `kill`: Terminate processes by PID with safety checks for system processes
    - `env`: Read/set environment variables or list all with filtering
    - `which`: Find executable locations in PATH
    - `curl`: HTTP requests (GET, POST, PUT, DELETE) with headers and body
    - `ping`: Network connectivity checks with RTT statistics
  - Plus custom tools (WeatherTool, CalculatorTool, TimeTool) always available
- **Working Directory Sandboxing**: Restrict file operations to specified directory with `--working-directory`
- **Parallel Execution**: Speed up evaluations with `--parallel-workers` (10-50x faster for API models)

## Installation

### Option 1: Install from source (recommended for development)

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Mandark-droid/SMOLTRACE.git
    cd SMOLTRACE
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install in editable mode**:
    ```bash
    pip install -e .
    ```

### Option 2: Install from PyPI (when available)

```bash
pip install smoltrace
```

### Optional Dependencies

For GPU metrics collection (when using local models with `--provider=transformers` or `--provider=ollama`):

```bash
pip install smoltrace[gpu]
```

**Note:** GPU metrics are **enabled by default** for local models (`transformers`, `ollama`). Use `--disable-gpu-metrics` to opt-out if desired.

**Requirements**:
- Python 3.10+
- Smolagents >=1.0.0
- Datasets, HuggingFace Hub
- OpenTelemetry SDK (auto-installed)
- genai-otel-instrument (auto-installed)
- duckduckgo-search (auto-installed)

## Quickstart

### 1. Setup Environment

Create a `.env` file (or export variables):

```bash
# Required
HF_TOKEN=hf_YOUR_HUGGINGFACE_TOKEN

# At least one API key (for --provider=litellm)
MISTRAL_API_KEY=YOUR_MISTRAL_API_KEY
# OR
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY
# OR other providers (see .env.example)
```

### 2. Copy Standard Datasets (First Time Setup)

**New users**: Copy the benchmark and tasks datasets to your HuggingFace account:

```bash
# Copy both datasets (recommended for first-time setup)
smoltrace-copy-datasets

# Or copy only what you need
smoltrace-copy-datasets --only benchmark  # 132 test cases
smoltrace-copy-datasets --only tasks      # 13 test cases
```

This will copy:
- `kshitijthakkar/smoltrace-benchmark-v1` → `{your_username}/smoltrace-benchmark-v1`
- `kshitijthakkar/smoltrace-tasks` → `{your_username}/smoltrace-tasks`

**Why copy?** Having your own copy allows you to:
- Modify datasets for custom testing
- Ensure datasets remain available for your evaluations
- Use your datasets as defaults in your workflows

**Note**: This step is optional. You can use the original datasets directly:
```bash
smoltrace-eval --dataset-name kshitijthakkar/smoltrace-tasks ...
```

### 3. Run Your First Evaluation

**Option A: Push to HuggingFace Hub (default)**

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

This automatically:
- Loads tasks from default dataset
- Evaluates both tool and code agents
- Collects OTEL traces and metrics
- Creates 4 datasets: `{username}/smoltrace-results-{timestamp}`, `{username}/smoltrace-traces-{timestamp}`, `{username}/smoltrace-metrics-{timestamp}`, `{username}/smoltrace-leaderboard`
- Pushes everything to HuggingFace Hub

**Option B: Save Locally as JSON**

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel \
  --output-format json \
  --output-dir ./my_results
```

This creates a timestamped directory with 5 JSON files:
- `results.json` - Test case results
- `traces.json` - OpenTelemetry traces
- `metrics.json` - Aggregated metrics
- `leaderboard_row.json` - Leaderboard entry
- `metadata.json` - Run metadata

### 3. Try Different Providers

**LiteLLM (API models)**
```bash
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type tool
```

**Transformers (GPU models)**
```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both
```

**Ollama (local models)**
```bash
# Ensure Ollama is running: ollama serve
smoltrace-eval \
  --model qwen2.5-coder:3b \
  --provider ollama \
  --agent-type tool \
  --enable-otel \
  --output-format hub
```

**Note**: Use the exact model name as it appears in Ollama (e.g., `mistral:latest`, `llama3.2:3b`, `qwen2.5-coder:3b`). Do not add `ollama/` prefix.

**HuggingFace Inference API (NEW)**
```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --provider inference \
  --agent-type both
```

## Usage

### CLI Arguments

#### Core Arguments

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--model` | Model ID (e.g., `mistral/mistral-small-latest`, `openai/gpt-4`) | **Required** | - |
| `--provider` | Model provider | `litellm` | `litellm`, `inference`, `transformers`, `ollama` |
| `--hf-token` | HuggingFace token (or use `HF_TOKEN` env var) | From env | - |
| `--hf-inference-provider` | HF inference provider (for `--provider=inference`) | None | - |
| `--agent-type` | Agent type to evaluate | `both` | `tool`, `code`, `both` |

#### Tool Configuration (NEW)

| Flag | Description | Default | Available Options |
|------|-------------|---------|-------------------|
| `--enable-tools` | Enable optional smolagents tools (space-separated) | None | Web: `google_search`, `duckduckgo_search`, `visit_webpage`<br>Research: `wikipedia_search`<br>File: `read_file`, `write_file`, `list_directory`, `search_files`<br>Text: `grep`, `sed`, `sort`, `head_tail`<br>Process/System: `ps`, `kill`, `env`, `which`, `curl`, `ping`<br>Other: `user_input` |
| `--search-provider` | Search provider for GoogleSearchTool | `duckduckgo` | `serper`, `brave`, `duckduckgo` |
| `--working-directory` | Working directory for file tools (restricts file operations) | Current dir | Any valid directory path |

#### Task Configuration

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--difficulty` | Filter tasks by difficulty | All tasks | `easy`, `medium`, `hard` |
| `--dataset-name` | HF dataset for tasks | `kshitijthakkar/smoltrace-tasks` | Any HF dataset |
| `--split` | Dataset split to use | `train` | - |

#### Observability & Output

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--enable-otel` | Enable OpenTelemetry tracing/metrics | `False` | - |
| `--run-id` | Unique run identifier (UUID format) | Auto-generated | Any string |
| `--output-format` | Output destination | `hub` | `hub`, `json` |
| `--output-dir` | Directory for JSON output (when `--output-format=json`) | `./smoltrace_results` | - |
| `--private` | Make HuggingFace datasets private | `False` | - |

#### Advanced Configuration

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--prompt-yml` | Path to custom prompt configuration YAML | None | - |
| `--mcp-server-url` | MCP server URL for MCP tools | None | - |
| `--additional-imports` | Additional Python modules for CodeAgent (space-separated) | None | - |
| `--model-args` | Model generation parameters as `key=value` pairs (space-separated) | None | Examples: `temperature=0.7 top_p=0.9 max_tokens=2048 seed=42` |
| `--parallel-workers` | Number of parallel workers for evaluation | `1` | Any integer (recommended: 8 for API models) |
| `--quiet` | Reduce output verbosity | `False` | - |
| `--debug` | Enable debug output | `False` | - |

**Note**: Dataset names (`results`, `traces`, `metrics`, `leaderboard`) are **automatically generated** from your HF username and timestamp. No need to specify repository names!

### Advanced Usage Examples

**1. Model Generation Parameters**

Control model behavior with custom generation parameters:

```bash
# Run with custom temperature, top_p, and max_tokens
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type both \
  --model-args temperature=0.7 top_p=0.9 max_tokens=2048 seed=42 \
  --enable-otel

# For deterministic results with seed
smoltrace-eval \
  --model anthropic/claude-3-opus \
  --provider litellm \
  --model-args temperature=0.0 seed=12345 max_tokens=4096

# With JSON list values (use quotes for complex JSON)
smoltrace-eval \
  --model openai/gpt-4 \
  --model-args temperature=0.8 'stop=["END","STOP"]' max_tokens=1024
```

**Supported Parameters** (vary by provider):
- `temperature` (float): Sampling temperature (0.0-2.0)
- `top_p` (float): Nucleus sampling threshold (0.0-1.0)
- `top_k` (int): Top-K sampling (Anthropic, Cohere)
- `max_tokens` (int): Maximum tokens to generate
- `frequency_penalty` (float): Frequency penalty (-2.0 to 2.0)
- `presence_penalty` (float): Presence penalty (-2.0 to 2.0)
- `seed` (int): Random seed for deterministic sampling
- `stop` (string/list): Stop sequences

**2. MCP Tools Integration**

Run evaluations with external tools via MCP server:

```bash
# Start your MCP server (e.g., http://localhost:8000/sse)
# Then run evaluation with MCP tools
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --mcp-server-url http://localhost:8000/sse \
  --enable-otel
```

**3. Custom Prompt Templates**

Use custom prompt configurations from YAML files:

```bash
# Use one of the built-in templates
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --prompt-yml smoltrace/prompts/code_agent.yaml \
  --enable-otel

# Or use your own custom prompt
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --prompt-yml path/to/my_custom_prompt.yaml \
  --enable-otel
```

Built-in prompt templates available in `smoltrace/prompts/`:
- `code_agent.yaml` - Standard code agent prompts
- `structured_code_agent.yaml` - Structured JSON output format
- `toolcalling_agent.yaml` - Tool calling agent prompts

**3. Additional Python Imports for CodeAgent**

Allow CodeAgent to use additional Python modules:

```bash
# Allow pandas, numpy, and matplotlib imports
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --additional-imports pandas numpy matplotlib \
  --enable-otel

# Combine with MCP tools and custom prompts
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --prompt-yml smoltrace/prompts/code_agent.yaml \
  --mcp-server-url http://localhost:8000/sse \
  --additional-imports pandas numpy json yaml plotly \
  --enable-otel
```

**Note**: Make sure the specified modules are installed in your environment.

**4. Enable Smolagents Tools (NEW)**

Use production-ready tools from smolagents for advanced capabilities:

```bash
# Enable web research tools
export SERPER_API_KEY=your_serper_key  # Optional, for google_search with serper provider
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools visit_webpage \
  --agent-type both \
  --enable-otel

# Enable Google Search with Serper
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools google_search visit_webpage \
  --search-provider serper \
  --agent-type tool \
  --enable-otel

# Enable all available smolagents tools
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools google_search duckduckgo_search visit_webpage wikipedia_search \
  --search-provider duckduckgo \
  --agent-type both \
  --enable-otel
```

**Available Tools**:

*Web & Research*:
- `google_search`: GoogleSearchTool (requires API key for `serper`/`brave`, or use `duckduckgo`)
- `duckduckgo_search`: DuckDuckGoSearchTool (official smolagents version)
- `visit_webpage`: VisitWebpageTool - Extract and read web page content
- `wikipedia_search`: WikipediaSearchTool (requires `pip install wikipedia-api`)

*Code & Computation*:
- `python_interpreter`: PythonInterpreterTool - Safe Python code execution

*File System (Phase 1)*:
- `read_file`: Read file contents with UTF-8/latin-1 encoding support (10MB limit)
- `write_file`: Write/append to files with automatic parent directory creation
- `list_directory`: List directory contents with optional glob pattern filtering
- `search_files`: Search by filename (glob patterns) or file content (grep-like)

*Text Processing (Phase 2)*:
- `grep`: Pattern matching in files with regex, context lines, line numbers, invert match
- `sed`: Stream editing with s/pattern/replacement/, /pattern/d, and line selection
- `sort`: Sort file lines alphabetically/numerically with unique, reverse, case-insensitive options
- `head_tail`: View first N lines (head) or last N lines (tail) of files

*Process & System (Phase 3 - NEW)*:
- `ps`: List running processes with filtering (name) and sorting (CPU, memory, PID, name)
- `kill`: Terminate processes by PID with safety checks for system processes
- `env`: Get/set/list environment variables with filtering
- `which`: Find executable locations in PATH (cross-platform)
- `curl`: HTTP requests (GET, POST, PUT, DELETE) with headers and body
- `ping`: Network connectivity checks with RTT statistics and packet loss

*Other*:
- `user_input`: UserInputTool - Interactive user input during execution

**Default Tools** (always available):
- `get_weather`: WeatherTool (custom)
- `calculator`: CalculatorTool (custom)
- `get_current_time`: TimeTool (custom)

**4b. File System Tools (Phase 1 - NEW)**

Enable file operations for GAIA-style tasks and SWE/DevOps/SRE benchmarks:

```bash
# Enable file tools for code analysis tasks
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file list_directory search_files \
  --working-directory ./my_project \
  --agent-type both \
  --enable-otel

# Enable all file tools for comprehensive file operations
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file write_file list_directory search_files \
  --working-directory /path/to/workspace \
  --agent-type both \
  --enable-otel

# Combine file tools with other tools for research + coding tasks
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file write_file visit_webpage \
  --working-directory ./workspace \
  --agent-type both \
  --enable-otel
```

**File Tool Details**:

1. **`read_file`**: Read file contents
   - Supports UTF-8, latin-1, ASCII encodings
   - 10MB file size limit for safety
   - Path traversal prevention (restricted to working directory)

2. **`write_file`**: Write or append to files
   - Automatic parent directory creation
   - Modes: `write` (overwrite) or `append`
   - System directory protection (blocks `/etc/`, `C:\Windows\`, etc.)
   - UTF-8 encoding (default)

3. **`list_directory`**: List directory contents
   - Optional glob pattern filtering (e.g., `*.py`, `*.json`)
   - Shows file/directory type, size, modification time

4. **`search_files`**: Search for files
   - Search types: `name` (glob patterns) or `content` (grep-like text search)
   - Max results limit (default: 100, configurable)
   - Recursive search in subdirectories

**Security Features**:
- All file operations restricted to `--working-directory` (defaults to current directory)
- Path traversal prevention (`../` blocked)
- System directory blacklist for write operations
- File size limits to prevent memory exhaustion
- UTF-8 text files only for content search

---

**4c. Text Processing Tools (Phase 2 - NEW)**

Enable advanced text processing capabilities for log analysis, data processing, and SRE tasks:

```bash
# Enable text processing tools for log analysis
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file grep sed sort head_tail \
  --working-directory ./logs \
  --agent-type both \
  --enable-otel

# Enable all file + text tools for comprehensive data processing
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools read_file write_file search_files grep sed sort head_tail \
  --working-directory /path/to/workspace \
  --agent-type both \
  --enable-otel

# Text processing for DevOps/SRE tasks
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools grep sed sort head_tail \
  --working-directory ./system_logs \
  --agent-type both \
  --enable-otel
```

**Text Processing Tool Details**:

1. **`grep`**: Pattern matching with regex support
   - Regex pattern matching with Python `re` module
   - Case-insensitive search (`-i`)
   - Context lines: show N lines before/after matches (`-B`, `-A`)
   - Invert match: show non-matching lines (`-v`)
   - Count only: return match count instead of lines
   - Line numbers with match prefix notation

2. **`sed`**: Stream editor for text transformations
   - Substitution: `s/pattern/replacement/` (first occurrence per line)
   - Global substitution: `s/pattern/replacement/` with `global_replace=True`
   - Deletion: `/pattern/d` (delete matching lines)
   - Line selection: `Np` (print specific line number)
   - Case-insensitive mode available
   - Optional output to new file

3. **`sort`**: Sort file lines
   - Alphabetical sorting (default)
   - Numeric sorting (extracts leading numbers from lines)
   - Reverse order
   - Unique lines only (removes duplicates)
   - Case-insensitive sorting
   - Optional output to new file

4. **`head_tail`**: View first or last N lines
   - Head mode: view first N lines of file
   - Tail mode: view last N lines of file
   - Configurable line count (default: 10)
   - Useful for quick file inspection and previews

**Use Cases**:
- **Log Analysis**: Use `grep` to find errors, `sed` to clean log formats, `sort` to organize entries
- **Data Processing**: Filter, transform, and organize text-based data files
- **SRE Tasks**: Analyze system logs, process configuration files, extract metrics
- **DevOps Workflows**: Parse build logs, filter test output, analyze deployment logs

**Security Features** (same as Phase 1):
- All text processing tools restricted to `--working-directory`
- Path traversal prevention
- Regex pattern validation (invalid patterns return errors)
- File size considerations (tools read files into memory)

---

**4d. Process & System Tools (Phase 3 - NEW)**

Enable process management and system interaction for SRE, DevOps, and monitoring tasks:

```bash
# Enable process tools for system monitoring
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools ps env which \
  --agent-type both \
  --enable-otel

# Enable network tools for connectivity testing
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools curl ping which \
  --agent-type both \
  --enable-otel

# Full SRE/DevOps toolkit
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools ps kill env which curl ping grep sed sort \
  --agent-type both \
  --enable-otel
```

**Process & System Tool Details**:

1. **`ps`**: List running processes
   - Filter by process name (case-insensitive substring match)
   - Sort by CPU, memory, PID, or name
   - Configurable result limit (default: 50, max: 500)
   - Returns PID, name, CPU%, memory%, status

2. **`kill`**: Terminate processes by PID
   - Safety checks for system processes (init, systemd, etc.)
   - Protects against self-termination
   - Graceful termination (SIGTERM) or force kill (SIGKILL)
   - Waits for confirmation with timeout

3. **`env`**: Environment variable operations
   - Get specific variable value
   - Set new variable (affects current process and children)
   - List all variables with optional filtering
   - Truncates long values for readability

4. **`which`**: Find executable locations
   - Searches PATH environment variable
   - Cross-platform support (Linux, macOS, Windows)
   - Can return all matches or just first one
   - Handles Windows extensions (.exe, .bat, .cmd)

5. **`curl`**: HTTP requests
   - Methods: GET, POST, PUT, DELETE, HEAD, PATCH
   - Custom headers (JSON format)
   - Request body support
   - Configurable timeout (default: 30s)
   - Response includes status, headers, body

6. **`ping`**: Network connectivity checks
   - ICMP echo requests to host/IP
   - Returns RTT statistics (min/avg/max)
   - Packet loss percentage
   - Cross-platform support (different ping syntax)
   - Configurable count and timeout

**Use Cases**:
- **SRE Monitoring**: Check process health with `ps`, monitor resource usage
- **Incident Response**: Investigate issues with `env`, `which`, check connectivity with `ping`
- **DevOps Automation**: Call APIs with `curl`, verify service availability
- **System Diagnostics**: Find executables with `which`, analyze environment with `env`
- **Health Checks**: Ping services, query HTTP endpoints, list processes

**Security Features**:
- **PsTool**: Read-only process listing (no modification)
- **KillTool**: Protected system processes cannot be terminated
- **EnvTool**: Only affects current process environment (no system-wide changes)
- **WhichTool**: Read-only PATH search
- **CurlTool**: URL validation, timeout protection
- **PingTool**: Count/timeout limits to prevent abuse

**5. HuggingFace Inference API (NEW)**

Use HuggingFace Inference API for hosted models without local GPU:

```bash
# Basic usage with HF Inference API
smoltrace-eval \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --provider inference \
  --agent-type both \
  --enable-otel

# With specific HF inference provider
smoltrace-eval \
  --model Qwen/Qwen2.5-72B-Instruct \
  --provider inference \
  --hf-inference-provider hf-inference-api \
  --agent-type tool \
  --enable-otel

# Combine with smolagents tools
smoltrace-eval \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --provider inference \
  --enable-tools visit_webpage \
  --agent-type both \
  --enable-otel
```

**6. Parallel Execution for Faster Evaluations (NEW)**

Speed up evaluations with parallel workers (ideal for API models):

```bash
# Run 8 tests in parallel (10-50x faster for API models)
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --parallel-workers 8 \
  --agent-type both \
  --enable-otel

# Combine with other features
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools visit_webpage \
  --parallel-workers 8 \
  --agent-type both \
  --enable-otel
```

**Note**: Use `--parallel-workers 1` (default) for GPU models to avoid memory issues. Parallel execution is most beneficial for API models where operations are I/O bound.

### Python API

```python
from smoltrace.core import run_evaluation
import os

# Simple usage - everything is auto-configured!
all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model="openai/gpt-4",
    provider="litellm",
    agent_type="both",
    difficulty="easy",
    enable_otel=True,
    enable_gpu_metrics=False,  # False for API models (default), True for local models
    hf_token=os.getenv("HF_TOKEN")
)

# Results are automatically pushed to HuggingFace Hub as:
# - {username}/smoltrace-results-{timestamp}
# - {username}/smoltrace-traces-{timestamp}
# - {username}/smoltrace-metrics-{timestamp}
# - {username}/smoltrace-leaderboard (updated)

print(f"Evaluation complete! Run ID: {run_id}")
print(f"Total tests: {len(all_results.get('tool', []) + all_results.get('code', []))}")
print(f"Traces collected: {len(trace_data)}")
```

**Advanced: Using MCP Tools, Custom Prompts, and Additional Imports**

```python
from smoltrace.core import run_evaluation
from smoltrace.utils import load_prompt_config
import os

# Load custom prompt configuration
prompt_config = load_prompt_config("smoltrace/prompts/code_agent.yaml")

# Run evaluation with all advanced features
all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model_name="openai/gpt-4",
    agent_types=["code"],  # CodeAgent only
    test_subset="medium",
    dataset_name="kshitijthakkar/smoltrace-tasks",
    split="train",
    enable_otel=True,
    verbose=True,
    debug=False,
    provider="litellm",
    prompt_config=prompt_config,  # Custom prompt template
    mcp_server_url="http://localhost:8000/sse",  # MCP tools
    additional_authorized_imports=["pandas", "numpy", "matplotlib", "json"],  # Extra imports
    enable_gpu_metrics=False,
)

print(f"✅ Evaluation complete!")
print(f"   Run ID: {run_id}")
print(f"   MCP tools were loaded from the server")
print(f"   CodeAgent can use: pandas, numpy, matplotlib, json")
print(f"   Custom prompts applied from YAML")
```

**Advanced: Manual dataset management**

```python
from smoltrace.core import run_evaluation
from smoltrace.utils import (
    get_hf_user_info,
    generate_dataset_names,
    push_results_to_hf,
    compute_leaderboard_row,
    update_leaderboard
)
import os

# Get HF token
hf_token = os.getenv("HF_TOKEN")

# Get username from token
user_info = get_hf_user_info(hf_token)
username = user_info["username"]

# Generate dataset names
results_repo, traces_repo, metrics_repo, leaderboard_repo = generate_dataset_names(username)

print(f"Will create datasets:")
print(f"  Results: {results_repo}")
print(f"  Traces: {traces_repo}")
print(f"  Metrics: {metrics_repo}")
print(f"  Leaderboard: {leaderboard_repo}")

# Run evaluation
all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model="meta-llama/Llama-3.1-8B",
    provider="transformers",
    agent_type="both",
    enable_otel=True,
    enable_gpu_metrics=True,  # Auto-enabled for local models (default)
    hf_token=hf_token
)

# Push to HuggingFace Hub
push_results_to_hf(
    all_results=all_results,
    trace_data=trace_data,
    metric_data=metric_data,
    results_repo=results_repo,
    traces_repo=traces_repo,
    metrics_repo=metrics_repo,
    model_name="meta-llama/Llama-3.1-8B",
    hf_token=hf_token,
    private=False,
    run_id=run_id
)

# Compute leaderboard row
leaderboard_row = compute_leaderboard_row(
    model_name="meta-llama/Llama-3.1-8B",
    all_results=all_results,
    trace_data=trace_data,
    metric_data=metric_data,
    dataset_used=dataset_used,
    results_dataset=results_repo,
    traces_dataset=traces_repo,
    metrics_dataset=metrics_repo,
    agent_type="both",
    run_id=run_id,
    provider="transformers"
)

# Update leaderboard
update_leaderboard(leaderboard_repo, leaderboard_row, hf_token)

print("✅ Evaluation complete and pushed to HuggingFace Hub!")
```

### Custom Tasks

Create a JSON dataset with tasks:

```json
[
  {
    "id": "custom-tool-test",
    "prompt": "What's the weather in Tokyo?",
    "expected_tool": "get_weather",
    "difficulty": "easy",
    "agent_type": "tool",
    "expected_keywords": ["18°C", "Clear"]
  }
]
```

Push to HF: `Dataset.from_list(tasks).push_to_hub("your-username/custom-tasks")`

Load in eval: `--dataset-name your-username/custom-tasks`.

## Available Datasets

SMOLTRACE provides three ready-to-use benchmark datasets:

### 1. Default Task Dataset (Small, Quick Testing)

**Dataset**: `kshitijthakkar/smoltrace-tasks`
- **Size**: 13 test cases
- **Purpose**: Quick validation and testing
- **Difficulty**: Easy to medium tasks
- **Coverage**: Weather queries, calculations, multi-step reasoning

**Usage** (default, no flag needed):
```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

### 2. Comprehensive Benchmark Dataset (Large, Production Evaluation)

**Dataset**: `kshitijthakkar/smoltrace-benchmark-v1`
- **Size**: 132 test cases
- **Source**: Transformed from `smolagents/benchmark-v1`
- **Categories**:
  - **GAIA** (32 rows): Hard difficulty, complex multi-step reasoning
  - **Math** (50 rows): Medium difficulty, mathematical problem-solving
  - **SimpleQA** (50 rows): Easy difficulty, general knowledge questions
- **Purpose**: Comprehensive agent evaluation and leaderboard comparison

**Usage**:

```bash
# Full benchmark evaluation (all 132 test cases)
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --agent-type both \
  --enable-otel

# Filter by difficulty
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --difficulty easy \
  --agent-type both \
  --enable-otel

# Test with specific provider (GPU model)
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --difficulty medium \
  --agent-type both \
  --enable-otel

# Quick validation with code agent only
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-benchmark-v1 \
  --agent-type code \
  --difficulty easy \
  --enable-otel
```

### 3. Operations Benchmark Dataset (APM/AIOps/SRE/DevOps) ⭐ NEW

**Dataset**: `kshitijthakkar/smoltrace-ops-benchmark`
- **Size**: 24 test cases
- **Purpose**: Evaluate agentic capabilities for infrastructure operations and site reliability
- **Categories**:
  - **Log Analysis** (2 tasks): Error detection, rate spike analysis
  - **Metrics Monitoring** (3 tasks): CPU/memory/disk threshold alerts and leak detection
  - **Configuration Management** (3 tasks): K8s validation, env var comparison, Nginx config checks
  - **Incident Response** (3 tasks): 503 diagnosis, DB pool exhaustion, cascade failure analysis
  - **Performance Optimization** (3 tasks): Slow query identification, API latency, cache hit rate
  - **Infrastructure Automation** (3 tasks): Scaling decisions, backup verification, certificate expiry
  - **Security & Compliance** (3 tasks): Vulnerability scanning, access log anomalies, compliance audits
  - **Multi-Service Debugging** (2 tasks): Microservice tracing, distributed transactions
  - **Cost Optimization** (2 tasks): Cloud cost analysis, storage cleanup

**Difficulty Distribution**:
- Easy: 4 tasks (17%)
- Medium: 11 tasks (46%)
- Hard: 9 tasks (37%)

**Required Tools**: File system tools (`read_file`, `write_file`, `list_directory`, `search_files`), `python_interpreter`

**Setup Sample Data** (Required for Ops Benchmark):

The ops benchmark requires sample data files (logs, metrics, configs) to function properly. SMOLTRACE provides an automated setup script:

```bash
# Generate sample data in default ops_sample directory
python setup_ops_sample_data.py

# Or generate in custom directory
python setup_ops_sample_data.py my_custom_dir
```

This creates a complete directory structure with realistic sample data:
- `logs/` - Application and system logs (app.log, mysql-slow.log, access.log, etc.)
- `metrics/` - Performance metrics in JSON format (CPU, memory, disk, database, API, cache)
- `config/` - Configuration files (nginx.conf, database.yml, .env.production, certificates)
- `k8s/` - Kubernetes deployment configurations
- `deployments/` - Deployment history and changelogs
- `backups/` - Backup manifests
- `security/` - Security scan results
- `billing/` - Cloud cost data
- `storage/` - Storage inventory
- `state/` - Service state information

The generated `ops_sample` directory is automatically ignored by git (.gitignore entry added).

**Usage**:

```bash
# STEP 1: Generate sample data first (required!)
python setup_ops_sample_data.py

# STEP 2: Run full ops benchmark (all 24 tasks)
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-ops-benchmark \
  --enable-tools read_file write_file list_directory search_files \
  --working-directory ./ops_sample \
  --agent-type both \
  --enable-otel

# Test specific difficulty level
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --dataset-name kshitijthakkar/smoltrace-ops-benchmark \
  --difficulty medium \
  --enable-tools read_file search_files \
  --working-directory ./ops_sample \
  --agent-type both \
  --enable-otel

# GPU model for ops tasks
smoltrace-eval \
  --model meta-llama/Llama-3.1-70B \
  --provider transformers \
  --dataset-name kshitijthakkar/smoltrace-ops-benchmark \
  --enable-tools read_file list_directory search_files \
  --working-directory ./ops_sample \
  --agent-type both \
  --enable-otel
```

**Key Features**:
- **Real-world scenarios**: Based on actual SRE/DevOps workflows
- **Multi-source analysis**: Tasks require analyzing logs, metrics, and configs together
- **Tool-heavy**: Emphasizes file operations and Python calculations
- **Critical thinking**: Root cause analysis and optimization decisions
- **Security-aware**: Includes vulnerability detection and compliance checks

**Use Cases**:
- Evaluate agent performance on infrastructure tasks
- Benchmark SRE/DevOps automation capabilities
- Test multi-file analysis and correlation
- Assess incident response and troubleshooting skills

**Schema Compatibility:**
All three datasets follow the same base schema:
- `id`: Unique test identifier
- `prompt`: Test question/task
- `difficulty`: `easy`, `medium`, or `hard`
- `agent_type`: `tool`, `code`, or `both`
- `expected_tool`: Tool(s) that should be called
- `expected_tool_calls`: Number of expected tool invocations
- `expected_keywords`: (optional) Keywords to validate in response
- `category`: Test category (gaia/math/simpleqa/log_analysis/metrics_monitoring/etc.)
- `required_tools`: (ops benchmark only) List of tools needed for the task

**Recommendation**:
- Use `smoltrace-tasks` for quick testing and development
- Use `smoltrace-benchmark-v1` for comprehensive general evaluation and leaderboard submissions
- Use `smoltrace-ops-benchmark` for infrastructure operations and SRE/DevOps capability assessment

## Examples

### Basic Tool Agent Eval

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type tool \
  --difficulty easy \
  --enable-otel
```

**Output** (console summary):
```
TOOL AGENT SUMMARY
Total: 5, Success: 4/5 (80.0%)
Tool called: 100%, Correct tool: 80%, Avg steps: 2.6

[SUCCESS] Evaluation complete! Results pushed to HuggingFace Hub.
  Results: https://huggingface.co/datasets/{username}/smoltrace-results-20250125_143000
  Traces: https://huggingface.co/datasets/{username}/smoltrace-traces-20250125_143000
  Metrics: https://huggingface.co/datasets/{username}/smoltrace-metrics-20250125_143000
  Leaderboard: https://huggingface.co/datasets/{username}/smoltrace-leaderboard
```

### OTEL-Enabled Run with GPU Model

```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel
```

**Automatically collects:**
- ✅ OpenTelemetry traces with span details
- ✅ Token usage (prompt, completion, total)
- ✅ Cost tracking
- ✅ GPU metrics (utilization, memory, temperature, power)
- ✅ CO2 emissions

**Automatically creates 4 datasets:**
- Results: Test case outcomes
- Traces: OpenTelemetry span data
- Metrics: GPU metrics and aggregates
- Leaderboard: Aggregate statistics (success rate, tokens, CO2, cost)

### HuggingFace Jobs Integration

Run SMOLTRACE evaluations on HuggingFace's cloud infrastructure with pay-as-you-go billing. Perfect for large-scale evaluations without local GPU requirements.

**Prerequisites:**
- HuggingFace Pro account or Team/Enterprise organization
- `huggingface_hub` Python package: `pip install huggingface_hub`

#### Option 1: CLI (Quick Start)

**Working CPU Example (API models):**
```bash
hf jobs run \
  --flavor cpu-basic \
  -s HF_TOKEN=hf_your_token \
  -s OPENAI_API_KEY=your_openai_api_key \
  python:3.12 \
  bash -c "pip install smoltrace ddgs && smoltrace-eval --model openai/gpt-4 --provider litellm --enable-otel"
```

**GPU Example (Local models):**
```bash
# Note: This triggers the job but may show fief-client warnings during installation
# The warnings don't prevent execution but the command may need refinement
hf jobs run \
  --flavor t4-small \
  -s HF_TOKEN=hf_your_token \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel \
  bash -c "pip install smoltrace ddgs smoltrace[gpu] && smoltrace-eval --model Qwen/Qwen3-4B --provider transformers --enable-otel"
```

**Available Flavors:**
- **CPU**: `cpu-basic`, `cpu-upgrade`
- **GPU**: `t4-small`, `t4-medium`, `l4x1`, `l4x4`, `a10g-small`, `a10g-large`, `a10g-largex2`, `a10g-largex4`, `a100-large`
- **TPU**: `v5e-1x1`, `v5e-2x2`, `v5e-2x4`

#### Option 2: Python API (Programmatic)

```python
from huggingface_hub import run_job

# CPU job for API models (OpenAI, Anthropic, etc.)
job = run_job(
    image="python:3.12",
    command=[
        "bash", "-c",
        "pip install smoltrace ddgs && smoltrace-eval --model openai/gpt-4o-mini --provider litellm --agent-type both --enable-otel"
    ],
    secrets={
        "HF_TOKEN": "hf_your_token",
        "OPENAI_API_KEY": "your_openai_api_key"
    },
    flavor="cpu-basic",
    timeout="1h"
)

print(f"Job ID: {job.id}")
print(f"Job URL: {job.url}")

# GPU job for local models (Qwen, Llama, Mistral, etc.)
job = run_job(
    image="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel",
    command=[
        "bash", "-c",
        "pip install smoltrace ddgs smoltrace[gpu] && smoltrace-eval --model Qwen/Qwen2-4B --provider transformers --agent-type both --enable-otel"
    ],
    secrets={
        "HF_TOKEN": "hf_your_token"
    },
    flavor="t4-small",  # Cost-effective GPU for small models
    timeout="2h"
)

print(f"Job ID: {job.id}")
```

#### Monitor Job Progress

```python
from huggingface_hub import inspect_job, fetch_job_logs

# Check job status
job_status = inspect_job(job_id=job.id)
print(f"Status: {job_status.status.stage}")  # PENDING, RUNNING, COMPLETED, ERROR

# Stream logs in real-time
for log in fetch_job_logs(job_id=job.id):
    print(log, end="")
```

#### Advanced: Scheduled Evaluations

Run evaluations on a schedule (e.g., nightly model comparisons):

```python
from huggingface_hub import create_scheduled_job

# Run every day at 2 AM
create_scheduled_job(
    image="python:3.12",
    command=[
        "pip", "install", "smoltrace", "&&",
        "smoltrace-eval",
        "--model", "openai/gpt-4",
        "--provider", "litellm",
        "--agent-type", "both",
        "--enable-otel"
    ],
    env={
        "HF_TOKEN": "hf_your_token",
        "OPENAI_API_KEY": "sk_your_key"
    },
    schedule="0 2 * * *",  # CRON syntax: 2 AM daily
    flavor="cpu-basic"
)

# Or use preset schedules
create_scheduled_job(..., schedule="@daily")  # Options: @hourly, @daily, @weekly, @monthly
```

**Results:** All datasets are automatically created under your HuggingFace account:
- `{username}/smoltrace-results-{timestamp}`
- `{username}/smoltrace-traces-{timestamp}`
- `{username}/smoltrace-metrics-{timestamp}`
- `{username}/smoltrace-leaderboard` (updated)

**Cost Optimization Tips:**
1. Use `cpu-basic` for API models (OpenAI, Anthropic) - no GPU needed
2. Use `a10g-small` for 7B-13B parameter models - cheapest GPU option
3. Set `timeout` to avoid runaway costs (e.g., `timeout="1h"`)
4. Use `--difficulty easy` for quick testing before full evaluation

**Note:** HuggingFace Jobs are available only to Pro users and Team/Enterprise organizations. Pay-as-you-go billing applies - you only pay for the seconds you use.

## Dataset Cleanup

**Important**: Each SMOLTRACE evaluation creates **3 new datasets** on HuggingFace Hub:
- `{username}/smoltrace-results-{timestamp}`
- `{username}/smoltrace-traces-{timestamp}`
- `{username}/smoltrace-metrics-{timestamp}`

After running multiple evaluations, this can clutter your HuggingFace profile. Use the `smoltrace-cleanup` utility to manage these datasets safely.

### Quick Start

```bash
# Preview what would be deleted (safe, no actual deletion)
smoltrace-cleanup --older-than 7d

# Delete datasets older than 30 days
smoltrace-cleanup --older-than 30d --no-dry-run

# Keep only 5 most recent evaluations
smoltrace-cleanup --keep-recent 5 --no-dry-run

# Delete incomplete runs (missing traces or metrics)
smoltrace-cleanup --incomplete-only --no-dry-run
```

### Cleanup Options

| Flag | Description | Example |
|------|-------------|---------|
| `--older-than DAYS` | Delete datasets older than N days | `--older-than 7d` |
| `--keep-recent N` | Keep only N most recent evaluations | `--keep-recent 5` |
| `--incomplete-only` | Delete only incomplete runs (missing datasets) | `--incomplete-only` |
| `--all` | Delete ALL SMOLTRACE datasets (⚠️ use with caution!) | `--all` |
| `--only TYPE` | Delete only specific dataset type | `--only results` |
| `--no-dry-run` | Actually delete (required for real deletion) | `--no-dry-run` |
| `--yes` | Skip confirmation prompts (for automation) | `--yes` |
| `--preserve-leaderboard` | Preserve leaderboard dataset (default: true) | `--preserve-leaderboard` |

### Safety Features

- **Dry-run by default**: Shows what would be deleted without actually deleting
- **Confirmation prompts**: Requires typing 'DELETE' to confirm deletion
- **Leaderboard protection**: Never deletes your leaderboard by default
- **Protected datasets**: Benchmark and tasks datasets are NEVER deleted (see below)
- **Pattern matching**: Only deletes datasets matching exact SMOLTRACE naming patterns
- **Error handling**: Continues on errors and reports partial success

### Protected Datasets (Never Deleted)

The following datasets are **permanently protected** from deletion and will NEVER be removed by any cleanup command:

- **`{username}/smoltrace-benchmark-v1`** - Comprehensive benchmark dataset (132 test cases)
- **`{username}/smoltrace-tasks`** - Default tasks dataset (13 test cases)

These datasets are protected because they are:
- Critical reference benchmarks used across all evaluations
- Not tied to specific evaluation runs
- Community resources for standardized testing

**Verification**: When running cleanup, you'll see:
```
[INFO] Protected datasets (never deleted): smoltrace-benchmark-v1, smoltrace-tasks
```

This protection applies to ALL cleanup commands, including:
- `smoltrace-cleanup --all`
- `smoltrace-cleanup --older-than X`
- `smoltrace-cleanup --keep-recent N`
- Any other cleanup operation

### CLI Examples

```bash
# 1. Preview deletion (safe, no actual deletion)
smoltrace-cleanup --older-than 7d
# Output: Shows 6 datasets (2 runs) that would be deleted

# 2. Delete datasets older than 30 days with confirmation
smoltrace-cleanup --older-than 30d --no-dry-run
# Prompts: Type 'DELETE' to confirm
# Output: Deletes matching datasets

# 3. Keep only 3 most recent evaluations (batch mode)
smoltrace-cleanup --keep-recent 3 --no-dry-run --yes
# No confirmation prompt, deletes immediately

# 4. Delete incomplete runs (missing traces or metrics)
smoltrace-cleanup --incomplete-only --no-dry-run

# 5. Delete only results datasets, keep traces and metrics
smoltrace-cleanup --only results --older-than 30d --no-dry-run

# 6. Get help
smoltrace-cleanup --help
```

### Python API

```python
from smoltrace import cleanup_datasets

# Preview deletion (dry-run)
result = cleanup_datasets(
    older_than_days=7,
    dry_run=True,
    hf_token="hf_..."
)
print(f"Would delete {result['total_deleted']} datasets from {result['total_scanned']} runs")

# Actual deletion with confirmation skip
result = cleanup_datasets(
    older_than_days=30,
    dry_run=False,
    confirm=False,  # Skip confirmation (use with caution!)
    hf_token="hf_..."
)
print(f"Deleted: {len(result['deleted'])}, Failed: {len(result['failed'])}")

# Keep only N most recent evaluations
result = cleanup_datasets(
    keep_recent=5,
    dry_run=False,
    hf_token="hf_..."
)

# Delete incomplete runs
result = cleanup_datasets(
    incomplete_only=True,
    dry_run=False,
    hf_token="hf_..."
)
```

### Example Output

```
======================================================================
  SMOLTRACE Dataset Cleanup (DRY-RUN)
======================================================================

User: kshitij

Scanning datasets...
[INFO] Discovered 6 results, 6 traces, 6 metrics datasets
[INFO] Grouped into 6 runs (6 complete, 0 incomplete)
[INFO] Filter: Older than 7 days (before 2025-01-18) → 2 to delete, 4 to keep

======================================================================
  Deletion Summary
======================================================================

Runs to delete: 2
Datasets to delete: 6
Runs to keep: 4
Leaderboard: Preserved ✓

Datasets to delete:
  1. kshitij/smoltrace-results-20250108_120000
  2. kshitij/smoltrace-traces-20250108_120000
  3. kshitij/smoltrace-metrics-20250108_120000
  4. kshitij/smoltrace-results-20250110_153000
  5. kshitij/smoltrace-traces-20250110_153000
  6. kshitij/smoltrace-metrics-20250110_153000

======================================================================
  This is a DRY-RUN. No datasets will be deleted.
======================================================================

To actually delete, run with: dry_run=False
```

### Best Practices

1. **Always preview first**: Run with default dry-run to see what would be deleted
2. **Use time-based filters**: Delete old datasets (e.g., `--older-than 30d`)
3. **Keep recent runs**: Maintain a rolling window (e.g., `--keep-recent 10`)
4. **Clean incomplete runs**: Remove failed evaluations with `--incomplete-only`
5. **Automate cleanup**: Add to cron/scheduled tasks with `--yes` flag
6. **Preserve leaderboard**: Never use `--delete-leaderboard` unless absolutely necessary

### Automation Example

Add to your CI/CD or cron job:

```bash
#!/bin/bash
# cleanup_old_datasets.sh

# Delete datasets older than 30 days, keep leaderboard
smoltrace-cleanup \
  --older-than 30d \
  --no-dry-run \
  --yes \
  --preserve-leaderboard

# Exit with error code if any deletions failed
exit $?
```

---

## Dataset Copy Command

### Overview

The `smoltrace-copy-datasets` command allows you to copy the standard benchmark and tasks datasets from the main repository to your own HuggingFace account.

### Usage

```bash
# Copy both datasets (default)
smoltrace-copy-datasets

# Copy only benchmark dataset
smoltrace-copy-datasets --only benchmark

# Copy only tasks dataset
smoltrace-copy-datasets --only tasks

# Make copies private
smoltrace-copy-datasets --private

# Skip confirmation prompts (for automation)
smoltrace-copy-datasets --yes
```

### Options

| Flag | Description | Example |
|------|-------------|---------|
| `--only {benchmark,tasks}` | Copy only specific dataset | `--only benchmark` |
| `--private` | Make copied datasets private | `--private` |
| `--yes`, `-y` | Skip confirmation prompts | `--yes` |
| `--source-user USER` | Source username (default: kshitijthakkar) | `--source-user username` |
| `--token TOKEN` | HuggingFace token | `--token hf_...` |

### What Gets Copied

**Benchmark Dataset** (`smoltrace-benchmark-v1`):
- 132 test cases total
- GAIA: 32 hard difficulty cases
- Math: 50 medium difficulty cases
- SimpleQA: 50 easy difficulty cases
- Source: `kshitijthakkar/smoltrace-benchmark-v1`
- Destination: `{your_username}/smoltrace-benchmark-v1`

**Tasks Dataset** (`smoltrace-tasks`):
- 13 test cases
- Easy to medium difficulty
- Quick validation and testing
- Source: `kshitijthakkar/smoltrace-tasks`
- Destination: `{your_username}/smoltrace-tasks`

### Example Output

```
======================================================================
  SMOLTRACE Dataset Copy
======================================================================

Source: kshitijthakkar
Destination: your_username
Privacy: Public

======================================================================
  Datasets to Copy
======================================================================

1. smoltrace-benchmark-v1
   Comprehensive benchmark dataset (132 test cases)
   kshitijthakkar/smoltrace-benchmark-v1 -> your_username/smoltrace-benchmark-v1

2. smoltrace-tasks
   Default tasks dataset (13 test cases)
   kshitijthakkar/smoltrace-tasks -> your_username/smoltrace-tasks

Checking for existing datasets...
  [NEW] your_username/smoltrace-benchmark-v1
  [NEW] your_username/smoltrace-tasks

======================================================================
  Confirmation
======================================================================

You are about to copy 2 dataset(s) to your account.

Type 'COPY' to confirm (or Ctrl+C to cancel): COPY

======================================================================
  Copying Datasets...
======================================================================

Copying smoltrace-benchmark-v1...
  [1/2] Loading from kshitijthakkar/smoltrace-benchmark-v1...
        Loaded 132 rows
  [2/2] Pushing to your_username/smoltrace-benchmark-v1...
        [OK] Copied successfully

Copying smoltrace-tasks...
  [1/2] Loading from kshitijthakkar/smoltrace-tasks...
        Loaded 13 rows
  [2/2] Pushing to your_username/smoltrace-tasks...
        [OK] Copied successfully

======================================================================
  Copy Summary
======================================================================

[SUCCESS] Copied 2 dataset(s):
  - your_username/smoltrace-benchmark-v1
    URL: https://huggingface.co/datasets/your_username/smoltrace-benchmark-v1
  - your_username/smoltrace-tasks
    URL: https://huggingface.co/datasets/your_username/smoltrace-tasks

======================================================================
Next Steps:
======================================================================

1. Verify datasets in your HuggingFace account
2. Run evaluations with your datasets:
   smoltrace-eval --model openai/gpt-4.1-nano --dataset-name your_username/smoltrace-tasks
   smoltrace-eval --model openai/gpt-4.1-nano --dataset-name your_username/smoltrace-benchmark-v1
```

### Benefits of Copying

1. **Customization**: Modify datasets for your specific testing needs
2. **Availability**: Ensure datasets remain accessible for your workflows
3. **Defaults**: Set your copies as default datasets in configurations
4. **Version Control**: Maintain specific dataset versions for reproducibility
5. **Independence**: Not affected by changes to the original datasets

### Protected from Cleanup

Once copied to your account, these datasets are automatically protected from the `smoltrace-cleanup` command and will never be accidentally deleted.

---

## API Reference

### Evaluation Functions

- **`run_evaluation(...)`**: Main evaluation function; returns `(results_dict, traces_list, metrics_dict, dataset_name, run_id)`.
  - Automatically handles dataset creation and HuggingFace Hub push
  - Parameters: `model`, `provider`, `agent_type`, `difficulty`, `enable_otel`, `enable_gpu_metrics`, `hf_token`, etc.

- **`run_evaluation_flow(args)`**: CLI wrapper for `run_evaluation()` that handles argument parsing

### Dataset Management Functions

- **`generate_dataset_names(username)`**: Auto-generates dataset names from username and timestamp
  - Returns: `(results_repo, traces_repo, metrics_repo, leaderboard_repo)`

- **`get_hf_user_info(token)`**: Fetches HuggingFace user info from token
  - Returns: `{"username": str, "type": str, ...}`

- **`push_results_to_hf(...)`**: Exports results, traces, and metrics to HuggingFace Hub
  - Creates 3 timestamped datasets automatically

- **`compute_leaderboard_row(...)`**: Aggregates metrics for leaderboard entry
  - Returns: Dict with success rate, tokens, CO2, GPU stats, duration, cost, etc.

- **`update_leaderboard(...)`**: Appends new row to leaderboard dataset

### Cleanup Functions

- **`cleanup_datasets(...)`**: Clean up old SMOLTRACE datasets from HuggingFace Hub
  - Parameters: `older_than_days`, `keep_recent`, `incomplete_only`, `dry_run`, etc.

- **`discover_smoltrace_datasets(...)`**: Discover all SMOLTRACE datasets for a user
  - Returns: Dict categorized by type (results, traces, metrics, leaderboard)

- **`group_datasets_by_run(...)`**: Group datasets by evaluation run (timestamp)
  - Returns: List of run dictionaries with completeness status

- **`filter_runs(...)`**: Filter runs by age, count, or completeness
  - Returns: Tuple of (runs_to_delete, runs_to_keep)

Full docs: [huggingface.co/docs/smoltrace](https://huggingface.co/docs/smoltrace).

## Leaderboard

View community rankings at [huggingface.co/datasets/huggingface/smolagents-leaderboard](https://huggingface.co/datasets/huggingface/smolagents-leaderboard). Top models by success rate:

| Model | Agent Type | Success Rate | Avg Steps | Avg Duration (ms) | Total Duration (ms) | Total Tokens | CO2 (g) | Total Cost (USD) |
|-------|------------|--------------|-----------|-------------------|---------------------|--------------|---------|------------------|
| mistral/mistral-large | both | 92.5% | 2.5 | 500.0 | 15000 | 15k | 0.22 | 0.005 |
| meta-llama/Llama-3.1-8B | tool | 88.0% | 2.1 | 450.0 | 12000 | 12k | 0.18 | 0.004 |

Contribute your runs!

## Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/Mandark-droid/SMOLTRACE/blob/main/CONTRIBUTING.md) for guidelines.

1. Fork the repo.
2. Install in dev mode: `pip install -e .[dev]`.
3. Run tests: `pytest`.
4. Submit PR to `main`.

## License

AGPL-3.0. See [LICENSE](https://github.com/Mandark-droid/SMOLTRACE/blob/main/LICENSE).

---

## Common Use Cases

### Test with Easy Tasks Only

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --difficulty easy \
  --output-format json
```

### Compare Tool vs Code Agents

```bash
# Tool agent only
smoltrace-eval --model openai/gpt-4 --provider litellm --agent-type tool

# Code agent only
smoltrace-eval --model openai/gpt-4 --provider litellm --agent-type code

# Compare results in respective output directories
```

### GPU Model Evaluation with Metrics

```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel
```

### Private Results (Don't Share Publicly)

```bash
smoltrace-eval \
  --model your-model \
  --provider litellm \
  --output-format hub \
  --private
```

---

⭐ **Star this repo** to support Smolagents! Questions? [Open an issue](https://github.com/Mandark-droid/SMOLTRACE/issues).
