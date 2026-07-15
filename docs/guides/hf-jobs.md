# HuggingFace Jobs

Run SMOLTRACE evaluations on HuggingFace's cloud infrastructure with pay-as-you-go billing — ideal for large-scale evaluations without local GPU requirements.

!!! note
    HuggingFace Jobs are available only to Pro users and Team/Enterprise organizations. Pay-as-you-go billing applies — you only pay for the seconds you use.

## Prerequisites

- A HuggingFace Pro account or Team/Enterprise organization.
- The `huggingface_hub` Python package: `pip install huggingface_hub`.

## Option 1: CLI (Quick Start)

**CPU (API models):**

```bash
hf jobs run \
  --flavor cpu-basic \
  -s HF_TOKEN=hf_your_token \
  -s OPENAI_API_KEY=your_openai_api_key \
  python:3.12 \
  bash -c "pip install smoltrace ddgs && smoltrace-eval --model openai/gpt-4 --provider litellm --enable-otel"
```

**GPU (local models):**

```bash
hf jobs run \
  --flavor t4-small \
  -s HF_TOKEN=hf_your_token \
  pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel \
  bash -c "pip install smoltrace ddgs smoltrace[gpu] && smoltrace-eval --model Qwen/Qwen3-4B --provider transformers --enable-otel"
```

### Available Flavors

- **CPU**: `cpu-basic`, `cpu-upgrade`
- **GPU**: `t4-small`, `t4-medium`, `l4x1`, `l4x4`, `a10g-small`, `a10g-large`, `a10g-largex2`, `a10g-largex4`, `a100-large`
- **TPU**: `v5e-1x1`, `v5e-2x2`, `v5e-2x4`

## Option 2: Python API

```python
from huggingface_hub import run_job

# CPU job for API models (OpenAI, Anthropic, etc.)
job = run_job(
    image="python:3.12",
    command=[
        "bash", "-c",
        "pip install smoltrace ddgs && smoltrace-eval --model openai/gpt-4o-mini --provider litellm --agent-type both --enable-otel",
    ],
    secrets={
        "HF_TOKEN": "hf_your_token",
        "OPENAI_API_KEY": "your_openai_api_key",
    },
    flavor="cpu-basic",
    timeout="1h",
)

print(f"Job ID: {job.id}")
print(f"Job URL: {job.url}")

# GPU job for local models (Qwen, Llama, Mistral, etc.)
job = run_job(
    image="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel",
    command=[
        "bash", "-c",
        "pip install smoltrace ddgs smoltrace[gpu] && smoltrace-eval --model Qwen/Qwen2-4B --provider transformers --agent-type both --enable-otel",
    ],
    secrets={"HF_TOKEN": "hf_your_token"},
    flavor="t4-small",  # Cost-effective GPU for small models
    timeout="2h",
)
```

## Monitor Job Progress

```python
from huggingface_hub import inspect_job, fetch_job_logs

# Check job status
job_status = inspect_job(job_id=job.id)
print(f"Status: {job_status.status.stage}")  # PENDING, RUNNING, COMPLETED, ERROR

# Stream logs in real time
for log in fetch_job_logs(job_id=job.id):
    print(log, end="")
```

## Scheduled Evaluations

Run evaluations on a schedule (e.g. nightly model comparisons):

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
        "--enable-otel",
    ],
    env={
        "HF_TOKEN": "hf_your_token",
        "OPENAI_API_KEY": "sk_your_key",
    },
    schedule="0 2 * * *",  # CRON: 2 AM daily
    flavor="cpu-basic",
)

# Or use preset schedules: @hourly, @daily, @weekly, @monthly
create_scheduled_job(..., schedule="@daily")
```

## Cost Optimization Tips

1. Use `cpu-basic` for API models (OpenAI, Anthropic) — no GPU needed.
2. Use `a10g-small` for 7B-13B parameter models — the cheapest GPU option.
3. Set `timeout` to avoid runaway costs (e.g. `timeout="1h"`).
4. Use `--difficulty easy` for quick testing before a full evaluation.
