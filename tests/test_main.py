"""Tests for smoltrace.main module."""

import os
from argparse import Namespace


def test_run_evaluation_flow_no_token(mocker, capsys):
    """Test run_evaluation_flow with no HF token."""
    from smoltrace.main import run_evaluation_flow

    # Mock args with no token
    args = Namespace(
        hf_token=None,
        model="test-model",
        provider="litellm",
        agent_type="both",
    )

    # Mock environment (no HF_TOKEN)
    mocker.patch.dict(os.environ, {}, clear=True)

    # Run
    run_evaluation_flow(args)

    # Should print error and return early
    captured = capsys.readouterr()
    assert "Error: HuggingFace token not found" in captured.out


def test_run_evaluation_flow_invalid_token(mocker, capsys):
    """Test run_evaluation_flow with invalid HF token."""
    from smoltrace.main import run_evaluation_flow

    args = Namespace(
        hf_token="invalid_token",
        model="test-model",
        provider="litellm",
        agent_type="both",
    )

    # Mock get_hf_user_info to return None (invalid token)
    mock_get_user = mocker.patch("smoltrace.main.get_hf_user_info")
    mock_get_user.return_value = None

    # Run
    run_evaluation_flow(args)

    # Should print error and return early
    captured = capsys.readouterr()
    assert "Error: Invalid HF token" in captured.out


def test_run_evaluation_flow_with_hub_output(mocker, capsys):
    """Test run_evaluation_flow with HuggingFace Hub output."""
    from smoltrace.main import run_evaluation_flow

    # Create args
    args = Namespace(
        hf_token="test_token",
        model="test-model",
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
        output_format="hub",
        output_dir="./output",
        run_id=None,
    )

    # Mock all external functions
    mock_get_user = mocker.patch("smoltrace.main.get_hf_user_info")
    mock_get_user.return_value = {"username": "test_user"}

    mock_generate = mocker.patch("smoltrace.main.generate_dataset_names")
    mock_generate.return_value = (
        "test_user/results",
        "test_user/traces",
        "test_user/metrics",
        "test_user/leaderboard",
    )

    mock_load_config = mocker.patch("smoltrace.main.load_prompt_config")
    mock_load_config.return_value = None

    mock_run_eval = mocker.patch("smoltrace.main.run_evaluation")
    mock_run_eval.return_value = (
        {"tool": [], "code": []},  # all_results
        [],  # trace_data
        {},  # metric_data
        "test/dataset",  # dataset_used
        "run_123",  # run_id
    )

    mock_push = mocker.patch("smoltrace.main.push_results_to_hf")
    mock_compute = mocker.patch("smoltrace.main.compute_leaderboard_row")
    mock_compute.return_value = {"model": "test-model"}
    mock_update = mocker.patch("smoltrace.main.update_leaderboard")

    # Run
    run_evaluation_flow(args)

    # Verify function calls
    mock_get_user.assert_called_once_with("test_token")
    mock_generate.assert_called_once_with("test_user")
    mock_run_eval.assert_called_once()
    mock_push.assert_called_once()
    mock_compute.assert_called_once()
    mock_update.assert_called_once()

    # Verify output
    captured = capsys.readouterr()
    assert "[OK] Logged in as: test_user" in captured.out
    assert "[RESULTS] Will be saved to: test_user/results" in captured.out
    assert "[RUN ID] run_123" in captured.out
    assert "[SUCCESS] Evaluation complete! Results pushed to HuggingFace Hub" in captured.out


