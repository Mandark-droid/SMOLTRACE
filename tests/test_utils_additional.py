"""Additional tests for smoltrace.utils module."""

import os
import tempfile
from unittest.mock import Mock

from smoltrace.utils import (
    aggregate_gpu_metrics,
    compute_leaderboard_row,
    flatten_results_for_hf,
    generate_dataset_names,
    get_hf_user_info,
    load_prompt_config,
    push_results_to_hf,
    save_results_locally,
    update_leaderboard,
)


# Tests for get_hf_user_info
def test_get_hf_user_info_success(mocker):
    """Test successful HF user info fetch."""
    mock_api = mocker.patch("smoltrace.utils.HfApi")
    mock_instance = mock_api.return_value
    mock_instance.whoami.return_value = {
        "name": "test_user",
        "type": "user",
        "fullname": "Test User",
        "email": "test@example.com",
        "avatarUrl": "https://example.com/avatar.png",
        "isPro": True,
        "canPay": False,
    }

    result = get_hf_user_info("test_token")

    assert result is not None
    assert result["username"] == "test_user"
    assert result["type"] == "user"
    assert result["fullname"] == "Test User"
    assert result["email"] == "test@example.com"
    assert result["avatar_url"] == "https://example.com/avatar.png"
    assert result["isPro"] is True
    assert result["canPay"] is False


def test_get_hf_user_info_error(mocker):
    """Test HF user info fetch with error."""
    mock_api = mocker.patch("smoltrace.utils.HfApi")
    mock_instance = mock_api.return_value
    mock_instance.whoami.side_effect = ValueError("Invalid token")

    result = get_hf_user_info("invalid_token")

    assert result is None


def test_get_hf_user_info_request_error(mocker):
    """Test HF user info fetch with request error."""
    import requests

    mock_api = mocker.patch("smoltrace.utils.HfApi")
    mock_instance = mock_api.return_value
    mock_instance.whoami.side_effect = requests.exceptions.RequestException("Network error")

    result = get_hf_user_info("test_token")

    assert result is None


# Tests for generate_dataset_names
def test_generate_dataset_names():
    """Test dataset name generation."""
    username = "test_user"

    results, traces, metrics, leaderboard = generate_dataset_names(username)

    assert results.startswith(f"{username}/smoltrace-results-")
    assert traces.startswith(f"{username}/smoltrace-traces-")
    assert metrics.startswith(f"{username}/smoltrace-metrics-")
    assert leaderboard == f"{username}/smoltrace-leaderboard"

    # Check timestamp format: YYYYMMDD_HHMMSS
    timestamp = results.split("-")[-1]
    assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
    assert "_" in timestamp


