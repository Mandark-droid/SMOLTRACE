"""Tests for smoltrace.exporters.opensearch module."""

import sys
from argparse import Namespace
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures & sample data
# ---------------------------------------------------------------------------

SAMPLE_FLAT_RESULTS = [
    {
        "model": "openai/gpt-4",
        "evaluation_date": "2025-11-16T14:23:00",
        "task_id": "task_001",
        "agent_type": "tool",
        "difficulty": "easy",
        "prompt": "What is 2+2?",
        "success": True,
        "tool_called": True,
        "correct_tool": True,
        "final_answer_called": True,
        "response_correct": True,
        "tools_used": ["calculator"],
        "steps": 2,
        "response": "4",
        "error": None,
        "trace_id": "trace_001",
        "execution_time_ms": 1200.0,
        "total_tokens": 150,
        "cost_usd": 0.001,
        "enhanced_trace_info": "{}",
    },
    {
        "model": "openai/gpt-4",
        "evaluation_date": "2025-11-16T14:23:05",
        "task_id": "task_002",
        "agent_type": "tool",
        "difficulty": "medium",
        "prompt": "Search for AI news",
        "success": False,
        "tool_called": False,
        "correct_tool": False,
        "final_answer_called": True,
        "response_correct": False,
        "tools_used": [],
        "steps": 1,
        "response": "I don't know",
        "error": "Tool not called",
        "trace_id": "trace_002",
        "execution_time_ms": 800.0,
        "total_tokens": 90,
        "cost_usd": 0.0005,
        "enhanced_trace_info": "{}",
    },
]

SAMPLE_TRACE_DATA = [
    {
        "trace_id": "trace_001",
        "model": "openai/gpt-4",
        "agent_type": "tool",
        "total_tokens": 150,
        "total_duration_ms": 1200.0,
        "total_cost_usd": 0.001,
        "spans": [
            {
                "span_id": "span_001",
                "parent_span_id": None,
                "name": "Agent Execution",
                "start_time": 1760947217774556600,
                "end_time": 1760947218974556600,
                "duration_ms": 1200.0,
                "attributes": {"agent.type": "tool"},
                "events": [],
                "status": {"code": "OK"},
            }
        ],
        "timestamp": "2025-11-16T14:23:00",
    },
]

SAMPLE_FLAT_METRICS = [
    {
        "run_id": "run_123",
        "service_name": "smoltrace-eval",
        "timestamp": "2025-11-16T14:23:01",
        "timestamp_unix_nano": "1760947217774556600",
        "gpu_id": "0",
        "gpu_name": "NVIDIA RTX 3060",
        "co2_emissions_gco2e": 0.036,
        "power_cost_usd": 9.19e-06,
        "gpu_utilization_percent": 67.5,
        "gpu_memory_used_mib": 512.34,
        "gpu_memory_total_mib": 6144.0,
        "gpu_temperature_celsius": 84.0,
        "gpu_power_watts": 18.741,
    },
]

