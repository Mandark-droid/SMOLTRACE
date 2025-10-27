"""
Test script to verify cost tracking and CO2/power cost metrics are working.
Run this AFTER reinstalling SMOLTRACE to confirm fixes are applied.
"""
from smoltrace.otel import setup_inmemory_otel
from opentelemetry import trace

print("=" * 70)
print("TEST 1: Verify CostEnrichmentSpanProcessor is added")
print("=" * 70)

# Set up OTEL
tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
    enable_otel=True,
    service_name='test',
    enable_gpu_metrics=True  # Enable GPU metrics to get CO2/power cost
)

# Check span processors
provider = trace.get_tracer_provider()
if hasattr(provider, '_active_span_processor'):
    processors = provider._active_span_processor._span_processors
    print(f"\nSpan processors ({len(processors)}):  ")
    for i, proc in enumerate(processors):
        proc_type = type(proc).__name__
        print(f"  {i+1}. {proc_type}")
        if proc_type == "CostEnrichmentSpanProcessor":
            print("     ✓ Cost tracking processor found!")
        elif proc_type == "SimpleSpanProcessor":
            print("     ✓ Export processor found!")

    # Check order
    if len(processors) >= 2:
        first_proc = type(processors[0]).__name__
        second_proc = type(processors[1]).__name__
        if first_proc == "CostEnrichmentSpanProcessor" and second_proc == "SimpleSpanProcessor":
            print("\n✓ PASS: Processors in correct order (Cost BEFORE Export)")
        else:
            print(f"\n✗ FAIL: Wrong order - {first_proc} before {second_proc}")
else:
    print("✗ FAIL: Could not access span processors")

print("\n" + "=" * 70)
print("TEST 2: Verify genai_otel configuration")
print("=" * 70)

# Check if genai_otel was configured correctly
print("\nExpected genai_otel.instrument() call:")
print("  - enable_gpu_metrics: True")
print("  - enable_cost_tracking: True")
print("  - enable_co2_tracking: True")

print("\nLook for these lines in the output above:")
print("  [OK] CostEnrichmentSpanProcessor added")
print("  [OK] genai_otel_instrument enabled (GPU metrics: True)")

print("\n" + "=" * 70)
print("INSTRUCTIONS")
print("=" * 70)
print("""
If you see:
  ✓ CostEnrichmentSpanProcessor added
  ✓ Processors in correct order

Then the fix IS applied and should work.

If NOT, you need to:
  1. git pull  (get latest code)
  2. pip install -e .  (reinstall SMOLTRACE)
  3. Run this test again
  4. Run an evaluation to verify cost appears in traces

For metrics (CO2 and power cost), they should appear automatically when:
  - enable_gpu_metrics=True
  - Running on a system with GPU
  - genai_otel emits the metrics
""")
