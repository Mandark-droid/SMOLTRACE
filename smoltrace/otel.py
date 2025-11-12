# smoltrace/otel.py

import logging
import os
import threading
import uuid
from typing import Dict, List

# OTEL Imports
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

# Smolagents (assume installed)

# from opentelemetry.sdk.metrics.aggregation import AggregationTemporality


os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Optional: Your genai_otel_instrument
try:
    import genai_otel

    GENAI_OTEL_AVAILABLE = True
except ImportError:
    GENAI_OTEL_AVAILABLE = False
    print("Warning: genai-otel-instrument not available; using basic OTEL.")

# ============================================================================
# In-Memory OTEL (Enhanced for genai_otel data)
# ============================================================================


class InMemorySpanExporter(SpanExporter):
    def __init__(self):
        self._spans = []

    def export(self, spans):
        for span in spans:
            span_dict = self._to_dict(span)
            self._spans.append(span_dict)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

    def get_finished_spans(self):
        return self._spans

    def _to_dict(self, span):
        # Map status code from numeric to string for UI compatibility
        status_code = None
        if hasattr(span.status, "status_code"):
            code_value = span.status.status_code.value
            # Map: 0=UNSET, 1=OK, 2=ERROR
            status_map = {0: "UNSET", 1: "OK", 2: "ERROR"}
            status_code = status_map.get(code_value, "UNKNOWN")

        # Clean up span kind - remove "SpanKind." prefix
        kind_str = str(span.kind)
        if kind_str.startswith("SpanKind."):
            kind_str = kind_str.replace("SpanKind.", "")

        d = {
            "trace_id": hex(span.get_span_context().trace_id),
            "span_id": hex(span.get_span_context().span_id),
            "parent_span_id": hex(span.parent.span_id) if span.parent else None,
            "name": span.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": (
                (span.end_time - span.start_time) / 1e6 if span.end_time and span.start_time else 0
            ),
            "attributes": dict(span.attributes),
            "events": [
                {"name": e.name, "attributes": dict(e.attributes), "timestamp": e.timestamp}
                for e in span.events
            ],
            "status": {
                "code": status_code,  # Use string code ("OK", "ERROR", "UNSET")
                "description": (
                    span.status.description if hasattr(span.status, "description") else None
                ),
            },
            "kind": kind_str,  # Cleaned kind without "SpanKind." prefix
            "resource": dict(span.resource.attributes) if span.resource else {},
        }
        # Enrich with genai-specific (from traces)
        attrs = d["attributes"]
        if "llm.token_count.total" in attrs:
            d["total_tokens"] = attrs["llm.token_count.total"]
        if "output.value" in attrs and "tool.name" in attrs:
            d["tool_output"] = attrs["output.value"][:200]  # Truncate

        # Safe attributes conversion (handle seq or mapping)
        def safe_dict(attrs):
            if isinstance(attrs, dict):
                return {str(k): str(v) for k, v in attrs.items()}
            elif hasattr(attrs, "items"):  # Mapping
                return {str(k): str(v) for k, v in attrs.items()}
            else:  # Seq of KeyValue (protobuf)
                return {str(kv.key): self._value_to_str(kv.value) for kv in attrs}

        # Safe conversion for attributes/resource (handle dict, Mapping, or seq/protobuf)
        def safe_attrs_to_dict(attrs):
            if not attrs:
                return {}
            try:
                if isinstance(attrs, dict):
                    return {str(k): str(v) for k, v in attrs.items()}
                elif hasattr(attrs, "items"):
                    return {str(k): str(v) for k, v in attrs.items()}
                else:  # Seq of KeyValue (e.g., protobuf from genai_otel)
                    return {
                        str(kv.key): self._value_to_str(getattr(kv.value, "stringValue", kv.value))
                        for kv in attrs
                    }
            except Exception as e:
                print(f"Warning: Attrs conversion failed: {e}; using empty")
                return {}

        def _value_to_str(val):
            if hasattr(val, "stringValue"):
                return val.stringValue
            elif hasattr(val, "intValue"):
                return str(val.intValue)
            elif hasattr(val, "doubleValue"):
                return str(val.doubleValue)
            elif hasattr(val, "boolValue"):
                return str(val.boolValue)
            else:
                return str(val)

        d["attributes"] = safe_attrs_to_dict(span.attributes)
        if span.resource and span.resource.attributes:
            d["resource"] = {"attributes": safe_attrs_to_dict(span.resource.attributes)}
        else:
            d["resource"] = {}

        return d