# Tests for load_prompt_config
def test_load_prompt_config_success():
    """Test loading prompt config from file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("system_prompt: Test prompt\nuser_template: Hello {name}")
        temp_path = f.name

    try:
        config = load_prompt_config(temp_path)
        assert config is not None
        assert config["system_prompt"] == "Test prompt"
        assert config["user_template"] == "Hello {name}"
    finally:
        os.unlink(temp_path)


def test_load_prompt_config_nonexistent():
    """Test loading prompt config from nonexistent file."""
    config = load_prompt_config("nonexistent_file.yml")
    assert config is None


def test_load_prompt_config_none():
    """Test loading prompt config with None."""
    config = load_prompt_config(None)
    assert config is None


def test_load_prompt_config_io_error(mocker):
    """Test loading prompt config with IO error."""
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", side_effect=IOError("Cannot read file"))

    config = load_prompt_config("test.yml")
    assert config is None


# Tests for aggregate_gpu_metrics
def test_aggregate_gpu_metrics_with_data():
    """Test GPU metrics aggregation with data."""
    resource_metrics = [
        {
            "scopeMetrics": [
                {
                    "metrics": [
                        {
                            "name": "gen_ai.gpu.utilization",
                            "gauge": {
                                "dataPoints": [
                                    {"asInt": "80"},
                                    {"asInt": "90"},
                                ]
                            },
                        },
                        {
                            "name": "gen_ai.gpu.memory.used",
                            "gauge": {
                                "dataPoints": [
                                    {"asDouble": 1024.5},
                                    {"asDouble": 2048.0},
                                ]
                            },
                        },
                        {
                            "name": "gen_ai.gpu.temperature",
                            "gauge": {
                                "dataPoints": [
                                    {"asInt": "70"},
                                    {"asInt": "75"},
                                ]
                            },
                        },
                        {
                            "name": "gen_ai.gpu.power",
                            "gauge": {
                                "dataPoints": [
                                    {"asDouble": 250.0},
                                    {"asDouble": 300.0},
                                ]
                            },
                        },
                    ]
                }
            ]
        }
    ]

    result = aggregate_gpu_metrics(resource_metrics)

    assert "utilization_avg" in result
    assert "utilization_max" in result
    assert "memory_avg" in result
    assert "memory_max" in result
    assert "temperature_avg" in result
    assert "temperature_max" in result
    assert "power_avg" in result


def test_aggregate_gpu_metrics_empty():
    """Test GPU metrics aggregation with empty data."""
    result = aggregate_gpu_metrics([])

    assert result["utilization_avg"] is None
    assert result["memory_avg"] is None
    assert result["utilization_max"] is None
    assert result["memory_max"] is None
    assert result["temperature_avg"] is None
    assert result["temperature_max"] is None
    assert result["power_avg"] is None


# Tests for flatten_results_for_hf
def test_flatten_results_for_hf():
    """Test flattening results for HF dataset."""
    all_results = {
        "tool": [
            {
                "test_id": "t1",
                "success": True,
                "agent_type": "tool",
                "difficulty": "easy",
                "prompt": "test prompt 1",
                "tool_called": True,
                "correct_tool": True,
                "final_answer_called": True,
                "tools_used": ["tool1"],
                "steps": 3,
                "response": "response 1",
            },
            {
                "test_id": "t2",
                "success": False,
                "agent_type": "tool",
                "difficulty": "medium",
                "prompt": "test prompt 2",
                "tool_called": False,
                "correct_tool": False,
                "final_answer_called": False,
                "tools_used": [],
                "steps": 1,
                "response": "response 2",
            },
        ],
        "code": [
            {
                "test_id": "c1",
                "success": True,
                "agent_type": "code",
                "difficulty": "hard",
                "prompt": "test prompt 3",
                "tool_called": True,
                "correct_tool": True,
                "final_answer_called": True,
                "tools_used": ["tool2"],
                "steps": 5,
                "response": "response 3",
            },
        ],
    }

    flattened = flatten_results_for_hf(all_results, "test-model")

    assert len(flattened) == 3
    assert all("model" in r for r in flattened)
    assert all(r["model"] == "test-model" for r in flattened)
    assert flattened[0]["task_id"] == "t1"
    assert flattened[1]["task_id"] == "t2"
    assert flattened[2]["task_id"] == "c1"


def test_flatten_results_for_hf_empty():
    """Test flattening empty results."""
    flattened = flatten_results_for_hf({}, "test-model")
    assert len(flattened) == 0


# Tests for update_leaderboard
def test_update_leaderboard_new(mocker):
    """Test updating leaderboard with new dataset."""
    mock_login = mocker.patch("smoltrace.utils.login")
    mock_load = mocker.patch("smoltrace.utils.load_dataset")
    mock_load.side_effect = FileNotFoundError()
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance

    new_row = {"model": "test-model", "agent_type": "tool", "success_rate": 95.0}

    update_leaderboard("test/leaderboard", new_row, "test_token")

    mock_login.assert_called_once()
    mock_dataset.from_list.assert_called_once()
    mock_ds_instance.push_to_hub.assert_called_once()


def test_update_leaderboard_append(mocker):
    """Test updating existing leaderboard."""
    mocker.patch("smoltrace.utils.login")
    mock_load = mocker.patch("smoltrace.utils.load_dataset")
    mock_ds = Mock()
    mock_ds.__iter__ = Mock(return_value=iter([{"model": "old-model", "agent_type": "code"}]))
    mock_load.return_value = mock_ds

    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance

    new_row = {"model": "new-model", "agent_type": "tool", "success_rate": 96.0}

    update_leaderboard("test/leaderboard", new_row, "test_token")

    # Should append to existing data
    call_args = mock_dataset.from_list.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0]["model"] == "old-model"
    assert call_args[1]["model"] == "new-model"


def test_update_leaderboard_no_repo():
    """Test update_leaderboard with no repo specified."""
    # Should return early without error
    update_leaderboard("", {"model": "test"}, "token")
    update_leaderboard(None, {"model": "test"}, "token")


def test_update_leaderboard_value_error(mocker):
    """Test update_leaderboard with ValueError."""
    mocker.patch("smoltrace.utils.login")
    mock_load = mocker.patch("smoltrace.utils.load_dataset")
    mock_load.side_effect = ValueError("Invalid dataset")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance

    new_row = {"model": "test-model", "agent_type": "both"}

    # Should handle ValueError and create new leaderboard
    update_leaderboard("test/leaderboard", new_row, "test_token")

    mock_dataset.from_list.assert_called_once()


# Tests for push_results_to_hf
def test_push_results_to_hf(mocker):
    """Test pushing results to HuggingFace Hub."""
    mocker.patch("smoltrace.utils.login")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance
    mock_flatten = mocker.patch("smoltrace.utils.flatten_results_for_hf")
    mock_flatten.return_value = [{"test_id": "t1"}]

    all_results = {"tool": [{"test_id": "t1"}]}
    trace_data = [{"trace_id": "tr1"}]
    metric_data = {"aggregates": []}  # Missing resourceMetrics, but empty metrics dataset created

    push_results_to_hf(
        all_results,
        trace_data,
        metric_data,
        "test/results",
        "test/traces",
        "test/metrics",
        "test-model",
        "test_token",
        private=False,
    )

    # Should be called 3 times (results, traces, empty metrics for API model)
    assert mock_dataset.from_list.call_count == 3
    assert mock_ds_instance.push_to_hub.call_count == 3


def test_push_results_to_hf_with_env_token(mocker):
    """Test pushing results with token from environment."""
    mocker.patch.dict(os.environ, {"HF_TOKEN": "env_token"})
    mock_login = mocker.patch("smoltrace.utils.login")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance
    mock_flatten = mocker.patch("smoltrace.utils.flatten_results_for_hf")
    mock_flatten.return_value = []

    push_results_to_hf(
        {},
        [],
        {},
        "test/results",
        "test/traces",
        "test/metrics",
        "test-model",
        None,  # No token provided, should use env
    )

    mock_login.assert_called_once_with("env_token")


# Tests for save_results_locally
def test_save_results_locally():
    """Test saving results to local files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        all_results = {
            "tool": [
                {
                    "test_id": "t1",
                    "success": True,
                    "agent_type": "tool",
                    "difficulty": "easy",
                    "prompt": "test prompt",
                    "tool_called": True,
                    "correct_tool": True,
                    "final_answer_called": True,
                    "tools_used": ["tool1"],
                    "steps": 3,
                    "response": "response",
                }
            ]
        }
        trace_data = [{"trace_id": "tr1"}]
        metric_data = [{"name": "test_metric"}]

        output_path = save_results_locally(
            all_results,
            trace_data,
            metric_data,
            "test-model",
            "tool",
            "test-dataset",
            temp_dir,
        )

        # Check that output directory was created and returned
        assert os.path.exists(output_path)
        assert os.path.isdir(output_path)

        # Check files were created in the output directory
        files = os.listdir(output_path)
        assert "results.json" in files
        assert "traces.json" in files
        assert "metrics.json" in files