def test_run_evaluation_flow_with_json_output(mocker, capsys):
    """Test run_evaluation_flow with local JSON output."""
    from smoltrace.main import run_evaluation_flow

    args = Namespace(
        hf_token="test_token",
        model="test-model",
        provider="transformers",  # Test GPU metrics path
        agent_type="tool",  # Single agent type
        quiet=False,
        debug=False,
        enable_otel=True,
        prompt_yml=None,
        mcp_server_url=None,
        difficulty="easy",
        dataset_name="test/dataset",
        split="train",
        private=False,
        output_format="json",  # JSON output
        output_dir="./output",
        run_id="custom_run_id",
    )

    # Mock all external functions
    mock_get_user = mocker.patch("smoltrace.main.get_hf_user_info")
    mock_get_user.return_value = {"username": "test_user"}

    mock_generate = mocker.patch("smoltrace.main.generate_dataset_names")
    mock_generate.return_value = (
        "test_user/results",
        "test_user/traces",
        "test_user/metrics",
        "test_user/leaderboard",
    )

    mock_load_config = mocker.patch("smoltrace.main.load_prompt_config")
    mock_load_config.return_value = None

    mock_run_eval = mocker.patch("smoltrace.main.run_evaluation")
    mock_run_eval.return_value = (
        {"tool": []},  # all_results
        [],  # trace_data
        {},  # metric_data
        "test/dataset",  # dataset_used
        "custom_run_id",  # run_id
    )

    # Mock save_results_locally from utils module (imported inside the function)
    mock_save = mocker.patch("smoltrace.utils.save_results_locally")
    mock_save.return_value = "./output/test-model_tool_20251116_123456"

    # Run
    run_evaluation_flow(args)

    # Verify function calls
    mock_save.assert_called_once()
    call_args = mock_save.call_args[0]
    assert call_args[3] == "test-model"  # model_name
    assert call_args[4] == "tool"  # agent_type
    assert call_args[5] == "test/dataset"  # dataset_used
    assert call_args[6] == "./output"  # output_dir

    # Verify enable_gpu_metrics is True for transformers
    eval_call_kwargs = mock_run_eval.call_args[1]
    assert eval_call_kwargs["enable_gpu_metrics"] is True

    # Verify agent_types is list with single element
    assert eval_call_kwargs["agent_types"] == ["tool"]

    # Verify output
    captured = capsys.readouterr()
    assert "[SUCCESS] Evaluation complete! Results saved locally" in captured.out
    assert "results.json" in captured.out


def test_run_evaluation_flow_with_prompt_config(mocker, capsys):
    """Test run_evaluation_flow with prompt configuration file."""
    from smoltrace.main import run_evaluation_flow

    args = Namespace(
        hf_token="test_token",
        model="test-model",
        provider="litellm",
        agent_type="both",
        quiet=False,
        debug=False,
        enable_otel=True,
        prompt_yml="prompts.yml",  # Prompt config file
        mcp_server_url=None,
        difficulty=None,
        dataset_name="test/dataset",
        split="train",
        private=True,  # Test private datasets
        output_format="hub",
        output_dir="./output",
        run_id=None,
    )

    # Mock all external functions
    mock_get_user = mocker.patch("smoltrace.main.get_hf_user_info")
    mock_get_user.return_value = {"username": "test_user"}

    mock_generate = mocker.patch("smoltrace.main.generate_dataset_names")
    mock_generate.return_value = (
        "test_user/results",
        "test_user/traces",
        "test_user/metrics",
        "test_user/leaderboard",
    )

    mock_load_config = mocker.patch("smoltrace.main.load_prompt_config")
    mock_load_config.return_value = {
        "system_prompt": "Test prompt",
        "user_template": "Hello {name}",
    }

    mock_run_eval = mocker.patch("smoltrace.main.run_evaluation")
    mock_run_eval.return_value = (
        {"tool": [], "code": []},
        [],
        {},
        "test/dataset",
        "run_123",
    )

    mock_push = mocker.patch("smoltrace.main.push_results_to_hf")
    mock_compute = mocker.patch("smoltrace.main.compute_leaderboard_row")
    mock_compute.return_value = {"model": "test-model"}
    mocker.patch("smoltrace.main.update_leaderboard")

    # Run
    run_evaluation_flow(args)

    # Verify prompt config was loaded
    mock_load_config.assert_called_once_with("prompts.yml")

    # Verify output
    captured = capsys.readouterr()
    assert "[CONFIG] Loaded prompt config from prompts.yml" in captured.out

    # Verify private=True was passed to push_results_to_hf
    push_call_args = mock_push.call_args[0]
    # private is at position 8 (0-indexed):
    # all_results, trace_data, metric_data, results_repo, traces_repo, metrics_repo, model_name, hf_token, private, run_id
    # Positions: 0          1          2            3             4            5              6           7        8        9
    assert push_call_args[8] is True  # args.private


