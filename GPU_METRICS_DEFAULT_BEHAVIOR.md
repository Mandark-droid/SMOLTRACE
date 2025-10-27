# GPU Metrics - Default Enabled for Local Models

## Design Philosophy

**Local models** (running on your hardware) → GPU metrics **enabled by default**
**API models** (OpenAI, Anthropic, etc.) → GPU metrics **disabled** (N/A)

## Behavior Matrix

| Provider | Model Type | GPU Metrics Default | Override Flag |
|---|---|---|---|
| `transformers` | Local HF models on GPU | ✅ **Enabled** | `--disable-gpu-metrics` to opt-out |
| `ollama` | Local models via Ollama | ✅ **Enabled** | `--disable-gpu-metrics` to opt-out |
| `litellm` | API models (OpenAI, etc.) | ❌ Disabled | N/A (no local GPU) |

## Usage Examples

### 1. Transformers (HuggingFace Local Models)

**Default behavior - GPU metrics enabled:**
```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel \
  --output-format hub
```

Output:
```
[OK] genai_otel_instrument enabled (GPU metrics: True)  ✅
```

**Opt-out if desired:**
```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel \
  --disable-gpu-metrics \
  --output-format hub
```

Output:
```
[INFO] GPU metrics disabled by user (--disable-gpu-metrics flag)
[OK] genai_otel_instrument enabled (GPU metrics: False)
```

### 2. Ollama (Local Models)

**Default behavior - GPU metrics enabled:**
```bash
smoltrace-eval \
  --model hf.co/kshitijthakkar/loggenix-moe-0.3B-A0.1B-smolagents-v0:f16 \
  --provider ollama \
  --agent-type both \
  --enable-otel \
  --output-format hub
```

Output:
```
[OK] genai_otel_instrument enabled (GPU metrics: True)  ✅
```

**No flag needed!** GPU metrics are automatically enabled for local models.

**Opt-out if desired:**
```bash
smoltrace-eval \
  --model hf.co/kshitijthakkar/loggenix-moe-0.3B-A0.1B-smolagents-v0:f16 \
  --provider ollama \
  --agent-type both \
  --enable-otel \
  --disable-gpu-metrics \
  --output-format hub
```

### 3. LiteLLM (API Models)

**Default behavior - GPU metrics disabled:**
```bash
smoltrace-eval \
  --model openai/gpt-4 \
  --provider litellm \
  --agent-type both \
  --enable-otel \
  --output-format hub
```

Output:
```
[OK] genai_otel_instrument enabled (GPU metrics: False)
```

This is **correct and expected** - API models don't use your local GPU.

## Logic Implementation

```python
# smoltrace/main.py

# Determine if GPU metrics should be enabled
is_local_model = args.provider in ["transformers", "ollama"]
user_disabled = hasattr(args, "disable_gpu_metrics") and args.disable_gpu_metrics

if user_disabled:
    enable_gpu_metrics = False  # User explicitly disabled
    print("[INFO] GPU metrics disabled by user (--disable-gpu-metrics flag)")
elif is_local_model:
    enable_gpu_metrics = True  # Auto-enable for local models
else:
    enable_gpu_metrics = False  # API models don't need GPU metrics
```

## Why This Design?

### ✅ Pros
1. **Sensible defaults** - Local models = local GPU = collect metrics
2. **Less typing** - Most users want GPU metrics for local models
3. **Opt-out vs opt-in** - Better UX for common case
4. **Clear semantics** - Local vs API is clear distinction

### 📊 Expected Dataset Behavior

#### Local Models (transformers, ollama) - GPU Available

```json
{
  "run_id": "...",
  "resourceMetrics": [
    {
      "resource": {...},
      "scopeMetrics": [{
        "metrics": [
          {"name": "gen_ai.gpu.utilization", ...},
          {"name": "gen_ai.gpu.memory.used", ...},
          {"name": "gen_ai.gpu.temperature", ...},
          {"name": "gen_ai.co2.emissions", ...}
        ]
      }]
    }
  ]
}
```

TraceMind UI will show GPU metrics charts! 📈

#### Local Models - CPU Only (No GPU)

```json
{
  "run_id": "...",
  "resourceMetrics": []  // Empty - expected, no GPU detected
}
```

This is **normal** - genai_otel_instrument detected no GPU.
TraceMind UI will show "N/A" for GPU metrics.

#### API Models (litellm)

```json
{
  "run_id": "...",
  "resourceMetrics": []  // Empty - expected, API models
}
```

This is **expected** - API models don't use local GPU.
TraceMind UI will show "N/A" for GPU metrics.

## Migration Guide

### Old Behavior (Before Fix)

```bash
# For ollama, had to explicitly enable
smoltrace-eval --model ... --provider ollama --enable-gpu-metrics ❌
```

### New Behavior (After Fix)

```bash
# For ollama, auto-enabled by default
smoltrace-eval --model ... --provider ollama ✅

# Only need flag to disable if desired
smoltrace-eval --model ... --provider ollama --disable-gpu-metrics
```

## Summary

**Before:**
- Transformers: GPU metrics on ✅
- Ollama: GPU metrics off ❌ (had to manually enable)
- LiteLLM: GPU metrics off ✅

**After:**
- Transformers: GPU metrics on ✅
- Ollama: GPU metrics on ✅ (auto-enabled!)
- LiteLLM: GPU metrics off ✅

**Result:** All local models get GPU metrics by default! 🎉

## Your Command (Simplified)

**Before (needed extra flag):**
```bash
smoltrace-eval \
  --model hf.co/kshitijthakkar/loggenix-moe-0.3B-A0.1B-smolagents-v0:f16 \
  --provider ollama \
  --agent-type both \
  --enable-otel \
  --enable-gpu-metrics \  # ❌ Had to add this
  --output-format hub
```

**After (automatic):**
```bash
smoltrace-eval \
  --model hf.co/kshitijthakkar/loggenix-moe-0.3B-A0.1B-smolagents-v0:f16 \
  --provider ollama \
  --agent-type both \
  --enable-otel \
  --output-format hub  # ✅ Just works!
```

Much cleaner! 🚀
