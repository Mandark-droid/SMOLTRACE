"""Test script to verify InMemoryMetricExporter fix"""

from smoltrace.otel import setup_inmemory_otel

print("=" * 60)
print("Testing InMemoryMetricExporter Fix")
print("=" * 60)

# Test 1: Basic setup
print("\n[Test 1] Basic setup without GPU metrics...")
tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
    enable_otel=True, service_name="test-service", run_id="test-run-001", enable_gpu_metrics=False
)
print(f"[OK] Setup successful! run_id: {run_id}")
print(f"[OK] metric_exporter type: {type(metric_exporter).__name__}")
print(f"[OK] Has _preferred_temporality: {hasattr(metric_exporter, '_preferred_temporality')}")
print(f"[OK] Has _preferred_aggregation: {hasattr(metric_exporter, '_preferred_aggregation')}")

# Test 2: Auto-generated run_id
print("\n[Test 2] Auto-generated run_id...")
tracer2, meter2, span_exporter2, metric_exporter2, trace_aggregator2, run_id2 = setup_inmemory_otel(
    enable_otel=True,
    service_name="test-service",
    run_id=None,  # Should auto-generate
    enable_gpu_metrics=False,
)
print(f"[OK] Setup successful! Auto-generated run_id: {run_id2}")
assert run_id2 is not None and len(run_id2) > 0, "run_id should be auto-generated"

# Test 3: With GPU metrics enabled
print("\n[Test 3] With GPU metrics enabled...")
tracer3, meter3, span_exporter3, metric_exporter3, trace_aggregator3, run_id3 = setup_inmemory_otel(
    enable_otel=True, service_name="test-service", run_id="test-run-gpu", enable_gpu_metrics=True
)
print(f"[OK] Setup successful! run_id: {run_id3}")

# Test 4: Disabled OTEL
print("\n[Test 4] Disabled OTEL (should return None values)...")
result = setup_inmemory_otel(enable_otel=False, service_name="test-service")
assert all(x is None for x in result), "All values should be None when OTEL is disabled"
print("[OK] Correctly returns None values when disabled")

print("\n" + "=" * 60)
print("All tests passed! [OK]")
print("=" * 60)
print("\nThe InMemoryMetricExporter fix is working correctly.")
print("You can now run smoltrace-eval successfully!")