def test_save_results_locally_with_flatten(mocker):
    """Test saving results with flattening."""
    mock_flatten = mocker.patch("smoltrace.utils.flatten_results_for_hf")
    mock_flatten.return_value = [{"test_id": "t1", "model": "test-model"}]

    # Mock compute_leaderboard_row to avoid KeyError in results data
    mock_compute = mocker.patch("smoltrace.utils.compute_leaderboard_row")
    mock_compute.return_value = {"model": "test-model", "success_rate": 100.0}

    with tempfile.TemporaryDirectory() as temp_dir:
        all_results = {
            "tool": [
                {
                    "test_id": "t1",
                    "success": True,
                    "agent_type": "tool",
                    "difficulty": "easy",
                    "prompt": "test",
                    "tool_called": True,
                    "correct_tool": True,
                    "final_answer_called": True,
                    "tools_used": [],
                    "steps": 1,
                    "response": "test",
                }
            ]
        }

        output_path = save_results_locally(
            all_results,
            [],
            [],
            "test-model",
            "tool",
            "test-dataset",
            temp_dir,
        )

        mock_flatten.assert_called_once_with(all_results, "test-model")
        assert os.path.exists(output_path)


# Tests for missing coverage lines


def test_aggregate_gpu_metrics_with_sum_type():
    """Test GPU metrics aggregation with 'sum' metric type (lines 92-93)."""
    resource_metrics = [
        {
            "scopeMetrics": [
                {
                    "metrics": [
                        {
                            "name": "gen_ai.gpu.power",
                            "sum": {
                                "dataPoints": [
                                    {"asDouble": 250.0},
                                    {"asDouble": 300.0},
                                ]
                            },
                        },
                    ]
                }
            ]
        }
    ]

    result = aggregate_gpu_metrics(resource_metrics)

    # Power metric uses sum type, should be aggregated
    assert result["power_avg"] == 275.0