SAMPLE_LEADERBOARD_ROW = {
    "run_id": "run_123",
    "model": "openai/gpt-4",
    "agent_type": "both",
    "provider": "litellm",
    "timestamp": "2025-11-16T14:23:00",
    "submitted_by": "test_user",
    "results_dataset": "test_user/smoltrace-results-20251116_142300",
    "traces_dataset": "test_user/smoltrace-traces-20251116_142300",
    "metrics_dataset": "test_user/smoltrace-metrics-20251116_142300",
    "dataset_used": "test/tasks",
    "total_tests": 2,
    "successful_tests": 1,
    "failed_tests": 1,
    "success_rate": 50.0,
    "avg_steps": 1.5,
    "avg_duration_ms": 1000.0,
    "total_duration_ms": 2000.0,
    "total_tokens": 240,
    "total_cost_usd": 0.0015,
    "gpu_utilization_avg": None,
    "gpu_memory_max_mib": None,
    "co2_emissions_g": None,
    "power_cost_total_usd": None,
    "notes": "Test evaluation",
}


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client with all necessary methods."""
    mock_client = MagicMock()
    mock_client.info.return_value = {"version": {"number": "2.11.0"}}
    mock_client.indices.exists.return_value = False
    mock_client.indices.create.return_value = {"acknowledged": True}
    mock_client.indices.put_index_template.return_value = {"acknowledged": True}
    mock_client.index.return_value = {"result": "created"}
    return mock_client


@pytest.fixture
def mock_opensearch_module(mock_opensearch_client):
    """Mock the opensearchpy module and return client + helpers."""
    mock_helpers = MagicMock()
    mock_helpers.bulk.return_value = (2, [])  # (success_count, errors)

    mock_os_class = MagicMock(return_value=mock_opensearch_client)

    mock_module = MagicMock()
    mock_module.OpenSearch = mock_os_class
    mock_module.helpers = mock_helpers

    return mock_module, mock_os_class, mock_helpers


@pytest.fixture
def exporter(mock_opensearch_module, mock_opensearch_client):
    """Create an OpenSearchExporter with mocked opensearchpy."""
    mock_module, mock_os_class, mock_helpers = mock_opensearch_module

    with patch.dict(sys.modules, {"opensearchpy": mock_module}):
        from smoltrace.exporters.opensearch import OpenSearchExporter

        exporter = OpenSearchExporter.__new__(OpenSearchExporter)
        exporter.client = mock_opensearch_client
        exporter.index_prefix = "smoltrace"

    return exporter


@pytest.fixture
def exporter_with_prefix(mock_opensearch_module, mock_opensearch_client):
    """Create an OpenSearchExporter with custom prefix."""
    mock_module, _, _ = mock_opensearch_module

    with patch.dict(sys.modules, {"opensearchpy": mock_module}):
        from smoltrace.exporters.opensearch import OpenSearchExporter

        exporter = OpenSearchExporter.__new__(OpenSearchExporter)
        exporter.client = mock_opensearch_client
        exporter.index_prefix = "myproject"

    return exporter


# ---------------------------------------------------------------------------
# _serialize_doc tests
# ---------------------------------------------------------------------------


class TestSerializeDoc:
    """Tests for the _serialize_doc helper function."""

    def test_serialize_datetime(self):
        from smoltrace.exporters.opensearch import _serialize_doc

        dt = datetime(2025, 11, 16, 14, 23, 0)
        result = _serialize_doc({"ts": dt})
        assert result["ts"] == "2025-11-16T14:23:00"

    def test_serialize_none(self):
        from smoltrace.exporters.opensearch import _serialize_doc

        result = _serialize_doc({"field": None})
        assert result["field"] is None

    def test_serialize_list(self):
        from smoltrace.exporters.opensearch import _serialize_doc

        result = _serialize_doc({"tools": ["a", "b"]})
        assert result["tools"] == ["a", "b"]

    def test_serialize_dict(self):
        from smoltrace.exporters.opensearch import _serialize_doc

        result = _serialize_doc({"attrs": {"key": "value"}})
        assert result["attrs"] == {"key": "value"}

    def test_serialize_primitives(self):
        from smoltrace.exporters.opensearch import _serialize_doc

        result = _serialize_doc({"name": "test", "count": 42, "rate": 0.5, "ok": True})
        assert result == {"name": "test", "count": 42, "rate": 0.5, "ok": True}

    def test_serialize_mixed(self):
        from smoltrace.exporters.opensearch import _serialize_doc

        dt = datetime(2025, 1, 1)
        doc = {"ts": dt, "name": "x", "tags": ["a"], "meta": {"k": 1}, "empty": None}
        result = _serialize_doc(doc)
        assert result["ts"] == "2025-01-01T00:00:00"
        assert result["name"] == "x"
        assert result["tags"] == ["a"]
        assert result["meta"] == {"k": 1}
        assert result["empty"] is None


# ---------------------------------------------------------------------------
# _get_index_name tests
# ---------------------------------------------------------------------------


class TestGetIndexName:
    """Tests for index name generation."""

    def test_leaderboard_index_ignores_timestamp(self, exporter):
        name = exporter._get_index_name("leaderboard", "20251116_142300")
        assert name == "smoltrace-leaderboard"

    def test_leaderboard_index_no_timestamp(self, exporter):
        name = exporter._get_index_name("leaderboard")
        assert name == "smoltrace-leaderboard"

    def test_results_with_timestamp(self, exporter):
        name = exporter._get_index_name("results", "20251116_142300")
        assert name == "smoltrace-results-20251116-142300"

    def test_traces_with_timestamp(self, exporter):
        name = exporter._get_index_name("traces", "20251116_142300")
        assert name == "smoltrace-traces-20251116-142300"

    def test_metrics_with_timestamp(self, exporter):
        name = exporter._get_index_name("metrics", "20251116_142300")
        assert name == "smoltrace-metrics-20251116-142300"

    def test_auto_timestamp_when_none(self, exporter):
        name = exporter._get_index_name("results")
        assert name.startswith("smoltrace-results-")
        # Should be YYYYMMDD-HHMMSS format
        ts_part = name.replace("smoltrace-results-", "")
        assert len(ts_part) == 15  # YYYYMMDD-HHMMSS

    def test_custom_prefix(self, exporter_with_prefix):
        name = exporter_with_prefix._get_index_name("results", "20251116_142300")
        assert name == "myproject-results-20251116-142300"

    def test_custom_prefix_leaderboard(self, exporter_with_prefix):
        name = exporter_with_prefix._get_index_name("leaderboard")
        assert name == "myproject-leaderboard"


# ---------------------------------------------------------------------------
# _create_index_if_not_exists tests
# ---------------------------------------------------------------------------


class TestCreateIndex:
    """Tests for index creation logic."""

    def test_creates_new_index(self, exporter, mock_opensearch_client):
        from smoltrace.exporters.opensearch import RESULTS_INDEX_MAPPING

        mock_opensearch_client.indices.exists.return_value = False

        exporter._create_index_if_not_exists("smoltrace-results-test", RESULTS_INDEX_MAPPING)

        mock_opensearch_client.indices.create.assert_called_once_with(
            index="smoltrace-results-test", body=RESULTS_INDEX_MAPPING
        )

    def test_skips_existing_index(self, exporter, mock_opensearch_client):
        mock_opensearch_client.indices.exists.return_value = True

        exporter._create_index_if_not_exists("smoltrace-results-test", {})

        mock_opensearch_client.indices.create.assert_not_called()


# ---------------------------------------------------------------------------
# _ensure_index_templates tests
# ---------------------------------------------------------------------------


class TestIndexTemplates:
    """Tests for index template creation."""

    def test_creates_four_templates(self, exporter, mock_opensearch_client, capsys):
        mock_opensearch_client.indices.put_index_template.reset_mock()

        exporter._ensure_index_templates()

        assert mock_opensearch_client.indices.put_index_template.call_count == 4

        template_names = [
            call[1]["name"]
            for call in mock_opensearch_client.indices.put_index_template.call_args_list
        ]
        assert "smoltrace-results-template" in template_names
        assert "smoltrace-traces-template" in template_names
        assert "smoltrace-metrics-template" in template_names
        assert "smoltrace-leaderboard-template" in template_names

        captured = capsys.readouterr()
        assert captured.out.count("[OK] Index template") == 4

    def test_template_uses_custom_prefix(self, exporter_with_prefix, mock_opensearch_client):
        mock_opensearch_client.indices.put_index_template.reset_mock()

        exporter_with_prefix._ensure_index_templates()

        template_names = [
            call[1]["name"]
            for call in mock_opensearch_client.indices.put_index_template.call_args_list
        ]
        assert "myproject-results-template" in template_names

        # Verify index pattern uses custom prefix
        results_call = [
            c
            for c in mock_opensearch_client.indices.put_index_template.call_args_list
            if c[1]["name"] == "myproject-results-template"
        ][0]
        assert results_call[1]["body"]["index_patterns"] == ["myproject-results-*"]

    def test_template_has_zero_replicas(self, exporter, mock_opensearch_client):
        mock_opensearch_client.indices.put_index_template.reset_mock()

        exporter._ensure_index_templates()

        for call in mock_opensearch_client.indices.put_index_template.call_args_list:
            template_body = call[1]["body"]["template"]
            assert template_body["settings"]["number_of_replicas"] == 0

    def test_template_has_priority(self, exporter, mock_opensearch_client):
        mock_opensearch_client.indices.put_index_template.reset_mock()

        exporter._ensure_index_templates()

        for call in mock_opensearch_client.indices.put_index_template.call_args_list:
            assert call[1]["body"]["priority"] == 100

    def test_template_failure_warns_but_continues(self, exporter, mock_opensearch_client, capsys):
        mock_opensearch_client.indices.put_index_template.reset_mock()
        mock_opensearch_client.indices.put_index_template.side_effect = Exception(
            "permission denied"
        )

        exporter._ensure_index_templates()

        captured = capsys.readouterr()
        assert captured.out.count("[WARN] Failed to create index template") == 4
        assert "permission denied" in captured.out

    def test_init_calls_ensure_templates(self, mock_opensearch_module):
        """Verify that __init__ calls _ensure_index_templates."""
        mock_module, mock_os_class, _ = mock_opensearch_module

        with patch.dict(sys.modules, {"opensearchpy": mock_module}):
            from smoltrace.exporters.opensearch import OpenSearchExporter

            OpenSearchExporter(host="localhost", port=9200)

        # Templates should have been created during init
        mock_os_class.return_value.indices.put_index_template.assert_called()


# ---------------------------------------------------------------------------
# _bulk_index tests
# ---------------------------------------------------------------------------


class TestBulkIndex:
    """Tests for bulk indexing."""

    def test_bulk_index_with_id_field(self, exporter, mock_opensearch_module):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (2, [])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            count = exporter._bulk_index(
                "test-index",
                [{"task_id": "t1", "val": 1}, {"task_id": "t2", "val": 2}],
                id_field="task_id",
            )

        assert count == 2
        # Verify bulk was called
        mock_helpers.bulk.assert_called_once()
        actions = mock_helpers.bulk.call_args[0][1]
        assert len(actions) == 2
        assert actions[0]["_id"] == "t1"
        assert actions[1]["_id"] == "t2"

    def test_bulk_index_without_id_field(self, exporter, mock_opensearch_module):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (3, [])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            count = exporter._bulk_index("test-index", [{"val": 1}, {"val": 2}, {"val": 3}])

        assert count == 3
        actions = mock_helpers.bulk.call_args[0][1]
        for action in actions:
            assert "_id" not in action

    def test_bulk_index_with_errors(self, exporter, mock_opensearch_module, capsys):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [{"index": {"error": "mapping error"}}])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            count = exporter._bulk_index("test-index", [{"val": 1}, {"val": 2}])

        assert count == 1
        captured = capsys.readouterr()
        assert "[WARN] 1 documents failed" in captured.out

    def test_bulk_index_id_field_missing_from_doc(self, exporter, mock_opensearch_module):
        """When id_field is specified but doc doesn't have it, no _id is set."""
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            exporter._bulk_index("test-index", [{"val": 1}], id_field="missing_field")

        actions = mock_helpers.bulk.call_args[0][1]
        assert "_id" not in actions[0]


