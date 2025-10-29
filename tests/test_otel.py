"""Tests for smoltrace.otel module."""

import threading
from unittest.mock import Mock


def test_inmemory_span_exporter_initialization():
    """Test InMemorySpanExporter initialization."""
    from smoltrace.otel import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    assert exporter._spans == []


def test_inmemory_span_exporter_export_and_get_spans():
    """Test exporting and retrieving spans."""
    from opentelemetry.sdk.trace.export import SpanExportResult

    from smoltrace.otel import InMemorySpanExporter

    exporter = InMemorySpanExporter()

    # Create mock span
    mock_span = Mock()
    mock_span.get_span_context().trace_id = 12345
    mock_span.get_span_context().span_id = 67890
    mock_span.parent = None
    mock_span.name = "test_span"
    mock_span.start_time = 1000000000
    mock_span.end_time = 2000000000
    mock_span.attributes = {"key": "value"}
    mock_span.events = []
    mock_span.status = Mock(status_code=Mock(value=0), description=None)
    mock_span.kind = "INTERNAL"
    mock_span.resource = Mock(attributes={"service.name": "test"})

    # Export span
    result = exporter.export([mock_span])
    assert result == SpanExportResult.SUCCESS

    # Get spans
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0]["name"] == "test_span"


def test_inmemory_span_exporter_with_parent_span():
    """Test exporting span with parent."""
    from smoltrace.otel import InMemorySpanExporter

    exporter = InMemorySpanExporter()

    # Create mock parent and child spans
    mock_parent = Mock()
    mock_parent.span_id = 11111

    mock_span = Mock()
    mock_span.get_span_context().trace_id = 12345
    mock_span.get_span_context().span_id = 67890
    mock_span.parent = mock_parent
    mock_span.name = "child_span"
    mock_span.start_time = 1000000000
    mock_span.end_time = 2000000000
    mock_span.attributes = {}
    mock_span.events = []
    mock_span.status = Mock(status_code=Mock(value=0), description=None)
    mock_span.kind = "CLIENT"
    mock_span.resource = None

    exporter.export([mock_span])
    spans = exporter.get_finished_spans()
    assert spans[0]["parent_span_id"] == hex(11111)


def test_inmemory_span_exporter_with_token_attributes():
    """Test span with LLM token attributes."""
    from smoltrace.otel import InMemorySpanExporter

    exporter = InMemorySpanExporter()

    mock_span = Mock()
    mock_span.get_span_context().trace_id = 12345
    mock_span.get_span_context().span_id = 67890
    mock_span.parent = None
    mock_span.name = "llm_call"
    mock_span.start_time = 1000000000
    mock_span.end_time = 2000000000
    mock_span.attributes = {"llm.token_count.total": 150}
    mock_span.events = []
    mock_span.status = Mock(status_code=Mock(value=0), description=None)
    mock_span.kind = "CLIENT"
    mock_span.resource = None

    exporter.export([mock_span])
    spans = exporter.get_finished_spans()
    assert spans[0]["total_tokens"] == 150


def test_inmemory_span_exporter_with_tool_output():
    """Test span with tool output attributes."""
    from smoltrace.otel import InMemorySpanExporter

    exporter = InMemorySpanExporter()

    mock_span = Mock()
    mock_span.get_span_context().trace_id = 12345
    mock_span.get_span_context().span_id = 67890
    mock_span.parent = None
    mock_span.name = "tool_call"
    mock_span.start_time = 1000000000
    mock_span.end_time = 2000000000
    mock_span.attributes = {
        "tool.name": "calculator",
        "output.value": "The answer is 42" * 20,  # Long output to test truncation
    }
    mock_span.events = []
    mock_span.status = Mock(status_code=Mock(value=0), description=None)
    mock_span.kind = "CLIENT"
    mock_span.resource = None

    exporter.export([mock_span])
    spans = exporter.get_finished_spans()
    assert "tool_output" in spans[0]
    assert len(spans[0]["tool_output"]) <= 200  # Truncated


def test_inmemory_span_exporter_shutdown():
    """Test shutdown method."""
    from smoltrace.otel import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    exporter.shutdown()  # Should not raise


