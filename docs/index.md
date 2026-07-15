# SMOLTRACE

*Tiny Agents. Total Visibility. Smol Agents. Smart Metrics.*

**SMOLTRACE** is a comprehensive benchmarking and evaluation framework for [Smolagents](https://huggingface.co/docs/smolagents), Hugging Face's lightweight agent library. It enables seamless testing of `ToolCallingAgent` and `CodeAgent` on custom or HF-hosted task datasets, with built-in support for OpenTelemetry (OTEL) tracing/metrics, results export to Hugging Face Datasets, and automated leaderboard updates.

Designed for reproducibility and scalability, it integrates with HF Spaces, Jobs, and the Datasets library. Evaluate your fine-tuned models, compare agent types, and contribute to community leaderboards — all in a few lines of code.

## Key Features

- **Zero Configuration** — Only `HF_TOKEN` required; dataset names are generated automatically from your username.
- **Task Loading** — Pull evaluation tasks from HF Datasets (e.g. `kshitijthakkar/smoltrace-tasks`) or local JSON.
- **Agent Benchmarking** — Run Tool and Code agents on categorized tasks (easy/medium/hard) with tool-usage verification.
- **Multi-Provider Support** — LiteLLM (API models), HuggingFace Inference API, local Transformers on GPU, and Ollama.
- **OTEL Integration** — Auto-instrument with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument) for traces (spans, token counts) and metrics (CO2 emissions, power cost, GPU utilization).
- **Comprehensive Metrics** — All 7 GPU metrics tracked and aggregated: CO2 emissions (gCO2e), power cost (USD), GPU utilization (%), memory usage (MiB), temperature (°C), and power (W).
- **Flexible Output** — Push to HuggingFace Hub, save locally as JSON, or export to OpenSearch.
- **Optional Agent Tools** — Web search, file system, text processing, and process/system tools enabled on demand.
- **Leaderboard** — Aggregate metrics (success rate, tokens, CO2, cost) and auto-update a shared org leaderboard.
- **CLI & HF Jobs** — Run standalone or in containerized HuggingFace environments.
- **Parallel Execution** — Speed up evaluations with `--parallel-workers` (10-50x faster for API models).

## Quick Start

```bash
pip install smoltrace
```

```bash
smoltrace-eval \
  --model mistral/mistral-small-latest \
  --provider litellm \
  --agent-type both \
  --enable-otel
```

This loads tasks from the default dataset, evaluates both tool and code agents, collects OTEL traces and metrics, and pushes results to the HuggingFace Hub.

## Next Steps

- [Installation](getting-started/installation.md) — Install from source, PyPI, or with optional extras.
- [Quickstart](getting-started/quickstart.md) — Set up your environment and run your first evaluation.
- [Configuration](getting-started/configuration.md) — Environment variables and first-time dataset setup.
- [Running Evaluations](guides/running-evaluations.md) — CLI, Python API, and advanced usage.
- [Model Providers](guides/providers.md) — LiteLLM, Inference API, Transformers, and Ollama.
- [Agent Tools](guides/tools.md) — Web, file system, text processing, and system tools.
- [Datasets](guides/datasets.md) — Available benchmark datasets and custom task creation.
- [Output Formats](guides/output-formats.md) — Hub, JSON, and the OpenSearch exporter.
- [Leaderboard](guides/leaderboard.md) — Community rankings and metric aggregation.

## Community

- [Discord](https://discord.gg/6SVz6VKK) — chat with the community (shared with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument))
- [TraceVerse Community](https://huggingface.co/traceverse-community) — open Hugging Face org for evaluation & observability datasets, spaces, and real-world MCP apps
- [TraceMind-AI collection](https://huggingface.co/collections/MCP-1st-Birthday/tracemind-ai) — 40+ domain-specific task datasets ready to evaluate against
- [GitHub](https://github.com/Mandark-droid/SMOLTRACE)
- [Issues](https://github.com/Mandark-droid/SMOLTRACE/issues)
- [PyPI](https://pypi.org/project/smoltrace/)
- [llms.txt](llms.txt) — a concise, machine-readable index of this documentation for LLM agents

## License

SMOLTRACE is licensed under the **Apache-2.0** License. See [LICENSE](https://github.com/Mandark-droid/SMOLTRACE/blob/main/LICENSE).
