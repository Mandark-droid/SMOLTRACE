# smoltrace/otel.py

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import requests
import yaml
from datasets import Dataset, load_dataset
from huggingface_hub import HfApi, login

# OTEL Imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SimpleSpanProcessor, SpanExportResult
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics import MeterProvider
#from opentelemetry.sdk.metrics.aggregation import AggregationTemporality

# Smolagents (assume installed)
from smolagents import CodeAgent, ToolCallingAgent, Tool, DuckDuckGoSearchTool, LiteLLMModel
from smolagents.memory import ActionStep, PlanningStep, FinalAnswerStep
from smolagents.models import ChatMessageStreamDelta

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
            self._spans.append(self._to_dict(span))
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

    def get_finished_spans(self):
        return self._spans

    def _to_dict(self, span):
        d = {
            "trace_id": hex(span.get_span_context().trace_id),
            "span_id": hex(span.get_span_context().span_id),
            "parent_span_id": hex(span.parent.span_id) if span.parent else None,
            "name": span.name,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": (span.end_time - span.start_time) / 1e6 if span.end_time and span.start_time else 0,
            "attributes": dict(span.attributes),
            "events": [
                {"name": e.name, "attributes": dict(e.attributes), "timestamp": e.timestamp}
                for e in span.events
            ],
            "status": {
                "code": span.status.status_code.value if hasattr(span.status, 'status_code') else None,
                "description": span.status.description if hasattr(span.status, 'description') else None
            },
            "kind": str(span.kind),
            "resource": dict(span.resource.attributes) if span.resource else {}
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
            elif hasattr(attrs, 'items'):  # Mapping
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
                elif hasattr(attrs, 'items'):
                    return {str(k): str(v) for k, v in attrs.items()}
                else:  # Seq of KeyValue (e.g., protobuf from genai_otel)
                    return {str(kv.key): self._value_to_str(getattr(kv.value, 'stringValue', kv.value)) for kv in attrs}
            except Exception as e:
                print(f"Warning: Attrs conversion failed: {e}; using empty")
                return {}
              
        def _value_to_str(val):
          if hasattr(val, 'stringValue'):
              return val.stringValue
          elif hasattr(val, 'intValue'):
              return str(val.intValue)
          elif hasattr(val, 'doubleValue'):
              return str(val.doubleValue)
          elif hasattr(val, 'boolValue'):
              return str(val.boolValue)
          else:
              return str(val)
        d["attributes"] = safe_attrs_to_dict(span.attributes)
        if span.resource and span.resource.attributes:
            d["resource"] = {"attributes": safe_attrs_to_dict(span.resource.attributes)}
        else:
            d["resource"] = {}       
            
        return d

class InMemoryMetricReaderCollector:
    def __init__(self):
        self._metrics = []

    def collect_all(self, trace_data: List[Dict] = None, all_results: List[Dict] = None):
        try:
            if not trace_data:
                print("No traces; returning empty")
                return []

            print(f"Aggregating metrics from {len(trace_data)} traces + {len(all_results or [])} results")
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
        success_map = {r["test_id"]: r["success"] for results_list in all_results.values() for r in results_list}

        # Aggregate from spans within traces
        total_success = 0
        total_tool_calls = 0
        total_steps = 0
        test_count = 0
        total_tokens = 0
        total_cost = 0.0

        for trace in trace_data:
            # Use the aggregated trace-level metrics
            if trace.get("total_tokens"):
                total_tokens += int(trace["total_tokens"])
            if trace.get("total_cost_usd"):
                total_cost += float(trace["total_cost_usd"])

            # Find test evaluation spans
            for span in trace.get("spans", []):
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

        print(f"  Aggregated: {test_count} tests, {total_success} success, {total_tokens} tokens, ${total_cost:.6f}, {co2_total:.4f}g CO2")

        # Build metrics with actual data
        metrics = [
            {
                "name": "tests.successful",
                "type": "counter",
                "data_points": [{"value": {"value": total_success}, "attributes": {
                    "total_tests": test_count,
                    "success_rate": round(total_success / test_count * 100, 2) if test_count else 0
                }}]
            },
            {
                "name": "tests.tool_calls",
                "type": "histogram",
                "data_points": [{"value": {
                    "sum": total_tool_calls,
                    "count": test_count,
                    "avg": round(total_tool_calls / test_count, 2) if test_count else 0
                }, "attributes": {}}]
            },
            {
                "name": "tests.steps",
                "type": "histogram",
                "data_points": [{"value": {
                    "sum": total_steps,
                    "count": test_count,
                    "avg": round(total_steps / test_count, 2) if test_count else 0
                }, "attributes": {}}]
            },
            {
                "name": "llm.token_count.total",
                "type": "sum",
                "unit": "tokens",
                "data_points": [{"value": {"value": total_tokens}, "attributes": {}}]
            },
            {
                "name": "gen_ai.usage.cost.total",
                "type": "sum",
                "unit": "USD",
                "data_points": [{"value": {"value": round(total_cost, 6)}, "attributes": {}}]
            },
            {
                "name": "gen_ai.co2.emissions",
                "type": "sum",
                "unit": "gCO2e",
                "data_points": [{"value": {"value": round(co2_total, 4)}, "attributes": {}}]
            }
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
                        if "stringValue" in val: flat_attrs[key] = val["stringValue"]
                        elif "intValue" in val: flat_attrs[key] = int(val["intValue"])
                        elif "doubleValue" in val: flat_attrs[key] = float(val["doubleValue"])
                        elif "boolValue" in val: flat_attrs[key] = bool(val["boolValue"])
                    # Handle RAW protobuf Value object
                    elif hasattr(val, 'string_value'): flat_attrs[key] = val.string_value
                    elif hasattr(val, 'int_value'): flat_attrs[key] = int(val.int_value)
                    elif hasattr(val, 'double_value'): flat_attrs[key] = float(val.double_value)
                    elif hasattr(val, 'bool_value'): flat_attrs[key] = bool(val.bool_value)
                    else: flat_attrs[key] = str(val)
        
        return flat_attrs
      
    def _metric_to_dict(self, metric, resource, scope):
        dp_values = []
        for dp in getattr(metric, 'data_points', []):
            dp_values.append({
                "value": dp.value if hasattr(dp, 'value') else None,
                "attributes": dict(dp.attributes) if hasattr(dp, 'attributes') else {},
                "start_time": dp.start_time_unix_nano,
                "time": dp.time_unix_nano
            })
        return {
            "name": metric.name,
            "description": metric.description,
            "unit": metric.unit,
            "scope": scope.name,
            "resource": dict(resource.attributes),
            "data_points": dp_values,
            "type": str(type(metric).__name__)
        }

# ============================================================================
# OTEL Setup (with genai_otel integration)
# ============================================================================

import logging
logging.getLogger('opentelemetry.trace').setLevel(logging.ERROR)
logging.getLogger('opentelemetry.metrics').setLevel(logging.ERROR)

def setup_inmemory_otel(enable_otel: bool = False, service_name: str = "agent-eval"):
    if not enable_otel:
        return None, None, None, None

    # Always set in-memory providers FIRST (avoids override if genai_otel called later)
    trace_provider = TracerProvider()
    span_exporter = InMemorySpanExporter()
    trace_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(service_name)

    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter(service_name)

    # Custom collector with force_flush support
    #metric_collector = InMemoryMetricReaderCollector(metric_reader, meter_provider)
# Simplified: No reader/meter_provider needed
    metric_collector = InMemoryMetricReaderCollector()  # Empty args
    

    # Instrument genai_otel AFTER (it uses existing providers; no override)
    if GENAI_OTEL_AVAILABLE:
        genai_otel.instrument(service_name=service_name,enable_gpu_metrics=True,
enable_cost_tracking=True,enable_co2_tracking=True)
        print("[OK] genai_otel_instrument enabled (using in-memory providers)")

    print("[OK] In-memory OTEL setup complete")
    return tracer, meter, span_exporter, metric_collector
