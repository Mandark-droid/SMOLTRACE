"""
Debug script to check what metrics are being collected and flattened.
"""
from smoltrace.otel import setup_inmemory_otel
from smoltrace.utils import flatten_metrics_for_hf
from opentelemetry import trace
import time

print("=" * 70)
print("DEBUGGING METRICS COLLECTION AND FLATTENING")
print("=" * 70)

# Set up OTEL with GPU metrics enabled
print("\n1. Setting up OTEL with GPU metrics enabled...")
tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
    enable_otel=True,
    service_name='test',
    enable_gpu_metrics=True
)

# Wait a bit for metrics to be collected
print("\n2. Waiting 15 seconds for GPU metrics to be collected...")
time.sleep(15)

# Force flush metrics
print("\n3. Forcing metrics flush...")
from opentelemetry import metrics
meter_provider = metrics.get_meter_provider()
if hasattr(meter_provider, 'force_flush'):
    meter_provider.force_flush()

# Get the metrics
print("\n4. Retrieving metrics from exporter...")
all_metrics = metric_exporter.get_metrics_data()
print(f"   Total metric batches: {len(all_metrics)}")

# Show metric names
if all_metrics:
    print(f"\n5. Metric names in first batch:")
    first_batch = all_metrics[0]
    if "scopeMetrics" in first_batch:
        for sm in first_batch["scopeMetrics"]:
            if "metrics" in sm:
                for m in sm["metrics"]:
                    metric_name = m.get("name", "unknown")
                    has_gauge = "gauge" in m
                    has_sum = "sum" in m
                    print(f"     - {metric_name} (gauge={has_gauge}, sum={has_sum})")

# Create metric_data structure
metric_data = {
    "run_id": run_id,
    "resourceMetrics": all_metrics,
    "aggregates": []
}

# Flatten metrics
print(f"\n6. Flattening metrics...")
print("-" * 70)
flat_metrics = flatten_metrics_for_hf(metric_data)
print("-" * 70)

print(f"\n7. Flattening complete!")
print(f"   Total rows created: {len(flat_metrics)}")

if flat_metrics:
    print(f"\n8. Columns in flattened data:")
    columns = list(flat_metrics[0].keys())
    for col in columns:
        print(f"     - {col}")

    print(f"\n9. Checking for CO2 and power cost:")
    has_co2 = 'co2_emissions_gco2e' in flat_metrics[0]
    has_cost = 'power_cost_usd' in flat_metrics[0]
    print(f"     co2_emissions_gco2e present: {has_co2}")
    print(f"     power_cost_usd present: {has_cost}")

    if has_co2:
        print(f"\n     CO2 values in first 3 rows:")
        for i in range(min(3, len(flat_metrics))):
            print(f"       Row {i}: {flat_metrics[i]['co2_emissions_gco2e']}")

    if has_cost:
        print(f"\n     Power cost values in first 3 rows:")
        for i in range(min(3, len(flat_metrics))):
            print(f"       Row {i}: {flat_metrics[i]['power_cost_usd']}")

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)