class InMemoryMetricExporter(MetricExporter):
    """
    Custom metric exporter that stores metrics in memory for later retrieval.
    This captures GPU metrics from genai_otel_instrument in OpenTelemetry format.
    Compatible with PeriodicExportingMetricReader.
    """

    def __init__(self):

        self._metrics_data = []  # Store all metric records
        self._lock = threading.Lock()

        # Required by PeriodicExportingMetricReader
        # Return CUMULATIVE temporality for all instrument types
        self._preferred_temporality = {
            # Default to CUMULATIVE for all instruments
        }
        self._preferred_aggregation = {
            # Use default aggregations
        }

        print("[InMemoryMetricExporter] Initialized")

    def export(self, metrics_data, timeout_millis=10000, **kwargs):
        """Called by MetricReader to export collected metrics"""
        with self._lock:
            # Convert ResourceMetrics to dict format
            for resource_metrics in metrics_data.resource_metrics:
                metrics_dict = self._convert_to_dict(resource_metrics)
                self._metrics_data.append(metrics_dict)
                print(
                    f"[InMemoryMetricExporter] Exported {len(metrics_dict.get('scopeMetrics', [{}])[0].get('metrics', []))} metrics"
                )
        return MetricExportResult.SUCCESS

    def _convert_to_dict(self, resource_metrics):
        """Convert ResourceMetrics to dict (OpenTelemetry resourceMetrics format)"""
        return {
            "resource": self._resource_to_dict(resource_metrics.resource),
            "scopeMetrics": [
                self._scope_metrics_to_dict(sm) for sm in resource_metrics.scope_metrics
            ],
        }

    def _resource_to_dict(self, resource):
        """Convert Resource to dict"""
        if not resource or not resource.attributes:
            return {"attributes": []}

        return {
            "attributes": [
                {"key": str(k), "value": self._attribute_value_to_dict(v)}
                for k, v in resource.attributes.items()
            ]
        }

    def _attribute_value_to_dict(self, value):
        """Convert attribute value to typed dict"""
        if isinstance(value, str):
            return {"stringValue": value}
        elif isinstance(value, bool):
            return {"boolValue": value}
        elif isinstance(value, int):
            return {"intValue": value}
        elif isinstance(value, float):
            return {"doubleValue": value}
        else:
            return {"stringValue": str(value)}

    def _scope_metrics_to_dict(self, scope_metrics):
        """Convert ScopeMetrics to dict with time-series data points"""
        return {
            "scope": {
                "name": scope_metrics.scope.name if scope_metrics.scope else "unknown",
                "version": (
                    scope_metrics.scope.version
                    if scope_metrics.scope and hasattr(scope_metrics.scope, "version")
                    else None
                ),
            },
            "metrics": [self._metric_to_dict(metric) for metric in scope_metrics.metrics],
        }

    def _metric_to_dict(self, metric):
        """Convert Metric to dict with proper data point structure"""
        from opentelemetry.sdk.metrics.export import Gauge, Histogram, Sum

        metric_dict = {
            "name": metric.name,
            "description": metric.description if hasattr(metric, "description") else "",
            "unit": metric.unit if hasattr(metric, "unit") else "",
        }

        # Handle different metric types
        if isinstance(metric.data, Gauge):
            metric_dict["gauge"] = {
                "dataPoints": [self._data_point_to_dict(dp) for dp in metric.data.data_points]
            }
        elif isinstance(metric.data, Sum):
            metric_dict["sum"] = {
                "dataPoints": [self._data_point_to_dict(dp) for dp in metric.data.data_points],
                "aggregationTemporality": int(metric.data.aggregation_temporality),
                "isMonotonic": metric.data.is_monotonic,
            }
        elif isinstance(metric.data, Histogram):
            metric_dict["histogram"] = {
                "dataPoints": [
                    self._histogram_data_point_to_dict(dp) for dp in metric.data.data_points
                ]
            }

        return metric_dict

    def _data_point_to_dict(self, data_point):
        """Convert DataPoint to dict with timestamp"""
        return {
            "attributes": (
                [
                    {"key": str(k), "value": self._attribute_value_to_dict(v)}
                    for k, v in data_point.attributes.items()
                ]
                if hasattr(data_point, "attributes") and data_point.attributes
                else []
            ),
            "timeUnixNano": str(data_point.time_unix_nano),  # String for precision
            "asInt": (
                str(int(data_point.value))
                if isinstance(data_point.value, (int, float))
                and data_point.value == int(data_point.value)
                else None
            ),
            "asDouble": (
                float(data_point.value)
                if isinstance(data_point.value, (int, float))
                and data_point.value != int(data_point.value)
                else None
            ),
        }

    def _histogram_data_point_to_dict(self, data_point):
        """Convert HistogramDataPoint to dict"""
        return {
            "attributes": (
                [
                    {"key": str(k), "value": self._attribute_value_to_dict(v)}
                    for k, v in data_point.attributes.items()
                ]
                if hasattr(data_point, "attributes") and data_point.attributes
                else []
            ),
            "timeUnixNano": str(data_point.time_unix_nano),
            "count": data_point.count,
            "sum": data_point.sum if hasattr(data_point, "sum") else None,
            "bucketCounts": (
                list(data_point.bucket_counts) if hasattr(data_point, "bucket_counts") else []
            ),
            "explicitBounds": (
                list(data_point.explicit_bounds) if hasattr(data_point, "explicit_bounds") else []
            ),
        }

    def get_metrics_data(self):
        """Retrieve all collected metrics in OpenTelemetry resourceMetrics format"""
        with self._lock:
            print(f"[InMemoryMetricExporter] Retrieved {len(self._metrics_data)} metric batches")
            return list(self._metrics_data)

    def clear(self):
        """Clear stored metrics"""
        with self._lock:
            self._metrics_data.clear()
            print("[InMemoryMetricExporter] Cleared metrics")

    def shutdown(self, timeout_millis=30000, **kwargs):
        """Cleanup on shutdown"""
        self.clear()
        return True

    def force_flush(self, timeout_millis=10000, **kwargs):
        """Force flush (no-op for in-memory)"""
        return True