def test_compute_leaderboard_row_with_invalid_tokens():
    """Test compute_leaderboard_row with invalid token values (lines 155-156)."""
    model_name = "test-model"
    all_results = {
        "tool": [
            {"test_id": "t1", "success": True, "steps": 5},
        ],
    }
    trace_data = [
        {
            "test_id": "t1",
            "total_tokens": "invalid",  # Invalid string that can't be converted
            "total_duration_ms": 500,
            "total_cost_usd": 0.001,
        },
    ]
    metric_data = {}

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should handle invalid token value gracefully, defaulting to 0
    assert leaderboard_row["total_tokens"] == 0


def test_compute_leaderboard_row_with_invalid_duration():
    """Test compute_leaderboard_row with invalid duration values (lines 164-165)."""
    model_name = "test-model"
    all_results = {
        "tool": [
            {"test_id": "t1", "success": True, "steps": 5},
        ],
    }
    trace_data = [
        {
            "test_id": "t1",
            "total_tokens": 100,
            "total_duration_ms": "not-a-number",  # Invalid string
            "total_cost_usd": 0.001,
        },
    ]
    metric_data = {}

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should handle invalid duration value gracefully, defaulting to 0
    assert leaderboard_row["total_duration_ms"] == 0
    assert leaderboard_row["avg_duration_ms"] == 0


def test_compute_leaderboard_row_with_invalid_cost():
    """Test compute_leaderboard_row with invalid cost values (lines 171-172)."""
    model_name = "test-model"
    all_results = {
        "tool": [
            {"test_id": "t1", "success": True, "steps": 5},
        ],
    }
    trace_data = [
        {
            "test_id": "t1",
            "total_tokens": 100,
            "total_duration_ms": 500,
            "total_cost_usd": "invalid-cost",  # Invalid string
        },
    ]
    metric_data = {}

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should handle invalid cost value gracefully, defaulting to 0.0
    assert leaderboard_row["total_cost_usd"] == 0.0