def test_inmemory_metric_exporter_initialization():
    """Test InMemoryMetricExporter initialization."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()
    assert exporter._metrics_data == []
    assert isinstance(exporter._lock, type(threading.Lock()))


def test_inmemory_metric_exporter_export():
    """Test metric export with real OpenTelemetry objects."""
    from opentelemetry.sdk.metrics._internal.point import Metric, NumberDataPoint
    from opentelemetry.sdk.metrics.export import Gauge, MetricExportResult
    from opentelemetry.sdk.resources import Resource

    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()

    # Create real resource
    resource = Resource.create({"service.name": "test"})

    # Create real data point
    data_point = NumberDataPoint(
        attributes={"gpu_id": "0"},
        start_time_unix_nano=1000000000,
        time_unix_nano=1234567890,
        value=75,
    )

    # Create real gauge data
    gauge_data = Gauge(data_points=[data_point])

    # Create real metric
    metric = Metric(
        name="gen_ai.gpu.utilization",
        description="GPU utilization",
        unit="%",
        data=gauge_data,
    )

    # Mock scope and scope metrics properly
    mock_scope = Mock()
    mock_scope.name = "test_scope"
    mock_scope.version = "1.0"

    mock_scope_metrics = Mock()
    mock_scope_metrics.scope = mock_scope
    mock_scope_metrics.metrics = [metric]

    mock_resource_metrics = Mock()
    mock_resource_metrics.resource = resource
    mock_resource_metrics.scope_metrics = [mock_scope_metrics]

    mock_metrics_data = Mock()
    mock_metrics_data.resource_metrics = [mock_resource_metrics]

    result = exporter.export(mock_metrics_data)

    assert result == MetricExportResult.SUCCESS
    metrics = exporter.get_metrics_data()
    assert len(metrics) > 0


def test_inmemory_metric_exporter_attribute_value_conversions():
    """Test attribute value type conversions."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()

    # Test string
    assert exporter._attribute_value_to_dict("test") == {"stringValue": "test"}

    # Test bool
    assert exporter._attribute_value_to_dict(True) == {"boolValue": True}
    assert exporter._attribute_value_to_dict(False) == {"boolValue": False}

    # Test int
    assert exporter._attribute_value_to_dict(42) == {"intValue": 42}

    # Test float
    assert exporter._attribute_value_to_dict(3.14) == {"doubleValue": 3.14}

    # Test other type (converted to string)
    assert exporter._attribute_value_to_dict([1, 2, 3]) == {"stringValue": "[1, 2, 3]"}


def test_inmemory_metric_exporter_resource_to_dict():
    """Test resource to dict conversion."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()

    # Test with attributes
    mock_resource = Mock()
    mock_resource.attributes = {"service.name": "test", "version": 123}

    result = exporter._resource_to_dict(mock_resource)
    assert "attributes" in result
    assert len(result["attributes"]) == 2

    # Test with no resource
    result = exporter._resource_to_dict(None)
    assert result == {"attributes": []}

    # Test with resource but no attributes
    mock_resource_empty = Mock()
    mock_resource_empty.attributes = None
    result = exporter._resource_to_dict(mock_resource_empty)
    assert result == {"attributes": []}


def test_inmemory_metric_exporter_data_point_to_dict_int():
    """Test data point conversion with integer value."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()

    mock_dp = Mock()
    mock_dp.attributes = {"key": "value"}
    mock_dp.time_unix_nano = 1234567890
    mock_dp.value = 100  # Integer value

    result = exporter._data_point_to_dict(mock_dp)
    assert result["asInt"] == "100"
    assert result["asDouble"] is None


def test_inmemory_metric_exporter_data_point_to_dict_float():
    """Test data point conversion with float value."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()

    mock_dp = Mock()
    mock_dp.attributes = {}
    mock_dp.time_unix_nano = 1234567890
    mock_dp.value = 75.5  # Float value

    result = exporter._data_point_to_dict(mock_dp)
    assert result["asInt"] is None
    assert result["asDouble"] == 75.5


def test_inmemory_metric_exporter_clear():
    """Test clearing metrics."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()
    exporter._metrics_data = [{"test": "data"}]
    exporter.clear()
    assert exporter._metrics_data == []


def test_inmemory_metric_exporter_shutdown():
    """Test shutdown."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()
    exporter._metrics_data = [{"test": "data"}]
    result = exporter.shutdown()
    assert result is True
    assert exporter._metrics_data == []


def test_inmemory_metric_exporter_force_flush():
    """Test force flush."""
    from smoltrace.otel import InMemoryMetricExporter

    exporter = InMemoryMetricExporter()
    result = exporter.force_flush()
    assert result is True


def test_trace_metrics_aggregator_initialization():
    """Test TraceMetricsAggregator initialization."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()
    assert aggregator._metrics == []


def test_trace_metrics_aggregator_collect_all_no_traces():
    """Test collecting metrics with no traces."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()
    result = aggregator.collect_all(trace_data=None, all_results=None)
    assert result == []


def test_trace_metrics_aggregator_collect_all_empty_traces():
    """Test collecting metrics with empty trace list."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()
    result = aggregator.collect_all(trace_data=[], all_results={})
    assert result == []


def test_trace_metrics_aggregator_collect_all_with_data():
    """Test collecting metrics with actual trace data."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()

    trace_data = [
        {
            "trace_id": "trace_1",
            "total_tokens": 150,
            "total_cost_usd": 0.005,
            "spans": [
                {
                    "span_id": "span_1",
                    "attributes": {
                        "test.id": "test_1",
                        "tests.tool_calls": "2",
                        "tests.steps": "3",
                    },
                }
            ],
        }
    ]

    all_results = {
        "tool": [
            {"test_id": "test_1", "success": True},
        ]
    }

    metrics = aggregator.collect_all(trace_data=trace_data, all_results=all_results)

    assert len(metrics) == 6  # 6 metric types
    assert any(m["name"] == "tests.successful" for m in metrics)
    assert any(m["name"] == "llm.token_count.total" for m in metrics)
    assert any(m["name"] == "gen_ai.co2.emissions" for m in metrics)


def test_trace_metrics_aggregator_with_exception():
    """Test aggregator handles exceptions gracefully."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()

    # Invalid trace data that would cause exception
    trace_data = [
        {
            "spans": "invalid",  # Should be list
        }
    ]

    result = aggregator.collect_all(trace_data=trace_data, all_results={})
    assert result == []  # Should return empty on exception


