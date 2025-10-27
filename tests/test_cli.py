"""Tests for smoltrace.cli module."""

import sys
from unittest.mock import MagicMock

import pytest

from smoltrace.cli import main


@pytest.fixture
def mock_run_evaluation_flow(mocker):
    """Mock the run_evaluation_flow function to avoid running actual evaluations."""
    return mocker.patch("smoltrace.cli.run_evaluation_flow")


@pytest.fixture
def mock_sys_argv(mocker):
    """Mock sys.argv to control CLI arguments."""
    original_argv = sys.argv.copy()
    yield
    sys.argv = original_argv


def test_cli_minimal_args(mock_run_evaluation_flow, mocker):
    """Test CLI with minimal required arguments."""
    sys.argv = ["smoltrace-eval", "--model", "gpt-4"]

    main()

    # Verify run_evaluation_flow was called
    mock_run_evaluation_flow.assert_called_once()
    # CLI passes args object, not kwargs
    args = mock_run_evaluation_flow.call_args[0][0]

    assert args.model == "gpt-4"
    assert args.provider == "litellm"  # default
    assert args.agent_type == "both"  # default


def test_cli_all_args(mock_run_evaluation_flow, mocker):
    """Test CLI with all possible arguments."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "gpt-4",
        "--provider",
        "litellm",
        "--agent-type",
        "tool",
        "--hf-token",
        "test_token",
        "--difficulty",
        "hard",
        "--prompt-yml",
        "prompts.yml",
        "--mcp-server-url",
        "http://localhost:8080",
        "--dataset-name",
        "custom/dataset",
        "--split",
        "test",
        "--private",
        "--enable-otel",
        "--run-id",
        "test-run-123",
        "--output-format",
        "json",
        "--output-dir",
        "./test_output",
        "--quiet",
        "--debug",
    ]

    main()

    mock_run_evaluation_flow.assert_called_once()
    args = mock_run_evaluation_flow.call_args[0][0]

    assert args.model == "gpt-4"
    assert args.provider == "litellm"
    assert args.agent_type == "tool"
    assert args.hf_token == "test_token"
    assert args.difficulty == "hard"
    assert args.enable_otel is True
    assert args.private is True
    assert args.run_id == "test-run-123"
    assert args.output_format == "json"
    assert args.quiet is True
    assert args.debug is True


def test_cli_transformers_provider(mock_run_evaluation_flow, mocker):
    """Test CLI with transformers provider."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "meta-llama/Llama-3.1-8B",
        "--provider",
        "transformers",
    ]

    main()

    mock_run_evaluation_flow.assert_called_once()
    args = mock_run_evaluation_flow.call_args[0][0]

    assert args.provider == "transformers"


def test_cli_ollama_provider(mock_run_evaluation_flow, mocker):
    """Test CLI with ollama provider."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "llama2",
        "--provider",
        "ollama",
    ]

    main()

    mock_run_evaluation_flow.assert_called_once()
    args = mock_run_evaluation_flow.call_args[0][0]

    assert args.provider == "ollama"


def test_cli_code_agent(mock_run_evaluation_flow, mocker):
    """Test CLI with code agent type."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "gpt-4",
        "--agent-type",
        "code",
    ]

    main()

    mock_run_evaluation_flow.assert_called_once()
    args = mock_run_evaluation_flow.call_args[0][0]

    assert args.agent_type == "code"


def test_cli_help(capsys):
    """Test CLI help message."""
    sys.argv = ["smoltrace-eval", "--help"]

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Run agent evaluations" in captured.out
    assert "--model" in captured.out
    assert "--provider" in captured.out


def test_cli_missing_required_arg():
    """Test CLI fails with missing required argument."""
    sys.argv = ["smoltrace-eval"]  # Missing --model

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0


def test_cli_invalid_provider():
    """Test CLI fails with invalid provider."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "gpt-4",
        "--provider",
        "invalid_provider",
    ]

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0


def test_cli_invalid_agent_type():
    """Test CLI fails with invalid agent type."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "gpt-4",
        "--agent-type",
        "invalid_type",
    ]

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0


def test_cli_invalid_difficulty():
    """Test CLI fails with invalid difficulty."""
    sys.argv = [
        "smoltrace-eval",
        "--model",
        "gpt-4",
        "--difficulty",
        "invalid_difficulty",
    ]

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0


def test_cli_env_var_hf_token(mock_run_evaluation_flow, mocker):
    """Test that HF_TOKEN environment variable is used when --hf-token not provided."""
    mocker.patch("os.getenv", return_value="env_token")
    sys.argv = ["smoltrace-eval", "--model", "gpt-4"]

    main()

    mock_run_evaluation_flow.assert_called_once()
    # The token from env should be used in run_evaluation_flow
