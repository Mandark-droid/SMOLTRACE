# GPU Metrics Collection - Complete Fix

## Issue Identified

GPU metrics were disabled for Ollama (local) models because:
1. The `--enable-gpu-metrics` CLI flag was **missing**
2. GPU metrics were hardcoded to only enable for `transformers` provider
3. Users running local models (Ollama) couldn't enable GPU metrics even if they wanted to

## Fixes Applied

### 1. Added `--enable-gpu-metrics` CLI Flag

**File:** `SMOLTRACE/smoltrace/cli.py`

```python
parser.add_argument(
    "--enable-gpu-metrics",
    action="store_true",
    help="Enable GPU metrics collection (auto-enabled for transformers, optional for ollama/local models)",
)
```

### 2. Updated GPU Metrics Logic

**File:** `SMOLTRACE/smoltrace/main.py`

**Before:**
```python
# Hardcoded - only transformers got GPU metrics
enable_gpu_metrics = args.provider == "transformers"
```

**After:**
```python
# Smart logic with explicit override
if hasattr(args, "enable_gpu_metrics") and args.enable_gpu_metrics:
    enable_gpu_metrics = True  # User explicitly requested GPU metrics
elif args.provider == "transformers":
    enable_gpu_metrics = True  # Auto-enable for transformers (HF GPU models)
else:
    enable_gpu_metrics = False  # Default off for API models and ollama unless flag set
```

### 3. force_flush() for Metrics Collection

**File:** `SMOLTRACE/smoltrace/core.py`

Added `force_flush()` before extracting metrics to ensure buffered metrics are exported:

```python
# CRITICAL FIX: Force flush metrics before collection
if metric_exporter and enable_otel:
    try:
        from opentelemetry import metrics as otel_metrics
        meter_provider = otel_metrics.get_meter_provider()
        if hasattr(meter_provider, "force_flush"):
            meter_provider.force_flush(timeout_millis=30000)
            print("[OK] Forced metrics flush before extraction")
    except Exception as e:
        print(f"[WARNING] Failed to force flush metrics: {e}")
```

## Usage

### For Transformers (HuggingFace Models)

GPU metrics are **auto-enabled**:

```bash
smoltrace-eval \
  --model meta-llama/Llama-3.1-8B \
  --provider transformers \
  --agent-type both \
  --enable-otel \
  --output-format hub
```

Output will show:
```
[OK] genai_otel_instrument enabled (GPU metrics: True)
```

### For Ollama (Local Models)

**Must explicitly enable** GPU metrics:

```bash
smoltrace-eval \
  --model hf.co/kshitijthakkar/loggenix-moe-0.3B-A0.1B-smolagents-v0:f16 \
  --provider ollama \
  --agent-type both \
  --enable-otel \
  --enable-gpu-metrics \
  --output-format hub
```

**Before fix:**
```
[OK] genai_otel_instrument enabled (GPU metrics: False)  ❌
```

**After fix (with flag):**
```
[OK] genai_otel_instrument enabled (GPU metrics: True)   ✅
```

### For LiteLLM (API Models)

GPU metrics **not needed** (API models don't use local GPU):

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

This is expected and correct - API models don't have GPU metrics.

## Complete Command for Your Case

Based on your execution, you should run:

```bash
smoltrace-eval \
  --model hf.co/kshitijthakkar/loggenix-moe-0.3B-A0.1B-smolagents-v0:f16 \
  --provider ollama \
  --agent-type both \
  --enable-otel \
  --enable-gpu-metrics \
  --output-format hub
```

## Expected Behavior

### With GPU Available

If you have a GPU and CUDA installed:

```
[OK] genai_otel_instrument enabled (GPU metrics: True)
[OK] Forced metrics flush before extraction
[InMemoryMetricExporter] Retrieved 5 metric batches
[Metrics] Collected 5 GPU metric batches
```

GPU metrics dataset will contain:
- `gen_ai.gpu.utilization` (%)
- `gen_ai.gpu.memory.used` (MiB)
- `gen_ai.gpu.temperature` (°C)
- `gen_ai.co2.emissions` (gCO2e)

### Without GPU (CPU-only)

If running on CPU-only machine:

```
[OK] genai_otel_instrument enabled (GPU metrics: True)
[OK] Forced metrics flush before extraction
[InMemoryMetricExporter] Retrieved 0 metric batches
[Metrics] No GPU metrics collected (empty list - likely CPU-only)
```

Metrics dataset will have:
```json
{
  "run_id": "...",
  "resourceMetrics": []  // Empty - expected for CPU
}
```

This is **normal** and **expected** for CPU-only systems.

## Verification

After running with `--enable-gpu-metrics`, check:

1. **Console output:**
   ```
   [OK] genai_otel_instrument enabled (GPU metrics: True)  ✅
   ```

2. **Metrics dataset on HuggingFace:**
   - Go to `kshitijthakkar/smoltrace-metrics-TIMESTAMP`
   - Check if `resourceMetrics` has data (if GPU available)

3. **TraceMind UI:**
   - Load the datasets
   - Navigate to Screen 4 (Trace Detail)
   - GPU metrics charts should display (if GPU was available)

## Summary

**Total fixes for GPU metrics:**

1. ✅ Added `--enable-gpu-metrics` CLI flag
2. ✅ Updated logic to support explicit enabling for Ollama
3. ✅ Added `force_flush()` to collect buffered metrics
4. ✅ Auto-enable for transformers (HF models)
5. ✅ Manual enable for ollama (local models)

**Files modified:**
- `smoltrace/cli.py` - Added CLI flag
- `smoltrace/main.py` - Smart GPU metrics logic
- `smoltrace/core.py` - force_flush() before collection

**Result:** GPU metrics now work for **all providers** (transformers auto, ollama manual, litellm N/A).
