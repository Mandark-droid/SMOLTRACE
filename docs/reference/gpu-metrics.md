# GPU Metrics & Cost

When `--enable-otel` is set, SMOLTRACE auto-instruments evaluation runs with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument) to capture traces (spans, token counts) and metrics (CO2 emissions, power cost, GPU utilization). For local models, GPU hardware metrics are collected as well.

## The 7 Tracked Metrics

All 7 GPU metrics are tracked and aggregated in results and the leaderboard:

| Category | Metric | Unit |
|----------|--------|------|
| Environmental | CO2 emissions | gCO2e |
| Environmental | Power cost | USD |
| Performance | GPU utilization | % |
| Performance | Memory usage | MiB |
| Performance | Temperature | °C |
| Performance | Power | W |

Metrics are stored in a flattened time-series format suited to dashboards and visualization, and aggregated into the leaderboard (see [Leaderboard](../guides/leaderboard.md)).

## Enabling GPU Metrics

GPU metrics are **enabled by default** for local providers (`transformers`, `ollama`). Install the GPU extra:

```bash
pip install smoltrace[gpu]
```

Use `--disable-gpu-metrics` to opt out. For API providers (`litellm`, `inference`), GPU metrics are off by default (there is no local GPU to measure), while token counts and cost tracking still apply.

In the Python API, control this with `enable_gpu_metrics`:

```python
run_evaluation(
    model="meta-llama/Llama-3.1-8B",
    provider="transformers",
    enable_otel=True,
    enable_gpu_metrics=True,  # Auto-enabled for local models
    hf_token=hf_token,
)
```

## What an OTEL Run Collects

A run with `--enable-otel` on a GPU model automatically collects:

- OpenTelemetry traces with span details
- Token usage (prompt, completion, total)
- Cost tracking
- GPU metrics (utilization, memory, temperature, power)
- CO2 emissions

And automatically creates 4 datasets — results, traces, metrics, and the aggregate leaderboard.

```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel
```

## Where Metrics Go

The metrics dataset/index is one of the four outputs of every run:

- **Hub**: `{username}/smoltrace-metrics-{timestamp}`
- **JSON**: `metrics.json`
- **OpenSearch**: `smoltrace-metrics-{timestamp}`

See [Output Formats](../guides/output-formats.md) for details on each destination.
