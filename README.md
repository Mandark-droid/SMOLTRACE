<div align="center">
  <img src="https://raw.githubusercontent.com/Mandark-droid/SMOLTRACE/main/.github/images/Logo.png" alt="SMOLTRACE Logo" width="400"/>

  <h3><em>Tiny Agents. Total Visibility.</em></h3>
  <h3><em>Smol Agents. Smart Metrics.</em></h3>

  [Documentation](https://mandark-droid.github.io/SMOLTRACE/) | [Quickstart](https://mandark-droid.github.io/SMOLTRACE/getting-started/quickstart/) | [PyPI](https://pypi.org/project/smoltrace/) | [Issues](https://github.com/Mandark-droid/SMOLTRACE/issues)
</div>

# smoltrace

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://github.com/Mandark-droid/SMOLTRACE/blob/main/LICENSE)
[![PyPI version](https://badge.fury.io/py/smoltrace.svg)](https://badge.fury.io/py/smoltrace)
[![Downloads](https://static.pepy.tech/badge/smoltrace)](https://pepy.tech/project/smoltrace)
[![Downloads/Month](https://static.pepy.tech/badge/smoltrace/month)](https://pepy.tech/project/smoltrace)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Tests](https://img.shields.io/github/actions/workflow/status/Mandark-droid/SMOLTRACE/test.yml?branch=main&label=tests)](https://github.com/Mandark-droid/SMOLTRACE/actions?query=workflow%3Atest)
[![Docs](https://img.shields.io/badge/docs-stable-blue.svg)](https://mandark-droid.github.io/SMOLTRACE/)

**SMOLTRACE** is a benchmarking and evaluation framework for [Smolagents](https://huggingface.co/docs/smolagents), Hugging Face's lightweight agent library. It runs `ToolCallingAgent` and `CodeAgent` against curated or custom task datasets, auto-instruments everything with OpenTelemetry, and publishes results, traces, metrics, and a leaderboard — with zero configuration.

## Get Started in 30 Seconds

```bash
pip install smoltrace
export HF_TOKEN=hf_your_token
export OPENAI_API_KEY=sk-your_key   # or MISTRAL_API_KEY, ANTHROPIC_API_KEY, ...

smoltrace-eval --model openai/gpt-4.1-nano --provider litellm --agent-type both --enable-otel
```

That's it. One command evaluates both agent types and automatically creates 4 datasets on the Hugging Face Hub:

- `{username}/smoltrace-results-{timestamp}` — per-test-case outcomes
- `{username}/smoltrace-traces-{timestamp}` — OpenTelemetry spans
- `{username}/smoltrace-metrics-{timestamp}` — GPU / CO2 / cost time-series
- `{username}/smoltrace-leaderboard` — aggregate stats, updated every run

No repo names to configure — everything is derived from your `HF_TOKEN`.

## Key Features

- **Zero configuration** — only `HF_TOKEN` required; dataset names are auto-generated from your username
- **Multi-provider** — [LiteLLM](https://mandark-droid.github.io/SMOLTRACE/guides/providers/) (OpenAI, Anthropic, Mistral, Groq, ...), HF Inference API, local Transformers models on GPU, and Ollama
- **OTEL native** — auto-instrumented via [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument): spans, token counts, cost tracking, CO2 emissions
- **GPU metrics** — utilization, memory, temperature, and power tracked by default for local models, flattened for dashboards
- **20+ agent tools** — web search, webpage reading, file system, text processing (`grep`/`sed`/`sort`), and process/system tools (`ps`/`curl`/`ping`), with working-directory sandboxing
- **3 benchmark datasets** — quick tasks (13), comprehensive benchmark (132: GAIA/Math/SimpleQA), and an ops/SRE benchmark (24)
- **Flexible output** — push to HF Hub, save local JSON, or export to OpenSearch with typed mappings
- **Parallel execution** — `--parallel-workers 8` for 10-50x faster API-model evaluations
- **Dataset lifecycle** — `smoltrace-copy-datasets` to bootstrap, `smoltrace-cleanup` to safely prune old runs
- **HF Jobs ready** — run on Hugging Face cloud hardware (CPU to A100) with pay-as-you-go billing

## Installation

```bash
pip install smoltrace                # core
pip install smoltrace[gpu]           # + GPU metrics for local models
pip install smoltrace[opensearch]    # + OpenSearch export
```

Requires Python 3.10+. For development installs and full requirements, see the [installation guide](https://mandark-droid.github.io/SMOLTRACE/getting-started/installation/).

## Usage

### CLI

```bash
# API model via LiteLLM (default provider)
smoltrace-eval --model openai/gpt-4 --provider litellm --agent-type tool

# Local GPU model via Transformers (GPU metrics on by default)
smoltrace-eval --model meta-llama/Llama-3.1-8B --provider transformers --agent-type both

# Local model via Ollama
smoltrace-eval --model qwen2.5-coder:3b --provider ollama --agent-type tool --enable-otel

# HF Inference API
smoltrace-eval --model meta-llama/Llama-3.1-70B-Instruct --provider inference --agent-type both

# Enable agent tools, filter by difficulty, run in parallel
smoltrace-eval \
  --model openai/gpt-4.1-nano \
  --provider litellm \
  --enable-tools visit_webpage read_file grep \
  --working-directory ./workspace \
  --difficulty easy \
  --parallel-workers 8 \
  --enable-otel
```

Other useful flags: `--dataset-name` (custom task dataset), `--model-args temperature=0.7 seed=42`, `--prompt-yml` (custom prompts), `--mcp-server-url` (MCP tools), `--private` (private datasets), `--output-format hub|json|opensearch`.

Full flag reference: [CLI documentation](https://mandark-droid.github.io/SMOLTRACE/reference/cli/).

### Python API

```python
import os
from smoltrace.core import run_evaluation

all_results, trace_data, metric_data, dataset_used, run_id = run_evaluation(
    model="openai/gpt-4",
    provider="litellm",
    agent_type="both",
    enable_otel=True,
    hf_token=os.getenv("HF_TOKEN"),
)
```

Lower-level building blocks (`generate_dataset_names`, `push_results_to_hf`, `compute_leaderboard_row`, `update_leaderboard`, ...) are documented in the [Python API reference](https://mandark-droid.github.io/SMOLTRACE/reference/python-api/).

## Benchmark Datasets

| Dataset | Size | Purpose |
|---------|------|---------|
| [`kshitijthakkar/smoltrace-tasks`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-tasks) (default) | 13 tasks | Quick validation and development |
| [`kshitijthakkar/smoltrace-benchmark-v1`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-benchmark-v1) | 132 tasks | Comprehensive evaluation (GAIA, Math, SimpleQA) |
| [`kshitijthakkar/smoltrace-ops-benchmark`](https://huggingface.co/datasets/kshitijthakkar/smoltrace-ops-benchmark) | 24 tasks | APM / AIOps / SRE / DevOps scenarios |

Copy them to your own account with `smoltrace-copy-datasets`, or bring your own tasks as a HF dataset or local JSON. Schemas, the ops-benchmark sample-data setup, and custom task creation are covered in the [datasets guide](https://mandark-droid.github.io/SMOLTRACE/guides/datasets/).

**Community task datasets:** the [TraceMind-AI collection](https://huggingface.co/collections/MCP-1st-Birthday/tracemind-ai) bundles 40+ ready-to-run task datasets spanning real-world domains — travel, e-commerce, healthcare, finance, DevOps/SRE, AIOps, cybersecurity, and more — for evaluating agents on domain-specific workloads. Point `--dataset-name` at any of them, e.g. `--dataset-name MCP-1st-Birthday/smoltrace-finance-tasks`.

## Output Formats

```bash
--output-format hub          # default: 4 datasets on the HF Hub
--output-format json         # 5 local JSON files (results, traces, metrics, leaderboard row, metadata)
--output-format opensearch   # 4 OpenSearch indexes with typed mappings and bulk indexing
```

Details and OpenSearch connection options: [output formats guide](https://mandark-droid.github.io/SMOLTRACE/guides/output-formats/).

## Run on HuggingFace Jobs

Run evaluations on HF cloud hardware without a local GPU (Pro / Team / Enterprise):

```bash
hf jobs run \
  --flavor cpu-basic \
  -s HF_TOKEN=hf_your_token \
  -s OPENAI_API_KEY=your_key \
  python:3.12 \
  bash -c "pip install smoltrace ddgs && smoltrace-eval --model openai/gpt-4 --provider litellm --enable-otel"
```

GPU flavors (`t4-small` through `a100-large`), the Python API, and scheduled evaluations are covered in the [HF Jobs guide](https://mandark-droid.github.io/SMOLTRACE/guides/hf-jobs/).

## Dataset Management

Each run creates 3 timestamped datasets, so periodic cleanup keeps your profile tidy:

```bash
smoltrace-cleanup --older-than 30d            # dry-run preview (default)
smoltrace-cleanup --keep-recent 5 --no-dry-run  # actually delete
```

Cleanup is dry-run by default, never touches your leaderboard, and permanently protects the benchmark/tasks datasets. See the [dataset management guide](https://mandark-droid.github.io/SMOLTRACE/guides/dataset-management/).

## Leaderboard

Every run appends aggregate stats (success rate, avg steps, tokens, duration, cost, CO2, GPU utilization) to your personal leaderboard, with links back to the run's results, traces, and metrics datasets. Community rankings live at [huggingface/smolagents-leaderboard](https://huggingface.co/datasets/huggingface/smolagents-leaderboard) — contribute your runs! More in the [leaderboard guide](https://mandark-droid.github.io/SMOLTRACE/guides/leaderboard/).

## Documentation

- [Quickstart](https://mandark-droid.github.io/SMOLTRACE/getting-started/quickstart/) — first evaluation in minutes
- [Configuration](https://mandark-droid.github.io/SMOLTRACE/getting-started/configuration/) — environment variables and options
- [Running evaluations](https://mandark-droid.github.io/SMOLTRACE/guides/running-evaluations/) — providers, difficulty filters, parallelism
- [Agent tools](https://mandark-droid.github.io/SMOLTRACE/guides/tools/) — all 20+ tools with security notes
- [GPU metrics & cost](https://mandark-droid.github.io/SMOLTRACE/reference/gpu-metrics/) — what's collected and how it's aggregated
- [Changelog](https://mandark-droid.github.io/SMOLTRACE/community/changelog/)
- [llms.txt](https://mandark-droid.github.io/SMOLTRACE/llms.txt) — machine-readable docs index for LLM agents

## Community

- [Discord](https://discord.gg/6SVz6VKK) — chat with the community (shared with [genai-otel-instrument](https://github.com/Mandark-droid/genai_otel_instrument))
- [TraceVerse Community](https://huggingface.co/traceverse-community) — an open org on the Hub for evaluation & observability datasets, spaces, and real-world MCP apps; join and share your own
- [TraceMind-AI collection](https://huggingface.co/collections/MCP-1st-Birthday/tracemind-ai) — 40+ domain-specific task datasets to evaluate against
- [GitHub Issues](https://github.com/Mandark-droid/SMOLTRACE/issues) — bug reports and feature requests

## Contributing

Contributions welcome! See the [contributing guide](https://mandark-droid.github.io/SMOLTRACE/community/contributing/).

```bash
git clone https://github.com/Mandark-droid/SMOLTRACE.git && cd SMOLTRACE
pip install -e .[dev]
pytest
```

## License

Apache-2.0. See [LICENSE](https://github.com/Mandark-droid/SMOLTRACE/blob/main/LICENSE).

---

⭐ **Star this repo** to support Smolagents! Questions? [Open an issue](https://github.com/Mandark-droid/SMOLTRACE/issues).
