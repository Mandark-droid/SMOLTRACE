# smoltrace

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/your-username/smoltrace.svg)](https://github.com/your-username/smoltrace/blob/main/LICENSE)
[![PyPI version](https://badge.fury.io/py/smoltrace.svg)](https://badge.fury.io/py/smoltrace)
[![Tests](https://img.shields.io/github/actions/workflow/status/your-username/smoltrace/ci.yml?branch=main&label=tests)](https://github.com/your-username/smoltrace/actions?query=workflow%3Aci)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://huggingface.co/docs/smoltrace/en/index)

**SMOLTRACE** is a comprehensive benchmarking and evaluation framework for [Smolagents](https://huggingface.co/docs/smolagents), Hugging Face's lightweight agent library. It enables seamless testing of `ToolCallingAgent` and `CodeAgent` on custom or HF-hosted task datasets, with built-in support for OpenTelemetry (OTEL) tracing/metrics, results export to Hugging Face Datasets, and automated leaderboard updates.

Designed for reproducibility and scalability, it integrates with HF Spaces, Jobs, and the Datasets library. Evaluate your fine-tuned models, compare agent types, and contribute to community leaderboards—all in a few lines of code.

## Features

- **Task Loading**: Pull evaluation tasks from HF Datasets (e.g., `smolagents/tasks`) or local JSON.
- **Agent Benchmarking**: Run Tool and Code agents on categorized tasks (easy/medium/hard) with tool usage verification.
- **OTEL Integration**: Auto-instrument with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument) for traces (spans, token counts) and metrics (CO2 emissions, GPU utilization).
- **Results Export**: Push structured results as multi-subset Datasets (`eval`, `traces`, `metrics`) to your HF repo.
- **Leaderboard**: Aggregate metrics (success rate, tokens, CO2) and auto-update a shared org leaderboard.
- **CLI & HF Jobs**: Run standalone or in containerized HF environments.

## Installation

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

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    pip install -e .
    ```

For OTEL support (recommended, already included in `requirements-dev.txt`):

```bash
pip install genai-otel-instrument[openinference]
```

**Requirements**:
- Python 3.10+
- Smolagents >=0.1.0
- Datasets, HuggingFace Hub
- OpenTelemetry SDK for traces/metrics

## Quickstart

1. **Set up HF token**: Export `HF_TOKEN` for pushes (get from [HF Settings](https://huggingface.co/settings/tokens)).

2. **Run evaluation** (CLI):

```bash
smoltrace-eval \
  --model mistral/mistral-large-latest \
  --results-repo your-username/agent-results \
  --leaderboard-repo huggingface/smolagents-leaderboard \
  --enable-otel \
  --agent-type both
```

This loads tasks from `huggingface/smolagents/tasks`, evaluates both agent types, collects OTEL data, pushes results to your repo, and updates the org leaderboard.

3. **Programmatic usage**:

```python
from smoltrace import evaluate_agents
from smoltrace.utils import generate_dataset_names, push_results_to_hf
import os

# Assuming HF_TOKEN is set as an environment variable
username = os.getenv("HF_TOKEN") # In a real scenario, you'd get the username from the token
results_repo, traces_repo, metrics_repo, _ = generate_dataset_names(username)

results, traces, metrics, _ = evaluate_agents(
    model="mistral/mistral-large-latest",
    tasks_dataset="huggingface/smolagents/tasks",
    enable_otel=True,
    agent_types=["tool", "code"]
)

# Push to HF
push_results_to_hf(results, traces, metrics, results_repo, traces_repo, metrics_repo, "mistral/mistral-large-latest", os.getenv("HF_TOKEN"))
```

Output: A Dataset with sub-splits (`train_eval`, `train_traces`, `train_metrics`) in your repo.

## Usage

### CLI Arguments

| Flag | Description | Default |
|------|-------------|---------|
| `--model` | Model ID (e.g., `mistral/mistral-large-latest`) | Required |
| `--agent-type` | `tool`, `code`, or `both` | `both` |
| `--difficulty` | Filter tasks: `easy`, `medium`, `hard` | All |
| `--dataset-name` | HF dataset for tasks (e.g., `huggingface/smolagents/tasks`) | `huggingface/smolagents/tasks` |
| `--private` | Make result datasets private | False |
| `--enable-otel` | Enable traces/metrics collection | False |
| `--quiet` / `--debug` | Verbose output toggle | Verbose |

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

⭐ **Star this repo** to support Smolagents! Questions? [Open an issue](https://github.com/your-username/smoltrace/issues).

### Updated useage
Usage:

  1. LiteLLM (API Models) - Default

  smoltrace-eval \
    --model mistral/mistral-small-latest \
    --provider litellm \
    --agent-type both \
    --enable-otel

  2. Transformers (HuggingFace GPU Models)

  smoltrace-eval \
    --model meta-llama/Llama-3.1-8B \
    --provider transformers \
    --agent-type both \
    --enable-otel \
    --enable-gpu-metrics

  3. Ollama (Local Models)

  smoltrace-eval \
    --model mistral \
    --provider ollama \
    --agent-type both \
    --enable-otel