class TraceMetricsAggregator:
    def __init__(self):
        self._metrics = []

    def collect_all(self, trace_data: List[Dict] = None, all_results: List[Dict] = None):
        try:
            if not trace_data:
                print("No traces; returning empty")
                return []

            print(
                f"Aggregating metrics from {len(trace_data)} traces + {len(all_results or [])} results"
            )
            self._metrics = self._aggregate_from_traces(trace_data, all_results)
            print(f"Collected {len(self._metrics)} metrics from traces")
        except Exception as e:
            print(f"Error aggregating from traces: {e}")
            import traceback

            traceback.print_exc()  # Show exact line
            self._metrics = []
        return self._metrics

    def _aggregate_from_traces(self, trace_data: List[Dict], all_results: List[Dict]) -> List[Dict]:
        # Create success lookup from results
        success_map = {
            r["test_id"]: r["success"]
            for results_list in all_results.values()
            for r in results_list
        }

        # Aggregate from spans within traces
        total_success = 0
        total_tool_calls = 0
        total_steps = 0
        test_count = 0
        total_tokens = 0
        total_cost = 0.0

        for trace_item in trace_data:
            # Use the aggregated trace-level metrics
            if trace_item.get("total_tokens"):
                total_tokens += int(trace_item["total_tokens"])
            if trace_item.get("total_cost_usd"):
                total_cost += float(trace_item["total_cost_usd"])

            # Find test evaluation spans
            for span in trace_item.get("spans", []):
                attrs = span.get("attributes", {})

                # Check if this is a test evaluation span
                test_id = attrs.get("test.id")
                if test_id:
                    test_count += 1
                    total_success += 1 if success_map.get(test_id, False) else 0

                    # Get test-specific metrics from span attributes
                    tool_calls = attrs.get("tests.tool_calls", "0")
                    steps = attrs.get("tests.steps", "0")

                    try:
                        total_tool_calls += int(tool_calls)
                    except (ValueError, TypeError):
                        pass

                    try:
                        total_steps += int(steps)
                    except (ValueError, TypeError):
                        pass

        # CO2 estimate (based on tokens)
        co2_total = total_tokens / 1000 * 0.0004 if total_tokens > 0 else 0

        print(
            f"  Aggregated: {test_count} tests, {total_success} success, {total_tokens} tokens, ${total_cost:.6f}, {co2_total:.4f}g CO2"
        )

        # Build metrics with actual data
        metrics = [
            {
                "name": "tests.successful",
                "type": "counter",
                "data_points": [
                    {
                        "value": {"value": total_success},
                        "attributes": {
                            "total_tests": test_count,
                            "success_rate": (
                                round(total_success / test_count * 100, 2) if test_count else 0
                            ),
                        },
                    }
                ],
            },
            {
                "name": "tests.tool_calls",
                "type": "histogram",
                "data_points": [
                    {
                        "value": {
                            "sum": total_tool_calls,
                            "count": test_count,
                            "avg": round(total_tool_calls / test_count, 2) if test_count else 0,
                        },
                        "attributes": {},
                    }
                ],
            },
            {
                "name": "tests.steps",
                "type": "histogram",
                "data_points": [
                    {
                        "value": {
                            "sum": total_steps,
                            "count": test_count,
                            "avg": round(total_steps / test_count, 2) if test_count else 0,
                        },
                        "attributes": {},
                    }
                ],
            },
            {
                "name": "llm.token_count.total",
                "type": "sum",
                "unit": "tokens",
                "data_points": [{"value": {"value": total_tokens}, "attributes": {}}],
            },
            {
                "name": "gen_ai.usage.cost.total",
                "type": "sum",
                "unit": "USD",
                "data_points": [{"value": {"value": round(total_cost, 6)}, "attributes": {}}],
            },
            {
                "name": "gen_ai.co2.emissions",
                "type": "sum",
                "unit": "gCO2e",
                "data_points": [{"value": {"value": round(co2_total, 4)}, "attributes": {}}],
            },
        ]

        return metrics

    def flatten_attributes(self, attrs):
        """Handle ALL attribute formats: flat dict, array of dicts, OR raw protobuf."""
        flat_attrs = {}

        # Case 1: Already FLAT dict (from InMemorySpanExporter)
        if isinstance(attrs, dict):
            return attrs

        # Case 2: ARRAY of {"key": "test.id", "value": {...}}
        if isinstance(attrs, list):
            for kv in attrs:
                if isinstance(kv, dict) and "key" in kv and "value" in kv:
                    key = kv["key"]
                    val = kv["value"]

                    # Handle NESTED DICT
                    if isinstance(val, dict):
                        if "stringValue" in val:
                            flat_attrs[key] = val["stringValue"]
                        elif "intValue" in val:
                            flat_attrs[key] = int(val["intValue"])
                        elif "doubleValue" in val:
                            flat_attrs[key] = float(val["doubleValue"])
                        elif "boolValue" in val:
                            flat_attrs[key] = bool(val["boolValue"])
                    # Handle RAW protobuf Value object
                    elif hasattr(val, "string_value"):
                        flat_attrs[key] = val.string_value
                    elif hasattr(val, "int_value"):
                        flat_attrs[key] = int(val.int_value)
                    elif hasattr(val, "double_value"):
                        flat_attrs[key] = float(val.double_value)
                    elif hasattr(val, "bool_value"):
                        flat_attrs[key] = bool(val.bool_value)
                    else:
                        flat_attrs[key] = str(val)

        return flat_attrs

    def _metric_to_dict(self, metric, resource, scope):
        dp_values = []
        for dp in getattr(metric, "data_points", []):
            dp_values.append(
                {
                    "value": dp.value if hasattr(dp, "value") else None,
                    "attributes": dict(dp.attributes) if hasattr(dp, "attributes") else {},
                    "start_time": dp.start_time_unix_nano,
                    "time": dp.time_unix_nano,
                }
            )
        return {
            "name": metric.name,
            "description": metric.description,
            "unit": metric.unit,
            "scope": scope.name,
            "resource": dict(resource.attributes),
            "data_points": dp_values,
            "type": str(type(metric).__name__),
        }