# ---------------------------------------------------------------------------
# export_results tests
# ---------------------------------------------------------------------------


class TestExportResults:
    """Tests for export_results method."""

    def test_export_results_success(
        self, exporter, mock_opensearch_client, mock_opensearch_module, capsys
    ):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (2, [])

        results = [dict(r) for r in SAMPLE_FLAT_RESULTS]  # copy to avoid mutation

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            exporter.export_results(results, "openai/gpt-4", "run_123", "smoltrace-results-test")

        # Verify index was created
        mock_opensearch_client.indices.create.assert_called_once()
        # Verify run_id was added to docs
        assert results[0]["run_id"] == "run_123"
        assert results[1]["run_id"] == "run_123"

        captured = capsys.readouterr()
        assert "[OK] Indexed 2 results" in captured.out

    def test_export_results_empty(self, exporter, mock_opensearch_client, capsys):
        exporter.export_results([], "openai/gpt-4", "run_123", "smoltrace-results-test")

        mock_opensearch_client.indices.create.assert_not_called()
        captured = capsys.readouterr()
        assert "[SKIP] No results" in captured.out


# ---------------------------------------------------------------------------
# export_traces tests
# ---------------------------------------------------------------------------


class TestExportTraces:
    """Tests for export_traces method."""

    def test_export_traces_success(
        self, exporter, mock_opensearch_client, mock_opensearch_module, capsys
    ):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        traces = [dict(t) for t in SAMPLE_TRACE_DATA]

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            exporter.export_traces(traces, "openai/gpt-4", "run_123", "smoltrace-traces-test")

        mock_opensearch_client.indices.create.assert_called_once()
        assert traces[0]["run_id"] == "run_123"

        captured = capsys.readouterr()
        assert "[OK] Indexed 1 traces" in captured.out

    def test_export_traces_empty(self, exporter, mock_opensearch_client, capsys):
        exporter.export_traces([], "openai/gpt-4", "run_123", "smoltrace-traces-test")

        mock_opensearch_client.indices.create.assert_not_called()
        captured = capsys.readouterr()
        assert "[SKIP] No traces" in captured.out


