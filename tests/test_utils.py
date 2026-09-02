import pytest
from datasets import Dataset

from smoltrace.utils import (
    _build_leaderboard_dataset,
    compute_leaderboard_row,
    compute_pass_at_1,
)


def test_compute_pass_at_1_uses_first_attempt_per_logical_task():
    results = [
        {"agent_type": "tool", "test_id": "task-1", "success": False},
        {"agent_type": "tool", "test_id": "task-1", "success": True},
        {"agent_type": "tool", "test_id": "task-2", "success": True},
        {"agent_type": "code", "test_id": "task-1", "success": True},
    ]

    assert compute_pass_at_1(results) == {
        "pass_at_1": 0.6667,
        "pass_rule": "success_boolean_first_attempt",
        "pass_attempts": 1,
        "evaluated_prompts": 3,
        "passed_prompts": 2,
    }


def test_compute_pass_at_1_empty_run_is_unmeasured():
    assert compute_pass_at_1([]) == {
        "pass_at_1": None,
        "pass_rule": "success_boolean_first_attempt",
        "pass_attempts": 0,
        "evaluated_prompts": 0,
        "passed_prompts": 0,
    }


def test_compute_leaderboard_row_with_data():
    model_name = "test-model"
    all_results = {
        "tool": [
            {"test_id": "t1", "success": True, "steps": 5},
            {"test_id": "t2", "success": False, "steps": 3},
        ],
        "code": [
            {"test_id": "c1", "success": True, "steps": 7},
        ],
    }
    trace_data = [
        {
            "test_id": "t1",
            "total_tokens": 100,
            "total_duration_ms": 500,
            "total_cost_usd": 0.001,
        },
        {
            "test_id": "t2",
            "total_tokens": 50,
            "total_duration_ms": 200,
            "total_cost_usd": 0.0005,
        },
        {
            "test_id": "c1",
            "total_tokens": 200,
            "total_duration_ms": 1000,
            "total_cost_usd": 0.002,
        },
    ]
    metric_data = {
        "aggregates": [
            {"name": "gen_ai.co2.emissions", "data_points": [{"value": {"value": 0.01}}]},
            {"name": "gen_ai.co2.emissions", "data_points": [{"value": {"value": 0.005}}]},
        ]
    }
    dataset_used = "test-dataset"
    results_dataset = "test-results-repo"
    traces_dataset = "test-traces-repo"
    metrics_dataset = "test-metrics-repo"

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        dataset_used,
        results_dataset,
        traces_dataset,
        metrics_dataset,
        agent_type="both",
    )

    assert leaderboard_row["model"] == model_name
    assert leaderboard_row["agent_type"] == "both"
    assert leaderboard_row["total_tests"] == 3
    assert leaderboard_row["success_rate"] == round(2 / 3 * 100, 2)
    assert leaderboard_row["pass_at_1"] == round(2 / 3, 4)
    assert leaderboard_row["pass_rule"] == "success_boolean_first_attempt"
    assert leaderboard_row["pass_attempts"] == 1
    assert leaderboard_row["evaluated_prompts"] == 3
    assert leaderboard_row["passed_prompts"] == 2
    assert leaderboard_row["avg_steps"] == round((5 + 3 + 7) / 3, 2)
    assert leaderboard_row["total_tokens"] == 350
    assert leaderboard_row["co2_emissions_g"] == round(0.01 + 0.005, 4)
    assert leaderboard_row["power_cost_total_usd"] == 0  # No GPU metrics in test data
    assert leaderboard_row["total_duration_ms"] == 1700
    assert leaderboard_row["avg_duration_ms"] == round(1700 / 3, 2)
    assert leaderboard_row["total_cost_usd"] == round(0.001 + 0.0005 + 0.002, 6)
    assert "timestamp" in leaderboard_row
    assert "notes" in leaderboard_row


def test_compute_leaderboard_row_no_data():
    model_name = "test-model-no-data"
    all_results = {"tool": [], "code": []}
    trace_data = []
    metric_data = {}
    dataset_used = "test-dataset"
    results_dataset = "test-results-repo"
    traces_dataset = "test-traces-repo"
    metrics_dataset = "test-metrics-repo"

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        dataset_used,
        results_dataset,
        traces_dataset,
        metrics_dataset,
        agent_type="both",
    )

    assert leaderboard_row["model"] == model_name
    assert leaderboard_row["total_tests"] == 0
    assert leaderboard_row["success_rate"] == 0
    assert leaderboard_row["avg_steps"] == 0
    assert leaderboard_row["total_tokens"] == 0
    assert leaderboard_row["co2_emissions_g"] == 0
    assert leaderboard_row["total_duration_ms"] == 0
    assert leaderboard_row["avg_duration_ms"] == 0
    assert leaderboard_row["total_cost_usd"] == 0.0
    assert leaderboard_row["pass_at_1"] is None
    assert leaderboard_row["pass_attempts"] == 0
    assert leaderboard_row["evaluated_prompts"] == 0
    assert leaderboard_row["passed_prompts"] == 0


def test_compute_leaderboard_row_grouping_metadata():
    row = compute_leaderboard_row(
        "test-model",
        {"tool": [], "code": []},
        [],
        {},
        "org/swiggy-tasks",
        "results",
        "traces",
        "metrics",
        use_case="  Swiggy MCP Ordering ",
        team="Platform Team",
        purpose="selection",
        suite_version=" Release 1.2 ",
    )

    assert row["use_case"] == "swiggy-mcp-ordering"
    assert row["team"] == "platform-team"
    assert row["purpose"] == "selection"
    assert row["suite_version"] == "release-1-2"


def test_compute_leaderboard_row_does_not_infer_grouping_metadata():
    row = compute_leaderboard_row(
        "test-model",
        {"tool": [], "code": []},
        [],
        {},
        "org/swiggy-tasks",
        "results",
        "traces",
        "metrics",
    )

    assert row["use_case"] is None
    assert row["team"] is None
    assert row["purpose"] is None
    assert row["suite_version"] is None


def test_compute_leaderboard_row_rejects_invalid_purpose():
    with pytest.raises(ValueError, match="Invalid purpose"):
        compute_leaderboard_row(
            "test-model",
            {"tool": [], "code": []},
            [],
            {},
            "tasks",
            "results",
            "traces",
            "metrics",
            purpose="ad-hoc",
        )


def test_old_schema_leaderboard_round_trips_with_nullable_metadata():
    old_rows = [{"model": "old-model", "total_tests": 1}]
    new_row = {
        "model": "new-model",
        "total_tests": 2,
        "use_case": "swiggy-mcp-ordering",
        "team": "platform",
        "purpose": "selection",
        "suite_version": "v1",
    }

    dataset = _build_leaderboard_dataset(old_rows, new_row)
    restored = Dataset.from_dict(dataset.to_dict(), features=dataset.features)

    assert restored[0]["use_case"] is None
    assert restored[1]["use_case"] == "swiggy-mcp-ordering"
    for field in ("use_case", "team", "purpose", "suite_version"):
        assert restored.features[field].dtype == "string"