# ============================================================================
# OTEL Setup (with genai_otel integration)
# ============================================================================

logging.getLogger("opentelemetry.trace").setLevel(logging.ERROR)
logging.getLogger("opentelemetry.metrics").setLevel(logging.ERROR)


def setup_inmemory_otel(
    enable_otel: bool = False,
    service_name: str = "agent-eval",
    run_id: str = None,
    enable_gpu_metrics: bool = False,
):
    """
    Set up in-memory OpenTelemetry instrumentation.

    Args:
        enable_otel: Whether to enable OTEL instrumentation
        service_name: Service name for traces and metrics
        run_id: Unique run identifier to attach to all telemetry. If None, generates UUID.
        enable_gpu_metrics: Whether to enable GPU metrics collection (for GPU jobs)

    Returns:
        tuple: (tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id)
    """
    if not enable_otel:
        return None, None, None, None, None, None

    # Generate run_id if not provided
    if run_id is None:
        run_id = str(uuid.uuid4())
        print(f"[OTEL Setup] Generated run_id: {run_id}")
    else:
        print(f"[OTEL Setup] Using provided run_id: {run_id}")

    # Create resource with run_id
    resource_attributes = {
        "service.name": service_name,
        "run.id": run_id,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
    }
    resource = Resource.create(resource_attributes)

    # Set up TracerProvider with resource
    trace_provider = TracerProvider(resource=resource)

    # Add CostEnrichmentSpanProcessor FIRST (if available)
    # This ensures cost is calculated and added to spans BEFORE they're exported
    if GENAI_OTEL_AVAILABLE:
        try:
            from genai_otel.cost_enrichment_processor import CostEnrichmentSpanProcessor

            cost_processor = CostEnrichmentSpanProcessor()
            trace_provider.add_span_processor(cost_processor)
            print("[OK] CostEnrichmentSpanProcessor added")
        except Exception as e:
            print(f"[WARNING] Could not add CostEnrichmentSpanProcessor: {e}")

    # Then add our InMemorySpanExporter with SimpleSpanProcessor
    # This exports spans AFTER cost has been added
    span_exporter = InMemorySpanExporter()
    trace_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(service_name)

    # Set up MetricProvider with InMemoryMetricExporter
    metric_exporter = InMemoryMetricExporter()

    # Use PeriodicExportingMetricReader to collect metrics every 10 seconds
    metric_reader = PeriodicExportingMetricReader(
        exporter=metric_exporter,
        export_interval_millis=10000,  # 10 seconds
    )

    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(service_name)

    # Create trace metrics aggregator (for span-based aggregates)
    trace_aggregator = TraceMetricsAggregator()

    # Instrument genai_otel AFTER setting up providers
    # It will use our existing providers and create GPU metrics
    if GENAI_OTEL_AVAILABLE:
        genai_otel.instrument(
            service_name=service_name,
            enable_gpu_metrics=enable_gpu_metrics,
            enable_cost_tracking=True,
            enable_co2_tracking=True,
        )
        print(f"[OK] genai_otel_instrument enabled (GPU metrics: {enable_gpu_metrics})")
    else:
        print("[WARNING] genai_otel_instrument not available")

    print("[OK] In-memory OTEL setup complete")
    return tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id