# ---------------------------------------------------------------------------
# export_metrics tests
# ---------------------------------------------------------------------------


class TestExportMetrics:
    """Tests for export_metrics method."""

    def test_export_metrics_with_data(
        self, exporter, mock_opensearch_client, mock_opensearch_module, capsys
    ):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        metrics = [dict(m) for m in SAMPLE_FLAT_METRICS]

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            exporter.export_metrics(metrics, "openai/gpt-4", "run_123", "smoltrace-metrics-test")

        mock_opensearch_client.indices.create.assert_called_once()

        captured = capsys.readouterr()
        assert "[OK] Indexed 1 metric time-series rows" in captured.out

    def test_export_metrics_empty_creates_placeholder(
        self, exporter, mock_opensearch_client, mock_opensearch_module, capsys
    ):
        """For API models with no GPU metrics, an empty placeholder document is created."""
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            exporter.export_metrics([], "openai/gpt-4", "run_123", "smoltrace-metrics-test")

        mock_opensearch_client.indices.create.assert_called_once()

        captured = capsys.readouterr()
        assert "[INFO] Creating empty metrics index for API model" in captured.out
        assert "[OK] Indexed 1 metric time-series rows" in captured.out


# ---------------------------------------------------------------------------
# export_leaderboard tests
# ---------------------------------------------------------------------------


class TestExportLeaderboard:
    """Tests for export_leaderboard method."""

    def test_export_leaderboard(self, exporter, mock_opensearch_client, capsys):
        row = dict(SAMPLE_LEADERBOARD_ROW)

        exporter.export_leaderboard(row, "smoltrace-leaderboard")

        mock_opensearch_client.indices.create.assert_called_once()
        mock_opensearch_client.index.assert_called_once()

        # Verify doc_id is run_id for upsert behavior
        index_call = mock_opensearch_client.index.call_args
        assert index_call[1]["id"] == "run_123"
        assert index_call[1]["refresh"] == "wait_for"

        captured = capsys.readouterr()
        assert "[OK] Indexed leaderboard entry" in captured.out

    def test_export_leaderboard_no_run_id(self, exporter, mock_opensearch_client):
        row = {"model": "test", "success_rate": 50.0}
        exporter.export_leaderboard(row, "smoltrace-leaderboard")

        index_call = mock_opensearch_client.index.call_args
        assert index_call[1]["id"] is None


# ---------------------------------------------------------------------------
# export_all tests
# ---------------------------------------------------------------------------


