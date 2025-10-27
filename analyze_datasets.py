"""Analyze the datasets to identify missing information."""

import json

from datasets import load_dataset

print("=" * 80)
print("ANALYZING TRACES DATASET")
print("=" * 80)

traces_ds = load_dataset("kshitijthakkar/smoltrace-traces-20251022_184153", split="train")
print(f"\nTotal traces: {len(traces_ds)}")
print(f"Columns: {traces_ds.column_names}")

# Analyze first trace
trace = traces_ds[0]
print(f"\n=== First Trace Analysis ===")
print(f"Trace ID: {trace['trace_id']}")
print(f"Total tokens: {trace['total_tokens']}")
print(f"Total duration: {trace['total_duration_ms']:.2f}ms")
print(f"Total cost: ${trace['total_cost_usd']:.6f}")
print(f"Number of spans: {len(trace['spans'])}")

# Check span details
print(f"\n=== Span Analysis (First 3 spans) ===")
for i, span in enumerate(trace["spans"][:3]):
    print(f"\nSpan {i + 1}: {span['name']}")
    print(f"  Duration: {span['duration_ms']:.2f}ms")

    # Non-null attributes
    non_null_attrs = {k: v for k, v in span["attributes"].items() if v is not None}
    print(f"  Non-null attributes ({len(non_null_attrs)}):")
    for k, v in non_null_attrs.items():
        if len(str(v)) > 100:
            print(f"    - {k}: {str(v)[:100]}...")
        else:
            print(f"    - {k}: {v}")

# Check for missing critical attributes across all spans
print(f"\n=== Missing Critical Attributes Across All Spans ===")
critical_attrs = [
    "test.id",
    "test.difficulty",
    "agent.type",
    "gen_ai.system",
    "gen_ai.request.model",
    "llm.model_name",
    "gen_ai.usage.cost.total",
]

for attr in critical_attrs:
    count = sum(1 for span in trace["spans"] if span["attributes"].get(attr) is not None)
    print(f"  {attr}: {count}/{len(trace['spans'])} spans have this")

print("\n" + "=" * 80)
print("ANALYZING METRICS DATASET")
print("=" * 80)

metrics_ds = load_dataset("kshitijthakkar/smoltrace-metrics-20251022_184153", split="train")
print(f"\nTotal metrics: {len(metrics_ds)}")
print(f"Columns: {metrics_ds.column_names}")

print(f"\n=== Available Metrics ===")
for i, metric in enumerate(metrics_ds):
    print(f"\n{i + 1}. {metric['name']}")
    print(f"   Type: {metric['type']}")
    if metric["data_points"]:
        dp = metric["data_points"][0]
        print(f"   Sample value: {dp['value']}")
        if dp.get("attributes"):
            print(f"   Sample attributes: {dp['attributes']}")

print(f"\n=== Missing Metrics ===")
expected_metrics = [
    "gen_ai.usage.cost.total",
    "gen_ai.usage.cost.per_token",
    "gen_ai.gpu.utilization",  # Expected for GPU jobs only
    "gen_ai.gpu.memory.used",  # Expected for GPU jobs only
]

present_names = [m["name"] for m in metrics_ds]
for metric_name in expected_metrics:
    if metric_name in present_names:
        print(f"  ✓ {metric_name}: PRESENT")
    else:
        note = " (expected for API models)" if "cost" in metric_name else " (only for GPU jobs)"
        print(f"  ✗ {metric_name}: MISSING{note}")

print("\n" + "=" * 80)
print("SUMMARY OF ISSUES")
print("=" * 80)
print("\n1. TRACES DATASET:")
print("   - Token counts are 0 (should have actual values)")
print("   - Cost is 0.0 (should be calculated from tokens)")
print("   - Missing test.id, test.difficulty, agent.type attributes")
print("   - Missing LLM model information (gen_ai.request.model)")
print("\n2. METRICS DATASET:")
print("   - Missing cost metrics (gen_ai.usage.cost.total)")
print("   - GPU metrics missing (expected, since using API models)")
print("\n3. ROOT CAUSES:")
print("   - genai_otel not capturing LiteLLM calls properly")
print("   - Test attributes not being attached to spans")
print("   - Cost calculation not implemented in metrics aggregation")