def test_trace_metrics_aggregator_flatten_attributes_dict():
    """Test flattening attributes when already a dict."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()

    attrs = {"key1": "value1", "key2": 123}
    result = aggregator.flatten_attributes(attrs)
    assert result == attrs


def test_trace_metrics_aggregator_flatten_attributes_list():
    """Test flattening attributes from list format."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()

    attrs = [
        {"key": "test.id", "value": {"stringValue": "test_1"}},
        {"key": "count", "value": {"intValue": 42}},
        {"key": "ratio", "value": {"doubleValue": 0.95}},
        {"key": "enabled", "value": {"boolValue": True}},
    ]

    result = aggregator.flatten_attributes(attrs)
    assert result["test.id"] == "test_1"
    assert result["count"] == 42
    assert result["ratio"] == 0.95
    assert result["enabled"] is True


def test_trace_metrics_aggregator_flatten_attributes_protobuf():
    """Test flattening attributes from protobuf format."""
    from smoltrace.otel import TraceMetricsAggregator

    aggregator = TraceMetricsAggregator()

    # Create mock protobuf-like value with string_value
    mock_string_val = type("MockProto", (), {})()
    mock_string_val.string_value = "proto_value"

    # Create mock protobuf-like value with int_value
    mock_int_val = type("MockProto", (), {})()
    mock_int_val.int_value = 999

    # Create mock protobuf-like value with double_value
    mock_double_val = type("MockProto", (), {})()
    mock_double_val.double_value = 3.14

    # Create mock protobuf-like value with bool_value
    mock_bool_val = type("MockProto", (), {})()
    mock_bool_val.bool_value = True

    attrs = [
        {"key": "str_key", "value": mock_string_val},
        {"key": "int_key", "value": mock_int_val},
        {"key": "double_key", "value": mock_double_val},
        {"key": "bool_key", "value": mock_bool_val},
    ]

    result = aggregator.flatten_attributes(attrs)
    assert result["str_key"] == "proto_value"
    assert result["int_key"] == 999
    assert result["double_key"] == 3.14
    assert result["bool_key"] is True


def test_setup_inmemory_otel_disabled():
    """Test OTEL setup when disabled."""
    from smoltrace.otel import setup_inmemory_otel

    result = setup_inmemory_otel(enable_otel=False)
    assert result == (None, None, None, None, None, None)


def test_setup_inmemory_otel_enabled_without_run_id(mocker):
    """Test OTEL setup generates run_id when not provided."""
    from smoltrace.otel import setup_inmemory_otel

    # Mock genai_otel availability
    mocker.patch("smoltrace.otel.GENAI_OTEL_AVAILABLE", False)

    tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
        enable_otel=True,
        service_name="test-service",
        run_id=None,
        enable_gpu_metrics=False,
    )

    # Should generate a UUID
    assert run_id is not None
    assert len(run_id) == 36  # UUID length
    assert tracer is not None
    assert meter is not None
    assert span_exporter is not None
    assert metric_exporter is not None
    assert trace_aggregator is not None


def test_setup_inmemory_otel_enabled_with_run_id(mocker):
    """Test OTEL setup uses provided run_id."""
    from smoltrace.otel import setup_inmemory_otel

    mocker.patch("smoltrace.otel.GENAI_OTEL_AVAILABLE", False)

    custom_run_id = "custom_12345"
    tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
        enable_otel=True,
        service_name="test-service",
        run_id=custom_run_id,
        enable_gpu_metrics=False,
    )

    assert run_id == custom_run_id


def test_setup_inmemory_otel_with_genai_otel(mocker):
    """Test OTEL setup with genai_otel_instrument available."""
    from smoltrace.otel import setup_inmemory_otel

    # Mock genai_otel as available
    mocker.patch("smoltrace.otel.GENAI_OTEL_AVAILABLE", True)
    mock_genai_otel = mocker.patch("smoltrace.otel.genai_otel")

    tracer, meter, span_exporter, metric_exporter, trace_aggregator, run_id = setup_inmemory_otel(
        enable_otel=True,
        service_name="test-service",
        run_id="test_run",
        enable_gpu_metrics=True,
    )

    # Should call genai_otel.instrument
    mock_genai_otel.instrument.assert_called_once_with(
        service_name="test-service",
        enable_gpu_metrics=True,
        enable_cost_tracking=True,
        enable_co2_tracking=True,
    )


# Note: Sum and Histogram metric type tests are complex to mock properly
# and can cause recursion issues. The core export functionality is tested
# with the Gauge metric type test above.