class TestExportAll:
    """Tests for the export_all orchestration method."""

    def test_export_all_returns_index_names(self, exporter, mock_opensearch_module, capsys):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            indexes = exporter.export_all(
                flat_results=[dict(r) for r in SAMPLE_FLAT_RESULTS],
                trace_data=[dict(t) for t in SAMPLE_TRACE_DATA],
                flat_metrics=[dict(m) for m in SAMPLE_FLAT_METRICS],
                leaderboard_row=dict(SAMPLE_LEADERBOARD_ROW),
                model_name="openai/gpt-4",
                run_id="run_123",
                timestamp="20251116_142300",
            )

        assert indexes["results"] == "smoltrace-results-20251116-142300"
        assert indexes["traces"] == "smoltrace-traces-20251116-142300"
        assert indexes["metrics"] == "smoltrace-metrics-20251116-142300"
        assert indexes["leaderboard"] == "smoltrace-leaderboard"

    def test_export_all_adds_index_refs_to_leaderboard(self, exporter, mock_opensearch_module):
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        leaderboard_row = dict(SAMPLE_LEADERBOARD_ROW)

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            exporter.export_all(
                flat_results=[dict(r) for r in SAMPLE_FLAT_RESULTS],
                trace_data=[dict(t) for t in SAMPLE_TRACE_DATA],
                flat_metrics=[dict(m) for m in SAMPLE_FLAT_METRICS],
                leaderboard_row=leaderboard_row,
                model_name="openai/gpt-4",
                run_id="run_123",
                timestamp="20251116_142300",
            )

        # Leaderboard row should have index references
        assert leaderboard_row["results_index"] == "smoltrace-results-20251116-142300"
        assert leaderboard_row["traces_index"] == "smoltrace-traces-20251116-142300"
        assert leaderboard_row["metrics_index"] == "smoltrace-metrics-20251116-142300"

    def test_export_all_with_empty_data(self, exporter, mock_opensearch_module, capsys):
        """export_all handles empty results/traces gracefully."""
        _, _, mock_helpers = mock_opensearch_module
        mock_helpers.bulk.return_value = (1, [])

        with patch.dict(sys.modules, {"opensearchpy": mock_opensearch_module[0]}):
            indexes = exporter.export_all(
                flat_results=[],
                trace_data=[],
                flat_metrics=[],
                leaderboard_row=dict(SAMPLE_LEADERBOARD_ROW),
                model_name="openai/gpt-4",
                run_id="run_123",
                timestamp="20251116_142300",
            )

        captured = capsys.readouterr()
        assert "[SKIP] No results" in captured.out
        assert "[SKIP] No traces" in captured.out
        # Metrics creates placeholder, leaderboard always created
        assert "smoltrace-leaderboard" in indexes["leaderboard"]


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestOpenSearchExporterInit:
    """Tests for OpenSearchExporter construction."""

    def test_init_with_host_port(self, mock_opensearch_module):
        mock_module, mock_os_class, _ = mock_opensearch_module

        with patch.dict(sys.modules, {"opensearchpy": mock_module}):
            from smoltrace.exporters.opensearch import OpenSearchExporter

            OpenSearchExporter(host="myhost", port=9201)

        mock_os_class.assert_called_once_with(
            hosts=["http://myhost:9201"],
            http_auth=None,
            use_ssl=False,
            verify_certs=True,
            ssl_show_warn=True,
        )

    def test_init_with_url(self, mock_opensearch_module):
        mock_module, mock_os_class, _ = mock_opensearch_module

        with patch.dict(sys.modules, {"opensearchpy": mock_module}):
            from smoltrace.exporters.opensearch import OpenSearchExporter

            OpenSearchExporter(
                opensearch_url="https://search.example.com",
                auth=("admin", "pass"),
                verify_certs=False,
            )

        mock_os_class.assert_called_once_with(
            hosts=["https://search.example.com"],
            http_auth=("admin", "pass"),
            verify_certs=False,
            ssl_show_warn=True,
        )

    def test_init_with_ssl(self, mock_opensearch_module):
        mock_module, mock_os_class, _ = mock_opensearch_module

        with patch.dict(sys.modules, {"opensearchpy": mock_module}):
            from smoltrace.exporters.opensearch import OpenSearchExporter

            OpenSearchExporter(use_ssl=True, verify_certs=False, ssl_show_warn=False)

        call_kwargs = mock_os_class.call_args[1]
        assert call_kwargs["use_ssl"] is True
        assert call_kwargs["verify_certs"] is False
        assert call_kwargs["ssl_show_warn"] is False
        # Should use https scheme when use_ssl=True
        assert call_kwargs["hosts"] == ["https://localhost:9200"]

    def test_init_import_error(self):
        """If opensearch-py is not installed, ImportError is raised with instructions."""
        with patch.dict(sys.modules, {"opensearchpy": None}):
            with pytest.raises(ImportError, match="pip install smoltrace\\[opensearch\\]"):
                from importlib import reload

                import smoltrace.exporters.opensearch as os_mod

                reload(os_mod)
                os_mod.OpenSearchExporter()

    def test_init_custom_prefix(self, mock_opensearch_module):
        mock_module, mock_os_class, _ = mock_opensearch_module

        with patch.dict(sys.modules, {"opensearchpy": mock_module}):
            from smoltrace.exporters.opensearch import OpenSearchExporter

            exporter = OpenSearchExporter(index_prefix="custom")

        assert exporter.index_prefix == "custom"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCLIOpenSearchArgs:
    """Test that CLI correctly parses OpenSearch arguments."""

    def test_cli_opensearch_output_format(self, mocker):
        """Test CLI accepts --output-format=opensearch."""
        mock_flow = mocker.patch("smoltrace.cli.run_evaluation_flow")
        sys.argv = [
            "smoltrace-eval",
            "--model",
            "gpt-4",
            "--output-format",
            "opensearch",
            "--opensearch-host",
            "192.168.1.100",
            "--opensearch-port",
            "9201",
            "--opensearch-user",
            "admin",
            "--opensearch-password",
            "secret",
            "--opensearch-ssl",
            "--opensearch-index-prefix",
            "myprefix",
        ]

        from smoltrace.cli import main

        main()

        mock_flow.assert_called_once()
        args = mock_flow.call_args[0][0]
        assert args.output_format == "opensearch"
        assert args.opensearch_host == "192.168.1.100"
        assert args.opensearch_port == 9201
        assert args.opensearch_user == "admin"
        assert args.opensearch_password == "secret"
        assert args.opensearch_ssl is True
        assert args.opensearch_index_prefix == "myprefix"

    def test_cli_opensearch_url_arg(self, mocker):
        """Test CLI accepts --opensearch-url."""
        mock_flow = mocker.patch("smoltrace.cli.run_evaluation_flow")
        sys.argv = [
            "smoltrace-eval",
            "--model",
            "gpt-4",
            "--output-format",
            "opensearch",
            "--opensearch-url",
            "https://search.example.com",
            "--opensearch-no-verify-certs",
        ]

        from smoltrace.cli import main

        main()

        args = mock_flow.call_args[0][0]
        assert args.opensearch_url == "https://search.example.com"
        assert args.opensearch_no_verify_certs is True

    def test_cli_opensearch_defaults(self, mocker):
        """Test CLI OpenSearch defaults."""
        mock_flow = mocker.patch("smoltrace.cli.run_evaluation_flow")
        sys.argv = [
            "smoltrace-eval",
            "--model",
            "gpt-4",
            "--output-format",
            "opensearch",
        ]

        from smoltrace.cli import main

        main()

        args = mock_flow.call_args[0][0]
        assert args.opensearch_host == "localhost"
        assert args.opensearch_port == 9200
        assert args.opensearch_user is None
        assert args.opensearch_password is None
        assert args.opensearch_ssl is False
        assert args.opensearch_no_verify_certs is False
        assert args.opensearch_index_prefix == "smoltrace"
        assert args.opensearch_url is None