def test_compute_leaderboard_row_with_invalid_co2():
    """Test compute_leaderboard_row with invalid CO2 values (lines 187-188)."""
    model_name = "test-model"
    all_results = {
        "tool": [
            {"test_id": "t1", "success": True, "steps": 5},
        ],
    }
    trace_data = []
    metric_data = {
        "aggregates": [
            {
                "name": "gen_ai.co2.emissions",
                "data_points": [{"value": {"value": "not-a-number"}}],  # Invalid value
            }
        ]
    }

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should handle invalid CO2 value gracefully, defaulting to 0
    assert leaderboard_row["co2_emissions_g"] == 0


def test_compute_leaderboard_row_with_gpu_metrics():
    """Test compute_leaderboard_row with resourceMetrics (line 194)."""
    model_name = "test-model"
    all_results = {
        "tool": [
            {"test_id": "t1", "success": True, "steps": 5},
        ],
    }
    trace_data = []
    metric_data = {
        "resourceMetrics": [
            {
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": "gen_ai.gpu.utilization",
                                "gauge": {
                                    "dataPoints": [
                                        {"asInt": "80"},
                                        {"asInt": "90"},
                                    ]
                                },
                            },
                        ]
                    }
                ]
            }
        ]
    }

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should aggregate GPU metrics from resourceMetrics
    assert leaderboard_row["gpu_utilization_avg"] == 85.0
    assert leaderboard_row["gpu_utilization_max"] == 90.0


def test_compute_leaderboard_row_hf_user_info_exception(mocker):
    """Test compute_leaderboard_row when get_hf_user_info raises exception (lines 200-205)."""
    mocker.patch.dict(os.environ, {"HF_TOKEN": "test_token"})
    mock_get_hf = mocker.patch("smoltrace.utils.get_hf_user_info")
    mock_get_hf.side_effect = Exception("Network error")

    model_name = "test-model"
    all_results = {"tool": [{"test_id": "t1", "success": True, "steps": 5}]}
    trace_data = []
    metric_data = {}

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should handle exception gracefully and use default "unknown"
    assert leaderboard_row["submitted_by"] == "unknown"


def test_compute_leaderboard_row_hf_user_info_returns_none(mocker):
    """Test compute_leaderboard_row when get_hf_user_info returns None (lines 202-203)."""
    mocker.patch.dict(os.environ, {"HF_TOKEN": "test_token"})
    mock_get_hf = mocker.patch("smoltrace.utils.get_hf_user_info")
    mock_get_hf.return_value = None  # Returns None instead of user info

    model_name = "test-model"
    all_results = {"tool": [{"test_id": "t1", "success": True, "steps": 5}]}
    trace_data = []
    metric_data = {}

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should handle None gracefully and use default "unknown"
    assert leaderboard_row["submitted_by"] == "unknown"


def test_compute_leaderboard_row_with_hf_user_info_success(mocker):
    """Test compute_leaderboard_row when get_hf_user_info succeeds (line 203)."""
    mocker.patch.dict(os.environ, {"HF_TOKEN": "test_token"})
    mock_get_hf = mocker.patch("smoltrace.utils.get_hf_user_info")
    mock_get_hf.return_value = {
        "username": "test_user",
        "type": "user",
    }

    model_name = "test-model"
    all_results = {"tool": [{"test_id": "t1", "success": True, "steps": 5}]}
    trace_data = []
    metric_data = {}

    leaderboard_row = compute_leaderboard_row(
        model_name,
        all_results,
        trace_data,
        metric_data,
        "test-dataset",
        "test-results",
        "test-traces",
        "test-metrics",
        agent_type="tool",
    )

    # Should extract username from user_info
    assert leaderboard_row["submitted_by"] == "test_user"


