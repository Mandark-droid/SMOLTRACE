# Quickstart

This guide takes you from a fresh install to your first evaluation.

## 1. Set Up Your Environment

Create a `.env` file (or export the variables):

```bash
# Required
HF_TOKEN=hf_YOUR_HUGGINGFACE_TOKEN

# At least one API key (for --provider=litellm)
MISTRAL_API_KEY=YOUR_MISTRAL_API_KEY
# OR
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY
# OR other providers (see .env.example)
```

See [Configuration](configuration.md) for the full list of environment variables.

## 2. Copy the Standard Datasets (First-Time Setup)

New users can copy the benchmark and tasks datasets into their own HuggingFace account:

```bash
# Copy both datasets (recommended for first-time setup)
smoltrace-copy-datasets

# Or copy only what you need
smoltrace-copy-datasets --only benchmark  # 132 test cases
smoltrace-copy-datasets --only tasks      # 13 test cases
```

This copies:

- `kshitijthakkar/smoltrace-benchmark-v1` → `{your_username}/smoltrace-benchmark-v1`
- `kshitijthakkar/smoltrace-tasks` → `{your_username}/smoltrace-tasks`

!!! note
    This step is optional — you can use the original datasets directly by passing `--dataset-name kshitijthakkar/smoltrace-tasks`. See [Datasets](../guides/datasets.md) and [Dataset Management](../guides/dataset-management.md).

## 3. Run Your First Evaluation

### Option A: Push to HuggingFace Hub (default)

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

This automatically:

- Loads tasks from the default dataset.
- Evaluates both tool and code agents.
- Collects OTEL traces and metrics.
- Creates 4 datasets: `{username}/smoltrace-results-{timestamp}`, `{username}/smoltrace-traces-{timestamp}`, `{username}/smoltrace-metrics-{timestamp}`, and `{username}/smoltrace-leaderboard`.
- Pushes everything to the HuggingFace Hub.

### Option B: Save Locally as JSON

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel \
  --output-format json \
  --output-dir ./my_results
```

This creates a timestamped directory with 5 JSON files: `results.json`, `traces.json`, `metrics.json`, `leaderboard_row.json`, and `metadata.json`.

### Option C: Export to OpenSearch

```bash
pip install smoltrace[opensearch]

smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel \
  --output-format opensearch \
  --opensearch-host localhost \
  --opensearch-port 9200
```

See [Output Formats](../guides/output-formats.md) for the full OpenSearch exporter reference.

## 4. Try Different Providers

=== "LiteLLM (API models)"

    ```bash
    smoltrace-eval \
      --model openai/gpt-4 \
      --provider litellm \
      --agent-type tool
    ```

=== "Transformers (GPU models)"

    ```bash
    smoltrace-eval \
      --model meta-llama/Llama-3.1-8B \
      --provider transformers \
      --agent-type both
    ```

=== "Ollama (local models)"

    ```bash
    # Ensure Ollama is running: ollama serve
    smoltrace-eval \
      --model qwen2.5-coder:3b \
      --provider ollama \
      --agent-type tool \
      --enable-otel \
      --output-format hub
    ```

=== "HuggingFace Inference API"

    ```bash
    smoltrace-eval \
      --model meta-llama/Llama-3.1-70B-Instruct \
      --provider inference \
      --agent-type both \
      --enable-otel
    ```

!!! note
    For Ollama, use the exact model name as it appears in Ollama (e.g. `mistral:latest`, `llama3.2:3b`, `qwen2.5-coder:3b`). Do **not** add an `ollama/` prefix.

See [Model Providers](../guides/providers.md) for details on each provider.

## Next Steps

- [Running Evaluations](../guides/running-evaluations.md) — Full CLI and Python API usage.
- [Agent Tools](../guides/tools.md) — Enable web, file, and system tools.
- [Datasets](../guides/datasets.md) — Understand the available benchmark datasets.