# ---------------------------------------------------------------------------
# main.py opensearch flow integration test
# ---------------------------------------------------------------------------


class TestMainOpenSearchFlow:
    """Test the opensearch path in run_evaluation_flow."""

    def test_run_evaluation_flow_opensearch(self, mocker, capsys):
        """Test run_evaluation_flow with opensearch output format."""
        from smoltrace.main import run_evaluation_flow

        args = Namespace(
            hf_token="test_token",
            model="openai/gpt-4",
            provider="litellm",
            agent_type="both",
            quiet=False,
            debug=False,
            enable_otel=True,
            prompt_yml=None,
            mcp_server_url=None,
            difficulty=None,
            dataset_name="test/dataset",
            split="train",
            private=False,
            output_format="opensearch",
            output_dir="./output",
            run_id=None,
            opensearch_host="localhost",
            opensearch_port=9200,
            opensearch_user=None,
            opensearch_password=None,
            opensearch_ssl=False,
            opensearch_no_verify_certs=False,
            opensearch_index_prefix="smoltrace",
            opensearch_url=None,
        )

        # Mock all external functions
        mocker.patch("smoltrace.main.get_hf_user_info", return_value={"username": "test_user"})
        mocker.patch(
            "smoltrace.main.generate_dataset_names",
            return_value=(
                "test_user/smoltrace-results-20251116_142300",
                "test_user/smoltrace-traces-20251116_142300",
                "test_user/smoltrace-metrics-20251116_142300",
                "test_user/smoltrace-leaderboard",
            ),
        )
        mocker.patch("smoltrace.main.load_prompt_config", return_value=None)
        # Mock run_evaluation with raw result format (pre-flatten, uses test_id not task_id)
        raw_result = {
            "test_id": "task_001",
            "agent_type": "tool",
            "difficulty": "easy",
            "prompt": "What is 2+2?",
            "success": True,
            "tool_called": True,
            "correct_tool": True,
            "final_answer_called": True,
            "response_correct": True,
            "tools_used": ["calculator"],
            "steps": 2,
            "response": "4",
            "error": None,
            "enhanced_trace_info": {},
        }
        mocker.patch(
            "smoltrace.main.run_evaluation",
            return_value=(
                {"tool": [raw_result], "code": []},
                SAMPLE_TRACE_DATA,
                {"resourceMetrics": []},
                "test/dataset",
                "run_123",
            ),
        )
        mocker.patch(
            "smoltrace.main.compute_leaderboard_row", return_value=dict(SAMPLE_LEADERBOARD_ROW)
        )

        # Mock the OpenSearchExporter
        mock_exporter_instance = MagicMock()
        mock_exporter_instance.export_all.return_value = {
            "results": "smoltrace-results-20251116-142300",
            "traces": "smoltrace-traces-20251116-142300",
            "metrics": "smoltrace-metrics-20251116-142300",
            "leaderboard": "smoltrace-leaderboard",
        }
        mock_exporter_class = mocker.patch(
            "smoltrace.exporters.opensearch.OpenSearchExporter",
            return_value=mock_exporter_instance,
        )

        run_evaluation_flow(args)

        # Verify exporter was constructed
        mock_exporter_class.assert_called_once_with(
            host="localhost",
            port=9200,
            auth=None,
            use_ssl=False,
            verify_certs=True,
            index_prefix="smoltrace",
            opensearch_url=None,
        )

        # Verify export_all was called
        mock_exporter_instance.export_all.assert_called_once()

        captured = capsys.readouterr()
        assert "[SUCCESS] Evaluation complete! Results exported to OpenSearch" in captured.out

    def test_run_evaluation_flow_opensearch_with_auth(self, mocker, capsys):
        """Test opensearch flow with user/password auth."""

        from smoltrace.main import run_evaluation_flow

        args = Namespace(
            hf_token="test_token",
            model="openai/gpt-4",
            provider="litellm",
            agent_type="both",
            quiet=False,
            debug=False,
            enable_otel=True,
            prompt_yml=None,
            mcp_server_url=None,
            difficulty=None,
            dataset_name="test/dataset",
            split="train",
            private=False,
            output_format="opensearch",
            output_dir="./output",
            run_id=None,
            opensearch_host="myhost",
            opensearch_port=9201,
            opensearch_user="admin",
            opensearch_password="secret",
            opensearch_ssl=True,
            opensearch_no_verify_certs=True,
            opensearch_index_prefix="prod",
            opensearch_url=None,
        )

        mocker.patch("smoltrace.main.get_hf_user_info", return_value={"username": "test_user"})
        mocker.patch(
            "smoltrace.main.generate_dataset_names",
            return_value=(
                "test_user/smoltrace-results-20251116_142300",
                "test_user/smoltrace-traces-20251116_142300",
                "test_user/smoltrace-metrics-20251116_142300",
                "test_user/smoltrace-leaderboard",
            ),
        )
        mocker.patch("smoltrace.main.load_prompt_config", return_value=None)
        mocker.patch(
            "smoltrace.main.run_evaluation",
            return_value=({"tool": [], "code": []}, [], {}, "test/dataset", "run_123"),
        )
        mocker.patch(
            "smoltrace.main.compute_leaderboard_row", return_value=dict(SAMPLE_LEADERBOARD_ROW)
        )

        mock_exporter_instance = MagicMock()
        mock_exporter_instance.export_all.return_value = {
            "results": "idx1",
            "traces": "idx2",
            "metrics": "idx3",
            "leaderboard": "idx4",
        }
        mock_exporter_class = mocker.patch(
            "smoltrace.exporters.opensearch.OpenSearchExporter",
            return_value=mock_exporter_instance,
        )

        run_evaluation_flow(args)

        mock_exporter_class.assert_called_once_with(
            host="myhost",
            port=9201,
            auth=("admin", "secret"),
            use_ssl=True,
            verify_certs=False,
            index_prefix="prod",
            opensearch_url=None,
        )

    def test_run_evaluation_flow_opensearch_password_from_env(self, mocker):
        """Test that OPENSEARCH_PASSWORD env var is picked up."""
        import os as os_mod

        from smoltrace.main import run_evaluation_flow

        args = Namespace(
            hf_token="test_token",
            model="openai/gpt-4",
            provider="litellm",
            agent_type="both",
            quiet=False,
            debug=False,
            enable_otel=True,
            prompt_yml=None,
            mcp_server_url=None,
            difficulty=None,
            dataset_name="test/dataset",
            split="train",
            private=False,
            output_format="opensearch",
            output_dir="./output",
            run_id=None,
            opensearch_host="localhost",
            opensearch_port=9200,
            opensearch_user="admin",
            opensearch_password=None,  # Not in args
            opensearch_ssl=False,
            opensearch_no_verify_certs=False,
            opensearch_index_prefix="smoltrace",
            opensearch_url=None,
        )

        mocker.patch("smoltrace.main.get_hf_user_info", return_value={"username": "test_user"})
        mocker.patch(
            "smoltrace.main.generate_dataset_names",
            return_value=("r", "t", "m", "l"),
        )
        mocker.patch("smoltrace.main.load_prompt_config", return_value=None)
        mocker.patch(
            "smoltrace.main.run_evaluation",
            return_value=({"tool": [], "code": []}, [], {}, "test/dataset", "run_123"),
        )
        mocker.patch(
            "smoltrace.main.compute_leaderboard_row", return_value=dict(SAMPLE_LEADERBOARD_ROW)
        )

        mock_exporter_instance = MagicMock()
        mock_exporter_instance.export_all.return_value = {
            "results": "r",
            "traces": "t",
            "metrics": "m",
            "leaderboard": "l",
        }
        mock_exporter_class = mocker.patch(
            "smoltrace.exporters.opensearch.OpenSearchExporter",
            return_value=mock_exporter_instance,
        )

        # Set env var
        mocker.patch.dict(os_mod.environ, {"OPENSEARCH_PASSWORD": "env_secret"})

        run_evaluation_flow(args)

        # Should pick up password from env and pair with user
        call_kwargs = mock_exporter_class.call_args[1]
        assert call_kwargs["auth"] == ("admin", "env_secret")