def test_push_results_to_hf_no_repo(mocker):
    """Test push_results_to_hf with no results_repo (lines 362-363)."""
    # Should return early without calling any HF functions
    mock_login = mocker.patch("smoltrace.utils.login")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")

    push_results_to_hf(
        all_results={},
        trace_data=[],
        metric_data={},
        results_repo="",  # Empty repo
        traces_repo="test/traces",
        metrics_repo="test/metrics",
        model_name="test-model",
        hf_token="test_token",
    )

    # Should not attempt to login or create datasets
    mock_login.assert_not_called()
    mock_dataset.from_list.assert_not_called()


def test_push_results_to_hf_json_parse_exception(mocker):
    """Test push_results_to_hf with JSON parsing exception (lines 375-384)."""
    mocker.patch("smoltrace.utils.login")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance

    mock_flatten = mocker.patch("smoltrace.utils.flatten_results_for_hf")
    # Return result with enhanced_trace_info that will cause JSON parse error
    mock_flatten.return_value = [
        {
            "test_id": "t1",
            "enhanced_trace_info": "invalid-json{{{",  # Invalid JSON
        }
    ]

    all_results = {"tool": [{"test_id": "t1"}]}

    # Should handle JSON parse exception gracefully
    push_results_to_hf(
        all_results=all_results,
        trace_data=[],
        metric_data={},
        results_repo="test/results",
        traces_repo="test/traces",
        metrics_repo="test/metrics",
        model_name="test-model",
        hf_token="test_token",
    )

    # Should still push results despite JSON error
    mock_ds_instance.push_to_hub.assert_called()


def test_push_results_to_hf_with_resource_metrics(mocker, capsys):
    """Test push_results_to_hf with resourceMetrics data (lines 411-431)."""
    mocker.patch("smoltrace.utils.login")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance
    mock_flatten = mocker.patch("smoltrace.utils.flatten_results_for_hf")
    mock_flatten.return_value = [{"test_id": "t1"}]

    metric_data = {
        "run_id": "test_run_123",
        "resourceMetrics": [
            {
                "resource": {"attributes": []},
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": "gen_ai.gpu.utilization",
                                "unit": "%",
                                "gauge": {
                                    "dataPoints": [
                                        {
                                            "asInt": 80,
                                            "timeUnixNano": "1761544695460017300",
                                            "attributes": [
                                                {"key": "gpu_id", "value": {"stringValue": "0"}}
                                            ],
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                ],
            }
        ],
    }

    push_results_to_hf(
        all_results={"tool": [{"test_id": "t1"}]},
        trace_data=[],
        metric_data=metric_data,
        results_repo="test/results",
        traces_repo="test/traces",
        metrics_repo="test/metrics",
        model_name="test-model",
        hf_token="test_token",
        run_id="test_run_123",
    )

    # Should push metrics with resourceMetrics (now flattened into time-series rows)
    assert mock_dataset.from_list.call_count == 2  # results + metrics
    captured = capsys.readouterr()
    assert "GPU metric time-series rows" in captured.out


def test_push_results_to_hf_with_empty_resource_metrics(mocker, capsys):
    """Test push_results_to_hf with empty resourceMetrics (lines 430-431)."""
    mocker.patch("smoltrace.utils.login")
    mock_dataset = mocker.patch("smoltrace.utils.Dataset")
    mock_ds_instance = Mock()
    mock_dataset.from_list.return_value = mock_ds_instance
    mock_flatten = mocker.patch("smoltrace.utils.flatten_results_for_hf")
    mock_flatten.return_value = [{"test_id": "t1"}]

    metric_data = {
        "run_id": "test_run_123",
        "resourceMetrics": [],  # Empty for API models
    }

    push_results_to_hf(
        all_results={"tool": [{"test_id": "t1"}]},
        trace_data=[],
        metric_data=metric_data,
        results_repo="test/results",
        traces_repo="test/traces",
        metrics_repo="test/metrics",
        model_name="test-model",
        hf_token="test_token",
        run_id="test_run_123",
    )

    # Should push metrics even with empty resourceMetrics
    assert mock_dataset.from_list.call_count == 2  # results + metrics
    captured = capsys.readouterr()
    assert "Pushed empty metrics dataset (API model" in captured.out
