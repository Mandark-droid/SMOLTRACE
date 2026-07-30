"""Tests for the test-case <-> trace join.

Every per-test-case result must carry the trace_id (and span_id) of the trace
that test case produced, and the trace document must carry the test-case
identifier so the join works in both directions.

Regression guard: a test case declared with ``agent_type: "both"`` runs once per
agent type and emits two distinct traces. The link used to be reconstructed from
span attributes keyed on ``test.id`` alone (first-wins), so both result rows
inherited the FIRST trace's id and half the deep links pointed at the wrong
trace.
"""

from unittest.mock import Mock

from smoltrace.core import (
    _build_trace_summary_index,
    build_test_case_uid,
    create_enhanced_trace_info,
    evaluate_single_test,
    extract_traces,
    span_identifiers,
)
from smoltrace.utils import flatten_results_for_hf

SHARED_TEST_CASE = {
    "id": "shared_basic_weather",
    "prompt": "What's the weather in Paris?",
    "difficulty": "easy",
    "expected_tool": "get_weather",
    "expected_tool_calls": 1,
    "agent_type": "both",
}


def _make_tracer(spans):
    """Tracer double that records span context and attributes like the SDK."""

    def start_as_current_span(name, attributes=None):
        span = Mock()
        index = len(spans)
        context = Mock()
        context.trace_id = 0x1000 + index
        context.span_id = 0x2000 + index
        span.get_span_context.return_value = context
        record = {
            "name": name,
            "trace_id": hex(context.trace_id),
            "span_id": hex(context.span_id),
            "parent_span_id": None,
            "attributes": dict(attributes or {}),
            "duration_ms": 1.0,
        }
        spans.append(record)
        span.set_attribute.side_effect = lambda k, v: record["attributes"].__setitem__(k, v)
        span.__enter__ = Mock(return_value=span)
        span.__exit__ = Mock(return_value=False)
        return span

    tracer = Mock()
    tracer.start_as_current_span.side_effect = start_as_current_span
    return tracer


class _StubTool:
    name = "get_weather"


class _StubAgent:
    """Agent double: no model calls, no smolagents step machinery."""

    tools = [_StubTool()]

    def run(self, task, stream=True, reset=True, additional_args=None):
        return iter(())


class _ExplodingAgent(_StubAgent):
    def run(self, task, stream=True, reset=True, additional_args=None):
        raise RuntimeError("agent blew up")


def test_build_test_case_uid_is_deterministic_and_agent_scoped():
    assert build_test_case_uid("tool", "t1") == "tool:t1"
    assert build_test_case_uid("code", "t1") == "code:t1"
    assert build_test_case_uid("tool", "t1") != build_test_case_uid("code", "t1")


def test_span_identifiers_matches_exporter_hex_format():
    """Must be byte-identical to InMemorySpanExporter._to_dict, or joins break."""
    span = Mock()
    context = Mock()
    context.trace_id = 12345
    context.span_id = 678
    span.get_span_context.return_value = context

    assert span_identifiers(span) == {"trace_id": hex(12345), "span_id": hex(678)}


def test_span_identifiers_never_raises():
    span = Mock()
    span.get_span_context.side_effect = RuntimeError("no context")

    assert span_identifiers(span) == {"trace_id": None, "span_id": None}


def test_result_carries_non_empty_trace_id():
    spans = []
    result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "tool", tracer=_make_tracer(spans), verbose=False
    )

    assert result["trace_id"], "result must carry a non-empty trace_id"
    assert result["span_id"], "result must carry a non-empty span_id"
    assert result["test_case_uid"] == "tool:shared_basic_weather"


def test_result_trace_id_matches_a_trace_document():
    spans = []
    result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "tool", tracer=_make_tracer(spans), verbose=False
    )

    exporter = Mock()
    exporter.get_finished_spans.return_value = spans
    traces = extract_traces(exporter, "run_1")

    assert [t["trace_id"] for t in traces] == [result["trace_id"]]
    assert traces[0]["root_span_id"] == result["span_id"]


def test_trace_document_carries_test_case_identifiers():
    """Reverse join: trace document -> test case, without walking nested spans."""
    spans = []
    result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "code", tracer=_make_tracer(spans), verbose=False
    )

    exporter = Mock()
    exporter.get_finished_spans.return_value = spans
    trace = extract_traces(exporter, "run_1")[0]

    assert trace["test_ids"] == [result["test_id"]]
    assert trace["test_case_uids"] == [result["test_case_uid"]]
    assert trace["agent_type"] == "code"


