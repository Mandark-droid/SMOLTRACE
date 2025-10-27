# Remaining Implementation Tasks

## Status: ~70% Complete ✅

### Completed So Far:
1. ✅ InMemoryMetricExporter with full OpenTelemetry support
2. ✅ setup_inmemory_otel with run_id generation
3. ✅ run_evaluation with run_id propagation
4. ✅ extract_traces and extract_metrics updated
5. ✅ main.py flow updated

### Remaining Tasks:

## 1. Update push_results_to_hf() in utils.py

**Current signature:**
```python
def push_results_to_hf(
    all_results: Dict,
    trace_data: List[Dict],
    metric_data: List[Dict],  # OLD: List
    ...
)
```

**New signature:**
```python
def push_results_to_hf(
    all_results: Dict,
    trace_data: List[Dict],
    metric_data: Dict,  # NEW: Dict with run_id and resourceMetrics
    results_repo: str,
    traces_repo: str,
    metrics_repo: str,
    model_name: str,
    hf_token: Optional[str],
    private: bool = False,
    run_id: str = None  # NEW parameter
):
```

**Changes needed:**
- Accept run_id parameter
- metric_data is now Dict (not List) with structure:
  ```python
  {
      "run_id": "uuid",
      "resourceMetrics": [...],  # GPU time-series
      "aggregates": [...]  # Trace metrics
  }
  ```
- When pushing metrics dataset, extract just resourceMetrics for OpenTelemetry format
- Add run_id to results and traces before pushing

## 2. Update compute_leaderboard_row() in utils.py

**Current signature:**
```python
def compute_leaderboard_row(
    model_name: str,
    all_results: Dict[str, List[Dict]],
    trace_data: List[Dict],
    metric_data: List[Dict],  # OLD
    dataset_used: str,
    results_dataset: str,
    traces_dataset: str,
    metrics_dataset: str,
    agent_type: str = "both",
)
```

**New signature:**
```python
def compute_leaderboard_row(
    model_name: str,
    all_results: Dict[str, List[Dict]],
    trace_data: List[Dict],
    metric_data: Dict,  # NEW: Dict
    dataset_used: str,
    results_dataset: str,
    traces_dataset: str,
    metrics_dataset: str,
    agent_type: str = "both",
    run_id: str = None,  # NEW
    provider: str = "litellm",  # NEW
) -> Dict:
```

**Changes needed:**
- Add aggregate_gpu_metrics() helper function (from implementation plan)
- Extract GPU metrics from metric_data['resourceMetrics']
- Add new fields to returned dict:
  ```python
  {
      "run_id": run_id,
      "provider": provider,
      "submitted_by": get_hf_username(hf_token),
      "gpu_utilization_avg": ...,
      "gpu_utilization_max": ...,
      "gpu_memory_avg_mib": ...,
      "gpu_memory_max_mib": ...,
      # ... etc
  }
  ```

## 3. Add --run-id CLI argument to cli.py

**Location:** `smoltrace/cli.py`

**Add argument:**
```python
parser.add_argument(
    "--run-id",
    type=str,
    default=None,
    help="Optional unique run identifier (UUID). Generated if not provided."
)
```

## 4. Create Sample Metrics Generator

**Location:** `MockTraceMind/sample_data/generate_sample_metrics.py`

See IMPLEMENTATION_PLAN.md Phase 4 for complete code.

**Purpose:** Generate sample GPU metrics in OpenTelemetry format for UI testing.

## 5. Testing

**Create:** `SMOLTRACE/tests/test_metrics.py`

**Test cases:**
- test_inmemory_metric_exporter()
- test_setup_otel_with_run_id()
- test_extract_metrics_format()
- test_gpu_metrics_aggregation()

## Quick Reference: Key Changes

### Metric Data Structure Change

**OLD (List of flat dicts):**
```python
metric_data = [
    {"name": "gen_ai.co2.emissions", "value": 0.123, ...},
    {"name": "llm.token_count.total", "value": 15000, ...}
]
```

**NEW (Dict with run_id and structured format):**
```python
metric_data = {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "resourceMetrics": [{  # GPU time-series (OpenTelemetry format)
        "resource": {"attributes": [...]},
        "scopeMetrics": [{
            "scope": {"name": "genai.gpu"},
            "metrics": [{
                "name": "gen_ai.gpu.utilization",
                "gauge": {
                    "dataPoints": [
                        {"timeUnixNano": "1760947217774556600", "asInt": "67"},
                        {"timeUnixNano": "1760947227774556600", "asInt": "72"},
                        # ... more data points
                    ]
                }
            }]
        }]
    }],
    "aggregates": [  # Trace-based aggregates (legacy format)
        {"name": "gen_ai.co2.emissions", "value": 0.123},
        {"name": "llm.token_count.total", "value": 15000}
    ]
}
```

### GPU Metrics Aggregation Helper

```python
def aggregate_gpu_metrics(resource_metrics: List[Dict]) -> Dict:
    """Aggregate GPU metrics from time-series data."""
    metrics_by_name = {}

    for rm in resource_metrics:
        for scope_metric in rm.get('scopeMetrics', []):
            for metric in scope_metric.get('metrics', []):
                metric_name = metric.get('name')
                data_points = []

                if 'gauge' in metric:
                    data_points = metric['gauge'].get('dataPoints', [])

                if metric_name not in metrics_by_name:
                    metrics_by_name[metric_name] = []

                for dp in data_points:
                    value = None
                    if dp.get('asInt'):
                        value = int(dp['asInt'])
                    elif dp.get('asDouble') is not None:
                        value = float(dp['asDouble'])

                    if value is not None:
                        metrics_by_name[metric_name].append(value)

    def safe_avg(values):
        return sum(values) / len(values) if values else None

    def safe_max(values):
        return max(values) if values else None

    return {
        "utilization_avg": safe_avg(metrics_by_name.get('gen_ai.gpu.utilization', [])),
        "utilization_max": safe_max(metrics_by_name.get('gen_ai.gpu.utilization', [])),
        "memory_avg": safe_avg(metrics_by_name.get('gen_ai.gpu.memory.used', [])),
        "memory_max": safe_max(metrics_by_name.get('gen_ai.gpu.memory.used', [])),
        "temperature_avg": safe_avg(metrics_by_name.get('gen_ai.gpu.temperature', [])),
        "temperature_max": safe_max(metrics_by_name.get('gen_ai.gpu.temperature', [])),
        "power_avg": safe_avg(metrics_by_name.get('gen_ai.gpu.power', []))
    }
```

## Next Steps

1. Update push_results_to_hf (15 minutes)
2. Update compute_leaderboard_row with GPU aggregation (20 minutes)
3. Add CLI argument (5 minutes)
4. Create sample data generator (10 minutes)
5. Test end-to-end (30 minutes)

**Total remaining: ~80 minutes**

## Files Modified Summary

### Completed:
- ✅ smoltrace/otel.py
- ✅ smoltrace/core.py
- ✅ smoltrace/main.py
- ✅ smoltrace_dataset_structure.md
- ✅ IMPLEMENTATION_PLAN.md

### Remaining:
- ⏳ smoltrace/utils.py (2 functions)
- ⏳ smoltrace/cli.py (1 argument)
- ⏳ MockTraceMind/sample_data/generate_sample_metrics.py (new file)
- ⏳ tests/test_metrics.py (new file - optional)

## No Changes Needed To:
- ❌ genai_otel_instrument (stays unchanged - mission accomplished!)
- ❌ MockTraceMind UI files
- ❌ Existing test cases