# ---------------------------------------------------------------------------
# Index mapping tests
# ---------------------------------------------------------------------------


class TestIndexMappings:
    """Verify index mappings have the expected structure."""

    def test_results_mapping_has_required_fields(self):
        from smoltrace.exporters.opensearch import RESULTS_INDEX_MAPPING

        props = RESULTS_INDEX_MAPPING["mappings"]["properties"]
        required = [
            "model",
            "task_id",
            "agent_type",
            "success",
            "trace_id",
            "execution_time_ms",
            "total_tokens",
            "cost_usd",
            "run_id",
        ]
        for field in required:
            assert field in props, f"Missing field: {field}"

    def test_traces_mapping_has_nested_spans(self):
        from smoltrace.exporters.opensearch import TRACES_INDEX_MAPPING

        props = TRACES_INDEX_MAPPING["mappings"]["properties"]
        assert props["spans"]["type"] == "nested"
        assert "span_id" in props["spans"]["properties"]

    def test_metrics_mapping_has_gpu_fields(self):
        from smoltrace.exporters.opensearch import METRICS_INDEX_MAPPING

        props = METRICS_INDEX_MAPPING["mappings"]["properties"]
        gpu_fields = [
            "gpu_utilization_percent",
            "gpu_memory_used_mib",
            "gpu_temperature_celsius",
            "gpu_power_watts",
        ]
        for field in gpu_fields:
            assert field in props

    def test_leaderboard_mapping_has_index_refs(self):
        from smoltrace.exporters.opensearch import LEADERBOARD_INDEX_MAPPING

        props = LEADERBOARD_INDEX_MAPPING["mappings"]["properties"]
        assert "results_index" in props
        assert "traces_index" in props
        assert "metrics_index" in props

    def test_all_mappings_have_settings(self):
        from smoltrace.exporters.opensearch import (
            LEADERBOARD_INDEX_MAPPING,
            METRICS_INDEX_MAPPING,
            RESULTS_INDEX_MAPPING,
            TRACES_INDEX_MAPPING,
        )

        for mapping in [
            RESULTS_INDEX_MAPPING,
            TRACES_INDEX_MAPPING,
            METRICS_INDEX_MAPPING,
            LEADERBOARD_INDEX_MAPPING,
        ]:
            assert "settings" in mapping
            assert mapping["settings"]["number_of_shards"] == 1