def test_both_agent_types_get_distinct_traces():
    """The regression: two executions of one test case must not share a trace."""
    spans = []
    tracer = _make_tracer(spans)
    tool_result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "tool", tracer=tracer, verbose=False
    )
    code_result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "code", tracer=tracer, verbose=False
    )

    assert tool_result["trace_id"] != code_result["trace_id"]

    exporter = Mock()
    exporter.get_finished_spans.return_value = spans
    by_uid = {t["test_case_uids"][0]: t["trace_id"] for t in extract_traces(exporter, "run_1")}

    assert by_uid["tool:shared_basic_weather"] == tool_result["trace_id"]
    assert by_uid["code:shared_basic_weather"] == code_result["trace_id"]


def test_flattened_rows_keep_distinct_trace_ids():
    spans = []
    tracer = _make_tracer(spans)
    tool_result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "tool", tracer=tracer, verbose=False
    )
    code_result = evaluate_single_test(
        _StubAgent(), dict(SHARED_TEST_CASE), "code", tracer=tracer, verbose=False
    )

    flat = flatten_results_for_hf({"tool": [tool_result], "code": [code_result]}, "stub/model")

    assert len(flat) == 2
    assert all(row["trace_id"] for row in flat)
    assert all(row["span_id"] for row in flat)
    assert flat[0]["trace_id"] != flat[1]["trace_id"]
    assert {row["test_case_uid"] for row in flat} == {
        "tool:shared_basic_weather",
        "code:shared_basic_weather",
    }
    # task_id stays as-is for existing consumers.
    assert {row["task_id"] for row in flat} == {"shared_basic_weather"}


def test_trace_link_survives_an_agent_failure():
    spans = []
    result = evaluate_single_test(
        _ExplodingAgent(),
        dict(SHARED_TEST_CASE),
        "tool",
        tracer=_make_tracer(spans),
        verbose=False,
    )

    assert result["error"] == "agent blew up"
    assert result["trace_id"], "a failed test case must still link to its trace"


def test_summary_index_prefers_uid_over_ambiguous_test_id():
    trace_data = [
        {
            "trace_id": "trace_tool",
            "root_span_id": "span_tool",
            "spans": [
                {
                    "span_id": "span_tool",
                    "attributes": {"test.id": "t1", "test.case_uid": "tool:t1"},
                }
            ],
        },
        {
            "trace_id": "trace_code",
            "root_span_id": "span_code",
            "spans": [
                {
                    "span_id": "span_code",
                    "attributes": {"test.id": "t1", "test.case_uid": "code:t1"},
                }
            ],
        },
    ]
    index = _build_trace_summary_index(trace_data)

    assert index["tool:t1"]["trace_id"] == "trace_tool"
    assert index["code:t1"]["trace_id"] == "trace_code"
    # Bare test_id stays first-wins for backward compatibility.
    assert index["t1"]["trace_id"] == "trace_tool"

    assert (
        create_enhanced_trace_info(trace_data, [], "t1", test_case_uid="code:t1")["trace_id"]
        == "trace_code"
    )


def test_create_enhanced_trace_info_falls_back_to_test_id():
    """Traces recorded before test.case_uid existed must still resolve."""
    trace_data = [
        {
            "trace_id": "trace_legacy",
            "spans": [{"span_id": "s1", "attributes": {"test.id": "t1"}}],
        }
    ]

    assert create_enhanced_trace_info(trace_data, [], "t1")["trace_id"] == "trace_legacy"
    assert (
        create_enhanced_trace_info(trace_data, [], "t1", test_case_uid="tool:t1")["trace_id"]
        == "trace_legacy"
    )


def test_flatten_falls_back_to_enhanced_trace_info():
    """Results produced by an older evaluate_single_test have no trace_id key."""
    legacy_result = {
        "test_id": "t1",
        "agent_type": "tool",
        "difficulty": "easy",
        "prompt": "p",
        "success": True,
        "tool_called": True,
        "correct_tool": True,
        "final_answer_called": True,
        "response_correct": True,
        "tools_used": [],
        "steps": 1,
        "response": "ok",
        "error": None,
        "enhanced_trace_info": {"trace_id": "trace_legacy", "root_span_id": "span_legacy"},
    }

    row = flatten_results_for_hf({"tool": [legacy_result]}, "stub/model")[0]

    assert row["trace_id"] == "trace_legacy"
    assert row["span_id"] == "span_legacy"
    assert row["test_case_uid"] == "tool:t1"
