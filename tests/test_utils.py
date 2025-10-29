from smoltrace.utils import compute_leaderboard_row


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
