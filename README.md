# smoltrace

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/your-username/smoltrace.svg)](https://github.com/your-username/smoltrace/blob/main/LICENSE)
[![PyPI version](https://badge.fury.io/py/smoltrace.svg)](https://badge.fury.io/py/smoltrace)
[![Tests](https://img.shields.io/github/actions/workflow/status/your-username/smoltrace/ci.yml?branch=main&label=tests)](https://github.com/your-username/smoltrace/actions?query=workflow%3Aci)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://huggingface.co/docs/smoltrace/en/index)

**SMOLTRACE** is a comprehensive benchmarking and evaluation framework for [Smolagents](https://huggingface.co/docs/smolagents), Hugging Face's lightweight agent library. It enables seamless testing of `ToolCallingAgent` and `CodeAgent` on custom or HF-hosted task datasets, with built-in support for OpenTelemetry (OTEL) tracing/metrics, results export to Hugging Face Datasets, and automated leaderboard updates.

Designed for reproducibility and scalability, it integrates with HF Spaces, Jobs, and the Datasets library. Evaluate your fine-tuned models, compare agent types, and contribute to community leaderboards—all in a few lines of code.

## Features

- **Zero Configuration**: Only HF_TOKEN required - automatically generates dataset names from username
- **Task Loading**: Pull evaluation tasks from HF Datasets (e.g., `smolagents/tasks`) or local JSON
- **Agent Benchmarking**: Run Tool and Code agents on categorized tasks (easy/medium/hard) with tool usage verification
- **Multi-Provider Support**:
  - **LiteLLM** (default): API models from OpenAI, Anthropic, Mistral, Groq, Together AI, etc.
  - **Transformers**: Local HuggingFace models on GPU
  - **Ollama**: Local models via Ollama server
- **OTEL Integration**: Auto-instrument with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument) for traces (spans, token counts) and metrics (CO2 emissions, cost tracking)
- **Flexible Output**:
  - Push to HuggingFace Hub (4 separate datasets: results, traces, metrics, leaderboard)
  - Save locally as JSON files (5 files: results, traces, metrics, leaderboard row, metadata)
- **Leaderboard**: Aggregate metrics (success rate, tokens, CO2, cost) and auto-update shared org leaderboard
- **CLI & HF Jobs**: Run standalone or in containerized HF environments

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

For GPU metrics collection (when using `--provider=transformers`):

```bash
pip install smoltrace[gpu]
```

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

### 2. Run Your First Evaluation

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
  --model mistral \
  --provider ollama \
  --agent-type tool
```

## Usage

### CLI Arguments

| Flag | Description | Default | Choices |
|------|-------------|---------|---------|
| `--model` | Model ID (e.g., `mistral/mistral-small-latest`) | **Required** | - |
| `--provider` | Model provider | `litellm` | `litellm`, `transformers`, `ollama` |
| `--hf-token` | HuggingFace token (or use `HF_TOKEN` env var) | From `.env` | - |
| `--agent-type` | Agent type to evaluate | `both` | `tool`, `code`, `both` |
| `--difficulty` | Filter tasks by difficulty | All tasks | `easy`, `medium`, `hard` |
| `--dataset-name` | HF dataset for tasks | `kshitijthakkar/smoalagent-tasks` | Any HF dataset |
| `--split` | Dataset split to use | `train` | - |
| `--enable-otel` | Enable OpenTelemetry tracing/metrics | `False` | - |
| `--output-format` | Output destination | `hub` | `hub`, `json` |
| `--output-dir` | Directory for JSON output (when `--output-format=json`) | `./smoltrace_results` | - |
| `--private` | Make HuggingFace datasets private | `False` | - |
| `--prompt-yml` | Path to custom prompt configuration YAML | None | - |
| `--mcp-server-url` | MCP server URL for MCP tools | None | - |
| `--quiet` | Reduce output verbosity | `False` | - |
| `--debug` | Enable debug output | `False` | - |

### Core API

```python
from smoltrace import evaluate_agents
from smoltrace.utils import compute_leaderboard_row, generate_dataset_names, push_results_to_hf, update_leaderboard
import os

# Assuming HF_TOKEN is set as an environment variable
username = os.getenv("HF_TOKEN") # In a real scenario, you'd get the username from the token
results_repo, traces_repo, metrics_repo, leaderboard_repo = generate_dataset_names(username)

# Evaluate
all_results, trace_data, metric_data, dataset_used = evaluate_agents(
    model="your-model",
    tasks_dataset="huggingface/smolagents/tasks",
    agent_types=["tool"],
    difficulty="hard",
    enable_otel=True
)

# Push results, traces, and metrics
push_results_to_hf(
    all_results, trace_data, metric_data,
    results_repo, traces_repo, metrics_repo,
    "your-model", os.getenv("HF_TOKEN")
)

# Aggregate for leaderboard
leaderboard_row = compute_leaderboard_row(
    model="your-model",
    all_results=all_results,
    trace_data=trace_data,
    metric_data=metric_data,
    dataset_used=dataset_used,
    results_dataset=results_repo,
    traces_dataset=traces_repo,
    metrics_dataset=metrics_repo,
    agent_type="tool"
)

# Update leaderboard (org repo)
update_leaderboard(leaderboard_repo, leaderboard_row, os.getenv("HF_TOKEN"))
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

## Examples

### Basic Tool Agent Eval

```bash
smoltrace-eval --model mistral/mistral-7b --agent-type tool --difficulty easy
```

**Output** (console summary):
```
TOOL AGENT SUMMARY
Total: 5, Success: 4/5 (80.0%)
Tool called: 100%, Correct tool: 80%, Avg steps: 2.6
```

Results pushed to `train_eval` split (15 rows with success metrics, responses).

### OTEL-Enabled Run with Leaderboard

```python
# With traces/metrics
results, traces, metrics = evaluate_agents(
    model="meta-llama/Llama-3.1-8B",
    enable_otel=True
)

# Leaderboard row: {'success_rate': 85.0, 'total_tokens': 12000, 'total_co2_g': 0.15, ...}
leaderboard_row = compute_leaderboard_metrics(results, traces, metrics)
update_leaderboard(leaderboard_row)
```

Pushes `train_traces` (spans with token counts) and `train_metrics` (GPU/CO2 data).

### HF Job Integration

In `hf_run.sh`:

```bash
#!/bin/bash
pip install smoltrace[otel]
smoltrace-eval \
  --model $MODEL_ID \
  --results-repo $HF_USER/agent-results-$(date +%Y%m%d) \
  --leaderboard-repo huggingface/smolagents-leaderboard \
  --enable-otel
```

Submit via HF UI or API.

## API Reference

- `evaluate_agents(...)`: Core eval function; returns `(results_dict, traces_list, metrics_list, dataset_name)`.
- `compute_leaderboard_row(...)`: Aggregates success, tokens, CO2, GPU stats, duration, and cost.
- `push_results_to_hf(...)`: Exports results, traces, and metrics to HF with sub-splits.
- `update_leaderboard(...)`: Appends to org leaderboard.

Full docs: [huggingface.co/docs/smoltrace](https://huggingface.co/docs/smoltrace).

## Leaderboard

View community rankings at [huggingface.co/datasets/huggingface/smolagents-leaderboard](https://huggingface.co/datasets/huggingface/smolagents-leaderboard). Top models by success rate:

| Model | Agent Type | Success Rate | Avg Steps | Avg Duration (ms) | Total Duration (ms) | Total Tokens | CO2 (g) | Total Cost (USD) |
|-------|------------|--------------|-----------|-------------------|---------------------|--------------|---------|------------------|
| mistral/mistral-large | both | 92.5% | 2.5 | 500.0 | 15000 | 15k | 0.22 | 0.005 |
| meta-llama/Llama-3.1-8B | tool | 88.0% | 2.1 | 450.0 | 12000 | 12k | 0.18 | 0.004 |

Contribute your runs!

## Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/your-username/smoltrace/blob/main/CONTRIBUTING.md) for guidelines.

1. Fork the repo.
2. Install in dev mode: `pip install -e .[dev]`.
3. Run tests: `pytest`.
4. Submit PR to `main`.

## License

Apache 2.0. See [LICENSE](https://github.com/your-username/smoltrace/blob/main/LICENSE).

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
