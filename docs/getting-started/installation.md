# Installation

## Requirements

- Python 3.10+
- Smolagents >= 1.0.0
- Datasets, HuggingFace Hub
- OpenTelemetry SDK (auto-installed)
- genai-otel-instrument (auto-installed)
- duckduckgo-search (auto-installed)

## Option 1: Install from PyPI

```bash
pip install smoltrace
```

## Option 2: Install from source (recommended for development)

1. **Clone the repository**:

    ```bash
    git clone https://github.com/Mandark-droid/SMOLTRACE.git
    cd SMOLTRACE
    ```

2. **Create and activate a virtual environment**:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3. **Install in editable mode**:

    ```bash
    pip install -e .
    ```

## Optional Dependencies

### GPU Metrics

For GPU metrics collection when using local models (`--provider=transformers` or `--provider=ollama`):

```bash
pip install smoltrace[gpu]
```

!!! note
    GPU metrics are **enabled by default** for local models (`transformers`, `ollama`). Use `--disable-gpu-metrics` to opt out.

### OpenSearch Export

For exporting evaluation results, traces, and metrics to OpenSearch:

```bash
pip install smoltrace[opensearch]
```

This installs `opensearch-py>=2.4.0`. See [Output Formats](../guides/output-formats.md) for usage.

## Command-Line Entry Points

Installing SMOLTRACE provides three CLI commands:

| Command | Purpose |
|---------|---------|
| `smoltrace-eval` | Run agent evaluations (see [Running Evaluations](../guides/running-evaluations.md)) |
| `smoltrace-cleanup` | Manage and delete old evaluation datasets (see [Dataset Management](../guides/dataset-management.md)) |
| `smoltrace-copy-datasets` | Copy standard benchmark and task datasets to your account (see [Dataset Management](../guides/dataset-management.md)) |

## Next Steps

- [Quickstart](quickstart.md) — Run your first evaluation.
- [Configuration](configuration.md) — Set up environment variables and datasets.
