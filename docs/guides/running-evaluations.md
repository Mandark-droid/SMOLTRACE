# Running Evaluations

SMOLTRACE evaluations can be driven from the command line (`smoltrace-eval`) or programmatically via the Python API. This guide covers both, plus advanced options. For the complete flag list, see the [CLI Reference](../reference/cli.md).

## Basic Command

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

- `--model` — the model ID (required).
- `--provider` — one of `litellm`, `inference`, `transformers`, `ollama` (default `litellm`). See [Model Providers](providers.md).
- `--agent-type` — `tool`, `code`, or `both` (default `both`).
- `--enable-otel` — enable OpenTelemetry tracing and metrics.

## Example Output

A tool-agent run prints a console summary:

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

## Advanced Usage

### Model Generation Parameters

Control model behavior with `--model-args` (space-separated `key=value` pairs):

```bash
# Custom temperature, top_p, max_tokens, and seed
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type both \
  --model-args temperature=0.7 top_p=0.9 max_tokens=2048 seed=42 \
  --enable-otel

# Deterministic results with a fixed seed
smoltrace-eval \
  --model anthropic/claude-3-opus \
  --provider litellm \
  --model-args temperature=0.0 seed=12345 max_tokens=4096

# JSON list values (quote complex JSON)
smoltrace-eval \
  --model openai/gpt-4 \
  --model-args temperature=0.8 'stop=["END","STOP"]' max_tokens=1024
```

**Supported parameters** (vary by provider): `temperature`, `top_p`, `top_k`, `max_tokens`, `frequency_penalty`, `presence_penalty`, `seed`, `stop`.

### MCP Tools Integration

Run evaluations with external tools served over an MCP server:

```bash
# Start your MCP server (e.g. http://localhost:8000/sse), then:
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --mcp-server-url http://localhost:8000/sse \
  --enable-otel
```

### Custom Prompt Templates

Supply a prompt configuration YAML with `--prompt-yml`:

```bash
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --prompt-yml smoltrace/prompts/code_agent.yaml \
  --enable-otel
```

Built-in templates in `smoltrace/prompts/`:

- `code_agent.yaml` — standard code agent prompts
- `structured_code_agent.yaml` — structured JSON output format
- `toolcalling_agent.yaml` — tool calling agent prompts

### Additional Python Imports for CodeAgent

Allow the CodeAgent to import extra modules with `--additional-imports`:

```bash
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type code \
  --additional-imports pandas numpy matplotlib \
  --enable-otel
```

!!! note
    Make sure the specified modules are installed in your environment.

### Parallel Execution

Speed up evaluations with `--parallel-workers` — 10-50x faster for API models, where operations are I/O bound:

```bash
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --parallel-workers 8 \
  --agent-type both \
  --enable-otel
```

!!! warning
    Use `--parallel-workers 1` (default) for GPU models to avoid memory issues.

## Python API

```python
from smoltrace.core import run_evaluation
import os

# Simple usage — everything is auto-configured
all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model="openai/gpt-4",
    provider="litellm",
    agent_type="both",
    difficulty="easy",
    enable_otel=True,
    enable_gpu_metrics=False,  # False for API models (default), True for local models
    hf_token=os.getenv("HF_TOKEN"),
)

print(f"Evaluation complete! Run ID: {run_id}")
print(f"Total tests: {len(all_results.get('tool', []) + all_results.get('code', []))}")
print(f"Traces collected: {len(trace_data)}")
```

Results are automatically pushed to the HuggingFace Hub as the four `smoltrace-*` datasets.

### Advanced: MCP Tools, Custom Prompts, and Additional Imports

```python
from smoltrace.core import run_evaluation
from smoltrace.utils import load_prompt_config
import os

prompt_config = load_prompt_config("smoltrace/prompts/code_agent.yaml")

all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model_name="openai/gpt-4",
    agent_types=["code"],
    test_subset="medium",
    dataset_name="kshitijthakkar/smoltrace-tasks",
    split="train",
    enable_otel=True,
    verbose=True,
    debug=False,
    provider="litellm",
    prompt_config=prompt_config,
    mcp_server_url="http://localhost:8000/sse",
    additional_authorized_imports=["pandas", "numpy", "matplotlib", "json"],
    enable_gpu_metrics=False,
)
```

### Advanced: Manual Dataset Management

For full control over dataset creation and pushing, compose the lower-level helpers:

```python
from smoltrace.core import run_evaluation
from smoltrace.utils import (
    get_hf_user_info,
    generate_dataset_names,
    push_results_to_hf,
    compute_leaderboard_row,
    update_leaderboard,
)
import os

hf_token = os.getenv("HF_TOKEN")
user_info = get_hf_user_info(hf_token)
username = user_info["username"]

results_repo, traces_repo, metrics_repo, leaderboard_repo = generate_dataset_names(username)

all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model="meta-llama/Llama-3.1-8B",
    provider="transformers",
    agent_type="both",
    enable_otel=True,
    enable_gpu_metrics=True,  # Auto-enabled for local models
    hf_token=hf_token,
)

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
    run_id=run_id,
)

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
    provider="transformers",
)

update_leaderboard(leaderboard_repo, leaderboard_row, hf_token)
```

See the [Python API reference](../reference/python-api.md) for the full set of functions.

## Common Use Cases

=== "Easy tasks only"

    ```bash
    smoltrace-eval \
      --model mistral/mistral-small-latest \
      --provider litellm \
      --difficulty easy \
      --output-format json
    ```

=== "Compare tool vs code agents"

    ```bash
    smoltrace-eval --model openai/gpt-4 --provider litellm --agent-type tool
    smoltrace-eval --model openai/gpt-4 --provider litellm --agent-type code
    ```

=== "GPU model with metrics"

    ```bash
    smoltrace-eval \
      --model meta-llama/Llama-3.1-8B \
      --provider transformers \
      --agent-type both \
      --enable-otel
    ```

=== "Private results"

    ```bash
    smoltrace-eval \
      --model your-model \
      --provider litellm \
      --output-format hub \
      --private
    ```
