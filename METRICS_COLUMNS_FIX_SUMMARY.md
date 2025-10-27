# Metrics Dataset Column Fix Summary

**Date:** 2025-10-28
**Status:** ✅ FIXED
**Commit:** `5cca3a2 - Fix: Ensure all 13 metric columns always present in datasets`

## Problem Reported

User observed that ollama-based model evaluations showed:
- ✅ Leaderboard dataset HAD CO2 and power cost values (e.g., CO2: 2.1291g, Power cost: $0.000538)
- ❌ Metrics dataset MISSING `co2_emissions_gco2e` and `power_cost_usd` columns
- ❌ Only 11 columns instead of expected 13 columns

This created an inconsistency where leaderboard showed values that didn't exist in the source metrics dataset.

## Root Cause Analysis

### Investigation Process

1. **Checked genai_otel export**: ✅ Confirmed it exports all 7 metrics correctly
2. **Checked flattening code**: ✅ Metric mapping includes all 7 metrics
3. **Checked batch structure**: ✅ All 7 metrics in same batch
4. **Tested pipeline**: ⚠️ Found the bug!

### The Bug

**Location**: `smoltrace/utils.py:440-441`

```python
# OLD CODE (BUGGY):
for metric in sm["metrics"]:
    # ... get data points ...

    if not data_points:
        continue  # ← SKIPS METRIC ENTIRELY!

    # ... process metric and add to flat_row ...
```

**What Happened:**
1. CO2 and power cost are **cumulative metrics** that start at 0
2. genai_otel samples GPU every 10 seconds
3. If evaluation starts and first metric batch is exported quickly, CO2/power cost may have **empty data point arrays**
4. Code skips metrics with empty data points
5. Those metrics never added to `flat_row` dictionary
6. Dataset created from rows missing those keys → columns don't exist!

**Why Leaderboard Still Showed Values:**
- Leaderboard aggregates from LATER metric batches where CO2/power cost DID accumulate
- But first few metrics datasets were missing the columns entirely

## The Fix

### Code Changes

**File**: `smoltrace/utils.py:422-435`

```python
# NEW CODE (FIXED):
# Create a flat row for this timestamp with ALL expected columns initialized
# This ensures all 13 columns exist even if some metrics have no data points yet
flat_row = {
    "run_id": run_id,
    "service_name": resource_attrs.get("service.name", "unknown"),
    # Initialize ALL expected metric columns with defaults
    "co2_emissions_gco2e": 0.0,
    "power_cost_usd": 0.0,
    "gpu_utilization_percent": 0.0,
    "gpu_memory_used_mib": 0.0,
    "gpu_memory_total_mib": 0.0,
    "gpu_temperature_celsius": 0.0,
    "gpu_power_watts": 0.0,
}

# Process each metric
for metric in sm["metrics"]:
    # ... get data points ...

    if not data_points:
        # Metric has no data points yet (common for CO2/power cost at start)
        # Column already initialized with default value above, so skip to next metric
        continue

    # Metric has data - overwrite default with actual value
    # ...
```

### How It Works Now

1. **Before processing metrics**: Initialize ALL 7 columns to 0.0
2. **During metric processing**:
   - Metrics WITH data points → overwrite 0.0 with actual value
   - Metrics WITHOUT data points → keep 0.0 default
3. **Result**: ALL 13 columns present in EVERY row, EVERY dataset

## Verification

### Test Results

```bash
# Test with only 2-second wait (CO2/power cost won't accumulate)
$ python test_fix.py

[InMemoryMetricExporter] Exported 5 metrics  ← Only 5 metrics!
Column count: 13  ← But 13 columns created!

Metric values in first row:
  co2_emissions_gco2e: 0.0  ← Default value (metric not in batch)
  power_cost_usd: 0.0       ← Default value (metric not in batch)
  gpu_utilization_percent: 0.0
  gpu_memory_used_mib: 312.2265625  ← Actual value (metric was in batch)
```

**Proof**: Even when only 5 metrics exported (CO2 and power cost missing), all 13 columns still created!

### Production Impact

**Before Fix:**
```
Metrics Dataset Schema:
- 11 columns
- Missing: co2_emissions_gco2e, power_cost_usd
```