# ---------------------------------------------------------------------------
# Base exporter tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Additional coverage: utils flatten functions edge cases
# ---------------------------------------------------------------------------


class TestFlattenEdgeCases:
    """Test edge cases in flatten functions used by the opensearch flow."""

    def test_flatten_results_with_invalid_json_enhanced_trace(self):
        """flatten_results_for_hf handles invalid JSON in enhanced_trace_info."""
        from smoltrace.utils import flatten_results_for_hf

        results = {
            "tool": [
                {
                    "test_id": "t1",
                    "agent_type": "tool",
                    "difficulty": "easy",
                    "prompt": "test",
                    "success": True,
                    "tool_called": True,
                    "correct_tool": True,
                    "final_answer_called": True,
                    "response_correct": True,
                    "tools_used": [],
                    "steps": 1,
                    "response": "ok",
                    "error": None,
                    "enhanced_trace_info": "not-valid-json{{{",
                }
            ]
        }
        flat = flatten_results_for_hf(results, "test-model")
        assert len(flat) == 1
        assert flat[0]["trace_id"] is None  # graceful fallback
        assert flat[0]["execution_time_ms"] == 0

    def test_flatten_metrics_with_sum_metric(self):
        """flatten_metrics_for_hf handles sum-type metrics (CO2, power cost)."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "smoltrace"}}
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "scope": {"name": "genai.gpu"},
                            "metrics": [
                                {
                                    "name": "gen_ai.co2.emissions",
                                    "sum": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": "1760947217774556600",
                                                "asDouble": 0.036,
                                            }
                                        ]
                                    },
                                },
                                {
                                    "name": "gen_ai.gpu.utilization",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": "1760947217774556600",
                                                "asDouble": 67.5,
                                                "attributes": [
                                                    {
                                                        "key": "gpu_id",
                                                        "value": {"stringValue": "0"},
                                                    },
                                                    {
                                                        "key": "gpu_name",
                                                        "value": {"stringValue": "RTX 3060"},
                                                    },
                                                ],
                                            }
                                        ]
                                    },
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert len(flat) == 1
        assert flat[0]["co2_emissions_gco2e"] == 0.036
        assert flat[0]["gpu_utilization_percent"] == 67.5
        assert flat[0]["gpu_id"] == "0"

    def test_flatten_metrics_no_data_points(self):
        """flatten_metrics_for_hf skips metrics with no data points."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [
                {
                    "resource": {"attributes": []},
                    "scopeMetrics": [
                        {
                            "scope": {"name": "genai.gpu"},
                            "metrics": [
                                {
                                    "name": "gen_ai.co2.emissions",
                                    "sum": {"dataPoints": []},
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert flat == []

    def test_flatten_metrics_no_scope_metrics(self):
        """flatten_metrics_for_hf skips resourceMetrics without scopeMetrics."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [{"resource": {"attributes": []}}],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert flat == []

    def test_flatten_metrics_no_metrics_in_scope(self):
        """flatten_metrics_for_hf skips scopeMetrics without metrics key."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [
                {
                    "resource": {"attributes": []},
                    "scopeMetrics": [{"scope": {"name": "test"}}],
                }
            ],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert flat == []

    def test_flatten_metrics_asint_value(self):
        """flatten_metrics_for_hf handles asInt data points."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [
                {
                    "resource": {"attributes": []},
                    "scopeMetrics": [
                        {
                            "scope": {"name": "test"},
                            "metrics": [
                                {
                                    "name": "gen_ai.gpu.utilization",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": "1760947217774556600",
                                                "asInt": 75,
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert len(flat) == 1
        assert flat[0]["gpu_utilization_percent"] == 75.0

    def test_flatten_metrics_no_timestamp(self):
        """flatten_metrics_for_hf skips data points without timeUnixNano."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [
                {
                    "resource": {"attributes": []},
                    "scopeMetrics": [
                        {
                            "scope": {"name": "test"},
                            "metrics": [
                                {
                                    "name": "gen_ai.gpu.utilization",
                                    "gauge": {"dataPoints": [{"asDouble": 50.0}]},
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert flat == []

    def test_flatten_metrics_null_value(self):
        """flatten_metrics_for_hf handles None/missing values gracefully."""
        from smoltrace.utils import flatten_metrics_for_hf

        metric_data = {
            "run_id": "run_1",
            "resourceMetrics": [
                {
                    "resource": {"attributes": []},
                    "scopeMetrics": [
                        {
                            "scope": {"name": "test"},
                            "metrics": [
                                {
                                    "name": "gen_ai.gpu.utilization",
                                    "gauge": {
                                        "dataPoints": [{"timeUnixNano": "1760947217774556600"}]
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        flat = flatten_metrics_for_hf(metric_data)
        assert len(flat) == 1
        assert flat[0]["gpu_utilization_percent"] == 0.0


class TestBaseExporter:
    """Test the BaseExporter ABC."""

    def test_cannot_instantiate_base(self):
        from smoltrace.exporters.base import BaseExporter

        with pytest.raises(TypeError):
            BaseExporter()

    def test_subclass_must_implement_all_methods(self):
        from smoltrace.exporters.base import BaseExporter

        class IncompleteExporter(BaseExporter):
            def export_results(self, *a, **kw):
                pass

        with pytest.raises(TypeError):
            IncompleteExporter()
