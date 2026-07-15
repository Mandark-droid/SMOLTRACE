# Model Providers

SMOLTRACE supports four model providers, selected with the `--provider` flag (default `litellm`).

| Provider | `--provider` value | Description |
|----------|--------------------|-------------|
| LiteLLM | `litellm` | API models from OpenAI, Anthropic, Mistral, Groq, Together AI, and more (default). |
| Inference | `inference` | HuggingFace Inference API (`InferenceClientModel`) for hosted models. |
| Transformers | `transformers` | Local HuggingFace models on GPU. |
| Ollama | `ollama` | Local models via an Ollama server. |

## LiteLLM (API models)

The default provider. Requires the corresponding provider API key (see [Configuration](../getting-started/configuration.md)).

```bash
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type tool
```

## HuggingFace Inference API

Use hosted models without a local GPU. Optionally select a specific HF inference provider with `--hf-inference-provider`.

```bash
# Basic usage
smoltrace-eval \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --provider inference \
  --agent-type both \
  --enable-otel

# With a specific HF inference provider
smoltrace-eval \
  --model Qwen/Qwen2.5-72B-Instruct \
  --provider inference \
  --hf-inference-provider hf-inference-api \
  --agent-type tool \
  --enable-otel
```

## Transformers (local GPU models)

Run local HuggingFace models on GPU. GPU metrics are collected by default (install the `smoltrace[gpu]` extra — see [Installation](../getting-started/installation.md)).

```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel
```

## Ollama (local models)

Run local models via a running Ollama server.

```bash
# Ensure Ollama is running: ollama serve
smoltrace-eval \
  --model qwen2.5-coder:3b \
  --provider ollama \
  --agent-type tool \
  --enable-otel \
  --output-format hub
```

!!! note
    Use the exact model name as it appears in Ollama (e.g. `mistral:latest`, `llama3.2:3b`, `qwen2.5-coder:3b`). Do **not** add an `ollama/` prefix.

## GPU Metrics by Provider

GPU metrics (utilization, memory, temperature, power, CO2, cost) are **enabled by default** for local providers (`transformers`, `ollama`) and disabled for API providers (`litellm`, `inference`). Use `--disable-gpu-metrics` to opt out. See [GPU Metrics & Cost](../reference/gpu-metrics.md).