def test_run_evaluation_flow_with_env_token(mocker, capsys):
    """Test run_evaluation_flow with HF_TOKEN from environment."""
    from smoltrace.main import run_evaluation_flow

    args = Namespace(
        hf_token=None,  # No token in args
        model="test-model",
        provider="litellm",
        agent_type="code",
        quiet=True,  # Test quiet mode
        debug=True,  # Test debug mode
        enable_otel=False,  # Test OTEL disabled
        prompt_yml=None,
        mcp_server_url="http://localhost:8080",  # Test MCP server
        difficulty=None,
        dataset_name="test/dataset",
        split="train",
        private=False,
        output_format="hub",
        output_dir="./output",
        run_id=None,
    )

    # Mock environment with HF_TOKEN
    mocker.patch.dict(os.environ, {"HF_TOKEN": "env_token"})

    # Mock all external functions
    mock_get_user = mocker.patch("smoltrace.main.get_hf_user_info")
    mock_get_user.return_value = {"username": "test_user"}

    mock_generate = mocker.patch("smoltrace.main.generate_dataset_names")
    mock_generate.return_value = (
        "test_user/results",
        "test_user/traces",
        "test_user/metrics",
        "test_user/leaderboard",
    )

    mock_load_config = mocker.patch("smoltrace.main.load_prompt_config")
    mock_load_config.return_value = None

    mock_run_eval = mocker.patch("smoltrace.main.run_evaluation")
    mock_run_eval.return_value = (
        {"code": []},
        [],
        {},
        "test/dataset",
        "run_123",
    )

    mocker.patch("smoltrace.main.push_results_to_hf")
    mock_compute = mocker.patch("smoltrace.main.compute_leaderboard_row")
    mock_compute.return_value = {"model": "test-model"}
    mocker.patch("smoltrace.main.update_leaderboard")

    # Run
    run_evaluation_flow(args)

    # Verify token from environment was used
    mock_get_user.assert_called_once_with("env_token")

    # Verify verbose=False (quiet=True)
    eval_call_kwargs = mock_run_eval.call_args[1]
    assert eval_call_kwargs["verbose"] is False
    assert eval_call_kwargs["debug"] is True
    assert eval_call_kwargs["enable_otel"] is False
    assert eval_call_kwargs["mcp_server_url"] == "http://localhost:8080"


def test_run_evaluation_flow_gpu_metrics_disabled_for_litellm(mocker):
    """Test that GPU metrics are disabled for litellm provider."""
    from smoltrace.main import run_evaluation_flow

    args = Namespace(
        hf_token="test_token",
        model="test-model",
        provider="litellm",  # Not transformers
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
        output_format="hub",
        output_dir="./output",
        run_id=None,
    )

    # Mock all external functions
    mock_get_user = mocker.patch("smoltrace.main.get_hf_user_info")
    mock_get_user.return_value = {"username": "test_user"}

    mock_generate = mocker.patch("smoltrace.main.generate_dataset_names")
    mock_generate.return_value = (
        "test_user/results",
        "test_user/traces",
        "test_user/metrics",
        "test_user/leaderboard",
    )

    mock_load_config = mocker.patch("smoltrace.main.load_prompt_config")
    mock_load_config.return_value = None

    mock_run_eval = mocker.patch("smoltrace.main.run_evaluation")
    mock_run_eval.return_value = (
        {"tool": [], "code": []},
        [],
        {},
        "test/dataset",
        "run_123",
    )

    mocker.patch("smoltrace.main.push_results_to_hf")
    mock_compute = mocker.patch("smoltrace.main.compute_leaderboard_row")
    mock_compute.return_value = {"model": "test-model"}
    mocker.patch("smoltrace.main.update_leaderboard")

    # Run
    run_evaluation_flow(args)

    # Verify enable_gpu_metrics is False for litellm
    eval_call_kwargs = mock_run_eval.call_args[1]
    assert eval_call_kwargs["enable_gpu_metrics"] is False