**After Fix:**
```
Metrics Dataset Schema:
- 13 columns (ALWAYS)
- co2_emissions_gco2e: 0.0 (starts at 0, increases during eval)
- power_cost_usd: 0.0 (starts at 0, increases during eval)
- All other GPU metrics: actual values or 0.0
```

## Benefits

### 1. Consistent Schema ✅
- Metrics dataset ALWAYS has all 13 columns
- No more missing column errors
- TraceMind UI can rely on consistent structure

### 2. Correct Aggregation ✅
- Leaderboard aggregation always has source data
- No more mismatches between leaderboard and metrics
- Values start at 0.0 and increase as evaluation runs

### 3. Better User Experience ✅
- No confusion about missing columns
- Clear that CO2/power cost start at 0 and accumulate
- Consistent behavior across all evaluations

## Migration Guide

### For Existing Evaluations

**No action needed!** The fix is forward-compatible:
- Old datasets (11 columns) continue to work
- New evaluations automatically get 13 columns
- Leaderboard aggregation handles both cases

### For New Evaluations

After pulling latest code:

```bash
# 1. Update SMOLTRACE
cd SMOLTRACE
git pull origin main
pip install -e .

# 2. Run evaluation
smoltrace-eval \
  --model qwen2.5-coder:3b \
  --provider ollama \
  --agent-type tool \
  --enable-otel

# 3. Verify metrics dataset has 13 columns
python -c "
from datasets import load_dataset
ds = load_dataset('your-username/smoltrace-metrics-latest', split='train')
print(f'Columns: {len(ds.column_names)}')
print(ds.column_names)
"
# Output should show 13 columns including co2_emissions_gco2e and power_cost_usd
```

## Technical Details

### Why CO2 and Power Cost Start at 0

genai_otel's GPUMetricsCollector works like this:

1. **Sampling**: Samples GPU power every 10 seconds
2. **Energy Calculation**: `delta_energy_wh = power_w * time_hours`
3. **CO2 Accumulation**: `co2 += delta_energy * carbon_intensity`
4. **Cost Accumulation**: `cost += delta_energy * price_per_kwh`
5. **Export**: Emits cumulative values as metrics

**First 10 seconds**: No samples yet → CO2 and cost are 0
**After 10 seconds**: First sample → CO2 and cost start accumulating
**During evaluation**: Values continuously increase

### Metric Types

**Gauge metrics** (instantaneous values):
- `gpu_utilization_percent`: Current GPU usage
- `gpu_memory_used_mib`: Current memory used
- `gpu_memory_total_mib`: Total memory available
- `gpu_temperature_celsius`: Current temperature
- `gpu_power_watts`: Current power draw

**Sum metrics** (cumulative values):
- `co2_emissions_gco2e`: Total CO2 emitted (starts at 0, increases)
- `power_cost_usd`: Total power cost (starts at 0, increases)

## Files Modified

- `smoltrace/utils.py`: Initialize all columns in `flatten_metrics_for_hf()`
  - Lines 422-435: Column initialization
  - Lines 449-452: Updated comment
- `changelog.md`: Documented fix

## References

- **Commit**: `5cca3a2`
- **Previous Fixes**:
  - `7d8b6b4` - LLM cost tracking in traces
  - Previous session - Metrics flattening enhancement
- **Related Docs**:
  - `COMPLETE_FIX_SUMMARY.md` - Overview of all cost/metrics fixes
  - `METRICS_AGGREGATION_SUMMARY.md` - How metrics are aggregated to leaderboard

## Summary

### What Was Fixed
✅ Metrics dataset now ALWAYS has all 13 columns
✅ CO2 and power cost columns never missing
✅ Consistent schema across all evaluations
✅ Leaderboard aggregation never fails due to missing columns

### User Action Required
1. Pull latest code: `git pull origin main`
2. Reinstall: `pip install -e .`
3. Run new evaluation
4. Verify metrics dataset has 13 columns

### Expected Behavior
- Early metric batches: CO2/power cost = 0.0 (haven't accumulated yet)
- Later metric batches: CO2/power cost > 0.0 (accumulated during eval)
- ALL batches: All 13 columns present

**The issue is now completely resolved!** 🎉
